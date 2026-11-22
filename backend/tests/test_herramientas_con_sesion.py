"""Las herramientas que miden contra una API desplegada mandan el token de una sesión cuando hay
uno en `QUANTIA_TOKEN` (ADR-0025). Va por el entorno y no por argumento: un argumento queda en el
historial de la terminal."""

from herramientas.sesion import encabezados_de_sesion


def test_con_token_en_el_entorno_mandan_el_encabezado(monkeypatch):
    monkeypatch.setenv("QUANTIA_TOKEN", " v1.abc.def \n")

    assert encabezados_de_sesion() == {"Authorization": "Bearer v1.abc.def"}


def test_sin_token_no_mandan_nada(monkeypatch):
    monkeypatch.delenv("QUANTIA_TOKEN", raising=False)

    assert encabezados_de_sesion() == {}
