"""El adaptador provisional que relee la clave de un examen (`infraestructura.claves`).

Devuelve la clave tal como se escribió, habilitada o no: la regla de no calificar sin habilitación
es de `calificacion`. Lo que sí le toca es distinguir un examen sin clave (None) de una clave mal
escrita (`ClaveMalEscrita`), y no dejar que el `examen_id`, que llega en el mensaje de la cola,
elija una ruta fuera del directorio."""

import json
from datetime import datetime, timezone

import pytest

from infraestructura.almacen import directorio_del_examen
from infraestructura.claves import ClaveMalEscrita, ClavesEnDisco
from infraestructura.modelo import ClaveDeRespuestas, Habilitacion, PreguntaDeLaClave

EXAMEN = "CALC-2026-01"


def _escribir(directorio, examen_id: str, contenido) -> None:
    texto = contenido if isinstance(contenido, str) else json.dumps(contenido)
    (directorio / f"{directorio_del_examen(examen_id)}.json").write_text(texto, encoding="utf-8")


def _clave_valida(**cambios) -> dict:
    clave = {
        "examen_id": EXAMEN,
        "preguntas": [
            {"numero": 1, "correcta": "A", "peso": 1.0},
            {"numero": 2, "correcta": "C", "peso": 0.5},
        ],
        "habilitacion": {"por": "Docente de prueba", "en": "2026-11-03T12:00:00+00:00"},
    }
    clave.update(cambios)
    return clave


def test_relee_la_clave_tal_como_se_escribio(tmp_path):
    _escribir(tmp_path, EXAMEN, _clave_valida())

    clave = ClavesEnDisco(tmp_path).clave_del_examen(EXAMEN)

    assert clave == ClaveDeRespuestas(
        examen_id=EXAMEN,
        preguntas=(PreguntaDeLaClave(1, "A", 1.0), PreguntaDeLaClave(2, "C", 0.5)),
        habilitacion=Habilitacion(
            por="Docente de prueba", en=datetime(2026, 11, 3, 12, 0, tzinfo=timezone.utc)
        ),
    )


def test_un_examen_sin_archivo_no_tiene_clave(tmp_path):
    assert ClavesEnDisco(tmp_path).clave_del_examen(EXAMEN) is None


def test_una_clave_sin_habilitar_se_devuelve_igual(tmp_path):
    _escribir(tmp_path, EXAMEN, _clave_valida(habilitacion=None))

    clave = ClavesEnDisco(tmp_path).clave_del_examen(EXAMEN)

    assert clave is not None
    assert clave.habilitacion is None


def test_sin_peso_la_pregunta_vale_lo_que_dice_el_modelo(tmp_path):
    _escribir(tmp_path, EXAMEN, _clave_valida(preguntas=[{"numero": 1, "correcta": "B"}]))

    clave = ClavesEnDisco(tmp_path).clave_del_examen(EXAMEN)

    assert clave is not None
    assert clave.preguntas == (PreguntaDeLaClave(1, "B", 1.0),)


@pytest.mark.parametrize(
    "contenido",
    [
        "{ esto no es JSON",
        json.dumps([1, 2, 3]),
        _clave_valida(examen_id="OTRO-EXAMEN"),
        _clave_valida(preguntas="A,B,C"),
        _clave_valida(preguntas=["A"]),
        _clave_valida(preguntas=[{"numero": "1", "correcta": "A"}]),
        _clave_valida(preguntas=[{"numero": True, "correcta": "A"}]),
        _clave_valida(preguntas=[{"numero": 1}]),
        _clave_valida(preguntas=[{"numero": 1, "correcta": "A", "peso": "1"}]),
        _clave_valida(habilitacion={"en": "2026-11-03T12:00:00+00:00"}),
        _clave_valida(habilitacion={"por": "Docente de prueba", "en": "ayer"}),
        _clave_valida(habilitacion={"por": "Docente de prueba", "en": "2026-11-03T12:00:00"}),
    ],
    ids=["no-es-json", "no-es-objeto", "de-otro-examen", "preguntas-texto", "pregunta-texto",
         "numero-texto", "numero-booleano", "sin-correcta", "peso-texto", "habilitacion-sin-quien",
         "fecha-que-no-es-iso", "fecha-sin-zona"],
)
def test_una_clave_mal_escrita_no_es_lo_mismo_que_no_tener_clave(tmp_path, contenido):
    _escribir(tmp_path, EXAMEN, contenido)

    with pytest.raises(ClaveMalEscrita):
        ClavesEnDisco(tmp_path).clave_del_examen(EXAMEN)


def test_una_clave_mal_escrita_es_un_valueerror():
    """Lo que promete el docstring del adaptador para quien no conozca la subclase."""
    assert issubclass(ClaveMalEscrita, ValueError)


def test_el_examen_id_no_elige_una_ruta_fuera_del_directorio(tmp_path):
    directorio = tmp_path / "claves"
    directorio.mkdir()
    (tmp_path / "fuera.json").write_text(json.dumps(_clave_valida(examen_id="../fuera")))

    assert ClavesEnDisco(directorio).clave_del_examen("../fuera") is None


def test_el_catalogo_lista_las_claves_que_el_worker_encontraria(tmp_path):
    _escribir(tmp_path, EXAMEN, _clave_valida())
    _escribir(tmp_path, "Cálculo 1", _clave_valida(examen_id="Cálculo 1", habilitacion=None))

    claves = ClavesEnDisco(tmp_path).claves_registradas()

    assert sorted(clave.examen_id for clave in claves) == ["CALC-2026-01", "Cálculo 1"]
    assert {clave.examen_id: clave.habilitacion is None for clave in claves} == {
        "CALC-2026-01": False,
        "Cálculo 1": True,
    }


def test_el_catalogo_deja_fuera_lo_que_no_es_una_clave_legible(tmp_path):
    """Un JSON roto, una clave sin preguntas y un archivo con el nombre de otro examen: ninguno
    es una clave que el worker leería con su `examen_id`, y ninguno tumba la lista."""
    _escribir(tmp_path, EXAMEN, _clave_valida())
    _escribir(tmp_path, "ROTO", "{no es json")
    _escribir(tmp_path, "SIN-PREGUNTAS", {"examen_id": "SIN-PREGUNTAS"})
    (tmp_path / "COPIADO.json").write_text(json.dumps(_clave_valida()), encoding="utf-8")
    (tmp_path / "notas.txt").write_text("no es una clave", encoding="utf-8")

    claves = ClavesEnDisco(tmp_path).claves_registradas()

    assert [clave.examen_id for clave in claves] == [EXAMEN]


def test_sin_directorio_el_catalogo_esta_vacio(tmp_path):
    assert ClavesEnDisco(tmp_path / "todavia-no-existe").claves_registradas() == ()
