"""Prueba 6: el endpoint de carga (RF-01) visto desde fuera, como lo llama el frontend.

Complementa a `test_recepcion.py` sin repetirla. Allí se verifica la regla de negocio; aquí,
que la ruta exista con la forma acordada, que acepte varios archivos en una sola petición y que
el cuerpo de la respuesta le diga al docente qué entró y qué no.

Las dependencias del almacén y de la cola se sustituyen con `dependency_overrides`, que es la
razón por la que `api/main.py` las declara con `Depends` en lugar de construirlas al importar:
así esta prueba corre sin Redis y sin escribir en el volumen real."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.main import app, obtener_almacen, obtener_cliente_cola
from infraestructura.almacen import AlmacenEnDisco
from tests.test_recepcion import JPG, PDF, PNG, ColaFalsa


@pytest.fixture
def cliente(tmp_path) -> TestClient:
    cola = ColaFalsa()
    app.dependency_overrides[obtener_almacen] = lambda: AlmacenEnDisco(tmp_path)
    app.dependency_overrides[obtener_cliente_cola] = lambda: cola
    yield TestClient(app)
    app.dependency_overrides.clear()


def _archivo(nombre: str, contenido: bytes, tipo: str = "image/jpeg"):
    return ("archivos", (nombre, contenido, tipo))


def test_carga_individual_confirma_la_recepcion(cliente):
    respuesta = cliente.post(
        "/examenes/CALC-2026-01/hojas",
        files=[_archivo("hoja.jpg", JPG)],
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["examen_id"] == "CALC-2026-01"
    assert cuerpo["total_procesados"] == 1
    assert cuerpo["rechazados"] == []
    assert cuerpo["aceptadas"][0]["nombre_archivo"] == "hoja.jpg"
    assert cuerpo["aceptadas"][0]["trabajo_id"]


def test_carga_en_lote_reporta_aceptadas_y_rechazadas_por_separado(cliente):
    """Un lote mixto responde 200, no un error: la petición se atendió completa y el cuerpo
    dice archivo por archivo qué pasó. Devolver un error obligaría a reenviar todo el lote,
    que es justo lo que EC-07 quiere evitar."""
    respuesta = cliente.post(
        "/examenes/CALC-2026-01/hojas",
        files=[
            _archivo("h1.jpg", JPG),
            _archivo("h2.png", PNG, "image/png"),
            _archivo("h3.pdf", PDF, "application/pdf"),
            _archivo("apuntes.txt", b"texto plano", "text/plain"),
        ],
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["total_procesados"] == 4
    assert len(cuerpo["aceptadas"]) == 3
    assert len(cuerpo["rechazados"]) == 1
    assert cuerpo["rechazados"][0]["nombre_archivo"] == "apuntes.txt"
    assert cuerpo["rechazados"][0]["motivo"]


def test_la_hoja_cargada_queda_en_el_almacen(cliente, tmp_path):
    respuesta = cliente.post(
        "/examenes/CALC-2026-01/hojas",
        files=[_archivo("hoja.jpg", JPG)],
    )

    referencia = respuesta.json()["aceptadas"][0]["referencia"]
    assert (Path(tmp_path) / referencia).read_bytes() == JPG


def test_una_peticion_sin_archivos_es_un_error_de_la_peticion(cliente):
    """422 y no 200: un lote vacío no es un lote recibido, es una petición mal formada. La
    distinción importa para que el frontend no muestre «0 hojas recibidas» como si fuera un
    resultado normal."""
    respuesta = cliente.post("/examenes/CALC-2026-01/hojas", files=[])

    assert respuesta.status_code == 422
