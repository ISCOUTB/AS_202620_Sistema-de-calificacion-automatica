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


def _imports_reales(nombre_modulo: str) -> list[tuple[str, int, str]]:
    """Recorre cada .py del paquete y devuelve (archivo_relativo, línea, módulo_importado)
    para cada import absoluto que apunte a otro de los siete módulos del dominio."""
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
                if importado in MODULOS and importado != nombre_modulo:
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
