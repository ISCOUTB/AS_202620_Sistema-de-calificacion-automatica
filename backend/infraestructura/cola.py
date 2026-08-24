"""Adaptador minimalista de cola sobre Redis: una lista FIFO, sin reintentos ni acuses de
recibo. Es el germen de lo que EC-07 (confirmación fiable de recepción del lote) va a exigir
más adelante, no una cola de producción."""

import json
import os
import uuid
from dataclasses import asdict, dataclass

import redis


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


def encolar(cliente: redis.Redis, cola: str, payload: dict) -> Trabajo:
    """Agrega un trabajo al final de la cola (RPUSH, FIFO)."""
    trabajo = Trabajo(id=str(uuid.uuid4()), payload=payload)
    cliente.rpush(cola, json.dumps(asdict(trabajo)))
    return trabajo


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
