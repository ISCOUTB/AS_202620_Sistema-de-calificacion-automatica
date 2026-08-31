import os

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
ALLOWED_ORIGIN = os.environ.get("ALLOWED_ORIGIN", "http://localhost:8080")

# Raíz del almacén de hojas escaneadas. En Docker apunta al volumen `almacen_imagenes`, que el
# compose monta en `api` y en `worker` para que ambos vean el mismo archivo. Fuera de Docker
# cae en un directorio local, que es lo que sirve para `uvicorn --reload` durante desarrollo.
RUTA_ALMACEN = os.environ.get("RUTA_ALMACEN", "almacen_imagenes")

# Nombre de la cola de trabajos. Debe coincidir con el que consume `worker/main.py`.
NOMBRE_COLA = os.environ.get("NOMBRE_COLA", "procesamiento")
