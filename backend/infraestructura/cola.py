"""Adaptador minimalista de cola sobre Redis: una lista FIFO, sin reintentos ni acuses de
recibo. Basta para lo que EC-07 mide, la recepción; el acuse de recibo que exigirá procesar
cada hoja sin perderla es trabajo de A-02, así que no es todavía una cola de producción.

Cuánto se espera a Redis (S11, ADR-0016)
----------------------------------------
Es la integración principal del sistema, y su modo de fallo más caro no era que Redis estuviera
caído (eso se rechaza al instante) sino que estuviera **lento**: aceptaba la conexión y no
contestaba. Medido con la versión del lock, publicar una sola hoja tardaba 10,0 s antes de
rendirse, que es el `socket_timeout` que necesita el worker para su `BLPOP`, y con eso solo ya se
pasaba el techo de 10 s de EC-07. Por eso las esperas son dos y no una:

- quien **publica** (la API) espera como máximo `ESPERA_AL_PUBLICAR_SEGUNDOS`: un `RPUSH` sano
  tarda milisegundos, y el lote no puede quedarse esperando a la cola;
- quien **consume** (el worker) espera `ESPERA_AL_CONSUMIR_SEGUNDOS`, por encima del bloqueo de
  5 s de `desencolar`, para que el socket no venza justo cuando Redis contesta que no hay nada.

La conexión se rinde en `ESPERA_DE_CONEXION_SEGUNDOS` en los dos casos, y el cliente **no
reintenta** (`Retry(NoBackoff(), 0)`). Hoy redis-py ya no reintentaba al crearse con `from_url`,
pero solo por cómo arma la conexión: el constructor de `redis.Redis` sí trae reintentos por
omisión. Un reintento oculto del `RPUSH`, después de un tiempo agotado en el que Redis sí guardó
el trabajo, es justamente una forma de que el mismo trabajo llegue dos veces.

El trabajo que llega dos veces (S11, ADR-0016)
----------------------------------------------
Aun sin reintentos ocultos, un trabajo puede llegar dos veces al worker: si el `RPUSH` vence en
el cliente después de que Redis lo guardó, la hoja queda `pendiente_de_encolar` en la bitácora
aunque su trabajo sí está en la cola, y el reintento de las pendientes la publicaría otra vez con
el mismo identificador. `primera_entrega` es lo que hace idempotente al worker: deja una marca
por identificador con `SET NX` y vigencia, y solo la primera entrega la encuentra libre.
"""

import json
import os
import uuid
from dataclasses import asdict, dataclass

import redis
# Se importa el submódulo explícitamente: `redis.exceptions` solo queda disponible como
# efecto secundario de los imports internos de redis-py, y depender de eso es frágil.
import redis.exceptions
from redis.backoff import NoBackoff
from redis.retry import Retry

# Las tres esperas del cliente de Redis (ADR-0016). Las de publicar y conectar son cortas porque
# EC-07 tiene un techo de 10 s para todo el lote; la de consumir es larga porque el worker
# bloquea a propósito en `desencolar`.
ESPERA_DE_CONEXION_SEGUNDOS = 2.0
ESPERA_AL_PUBLICAR_SEGUNDOS = 2.0
ESPERA_AL_CONSUMIR_SEGUNDOS = 10.0

# Cuánto se recuerda que un trabajo ya se entregó (idempotencia del worker, ADR-0016). Una semana
# cubre de sobra el reintento de una hoja pendiente, que ocurre el mismo día; después la marca
# vence sola y la memoria de Redis no crece sin límite. Con 800 hojas al mes son unos KB.
VIGENCIA_DE_UN_TRABAJO_VISTO_SEGUNDOS = 7 * 24 * 60 * 60
_PREFIJO_TRABAJO_VISTO = "trabajo-visto:"


class ColaNoDisponible(RuntimeError):
    """La cola rechazó el trabajo o no estaba disponible.

    Existe para que `ingesta` pueda reaccionar a un fallo de la cola sin importar `redis`: su
    docstring declara que no conoce ni FastAPI ni Redis, y traducir el error aquí es lo que
    mantiene esa frase cierta. `publicar` es el único punto donde una excepción de redis-py se
    convierte en esta."""


@dataclass
class Trabajo:
    id: str
    payload: dict


def cliente_redis(
    url: str | None = None, espera_segundos: float = ESPERA_AL_CONSUMIR_SEGUNDOS
) -> redis.Redis:
    """Crea el cliente Redis a partir de REDIS_URL (o el valor pasado).

    `espera_segundos` es el `socket_timeout`: cuánto se espera una respuesta antes de rendirse.
    Por omisión es la del worker, por encima del timeout de bloqueo que usa `desencolar` para que
    el socket no expire justo cuando el servidor está por responder nil al vencer el BLPOP. La API
    pasa `ESPERA_AL_PUBLICAR_SEGUNDOS`. La conexión se rinde en `ESPERA_DE_CONEXION_SEGUNDOS` y
    el cliente no reintenta en ningún caso (ver el docstring del módulo)."""
    return redis.Redis.from_url(
        url or os.environ["REDIS_URL"],
        decode_responses=True,
        socket_timeout=espera_segundos,
        socket_connect_timeout=ESPERA_DE_CONEXION_SEGUNDOS,
        retry=Retry(NoBackoff(), 0),
    )


def preparar_trabajo(payload: dict) -> Trabajo:
    """Acuña el trabajo y su identificador **sin tocar la cola**.

    Está separado de `publicar` desde [ADR-0006](../../docs/adr/0006-registrar-la-recepcion-en-una-bitacora-antes-de-encolar.md):
    la bitácora de recepción tiene que registrar el identificador antes de que exista el riesgo
    de que la cola falle, y no puede inventarse uno distinto del que viajará en el trabajo."""
    return Trabajo(id=str(uuid.uuid4()), payload=payload)


def publicar(cliente: redis.Redis, cola: str, trabajo: Trabajo) -> Trabajo:
    """Agrega un trabajo ya acuñado al final de la cola (RPUSH, FIFO).

    Traduce cualquier fallo de redis-py a `ColaNoDisponible` para que quien llame no tenga que
    importar `redis` solo para atraparlo."""
    try:
        cliente.rpush(cola, json.dumps(asdict(trabajo)))
    except redis.exceptions.RedisError as error:
        raise ColaNoDisponible(str(error)) from error
    return trabajo


def encolar(cliente: redis.Redis, cola: str, payload: dict) -> Trabajo:
    """Acuña y publica en un solo paso. Se conserva para quien no necesita el identificador
    antes de publicar; `ingesta` sí lo necesita y usa las dos mitades por separado."""
    return publicar(cliente, cola, preparar_trabajo(payload))


def primera_entrega(cliente: redis.Redis, trabajo_id: str) -> bool:
    """True si es la primera vez que este trabajo se entrega; False si ya se entregó antes.

    Es la idempotencia del worker (ADR-0016): `SET trabajo-visto:<id> 1 NX EX <vigencia>` es
    atómico en Redis, así que de dos entregas del mismo identificador, aunque lleguen a dos
    workers a la vez, solo una encuentra la marca libre. Traduce los fallos de redis-py a
    `ColaNoDisponible`, como `publicar`: decidir qué hacer si no se pudo comprobar es de quien
    llama."""
    try:
        marcado = cliente.set(
            f"{_PREFIJO_TRABAJO_VISTO}{trabajo_id}",
            "1",
            nx=True,
            ex=VIGENCIA_DE_UN_TRABAJO_VISTO_SEGUNDOS,
        )
    except redis.exceptions.RedisError as error:
        raise ColaNoDisponible(str(error)) from error
    return bool(marcado)


def desencolar(cliente: redis.Redis, cola: str, timeout: int = 5) -> Trabajo | None:
    """Retira el trabajo más antiguo (BLPOP, bloqueante hasta `timeout` segundos). None si no
    llegó nada en ese tiempo, ya sea porque Redis devolvió nil o porque el socket del cliente
    expiró esperando esa respuesta (mismo caso desde el punto de vista del dominio)."""
    try:
        resultado = cliente.blpop(cola, timeout=timeout)
    except redis.exceptions.TimeoutError:
        return None
    if resultado is None:
        return None
    _, crudo = resultado
    datos = json.loads(crudo)
    return Trabajo(id=datos["id"], payload=datos["payload"])
