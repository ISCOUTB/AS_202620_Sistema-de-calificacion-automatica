"""Modelo de datos compartido por los siete módulos del dominio.

Vive en `infraestructura` porque es el único módulo que todos los demás declaran poder
importar (ver la línea `Importa:` de cada `__init__.py`), así que ubicarlo aquí no obliga a
mover ninguna frontera ni a escribir un ADR para habilitarlo.

Solo depende de la biblioteca estándar: `infraestructura` declara `Importa: ninguno` y este
archivo no puede ser la excepción. Tampoco conoce FastAPI ni Redis; el dominio no debe saber
por qué puerta entró un archivo ni a dónde se guardó.

Hoy cubre únicamente el aspecto A-01 (carga de examen para calificación). Los aspectos A-02 a
A-05 sumarán aquí sus propias estructuras —detección, nota, clave— cuando se especifiquen.
"""

from dataclasses import dataclass
from datetime import datetime

__all__ = [
    "ArchivoCargado",
    "HojaAceptada",
    "ArchivoRechazado",
    "ResultadoRecepcion",
    "EntradaDeBitacora",
    "ENCOLADA",
    "PENDIENTE_DE_ENCOLAR",
]

# Estados en los que puede quedar una hoja aceptada. Son dos y no uno desde
# [ADR-0006](../../docs/adr/0006-registrar-la-recepcion-en-una-bitacora-antes-de-encolar.md):
# una hoja puede estar almacenada y registrada sin que su trabajo haya llegado a la cola, y
# EC-07 exige que el docente vea esa diferencia en lugar de no ver la hoja.
ENCOLADA = "encolada"
PENDIENTE_DE_ENCOLAR = "pendiente_de_encolar"


@dataclass(frozen=True)
class ArchivoCargado:
    """Un archivo tal como llega, antes de que nadie lo haya juzgado.

    Es deliberadamente pobre: nombre y bytes. Que el transporte haya sido una petición HTTP
    multipart es asunto de `api`, no del dominio."""

    nombre: str
    contenido: bytes


@dataclass(frozen=True)
class HojaAceptada:
    """Una hoja que pasó la validación y quedó almacenada, con su trabajo encolado o pendiente.

    `referencia` es la ubicación que devolvió el almacén, opaca a propósito: quien la recibe no
    debe suponer que es una ruta de disco, porque el ADR de persistencia (R-06) puede
    convertirla en una clave de objeto sin que este modelo cambie.

    `estado` distingue la hoja cuyo trabajo llegó a la cola de la que quedó almacenada y
    registrada en la bitácora esperando un reintento. El `trabajo_id` existe en ambos casos:
    se acuña antes de tocar la cola, precisamente para que la entrada de bitácora y el trabajo
    que llegue después se refieran al mismo identificador.

    **`hoja_id` y `trabajo_id` son dos identidades distintas** desde
    [ADR-0018](../../docs/adr/0018-dar-a-la-hoja-una-identidad-propia-y-derivar-su-estado-de-la-bitacora.md).
    `hoja_id` es la de la hoja: se acuña una sola vez, al aceptarla, y es la que referenciará todo
    lo que se sepa de ella después (la detección, la nota, la revisión manual). `trabajo_id` es
    la de un encargo de procesarla: el reintento desde la bitácora conserva el mismo, y volver a
    procesar la hoja (por ejemplo, para recalificarla tras corregir la clave) será un trabajo
    nuevo de la misma hoja. Usar uno para las dos cosas obligaba a elegir entre poder
    reprocesar y que el worker no procese dos veces el mismo encargo (ADR-0016).

    **`estado` es una instantánea del momento de la respuesta, no el estado vigente.** El
    estado vigente de una hoja se deriva de la bitácora, que es su fuente de verdad (ADR-0018 y
    la violación V-3 del arc42 §8.3): una hoja `pendiente_de_encolar` que después se reintente
    seguirá diciendo `pendiente_de_encolar` en esta copia."""

    examen_id: str
    nombre_archivo: str
    referencia: str
    trabajo_id: str
    recibida_en: datetime
    hoja_id: str
    estado: str = ENCOLADA


@dataclass(frozen=True)
class ArchivoRechazado:
    """Un archivo que no se admitió, con el motivo en texto legible para el docente.

    El motivo es obligatorio: EC-07 exige que ningún archivo desaparezca sin dejar traza, y un
    rechazo sin explicación es indistinguible de una pérdida desde el lado del usuario."""

    nombre_archivo: str
    motivo: str


@dataclass(frozen=True)
class ResultadoRecepcion:
    """Lo que se le responde al docente tras una carga: qué entró y qué no.

    Su invariante es la promesa de EC-07: la suma de aceptadas y rechazados es igual al número
    de archivos que se cargaron. Ningún archivo se pierde en silencio."""

    examen_id: str
    aceptadas: tuple[HojaAceptada, ...]
    rechazados: tuple[ArchivoRechazado, ...]

    @property
    def total_procesados(self) -> int:
        return len(self.aceptadas) + len(self.rechazados)


@dataclass(frozen=True)
class EntradaDeBitacora:
    """Una hoja almacenada cuyo procesamiento se va a encolar, o quedó pendiente de encolarse.

    Es lo mínimo que hace falta para reintentar sin volver a pedirle el archivo al docente: el
    identificador del trabajo, dónde quedó la imagen y de qué examen es. Desde ADR-0018 lleva
    también la identidad de la hoja, para que el reintento publique un trabajo de la misma hoja
    y no una hoja nueva."""

    trabajo_id: str
    examen_id: str
    referencia: str
    nombre_archivo: str
    hoja_id: str
