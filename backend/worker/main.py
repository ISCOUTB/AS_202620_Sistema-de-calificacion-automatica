"""Punto de entrada del worker: consume la cola de `infraestructura` en un ciclo. Comparte el
mismo código de dominio que la API (misma imagen, mismo proyecto); todavía no ejecuta el
pipeline de calificación (omr -> calificacion): solo registra en su log el trabajo que `ingesta`
encoló, con la referencia de la hoja en el almacén, sin abrirla todavía.

Es idempotente (S11, ADR-0016): si el mismo trabajo llega dos veces, la segunda se registra como
`trabajo_repetido` y no se procesa. Hoy la marca se pone antes de procesar, porque procesar es
escribir una línea de log. Cuando A-02 procese la hoja de verdad, la marca tiene que pasar a
después de terminar, o una caída a mitad dejaría el trabajo marcado y sin hacer."""

import logging
import os
import time

import redis
# Se importa el submódulo explícitamente: `redis.exceptions` solo queda disponible como
# efecto secundario de los imports internos de redis-py, y depender de eso es frágil.
import redis.exceptions

from infraestructura.cola import ColaNoDisponible, cliente_redis, desencolar, primera_entrega
from infraestructura.registro import configurar_registro

configurar_registro()
logger = logging.getLogger("worker")

# Se lee del entorno, con el mismo valor por omisión que `api/settings.py`. Estuvo escrito
# aquí como literal mientras la API ya lo leía de `NOMBRE_COLA`: cambiar esa variable dejaba a
# la API encolando en una lista y al worker escuchando otra, con el docente viendo el lote
# confirmado y ninguna hoja procesada. Es el mismo modo de fallo que ADR-0006 ataca desde el
# otro lado, y por eso se corrige aquí.
NOMBRE_COLA = os.environ.get("NOMBRE_COLA", "procesamiento")
ESPERA_TRAS_ERROR_SEGUNDOS = 5


def ejecutar() -> None:
    cliente = cliente_redis()
    logger.info(
        "Worker escuchando la cola", extra={"evento": "worker_iniciado", "cola": NOMBRE_COLA}
    )
    while True:
        try:
            trabajo = desencolar(cliente, NOMBRE_COLA, timeout=5)
        except redis.exceptions.RedisError as error:
            logger.warning(
                "Fallo transitorio de Redis, reintentando",
                extra={"evento": "fallo_de_la_cola", "error": str(error)},
            )
            time.sleep(ESPERA_TRAS_ERROR_SEGUNDOS)
            continue
        if trabajo is None:
            continue

        datos = trabajo.payload
        if not _es_primera_entrega(cliente, trabajo.id):
            logger.info(
                "Trabajo repetido, no se procesa otra vez",
                extra={
                    "evento": "trabajo_repetido",
                    "trabajo": trabajo.id,
                    "hoja": datos.get("hoja_id"),
                    "examen": datos.get("examen_id"),
                },
            )
            continue

        # El siguiente paso de este trabajo es el aspecto A-02 (detección de marcas), que
        # todavía no existe. Registrarlo es, por ahora, el final del recorrido: es lo que hace
        # observable de punta a punta el corte vertical de A-01.
        logger.info(
            "Hoja recibida",
            extra={
                "evento": "hoja_recibida",
                "trabajo": trabajo.id,
                "hoja": datos.get("hoja_id"),
                "examen": datos.get("examen_id"),
                "archivo": datos.get("nombre_archivo"),
                "referencia": datos.get("referencia"),
            },
        )


def _es_primera_entrega(cliente, trabajo_id: str) -> bool:
    """Si no se puede comprobar porque Redis falló justo ahí, el trabajo se procesa igual: el
    trabajo ya salió de la cola, así que descartarlo sería perder la hoja, y procesarla dos veces
    es el mal menor que la marca existe para evitar, no uno peor."""
    try:
        return primera_entrega(cliente, trabajo_id)
    except ColaNoDisponible as error:
        logger.warning(
            "No se pudo comprobar si el trabajo es repetido; se procesa",
            extra={
                "evento": "idempotencia_sin_comprobar",
                "trabajo": trabajo_id,
                "error": str(error),
            },
        )
        return True


if __name__ == "__main__":
    ejecutar()
