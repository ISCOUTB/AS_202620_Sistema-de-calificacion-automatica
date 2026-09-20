"""Exporta el contrato OpenAPI de la API a un archivo versionado del repositorio.

Por que el contrato se versiona en vez de consultarse en caliente
-----------------------------------------------------------------
`/openapi.json` solo existe mientras la API esta levantada, y describe la version que este
corriendo en ese momento. Un consumidor que quiera generar su cliente, o un revisor que quiera
ver que prometia la API en un commit dado, no pueden levantarla: necesitan el documento dentro
del repositorio, con su historia de git.

Versionarlo tambien es lo que hace posible la prueba de contrato. Con el documento guardado, un
cambio incompatible deja de ser invisible: aparece como un diff en este archivo, y la prueba
puede comparar lo que la aplicacion genera hoy contra lo que el repositorio tiene acordado.

Como se regenera
----------------
Desde `backend/`, con el entorno del proyecto:

    python -m herramientas.exportar_contrato

Escribe `docs/contrato/openapi.json`. Si el diff sale vacio, el contrato no cambio. Si sale con
cambios, hay que mirarlos uno por uno antes de commitear: un campo que desaparece o un tipo que
se estrecha rompen a quien ya consume la API.

Determinismo
------------
Las claves se escriben ordenadas y la indentacion es fija, para que dos exportaciones del mismo
codigo den el mismo byte. Sin eso, un reordenamiento interno de FastAPI produciria un diff que
no corresponde a ningun cambio del contrato, y el equipo aprenderia a ignorar los diffs de este
archivo, que es justo lo que no puede pasar.
"""

import json
from pathlib import Path

from api.main import app

RAIZ_REPOSITORIO = Path(__file__).resolve().parent.parent.parent
RUTA_CONTRATO = RAIZ_REPOSITORIO / "docs" / "contrato" / "openapi.json"


def documento_openapi() -> dict:
    """Genera el documento OpenAPI tal como lo publicaria la API en `/openapi.json`."""
    return app.openapi()


def serializar(documento: dict) -> str:
    """Convierte el documento a texto estable: claves ordenadas, indentacion fija, salto final.

    `ensure_ascii=False` deja las tildes legibles en el archivo, que es un documento que se lee
    en la revision y no solo un artefacto de maquina.
    """
    return json.dumps(documento, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def exportar() -> Path:
    RUTA_CONTRATO.parent.mkdir(parents=True, exist_ok=True)
    RUTA_CONTRATO.write_text(serializar(documento_openapi()), encoding="utf-8")
    return RUTA_CONTRATO


if __name__ == "__main__":
    ruta = exportar()
    documento = documento_openapi()
    print(f"Contrato escrito en {ruta.relative_to(RAIZ_REPOSITORIO)}")
    print(f"  version : {documento['info']['version']}")
    print(f"  rutas   : {len(documento['paths'])}")
    print(f"  esquemas: {len(documento['components']['schemas'])}")
