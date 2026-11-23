"""Los exámenes de cada docente (ADR-0028): el identificador lo acuña el sistema, el nombre lo pone
el docente, y un examen es de quien lo creó.

Las reglas se prueban contra los tres adaptadores del registro (memoria, disco y Postgres, este
solo con `DATABASE_URL_PRUEBAS`), porque la API elige uno u otro según haya base de datos y los
tres tienen que comportarse igual."""

import os
import threading
from datetime import datetime, timezone

import pytest

from autoria import (
    ExamenNoEncontrado,
    NombreDeExamenInvalido,
    adoptar_examenes_sin_dueno,
    clave_del_nombre,
    crear_examen,
    examen_del_docente,
    examenes_del_docente,
)
from infraestructura.claves import ClavesEnDisco
from infraestructura.examenes import (
    ExamenesEnDisco,
    ExamenesEnMemoria,
    siguiente_identificador,
)
from infraestructura.modelo import ClaveDeRespuestas, Habilitacion, PreguntaDeLaClave

URL = os.environ.get("DATABASE_URL_PRUEBAS", "")
ANA = "ana@utb.edu.co"
BETO = "beto@utb.edu.co"
EN = datetime(2026, 11, 23, 8, 0, tzinfo=timezone.utc)


def _postgres():
    import psycopg

    from infraestructura.base_de_datos import ExamenesEnPostgres, crear_esquema

    crear_esquema(URL)
    with psycopg.connect(URL) as conexion:
        conexion.execute("TRUNCATE examenes")
        conexion.execute("ALTER SEQUENCE examenes_numero RESTART WITH 1")
    return ExamenesEnPostgres(URL)


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
        return ExamenesEnMemoria()
    if request.param == "disco":
        return ExamenesEnDisco(tmp_path / "examenes.json")
    return _postgres()


# --- El identificador ------------------------------------------------------------------------


def test_el_identificador_es_el_siguiente_numero_de_seis_digitos():
    assert siguiente_identificador(set()) == "000001"
    assert siguiente_identificador({"000001", "000002"}) == "000003"
    # Los identificadores viejos no son números y no cuentan.
    assert siguiente_identificador({"PARCIAL-1", "000007"}) == "000008"


def test_cada_examen_nuevo_recibe_el_siguiente_identificador(registro):
    primero, creado_1 = crear_examen("Parcial 1", ANA, EN, registro)
    segundo, creado_2 = crear_examen("Parcial 2", ANA, EN, registro)

    assert (primero.examen_id, primero.nombre, primero.docente, creado_1) == (
        "000001", "Parcial 1", ANA, True
    )
    assert (segundo.examen_id, creado_2) == ("000002", True)


# --- El nombre ---------------------------------------------------------------------------------


def test_dos_docentes_pueden_usar_el_mismo_nombre_y_cada_uno_tiene_su_examen(registro):
    de_ana, _ = crear_examen("Parcial 1", ANA, EN, registro)
    de_beto, creado = crear_examen("Parcial 1", BETO, EN, registro)

    assert creado is True
    assert de_ana.examen_id != de_beto.examen_id
    assert (de_ana.docente, de_beto.docente) == (ANA, BETO)


def test_el_mismo_docente_con_el_mismo_nombre_recibe_el_examen_que_ya_tenia(registro):
    original, _ = crear_examen("Parcial 1", ANA, EN, registro)

    otra_vez, creado = crear_examen("  parcial   1 ", ANA, EN, registro)

    assert creado is False
    assert otra_vez == original
    assert len(registro.examenes_del_docente(ANA)) == 1


def test_el_nombre_se_guarda_sin_espacios_de_mas():
    examen, _ = crear_examen("  Quiz   de  límites ", ANA, EN, ExamenesEnMemoria())

    assert examen.nombre == "Quiz de límites"
    assert clave_del_nombre("Quiz DE  Límites") == "quiz de límites"


@pytest.mark.parametrize(
    ("nombre", "dice"),
    [("   ", "Escriba"), ("x" * 81, "80"), ("Parcial\x001", "no se pueden leer")],
    ids=["vacio", "largo", "control"],
)
def test_un_nombre_que_no_sirve_no_crea_nada(nombre, dice):
    registro = ExamenesEnMemoria()

    with pytest.raises(NombreDeExamenInvalido, match=dice):
        crear_examen(nombre, ANA, EN, registro)
    assert registro.examenes_del_docente(ANA) == ()


# --- El dueño ----------------------------------------------------------------------------------


def test_el_examen_de_otro_docente_no_existe_para_quien_pregunta(registro):
    de_ana, _ = crear_examen("Parcial 1", ANA, EN, registro)

    assert examen_del_docente(de_ana.examen_id, ANA, registro) == de_ana
    with pytest.raises(ExamenNoEncontrado):
        examen_del_docente(de_ana.examen_id, BETO, registro)
    with pytest.raises(ExamenNoEncontrado):
        examen_del_docente("999999", ANA, registro)


def test_cada_docente_lista_solo_los_suyos(registro):
    crear_examen("Parcial 1", ANA, EN, registro)
    crear_examen("Parcial 1", BETO, EN, registro)
    crear_examen("Quiz", ANA, EN, registro)

    assert [e.nombre for e in registro.examenes_del_docente(ANA)] == ["Parcial 1", "Quiz"]
    assert [e.nombre for e in registro.examenes_del_docente(BETO)] == ["Parcial 1"]


def test_la_lista_de_la_carga_trae_solo_los_del_docente_que_tienen_clave(registro, tmp_path):
    claves = ClavesEnDisco(tmp_path / "claves")
    con_clave, _ = crear_examen("Parcial 1", ANA, EN, registro)
    crear_examen("Sin clave todavía", ANA, EN, registro)
    de_beto, _ = crear_examen("Parcial 1", BETO, EN, registro)
    for examen_id in (con_clave.examen_id, de_beto.examen_id):
        claves.guardar(
            ClaveDeRespuestas(
                examen_id, (PreguntaDeLaClave(1, "A"),), Habilitacion(ANA, EN)
            )
        )

    lista = examenes_del_docente(ANA, registro, claves)

    assert [(e.examen_id, e.nombre, e.habilitada) for e in lista] == [
        (con_clave.examen_id, "Parcial 1", True)
    ]


# --- Los exámenes anteriores a ADR-0028 ------------------------------------------------------


def test_los_examenes_sin_dueno_se_adoptan_con_su_identificador_como_nombre(registro):
    adoptados = adoptar_examenes_sin_dueno({"PARCIAL-1", "QUIZ-3"}, ANA, EN, registro)

    assert adoptados == ("PARCIAL-1", "QUIZ-3")
    examen = examen_del_docente("PARCIAL-1", ANA, registro)
    assert (examen.nombre, examen.docente) == ("PARCIAL-1", ANA)


def test_adoptar_otra_vez_no_toca_los_que_ya_tienen_dueno(registro):
    de_beto, _ = crear_examen("Parcial 1", BETO, EN, registro)
    adoptar_examenes_sin_dueno({"PARCIAL-1"}, ANA, EN, registro)

    otra_vez = adoptar_examenes_sin_dueno({"PARCIAL-1", de_beto.examen_id}, ANA, EN, registro)

    assert otra_vez == ()
    assert examen_del_docente(de_beto.examen_id, BETO, registro) == de_beto


def test_un_examen_nuevo_no_reusa_el_identificador_de_uno_adoptado(registro):
    adoptar_examenes_sin_dueno({"000001"}, ANA, EN, registro)

    nuevo, _ = crear_examen("Parcial 2", ANA, EN, registro)

    assert nuevo.examen_id != "000001"
    assert examen_del_docente("000001", ANA, registro).nombre == "000001"


def test_el_registro_en_disco_sobrevive_al_proceso(tmp_path):
    ruta = tmp_path / "examenes.json"
    creado, _ = crear_examen("Parcial 1", ANA, EN, ExamenesEnDisco(ruta))

    assert ExamenesEnDisco(ruta).examen(creado.examen_id) == creado


def test_crear_a_la_vez_el_mismo_examen_deja_uno_solo(registro):
    """Dos pestañas que guardan la clave a la vez piden el mismo examen."""
    resultados = []

    def crear():
        resultados.append(crear_examen("Parcial 1", ANA, EN, registro)[0])

    hilos = [threading.Thread(target=crear) for _ in range(8)]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join()

    assert len({examen.examen_id for examen in resultados}) == 1
    assert len(registro.examenes_del_docente(ANA)) == 1
