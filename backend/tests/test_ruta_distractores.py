"""Prueba 11: la ruta de distractores vista desde fuera (RF-11, EC-08, ADR-0013).

Complementa a `test_distractores.py` sin repetirla. Allí se verifica la regla; aquí, que la ruta
la aplique, que devuelva lo descartado con su motivo y que se degrade con un 503 que no arrastra
al resto de la API. El proveedor se sustituye con `dependency_overrides`, así que ninguna prueba
sale a la red ni necesita una clave."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from api.main import app, obtener_generador
from autoria import DistractorPropuesto, ProveedorNoDisponible
from tests.test_distractores import GeneradorFalso

SOLICITUD = {"enunciado": "Derivada de x·sin(x)", "respuesta_correcta": "sin(x) + x·cos(x)"}


@pytest.fixture
def cliente() -> Iterator[TestClient]:
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_devuelve_las_propuestas_y_lo_descartado_con_su_motivo(cliente: TestClient) -> None:
    app.dependency_overrides[obtener_generador] = lambda: GeneradorFalso([
        DistractorPropuesto("cos(x)", "Se omitió la regla del producto"),
        DistractorPropuesto("sin(x)+x*cos(x)", "Ninguno"),
    ])

    respuesta = cliente.post("/distractores", json=SOLICITUD)

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["distractores"] == [
        {"expresion": "cos(x)", "error": "Se omitió la regla del producto"}
    ]
    assert cuerpo["descartados"][0]["expresion"] == "sin(x)+x*cos(x)"
    assert "respuesta correcta" in cuerpo["descartados"][0]["motivo"]


def test_sin_proveedor_configurado_responde_503_y_la_api_sigue_viva(
    cliente: TestClient,
) -> None:
    app.dependency_overrides[obtener_generador] = lambda: None

    respuesta = cliente.post("/distractores", json=SOLICITUD)

    assert respuesta.status_code == 503
    assert "no está configurado" in respuesta.json()["detail"]
    assert cliente.get("/health").status_code == 200


def test_si_el_proveedor_falla_responde_503_con_el_motivo(cliente: TestClient) -> None:
    app.dependency_overrides[obtener_generador] = lambda: GeneradorFalso(
        falla=ProveedorNoDisponible("Se agotó la cuota gratuita del proveedor por ahora.")
    )

    respuesta = cliente.post("/distractores", json=SOLICITUD)

    assert respuesta.status_code == 503
    assert respuesta.json() == {"detail": "Se agotó la cuota gratuita del proveedor por ahora."}


@pytest.mark.parametrize(
    "solicitud",
    [
        {"enunciado": "", "respuesta_correcta": "2x"},
        {"enunciado": "Derivada de x²", "respuesta_correcta": "2x", "cantidad": 0},
        {"enunciado": "Derivada de x²", "respuesta_correcta": "2x", "cantidad": 6},
        {"enunciado": "Derivada de x²"},
    ],
)
def test_una_solicitud_mal_formada_no_llega_al_proveedor(
    cliente: TestClient, solicitud: dict
) -> None:
    generador = GeneradorFalso([])
    app.dependency_overrides[obtener_generador] = lambda: generador

    respuesta = cliente.post("/distractores", json=solicitud)

    assert respuesta.status_code == 422
    assert generador.preguntas == []
