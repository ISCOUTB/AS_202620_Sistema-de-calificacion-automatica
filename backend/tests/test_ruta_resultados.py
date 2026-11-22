"""Cómo quedó cada hoja leída de un examen: la proyección de `dashboard` y la ruta
`GET /examenes/{examen_id}/resultados` que la publica (A-02 y A-03, ADR-0023).

Los hechos se escriben con el mismo registro que usa el worker, a partir de lecturas de verdad de
hojas sintéticas. Lo que cuidan, además de los estados, es que el código del estudiante no salga
por la ruta: es pública hasta A-05 (AM-02)."""

from collections.abc import Iterator
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from api.main import app, obtener_lector_de_resultados
from calificacion import calificar
from dashboard import resultados_del_examen
from herramientas.hojas_sinteticas import fotografiar, hoja_marcada, patron
from infraestructura.modelo import (
    CALIFICADA,
    EN_REVISION,
    ILEGIBLE,
    SIN_CLAVE_HABILITADA,
    ClaveDeRespuestas,
    Habilitacion,
    PreguntaDeLaClave,
)
from infraestructura.resultados import SIN_CLAVE, ResultadosEnDisco
from omr import leer_hoja

EXAMEN = "CALC-2026-02"
CODIGO = "20261105"
CLAVE = ClaveDeRespuestas(
    EXAMEN,
    tuple(PreguntaDeLaClave(n, patron(n)) for n in range(1, 41)),
    Habilitacion(por="Docente de prueba", en=datetime(2026, 11, 5, tzinfo=timezone.utc)),
)


@pytest.fixture(scope="module")
def lectura_clara():
    return leer_hoja(fotografiar(hoja_marcada({n: patron(n) for n in range(1, 41)}, CODIGO)), 70)


@pytest.fixture(scope="module")
def lectura_con_dudas():
    respuestas = {n: patron(n) for n in range(1, 41) if n != 7}
    return leer_hoja(
        fotografiar(hoja_marcada(respuestas, CODIGO, a_medias=((7, "C"),))), 70
    )


@pytest.fixture
def registro(tmp_path, lectura_clara, lectura_con_dudas) -> ResultadosEnDisco:
    registro = ResultadosEnDisco(tmp_path / "resultados.jsonl")
    registro.registrar_lectura("h-1", "t-1", EXAMEN, lectura_clara, calificar(lectura_clara, CLAVE))
    registro.registrar_lectura(
        "h-2", "t-2", EXAMEN, lectura_con_dudas, calificar(lectura_con_dudas, CLAVE)
    )
    registro.registrar_lectura_imposible("h-3", "t-3", EXAMEN, "imagen_ilegible")
    registro.registrar_lectura("h-4", "t-4", "OTRO", lectura_clara, None, SIN_CLAVE)
    return registro


def test_cada_hoja_muestra_su_estado_su_nota_y_lo_que_espera_al_profesor(registro):
    resultados = resultados_del_examen(EXAMEN, registro)

    hojas = {h.hoja_id: h for h in resultados.hojas}
    assert list(hojas) == ["h-1", "h-2", "h-3"]
    assert (hojas["h-1"].estado, hojas["h-1"].nota_en_decimas, hojas["h-1"].provisional) == (
        CALIFICADA, 50, False
    )
    assert hojas["h-1"].codigo_completo is True
    assert (hojas["h-2"].estado, hojas["h-2"].preguntas_por_revisar) == (EN_REVISION, (7,))
    assert hojas["h-2"].provisional is True
    assert (hojas["h-3"].estado, hojas["h-3"].motivo, hojas["h-3"].nota_en_decimas) == (
        ILEGIBLE, "imagen_ilegible", None
    )


def test_una_hoja_leida_otra_vez_muestra_la_ultima_lectura_en_su_mismo_lugar(
    registro, lectura_clara
):
    """Recalificar es un trabajo nuevo de la misma hoja (ADR-0018): el último hecho manda."""
    registro.registrar_lectura("h-3", "t-5", EXAMEN, lectura_clara, None, SIN_CLAVE)

    hojas = resultados_del_examen(EXAMEN, registro).hojas

    assert [h.hoja_id for h in hojas] == ["h-1", "h-2", "h-3"]
    assert (hojas[2].estado, hojas[2].motivo) == (SIN_CLAVE_HABILITADA, SIN_CLAVE)


@pytest.fixture
def cliente(registro) -> Iterator[TestClient]:
    app.dependency_overrides[obtener_lector_de_resultados] = lambda: registro
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_la_ruta_publica_los_resultados_del_examen(cliente):
    respuesta = cliente.get(f"/examenes/{EXAMEN}/resultados")

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["examen_id"] == EXAMEN
    assert [(h["hoja_id"], h["estado"], h["nota_en_decimas"]) for h in cuerpo["hojas"]] == [
        ("h-1", CALIFICADA, 50),
        ("h-2", EN_REVISION, cuerpo["hojas"][1]["nota_en_decimas"]),
        ("h-3", ILEGIBLE, None),
    ]
    assert cuerpo["hojas"][1]["preguntas_por_revisar"] == [7]


def test_el_codigo_del_estudiante_no_sale_por_la_ruta(cliente):
    """El registro sí lo guarda; la ruta, que es pública hasta A-05, no."""
    respuesta = cliente.get(f"/examenes/{EXAMEN}/resultados")

    assert CODIGO not in respuesta.text


def test_un_examen_sin_hojas_leidas_responde_una_lista_vacia(cliente):
    respuesta = cliente.get("/examenes/SIN-HOJAS/resultados")

    assert (respuesta.status_code, respuesta.json()["hojas"]) == (200, [])
