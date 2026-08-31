import os

import pytest
import redis

from infraestructura.cola import cliente_redis


@pytest.fixture
def cliente() -> redis.Redis:
    """Cliente Redis para la prueba de encolado. Si no hay un Redis real disponible
    (por ejemplo, no se levantó `docker compose up -d redis`), la prueba se salta con un
    mensaje claro en vez de fallar de forma confusa."""
    url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    cliente = cliente_redis(url)
    try:
        cliente.ping()
    except redis.ConnectionError:
        pytest.skip(
            f"No se pudo conectar a Redis en {url}. "
            "Levanta 'docker compose up -d redis' antes de correr esta prueba."
        )
    yield cliente
    cliente.close()
