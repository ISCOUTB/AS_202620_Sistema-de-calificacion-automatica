import os
from collections.abc import Iterator

import pytest
import redis

from infraestructura.cola import cliente_redis


@pytest.fixture
def cliente() -> Iterator[redis.Redis]:
    """Cliente Redis para la prueba de encolado. Si no hay un Redis real disponible
    (por ejemplo, no se levantó `docker compose up -d redis`), la prueba se salta con un
    mensaje claro en vez de fallar de forma confusa."""
    url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    cliente = cliente_redis(url)
    try:
        cliente.ping()
    # Las dos formas en que falta Redis. Con la espera de conexión de ADR-0016, en Windows un
    # `localhost` sin servidor no rechaza la conexión sino que la deja vencer, y eso es
    # `TimeoutError`, que no hereda de `ConnectionError`: sin atraparlo, la prueba terminaba en
    # error de preparación en vez de omitirse con este mensaje.
    except (redis.ConnectionError, redis.TimeoutError):
        pytest.skip(
            f"No se pudo conectar a Redis en {url}. "
            "Levanta 'docker compose up -d redis' antes de correr esta prueba."
        )
    yield cliente
    cliente.close()
