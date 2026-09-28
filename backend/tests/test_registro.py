"""El registro estructurado: cada evento sale como una línea JSON con campos con nombre.

Es la evidencia de «logs estructurados» de la S8, y además la base de la métrica de EC-07 que
registra la API: si una línea deja de ser JSON o pierde sus campos, la métrica deja de poder
consultarse sin que nada más falle. Se validó provocando la falla: con un `FormateadorJSON` que
devuelve el texto del mensaje, las tres pruebas se ponen en rojo.
"""

import json
import logging
from pathlib import Path

import pytest

import worker.main as worker_main
from infraestructura.cola import Trabajo
from infraestructura.registro import FormateadorJSON


def _formatear(**campos: object) -> dict:
    registro = logging.makeLogRecord(
        {"name": "prueba", "levelname": "INFO", "levelno": logging.INFO,
         "msg": "Hoja %s", "args": ("recibida",), **campos}
    )
    linea = FormateadorJSON().format(registro)
    assert "\n" not in linea, "cada evento tiene que ocupar una sola línea"
    return json.loads(linea)


def test_cada_evento_es_una_linea_json_con_sus_campos() -> None:
    linea = _formatear(evento="hoja_recibida", trabajo="t-1", examen="parcial-1")

    assert linea["nivel"] == "INFO"
    assert linea["registro"] == "prueba"
    assert linea["mensaje"] == "Hoja recibida"
    assert linea["momento"].endswith("+00:00")
    assert linea["evento"] == "hoja_recibida"
    assert linea["trabajo"] == "t-1"
    assert linea["examen"] == "parcial-1"
    # Los atributos internos de `logging` no se cuelan como campos del evento.
    assert "levelno" not in linea
    assert "args" not in linea


def test_un_valor_que_no_es_json_sale_como_texto_en_vez_de_romper_el_registro() -> None:
    linea = _formatear(evento="hoja_recibida", referencia=Path("parcial-1") / "hoja.jpg")

    assert linea["referencia"].endswith("hoja.jpg")


class _FinDeLaPrueba(Exception):
    """Corta el ciclo infinito del worker después del primer trabajo."""


def test_el_worker_registra_la_hoja_recibida_con_los_datos_del_trabajo(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    trabajos = iter([
        Trabajo(id="t-1", payload={"examen_id": "parcial-1", "nombre_archivo": "hoja-001.jpg",
                                   "referencia": "parcial-1/hoja-001.jpg"}),
    ])

    def desencolar_una_vez(*_args: object, **_kwargs: object) -> Trabajo:
        try:
            return next(trabajos)
        except StopIteration:
            raise _FinDeLaPrueba from None

    monkeypatch.setattr(worker_main, "cliente_redis", lambda: object())
    monkeypatch.setattr(worker_main, "desencolar", desencolar_una_vez)

    with caplog.at_level(logging.INFO, logger="worker"), pytest.raises(_FinDeLaPrueba):
        worker_main.ejecutar()

    [registro] = [r for r in caplog.records if getattr(r, "evento", None) == "hoja_recibida"]
    linea = json.loads(FormateadorJSON().format(registro))
    assert linea["trabajo"] == "t-1"
    assert linea["examen"] == "parcial-1"
    assert linea["archivo"] == "hoja-001.jpg"
    assert linea["referencia"] == "parcial-1/hoja-001.jpg"
