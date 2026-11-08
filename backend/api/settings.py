import os

from autoria import SOLICITUDES_POR_DIA, SOLICITUDES_POR_MINUTO
from infraestructura.almacen import RUTA_ALMACEN_POR_OMISION
from infraestructura.claves import RUTA_CLAVES_POR_OMISION
from infraestructura.cola import REDIS_URL_POR_OMISION
from infraestructura.resultados import RUTA_RESULTADOS_POR_OMISION
from infraestructura.revisiones import RUTA_REVISIONES_POR_OMISION
from ingesta import HOJAS_POR_LOTE, MB_POR_DIA

# El valor por omisión viene de `infraestructura/cola.py`, el mismo que usa el worker.
REDIS_URL = os.environ.get("REDIS_URL", REDIS_URL_POR_OMISION)
ALLOWED_ORIGIN = os.environ.get("ALLOWED_ORIGIN", "http://localhost:8080")

# Raíz del almacén de hojas escaneadas. En Docker apunta al volumen `almacen_imagenes`, que el
# compose monta en `api` y en `worker` para que ambos vean el mismo archivo. Fuera de Docker
# cae en un directorio local, que es lo que sirve para `uvicorn --reload` durante desarrollo.
RUTA_ALMACEN = os.environ.get("RUTA_ALMACEN", RUTA_ALMACEN_POR_OMISION)

# Nombre de la cola de trabajos. Debe coincidir con el que consume `worker/main.py`, que lo lee
# de la misma variable de entorno y con el mismo valor por omisión.
NOMBRE_COLA = os.environ.get("NOMBRE_COLA", "procesamiento")

# Bitácora de recepción (ADR-0006). Vive junto al almacén, en el mismo volumen, porque las dos
# cosas que relaciona son el archivo guardado y el trabajo encolado: separarlas de volumen
# permitiría que sobreviva una sin la otra, que es exactamente lo que la bitácora evita.
RUTA_BITACORA = os.environ.get(
    "RUTA_BITACORA", os.path.join(RUTA_ALMACEN, "bitacora-de-recepcion.jsonl")
)

# Registro de resultados (ADR-0023): lo escribe el worker y la API lo lee para mostrar cómo quedó
# cada hoja. La misma variable y el mismo valor por omisión que en `worker/main.py`, o cada uno
# miraría un archivo distinto.
RUTA_RESULTADOS = os.environ.get("RUTA_RESULTADOS", RUTA_RESULTADOS_POR_OMISION)

# Claves de respuestas: el worker las lee para calificar, y la API, para ofrecer en la pantalla de
# carga los exámenes que tienen una. Misma variable y mismo valor por omisión que en el worker.
RUTA_CLAVES = os.environ.get("RUTA_CLAVES", RUTA_CLAVES_POR_OMISION)

# Lo que resuelve el profesor en las preguntas en revisión (RF-08). Solo la API lo escribe y lo lee.
RUTA_REVISIONES = os.environ.get("RUTA_REVISIONES", RUTA_REVISIONES_POR_OMISION)

# Proveedor de LLM que propone distractores diagnósticos (RF-11, ADR-0013). Habla el protocolo de
# chat de OpenAI, así que cambiar de proveedor es cambiar estas tres variables y no el código. Sin
# clave, la ruta de distractores responde 503 y el resto de la API funciona igual, porque RF-11 es
# opcional (ADR-0005). La clave nunca va en el repositorio (RNF-11): llega por el entorno.
LLM_URL_BASE = os.environ.get("LLM_URL_BASE", "https://api.groq.com/openai/v1")
LLM_MODELO = os.environ.get("LLM_MODELO", "openai/gpt-oss-120b")
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")

# Presupuesto de solicitudes al proveedor de LLM (escenario del segundo corte, EC-09, ADR-0015).
# Los valores por omisión no se repiten aquí: se leen de `autoria` (`presupuesto.py`), que es
# donde está su justificación, para no volver a tener dos declaraciones del mismo dato (la
# lección de V-2 con NOMBRE_COLA).
LLM_SOLICITUDES_POR_MINUTO = int(
    os.environ.get("LLM_SOLICITUDES_POR_MINUTO", SOLICITUDES_POR_MINUTO)
)
LLM_SOLICITUDES_POR_DIA = int(os.environ.get("LLM_SOLICITUDES_POR_DIA", SOLICITUDES_POR_DIA))

# Presupuesto de carga (S13, ADR-0022): hojas por lote y MB por día que admite la ruta de carga.
# Por la misma razón, los valores por omisión y su justificación están en `ingesta`
# (`presupuesto.py`).
CARGA_HOJAS_POR_LOTE = int(os.environ.get("CARGA_HOJAS_POR_LOTE", HOJAS_POR_LOTE))
CARGA_MB_POR_DIA = int(os.environ.get("CARGA_MB_POR_DIA", MB_POR_DIA))
