"""Adaptador minimalista de cola sobre Redis: una lista FIFO, sin reintentos ni acuses de
recibo. Es el germen de lo que EC-07 (confirmación fiable de recepción del lote) va a exigir
más adelante, no una cola de producción."""

import json
import os
import uuid
from dataclasses import asdict, dataclass

import redis
# Se importa el submódulo explícitamente: `redis.exceptions` solo queda disponible como
# efecto secundario de los imports internos de redis-py, y depender de eso es frágil.
import redis.exceptions


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


def cliente_redis(url: str | None = None) -> redis.Redis:
    """Crea el cliente Redis a partir de REDIS_URL (o el valor pasado). `socket_timeout` se fija
    por encima del timeout de bloqueo que usa `desencolar` para que el socket no expire justo
    cuando el servidor está por responder nil al vencer el BLPOP."""
    return redis.Redis.from_url(
        url or os.environ["REDIS_URL"], decode_responses=True, socket_timeout=10
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
