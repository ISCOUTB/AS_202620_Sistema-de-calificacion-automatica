"""Prueba 13: los modos de fallo de la integración principal, la cola de trabajos (S11, ADR-0016).

La tabla de modos de fallo (`docs/evidencia/modos-de-fallo.md`) pide tres casos para cada
integración: que el otro lado no responda, que responda tarde y que responda dos veces. De la cola,
el primero ya lo cubre `test_durabilidad_recepcion.py` (ADR-0006). Este archivo cubre los otros dos
con un Redis de verdad mal portado, no con un sustituto que falla al instante:

- **Responde tarde.** Un servidor TCP que acepta la conexión y nunca contesta. Es el caso que se
  midió en 10,0 s por hoja antes de ADR-0016, más que todo el techo de EC-07.
- **Sin reintentos ocultos.** El mismo servidor cuenta cuántas veces se le conecta el cliente: un
  reintento después de un tiempo agotado es una vía para que el mismo trabajo llegue dos veces.

Ninguna necesita Redis: el servidor lo levanta la prueba en un puerto libre de 127.0.0.1.

Se validaron provocando la falla, una mutación a la vez sobre una copia del código:

- `ESPERA_AL_PUBLICAR_SEGUNDOS = 10.0`: fallan 3 de 4;
- `obtener_cliente_cola` sin la espera corta, como estaba antes: fallan las 2 del Redis lento;
- `retry=Retry(NoBackoff(), 3)`: fallan 3 de 4, y la de los reintentos cuenta 4 conexiones;
- sin `socket_connect_timeout`: falla la de la espera de conexión.
"""

import socket
import threading
import time
from collections.abc import Iterator

import pytest

import api.main
from infraestructura.almacen import AlmacenEnDisco
from infraestructura.bitacora import BitacoraEnMemoria
from infraestructura.cola import (
    ESPERA_AL_PUBLICAR_SEGUNDOS,
    ESPERA_DE_CONEXION_SEGUNDOS,
    ColaNoDisponible,
    cliente_redis,
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
