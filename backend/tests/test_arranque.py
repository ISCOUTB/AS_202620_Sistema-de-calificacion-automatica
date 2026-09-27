"""Prueba 1 (la de más peso para RNF-07): la aplicación FastAPI se importa sin error y su
endpoint de salud responde 200."""

from fastapi.testclient import TestClient

from api.main import app


def test_endpoint_de_salud_responde_200():
    cliente = TestClient(app)

    respuesta = cliente.get("/health")

    assert respuesta.status_code == 200
    assert respuesta.json() == {"status": "ok"}


def test_endpoint_de_salud_responde_200_a_head():
    """El monitor externo que mantiene despierta la API desplegada (ADR-0009) la consulta con
    `HEAD`. Sin la ruta para ese método, la respuesta era 405 y el monitor la daba por caída."""
    cliente = TestClient(app)

    respuesta = cliente.head("/health")

    assert respuesta.status_code == 200
