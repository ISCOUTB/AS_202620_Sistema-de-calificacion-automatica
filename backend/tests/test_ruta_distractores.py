"""Prueba 11: la ruta de distractores vista desde fuera (RF-11, EC-08, ADR-0013).

Complementa a `test_distractores.py` sin repetirla. Allí se verifica la regla; aquí, que la ruta
la aplique, que devuelva lo descartado con su motivo y que se degrade con un 503 que no arrastra
al resto de la API. El proveedor se sustituye con `dependency_overrides`, así que ninguna prueba
sale a la red ni necesita una clave.

Desde el segundo corte también comprueba el presupuesto visto desde fuera (EC-09, ADR-0015): el
429 con `Retry-After`, que la solicitud cortada no llega al proveedor, y `GET /metricas`. Cada
prueba recibe un presupuesto nuevo, para que ninguna gaste el cupo de la siguiente."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from api.main import app, obtener_generador, obtener_presupuesto
from api.settings import ALLOWED_ORIGIN
from autoria import DistractorPropuesto, PresupuestoDeSolicitudes, ProveedorNoDisponible
from tests.test_distractores import GeneradorFalso

SOLICITUD = {"enunciado": "Derivada de x·sin(x)", "respuesta_correcta": "sin(x) + x·cos(x)"}


@pytest.fixture
def cliente() -> Iterator[TestClient]:
    app.dependency_overrides[obtener_presupuesto] = lambda: PresupuestoDeSolicitudes()
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


def _con_presupuesto(por_minuto: int) -> PresupuestoDeSolicitudes:
    presupuesto = PresupuestoDeSolicitudes(por_minuto=por_minuto, por_dia=150)
    app.dependency_overrides[obtener_presupuesto] = lambda: presupuesto
    return presupuesto


def test_la_solicitud_sin_cupo_responde_429_sin_llegar_al_proveedor(cliente: TestClient) -> None:
    """La medida del escenario: lo que no cabe en el presupuesto no sale a la red. Con dos de
    cupo, una ráfaga de cinco deja dos en el proveedor y tres en 429."""
    _con_presupuesto(por_minuto=2)
    generador = GeneradorFalso([DistractorPropuesto("x", "Se bajó el exponente sin multiplicar")])
    app.dependency_overrides[obtener_generador] = lambda: generador

    codigos = [cliente.post("/distractores", json=SOLICITUD).status_code for _ in range(5)]

    assert codigos == [200, 200, 429, 429, 429]
    assert len(generador.preguntas) == 2


def test_el_429_dice_cuando_volver_a_pedirlo(cliente: TestClient) -> None:
    _con_presupuesto(por_minuto=1)
    app.dependency_overrides[obtener_generador] = lambda: GeneradorFalso([])
    cliente.post("/distractores", json=SOLICITUD)

    respuesta = cliente.post("/distractores", json=SOLICITUD)

    assert respuesta.status_code == 429
    assert 1 <= int(respuesta.headers["retry-after"]) <= 60
    assert "por minuto" in respuesta.json()["detail"]
    assert cliente.get("/health").status_code == 200


def test_el_sitio_puede_leer_cuanto_esperar_despues_del_429(cliente: TestClient) -> None:
    """El sitio es otro origen: el navegador le entrega la respuesta, pero solo le deja leer las
    cabeceras que CORS expone, y `Retry-After` no está entre las de por omisión. Se pide con el
    `Origin` del sitio, como lo hace el navegador."""
    _con_presupuesto(por_minuto=1)
    app.dependency_overrides[obtener_generador] = lambda: GeneradorFalso([])
    cliente.post("/distractores", json=SOLICITUD, headers={"Origin": ALLOWED_ORIGIN})

    respuesta = cliente.post("/distractores", json=SOLICITUD, headers={"Origin": ALLOWED_ORIGIN})

    assert respuesta.status_code == 429
    assert respuesta.headers["access-control-allow-origin"] == ALLOWED_ORIGIN
    expuestas = respuesta.headers["access-control-expose-headers"].lower().split(",")
    assert "retry-after" in [cabecera.strip() for cabecera in expuestas]


def test_sin_proveedor_configurado_no_se_gasta_cupo(cliente: TestClient) -> None:
    """El 503 de «no configurado» sale antes de reservar: un entorno sin clave no se queda sin
    presupuesto el día que se configure."""
    presupuesto = _con_presupuesto(por_minuto=1)
    app.dependency_overrides[obtener_generador] = lambda: None

    for _ in range(3):
        assert cliente.post("/distractores", json=SOLICITUD).status_code == 503

    assert presupuesto.estado().enviadas_desde_el_arranque == 0


def test_las_metricas_publican_lo_usado_y_lo_cortado(cliente: TestClient) -> None:
    _con_presupuesto(por_minuto=1)
    app.dependency_overrides[obtener_generador] = lambda: GeneradorFalso([])
    cliente.post("/distractores", json=SOLICITUD)
    cliente.post("/distractores", json=SOLICITUD)

    respuesta = cliente.get("/metricas")

    assert respuesta.status_code == 200
    presupuesto = respuesta.json()["presupuesto_de_distractores"]
    assert presupuesto["limite_por_minuto"] == 1
    assert presupuesto["usadas_en_el_ultimo_minuto"] == 1
    assert presupuesto["enviadas_desde_el_arranque"] == 1
    assert presupuesto["rechazadas_desde_el_arranque"] == 1


def test_la_misma_solicitud_dos_veces_no_deja_estado_y_gasta_su_propio_cupo(
    cliente: TestClient,
) -> None:
    """Responde dos veces, en la integración con el proveedor (S11, MF-09): si el profesor pide lo
    mismo dos veces, o el navegador reenvía, cada una es una propuesta completa e independiente.
    La ruta no guarda nada entre solicitudes, así que no hay un estado que pueda quedar a medias
    ni duplicado: lo único que cuesta la repetida es su cupo, y el presupuesto lo cuenta."""
    presupuesto = _con_presupuesto(por_minuto=6)
    generador = GeneradorFalso([DistractorPropuesto("x", "Se bajó el exponente sin multiplicar")])
    app.dependency_overrides[obtener_generador] = lambda: generador

    primera = cliente.post("/distractores", json=SOLICITUD)
    segunda = cliente.post("/distractores", json=SOLICITUD)

    assert primera.status_code == segunda.status_code == 200
    assert primera.json() == segunda.json()
    assert len(generador.preguntas) == 2
    assert presupuesto.estado().enviadas_desde_el_arranque == 2
