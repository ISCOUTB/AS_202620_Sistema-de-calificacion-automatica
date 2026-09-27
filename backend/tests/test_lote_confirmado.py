"""La métrica de EC-07 en la API: cada lote confirmado deja un evento `lote_confirmado`.

EC-07 pide confirmar el lote en <= 10 s sin pérdida silenciosa. Hasta la S8 esas dos cifras
solo existían en la medición del corte 1 (`herramientas/medir_ec07.py`); desde aquí cada lote
real las registra, y el entorno desplegado las deja consultables en su log. Estas pruebas
comprueban que el evento sale, que sus cuentas cuadran con la respuesta que recibe el docente, y
que una cola caída a mitad del lote se ve en `hojas_pendientes_de_encolar`. Se validaron
provocando la falla: sin el `logger.info` del endpoint, las dos se ponen en rojo.
"""

import json
import logging
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from api.main import app, obtener_almacen, obtener_bitacora, obtener_cliente_cola
from infraestructura.almacen import AlmacenEnDisco
from infraestructura.bitacora import BitacoraEnMemoria
from infraestructura.registro import FormateadorJSON
from tests.test_durabilidad_recepcion import ColaQueSeCae
from tests.test_recepcion import JPG

EXAMEN = "CALC-2026-01"


@pytest.fixture
def cargar(tmp_path) -> Iterator:
    """Devuelve una función que carga un lote contra una cola que acepta `hasta` trabajos."""

    def _cargar(archivos: list, hasta: int) -> dict:
        cola = ColaQueSeCae(hasta=hasta)
        app.dependency_overrides[obtener_almacen] = lambda: AlmacenEnDisco(tmp_path)
        app.dependency_overrides[obtener_cliente_cola] = lambda: cola
        app.dependency_overrides[obtener_bitacora] = lambda: BitacoraEnMemoria()
        respuesta = TestClient(app).post(f"/examenes/{EXAMEN}/hojas", files=archivos)
        assert respuesta.status_code == 200
        return respuesta.json()

    yield _cargar
    app.dependency_overrides.clear()


def _evento(caplog: pytest.LogCaptureFixture) -> dict:
    [registro] = [r for r in caplog.records if getattr(r, "evento", None) == "lote_confirmado"]
    return json.loads(FormateadorJSON().format(registro))


def test_cada_lote_confirmado_deja_su_metrica(cargar, caplog) -> None:
    archivos = [
        ("archivos", ("h1.jpg", JPG, "image/jpeg")),
        ("archivos", ("h2.jpg", JPG, "image/jpeg")),
        ("archivos", ("apuntes.txt", b"texto plano", "text/plain")),
    ]

    with caplog.at_level(logging.INFO, logger="api"):
        cuerpo = cargar(archivos, hasta=10)

    evento = _evento(caplog)
    assert evento["examen"] == EXAMEN
    assert evento["hojas_aceptadas"] == len(cuerpo["aceptadas"]) == 2
    assert evento["hojas_rechazadas"] == len(cuerpo["rechazados"]) == 1
    assert evento["hojas_pendientes_de_encolar"] == 0
    assert 0 <= evento["duracion_confirmacion_ms"] < 10_000


def test_la_cola_caida_a_mitad_del_lote_se_ve_en_la_metrica(cargar, caplog) -> None:
    archivos = [("archivos", (f"h{i}.jpg", JPG, "image/jpeg")) for i in range(1, 5)]

    with caplog.at_level(logging.INFO, logger="api"):
        cuerpo = cargar(archivos, hasta=1)

    evento = _evento(caplog)
    pendientes = [h for h in cuerpo["aceptadas"] if h["estado"] == "pendiente_de_encolar"]
    assert evento["hojas_aceptadas"] == 4
    assert evento["hojas_pendientes_de_encolar"] == len(pendientes) == 3
