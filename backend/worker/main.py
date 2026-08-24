"""Punto de entrada del worker: consume la cola de `infraestructura` en un ciclo. Comparte el
mismo código de dominio que la API (misma imagen, mismo proyecto); todavía no ejecuta ningún
pipeline (omr -> calificacion), solo confirma que puede recibir trabajos encolados."""

import logging
import time

import redis

from infraestructura.cola import cliente_redis, desencolar

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("worker")

NOMBRE_COLA = "procesamiento"
ESPERA_TRAS_ERROR_SEGUNDOS = 5


def ejecutar() -> None:
    cliente = cliente_redis()
    logger.info("Worker escuchando la cola '%s'", NOMBRE_COLA)
    while True:
        try:
            trabajo = desencolar(cliente, NOMBRE_COLA, timeout=5)
        except redis.exceptions.RedisError as error:
            logger.warning("Fallo transitorio de Redis, reintentando: %s", error)
            time.sleep(ESPERA_TRAS_ERROR_SEGUNDOS)
            continue
        if trabajo is not None:
            logger.info("Trabajo recibido: %s", trabajo)


if __name__ == "__main__":
    ejecutar()
