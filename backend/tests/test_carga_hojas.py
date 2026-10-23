"""Prueba 6: el endpoint de carga (RF-01) visto desde fuera, como lo llama el frontend.

Complementa a `test_recepcion.py` sin repetirla. Allí se verifica la regla de negocio; aquí,
que la ruta exista con la forma acordada, que acepte varios archivos en una sola petición y que
el cuerpo de la respuesta le diga al docente qué entró y qué no.

Las dependencias del almacén y de la cola se sustituyen con `dependency_overrides`, que es la
razón por la que `api/main.py` las declara con `Depends` en lugar de construirlas al importar:
así esta prueba corre sin Redis y sin escribir en el volumen real."""

import asyncio
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.main import app, obtener_almacen, obtener_bitacora, obtener_cliente_cola
from infraestructura.almacen import AlmacenEnDisco
from infraestructura.bitacora import BitacoraEnMemoria
from ingesta import TAMANO_MAXIMO_DE_UNA_HOJA_BYTES
from tests.test_recepcion import JPG, PDF, PNG, ColaFalsa


@pytest.fixture
def cliente(tmp_path) -> Iterator[TestClient]:
    cola = ColaFalsa()
    app.dependency_overrides[obtener_almacen] = lambda: AlmacenEnDisco(tmp_path)
    app.dependency_overrides[obtener_cliente_cola] = lambda: cola
    yield TestClient(app)
    app.dependency_overrides.clear()


def _archivo(nombre: str, contenido: bytes, tipo: str = "image/jpeg"):
    return ("archivos", (nombre, contenido, tipo))


def test_carga_individual_confirma_la_recepcion(cliente):
    respuesta = cliente.post(
        "/examenes/CALC-2026-01/hojas",
        files=[_archivo("hoja.jpg", JPG)],
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["examen_id"] == "CALC-2026-01"
    assert cuerpo["total_procesados"] == 1
    assert cuerpo["rechazados"] == []
    assert cuerpo["aceptadas"][0]["nombre_archivo"] == "hoja.jpg"
    assert cuerpo["aceptadas"][0]["trabajo_id"]


def test_carga_en_lote_reporta_aceptadas_y_rechazadas_por_separado(cliente):
    """Un lote mixto responde 200, no un error: la petición se atendió completa y el cuerpo
    dice archivo por archivo qué pasó. Devolver un error obligaría a reenviar todo el lote,
    que es justo lo que EC-07 quiere evitar."""
    respuesta = cliente.post(
        "/examenes/CALC-2026-01/hojas",
        files=[
            _archivo("h1.jpg", JPG),
            _archivo("h2.png", PNG, "image/png"),
            _archivo("h3.pdf", PDF, "application/pdf"),
            _archivo("apuntes.txt", b"texto plano", "text/plain"),
        ],
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["total_procesados"] == 4
    assert len(cuerpo["aceptadas"]) == 3
    assert len(cuerpo["rechazados"]) == 1
    assert cuerpo["rechazados"][0]["nombre_archivo"] == "apuntes.txt"
    assert cuerpo["rechazados"][0]["motivo"]


def test_la_hoja_cargada_queda_en_el_almacen(cliente, tmp_path):
    respuesta = cliente.post(
        "/examenes/CALC-2026-01/hojas",
        files=[_archivo("hoja.jpg", JPG)],
    )

    referencia = respuesta.json()["aceptadas"][0]["referencia"]
    assert (Path(tmp_path) / referencia).read_bytes() == JPG


def test_una_peticion_sin_archivos_es_un_error_de_la_peticion(cliente):
    """422 y no 200: un lote vacío no es un lote recibido, es una petición mal formada. La
    distinción importa para que el frontend no muestre «0 hojas recibidas» como si fuera un
    resultado normal."""
    respuesta = cliente.post("/examenes/CALC-2026-01/hojas", files=[])

    assert respuesta.status_code == 422


class AlmacenQueMiraSuHilo(AlmacenEnDisco):
    """Almacén que anota si `guardar` corrió en el hilo del event loop de la API."""

    def __init__(self, raiz) -> None:
        super().__init__(raiz)
        self.en_el_event_loop: list[bool] = []

    def guardar(self, examen_id: str, nombre_archivo: str, contenido: bytes) -> str:
        try:
            asyncio.get_running_loop()
            self.en_el_event_loop.append(True)
        except RuntimeError:
            self.en_el_event_loop.append(False)
        return super().guardar(examen_id, nombre_archivo, contenido)


def test_el_lote_se_confirma_fuera_del_event_loop(tmp_path):
    """Riesgo R-21: `recibir_lote` escribe con `fsync` y
    espera a Redis, y llamada dentro de la ruta `async` congelaba la API durante el lote. Si
    `guardar` encuentra un event loop corriendo en su hilo, es que la API no puede atender nada
    más mientras tanto. Sin `run_in_threadpool`, esta prueba falla."""
    almacen = AlmacenQueMiraSuHilo(tmp_path)
    app.dependency_overrides[obtener_almacen] = lambda: almacen
    app.dependency_overrides[obtener_cliente_cola] = lambda: ColaFalsa()
    app.dependency_overrides[obtener_bitacora] = lambda: BitacoraEnMemoria()
    try:
        respuesta = TestClient(app).post(
            "/examenes/CALC-2026-01/hojas",
            files=[_archivo("h1.jpg", JPG), _archivo("h2.jpg", JPG)],
        )
    finally:
        app.dependency_overrides.clear()

    assert respuesta.status_code == 200
    assert almacen.en_el_event_loop == [False, False]


def test_una_hoja_que_pasa_del_tope_se_rechaza_y_el_lote_sigue(cliente):
    """No había tope por archivo en una ruta pública. La
    hoja grande se rechaza con su motivo; la otra entra."""
    grande = JPG + b"\x00" * TAMANO_MAXIMO_DE_UNA_HOJA_BYTES

    respuesta = cliente.post(
        "/examenes/CALC-2026-01/hojas",
        files=[_archivo("enorme.jpg", grande), _archivo("normal.jpg", JPG)],
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert [h["nombre_archivo"] for h in cuerpo["aceptadas"]] == ["normal.jpg"]
    assert cuerpo["rechazados"][0]["nombre_archivo"] == "enorme.jpg"
    assert "MB por hoja" in cuerpo["rechazados"][0]["motivo"]


def test_las_hojas_llegan_a_recibir_lote_de_a_una(cliente, monkeypatch):
    """La API leía el lote entero a una lista antes de procesar la primera hoja, y
    200 escaneos a la vez no caben en una instancia de 512 MB. Ahora le pasa a `recibir_lote` un
    iterador que lee cada hoja cuando le toca. Con la lista de antes, esta prueba falla."""
    import api.main as modulo_api

    recibidos = []
    original = modulo_api.recibir_lote

    def espia(**argumentos):
        recibidos.append(argumentos["archivos"])
        return original(**argumentos)

    monkeypatch.setattr(modulo_api, "recibir_lote", espia)

    respuesta = cliente.post(
        "/examenes/CALC-2026-01/hojas",
        files=[_archivo("h1.jpg", JPG), _archivo("h2.jpg", JPG)],
    )

    assert respuesta.status_code == 200
    assert len(recibidos) == 1
    assert isinstance(recibidos[0], Iterator)
