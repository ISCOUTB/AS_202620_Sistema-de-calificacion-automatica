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
from infraestructura.bitacora import BitacoraDeRecepcion
from infraestructura.cola import ColaNoDisponible, preparar_trabajo, publicar
from infraestructura.modelo import (
    ENCOLADA,
    PENDIENTE_DE_ENCOLAR,
    ArchivoCargado,
    ArchivoRechazado,
    EntradaDeBitacora,
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
    bitacora: BitacoraDeRecepcion,
) -> ResultadoRecepcion:
    """Procesa un lote completo y devuelve el reporte de recepción.

    El orden importa y es el que sostiene la promesa de EC-07. Son cuatro pasos por hoja y
    ninguno se puede adelantar: se almacena, se acuña el trabajo, se registra en la bitácora y
    solo entonces se publica en la cola. Almacenar primero evita que al worker le llegue un
    trabajo apuntando a una imagen que todavía no existe; registrar antes de publicar evita lo
    contrario, que la imagen exista y nadie sepa que está ahí.

    **El fallo de la cola ya no tumba el lote.** Antes de
    [ADR-0006](../../docs/adr/0006-registrar-la-recepcion-en-una-bitacora-antes-de-encolar.md)
    una excepción al encolar la hoja número cien abortaba la función entera: el docente recibía
    un 500, ninguna de las doscientas hojas quedaba reportada y las noventa y nueve ya
    encoladas se duplicaban al reintentar. Medido, eran 100 % de pérdida silenciosa contra un
    umbral de 0 % (`docs/evidencia/medicion-ec07.md`). Hoy la hoja se reporta como aceptada con
    estado `pendiente_de_encolar`: está almacenada, está en la bitácora y se puede reintentar
    desde ahí sin pedirle el archivo otra vez al docente.

    **El lote deja de insistir con una cola caída.** El primer `ColaNoDisponible` marca la cola
    como no disponible para lo que resta del lote, y las hojas siguientes se almacenan, se
    registran y se reportan como pendientes sin volver a intentar publicarlas. Esto es lo que
    mantiene alcanzable el techo de 10 s del escenario: reintentar 200 veces contra un servidor
    ausente cuesta el timeout de conexión en cada intento y lleva el lote a más de veinte
    minutos, para terminar exactamente en el mismo estado.

    Lo que sigue sin resolverse, y conviene no vendérselo a nadie: la bitácora es de un solo
    proceso y el reintento todavía no está automatizado. `bitacora.pendientes()` deja el dato
    listo para el proceso que lo consuma, y ese proceso es trabajo del aspecto A-02. Tampoco se
    reintenta dentro del propio lote si la cola se recupera a mitad de camino: se prefiere un
    lote rápido y honesto sobre uno lento que adivina.
    """
    aceptadas: list[HojaAceptada] = []
    rechazados: list[ArchivoRechazado] = []

    # Una vez que la cola dejó de responder, no se vuelve a intentar en lo que queda del lote.
    # No es una optimización: es lo que hace alcanzable el techo de 10 s de EC-07. Un cliente de
    # Redis que no encuentra servidor tarda segundos en rendirse (7,1 s medidos contra un
    # contenedor detenido), así que reintentar hoja por hoja convierte un lote de 200 en más de
    # veinte minutos de espera para llegar al mismo sitio: las mismas 200 hojas almacenadas,
    # registradas y pendientes. El primer fallo ya contestó la pregunta.
    cola_disponible = True

    for archivo in archivos:
        motivo = motivo_de_rechazo(archivo)
        if motivo is not None:
            rechazados.append(ArchivoRechazado(nombre_archivo=archivo.nombre, motivo=motivo))
            continue

        referencia = almacen.guardar(examen_id, archivo.nombre, archivo.contenido)

        trabajo = preparar_trabajo(
            {
                "examen_id": examen_id,
                "referencia": referencia,
                "nombre_archivo": archivo.nombre,
            }
        )
        bitacora.registrar(
            EntradaDeBitacora(
                trabajo_id=trabajo.id,
                examen_id=examen_id,
                referencia=referencia,
                nombre_archivo=archivo.nombre,
            )
        )

        if not cola_disponible:
            estado = PENDIENTE_DE_ENCOLAR
        else:
            try:
                publicar(cliente_cola, nombre_cola, trabajo)
            except ColaNoDisponible:
                cola_disponible = False
                estado = PENDIENTE_DE_ENCOLAR
            else:
                bitacora.confirmar_encolada(trabajo.id)
                estado = ENCOLADA

        aceptadas.append(
            HojaAceptada(
                examen_id=examen_id,
                nombre_archivo=archivo.nombre,
                referencia=referencia,
                trabajo_id=trabajo.id,
                recibida_en=datetime.now(timezone.utc),
                estado=estado,
            )
        )

    return ResultadoRecepcion(
        examen_id=examen_id,
        aceptadas=tuple(aceptadas),
        rechazados=tuple(rechazados),
    )
