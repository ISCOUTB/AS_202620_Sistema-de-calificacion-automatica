"""Registrar la clave de un examen y habilitarla desde la aplicación (A-04, RF-07, ADR-0026).

`autoria` decide qué es una clave válida y cuándo se puede cambiar; `ClavesEnDisco` la guarda en
la misma forma en que el worker la lee."""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from autoria import (
    MAXIMO_DE_PREGUNTAS,
    ClaveInvalida,
    ClaveYaUsada,
    ExamenSinClave,
    clave_se_puede_cambiar,
    habilitar_clave,
    registrar_clave,
)
from infraestructura.claves import ClavesEnDisco
from infraestructura.modelo import Habilitacion
from omr import FORMATO_V1

EXAMEN = "CALC-2026-03"
EN = datetime(2026, 11, 22, 15, 0, tzinfo=timezone.utc)


class ResultadosFalsos:
    """El registro de resultados, con los hechos que se le den."""

    def __init__(self, hechos: list[dict] | None = None) -> None:
        self.hechos = hechos or []

    def hechos_del_examen(self, examen_id: str) -> list[dict]:
        return [hecho for hecho in self.hechos if hecho["examen_id"] == examen_id]


@pytest.fixture
def claves(tmp_path: Path) -> ClavesEnDisco:
    return ClavesEnDisco(tmp_path / "claves")


def test_el_maximo_de_preguntas_es_el_de_la_hoja():
    """`autoria` no puede importar `omr`: el número se repite, y esta prueba los mantiene juntos."""
    assert MAXIMO_DE_PREGUNTAS == FORMATO_V1.numero_de_preguntas()


def test_la_clave_registrada_se_guarda_sin_habilitar_y_el_worker_la_lee_igual(claves):
    clave = registrar_clave(EXAMEN, ["A", "b", "C", "D"], claves, ResultadosFalsos())

    assert clave.habilitacion is None
    leida = claves.clave_del_examen(EXAMEN)
    assert leida == clave
    assert [(p.numero, p.correcta, p.peso) for p in leida.preguntas] == [
        (1, "A", 1.0), (2, "B", 1.0), (3, "C", 1.0), (4, "D", 1.0),
    ]


@pytest.mark.parametrize(
    ("respuestas", "motivo"),
    [
        ([], "al menos una"),
        (["A"] * (MAXIMO_DE_PREGUNTAS + 1), "41"),
        (["A", "E"], "pregunta 2"),
        (["A", ""], "pregunta 2"),
    ],
    ids=["vacia", "demasiadas", "opcion-que-no-existe", "en-blanco"],
)
def test_una_clave_que_no_cabe_en_la_hoja_no_se_guarda(claves, respuestas, motivo):
    with pytest.raises(ClaveInvalida, match=motivo):
        registrar_clave(EXAMEN, respuestas, claves, ResultadosFalsos())

    assert claves.clave_del_examen(EXAMEN) is None


@pytest.mark.parametrize("examen", ["", " ", "../otro", "con espacio", "x" * 65, "ñandú"])
def test_un_identificador_de_examen_raro_no_se_acepta(claves, examen):
    """El identificador es el nombre del archivo de la clave y el que se escribe en la carga."""
    with pytest.raises(ClaveInvalida, match="identificador"):
        registrar_clave(examen, ["A"], claves, ResultadosFalsos())


def test_habilitarla_la_deja_a_nombre_del_docente_y_con_la_hora(claves):
    registrar_clave(EXAMEN, ["A", "B"], claves, ResultadosFalsos())

    habilitada = habilitar_clave(EXAMEN, "profe@utb.edu.co", EN, claves)

    assert habilitada.habilitacion == Habilitacion(por="profe@utb.edu.co", en=EN)
    assert claves.clave_del_examen(EXAMEN) == habilitada


def test_habilitar_otra_vez_conserva_quien_y_cuando(claves):
    registrar_clave(EXAMEN, ["A"], claves, ResultadosFalsos())
    primera = habilitar_clave(EXAMEN, "profe@utb.edu.co", EN, claves)

    segunda = habilitar_clave(EXAMEN, "otra@utb.edu.co", datetime.now(timezone.utc), claves)

    assert segunda.habilitacion == primera.habilitacion


def test_no_se_habilita_un_examen_sin_clave(claves):
    with pytest.raises(ExamenSinClave):
        habilitar_clave(EXAMEN, "profe@utb.edu.co", EN, claves)


def test_cambiar_una_clave_habilitada_la_deja_sin_habilitar(claves):
    """La habilitación certifica unas respuestas: si cambian, hay que volver a habilitarla."""
    registrar_clave(EXAMEN, ["A"], claves, ResultadosFalsos())
    habilitar_clave(EXAMEN, "profe@utb.edu.co", EN, claves)

    cambiada = registrar_clave(EXAMEN, ["B"], claves, ResultadosFalsos())

    assert cambiada.habilitacion is None
    assert claves.clave_del_examen(EXAMEN).preguntas[0].correcta == "B"


def test_con_hojas_calificadas_la_clave_ya_no_se_cambia(claves):
    """Las notas no se recalculan al cambiar la clave: una hoja quedaría con la vieja y la
    siguiente con la nueva."""
    registrar_clave(EXAMEN, ["A"], claves, ResultadosFalsos())
    calificada = ResultadosFalsos([{"examen_id": EXAMEN, "calificacion": {"nota_en_decimas": 50}}])

    assert not clave_se_puede_cambiar(EXAMEN, calificada)
    with pytest.raises(ClaveYaUsada):
        registrar_clave(EXAMEN, ["B"], claves, calificada)
    assert claves.clave_del_examen(EXAMEN).preguntas[0].correcta == "A"


def test_hojas_leidas_sin_nota_no_la_dejan_fija(claves):
    """Una hoja leída sin clave habilitada no tiene nota que la vieja clave haya calculado."""
    sin_nota = ResultadosFalsos([
        {"examen_id": EXAMEN, "calificacion": None},
        {"examen_id": "OTRO", "calificacion": {"nota_en_decimas": 30}},
    ])

    assert clave_se_puede_cambiar(EXAMEN, sin_nota)
    registrar_clave(EXAMEN, ["C"], claves, sin_nota)


def test_la_clave_se_escribe_completa_o_no_se_escribe(claves, monkeypatch):
    """Se escribe en un temporal y se reemplaza: el worker nunca lee una clave a medias."""
    registrar_clave(EXAMEN, ["A"], claves, ResultadosFalsos())

    def falla(*args, **kwargs):
        raise OSError("disco lleno")

    monkeypatch.setattr("infraestructura.claves.os.replace", falla)
    with pytest.raises(OSError):
        registrar_clave(EXAMEN, ["B"], claves, ResultadosFalsos())

    assert claves.clave_del_examen(EXAMEN).preguntas[0].correcta == "A"
    assert [r.name for r in claves.directorio.iterdir()] == [f"{EXAMEN}.json"]
