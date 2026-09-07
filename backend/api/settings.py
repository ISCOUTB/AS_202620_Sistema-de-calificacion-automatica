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
