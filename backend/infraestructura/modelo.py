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
]


@dataclass(frozen=True)
class ArchivoCargado:
    """Un archivo tal como llega, antes de que nadie lo haya juzgado.

    Es deliberadamente pobre: nombre y bytes. Que el transporte haya sido una petición HTTP
    multipart es asunto de `api`, no del dominio."""

    nombre: str
    contenido: bytes


@dataclass(frozen=True)
class HojaAceptada:
    """Una hoja que pasó la validación, quedó almacenada y tiene un trabajo encolado.

    `referencia` es la ubicación que devolvió el almacén, opaca a propósito: quien la recibe no
    debe suponer que es una ruta de disco, porque el ADR de persistencia (R-06) puede
    convertirla en una clave de objeto sin que este modelo cambie."""

    examen_id: str
    nombre_archivo: str
    referencia: str
    trabajo_id: str
    recibida_en: datetime


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
