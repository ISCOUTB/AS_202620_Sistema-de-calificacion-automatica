import os
from collections.abc import Iterator

import pytest
import redis

from infraestructura.cola import cliente_redis
from tests.sesion_de_prueba import DOCENTE_DE_PRUEBA, RegistroDondeTodoEsDelDocente


@pytest.fixture(autouse=True)
def docente_con_sesion() -> Iterator[None]:
    """Las pruebas de las rutas hablan con la API como un docente que ya entró (ADR-0025). La
    sesión en sí se prueba en `test_sesion.py`, que quita esta sustitución.

    Y con un registro de exámenes donde todo examen es de ese docente (ADR-0028): las pruebas que
    tratan del dueño ponen el suyo encima."""
    from api.main import app, docente_de_la_sesion, obtener_registro_de_examenes

    registro = RegistroDondeTodoEsDelDocente()
    app.dependency_overrides[docente_de_la_sesion] = lambda: DOCENTE_DE_PRUEBA
    app.dependency_overrides[obtener_registro_de_examenes] = lambda: registro
    yield
    app.dependency_overrides.pop(docente_de_la_sesion, None)
    app.dependency_overrides.pop(obtener_registro_de_examenes, None)


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
