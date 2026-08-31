"""Almacenamiento de las hojas escaneadas, detrás de un puerto.

**Por qué hay un puerto y no una función que escribe en disco.** El riesgo R-06 del arc42 está
abierto: no hay decisión de persistencia ni de almacenamiento de imágenes. El corte vertical
A-01 necesita guardar archivos hoy, y tomar esa decisión de paso, sin ADR, sería cerrarla por
la puerta de atrás.

El arc42 §4 ya resolvió cómo salir de esto: el aislamiento hexagonal no se aplica en los siete
módulos, sino **selectivamente en los dos puntos donde la matriz de estilos muestra que
compensa**, y el almacén de imágenes es uno de esos dos. Así que `AlmacenDeImagenes` es el
puerto —lo único que `ingesta` conoce— y `AlmacenEnDisco` es un adaptador **provisional**.

Cuando se escriba el ADR de persistencia, lo que cambia es esta clase o la que la reemplace.
`ingesta`, el modelo y las pruebas del aspecto no se tocan. La política de retención que exige
RNF-14 también aterriza aquí, y todavía no está implementada: hoy nada borra lo que se guarda.
"""

import re
import unicodedata
import uuid
from pathlib import Path
from typing import Protocol

__all__ = ["AlmacenDeImagenes", "AlmacenEnDisco", "nombre_seguro"]

_CARACTERES_PERMITIDOS = re.compile(r"[^A-Za-z0-9._-]")


def nombre_seguro(nombre: str) -> str:
    """Reduce un nombre de archivo a algo que no pueda escapar del directorio del examen.

    Se queda con el último segmento (descarta `../..` y rutas absolutas de Windows o POSIX),
    quita los acentos y reemplaza todo lo que no sea alfanumérico, punto, guion o guion bajo.
    El nombre original no se pierde: viaja en `HojaAceptada.nombre_archivo`, que es lo que se le
    muestra al docente.

    Las dos defensas son redundantes a propósito: la lista blanca sola ya neutraliza `/` y `\\`,
    y quedarse con el último segmento sola también. Se conservan ambas porque el costo es nulo
    y porque una de las dos podría relajarse en el futuro (por ejemplo, admitir acentos) sin
    que la otra deje de proteger."""
    ultimo = re.split(r"[\\/]", nombre)[-1]
    sin_acentos = unicodedata.normalize("NFKD", ultimo).encode("ascii", "ignore").decode()
    limpio = _CARACTERES_PERMITIDOS.sub("_", sin_acentos).lstrip(".")
    return limpio or "archivo"


class AlmacenDeImagenes(Protocol):
    """El puerto. `ingesta` depende de esta forma, no de una implementación concreta."""

    def guardar(self, examen_id: str, nombre_archivo: str, contenido: bytes) -> str:
        """Persiste el contenido y devuelve una referencia opaca para recuperarlo después.

        Quien la recibe no debe interpretarla como una ruta: el adaptador que venga puede
        devolver una clave de objeto o un identificador de fila."""
        ...


class AlmacenEnDisco:
    """Adaptador provisional sobre el sistema de archivos.

    Escribe en el volumen `almacen_imagenes` que el `docker-compose.yml` monta en `api` y
    `worker`, de modo que el archivo que la API guarda es el mismo que el worker leerá. Cada
    hoja recibe un nombre único con UUID para que dos escaneos homónimos no se pisen; el
    nombre original se conserva como sufijo, únicamente para que el directorio sea legible
    cuando alguien lo inspecciona a mano."""

    def __init__(self, raiz: Path) -> None:
        self.raiz = Path(raiz)

    def guardar(self, examen_id: str, nombre_archivo: str, contenido: bytes) -> str:
        directorio = self.raiz / nombre_seguro(examen_id)
        directorio.mkdir(parents=True, exist_ok=True)

        nombre_en_disco = f"{uuid.uuid4()}-{nombre_seguro(nombre_archivo)}"
        (directorio / nombre_en_disco).write_bytes(contenido)

        return f"{nombre_seguro(examen_id)}/{nombre_en_disco}"
