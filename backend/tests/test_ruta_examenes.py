"""Los exámenes con clave registrada: la vista de `autoria` y la ruta `GET /examenes` que la
publica para la lista de la pantalla de carga.

Lo que cuidan, además del orden y de la marca de habilitación, es que las respuestas de la clave no
salgan por la ruta: es pública hasta A-05 (AM-02)."""

import json
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from api.main import app, obtener_catalogo_de_claves
from autoria import ExamenConClave, examenes_con_clave
from infraestructura.almacen import directorio_del_examen
from infraestructura.claves import ClavesEnDisco

PREGUNTAS = [{"numero": n, "correcta": "D", "peso": 1.0} for n in range(1, 41)]
HABILITACION = {"por": "Docente de prueba", "en": "2026-11-05T12:00:00+00:00"}


def _escribir(directorio, examen_id: str, habilitacion=HABILITACION) -> None:
    clave = {"examen_id": examen_id, "preguntas": PREGUNTAS, "habilitacion": habilitacion}
    (directorio / f"{directorio_del_examen(examen_id)}.json").write_text(
        json.dumps(clave), encoding="utf-8"
    )


@pytest.fixture
def catalogo(tmp_path) -> ClavesEnDisco:
    _escribir(tmp_path, "PARCIAL-2")
    _escribir(tmp_path, "PARCIAL-1")
    _escribir(tmp_path, "QUIZ-3", habilitacion=None)
    return ClavesEnDisco(tmp_path)


def test_cada_examen_con_clave_sale_una_vez_en_orden_y_dice_si_esta_habilitado(catalogo):
    assert examenes_con_clave(catalogo) == (
        ExamenConClave("PARCIAL-1", habilitada=True),
        ExamenConClave("PARCIAL-2", habilitada=True),
        ExamenConClave("QUIZ-3", habilitada=False),
    )


@pytest.fixture
def cliente(catalogo) -> Iterator[TestClient]:
    app.dependency_overrides[obtener_catalogo_de_claves] = lambda: catalogo
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_la_ruta_publica_los_examenes_con_clave(cliente):
    respuesta = cliente.get("/examenes")

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "examenes": [
            {"examen_id": "PARCIAL-1", "habilitada": True},
            {"examen_id": "PARCIAL-2", "habilitada": True},
            {"examen_id": "QUIZ-3", "habilitada": False},
        ]
    }


def test_las_respuestas_de_la_clave_no_salen_por_la_ruta(cliente):
    """El catálogo sí las lee; la ruta, que es pública hasta A-05, no las publica."""
    texto = cliente.get("/examenes").text

    assert "correcta" not in texto
    assert "preguntas" not in texto
    assert "Docente de prueba" not in texto


def test_sin_claves_la_lista_esta_vacia(tmp_path):
    app.dependency_overrides[obtener_catalogo_de_claves] = lambda: ClavesEnDisco(tmp_path)
    try:
        respuesta = TestClient(app).get("/examenes")
    finally:
        app.dependency_overrides.clear()

    assert (respuesta.status_code, respuesta.json()) == (200, {"examenes": []})
