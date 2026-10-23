"""Prueba 13: los modos de fallo de la integración principal, la cola de trabajos (S11, ADR-0016).

La tabla de modos de fallo (`docs/evidencia/modos-de-fallo.md`) pide tres casos para cada
integración: que el otro lado no responda, que responda tarde y que responda dos veces. De la cola,
el «no responde» al publicar ya lo cubre `test_durabilidad_recepcion.py` (ADR-0006). Este archivo
cubre el resto, de los dos lados de la cola:

- **Responde tarde, al publicar.** Un servidor TCP que acepta la conexión y nunca contesta: un Redis
  vivo pero lento, no un sustituto que falla al instante. Es el caso que se midió en 10,0 s por hoja
  antes de ADR-0016, más que todo el techo de EC-07.
- **Sin reintentos ocultos.** El mismo servidor cuenta cuántas veces se le conecta el cliente: un
  reintento después de un tiempo agotado es una vía para que el mismo trabajo llegue dos veces.
- **Responde dos veces.** El mismo trabajo publicado dos veces en un Redis real se procesa una sola
  vez: el worker es idempotente por identificador de trabajo.
- **No responde y responde tarde, al consumir.** El worker sobrevive a un fallo de Redis, y
  `desencolar` no se cuelga si Redis no contesta.

Al final va el mismo caso de «responde tarde» para la otra integración que sale de la API, el
proveedor de LLM (ADR-0013), contra el mismo servidor que no contesta.

Todas corren sin Redis salvo la de «responde dos veces», que usa el Redis del CI y se salta con un
mensaje si no hay uno, como `test_encolado.py`.

Se validaron provocando la falla, una mutación a la vez sobre una copia del código:

- `ESPERA_AL_PUBLICAR_SEGUNDOS = 10.0`: fallan 3 de 4;
- `obtener_cliente_cola` sin la espera corta, como estaba antes: fallan las 2 del Redis lento;
- `retry=Retry(NoBackoff(), 3)`: fallan 3 de 4, y la de los reintentos cuenta 4 conexiones;
- sin `socket_connect_timeout`: falla la de la espera de conexión;
- el worker sin la comprobación de `primera_entrega`: fallan la de «responde dos veces», con el
  trabajo repetido procesado dos veces, y la de la marca sin comprobar;
- `_es_primera_entrega` devolviendo False cuando Redis falla: falla la de la marca sin comprobar.
- el adaptador del proveedor de LLM esperando ocho veces su tiempo de espera: falla la del
  proveedor que no contesta.
"""

import logging
import socket
import threading
import time
import uuid
from collections.abc import Iterator

import pytest
import redis.exceptions

import api.main
import worker.main as worker_main
from autoria.distractores import PreguntaParaDistractores, ProveedorNoDisponible
from autoria.proveedor_llm import TIEMPO_DE_ESPERA_SEGUNDOS, GeneradorCompatibleConOpenAI
from infraestructura.almacen import AlmacenEnDisco
from infraestructura.bitacora import BitacoraEnMemoria
from infraestructura.cola import (
    ESPERA_AL_PUBLICAR_SEGUNDOS,
    ESPERA_DE_CONEXION_SEGUNDOS,
    REDIS_URL_POR_OMISION,
    VIGENCIA_DE_UN_TRABAJO_VISTO_SEGUNDOS,
    ColaNoDisponible,
    Trabajo,
    cliente_redis,
    desencolar,
    preparar_trabajo,
    publicar,
)
from infraestructura.modelo import PENDIENTE_DE_ENCOLAR, ArchivoCargado
from ingesta import recibir_lote

JPG = b"\xff\xd8\xff" + b"\x00" * 32
UMBRAL_EC07_SEGUNDOS = 10.0
# Lo que puede costar, como mucho, una publicación contra un Redis que no contesta. Va escrito
# como número y no como la constante, para que subir la espera ponga la prueba en rojo.
TECHO_DE_UNA_PUBLICACION_SEGUNDOS = 3.0


class RedisQueNoContesta:
    """Acepta conexiones TCP y nunca escribe una respuesta: un Redis vivo pero lento.

    Cuenta las conexiones que recibe, que es la forma de ver desde afuera si el cliente reintentó.
    """

    def __init__(self) -> None:
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.bind(("127.0.0.1", 0))
        self._socket.listen(16)
        self._socket.settimeout(0.2)
        self._abiertas: list[socket.socket] = []
        self._seguir = True
        self._hilo = threading.Thread(target=self._aceptar, daemon=True)
        self._hilo.start()

    @property
    def url(self) -> str:
        return f"redis://127.0.0.1:{self._socket.getsockname()[1]}/0"

    @property
    def conexiones(self) -> int:
        return len(self._abiertas)

    def _aceptar(self) -> None:
        while self._seguir:
            try:
                conexion, _ = self._socket.accept()
            except OSError:
                continue
            self._abiertas.append(conexion)

    def cerrar(self) -> None:
        self._seguir = False
        self._hilo.join(timeout=1)
        for conexion in self._abiertas:
            conexion.close()
        self._socket.close()


@pytest.fixture
def redis_lento() -> Iterator[RedisQueNoContesta]:
    servidor = RedisQueNoContesta()
    yield servidor
    servidor.cerrar()


@pytest.fixture
def cliente_de_la_api(redis_lento: RedisQueNoContesta, monkeypatch: pytest.MonkeyPatch):
    """El cliente que usa la API de verdad (`obtener_cliente_cola`), apuntado al Redis lento."""
    monkeypatch.setattr(api.main, "REDIS_URL", redis_lento.url)
    return api.main.obtener_cliente_cola()


def test_publicar_contra_un_redis_que_no_contesta_se_rinde_en_la_espera_corta(
    cliente_de_la_api,
) -> None:
    """Responde tarde: la API se rinde en su espera corta y no en la del worker."""
    inicio = time.perf_counter()
    with pytest.raises(ColaNoDisponible):
        publicar(cliente_de_la_api, "procesamiento", preparar_trabajo({"examen_id": "CALC"}))
    transcurrido = time.perf_counter() - inicio

    assert transcurrido < TECHO_DE_UNA_PUBLICACION_SEGUNDOS


def test_un_lote_contra_un_redis_que_no_contesta_cumple_el_techo_de_ec07(
    redis_lento: RedisQueNoContesta, cliente_de_la_api, tmp_path
) -> None:
    """El caso completo, como lo ve el docente: 100 hojas con la cola lenta desde la primera.

    Todas quedan aceptadas y pendientes en la bitácora (ADR-0006), y la confirmación llega dentro
    del techo de EC-07 porque el lote solo paga una espera corta y deja de insistir."""
    archivos = [ArchivoCargado(f"hoja-{i:03d}.jpg", JPG) for i in range(1, 101)]
    bitacora = BitacoraEnMemoria()

    inicio = time.perf_counter()
    resultado = recibir_lote(
        "CALC-2026-01",
        archivos,
        AlmacenEnDisco(tmp_path),
        cliente_de_la_api,
        "procesamiento",
        bitacora,
    )
    transcurrido = time.perf_counter() - inicio

    assert resultado.total_procesados == 100
    assert all(hoja.estado == PENDIENTE_DE_ENCOLAR for hoja in resultado.aceptadas)
    assert len(bitacora.pendientes()) == 100
    assert transcurrido < UMBRAL_EC07_SEGUNDOS
    assert redis_lento.conexiones == 1, "el lote volvió a la cola después del primer fallo"


def test_el_cliente_no_reintenta_por_su_cuenta(redis_lento: RedisQueNoContesta) -> None:
    """Un solo intento por operación: lo que se reintente lo decide quien llama, con el mismo
    identificador de trabajo, y no redis-py en silencio."""
    cliente = cliente_redis(redis_lento.url, espera_segundos=0.5)

    with pytest.raises(ColaNoDisponible):
        publicar(cliente, "procesamiento", preparar_trabajo({"examen_id": "CALC"}))
    time.sleep(0.3)

    assert redis_lento.conexiones == 1


def test_la_conexion_se_rinde_en_la_espera_de_conexion() -> None:
    """Un Redis que no acepta la conexión (red caída, no un puerto cerrado) no puede costar más
    que la espera de conexión. No se provoca, porque exige una red que descarte paquetes; se
    comprueba que el cliente la lleva configurada."""
    cliente = cliente_redis("redis://127.0.0.1:6379/0")
    configuracion = cliente.connection_pool.connection_kwargs

    assert configuracion["socket_connect_timeout"] == ESPERA_DE_CONEXION_SEGUNDOS
    assert ESPERA_DE_CONEXION_SEGUNDOS + ESPERA_AL_PUBLICAR_SEGUNDOS < UMBRAL_EC07_SEGUNDOS


def test_el_worker_y_la_api_buscan_a_redis_en_el_mismo_lugar_sin_redis_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Sin `REDIS_URL`, la API caía en `localhost` y el
    worker, que llama a `cliente_redis()` sin URL, moría con `KeyError` al arrancar. Sin el
    valor por omisión, esta prueba termina en ese `KeyError`."""
    monkeypatch.delenv("REDIS_URL", raising=False)

    del_worker = cliente_redis().connection_pool.connection_kwargs

    assert REDIS_URL_POR_OMISION == "redis://localhost:6379/0"
    assert (del_worker["host"], del_worker["port"]) == ("localhost", 6379)


def test_la_api_reusa_un_solo_cliente_de_la_cola(monkeypatch: pytest.MonkeyPatch) -> None:
    """Un cliente nuevo por petición repetía la conexión y
    el saludo inicial de redis-py en cada lote. Sin la caché, cada llamada da un objeto distinto
    y esta prueba falla. No toca la red: el cliente conecta con el primer comando."""
    monkeypatch.setattr(api.main, "REDIS_URL", "redis://127.0.0.1:1/0")

    primero = api.main.obtener_cliente_cola()

    assert api.main.obtener_cliente_cola() is primero


# --- El lado del worker: la cola entrega el trabajo, tarde, nunca o dos veces ---------------


class _FinDeLaPrueba(Exception):
    """Corta el ciclo infinito del worker cuando la prueba ya vio lo que necesitaba."""


def _correr_worker(
    monkeypatch: pytest.MonkeyPatch, cliente: object, entregas: list
) -> None:
    """Corre `worker.main.ejecutar` con las entregas dadas, en orden, y lo corta al terminar.

    Cada entrega es un `Trabajo` o una excepción que `desencolar` levanta en su lugar."""
    pendientes = iter(entregas)

    def desencolar_siguiente(*_args: object, **_kwargs: object) -> Trabajo | None:
        try:
            siguiente = next(pendientes)
        except StopIteration:
            raise _FinDeLaPrueba from None
        if isinstance(siguiente, Exception):
            raise siguiente
        return siguiente

    monkeypatch.setattr(worker_main, "cliente_redis", lambda: cliente)
    monkeypatch.setattr(worker_main, "desencolar", desencolar_siguiente)
    # La pausa del worker, y no `time.sleep`: `worker_main.time` es el módulo `time` de todo el
    # proceso, y reemplazar su `sleep` apagaba cualquier otra espera mientras durara la prueba,
    # también las que no son del worker.
    monkeypatch.setattr(worker_main, "ESPERA_TRAS_ERROR_SEGUNDOS", 0)
    with pytest.raises(_FinDeLaPrueba):
        worker_main.ejecutar()


def _eventos(caplog: pytest.LogCaptureFixture, nombre: str) -> list[logging.LogRecord]:
    return [r for r in caplog.records if getattr(r, "evento", None) == nombre]


def _trabajo(trabajo_id: str) -> Trabajo:
    return Trabajo(
        id=trabajo_id,
        payload={"examen_id": "CALC", "nombre_archivo": "h.jpg", "referencia": "CALC/h.jpg"},
    )


def test_el_trabajo_que_llega_dos_veces_se_procesa_una_sola_vez(
    cliente, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Responde dos veces, contra un Redis real: el mismo identificador publicado dos veces en la
    cola (lo que deja un `RPUSH` que venció en el cliente y después se reintentó) se procesa una
    vez. El otro trabajo, con su propio identificador, se procesa normal."""
    cola = f"prueba-repetidos-{uuid.uuid4()}"
    repetido, otro = _trabajo(str(uuid.uuid4())), _trabajo(str(uuid.uuid4()))
    try:
        for trabajo in (repetido, repetido, otro):
            publicar(cliente, cola, trabajo)
        entregas = [desencolar(cliente, cola, timeout=1) for _ in range(3)]

        with caplog.at_level(logging.INFO, logger="worker"):
            _correr_worker(monkeypatch, cliente, entregas)

        procesados = [vars(r)["trabajo"] for r in _eventos(caplog, "hoja_recibida")]
        repetidos = [vars(r)["trabajo"] for r in _eventos(caplog, "trabajo_repetido")]
        assert procesados == [repetido.id, otro.id]
        assert repetidos == [repetido.id]
        vigencia = cliente.ttl(f"trabajo-visto:{repetido.id}")
        assert 0 < vigencia <= VIGENCIA_DE_UN_TRABAJO_VISTO_SEGUNDOS
    finally:
        # Aunque una aserción falle: si no, las marcas quedan 7 días en el Redis de desarrollo o
        # del CI.
        cliente.delete(f"trabajo-visto:{repetido.id}", f"trabajo-visto:{otro.id}", cola)


def test_si_no_se_puede_comprobar_la_marca_el_trabajo_se_procesa_igual(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """El trabajo ya salió de la cola: descartarlo por no poder comprobar sería perder la hoja."""

    def redis_falla(*_args: object) -> bool:
        raise ColaNoDisponible("Error 111 connecting to redis:6379. Connection refused.")

    monkeypatch.setattr(worker_main, "primera_entrega", redis_falla)
    with caplog.at_level(logging.INFO, logger="worker"):
        _correr_worker(monkeypatch, object(), [_trabajo("t-1")])

    assert len(_eventos(caplog, "idempotencia_sin_comprobar")) == 1
    assert len(_eventos(caplog, "hoja_recibida")) == 1


@pytest.mark.parametrize(
    "falla",
    [
        redis.exceptions.ConnectionError("Connection refused."),
        redis.exceptions.TimeoutError("Timeout reading from socket"),
    ],
    ids=["no-responde", "responde-tarde"],
)
def test_el_worker_sigue_vivo_si_la_cola_no_responde(
    falla: Exception, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """No responde o responde tarde, del lado del worker: un fallo de Redis no lo tumba; lo
    registra, espera y vuelve a pedir. La espera vencida cuenta como fallo y no como cola vacía
    (antes, `desencolar` la convertía en `None`)."""
    monkeypatch.setattr(worker_main, "primera_entrega", lambda *_args: True)
    entregas = [falla, _trabajo("t-1")]

    with caplog.at_level(logging.INFO, logger="worker"):
        _correr_worker(monkeypatch, object(), entregas)

    assert len(_eventos(caplog, "fallo_de_la_cola")) == 1
    assert len(_eventos(caplog, "hoja_recibida")) == 1


def test_desencolar_de_una_cola_que_no_contesta_avisa_en_vez_de_colgarse(
    redis_lento: RedisQueNoContesta,
) -> None:
    """Responde tarde, del lado del worker: si Redis no contesta dentro de la espera del socket,
    `desencolar` no se queda esperando para siempre ni lo hace pasar por una cola vacía: levanta
    el `TimeoutError`, que el worker registra como `fallo_de_la_cola`. Antes devolvía None, y una
    cola caída se veía como un worker sin trabajo."""
    cliente = cliente_redis(redis_lento.url, espera_segundos=0.5)

    inicio = time.perf_counter()
    with pytest.raises(redis.exceptions.TimeoutError):
        desencolar(cliente, "procesamiento", timeout=0)
    assert time.perf_counter() - inicio < 2.0


# --- La otra integración que sale de la API: el proveedor de LLM (ADR-0013) -----------------


def test_un_proveedor_que_no_contesta_se_corta_en_su_espera_y_sin_reintentar(
    redis_lento: RedisQueNoContesta,
) -> None:
    """Responde tarde, en la integración con el proveedor de LLM (MF-08). El mismo servidor sirve
    de proveedor lento: acepta la conexión y no contesta nada, ni a Redis ni a HTTP. El adaptador
    se corta en su tiempo de espera, responde con un motivo para el profesor y no reintenta: una
    sola conexión. En operación la espera es de 20 s (ADR-0013); aquí se baja para que la prueba
    tarde medio segundo."""
    puerto = redis_lento.url.split(":")[2].split("/")[0]
    generador = GeneradorCompatibleConOpenAI(
        url_base=f"http://127.0.0.1:{puerto}/v1", modelo="prueba", clave="prueba",
        tiempo_de_espera=0.5,
    )

    inicio = time.perf_counter()
    with pytest.raises(ProveedorNoDisponible) as falla:
        generador.proponer(PreguntaParaDistractores("Derivada de x²", "2x"))
    transcurrido = time.perf_counter() - inicio

    assert "no respondió en 0.5 s" in falla.value.motivo
    assert transcurrido < 2.0
    assert redis_lento.conexiones == 1
    assert TIEMPO_DE_ESPERA_SEGUNDOS == 20
