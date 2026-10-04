"""Prueba 3 (la más importante): recorre las importaciones reales de cada módulo y falla si
alguno importa otro que su propio docstring no declara permitido. Convierte el riesgo R-08 del
arc42 (que el proyecto se degrade a un paquete plano) en algo que el CI detecta, en vez de algo
que depende de la disciplina del equipo.

El docstring de cada `__init__.py` es la fuente de verdad: su línea `Importa:` declara el
conjunto de los otros módulos que puede importar (ver ADR-0002 y ADR-0003)."""

import ast
import re
from pathlib import Path

import pytest

RAIZ_BACKEND = Path(__file__).resolve().parent.parent

MODULOS = [
    "autoria",
    "ingesta",
    "omr",
    "calificacion",
    "dashboard",
    "identidad",
    "infraestructura",
]

# Los puntos de entrada: traducen HTTP y la cola a llamadas de dominio, y por eso importan a los
# módulos. Al revés no puede pasar: un módulo de dominio que importe `api` o `worker` queda atado
# a la puerta por la que entra la petición. La prueba de abajo solo miraba los siete módulos, así
# que un `from api.settings import ...` dentro de `autoria` pasaba sin que nada fallara. Es el
# flanco de V-1 (arc42 §8.3) visto desde el dominio.
PUNTOS_DE_ENTRADA = ["api", "worker"]


def _importados_permitidos(nombre_modulo: str) -> set[str]:
    """Lee la línea 'Importa:' del docstring de <modulo>/__init__.py."""
    ruta_init = RAIZ_BACKEND / nombre_modulo / "__init__.py"
    arbol = ast.parse(ruta_init.read_text(encoding="utf-8"))
    docstring = ast.get_docstring(arbol) or ""

    coincidencia = re.search(r"^Importa:\s*(.+)$", docstring, re.MULTILINE)
    if not coincidencia:
        raise AssertionError(
            f"El docstring de {ruta_init} no declara una línea 'Importa:'. "
            "Es la fuente de verdad de la prueba de fronteras; sin ella no se puede verificar "
            f"qué puede importar '{nombre_modulo}'."
        )

    valor = coincidencia.group(1).strip()
    if valor == "ninguno":
        return set()
    return {m.strip() for m in valor.split(",")}


def _imports_reales(
    nombre_modulo: str, destinos: list[str] = MODULOS
) -> list[tuple[str, int, str]]:
    """Recorre cada .py del paquete y devuelve (archivo_relativo, línea, módulo_importado)
    para cada import absoluto que apunte a uno de `destinos`: por omisión, los otros seis
    módulos del dominio."""
    violaciones_candidatas = []
    directorio_modulo = RAIZ_BACKEND / nombre_modulo

    for archivo in directorio_modulo.rglob("*.py"):
        arbol = ast.parse(archivo.read_text(encoding="utf-8"))
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.Import):
                nombres_importados = [alias.name.split(".")[0] for alias in nodo.names]
            elif isinstance(nodo, ast.ImportFrom) and nodo.level == 0 and nodo.module:
                nombres_importados = [nodo.module.split(".")[0]]
            else:
                continue

            for importado in nombres_importados:
                if importado in destinos and importado != nombre_modulo:
                    violaciones_candidatas.append(
                        (str(archivo.relative_to(RAIZ_BACKEND)), nodo.lineno, importado)
                    )

    return violaciones_candidatas


@pytest.mark.parametrize("nombre_modulo", MODULOS)
def test_modulo_no_importa_fuera_de_lo_declarado(nombre_modulo):
    permitidos = _importados_permitidos(nombre_modulo)
    reales = _imports_reales(nombre_modulo)

    no_declarados = [
        (archivo, linea, importado)
        for archivo, linea, importado in reales
        if importado not in permitidos
    ]

    if no_declarados:
        detalle = "\n".join(
            f"  - {archivo}:{linea} importa '{importado}'"
            for archivo, linea, importado in no_declarados
        )
        declarados_txt = ", ".join(sorted(permitidos)) or "ninguno"
        raise AssertionError(
            f"El módulo '{nombre_modulo}' importa módulos que su docstring no declara "
            f"permitidos (declarado en 'Importa:': {declarados_txt}):\n{detalle}\n"
            "Corrige el import, o si la frontera debe cambiar, actualiza primero el docstring "
            "con una razón explícita (ver docs/adr/0002-procesar-calificacion-de-forma-asincrona.md)."
        )


@pytest.mark.parametrize("nombre_modulo", MODULOS)
def test_ningun_modulo_del_dominio_importa_un_punto_de_entrada(nombre_modulo):
    """Se validó provocando la falla: con `from api.settings import LLM_MODELO` dentro de
    `autoria/proveedor_llm.py`, esta prueba se pone en rojo y la de arriba sigue en verde,
    porque `api` no es uno de los siete módulos que aquella recorre."""
    reales = _imports_reales(nombre_modulo, destinos=PUNTOS_DE_ENTRADA)

    if reales:
        detalle = "\n".join(
            f"  - {archivo}:{linea} importa '{importado}'" for archivo, linea, importado in reales
        )
        raise AssertionError(
            f"El módulo '{nombre_modulo}' importa un punto de entrada del sistema:\n{detalle}\n"
            "El dominio no puede depender de la puerta por la que entra la petición. Si necesita "
            "un dato de configuración, que se lo pase quien lo llama."
        )
