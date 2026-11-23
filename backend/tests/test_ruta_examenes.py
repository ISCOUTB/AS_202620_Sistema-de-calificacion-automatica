"""Los exámenes con clave registrada: la vista de `autoria` y la ruta `GET /examenes` que la
publica para la lista de la pantalla de carga.

Lo que cuidan, además del orden y de la marca de habilitación, es que las respuestas de la clave no
salgan por la ruta (AM-02) y, desde ADR-0028, que cada docente vea solo los suyos."""

import json
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from datetime import datetime, timezone

from api.main import app, obtener_catalogo_de_claves, obtener_registro_de_examenes
from autoria import ExamenConClave, examenes_con_clave
from infraestructura.almacen import directorio_del_examen
from infraestructura.claves import ClavesEnDisco
from infraestructura.examenes import ExamenesEnMemoria
from tests.sesion_de_prueba import DOCENTE_DE_PRUEBA

ANTES = datetime(2026, 11, 1, tzinfo=timezone.utc)

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
        ExamenConClave("PARCIAL-1", habilitada=True, nombre="PARCIAL-1"),
        ExamenConClave("PARCIAL-2", habilitada=True, nombre="PARCIAL-2"),
        ExamenConClave("QUIZ-3", habilitada=False, nombre="QUIZ-3"),
    )


@pytest.fixture
def cliente(catalogo) -> Iterator[TestClient]:
    """Tres de las claves son del docente de prueba; `PARCIAL-2` es de otro docente."""
    registro = ExamenesEnMemoria()
    for examen_id in ("PARCIAL-1", "QUIZ-3"):
        registro.adoptar(examen_id, DOCENTE_DE_PRUEBA, ANTES)
    registro.adoptar("PARCIAL-2", "otra@quantia.test", ANTES)
    app.dependency_overrides[obtener_catalogo_de_claves] = lambda: catalogo
    app.dependency_overrides[obtener_registro_de_examenes] = lambda: registro
    yield TestClient(app)
    app.dependency_overrides.pop(obtener_catalogo_de_claves, None)


def test_la_ruta_publica_solo_los_examenes_con_clave_del_docente(cliente):
    respuesta = cliente.get("/examenes")

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "examenes": [
            {"examen_id": "PARCIAL-1", "nombre": "PARCIAL-1", "habilitada": True},
            {"examen_id": "QUIZ-3", "nombre": "QUIZ-3", "habilitada": False},
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
        app.dependency_overrides.pop(obtener_catalogo_de_claves, None)

    assert (respuesta.status_code, respuesta.json()) == (200, {"examenes": []})
