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

import hashlib
import re
import unicodedata
import uuid
from pathlib import Path
from typing import Protocol

__all__ = ["AlmacenDeImagenes", "AlmacenEnDisco", "directorio_del_examen", "nombre_seguro"]

_CARACTERES_PERMITIDOS = re.compile(r"[^A-Za-z0-9._-]")

# Casi todos los sistemas de archivos admiten 255 bytes por componente de la ruta. El nombre en
# disco le suma al nombre limpio un UUID de 36 caracteres y un guion, y el directorio del examen
# un guion y 8 caracteres de resumen: con 100 queda holgura de sobra. El nombre limpio es ASCII,
# así que caracteres y bytes coinciden.
LARGO_MAXIMO_DEL_NOMBRE = 100
_LARGO_MAXIMO_DE_LA_EXTENSION = 10


def nombre_seguro(nombre: str, largo_maximo: int = LARGO_MAXIMO_DEL_NOMBRE) -> str:
    """Reduce un nombre de archivo a algo que no pueda escapar del directorio del examen.

    Se queda con el último segmento (descarta `../..` y rutas absolutas de Windows o POSIX),
    quita los acentos y reemplaza todo lo que no sea alfanumérico, punto, guion o guion bajo.
    El nombre original no se pierde: viaja en `HojaAceptada.nombre_archivo`, que es lo que se le
    muestra al docente.

    Las dos defensas son redundantes a propósito: la lista blanca sola ya neutraliza `/` y `\\`,
    y quedarse con el último segmento sola también. Se conservan ambas porque el costo es nulo
    y porque una de las dos podría relajarse en el futuro (por ejemplo, admitir acentos) sin
    que la otra deje de proteger.

    **Y lo acorta a `largo_maximo`, conservando la extensión.** Sin el recorte, un nombre de más
    de unos 218 caracteres pasaba de 255 bytes con el UUID delante, y escribirlo fallaba con un
    error del sistema operativo."""
    ultimo = re.split(r"[\\/]", nombre)[-1]
    sin_acentos = unicodedata.normalize("NFKD", ultimo).encode("ascii", "ignore").decode()
    limpio = _CARACTERES_PERMITIDOS.sub("_", sin_acentos).lstrip(".") or "archivo"
    if len(limpio) <= largo_maximo:
        return limpio
    raiz, punto, extension = limpio.rpartition(".")
    if punto and raiz and len(extension) <= _LARGO_MAXIMO_DE_LA_EXTENSION:
        return f"{raiz[: largo_maximo - len(extension) - 1]}.{extension}"
    return limpio[:largo_maximo]


def directorio_del_examen(examen_id: str) -> str:
    """El nombre del directorio de un examen, que no comparte con ningún otro examen.

    Limpiar el identificador con `nombre_seguro` puede llevar dos exámenes distintos al mismo
    nombre: «Cálculo 1» y «Calculo_1» quedan los dos en `Calculo_1`, y `..` queda en `archivo`.
    Sus hojas se mezclarían en un directorio, y una retención por examen (RNF-14) borraría las del
    otro. Por eso, si limpiar cambió algo, se suma un resumen del identificador original. Un
    identificador que ya estaba limpio, como `CALC-2026-01`, conserva su directorio de siempre."""
    limpio = nombre_seguro(examen_id)
    if limpio == examen_id:
        return limpio
    resumen = hashlib.sha256(examen_id.encode("utf-8")).hexdigest()[:8]
    return f"{limpio}-{resumen}"


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
        carpeta = directorio_del_examen(examen_id)
        directorio = self.raiz / carpeta
        directorio.mkdir(parents=True, exist_ok=True)

        nombre_en_disco = f"{uuid.uuid4()}-{nombre_seguro(nombre_archivo)}"
        (directorio / nombre_en_disco).write_bytes(contenido)

        return f"{carpeta}/{nombre_en_disco}"
