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

import logging
import time
import uuid
from collections.abc import Callable, Iterable
from datetime import datetime, timezone
from pathlib import PurePosixPath

from infraestructura.almacen import AlmacenDeImagenes
from infraestructura.bitacora import BitacoraDeRecepcion
from infraestructura.cola import (
    ESPERA_AL_PUBLICAR_SEGUNDOS,
    ColaNoDisponible,
    preparar_trabajo,
    publicar,
)
from infraestructura.modelo import (
    ENCOLADA,
    PENDIENTE_DE_ENCOLAR,
    ArchivoCargado,
    ArchivoRechazado,
    EntradaDeBitacora,
    HojaAceptada,
    ResultadoRecepcion,
)

__all__ = [
    "recibir_lote",
    "motivo_de_rechazo",
    "EXTENSIONES_ACEPTADAS",
    "TAMANO_MAXIMO_DE_UNA_HOJA_BYTES",
]

logger = logging.getLogger("ingesta")

# Los dos motivos de una hoja válida que no se pudo recibir. A diferencia de un rechazo por
# formato, el archivo está bien: el motivo dice que no entró y que basta con volver a subirlo.
NO_SE_PUDO_GUARDAR = (
    "No se pudo guardar en el almacén del sistema. La hoja no entró: vuelva a subirla."
)
NO_SE_PUDO_REGISTRAR = (
    "No se pudo registrar su recepción. La hoja no entró: vuelva a subirla."
)

# Cuánto del lote se puede gastar publicando en la cola. EC-07 pide confirmar el lote en 10 s, y
# la última publicación que empiece antes del plazo puede tardar hasta la espera de ADR-0016 en
# terminar: 10 - 2 = 8 s. Vencido el plazo, las hojas que faltan se reportan pendientes, igual
# que tras el primer fallo de la cola.
TECHO_DE_CONFIRMACION_SEGUNDOS = 10.0
PLAZO_PARA_ENCOLAR_SEGUNDOS = TECHO_DE_CONFIRMACION_SEGUNDOS - ESPERA_AL_PUBLICAR_SEGUNDOS

# RNF-02: la entrada es una hoja de respuestas estructurada, escaneada o fotografiada.
FIRMAS_POR_EXTENSION: dict[str, tuple[bytes, ...]] = {
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
    ".png": (b"\x89PNG\r\n\x1a\n",),
    ".pdf": (b"%PDF-",),
}

EXTENSIONES_ACEPTADAS = tuple(sorted(FIRMAS_POR_EXTENSION))

NOMBRES_LEGIBLES = {".jpg": "JPG", ".jpeg": "JPG", ".png": "PNG", ".pdf": "PDF"}

# El tope de una hoja, para que la memoria de la API no dependa de lo que alguien decida subir a
# una ruta pública. El valor es un punto de partida y no una medida: no hay todavía hojas reales
# que pesar (R-01), y se dejó holgado para que quepa una foto de celular. `api` lee como máximo un
# byte más que esto, así que un archivo enorme no llega a cargarse entero para ser rechazado.
TAMANO_MAXIMO_DE_UNA_HOJA_BYTES = 20 * 1024 * 1024


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

    if len(archivo.contenido) > TAMANO_MAXIMO_DE_UNA_HOJA_BYTES:
        maximo_mb = TAMANO_MAXIMO_DE_UNA_HOJA_BYTES // (1024 * 1024)
        return f"El archivo pasa del máximo de {maximo_mb} MB por hoja."

    firmas = FIRMAS_POR_EXTENSION[extension]
    if not any(archivo.contenido.startswith(firma) for firma in firmas):
        return (
            f"El contenido no corresponde a un {NOMBRES_LEGIBLES[extension]}; "
            "puede que el archivo esté dañado o que se le haya cambiado la extensión."
        )

    return None


def recibir_lote(
    examen_id: str,
    archivos: Iterable[ArchivoCargado],
    almacen: AlmacenDeImagenes,
    cliente_cola,
    nombre_cola: str,
    bitacora: BitacoraDeRecepcion,
    plazo_para_encolar_segundos: float = PLAZO_PARA_ENCOLAR_SEGUNDOS,
    reloj: Callable[[], float] = time.monotonic,
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

    **Y deja de insistir con una cola lenta.** La espera corta de ADR-0016 es por llamada, así
    que una cola que contesta cada publicación justo antes de los 2 s nunca falla y lleva el lote
    de 200 a unos 380 s. Por eso hay además un plazo para todo el lote
    (`PLAZO_PARA_ENCOLAR_SEGUNDOS`): vencido, las hojas que faltan se reportan pendientes sin
    tocar la cola, y el lote se confirma dentro del techo de EC-07. `reloj` existe para que las
    pruebas lo comprueben sin esperar.

    **Un fallo del almacén o de la bitácora tampoco tumba el lote.** Es el mismo caso con otro
    colaborador: un disco lleno en la hoja ciento uno devolvía un 500, aunque las cien primeras
    ya estaban almacenadas y en la cola. Hoy la hoja que no se pudo guardar o registrar se
    reporta como rechazada, con un motivo que dice que no entró y que hay que volver a subirla, y
    el lote sigue. Si lo que falla es confirmar en la bitácora una hoja que ya se publicó, la hoja
    se reporta encolada, porque lo está: la bitácora la seguirá dando por pendiente, y si alguien
    la vuelve a publicar llega con el mismo `trabajo_id`, que el worker procesa una sola vez
    (ADR-0016).

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
    inicio = reloj()

    for archivo in archivos:
        motivo = motivo_de_rechazo(archivo)
        if motivo is not None:
            rechazados.append(ArchivoRechazado(nombre_archivo=archivo.nombre, motivo=motivo))
            continue

        try:
            referencia = almacen.guardar(examen_id, archivo.nombre, archivo.contenido)
        except OSError:
            rechazados.append(
                ArchivoRechazado(nombre_archivo=archivo.nombre, motivo=NO_SE_PUDO_GUARDAR)
            )
            continue

        # La identidad de la hoja (ADR-0018), distinta de la de su trabajo: el trabajo es un
        # encargo de procesarla, y la hoja puede tener más de uno.
        hoja_id = str(uuid.uuid4())
        trabajo = preparar_trabajo(
            {
                "hoja_id": hoja_id,
                "examen_id": examen_id,
                "referencia": referencia,
                "nombre_archivo": archivo.nombre,
            }
        )
        try:
            bitacora.registrar(
                EntradaDeBitacora(
                    trabajo_id=trabajo.id,
                    examen_id=examen_id,
                    referencia=referencia,
                    nombre_archivo=archivo.nombre,
                    hoja_id=hoja_id,
                )
            )
        except OSError:
            # La imagen quedó en el almacén, pero sin entrada en la bitácora nadie sabría que
            # está ahí, y publicarla así es lo que ADR-0006 prohíbe. Se rechaza sin encolar; el
            # archivo huérfano no lo lee nadie y no cambia ninguna nota.
            rechazados.append(
                ArchivoRechazado(nombre_archivo=archivo.nombre, motivo=NO_SE_PUDO_REGISTRAR)
            )
            continue

        if cola_disponible and reloj() - inicio > plazo_para_encolar_segundos:
            cola_disponible = False
            logger.warning(
                "Plazo del lote vencido: las hojas que faltan quedan pendientes de encolar",
                extra={"evento": "plazo_de_encolado_vencido", "examen": examen_id},
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
                estado = ENCOLADA
                # El primer eslabón del rastro de un mensaje (ADR-0020): los eventos del worker
                # llevan el mismo `trabajo` y la misma `hoja`.
                logger.info(
                    "Trabajo publicado",
                    extra={
                        "evento": "trabajo_publicado",
                        "trabajo": trabajo.id,
                        "hoja": hoja_id,
                        "examen": examen_id,
                        "cola": nombre_cola,
                    },
                )
                try:
                    bitacora.confirmar_encolada(trabajo.id)
                except OSError as error:
                    logger.warning(
                        "Hoja encolada sin confirmación en la bitácora",
                        extra={
                            "evento": "encolada_sin_confirmar",
                            "trabajo": trabajo.id,
                            "examen": examen_id,
                            "error": str(error),
                        },
                    )

        aceptadas.append(
            HojaAceptada(
                examen_id=examen_id,
                nombre_archivo=archivo.nombre,
                referencia=referencia,
                trabajo_id=trabajo.id,
                recibida_en=datetime.now(timezone.utc),
                hoja_id=hoja_id,
                estado=estado,
            )
        )

    return ResultadoRecepcion(
        examen_id=examen_id,
        aceptadas=tuple(aceptadas),
        rechazados=tuple(rechazados),
    )
