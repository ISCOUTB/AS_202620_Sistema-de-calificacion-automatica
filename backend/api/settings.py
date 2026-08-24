import os

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
ALLOWED_ORIGIN = os.environ.get("ALLOWED_ORIGIN", "http://localhost:8080")
