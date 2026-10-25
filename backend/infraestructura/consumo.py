"""El lado del consumidor de la cola: acuse de recibo, reintentos con espera creciente y lista de
fallidos (taller de mensajería, ADR-0020).

**La garantía: al menos una vez.** Antes el worker retiraba el trabajo con `BLPOP`, y si moría a
mitad lo perdía (MF-06, R-22): como mucho una vez. Ahora `tomar` lo mueve, en un solo paso
atómico de Redis (`BLMOVE`), de la cola a una lista de trabajos **en curso**, y solo sale de ahí
con el acuse (`confirmar`), con un reintento programado o con su paso a la lista de fallidos. Si
el worker muere en medio, el trabajo sigue en curso, y `recuperar_en_curso` lo devuelve a la cola
cuando el worker vuelve a arrancar. Eso puede entregarlo dos veces; la marca de
`cola.marcar_procesado`, puesta después de procesar, hace que la segunda solo se confirme.

**Las cuatro listas de una cola** (para `procesamiento`):

- `procesamiento`, una lista: los trabajos por tomar, en orden.
- `procesamiento:en-curso`, una lista: los que el worker tomó y todavía no confirmó.
- `procesamiento:reintentos`, un conjunto ordenado: los que fallaron y esperan, ordenados por la
  hora de su próximo intento.
- `procesamiento:fallidos`, una lista: los que no se pueden procesar, con el motivo, para que una
  persona los revise.

**La política de reintentos.** Un fallo recuperable (la imagen no se pudo leer) se reintenta
hasta completar `MAXIMO_DE_INTENTOS`, con una espera que se duplica en cada intento y una variación
al azar de hasta el 20 % para que varios fallos simultáneos no vuelvan todos a la vez: unos 5, 10 y
20 s. Un fallo permanente (un mensaje que no cumple el contrato) va directo a fallidos: volver a
leer el mismo texto da el mismo error. La espera no se hace con un `sleep` en el worker, que lo
bloquearía y se perdería si muere: el trabajo se guarda en el conjunto de reintentos, en Redis, y
`mover_reintentos_vencidos` lo devuelve a la cola cuando llega su hora.

**Supone un solo consumidor.** `recuperar_en_curso` devuelve a la cola todo lo que está en curso,
lo que es correcto porque hay un solo worker (ADR-0011): lo que está en curso cuando arranca es lo
que dejó a medias. Con dos workers, uno le quitaría al otro lo que está procesando (R-29).

Las operaciones que mueven un trabajo entre dos listas son atómicas (`BLMOVE`, `LMOVE` o una
transacción `MULTI`): un trabajo nunca queda en dos sitios ni en ninguno.
"""

import json
import random
import time
from collections.abc import Callable
from dataclasses import replace
from datetime import datetime, timezone
from typing import cast

import redis

from infraestructura.cola import (
    MensajeInvalido,
    Trabajo,
    leer_trabajo,
    serializar_trabajo,
    texto,
)

__all__ = [
    "MAXIMO_DE_INTENTOS",
    "ESPERA_BASE_SEGUNDOS",
    "VARIACION_DE_LA_ESPERA",
    "clave_en_curso",
    "clave_reintentos",
    "clave_fallidos",
    "espera_antes_del_intento",
    "tomar",
    "confirmar",
    "reintentar_mas_tarde",
    "mover_reintentos_vencidos",
    "enviar_a_fallidos",
    "recuperar_en_curso",
    "reencolar_fallidos",
    "estado_de_la_cola",
]

# Cuatro intentos en total: el primero y tres reintentos, con esperas de unos 5, 10 y 20 s. Un
# fallo que dura más de medio minuto ya no es un parpadeo, y es mejor que lo vea una persona en la
# lista de fallidos que seguir insistiendo.
MAXIMO_DE_INTENTOS = 4
ESPERA_BASE_SEGUNDOS = 5.0
VARIACION_DE_LA_ESPERA = 0.2


def clave_en_curso(cola: str) -> str:
    return f"{cola}:en-curso"


def clave_reintentos(cola: str) -> str:
    return f"{cola}:reintentos"


def clave_fallidos(cola: str) -> str:
    return f"{cola}:fallidos"


def espera_antes_del_intento(intento: int, azar: Callable[[], float] = random.random) -> float:
    """Segundos de espera antes del intento número `intento` (2, 3, 4…): la base, duplicada en
    cada intento, más una variación al azar de hasta `VARIACION_DE_LA_ESPERA`."""
    base = ESPERA_BASE_SEGUNDOS * 2 ** (intento - 2)
    return base * (1 + VARIACION_DE_LA_ESPERA * azar())


def tomar(cliente: redis.Redis, cola: str, timeout: int = 5) -> str | None:
    """Mueve el trabajo más antiguo de la cola a la lista en curso y lo devuelve tal cual, como
    texto (`BLMOVE`, bloqueante hasta `timeout` segundos). None si no llegó nada.

    Devuelve el texto y no un `Trabajo` porque el acuse tiene que quitar de la lista en curso
    exactamente lo que se puso, y porque un texto que no cumple el contrato también hay que poder
    sacarlo de ahí, hacia fallidos."""
    crudo = cliente.blmove(cola, clave_en_curso(cola), timeout, "LEFT", "RIGHT")
    return None if crudo is None else texto(crudo)


def confirmar(cliente: redis.Redis, cola: str, crudo: str) -> None:
    """El acuse: el trabajo terminó y sale de la lista en curso."""
    cliente.lrem(clave_en_curso(cola), 1, crudo)


def reintentar_mas_tarde(
    cliente: redis.Redis,
    cola: str,
    crudo: str,
    trabajo: Trabajo,
    espera_segundos: float,
    ahora: float | None = None,
) -> Trabajo:
    """Programa el siguiente intento: el trabajo, con `intento` + 1 y el mismo `id`, entra al
    conjunto de reintentos con la hora en que vence, y sale de la lista en curso. Las dos cosas
    en una transacción. Devuelve el trabajo tal como se va a reintentar."""
    siguiente = replace(trabajo, intento=trabajo.intento + 1)
    vence = (time.time() if ahora is None else ahora) + espera_segundos
    with cliente.pipeline(transaction=True) as tuberia:
        tuberia.zadd(clave_reintentos(cola), {serializar_trabajo(siguiente): vence})
        tuberia.lrem(clave_en_curso(cola), 1, crudo)
        tuberia.execute()
    return siguiente


def mover_reintentos_vencidos(cliente: redis.Redis, cola: str, ahora: float | None = None) -> int:
    """Devuelve a la cola los reintentos cuya hora ya llegó. Cada uno sale del conjunto y entra a
    la cola en una sola transacción. Devuelve cuántos movió."""
    momento = time.time() if ahora is None else ahora
    # Sin `withscores`, redis-py devuelve solo los miembros; el tipo de la biblioteca no lo dice.
    vencidos = [
        texto(cast(str, miembro))
        for miembro in cliente.zrangebyscore(clave_reintentos(cola), "-inf", momento)
    ]
    for crudo in vencidos:
        with cliente.pipeline(transaction=True) as tuberia:
            tuberia.zrem(clave_reintentos(cola), crudo)
            tuberia.rpush(cola, crudo)
            tuberia.execute()
    return len(vencidos)


def enviar_a_fallidos(
    cliente: redis.Redis, cola: str, crudo: str, motivo: str, intentos: int
) -> None:
    """Lleva el trabajo a la lista de fallidos, con el motivo y los intentos, y lo saca de la
    lista en curso, en una transacción. Se guarda el texto original tal cual, aunque no cumpla el
    contrato, para que quien lo revise vea exactamente lo que llegó."""
    registro = json.dumps(
        {
            "mensaje": crudo,
            "motivo": motivo,
            "intentos": intentos,
            "momento": datetime.now(timezone.utc).isoformat(),
        },
        ensure_ascii=False,
    )
    with cliente.pipeline(transaction=True) as tuberia:
        tuberia.rpush(clave_fallidos(cola), registro)
        tuberia.lrem(clave_en_curso(cola), 1, crudo)
        tuberia.execute()


def recuperar_en_curso(cliente: redis.Redis, cola: str) -> int:
    """Devuelve a la cabeza de la cola todo lo que quedó en curso: lo que el worker tomó y no
    alcanzó a confirmar antes de morir. Supone un solo consumidor (ver el docstring del módulo).
    Devuelve cuántos devolvió."""
    devueltos = 0
    while cliente.lmove(clave_en_curso(cola), cola, "RIGHT", "LEFT") is not None:
        devueltos += 1
    return devueltos


def reencolar_fallidos(cliente: redis.Redis, cola: str) -> int:
    """Devuelve a la cola los fallidos que cumplen el contrato, con el intento en 1, para cuando
    una persona corrigió la causa (por ejemplo, la imagen volvió al almacén). Los que no cumplen el
    contrato se quedan: reencolarlos los traería de vuelta al mismo lugar. Devuelve cuántos
    movió."""
    movidos = 0
    for registro in map(texto, cliente.lrange(clave_fallidos(cola), 0, -1)):
        try:
            trabajo = leer_trabajo(json.loads(registro)["mensaje"])
        except (MensajeInvalido, KeyError, ValueError):
            continue
        with cliente.pipeline(transaction=True) as tuberia:
            tuberia.lrem(clave_fallidos(cola), 1, registro)
            tuberia.rpush(cola, serializar_trabajo(replace(trabajo, intento=1)))
            tuberia.execute()
        movidos += 1
    return movidos


def estado_de_la_cola(cliente: redis.Redis, cola: str) -> dict[str, int]:
    """Cuántos trabajos hay en cada una de las cuatro listas de la cola."""
    return {
        "pendientes": cliente.llen(cola),
        "en_curso": cliente.llen(clave_en_curso(cola)),
        "esperando_reintento": cliente.zcard(clave_reintentos(cola)),
        "fallidos": cliente.llen(clave_fallidos(cola)),
    }
