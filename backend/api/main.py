"""Entrada HTTP del sistema. No es dominio: traduce peticiones a llamadas de módulo y de
vuelta, y ese es todo su trabajo. La validación, el almacenamiento y el encolado viven en
`ingesta` e `infraestructura`; la regla de los distractores y el presupuesto del proveedor, en
`autoria`."""

import logging
import time
from collections.abc import Iterator
from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, Response, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware

from api.esquemas import (
    VERSION_DEL_CONTRATO,
    ArchivoRechazadoEnRespuesta,
    DescartadoEnRespuesta,
    DistractorEnRespuesta,
    EstadoDelPresupuestoEnRespuesta,
    HojaAceptadaEnRespuesta,
    PresupuestoAgotadoEnRespuesta,
    ProveedorNoDisponibleEnRespuesta,
    RespuestaDeCarga,
    RespuestaDeDistractores,
    RespuestaDeMetricas,
    RespuestaDeSalud,
    SolicitudDeDistractores,
)
from api.settings import (
    ALLOWED_ORIGIN,
    LLM_API_KEY,
    LLM_MODELO,
    LLM_SOLICITUDES_POR_DIA,
    LLM_SOLICITUDES_POR_MINUTO,
    LLM_URL_BASE,
    NOMBRE_COLA,
    REDIS_URL,
    RUTA_ALMACEN,
    RUTA_BITACORA,
)
from autoria import (
    GeneradorCompatibleConOpenAI,
    GeneradorConPresupuesto,
    GeneradorDeDistractores,
    PreguntaParaDistractores,
    PresupuestoAgotado,
    PresupuestoDeSolicitudes,
    ProveedorNoDisponible,
    proponer_distractores,
)
from infraestructura.almacen import AlmacenDeImagenes, AlmacenEnDisco
from infraestructura.bitacora import BitacoraDeRecepcion, BitacoraEnDisco
from infraestructura.cola import ESPERA_AL_PUBLICAR_SEGUNDOS, cliente_redis
from infraestructura.modelo import PENDIENTE_DE_ENCOLAR, ArchivoCargado
from infraestructura.registro import configurar_registro
from ingesta import TAMANO_MAXIMO_DE_UNA_HOJA_BYTES, recibir_lote

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
        "(propuesta opcional de distractores diagnósticos), con el presupuesto que protege la "
        "cuota del proveedor de LLM y su métrica en `GET /metricas` (EC-09)."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[ALLOWED_ORIGIN],
    allow_methods=["*"],
    allow_headers=["*"],
    # El navegador solo deja leer las cabeceras de respuesta que CORS declara, y `Retry-After`
    # no está entre las que se leen por omisión: sin esta línea, el sitio recibe el 429 del
    # presupuesto (ADR-0015) pero no sabe cuánto tiene que esperar el docente.
    expose_headers=["Retry-After"],
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
    ninguna prueba de la API podría correr sin un Redis levantado.

    La API solo publica, así que usa la espera corta (ADR-0016): un Redis que acepta la conexión
    y no contesta cuesta 2 s al lote y no los 10 s que necesita el worker para su `BLPOP`."""
    return cliente_redis(REDIS_URL, espera_segundos=ESPERA_AL_PUBLICAR_SEGUNDOS)


# El presupuesto del proveedor de LLM (ADR-0015). A diferencia del almacén y la cola, se crea una
# sola vez al importar y no por petición: lo que cuenta tiene que sobrevivir de una solicitud a la
# siguiente. Vive en la memoria de este proceso, que es correcto con la única instancia y el único
# proceso de uvicorn que corren hoy (`arrancar-api-y-worker.sh`), y se vacía con cada reinicio
# (R-18). Crearlo no toca la red ni el disco, así que `test_arranque` sigue igual.
PRESUPUESTO_DE_DISTRACTORES = PresupuestoDeSolicitudes(
    por_minuto=LLM_SOLICITUDES_POR_MINUTO, por_dia=LLM_SOLICITUDES_POR_DIA
)


def obtener_presupuesto() -> PresupuestoDeSolicitudes:
    """Dependencia del presupuesto. Sustituible, como las otras: cada prueba recibe uno nuevo y
    ninguna gasta el cupo de la siguiente."""
    return PRESUPUESTO_DE_DISTRACTORES


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
    El módulo `autoria` es el que registrará los exámenes, y esa parte (aspecto A-04) aún no
    existe; `identidad` (A-05) es el que comprobará que el docente puede cargar en ese curso, y
    tampoco. La ruta ya tiene la forma definitiva para que cuando esas partes lleguen solo
    haya que sumar la comprobación, sin migrar el frontend.
    """
    inicio = time.perf_counter()

    # Las hojas se leen de a una, cuando `recibir_lote` llega a cada una, y no todas antes de
    # empezar: leer el lote entero a una lista eran 200 escaneos a la vez en la memoria de una
    # instancia de 512 MB. Starlette ya dejó cada archivo subido en un temporal (en disco pasado
    # 1 MB), así que en memoria queda solo la hoja en curso. Y de cada una se lee como máximo un
    # byte más que el tope de `ingesta`: alcanza para que la regla la rechace sin cargarla entera.
    def leer_de_a_una() -> Iterator[ArchivoCargado]:
        for archivo in archivos:
            yield ArchivoCargado(
                nombre=archivo.filename or "sin-nombre",
                contenido=archivo.file.read(TAMANO_MAXIMO_DE_UNA_HOJA_BYTES + 1),
            )

    # El lote se confirma en un hilo aparte, no en el que atiende las peticiones, y ahí también
    # se leen las hojas. `recibir_lote` bloquea: escribe con `fsync` dos veces por hoja y espera
    # a Redis hasta 2 s por publicación. Llamarla aquí directamente congelaba el único proceso de
    # uvicorn durante todo el lote, y con él `GET` y `HEAD /health` (el chequeo de Render y el del
    # monitor), `/distractores` y el lote de cualquier otro docente: era el riesgo R-21. (Va en un
    # comentario y no en el docstring porque el docstring se publica en el contrato, y esto no
    # cambia nada de lo que ve quien llama a la ruta.)
    resultado = await run_in_threadpool(
        recibir_lote,
        examen_id=examen_id,
        archivos=leer_de_a_una(),
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
        429: {
            "model": PresupuestoAgotadoEnRespuesta,
            "description": (
                "La solicitud no cabe en el presupuesto del proveedor de LLM y no se envió "
                "(ADR-0015). La cabecera `Retry-After` dice en cuántos segundos habrá cupo."
            ),
        },
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
    presupuesto: PresupuestoDeSolicitudes = Depends(obtener_presupuesto),
) -> RespuestaDeDistractores:
    """Pide al proveedor de LLM distractores diagnósticos para una pregunta (RF-11, EC-08).

    **Es opcional y se degrada sin arrastrar a nadie.** Si el proveedor no está configurado,
    tarda más de lo que el adaptador espera o falla, la respuesta es 503 con el motivo, y el
    resto de la API sigue igual: la calificación no usa el LLM (ADR-0005) y el registro manual
    de preguntas no depende de él (ADR-0013).

    **Ninguna propuesta que repita la respuesta correcta llega al profesor** (M1 de EC-08). Lo
    que la regla descarta vuelve en `descartados`, con su motivo.

    **Ninguna solicitud sale al proveedor sin cupo en el presupuesto** (EC-09, ADR-0015). Si no
    cabe, la respuesta es 429 con `Retry-After`, sin tocar la red. Una solicitud sin proveedor
    configurado responde 503 antes de reservar, así que no gasta cupo.

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
            GeneradorConPresupuesto(generador, presupuesto),
        )
    except PresupuestoAgotado as agotado:
        # La métrica de EC-09 en el registro: cada solicitud cortada deja un evento, con la
        # ventana que la cortó y lo usado en ese momento.
        estado = presupuesto.estado()
        logger.warning(
            "Presupuesto agotado",
            extra={
                "evento": "presupuesto_agotado",
                "ventana": agotado.ventana,
                "reintentar_en_segundos": agotado.reintentar_en_segundos,
                "usadas_en_el_ultimo_minuto": estado.usadas_en_el_ultimo_minuto,
                "usadas_en_las_ultimas_24_horas": estado.usadas_en_las_ultimas_24_horas,
                "rechazadas_desde_el_arranque": estado.rechazadas_desde_el_arranque,
            },
        )
        raise HTTPException(
            status_code=429,
            detail=agotado.motivo,
            headers={"Retry-After": str(agotado.reintentar_en_segundos)},
        ) from agotado
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


@app.get(
    "/metricas",
    summary="Estado del presupuesto del proveedor de LLM",
    response_description="Lo usado en las dos ventanas y lo enviado y cortado desde el arranque.",
)
def metricas(
    presupuesto: PresupuestoDeSolicitudes = Depends(obtener_presupuesto),
) -> RespuestaDeMetricas:
    """La métrica de EC-09 consultable en vivo (ADR-0015).

    Dice cuántas solicitudes al proveedor caben todavía y cuántas se cortaron con 429, sin
    revisar el registro. Solo publica cuentas, ningún dato de un profesor ni de una pregunta, y no
    toca la red ni el disco, así que responde aunque el proveedor esté caído."""
    return RespuestaDeMetricas(
        presupuesto_de_distractores=EstadoDelPresupuestoEnRespuesta.model_validate(
            presupuesto.estado()
        )
    )
