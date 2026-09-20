"""Entrada HTTP del sistema. No es dominio: traduce peticiones a llamadas de módulo y de
vuelta, y ese es todo su trabajo. La validación, el almacenamiento y el encolado viven en
`ingesta` e `infraestructura`."""

from pathlib import Path

from fastapi import Depends, FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from api.esquemas import (
    VERSION_DEL_CONTRATO,
    ArchivoRechazadoEnRespuesta,
    HojaAceptadaEnRespuesta,
    RespuestaDeCarga,
    RespuestaDeSalud,
)
from api.settings import (
    ALLOWED_ORIGIN,
    NOMBRE_COLA,
    REDIS_URL,
    RUTA_ALMACEN,
    RUTA_BITACORA,
)
from infraestructura.almacen import AlmacenDeImagenes, AlmacenEnDisco
from infraestructura.bitacora import BitacoraDeRecepcion, BitacoraEnDisco
from infraestructura.cola import cliente_redis
from infraestructura.modelo import ArchivoCargado
from ingesta import recibir_lote

app = FastAPI(
    title="Sistema de Calificación OMR",
    # Sin `version`, FastAPI publica «0.1.0» por omisión y el documento no dice nada: un
    # consumidor no puede distinguir un contrato estable de uno recién generado. El número lo
    # fija `api/esquemas.py`, junto a los esquemas que versiona.
    version=VERSION_DEL_CONTRATO,
    description=(
        "Interfaz HTTP del sistema de calificación de exámenes de opción múltiple. "
        "Hoy cubre el aspecto A-01 (carga de hojas escaneadas para calificación)."
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


@app.get("/health", summary="Sonda de vida", response_description="La API responde.")
def salud() -> RespuestaDeSalud:
    return RespuestaDeSalud(status="ok")


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
