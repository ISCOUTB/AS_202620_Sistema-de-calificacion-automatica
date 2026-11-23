"""Los distractores que el docente aprueba, guardados a su nombre (ADR-0029).

Las reglas se prueban contra los tres adaptadores del registro (memoria, disco y Postgres, este
solo con `DATABASE_URL_PRUEBAS`), porque la API elige uno u otro según haya base de datos. Las
rutas, con el registro en memoria y el docente de la sesión sustituido."""

import os
from collections.abc import Iterator
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from api.main import app, docente_de_la_sesion, obtener_registro_de_distractores
from autoria import (
    DISTRACTORES_POR_PREGUNTA,
    DistractoresInvalidos,
    guardar_distractores,
    llave_de_la_pregunta,
)
from infraestructura.distractores_guardados import DistractoresEnDisco, DistractoresEnMemoria
from infraestructura.modelo import DistractorGuardado

URL = os.environ.get("DATABASE_URL_PRUEBAS", "")
ANA = "ana@utb.edu.co"
BETO = "beto@utb.edu.co"
EN = datetime(2026, 11, 23, 9, 0, tzinfo=timezone.utc)
DESPUES = datetime(2026, 11, 23, 10, 0, tzinfo=timezone.utc)
MAS_TARDE = datetime(2026, 11, 23, 11, 0, tzinfo=timezone.utc)

ENUNCIADO = "Derive f(x) = x^2 + 3x"
CORRECTA = "2x + 3"
LLAVE = llave_de_la_pregunta(ENUNCIADO, CORRECTA)
OTRO_ENUNCIADO = "Derive f(x) = x^3"
OTRA_CORRECTA = "3x^2"
SUMO_EXPONENTE = DistractorGuardado("x + 3", "Bajó el exponente sin multiplicar por él.")
SIN_LINEAL = DistractorGuardado("2x", "Olvidó derivar el término lineal.")
PRIMERO_SOLO = DistractorGuardado("x^2 + 3", "Derivó solo el segundo término.")
SIN_BAJAR = DistractorGuardado("x^2", "No bajó el exponente.")


def _postgres():
    import psycopg

    from infraestructura.base_de_datos import DistractoresEnPostgres, crear_esquema

    crear_esquema(URL)
    with psycopg.connect(URL) as conexion:
        conexion.execute("TRUNCATE distractores_guardados")
    return DistractoresEnPostgres(URL)


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
        return DistractoresEnMemoria()
    if request.param == "disco":
        return DistractoresEnDisco(tmp_path / "distractores-guardados.json")
    return _postgres()


def _de(registro, docente: str) -> dict:
    """Lo guardado por el docente, por llave."""
    return dict(registro.del_docente(docente))


# --- La pregunta ----------------------------------------------------------------------------------


def test_la_llave_no_cambia_con_los_espacios():
    assert LLAVE == llave_de_la_pregunta("  Derive  f(x) =  x^2 + 3x ", "2x  + 3")


def test_la_llave_cambia_con_la_respuesta_correcta():
    assert LLAVE != llave_de_la_pregunta(ENUNCIADO, "2x + 4")


# --- Guardar, listar y quitar, en los tres adaptadores --------------------------------------------


def test_lo_guardado_queda_con_la_llave_de_la_pregunta(registro):
    guardar_distractores(
        ANA, " Derive f(x) =  x^2 + 3x", "2x + 3 ", [SUMO_EXPONENTE, SIN_LINEAL], EN, registro
    )

    [(llave, guardados)] = registro.del_docente(ANA)

    assert llave == LLAVE
    assert guardados.distractores == (SUMO_EXPONENTE, SIN_LINEAL)
    assert guardados.enunciado == ENUNCIADO
    assert guardados.respuesta_correcta == CORRECTA
    assert guardados.guardado_en == EN


def test_sin_guardar_no_hay_nada(registro):
    assert registro.del_docente(ANA) == []


def test_guardar_otra_vez_reemplaza_lo_anterior(registro):
    guardar_distractores(ANA, ENUNCIADO, CORRECTA, [SUMO_EXPONENTE, SIN_LINEAL], EN, registro)
    guardar_distractores(ANA, ENUNCIADO, CORRECTA, [PRIMERO_SOLO], DESPUES, registro)

    [(_, guardados)] = registro.del_docente(ANA)

    assert guardados.distractores == (PRIMERO_SOLO,)
    assert guardados.guardado_en == DESPUES


def test_cada_docente_tiene_los_suyos(registro):
    guardar_distractores(ANA, ENUNCIADO, CORRECTA, [SUMO_EXPONENTE], EN, registro)

    assert registro.del_docente(BETO) == []

    guardar_distractores(BETO, ENUNCIADO, CORRECTA, [SIN_LINEAL], EN, registro)
    assert _de(registro, ANA)[LLAVE].distractores == (SUMO_EXPONENTE,)


def test_la_lista_termina_en_lo_ultimo_que_se_guardo(registro):
    """La pantalla pone lo guardado al final de la lista: lo más reciente, de último."""
    guardar_distractores(ANA, ENUNCIADO, CORRECTA, [SIN_LINEAL], DESPUES, registro)
    guardar_distractores(ANA, OTRO_ENUNCIADO, OTRA_CORRECTA, [SIN_BAJAR], EN, registro)

    assert [g.enunciado for _, g in registro.del_docente(ANA)] == [OTRO_ENUNCIADO, ENUNCIADO]

    guardar_distractores(ANA, OTRO_ENUNCIADO, OTRA_CORRECTA, [SIN_BAJAR], MAS_TARDE, registro)
    assert [g.enunciado for _, g in registro.del_docente(ANA)] == [ENUNCIADO, OTRO_ENUNCIADO]


def test_quitar_borra_solo_esa_pregunta(registro):
    guardar_distractores(ANA, ENUNCIADO, CORRECTA, [SIN_LINEAL], EN, registro)
    guardar_distractores(ANA, OTRO_ENUNCIADO, OTRA_CORRECTA, [SIN_BAJAR], EN, registro)

    assert registro.eliminar(ANA, LLAVE) is True

    assert [g.enunciado for _, g in registro.del_docente(ANA)] == [OTRO_ENUNCIADO]
    assert registro.eliminar(ANA, LLAVE) is False


def test_quitar_no_toca_lo_de_otro_docente(registro):
    guardar_distractores(ANA, ENUNCIADO, CORRECTA, [SIN_LINEAL], EN, registro)

    assert registro.eliminar(BETO, LLAVE) is False
    assert LLAVE in _de(registro, ANA)


def test_se_guarda_sin_los_espacios_de_los_extremos(registro):
    con_espacios = DistractorGuardado("  2x ", " Olvidó el término lineal. ")
    guardar_distractores(ANA, ENUNCIADO, CORRECTA, [con_espacios], EN, registro)

    assert _de(registro, ANA)[LLAVE].distractores == (
        DistractorGuardado("2x", "Olvidó el término lineal."),
    )


# --- Lo que no se guarda --------------------------------------------------------------------------


def test_sin_ninguno_no_se_guarda():
    with pytest.raises(DistractoresInvalidos, match="al menos uno"):
        guardar_distractores(ANA, ENUNCIADO, CORRECTA, [], EN, DistractoresEnMemoria())


def test_no_caben_mas_de_los_que_tiene_la_hoja():
    cuatro = [SUMO_EXPONENTE, SIN_LINEAL, PRIMERO_SOLO, DistractorGuardado("3", "Derivó solo 3x.")]
    assert DISTRACTORES_POR_PREGUNTA == 3
    with pytest.raises(DistractoresInvalidos, match="3 distractores"):
        guardar_distractores(ANA, ENUNCIADO, CORRECTA, cuatro, EN, DistractoresEnMemoria())


def test_la_respuesta_correcta_escrita_de_otra_forma_no_es_un_distractor():
    with pytest.raises(DistractoresInvalidos, match="respuesta correcta"):
        guardar_distractores(
            ANA, ENUNCIADO, CORRECTA, [DistractorGuardado("2·x+3", "Ninguno.")], EN,
            DistractoresEnMemoria(),
        )


def test_un_distractor_repetido_no_se_guarda():
    with pytest.raises(DistractoresInvalidos, match="dos veces"):
        guardar_distractores(
            ANA, ENUNCIADO, CORRECTA, [SIN_LINEAL, DistractorGuardado("2 x", "Otro motivo.")], EN,
            DistractoresEnMemoria(),
        )


def test_sin_el_error_que_representa_no_se_guarda():
    with pytest.raises(DistractoresInvalidos, match="error"):
        guardar_distractores(
            ANA, ENUNCIADO, CORRECTA, [DistractorGuardado("2x", "  ")], EN, DistractoresEnMemoria()
        )


def test_lo_que_no_se_guarda_no_borra_lo_que_habia():
    registro = DistractoresEnMemoria()
    guardar_distractores(ANA, ENUNCIADO, CORRECTA, [SIN_LINEAL], EN, registro)

    with pytest.raises(DistractoresInvalidos):
        guardar_distractores(ANA, ENUNCIADO, CORRECTA, [], DESPUES, registro)

    assert _de(registro, ANA)[LLAVE].distractores == (SIN_LINEAL,)


# --- Las rutas ------------------------------------------------------------------------------------


@pytest.fixture
def cliente() -> Iterator[tuple[TestClient, DistractoresEnMemoria]]:
    registro = DistractoresEnMemoria()
    app.dependency_overrides[obtener_registro_de_distractores] = lambda: registro
    yield TestClient(app), registro
    app.dependency_overrides.pop(obtener_registro_de_distractores, None)


def _cuerpo(*distractores: DistractorGuardado) -> dict:
    return {
        "enunciado": ENUNCIADO,
        "respuesta_correcta": CORRECTA,
        "distractores": [{"expresion": d.expresion, "error": d.error} for d in distractores],
    }


def test_la_ruta_guarda_y_la_lista_los_devuelve(cliente):
    http, _ = cliente
    guardado = http.put("/distractores/guardados", json=_cuerpo(SUMO_EXPONENTE, SIN_LINEAL))
    assert guardado.status_code == 200, guardado.text
    assert guardado.json()["llave"] == LLAVE
    assert [d["expresion"] for d in guardado.json()["distractores"]] == ["x + 3", "2x"]

    lista = http.get("/distractores/guardados")

    assert lista.status_code == 200
    [pregunta] = lista.json()
    assert pregunta["llave"] == LLAVE
    assert pregunta["enunciado"] == ENUNCIADO
    assert pregunta["respuesta_correcta"] == CORRECTA
    assert pregunta["guardado_en"] is not None
    assert pregunta["distractores"] == [
        {"expresion": "x + 3", "error": SUMO_EXPONENTE.error},
        {"expresion": "2x", "error": SIN_LINEAL.error},
    ]


def test_sin_nada_guardado_la_lista_va_vacia(cliente):
    http, _ = cliente
    lista = http.get("/distractores/guardados")
    assert lista.status_code == 200
    assert lista.json() == []


def test_la_ruta_rechaza_con_el_motivo(cliente):
    http, registro = cliente
    respuesta = http.put("/distractores/guardados", json=_cuerpo(DistractorGuardado("2x+3", "x")))
    assert respuesta.status_code == 422
    assert "respuesta correcta" in respuesta.json()["detail"]
    assert registro.del_docente("docente@quantia.test") == []


def test_otro_docente_no_ve_lo_guardado(cliente):
    http, _ = cliente
    assert http.put("/distractores/guardados", json=_cuerpo(SIN_LINEAL)).status_code == 200

    app.dependency_overrides[docente_de_la_sesion] = lambda: BETO

    assert http.get("/distractores/guardados").json() == []


def test_quitar_por_la_ruta(cliente):
    http, _ = cliente
    assert http.put("/distractores/guardados", json=_cuerpo(SIN_LINEAL)).status_code == 200

    quitado = http.delete(f"/distractores/guardados/{LLAVE}")

    assert quitado.status_code == 204
    assert http.get("/distractores/guardados").json() == []
    otra_vez = http.delete(f"/distractores/guardados/{LLAVE}")
    assert otra_vez.status_code == 404
    assert otra_vez.json()["detail"] == "Esa pregunta no tiene distractores guardados."


def test_otro_docente_no_puede_quitar_lo_guardado(cliente):
    http, registro = cliente
    assert http.put("/distractores/guardados", json=_cuerpo(SIN_LINEAL)).status_code == 200

    app.dependency_overrides[docente_de_la_sesion] = lambda: BETO

    assert http.delete(f"/distractores/guardados/{LLAVE}").status_code == 404
    assert LLAVE in _de(registro, "docente@quantia.test")


def test_una_llave_que_no_es_de_una_pregunta_da_422(cliente):
    http, _ = cliente
    assert http.delete("/distractores/guardados/no-es-una-llave").status_code == 422
