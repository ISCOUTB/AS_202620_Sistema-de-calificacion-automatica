"""Prueba 15: cada hoja tiene una identidad propia, separada de la de su trabajo (ADR-0018).

La identidad de la hoja es la decisión de datos más cara de revertir del sistema: cuando A-02 y
A-03 guarden la detección, la nota y la revisión manual, todo lo que se sepa de una hoja va a
colgar de ella, y cambiarla después obliga a migrar cada registro y cada cliente. Por eso se
fija ahora, antes de que haya datos que migrar, y estas pruebas sostienen las cuatro promesas
que la decisión hace:

1. **Una hoja, una identidad**, acuñada una sola vez al aceptarla, y distinta de la de su
   trabajo: volver a procesar la hoja será un trabajo nuevo de la misma hoja.
2. **La misma identidad en todas las copias**: el reporte al docente, la bitácora y el trabajo
   que viaja por la cola dicen el mismo `hoja_id`.
3. **La bitácora es la fuente de verdad** y la conserva al releerse, también en las líneas
   escritas antes de la decisión, que se leen con el `trabajo_id` como identidad de la hoja.
4. **El contrato la publica como obligatoria**, para que ningún cliente tenga que adivinarla.

Validadas provocando la falla: si el reporte usa `trabajo.id` como `hoja_id`, fallan cuatro (la
primera, la de las copias, la de releer la bitácora y la de la API); si el payload del trabajo no
lleva `hoja_id`, falla la de las copias; si la bitácora no escribe `hoja_id`, falla la de
releerla; si la lectura de una línea vieja inventa un identificador nuevo en vez de usar el del
trabajo, falla la de compatibilidad.
"""

import json
import logging
import uuid
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

import worker.main as worker_main
from api.main import app, obtener_almacen, obtener_bitacora, obtener_cliente_cola
from herramientas.exportar_contrato import RUTA_CONTRATO
from infraestructura.almacen import AlmacenEnDisco
from infraestructura.bitacora import BitacoraEnDisco, BitacoraEnMemoria
from infraestructura.cola import Trabajo
from infraestructura.modelo import PENDIENTE_DE_ENCOLAR, ArchivoCargado
from ingesta import recibir_lote
from tests.test_durabilidad_recepcion import ColaQueSeCae
from tests.test_recepcion import JPG, PNG, ColaFalsa

EXAMEN = "CALC-2026-01"
COLA = "procesamiento"


def _es_uuid(valor: str) -> bool:
    try:
        uuid.UUID(valor)
    except ValueError:
        return False
    return True


def test_cada_hoja_tiene_una_identidad_propia_distinta_de_la_de_su_trabajo(tmp_path):
    archivos = [ArchivoCargado("h1.jpg", JPG), ArchivoCargado("h2.png", PNG)]

    resultado = recibir_lote(
        EXAMEN, archivos, AlmacenEnDisco(tmp_path), ColaFalsa(), COLA, BitacoraEnMemoria()
    )

    hojas = {h.hoja_id for h in resultado.aceptadas}
    trabajos = {h.trabajo_id for h in resultado.aceptadas}
    assert len(hojas) == 2
    assert all(_es_uuid(hoja_id) for hoja_id in hojas)
    assert hojas.isdisjoint(trabajos)


def test_el_reporte_la_bitacora_y_el_trabajo_dicen_la_misma_hoja(tmp_path):
    cola = ColaFalsa()
    bitacora = BitacoraEnMemoria()

    resultado = recibir_lote(
        EXAMEN, [ArchivoCargado("h1.jpg", JPG)], AlmacenEnDisco(tmp_path), cola, COLA, bitacora
    )

    [hoja] = resultado.aceptadas
    [(_, publicado)] = cola.empujados
    trabajo = json.loads(publicado)
    assert trabajo["id"] == hoja.trabajo_id
    assert trabajo["payload"]["hoja_id"] == hoja.hoja_id
    assert bitacora.recibidas[hoja.trabajo_id].hoja_id == hoja.hoja_id


def test_la_bitacora_en_disco_conserva_la_identidad_de_la_hoja_pendiente(tmp_path):
    """La fuente de verdad (ADR-0018): lo que se relee del archivo, desde otro objeto, trae la
    misma identidad que se le reportó al docente, que es la que usará el reintento."""
    ruta = tmp_path / "bitacora" / "recepcion.jsonl"

    resultado = recibir_lote(
        EXAMEN,
        [ArchivoCargado(f"h{i}.jpg", JPG) for i in range(3)],
        AlmacenEnDisco(tmp_path / "almacen"),
        ColaQueSeCae(hasta=1),
        COLA,
        BitacoraEnDisco(ruta),
    )

    pendientes = BitacoraEnDisco(ruta).pendientes()
    reportadas = {
        h.trabajo_id: h.hoja_id for h in resultado.aceptadas if h.estado == PENDIENTE_DE_ENCOLAR
    }
    assert len(pendientes) == 2
    assert {e.trabajo_id: e.hoja_id for e in pendientes} == reportadas


def test_una_linea_anterior_a_la_decision_se_lee_con_su_trabajo_como_hoja(tmp_path):
    """Las bitácoras escritas antes de ADR-0018 no traen `hoja_id`. Entonces el trabajo era la
    hoja: leerlas con un identificador nuevo dejaría a la misma hoja con dos identidades."""
    ruta = tmp_path / "recepcion.jsonl"
    ruta.write_text(
        json.dumps(
            {
                "hecho": "recibida",
                "trabajo_id": "trabajo-viejo",
                "examen_id": EXAMEN,
                "referencia": f"{EXAMEN}/x-h1.jpg",
                "nombre_archivo": "h1.jpg",
                "momento": "2026-10-01T12:00:00+00:00",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    [entrada] = BitacoraEnDisco(ruta).pendientes()

    assert entrada.hoja_id == "trabajo-viejo"
    assert entrada.trabajo_id == "trabajo-viejo"


@pytest.fixture
def cliente_http(tmp_path) -> Iterator[TestClient]:
    app.dependency_overrides[obtener_almacen] = lambda: AlmacenEnDisco(tmp_path)
    app.dependency_overrides[obtener_cliente_cola] = lambda: ColaFalsa()
    app.dependency_overrides[obtener_bitacora] = lambda: BitacoraEnMemoria()
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_la_api_publica_la_identidad_de_la_hoja_y_el_contrato_la_exige(cliente_http):
    respuesta = cliente_http.post(
        f"/examenes/{EXAMEN}/hojas", files=[("archivos", ("hoja.jpg", JPG, "image/jpeg"))]
    )

    [hoja] = respuesta.json()["aceptadas"]
    assert _es_uuid(hoja["hoja_id"])
    assert hoja["hoja_id"] != hoja["trabajo_id"]
    contrato = json.loads(RUTA_CONTRATO.read_text(encoding="utf-8"))
    esquema = contrato["components"]["schemas"]["HojaAceptadaEnRespuesta"]
    assert {"hoja_id", "trabajo_id"} <= set(esquema["required"])


class _FinDeLaPrueba(Exception):
    """Corta el ciclo infinito del worker después del primer trabajo."""


def test_el_worker_registra_de_que_hoja_es_el_trabajo(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    trabajos = iter([
        Trabajo(id="t-1", payload={"hoja_id": "h-1", "examen_id": EXAMEN,
                                   "nombre_archivo": "h1.jpg", "referencia": "r"}),
    ])

    def desencolar_una_vez(*_args: object, **_kwargs: object) -> Trabajo:
        try:
            return next(trabajos)
        except StopIteration:
            raise _FinDeLaPrueba from None

    monkeypatch.setattr(worker_main, "cliente_redis", lambda: object())
    monkeypatch.setattr(worker_main, "desencolar", desencolar_una_vez)
    monkeypatch.setattr(worker_main, "primera_entrega", lambda *_args: True)

    with caplog.at_level(logging.INFO, logger="worker"), pytest.raises(_FinDeLaPrueba):
        worker_main.ejecutar()

    [registro] = [r for r in caplog.records if getattr(r, "evento", None) == "hoja_recibida"]
    assert vars(registro)["hoja"] == "h-1"
    assert vars(registro)["trabajo"] == "t-1"
