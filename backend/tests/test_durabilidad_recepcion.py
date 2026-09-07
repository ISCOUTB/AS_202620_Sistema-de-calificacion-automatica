"""Prueba 6: la recepción no pierde hojas en silencio cuando la cola falla (EC-07, ADR-0006).

Es la prueba que cubre el cambio del reto del primer corte. Lo que sostiene es la segunda cifra
de EC-07 —**0 % de pérdida silenciosa**— en el caso que antes la rompía: la cola se cae a mitad
de un lote.

Antes del cambio, medido y no supuesto (`docs/evidencia/medicion-ec07.md`): un lote de 200
hojas con la cola cayendo en la número 101 devolvía 500, reportaba **0** de 200 y dejaba 100
trabajos encolados que el docente no podía conocer y que se duplicaban al reintentar.

Estas pruebas se validaron provocando la falla, según la convención del equipo: se revirtió el
`try/except` de `recibir_lote` y se comprobó que la primera falla; se quitó la llamada a
`bitacora.registrar` y falla la segunda; se cambió el `fsync` de `BitacoraEnDisco` por un
`pass` y la cuarta sigue pasando **a propósito**, porque `fsync` protege contra la caída del
sistema operativo y no contra el fin del proceso, que es lo único que una prueba en un solo
proceso puede simular. Eso está anotado en el docstring de esa prueba en vez de fingir que la
cubre.
"""

import json

import pytest
import redis.exceptions
from fastapi.testclient import TestClient

from api.main import app, obtener_almacen, obtener_bitacora, obtener_cliente_cola
from infraestructura.almacen import AlmacenEnDisco
from infraestructura.bitacora import BitacoraEnDisco, BitacoraEnMemoria
from infraestructura.modelo import ENCOLADA, PENDIENTE_DE_ENCOLAR, ArchivoCargado
from ingesta import recibir_lote

JPG = b"\xff\xd8\xff" + b"\x00" * 32
EXAMEN = "CALC-2026-01"
COLA = "procesamiento"


class ColaQueSeCae:
    """Cliente de cola que acepta los primeros `hasta` trabajos y luego deja de responder.

    Reproduce el modo de fallo que importa: no que la cola esté caída desde el principio (eso
    se nota antes de subir nada), sino que se caiga con el lote a medio procesar."""

    def __init__(self, hasta: int) -> None:
        self.hasta = hasta
        self.empujados: list[str] = []
        self.intentos = 0

    def rpush(self, cola: str, valor: str) -> int:
        self.intentos += 1
        if len(self.empujados) >= self.hasta:
            raise redis.exceptions.ConnectionError(
                "Error 111 connecting to redis:6379. Connection refused."
            )
        self.empujados.append(valor)
        return len(self.empujados)


def _lote(cantidad: int) -> list[ArchivoCargado]:
    return [ArchivoCargado(f"hoja-{i:03d}.jpg", JPG) for i in range(1, cantidad + 1)]


def test_ninguna_hoja_del_lote_queda_sin_reportar_si_la_cola_se_cae(tmp_path):
    """La cifra del escenario: 200 cargadas, 200 reportadas, 0 % de pérdida silenciosa."""
    almacen = AlmacenEnDisco(tmp_path)
    cola = ColaQueSeCae(hasta=100)
    bitacora = BitacoraEnMemoria()

    resultado = recibir_lote(EXAMEN, _lote(200), almacen, cola, COLA, bitacora)

    assert resultado.total_procesados == 200
    assert len(resultado.aceptadas) == 200
    assert len(resultado.rechazados) == 0

    encoladas = [h for h in resultado.aceptadas if h.estado == ENCOLADA]
    pendientes = [h for h in resultado.aceptadas if h.estado == PENDIENTE_DE_ENCOLAR]
    assert len(encoladas) == 100
    assert len(pendientes) == 100


def test_la_hoja_que_no_se_encolo_queda_pendiente_en_la_bitacora(tmp_path):
    """Reportarla no basta: tiene que quedar el dato para reintentarla sin el docente."""
    almacen = AlmacenEnDisco(tmp_path)
    cola = ColaQueSeCae(hasta=2)
    bitacora = BitacoraEnMemoria()

    resultado = recibir_lote(EXAMEN, _lote(5), almacen, cola, COLA, bitacora)

    pendientes = bitacora.pendientes()
    assert len(pendientes) == 3

    ids_pendientes = {e.trabajo_id for e in pendientes}
    ids_reportados = {
        h.trabajo_id for h in resultado.aceptadas if h.estado == PENDIENTE_DE_ENCOLAR
    }
    assert ids_pendientes == ids_reportados

    # La referencia guardada permite recuperar la imagen: el reintento no vuelve a pedir nada.
    for entrada in pendientes:
        assert (tmp_path / entrada.referencia).exists()


def test_un_lote_sin_incidentes_no_deja_nada_pendiente(tmp_path):
    """La bitácora no puede acumular ruido cuando todo salió bien, o nadie la mirará."""
    almacen = AlmacenEnDisco(tmp_path)
    cola = ColaQueSeCae(hasta=1000)
    bitacora = BitacoraEnMemoria()

    resultado = recibir_lote(EXAMEN, _lote(10), almacen, cola, COLA, bitacora)

    assert all(h.estado == ENCOLADA for h in resultado.aceptadas)
    assert bitacora.pendientes() == []


def test_la_bitacora_en_disco_se_relee_desde_otro_objeto(tmp_path):
    """Lo pendiente se reconstruye leyendo el archivo, no de la memoria de quien lo escribió.

    Es lo máximo que puede afirmar una prueba en un solo proceso, y conviene decirlo con
    precisión: demuestra que el estado vive en el archivo y no en el objeto, que es la
    condición necesaria para sobrevivir a un reinicio. La suficiente —que el archivo esté en el
    plato del disco y no en la caché del sistema operativo— la da el `fsync` de
    `BitacoraEnDisco`, y verificarla exigiría cortarle la corriente a la máquina."""
    ruta = tmp_path / "bitacora.jsonl"
    almacen = AlmacenEnDisco(tmp_path / "imagenes")

    recibir_lote(EXAMEN, _lote(4), almacen, ColaQueSeCae(hasta=1), COLA, BitacoraEnDisco(ruta))

    otra = BitacoraEnDisco(ruta)
    assert len(otra.pendientes()) == 3


def test_una_linea_truncada_no_inutiliza_la_bitacora(tmp_path):
    """Si el proceso muere escribiendo, la última línea queda a medias. Las anteriores valen."""
    ruta = tmp_path / "bitacora.jsonl"
    almacen = AlmacenEnDisco(tmp_path / "imagenes")
    recibir_lote(EXAMEN, _lote(3), almacen, ColaQueSeCae(hasta=0), COLA, BitacoraEnDisco(ruta))

    with open(ruta, "a", encoding="utf-8") as archivo:
        archivo.write('{"hecho": "recibida", "trabajo_i')

    assert len(BitacoraEnDisco(ruta).pendientes()) == 3


def test_la_bitacora_solo_agrega_lineas(tmp_path):
    """Confirmar una entrada agrega un hecho; no reescribe el anterior."""
    ruta = tmp_path / "bitacora.jsonl"
    almacen = AlmacenEnDisco(tmp_path / "imagenes")
    recibir_lote(EXAMEN, _lote(2), almacen, ColaQueSeCae(hasta=2), COLA, BitacoraEnDisco(ruta))

    hechos = [json.loads(l) for l in ruta.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert [h["hecho"] for h in hechos] == ["recibida", "encolada", "recibida", "encolada"]


def test_el_endpoint_confirma_el_lote_en_vez_de_devolver_500(tmp_path):
    """De punta a punta por HTTP, que es lo que ve el docente.

    Antes de ADR-0006 esta misma petición devolvía 500 y un cuerpo sin ninguna hoja."""
    cola = ColaQueSeCae(hasta=2)
    app.dependency_overrides[obtener_almacen] = lambda: AlmacenEnDisco(tmp_path)
    app.dependency_overrides[obtener_cliente_cola] = lambda: cola
    app.dependency_overrides[obtener_bitacora] = lambda: BitacoraEnDisco(
        tmp_path / "bitacora.jsonl"
    )
    try:
        cliente = TestClient(app, raise_server_exceptions=False)
        respuesta = cliente.post(
            "/examenes/CALC-2026-01/hojas",
            files=[("archivos", (f"hoja-{i}.jpg", JPG, "image/jpeg")) for i in range(5)],
        )
    finally:
        app.dependency_overrides.clear()

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["total_procesados"] == 5
    estados = [h["estado"] for h in cuerpo["aceptadas"]]
    assert estados.count(ENCOLADA) == 2
    assert estados.count(PENDIENTE_DE_ENCOLAR) == 3


@pytest.mark.parametrize("hasta", [0, 1, 199, 200])
def test_la_suma_reportada_es_el_lote_completo_caiga_donde_caiga(tmp_path, hasta):
    """La invariante de EC-07 no depende de en qué hoja se caiga la cola."""
    almacen = AlmacenEnDisco(tmp_path / str(hasta))
    resultado = recibir_lote(
        EXAMEN, _lote(200), almacen, ColaQueSeCae(hasta=hasta), COLA, BitacoraEnMemoria()
    )
    assert resultado.total_procesados == 200


def test_el_lote_no_insiste_contra_una_cola_caida(tmp_path):
    """Tras el primer fallo, no se vuelve a tocar la cola en lo que queda del lote.

    Es la prueba que sostiene el techo de 10 s de EC-07 en el caso de fallo. Un cliente de Redis
    que no encuentra servidor tarda segundos en rendirse: contra un contenedor detenido se
    midieron 7,1 s para una sola hoja. Sin esta condición, un lote de 200 pagaría ese timeout
    doscientas veces (más de veinte minutos) para terminar exactamente en el mismo estado.

    Se validó provocando la falla: al quitar el corte, `intentos` sube a 200 y la prueba se pone
    en rojo."""
    almacen = AlmacenEnDisco(tmp_path)
    cola = ColaQueSeCae(hasta=0)
    bitacora = BitacoraEnMemoria()

    resultado = recibir_lote(EXAMEN, _lote(200), almacen, cola, COLA, bitacora)

    assert cola.intentos == 1, "la cola se tocó más de una vez con el servidor caído"
    assert resultado.total_procesados == 200
    assert all(h.estado == PENDIENTE_DE_ENCOLAR for h in resultado.aceptadas)
    assert len(bitacora.pendientes()) == 200


def test_el_lote_agota_la_cola_sana_antes_de_cortar(tmp_path):
    """El corte no se adelanta: mientras la cola responde, se sigue publicando.

    Con la cola aceptando 120 de 200, se esperan exactamente 121 intentos: las 120 que
    funcionaron más la que falló. Ni una más."""
    almacen = AlmacenEnDisco(tmp_path)
    cola = ColaQueSeCae(hasta=120)

    resultado = recibir_lote(EXAMEN, _lote(200), almacen, cola, COLA, BitacoraEnMemoria())

    assert cola.intentos == 121
    assert len([h for h in resultado.aceptadas if h.estado == ENCOLADA]) == 120
    assert len([h for h in resultado.aceptadas if h.estado == PENDIENTE_DE_ENCOLAR]) == 80
