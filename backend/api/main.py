"""Entrada HTTP del sistema. No es dominio: traduce peticiones a llamadas de módulo y de
vuelta, y ese es todo su trabajo. La validación, el almacenamiento y el encolado viven en
`ingesta` e `infraestructura`."""

from pathlib import Path

from fastapi import Depends, FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from api.settings import ALLOWED_ORIGIN, NOMBRE_COLA, REDIS_URL, RUTA_ALMACEN
from infraestructura.almacen import AlmacenDeImagenes, AlmacenEnDisco
from infraestructura.cola import cliente_redis
from infraestructura.modelo import ArchivoCargado
from ingesta import recibir_lote

app = FastAPI(title="Sistema de Calificación OMR")

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


def obtener_cliente_cola():
    """Dependencia de la cola. Misma razón que arriba: si el cliente se creara al importar,
    ninguna prueba de la API podría correr sin un Redis levantado."""
    return cliente_redis(REDIS_URL)


@app.get("/health")
def salud() -> dict:
    return {"status": "ok"}


@app.post("/examenes/{examen_id}/hojas")
async def cargar_hojas(
    examen_id: str,
    archivos: list[UploadFile] = File(...),
    almacen: AlmacenDeImagenes = Depends(obtener_almacen),
    cliente_cola=Depends(obtener_cliente_cola),
) -> dict:
    """Recibe una o varias hojas escaneadas de un examen y confirma qué entró y qué no (RF-01).

    **Responde 200 aunque haya archivos rechazados, y eso es deliberado.** La petición se
    atendió por completo: el 200 confirma que el sistema procesó el lote entero, y el cuerpo
    dice archivo por archivo qué pasó. Devolver un error por un rechazo obligaría al cliente a
    reenviar el lote completo, que es justo lo que EC-07 quiere evitar.

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
    )

    return {
        "examen_id": resultado.examen_id,
        "total_procesados": resultado.total_procesados,
        "aceptadas": [
            {
                "nombre_archivo": hoja.nombre_archivo,
                "referencia": hoja.referencia,
                "trabajo_id": hoja.trabajo_id,
                "recibida_en": hoja.recibida_en.isoformat(),
            }
            for hoja in resultado.aceptadas
        ],
        "rechazados": [
            {"nombre_archivo": r.nombre_archivo, "motivo": r.motivo}
            for r in resultado.rechazados
        ],
    }
