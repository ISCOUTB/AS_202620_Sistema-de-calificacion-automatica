"""Las rutas de la clave de un examen (A-04, ADR-0026): leerla, registrarla y habilitarla, con la
sesión del docente. La sesión la pone `conftest.py`; que sin ella respondan 401 lo prueba
`test_sesion.py`, que recorre todas las rutas."""

import logging
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from api.main import (
    app,
    obtener_catalogo_de_claves,
    obtener_lector_de_resultados,
    obtener_registro_de_claves,
)
from infraestructura.claves import ClavesEnDisco
from tests.sesion_de_prueba import DOCENTE_DE_PRUEBA

EXAMEN = "CALC-2026-03"


class ResultadosFalsos:
    def __init__(self) -> None:
        self.hechos: list[dict] = []

    def hechos_del_examen(self, examen_id: str) -> list[dict]:
        return [hecho for hecho in self.hechos if hecho["examen_id"] == examen_id]


@pytest.fixture
def resultados() -> ResultadosFalsos:
    return ResultadosFalsos()


@pytest.fixture
def claves(tmp_path) -> ClavesEnDisco:
    return ClavesEnDisco(tmp_path / "claves")


@pytest.fixture
def cliente(claves, resultados) -> Iterator[TestClient]:
    app.dependency_overrides[obtener_registro_de_claves] = lambda: claves
    app.dependency_overrides[obtener_catalogo_de_claves] = lambda: claves
    app.dependency_overrides[obtener_lector_de_resultados] = lambda: resultados
    yield TestClient(app)
    for dependencia in (obtener_registro_de_claves, obtener_catalogo_de_claves,
                        obtener_lector_de_resultados):
        app.dependency_overrides.pop(dependencia, None)


def _registrar(cliente, respuestas, examen=EXAMEN):
    return cliente.put(f"/examenes/{examen}/clave", json={"respuestas": respuestas})


def _crear(cliente, nombre="Cálculo 3") -> str:
    """Crea el examen como lo hace la aplicación desde ADR-0028 y devuelve su identificador."""
    respuesta = cliente.post("/examenes", json={"nombre": nombre})
    assert respuesta.status_code == 201
    return respuesta.json()["examen_id"]


def test_la_clave_registrada_se_lee_sin_habilitar_y_aparece_en_la_carga(cliente):
    examen = _crear(cliente)
    respuesta = _registrar(cliente, ["A", "B", "c"], examen)

    assert respuesta.status_code == 200
    clave = cliente.get(f"/examenes/{examen}/clave").json()
    assert clave == {
        "examen_id": examen,
        "respuestas": ["A", "B", "C"],
        "habilitada_por": None,
        "habilitada_en": None,
        "se_puede_cambiar": True,
    }
    assert respuesta.json() == clave
    assert cliente.get("/examenes").json()["examenes"] == [
        {"examen_id": examen, "nombre": "Cálculo 3", "habilitada": False}
    ]


def test_habilitarla_la_deja_a_nombre_del_docente_de_la_sesion(cliente):
    examen = _crear(cliente)
    _registrar(cliente, ["A", "B"], examen)

    respuesta = cliente.post(f"/examenes/{examen}/clave/habilitacion")

    assert respuesta.status_code == 200
    assert respuesta.json()["habilitada_por"] == DOCENTE_DE_PRUEBA
    assert respuesta.json()["habilitada_en"] is not None
    assert cliente.get("/examenes").json()["examenes"][0]["habilitada"] is True


def test_un_examen_sin_clave_responde_404(cliente):
    assert cliente.get(f"/examenes/{EXAMEN}/clave").status_code == 404
    assert cliente.post(f"/examenes/{EXAMEN}/clave/habilitacion").status_code == 404


@pytest.mark.parametrize(
    ("examen", "respuestas", "dice"),
    [
        (EXAMEN, ["A", "E"], "pregunta 2"),
        (EXAMEN, [], "al menos una"),
        (EXAMEN, ["A"] * 41, "41"),
        ("con espacio", ["A"], "identificador"),
    ],
    ids=["opcion-que-no-existe", "vacia", "demasiadas", "identificador"],
)
def test_una_clave_que_no_cabe_responde_422_con_el_motivo(
    cliente, claves, examen, respuestas, dice
):
    respuesta = _registrar(cliente, respuestas, examen=examen)

    assert respuesta.status_code == 422
    assert dice in respuesta.json()["detail"]
    assert claves.claves_registradas() == ()


def test_con_hojas_calificadas_no_se_cambia_y_lo_dice(cliente, resultados):
    _registrar(cliente, ["A"])
    resultados.hechos.append({"examen_id": EXAMEN, "calificacion": {"nota_en_decimas": 50}})

    assert cliente.get(f"/examenes/{EXAMEN}/clave").json()["se_puede_cambiar"] is False
    respuesta = _registrar(cliente, ["B"])

    assert respuesta.status_code == 409
    assert "no se puede cambiar" in respuesta.json()["detail"]
    assert cliente.get(f"/examenes/{EXAMEN}/clave").json()["respuestas"] == ["A"]


def test_cambiarla_la_deja_sin_habilitar(cliente):
    _registrar(cliente, ["A"])
    cliente.post(f"/examenes/{EXAMEN}/clave/habilitacion")

    cambiada = _registrar(cliente, ["B"]).json()

    assert (cambiada["respuestas"], cambiada["habilitada_por"]) == (["B"], None)


def test_el_registro_dice_que_se_guardo_y_se_habilito_sin_el_correo(cliente, caplog):
    with caplog.at_level(logging.INFO):
        _registrar(cliente, ["A", "B"])
        cliente.post(f"/examenes/{EXAMEN}/clave/habilitacion")

    eventos = [getattr(r, "evento", None) for r in caplog.records]
    assert "clave_registrada" in eventos
    assert "clave_habilitada" in eventos
    assert all(DOCENTE_DE_PRUEBA not in str(vars(registro)) for registro in caplog.records)
