"""El registro estructurado: cada evento sale como una línea JSON con campos con nombre.

Es la evidencia de «logs estructurados» de la S8, y además la base de la métrica de EC-07 que
registra la API: si una línea deja de ser JSON o pierde sus campos, la métrica deja de poder
consultarse sin que nada más falle. Se validó provocando la falla: con un `FormateadorJSON` que
devuelve el texto del mensaje, las tres pruebas se ponen en rojo.
"""

import json
import logging
import uuid
from pathlib import Path

import pytest

import worker.main as worker_main
from infraestructura.almacen import AlmacenEnDisco
from infraestructura.cola import Trabajo, publicar
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


def test_el_worker_registra_la_hoja_recibida_con_los_datos_del_trabajo(
    cliente, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Desde el taller de mensajería (ADR-0020) el worker abre la imagen y consume con acuse, así
    que la prueba usa el Redis del CI (se salta sin él) y una imagen de verdad en un almacén
    temporal."""
    cola = f"prueba-registro-{uuid.uuid4()}"
    (tmp_path / "parcial-1").mkdir()
    (tmp_path / "parcial-1" / "hoja-001.jpg").write_bytes(b"\xff\xd8\xff" + b"\x00" * 8)
    trabajo = Trabajo(id=f"t-{uuid.uuid4()}", payload={
        "hoja_id": "h-1", "examen_id": "parcial-1", "nombre_archivo": "hoja-001.jpg",
        "referencia": "parcial-1/hoja-001.jpg",
    })
    try:
        publicar(cliente, cola, trabajo)
        with caplog.at_level(logging.INFO, logger="worker"):
            worker_main.atender_una_vez(cliente, cola, AlmacenEnDisco(tmp_path))
    finally:
        cliente.delete(cola, f"{cola}:en-curso", f"trabajo-visto:{trabajo.id}")

    [registro] = [r for r in caplog.records if getattr(r, "evento", None) == "hoja_recibida"]
    linea = json.loads(FormateadorJSON().format(registro))
    assert linea["trabajo"] == trabajo.id
    assert linea["examen"] == "parcial-1"
    assert linea["archivo"] == "hoja-001.jpg"
    assert linea["referencia"] == "parcial-1/hoja-001.jpg"
