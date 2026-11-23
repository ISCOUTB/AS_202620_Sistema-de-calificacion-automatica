"""Las preguntas que el docente agrega en Pauta, guardadas a su nombre (ADR-0030).

Como los distractores guardados, se prueban contra los tres adaptadores del registro (memoria,
disco y Postgres, este solo con `DATABASE_URL_PRUEBAS`), y las rutas con el registro en memoria y
el docente de la sesión sustituido."""

import os
from collections.abc import Iterator
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from api.main import app, docente_de_la_sesion, obtener_registro_de_preguntas
from autoria import PreguntaInvalida, PreguntaRepetida, agregar_pregunta, llave_de_la_pregunta
from infraestructura.preguntas_del_docente import PreguntasEnDisco, PreguntasEnMemoria

URL = os.environ.get("DATABASE_URL_PRUEBAS", "")
ANA = "ana@utb.edu.co"
BETO = "beto@utb.edu.co"
EN = datetime(2026, 11, 23, 9, 0, tzinfo=timezone.utc)
DESPUES = datetime(2026, 11, 23, 10, 0, tzinfo=timezone.utc)

ENUNCIADO = "Calcule la derivada de f(x) = x·ln(x)."
CORRECTA = "ln(x) + 1"
LLAVE = llave_de_la_pregunta(ENUNCIADO, CORRECTA)
OTRO_ENUNCIADO = "Calcule la derivada de f(x) = cos(2x)."
OTRA_CORRECTA = "-2·sin(2x)"


def _postgres():
    import psycopg

    from infraestructura.base_de_datos import PreguntasEnPostgres, crear_esquema

    crear_esquema(URL)
    with psycopg.connect(URL) as conexion:
        conexion.execute("TRUNCATE preguntas_del_docente")
    return PreguntasEnPostgres(URL)


@pytest.fixture(
    params=[
        "memoria",
        "disco",
        pytest.param(
            "postgres",
            marks=pytest.mark.skipif(not URL, reason="sin DATABASE_URL_PRUEBAS"),
        ),
    ]
)
def registro(request, tmp_path):
    if request.param == "memoria":
        return PreguntasEnMemoria()
    if request.param == "disco":
        return PreguntasEnDisco(tmp_path / "preguntas-del-docente.json")
    return _postgres()


# --- Agregar, listar y eliminar, en los tres adaptadores ------------------------------------------


def test_la_pregunta_agregada_queda_en_la_lista_del_docente(registro):
    llave, pregunta = agregar_pregunta(
        ANA, "  Calcule la derivada de  f(x) = x·ln(x). ", " ln(x)  + 1", EN, registro
    )

    assert llave == LLAVE
    assert pregunta.enunciado == ENUNCIADO
    assert pregunta.respuesta_correcta == CORRECTA
    assert registro.del_docente(ANA) == [(LLAVE, pregunta)]


def test_sin_agregar_no_hay_ninguna(registro):
    assert registro.del_docente(ANA) == []


def test_las_mas_recientes_van_primero(registro):
    """Las agregadas van arriba en la lista de Pauta: la última, la primera."""
    agregar_pregunta(ANA, ENUNCIADO, CORRECTA, EN, registro)
    agregar_pregunta(ANA, OTRO_ENUNCIADO, OTRA_CORRECTA, DESPUES, registro)

    assert [p.enunciado for _, p in registro.del_docente(ANA)] == [OTRO_ENUNCIADO, ENUNCIADO]


def test_la_misma_pregunta_con_otros_espacios_no_se_agrega_dos_veces(registro):
    agregar_pregunta(ANA, ENUNCIADO, CORRECTA, EN, registro)

    with pytest.raises(PreguntaRepetida, match="ya está en su lista"):
        agregar_pregunta(ANA, f" {ENUNCIADO} ", CORRECTA, DESPUES, registro)

    [(_, pregunta)] = registro.del_docente(ANA)
    assert pregunta.agregada_en == EN


def test_cada_docente_tiene_las_suyas(registro):
    agregar_pregunta(ANA, ENUNCIADO, CORRECTA, EN, registro)

    assert registro.del_docente(BETO) == []
    agregar_pregunta(BETO, ENUNCIADO, CORRECTA, EN, registro)
    assert len(registro.del_docente(ANA)) == 1


def test_eliminar_borra_solo_esa(registro):
    agregar_pregunta(ANA, ENUNCIADO, CORRECTA, EN, registro)
    agregar_pregunta(ANA, OTRO_ENUNCIADO, OTRA_CORRECTA, EN, registro)

    assert registro.eliminar(ANA, LLAVE) is True

    assert [p.enunciado for _, p in registro.del_docente(ANA)] == [OTRO_ENUNCIADO]
    assert registro.eliminar(ANA, LLAVE) is False


def test_eliminar_no_toca_las_de_otro_docente(registro):
    agregar_pregunta(ANA, ENUNCIADO, CORRECTA, EN, registro)

    assert registro.eliminar(BETO, LLAVE) is False
    assert len(registro.del_docente(ANA)) == 1


@pytest.mark.parametrize(("enunciado", "correcta"), [("   ", CORRECTA), (ENUNCIADO, " ")])
def test_sin_enunciado_o_sin_respuesta_no_se_agrega(enunciado, correcta):
    registro = PreguntasEnMemoria()
    with pytest.raises(PreguntaInvalida, match="enunciado y la respuesta correcta"):
        agregar_pregunta(ANA, enunciado, correcta, EN, registro)
    assert registro.del_docente(ANA) == []


# --- Las rutas ------------------------------------------------------------------------------------


@pytest.fixture
def cliente() -> Iterator[tuple[TestClient, PreguntasEnMemoria]]:
    registro = PreguntasEnMemoria()
    app.dependency_overrides[obtener_registro_de_preguntas] = lambda: registro
    yield TestClient(app), registro
    app.dependency_overrides.pop(obtener_registro_de_preguntas, None)


PREGUNTA = {"enunciado": ENUNCIADO, "respuesta_correcta": CORRECTA}


def test_la_ruta_agrega_y_la_lista_la_devuelve(cliente):
    http, _ = cliente

    agregada = http.post("/preguntas", json=PREGUNTA)

    assert agregada.status_code == 201, agregada.text
    assert agregada.json()["llave"] == LLAVE
    assert agregada.json()["agregada_en"] is not None
    lista = http.get("/preguntas")
    assert lista.status_code == 200
    assert [(p["llave"], p["enunciado"], p["respuesta_correcta"]) for p in lista.json()] == [
        (LLAVE, ENUNCIADO, CORRECTA)
    ]


def test_la_ruta_no_agrega_una_repetida(cliente):
    http, _ = cliente
    assert http.post("/preguntas", json=PREGUNTA).status_code == 201

    repetida = http.post("/preguntas", json={**PREGUNTA, "enunciado": f"  {ENUNCIADO}"})

    assert repetida.status_code == 409
    assert repetida.json()["detail"] == "Esa pregunta ya está en su lista."


def test_la_ruta_no_agrega_una_en_blanco(cliente):
    http, registro = cliente
    respuesta = http.post("/preguntas", json={**PREGUNTA, "respuesta_correcta": "   "})
    assert respuesta.status_code == 422
    assert registro.del_docente("docente@quantia.test") == []


def test_eliminar_por_la_ruta(cliente):
    http, _ = cliente
    assert http.post("/preguntas", json=PREGUNTA).status_code == 201

    assert http.delete(f"/preguntas/{LLAVE}").status_code == 204

    assert http.get("/preguntas").json() == []
    otra_vez = http.delete(f"/preguntas/{LLAVE}")
    assert otra_vez.status_code == 404
    assert otra_vez.json()["detail"] == "Esa pregunta no está en su lista."


def test_otro_docente_no_ve_ni_elimina_las_preguntas(cliente):
    http, registro = cliente
    assert http.post("/preguntas", json=PREGUNTA).status_code == 201

    app.dependency_overrides[docente_de_la_sesion] = lambda: BETO

    assert http.get("/preguntas").json() == []
    assert http.delete(f"/preguntas/{LLAVE}").status_code == 404
    assert len(registro.del_docente("docente@quantia.test")) == 1


def test_una_llave_que_no_es_de_una_pregunta_da_422(cliente):
    http, _ = cliente
    assert http.delete("/preguntas/no-es-una-llave").status_code == 422
