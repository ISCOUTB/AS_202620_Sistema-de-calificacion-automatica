"""Entrada HTTP del sistema. No es dominio: traduce peticiones a llamadas de módulo y de
vuelta, y ese es todo su trabajo. La validación, el almacenamiento y el encolado viven en
`ingesta` e `infraestructura`; la regla de los distractores, en `autoria`."""

import logging
import time
from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from api.esquemas import (
    VERSION_DEL_CONTRATO,
    ArchivoRechazadoEnRespuesta,
    DescartadoEnRespuesta,
    DistractorEnRespuesta,
    HojaAceptadaEnRespuesta,
    ProveedorNoDisponibleEnRespuesta,
    RespuestaDeCarga,
    RespuestaDeDistractores,
    RespuestaDeSalud,
    SolicitudDeDistractores,
)
from api.settings import (
    ALLOWED_ORIGIN,
    LLM_API_KEY,
    LLM_MODELO,
    LLM_URL_BASE,
    NOMBRE_COLA,
    REDIS_URL,
    RUTA_ALMACEN,
    RUTA_BITACORA,
)
from autoria import (
    GeneradorCompatibleConOpenAI,
    GeneradorDeDistractores,
    PreguntaParaDistractores,
    ProveedorNoDisponible,
    proponer_distractores,
)
from infraestructura.almacen import AlmacenDeImagenes, AlmacenEnDisco
from infraestructura.bitacora import BitacoraDeRecepcion, BitacoraEnDisco
from infraestructura.cola import cliente_redis
from infraestructura.modelo import PENDIENTE_DE_ENCOLAR, ArchivoCargado
from infraestructura.registro import configurar_registro
from ingesta import recibir_lote

configurar_registro()
logger = logging.getLogger("api")

app = FastAPI(
    title="QuantIA",
    # Sin `version`, FastAPI publica «0.1.0» por omisión y el documento no dice nada: un
    # consumidor no puede distinguir un contrato estable de uno recién generado. El número lo
    # fija `api/esquemas.py`, junto a los esquemas que versiona.
    version=VERSION_DEL_CONTRATO,
    description=(
        "Interfaz HTTP de QuantIA, sistema de calificación de exámenes de opción múltiple. "
        "Hoy cubre el aspecto A-01 (carga de hojas escaneadas para calificación) y el A-06 "
        "(propuesta opcional de distractores diagnósticos)."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[ALLOWED_ORIGIN],
    allow_methods=["*"],
    allow_headers=["*"],
)


def obtener_almacen() -> AlmacenDeImagenes:
    """Dependencia del almacén. Se construye por petición y no al importar el módulo, para que
    levantar la app no exija que el volumen exista —así `test_arranque` sigue sin tocar disco—
    y para que las pruebas puedan sustituirla con `app.dependency_overrides`."""
    return AlmacenEnDisco(Path(RUTA_ALMACEN))


def obtener_bitacora() -> BitacoraDeRecepcion:
    """Dependencia de la bitácora de recepción (ADR-0006). Por petición y sustituible, por las
    mismas dos razones que el almacén."""
    return BitacoraEnDisco(Path(RUTA_BITACORA))


def obtener_cliente_cola():
    """Dependencia de la cola. Misma razón que arriba: si el cliente se creara al importar,
    ninguna prueba de la API podría correr sin un Redis levantado."""
    return cliente_redis(REDIS_URL)


def obtener_generador() -> GeneradorDeDistractores | None:
    """Dependencia del proveedor de LLM (ADR-0013). Devuelve `None` si no hay clave configurada:
    la ruta de distractores responde 503 y nada más se entera, porque RF-11 es opcional. Por
    petición y sustituible, como las otras, para que ninguna prueba salga a la red."""
    if not LLM_API_KEY:
        return None
    return GeneradorCompatibleConOpenAI(LLM_URL_BASE, LLM_MODELO, LLM_API_KEY)


@app.get("/health", summary="Sonda de vida", response_description="La API responde.")
def salud() -> RespuestaDeSalud:
    return RespuestaDeSalud(status="ok")


# La misma sonda para `HEAD`, que es el método con el que la consulta el monitor externo que
# mantiene despierta la API desplegada (ADR-0009): sin esta ruta respondía 405 y el monitor la
# daba por caída aunque estuviera atendiendo. Queda fuera del contrato publicado a propósito: es
# una conveniencia de operación, no una operación nueva de la API, y `test_contrato.py` sigue
# comparando las mismas dos rutas.
@app.head("/health", include_in_schema=False)
def salud_para_monitores() -> Response:
    return Response(status_code=200)


@app.post(
    "/examenes/{examen_id}/hojas",
    summary="Cargar hojas escaneadas de un examen",
    response_description="Qué entró y qué no, archivo por archivo.",
)
async def cargar_hojas(
    examen_id: str,
    archivos: list[UploadFile] = File(...),
    almacen: AlmacenDeImagenes = Depends(obtener_almacen),
    cliente_cola=Depends(obtener_cliente_cola),
    bitacora: BitacoraDeRecepcion = Depends(obtener_bitacora),
) -> RespuestaDeCarga:
    """Recibe una o varias hojas escaneadas de un examen y confirma qué entró y qué no (RF-01).

    **Responde 200 aunque haya archivos rechazados, y eso es deliberado.** La petición se
    atendió por completo: el 200 confirma que el sistema procesó el lote entero, y el cuerpo
    dice archivo por archivo qué pasó. Devolver un error por un rechazo obligaría al cliente a
    reenviar el lote completo, que es justo lo que EC-07 quiere evitar.

    **Una hoja puede volver como aceptada y todavía pendiente de encolar.** Desde ADR-0006 el
    campo `estado` de cada aceptada vale `encolada` o `pendiente_de_encolar`: la segunda es una
    hoja almacenada y registrada en la bitácora cuyo trabajo no llegó a la cola. Se reporta en
    vez de omitirse porque EC-07 exige que ningún archivo cargado desaparezca sin traza, y
    reintentarla es asunto del sistema, no del docente: el archivo ya está adentro.

    **El `examen_id` todavía no se verifica contra nada, y es un hueco conocido, no un olvido.**
    El módulo `autoria` (aspecto A-04) es el que registrará los exámenes, y aún no existe;
    `identidad` (A-05) es el que comprobará que el docente puede cargar en ese curso, y
    tampoco. La ruta ya tiene la forma definitiva para que cuando esos módulos lleguen solo
    haya que sumar la comprobación, sin migrar el frontend.
    """
    inicio = time.perf_counter()
    cargados = [
        ArchivoCargado(nombre=archivo.filename or "sin-nombre", contenido=await archivo.read())
        for archivo in archivos
    ]

    resultado = recibir_lote(
        examen_id=examen_id,
        archivos=cargados,
        almacen=almacen,
        cliente_cola=cliente_cola,
        nombre_cola=NOMBRE_COLA,
        bitacora=bitacora,
    )

    # La métrica de EC-07 («confirmación del lote en <= 10 s, 0 % de pérdida silenciosa»),
    # registrada en cada lote real y no solo en la medición del corte 1. Cuenta desde que el
    # endpoint tiene los archivos hasta la confirmación, así que no incluye la subida por la red
    # del docente. Aceptadas y rechazadas suman los archivos cargados, que es la invariante de
    # `ResultadoRecepcion`, y las pendientes son las aceptadas que quedaron en la bitácora sin
    # llegar a la cola (ADR-0006).
    logger.info(
        "Lote confirmado",
        extra={
            "evento": "lote_confirmado",
            "examen": resultado.examen_id,
            "hojas_aceptadas": len(resultado.aceptadas),
            "hojas_pendientes_de_encolar": sum(
                1 for hoja in resultado.aceptadas if hoja.estado == PENDIENTE_DE_ENCOLAR
            ),
            "hojas_rechazadas": len(resultado.rechazados),
            "duracion_confirmacion_ms": round((time.perf_counter() - inicio) * 1000, 1),
        },
    )

    # La raíz se construye campo por campo porque los dos que lleva son decisiones del contrato:
    # `examen_id` viaja una sola vez en vez de repetirse por hoja, y `total_procesados` es una
    # propiedad calculada del dominio que aquí pasa a ser un campo publicado.
    #
    # Las hojas y los rechazos se validan desde los atributos de la dataclass, cuyos nombres ya
    # coinciden uno a uno. Eso hace dos cosas que el diccionario anterior no hacía: descarta el
    # `examen_id` de cada hoja de forma explícita, y comprueba `estado` contra los dos valores
    # que el contrato declara, así que una hoja con un estado nuevo falla aquí en vez de salir
    # publicada en una respuesta que el esquema dice que no puede existir.
    return RespuestaDeCarga(
        examen_id=resultado.examen_id,
        total_procesados=resultado.total_procesados,
        aceptadas=[
            HojaAceptadaEnRespuesta.model_validate(hoja) for hoja in resultado.aceptadas
        ],
        rechazados=[
            ArchivoRechazadoEnRespuesta.model_validate(rechazado)
            for rechazado in resultado.rechazados
        ],
    )


@app.post(
    "/distractores",
    summary="Proponer distractores diagnósticos para una pregunta",
    response_description="Las propuestas que pasaron la regla y las que no, con su motivo.",
    responses={
        503: {
            "model": ProveedorNoDisponibleEnRespuesta,
            "description": (
                "El proveedor de LLM no está configurado, no respondió a tiempo o falló. El "
                "profesor puede volver a pedirlo o escribir los distractores a mano."
            ),
        }
    },
)
def proponer_distractores_para_una_pregunta(
    solicitud: SolicitudDeDistractores,
    generador: GeneradorDeDistractores | None = Depends(obtener_generador),
) -> RespuestaDeDistractores:
    """Pide al proveedor de LLM distractores diagnósticos para una pregunta (RF-11, EC-08).

    **Es opcional y se degrada sin arrastrar a nadie.** Si el proveedor no está configurado,
    tarda más de lo que el adaptador espera o falla, la respuesta es 503 con el motivo, y el
    resto de la API sigue igual: la calificación no usa el LLM (ADR-0005) y el registro manual
    de preguntas no depende de él (ADR-0013).

    **Ninguna propuesta que repita la respuesta correcta llega al profesor** (M1 de EC-08). Lo
    que la regla descarta vuelve en `descartados`, con su motivo.

    Es una ruta `def` y no `async def` a propósito: la llamada al proveedor bloquea mientras
    espera, y FastAPI corre estas rutas en su grupo de hilos, así que la espera no detiene a las
    demás peticiones.
    """
    if generador is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "El proveedor de LLM no está configurado en este entorno. Los distractores se "
                "pueden escribir a mano."
            ),
        )
    try:
        resultado = proponer_distractores(
            PreguntaParaDistractores(
                enunciado=solicitud.enunciado,
                respuesta_correcta=solicitud.respuesta_correcta,
                cantidad=solicitud.cantidad,
            ),
            generador,
        )
    except ProveedorNoDisponible as falla:
        raise HTTPException(status_code=503, detail=falla.motivo) from falla

    return RespuestaDeDistractores(
        distractores=[
            DistractorEnRespuesta.model_validate(propuesto) for propuesto in resultado.propuestos
        ],
        descartados=[
            DescartadoEnRespuesta.model_validate(descartado)
            for descartado in resultado.descartados
        ],
    )
