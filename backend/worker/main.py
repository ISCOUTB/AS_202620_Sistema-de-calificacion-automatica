"""Punto de entrada del worker: consume la cola de `infraestructura` en un ciclo. Comparte el
mismo código de dominio que la API (misma imagen, mismo proyecto); todavía no ejecuta el
pipeline de calificación (omr -> calificacion): abre la imagen de la hoja que `ingesta` encoló,
para comprobar que está, y registra el trabajo en su log.

Es idempotente (S11, ADR-0016): si el mismo trabajo llega dos veces, la segunda se registra como
`trabajo_repetido` y no se procesa.

**Desde el taller de mensajería (ADR-0020) consume con acuse, reintentos y lista de fallidos**,
con lo que pasa de entregar como mucho una vez a entregar al menos una vez:

1. Al arrancar, y después de cada fallo de Redis, devuelve a la cola lo que quedó en curso.
2. En cada vuelta, devuelve a la cola los reintentos cuya hora llegó y toma un trabajo, que queda
   en la lista en curso hasta el acuse (`consumo.tomar`).
3. Si el mensaje no cumple el contrato, va a la lista de fallidos sin reintentarse.
4. Si ya se procesó, se registra como repetido y se confirma.
5. Si la imagen no se puede leer, es un fallo recuperable: se programa un reintento con espera
   creciente, o, agotados los intentos, va a la lista de fallidos con el motivo.
6. Si sale bien, se registra, se marca como procesado y, solo entonces, se confirma. La marca va
   antes del acuse para que, si el worker muere entre los dos, la entrega que vuelve se confirme
   sin procesarse otra vez.

Todos los eventos llevan `trabajo` y `hoja`, los mismos que el productor registra al publicar
(`trabajo_publicado`, en `ingesta`): con eso se sigue un mensaje de punta a punta en el registro,
y `herramientas/seguir_trabajo.py` lo hace a partir del log."""

import logging
import os
import random
import time
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

import redis
# Se importa el submódulo explícitamente: `redis.exceptions` solo queda disponible como
# efecto secundario de los imports internos de redis-py, y depender de eso es frágil.
import redis.exceptions

from infraestructura.almacen import RUTA_ALMACEN_POR_OMISION, AlmacenDeImagenes, AlmacenEnDisco
from infraestructura.cola import (
    MensajeInvalido,
    cliente_redis,
    leer_trabajo,
    marcar_procesado,
    ya_procesado,
)
from infraestructura.consumo import (
    MAXIMO_DE_INTENTOS,
    clave_reintentos,
    confirmar,
    enviar_a_fallidos,
    espera_antes_del_intento,
    mover_reintentos_vencidos,
    recuperar_en_curso,
    reintentar_mas_tarde,
    tomar,
)
from infraestructura.registro import configurar_registro

configurar_registro()
logger = logging.getLogger("worker")

# Se lee del entorno, con el mismo valor por omisión que `api/settings.py`. Estuvo escrito
# aquí como literal mientras la API ya lo leía de `NOMBRE_COLA`: cambiar esa variable dejaba a
# la API encolando en una lista y al worker escuchando otra, con el docente viendo el lote
# confirmado y ninguna hoja procesada. Es el mismo modo de fallo que ADR-0006 ataca desde el
# otro lado, y por eso se corrige aquí.
NOMBRE_COLA = os.environ.get("NOMBRE_COLA", "procesamiento")
RUTA_ALMACEN = os.environ.get("RUTA_ALMACEN", RUTA_ALMACEN_POR_OMISION)
ESPERA_TRAS_ERROR_SEGUNDOS = 5
# Cuánto bloquea `tomar` esperando un trabajo. Con reintentos programados se espera menos, para
# que uno vencido no tarde más de un segundo en volver a la cola.
ESPERA_DE_LA_TOMA_SEGUNDOS = 5
ESPERA_DE_LA_TOMA_CON_REINTENTOS_SEGUNDOS = 1

# Lo que puede devolver `atender_una_vez`.
NADA = "nada"
PROCESADO = "procesado"
REPETIDO = "repetido"
REINTENTO = "reintento"
FALLIDO = "fallido"


def ejecutar() -> None:
    cliente = cliente_redis()
    almacen = AlmacenEnDisco(Path(RUTA_ALMACEN))
    logger.info(
        "Worker escuchando la cola", extra={"evento": "worker_iniciado", "cola": NOMBRE_COLA}
    )
    recuperar = True
    while True:
        try:
            if recuperar:
                _recuperar(cliente, NOMBRE_COLA)
                recuperar = False
            atender_una_vez(cliente, NOMBRE_COLA, almacen)
        except redis.exceptions.RedisError as error:
            logger.warning(
                "Fallo transitorio de Redis, reintentando",
                extra={"evento": "fallo_de_la_cola", "error": str(error)},
            )
            time.sleep(ESPERA_TRAS_ERROR_SEGUNDOS)
            # Lo que estaba en curso cuando Redis falló no se pudo confirmar ni reintentar.
            recuperar = True


def _recuperar(cliente: redis.Redis, cola: str) -> None:
    devueltos = recuperar_en_curso(cliente, cola)
    if devueltos:
        logger.warning(
            "Trabajos que quedaron en curso vuelven a la cola",
            extra={"evento": "trabajos_recuperados", "cola": cola, "cantidad": devueltos},
        )


def atender_una_vez(
    cliente: redis.Redis,
    cola: str,
    almacen: AlmacenDeImagenes,
    reloj: Callable[[], float] = time.time,
    azar: Callable[[], float] = random.random,
) -> str:
    """Una vuelta del ciclo: mueve los reintentos vencidos, toma un trabajo y lo atiende.
    Devuelve qué pasó (`NADA`, `PROCESADO`, `REPETIDO`, `REINTENTO` o `FALLIDO`).

    Los errores de Redis suben: el ciclo de `ejecutar` los registra, espera y recupera lo que
    quedó en curso. `reloj` y `azar` existen para que las pruebas controlen el tiempo y la
    variación de la espera."""
    mover_reintentos_vencidos(cliente, cola, reloj())
    espera = (
        ESPERA_DE_LA_TOMA_CON_REINTENTOS_SEGUNDOS
        if cliente.zcard(clave_reintentos(cola))
        else ESPERA_DE_LA_TOMA_SEGUNDOS
    )
    crudo = tomar(cliente, cola, espera)
    if crudo is None:
        return NADA

    try:
        trabajo = leer_trabajo(crudo)
    except MensajeInvalido as error:
        enviar_a_fallidos(cliente, cola, crudo, str(error), intentos=1)
        logger.error(
            "Mensaje fuera del contrato, a la lista de fallidos",
            extra={"evento": "trabajo_a_fallidos", "motivo": str(error), "intentos": 1},
        )
        return FALLIDO

    datos = trabajo.payload
    rastro = {"trabajo": trabajo.id, "hoja": datos.get("hoja_id"), "intento": trabajo.intento}
    logger.info(
        "Trabajo tomado",
        extra={
            "evento": "trabajo_tomado",
            **rastro,
            "examen": datos.get("examen_id"),
            "espera_en_cola_ms": _milisegundos_desde(trabajo.emitido_en),
        },
    )

    if ya_procesado(cliente, trabajo.id):
        confirmar(cliente, cola, crudo)
        logger.info(
            "Trabajo repetido, no se procesa otra vez",
            extra={"evento": "trabajo_repetido", **rastro, "examen": datos.get("examen_id")},
        )
        return REPETIDO

    try:
        contenido = almacen.leer(datos["referencia"])
    except ValueError as error:
        enviar_a_fallidos(cliente, cola, crudo, str(error), intentos=trabajo.intento)
        logger.error(
            "Referencia inválida, a la lista de fallidos",
            extra={"evento": "trabajo_a_fallidos", **rastro, "motivo": str(error)},
        )
        return FALLIDO
    except OSError as error:
        motivo = f"No se pudo leer la imagen: {type(error).__name__}: {error}"
        if trabajo.intento >= MAXIMO_DE_INTENTOS:
            enviar_a_fallidos(cliente, cola, crudo, motivo, intentos=trabajo.intento)
            logger.error(
                "Intentos agotados, a la lista de fallidos",
                extra={"evento": "trabajo_a_fallidos", **rastro, "motivo": motivo},
            )
            return FALLIDO
        espera_s = espera_antes_del_intento(trabajo.intento + 1, azar)
        reintentar_mas_tarde(cliente, cola, crudo, trabajo, espera_s, ahora=reloj())
        logger.warning(
            "Fallo recuperable, reintento programado",
            extra={
                "evento": "reintento_programado",
                **rastro,
                "siguiente_intento": trabajo.intento + 1,
                "espera_s": round(espera_s, 1),
                "motivo": motivo,
            },
        )
        return REINTENTO

    # El siguiente paso de este trabajo es el aspecto A-02 (detección de marcas), que
    # todavía no existe. Registrarlo es, por ahora, el final del recorrido: es lo que hace
    # observable de punta a punta el corte vertical de A-01.
    logger.info(
        "Hoja recibida",
        extra={
            "evento": "hoja_recibida",
            **rastro,
            "examen": datos.get("examen_id"),
            "archivo": datos.get("nombre_archivo"),
            "referencia": datos.get("referencia"),
            "bytes": len(contenido),
        },
    )
    marcar_procesado(cliente, trabajo.id)
    confirmar(cliente, cola, crudo)
    return PROCESADO


def _milisegundos_desde(momento_iso: str) -> float | None:
    """Cuánto pasó desde `momento_iso` hasta ahora, o None si el mensaje no lo trae (los
    anteriores al contrato) o no se puede leer."""
    try:
        momento = datetime.fromisoformat(momento_iso)
    except (TypeError, ValueError):
        return None
    return round((datetime.now(timezone.utc) - momento).total_seconds() * 1000, 1)


if __name__ == "__main__":
    ejecutar()
