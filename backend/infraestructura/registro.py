"""Registro estructurado: una línea JSON por evento, para la API y para el worker.

Los dos procesos escribían texto libre (`logging.basicConfig` en el worker, el formato por
omisión de uvicorn en la API). Con texto libre, contar cuántas hojas quedaron pendientes o
cuánto tardó la confirmación de un lote exige una expresión regular por mensaje, y cualquier
cambio de redacción la rompe en silencio. Aquí cada evento sale con campos con nombre: el
mensaje para leerlo, y `evento` más los datos del caso para buscarlo y medirlo.

Quien registra pasa los campos con `extra`:

    logger.info("Lote confirmado", extra={"evento": "lote_confirmado", "hojas_aceptadas": 200})

y sale una línea como:

    {"momento": "2026-09-27T18:30:00.125+00:00", "nivel": "INFO", "registro": "api",
     "mensaje": "Lote confirmado", "evento": "lote_confirmado", "hojas_aceptadas": 200}

La salida es la de error estándar, como la de `logging` por omisión: así no se mezcla con lo que
algunas herramientas del repositorio imprimen como resultado (`medir_ec07.py` escribe su informe
JSON en la salida estándar). En Docker y en Render las dos salidas terminan en el mismo registro.

Solo usa la biblioteca estándar, así que `infraestructura` sigue sin importar a nadie.
"""

import json
import logging
import logging.config
from datetime import datetime, timezone

# Atributos que `logging` pone en todo registro. Lo que no esté aquí llegó por `extra` y es un
# campo del evento. Se calculan de un registro real en vez de copiarse de la documentación,
# porque cambian entre versiones de Python (3.12 agregó `taskName`).
_ATRIBUTOS_DE_LOGGING = set(vars(logging.makeLogRecord({}))) | {"message", "asctime"}

# Uvicorn repite algunos mensajes en `color_message`, con códigos de color para la terminal. En una
# línea JSON solo agregan ruido: el mensaje ya está en `mensaje`.
_CAMPOS_IGNORADOS = _ATRIBUTOS_DE_LOGGING | {"color_message"}


class FormateadorJSON(logging.Formatter):
    """Convierte cada registro en un objeto JSON de una sola línea."""

    def format(self, record: logging.LogRecord) -> str:
        linea = {
            "momento": datetime.fromtimestamp(record.created, timezone.utc).isoformat(
                timespec="milliseconds"
            ),
            "nivel": record.levelname,
            "registro": record.name,
            "mensaje": record.getMessage(),
        }
        for clave, valor in vars(record).items():
            if clave not in _CAMPOS_IGNORADOS and not clave.startswith("_"):
                linea[clave] = valor
        if record.exc_info:
            linea["excepcion"] = self.formatException(record.exc_info)
        # `default=str` para que un valor que no es JSON (una fecha, una ruta) salga como texto
        # en vez de tumbar el registro, que es lo último que puede fallar en un proceso.
        return json.dumps(linea, ensure_ascii=False, default=str)


# Los loggers de uvicorn se declaran aparte porque uvicorn los configura con su propio formato
# al arrancar, antes de importar la aplicación, y sin esto el acceso seguiría saliendo en texto.
CONFIGURACION: dict = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"json": {"()": FormateadorJSON}},
    "handlers": {
        "salida": {
            "class": "logging.StreamHandler",
            "formatter": "json",
            "stream": "ext://sys.stderr",
        }
    },
    "root": {"level": "INFO", "handlers": ["salida"]},
    "loggers": {
        nombre: {"level": "INFO", "handlers": ["salida"], "propagate": False}
        for nombre in ("uvicorn", "uvicorn.error", "uvicorn.access")
    },
}


def configurar_registro() -> None:
    """Aplica la configuración. La llaman los puntos de entrada (`api` y `worker`) al arrancar."""
    logging.config.dictConfig(CONFIGURACION)
