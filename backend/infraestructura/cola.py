"""Adaptador minimalista de cola sobre Redis: una lista FIFO, sin reintentos ni acuses de
recibo. Basta para lo que EC-07 mide, la recepción; el acuse de recibo que exigirá procesar
cada hoja sin perderla es trabajo de A-02, así que no es todavía una cola de producción.

El contrato del mensaje (ADR-0020)
----------------------------------
Lo que viaja por la cola es un `Trabajo` serializado en JSON, versión `VERSION_DEL_TRABAJO`. Su
forma exacta está en `ESQUEMA_DEL_TRABAJO`, que `herramientas.exportar_contrato` publica en
`docs/contrato/trabajo-v1.schema.json`. El criterio de compatibilidad:

- **Agregar** un campo opcional no cambia la versión: quien lee ignora lo que no conoce
  (`leer_trabajo` es un lector tolerante).
- **Quitar, renombrar o cambiar el tipo o el significado** de un campo obligatorio es una
  versión nueva. Quien lee rechaza las versiones que no conoce (`MensajeInvalido`): reintentar
  el mismo texto no lo arreglaría.
- Un mensaje **anterior al contrato** (sin `version`, publicado antes del taller y todavía en la
  cola tras un despliegue) se lee como versión 1; si no trae `hoja_id`, su `id` hace de hoja,
  la misma regla que la bitácora sigue desde ADR-0018.

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
from datetime import datetime, timezone
from typing import Any

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

# Dónde está Redis si no lo dice `REDIS_URL`. Es el mismo valor para la API y para el worker, y
# por eso se declara una sola vez aquí, que es lo que los dos importan (la lección de V-2 con
# `NOMBRE_COLA`): antes la API caía en este valor y el worker moría con `KeyError`.
REDIS_URL_POR_OMISION = "redis://localhost:6379/0"

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


# La versión del contrato del mensaje. Sube solo con un cambio incompatible (ver el docstring).
VERSION_DEL_TRABAJO = 1
TIPO_HOJA_RECIBIDA = "hoja_recibida"


class MensajeInvalido(ValueError):
    """Lo que llegó por la cola no cumple el contrato, o es de una versión que no se conoce.

    Es un error permanente: volver a leer el mismo texto da el mismo resultado, así que el
    consumidor lo manda a la lista de fallidos sin reintentarlo."""


@dataclass
class Trabajo:
    """El mensaje que viaja por la cola: un sobre con identidad, versión e intento, y el payload.

    `id` es el del encargo (el `trabajo_id`); la identidad de la hoja viaja en el payload, como
    `hoja_id` (ADR-0018). `emitido_en` es el momento en que el productor lo acuñó, y sirve para
    medir cuánto esperó en la cola. `intento` empieza en 1 y lo sube el consumidor cada vez que
    programa un reintento (ADR-0020)."""

    id: str
    payload: dict
    version: int = VERSION_DEL_TRABAJO
    tipo: str = TIPO_HOJA_RECIBIDA
    emitido_en: str = ""
    intento: int = 1


# El contrato del mensaje, versión 1, como JSON Schema. Es la fuente: el archivo de
# `docs/contrato/` se genera desde aquí y una prueba comprueba que no se separen.
ESQUEMA_DEL_TRABAJO: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "urn:quantia:contrato:trabajo:v1",
    "title": "Trabajo de la cola de procesamiento, versión 1",
    "description": (
        "Mensaje que la API publica en la cola por cada hoja aceptada y que el worker consume "
        "(ADR-0002, ADR-0020). Compatibilidad: agregar un campo opcional no cambia la versión, y "
        "quien lee ignora lo que no conoce; quitar, renombrar o cambiar el tipo de un campo "
        "obligatorio es una versión nueva, y quien lee rechaza las que no conoce."
    ),
    "type": "object",
    "required": ["id", "version", "tipo", "emitido_en", "intento", "payload"],
    "properties": {
        "id": {
            "type": "string",
            "format": "uuid",
            "description": "Identidad del encargo (trabajo_id). La conserva cada reintento.",
        },
        "version": {"const": VERSION_DEL_TRABAJO, "description": "Versión de este contrato."},
        "tipo": {"const": TIPO_HOJA_RECIBIDA, "description": "Qué pide el mensaje."},
        "emitido_en": {
            "type": "string",
            "format": "date-time",
            "description": "Cuándo lo acuñó el productor, en UTC.",
        },
        "intento": {
            "type": "integer",
            "minimum": 1,
            "description": "Número de intento. 1 al publicarse; lo sube cada reintento.",
        },
        "payload": {
            "type": "object",
            "required": ["hoja_id", "examen_id", "referencia", "nombre_archivo"],
            "properties": {
                "hoja_id": {
                    "type": "string",
                    "description": "Identidad de la hoja (ADR-0018), distinta de la del trabajo.",
                },
                "examen_id": {"type": "string"},
                "referencia": {
                    "type": "string",
                    "description": "Dónde está la imagen en el almacén. Opaca para el consumidor.",
                },
                "nombre_archivo": {"type": "string"},
            },
        },
    },
}




def cliente_redis(
    url: str | None = None, espera_segundos: float = ESPERA_AL_CONSUMIR_SEGUNDOS
) -> redis.Redis:
    """Crea el cliente Redis a partir del valor pasado, o de `REDIS_URL`, o de
    `REDIS_URL_POR_OMISION` si no hay ninguno.

    `espera_segundos` es el `socket_timeout`: cuánto se espera una respuesta antes de rendirse.
    Por omisión es la del worker, por encima del timeout de bloqueo que usa `desencolar` para que
    el socket no expire justo cuando el servidor está por responder nil al vencer el BLPOP. La API
    pasa `ESPERA_AL_PUBLICAR_SEGUNDOS`. La conexión se rinde en `ESPERA_DE_CONEXION_SEGUNDOS` y
    el cliente no reintenta en ningún caso (ver el docstring del módulo)."""
    return redis.Redis.from_url(
        url or os.environ.get("REDIS_URL", REDIS_URL_POR_OMISION),
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
    return Trabajo(
        id=str(uuid.uuid4()),
        payload=payload,
        emitido_en=datetime.now(timezone.utc).isoformat(),
    )


def texto(valor: str | bytes) -> str:
    """Lo que devuelve redis-py, como texto. Los clientes de `cliente_redis` ya devuelven `str`
    (`decode_responses=True`); esto existe para que los tipos lo digan y para quien pase otro."""
    return valor.decode("utf-8") if isinstance(valor, bytes) else valor


def serializar_trabajo(trabajo: Trabajo) -> str:
    """El texto que viaja por la cola: el `Trabajo` entero, en JSON."""
    return json.dumps(asdict(trabajo), ensure_ascii=False)


def leer_trabajo(crudo: str) -> Trabajo:
    """Lee un mensaje de la cola con el criterio de compatibilidad del contrato.

    Ignora los campos que no conoce, lee como versión 1 el mensaje sin `version` y le da su `id`
    como `hoja_id` al que no la trae. Levanta `MensajeInvalido` si no es JSON, si le falta un
    campo obligatorio o si su versión no es una que este consumidor conozca."""
    try:
        datos = json.loads(crudo)
    except (TypeError, ValueError) as error:
        raise MensajeInvalido("No es JSON.") from error
    if not isinstance(datos, dict):
        raise MensajeInvalido("No es un objeto JSON.")
    version = datos.get("version", VERSION_DEL_TRABAJO)
    if version != VERSION_DEL_TRABAJO:
        raise MensajeInvalido(f"La versión {version!r} del contrato no se conoce.")
    identificador = datos.get("id")
    payload = datos.get("payload")
    if not isinstance(identificador, str) or not identificador:
        raise MensajeInvalido("Falta el id del trabajo.")
    if not isinstance(payload, dict):
        raise MensajeInvalido("Falta el payload.")
    if not isinstance(payload.get("referencia"), str):
        raise MensajeInvalido("Falta la referencia de la hoja en el almacén.")
    intento = datos.get("intento", 1)
    if not isinstance(intento, int) or intento < 1:
        raise MensajeInvalido(f"El intento {intento!r} no es un entero positivo.")
    return Trabajo(
        id=identificador,
        payload={**payload, "hoja_id": payload.get("hoja_id") or identificador},
        version=VERSION_DEL_TRABAJO,
        tipo=datos.get("tipo", TIPO_HOJA_RECIBIDA),
        emitido_en=datos.get("emitido_en", ""),
        intento=intento,
    )




def publicar(cliente: redis.Redis, cola: str, trabajo: Trabajo) -> Trabajo:
    """Agrega un trabajo ya acuñado al final de la cola (RPUSH, FIFO).

    Traduce cualquier fallo de redis-py a `ColaNoDisponible` para que quien llame no tenga que
    importar `redis` solo para atraparlo."""
    try:
        cliente.rpush(cola, serializar_trabajo(trabajo))
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
    llegó nada en ese tiempo.

    **Un `TimeoutError` del cliente no es una cola vacía, y sube como error.** Con la espera del
    worker por encima del bloqueo del `BLPOP` (ADR-0016), Redis siempre contesta antes de que
    venza el socket, con un trabajo o con nil. Si el socket vence igual, es que Redis no contesta
    o que la conexión no se pudo abrir (en Windows, un `localhost` sin servidor da `TimeoutError`
    y no `ConnectionError`). Antes se devolvía None, y una cola caída se veía como un worker sin
    trabajo, sin aviso ni pausa; y si Redis ya había sacado el trabajo cuando la respuesta llegó
    tarde, se perdía sin dejar rastro. Ahora el error llega al worker, que lo registra como
    `fallo_de_la_cola` y espera antes de volver a pedir."""
    resultado = cliente.blpop(cola, timeout=timeout)
    if resultado is None:
        return None
    _, crudo = resultado
    return leer_trabajo(texto(crudo))
