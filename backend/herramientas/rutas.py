"""Las rutas y la URL que las herramientas de medición reciben por la línea de comandos.

Son herramientas que un agente de IA podría invocar con argumentos manipulados (SonarCloud,
S8707 y S8703): con una ruta libre podrían leer o pisar cualquier archivo, y con una URL libre,
hacer peticiones a cualquier servidor. Por eso un archivo solo se lee o se escribe dentro del
repositorio, como en `seguir_trabajo.py` (S12); lo que esté en otra parte entra por la entrada
estándar o sale por la salida estándar. Y la URL solo puede apuntar al sistema en local o a la
API del servidor del laboratorio.
"""

import os
from pathlib import Path
from urllib.parse import urlsplit

CARPETA_DEL_REPOSITORIO = Path(__file__).resolve().parent.parent.parent

# La API en local (`docker compose` o `repetir-local.sh`, en el puerto que sea) y la del servidor
# del laboratorio (deploy/compose.lab.yaml). Si la API cambia de dirección, se cambia aquí.
HOSTS_PERMITIDOS = frozenset({"localhost", "127.0.0.1", "api-calificacion.iscoutb.dev"})


def ruta_en_el_repositorio(nombre: str, opcion: str) -> str:
    """La ruta canónica de `nombre`, si está dentro del repositorio. Se resuelve la ruta (con `..`
    y enlaces incluidos) y se comprueba que siga dentro, con el separador al final para que una
    carpeta hermana con el mismo prefijo no pase la comprobación."""
    base = os.path.realpath(CARPETA_DEL_REPOSITORIO)
    ruta = os.path.realpath(nombre)
    if not ruta.startswith(base + os.sep):
        raise SystemExit(
            f"{opcion} tiene que estar dentro del repositorio: {nombre!r}. Si está en otra "
            "parte, usa la entrada o la salida estándar"
        )
    return ruta


def url_de_la_api(url: str) -> str:
    """`url`, si es http o https y su host es uno de `HOSTS_PERMITIDOS`. Se compara el host ya
    separado, no el texto: `http://localhost.otro.com` o `http://otro.com/?localhost` empiezan o
    contienen un host permitido y no lo son."""
    partes = urlsplit(url)
    if partes.hostname not in HOSTS_PERMITIDOS:
        raise SystemExit(
            f"--url tiene que apuntar a la API en local o en el servidor del laboratorio "
            f"({', '.join(sorted(HOSTS_PERMITIDOS))}): {url!r}"
        )
    if partes.scheme not in ("http", "https"):
        raise SystemExit(f"--url tiene que empezar por http:// o https://: {url!r}")
    return url
