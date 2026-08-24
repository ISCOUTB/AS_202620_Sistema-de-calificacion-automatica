"""Prueba 1 (la de más peso para RNF-07): la aplicación FastAPI se importa sin error y su
endpoint de salud responde 200."""

from fastapi.testclient import TestClient

from api.main import app


def test_endpoint_de_salud_responde_200():
    cliente = TestClient(app)

    respuesta = cliente.get("/health")

    assert respuesta.status_code == 200
    assert respuesta.json() == {"status": "ok"}
