"""Recepción de hojas escaneadas: valida, almacena, encola y responde qué entró y qué no.

Realiza RF-01 y es el corazón del aspecto A-01. Su medida es EC-07: confirmación del lote con
**0 % de pérdida silenciosa**, es decir, todo archivo cargado sale de aquí como *aceptado* o
como *rechazado con motivo*, nunca omitido.

De ahí las dos decisiones de forma de este módulo:

1. **Un archivo inválido no aborta el lote.** Doscientas hojas escaneadas y una corrupta no
   pueden costarle al docente volver a subir las otras ciento noventa y nueve. Cada archivo se
   juzga por separado y el resultado los reporta a todos.
2. **No conoce FastAPI ni Redis.** Recibe bytes y colaboradores; devuelve un dato. Por eso se
   puede probar sin levantar ni un servidor ni una cola.
"""

from datetime import datetime, timezone
from pathlib import PurePosixPath

from infraestructura.almacen import AlmacenDeImagenes
from infraestructura.cola import encolar
from infraestructura.modelo import (
    ArchivoCargado,
    ArchivoRechazado,
    HojaAceptada,
    ResultadoRecepcion,
)

__all__ = ["recibir_lote", "motivo_de_rechazo", "EXTENSIONES_ACEPTADAS"]

# RNF-02: la entrada es una hoja de respuestas estructurada, escaneada o fotografiada.
FIRMAS_POR_EXTENSION: dict[str, tuple[bytes, ...]] = {
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
    ".png": (b"\x89PNG\r\n\x1a\n",),
    ".pdf": (b"%PDF-",),
}

EXTENSIONES_ACEPTADAS = tuple(sorted(FIRMAS_POR_EXTENSION))

NOMBRES_LEGIBLES = {".jpg": "JPG", ".jpeg": "JPG", ".png": "PNG", ".pdf": "PDF"}


def motivo_de_rechazo(archivo: ArchivoCargado) -> str | None:
    """Devuelve el motivo por el que el archivo no se admite, o None si es válido.

    Se revisa la extensión **y** los primeros bytes. Solo la extensión no alcanza: renombrar
    un `.docx` a `.jpg` es trivial y el error aparecería mucho más tarde, dentro del worker,
    cuando ya no hay nadie mirando a quién avisarle."""
    extension = PurePosixPath(archivo.nombre).suffix.lower()

    if extension not in FIRMAS_POR_EXTENSION:
        admitidas = ", ".join(sorted(set(NOMBRES_LEGIBLES.values())))
        visible = extension or "sin extensión"
        return f"Extensión no admitida ({visible}). Se aceptan {admitidas}."

    if not archivo.contenido:
        return "El archivo está vacío (0 bytes)."

    firmas = FIRMAS_POR_EXTENSION[extension]
    if not any(archivo.contenido.startswith(firma) for firma in firmas):
        return (
            f"El contenido no corresponde a un {NOMBRES_LEGIBLES[extension]}; "
            "puede que el archivo esté dañado o que se le haya cambiado la extensión."
        )

    return None


def recibir_lote(
    examen_id: str,
    archivos: list[ArchivoCargado],
    almacen: AlmacenDeImagenes,
    cliente_cola,
    nombre_cola: str,
) -> ResultadoRecepcion:
    """Procesa un lote completo y devuelve el reporte de recepción.

    El orden importa y es el que sostiene la promesa de EC-07: primero se almacena y solo
    después se encola. Al revés, un trabajo podría llegarle al worker apuntando a una imagen
    que todavía no existe.

    Queda un hueco conocido, y es honesto nombrarlo: entre el guardado y el encolado no hay
    transacción. Si el proceso muere justo en medio, el archivo queda huérfano en el almacén.
    Cerrarlo exige acuse de recibo en la cola o una bitácora de recepción, que es parte de lo
    que el ADR de persistencia (R-06) tiene que resolver; hoy no está resuelto y por eso la
    durabilidad tras reinicio no se declara verificada en `docs/aspectos.md`.
    """
    aceptadas: list[HojaAceptada] = []
    rechazados: list[ArchivoRechazado] = []

    for archivo in archivos:
        motivo = motivo_de_rechazo(archivo)
        if motivo is not None:
            rechazados.append(ArchivoRechazado(nombre_archivo=archivo.nombre, motivo=motivo))
            continue

        referencia = almacen.guardar(examen_id, archivo.nombre, archivo.contenido)
        trabajo = encolar(
            cliente_cola,
            nombre_cola,
            {
                "examen_id": examen_id,
                "referencia": referencia,
                "nombre_archivo": archivo.nombre,
            },
        )

        aceptadas.append(
            HojaAceptada(
                examen_id=examen_id,
                nombre_archivo=archivo.nombre,
                referencia=referencia,
                trabajo_id=trabajo.id,
                recibida_en=datetime.now(timezone.utc),
            )
        )

    return ResultadoRecepcion(
        examen_id=examen_id,
        aceptadas=tuple(aceptadas),
        rechazados=tuple(rechazados),
    )
