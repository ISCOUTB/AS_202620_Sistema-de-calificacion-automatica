"""Las rutas y la URL que las herramientas de medición reciben por la línea de comandos.

Son herramientas que un agente de IA podría invocar con argumentos manipulados (SonarCloud,
S8707 y S8703): con una ruta libre podrían leer o pisar cualquier archivo, y con una URL libre,
hacer peticiones a cualquier servidor. Por eso un archivo solo se lee o se escribe dentro del
repositorio, como en `seguir_trabajo.py` (S12); lo que esté en otra parte entra por la entrada
estándar o sale por la salida estándar. Y la URL sale de una lista fija: la API en local o la del
servidor del laboratorio.
"""

import os
from pathlib import Path

CARPETA_DEL_REPOSITORIO = Path(__file__).resolve().parent.parent.parent

# La API en local (`docker compose` en el 8000; `repetir-local.sh` y la medición de
# medicion-lectura-omr.md en el 8010) y la del servidor del laboratorio (deploy/compose.lab.yaml).
# Si la API cambia de dirección, o `repetir-local.sh` corre con otro PUERTO_API, se agrega aquí.
APIS_PERMITIDAS = (
    "http://localhost:8000",
    "http://localhost:8010",
    "http://127.0.0.1:8000",
    "http://127.0.0.1:8010",
    "https://api-calificacion.iscoutb.dev",
)


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
    """La dirección de `APIS_PERMITIDAS` igual a `url`. Devuelve la de la lista y no `url`, como
    `_url_del_destino` en `medir_arranque_en_frio.py`: así ningún argumento decide a qué servidor
    se le hacen las peticiones, aunque pase la comprobación. Y se compara la dirección entera:
    `http://localhost:8000.otro.example` empieza con una permitida y no lo es."""
    pedida = url.rstrip("/")
    for permitida in APIS_PERMITIDAS:
        if pedida == permitida:
            return permitida
    raise SystemExit(
        f"--url tiene que ser la API en local o la del servidor del laboratorio "
        f"({', '.join(APIS_PERMITIDAS)}): {url!r}"
    )
