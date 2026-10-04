import os

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
ALLOWED_ORIGIN = os.environ.get("ALLOWED_ORIGIN", "http://localhost:8080")

# Raíz del almacén de hojas escaneadas. En Docker apunta al volumen `almacen_imagenes`, que el
# compose monta en `api` y en `worker` para que ambos vean el mismo archivo. Fuera de Docker
# cae en un directorio local, que es lo que sirve para `uvicorn --reload` durante desarrollo.
RUTA_ALMACEN = os.environ.get("RUTA_ALMACEN", "almacen_imagenes")

# Nombre de la cola de trabajos. Debe coincidir con el que consume `worker/main.py`, que lo lee
# de la misma variable de entorno y con el mismo valor por omisión.
NOMBRE_COLA = os.environ.get("NOMBRE_COLA", "procesamiento")

# Bitácora de recepción (ADR-0006). Vive junto al almacén, en el mismo volumen, porque las dos
# cosas que relaciona son el archivo guardado y el trabajo encolado: separarlas de volumen
# permitiría que sobreviva una sin la otra, que es exactamente lo que la bitácora evita.
RUTA_BITACORA = os.environ.get(
    "RUTA_BITACORA", os.path.join(RUTA_ALMACEN, "bitacora-de-recepcion.jsonl")
)

# Proveedor de LLM que propone distractores diagnósticos (RF-11, ADR-0013). Habla el protocolo de
# chat de OpenAI, así que cambiar de proveedor es cambiar estas tres variables y no el código. Sin
# clave, la ruta de distractores responde 503 y el resto de la API funciona igual, porque RF-11 es
# opcional (ADR-0005). La clave nunca va en el repositorio (RNF-11): llega por el entorno.
LLM_URL_BASE = os.environ.get("LLM_URL_BASE", "https://api.groq.com/openai/v1")
LLM_MODELO = os.environ.get("LLM_MODELO", "openai/gpt-oss-120b")
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
