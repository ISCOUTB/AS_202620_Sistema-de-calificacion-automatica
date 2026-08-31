"""Punto de entrada del worker: consume la cola de `infraestructura` en un ciclo. Comparte el
mismo código de dominio que la API (misma imagen, mismo proyecto); todavía no ejecuta el
pipeline de calificación (omr -> calificacion), solo confirma que la hoja que `ingesta` encoló
le llegó y que puede ubicarla en el almacén."""

import logging
import time

import redis
# Se importa el submódulo explícitamente: `redis.exceptions` solo queda disponible como
# efecto secundario de los imports internos de redis-py, y depender de eso es frágil.
import redis.exceptions

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
        if trabajo is None:
            continue

        datos = trabajo.payload
        # El siguiente paso de este trabajo es el aspecto A-02 (detección de marcas), que
        # todavía no existe. Registrarlo es, por ahora, el final del recorrido: es lo que hace
        # observable de punta a punta el corte vertical de A-01.
        logger.info(
            "Hoja recibida | trabajo=%s examen=%s archivo=%s referencia=%s",
            trabajo.id,
            datos.get("examen_id"),
            datos.get("nombre_archivo"),
            datos.get("referencia"),
        )


if __name__ == "__main__":
    ejecutar()
