"""Punto de entrada del worker: consume la cola de `infraestructura` en un ciclo. Comparte el
mismo código de dominio que la API (misma imagen, mismo proyecto). Por cada trabajo abre la imagen
de la hoja que `ingesta` encoló, `omr` la lee, `calificacion` la califica contra la clave del
examen, y el resultado queda en el registro de resultados (A-02 y A-03).

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
6. La hoja se lee y se califica (`leer_y_calificar`). Una hoja ilegible o sin clave también
   termina aquí: queda registrada con su estado y su motivo, y no se reintenta. Un fallo de disco
   al leer la clave o al guardar el resultado es recuperable, como el del paso 5. Cualquier otro
   error va a fallidos: reintentarlo daría lo mismo.
7. Si sale bien, se marca como procesado y, solo entonces, se confirma. La marca va antes del
   acuse para que, si el worker muere entre los dos, la entrega que vuelve se confirme sin
   procesarse otra vez. Si muere después de guardar el resultado y antes de la marca, la entrega
   que vuelve deja un segundo hecho del mismo trabajo, igual al primero: el registro es de solo
   agregado y el último hecho de la hoja es el que vale.

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

from calificacion import ClaveIncompatible, ClaveNoHabilitada, calificar
from infraestructura.almacen import RUTA_ALMACEN_POR_OMISION, AlmacenDeImagenes, AlmacenEnDisco
from infraestructura.claves import (
    RUTA_CLAVES_POR_OMISION,
    ClaveMalEscrita,
    ClavesEnDisco,
    FuenteDeClaves,
)
from infraestructura.cola import (
    MensajeInvalido,
    Trabajo,
    cliente_redis,
    leer_trabajo,
    marcar_procesado,
    ya_procesado,
)
from infraestructura.consumo import (
    MAXIMO_DE_INTENTOS,
    MOTIVO_EL_WORKER_MURIO,
    clave_reintentos,
    confirmar,
    enviar_a_fallidos,
    espera_antes_del_intento,
    mover_reintentos_vencidos,
    recuperar_en_curso,
    reintentar_mas_tarde,
    tomar,
)
from infraestructura.modelo import ILEGIBLE, POR_REVISAR, CalificacionDeHoja
from infraestructura.registro import configurar_registro
from infraestructura.resultados import (
    CLAVE_MAL_ESCRITA,
    CLAVE_SIN_HABILITAR,
    RUTA_RESULTADOS_POR_OMISION,
    SIN_CLAVE,
    RegistroDeResultados,
    ResultadosEnDisco,
    estado_tras_la_lectura,
)
from omr import LecturaImposible, comprobar_umbral_de_confianza, leer_hoja_con_recortes

configurar_registro()
logger = logging.getLogger("worker")

# Se lee del entorno, con el mismo valor por omisión que `api/settings.py`. Estuvo escrito
# aquí como literal mientras la API ya lo leía de `NOMBRE_COLA`: cambiar esa variable dejaba a
# la API encolando en una lista y al worker escuchando otra, con el docente viendo el lote
# confirmado y ninguna hoja procesada. Es el mismo modo de fallo que ADR-0006 ataca desde el
# otro lado, y por eso se corrige aquí.
NOMBRE_COLA = os.environ.get("NOMBRE_COLA", "procesamiento")
RUTA_ALMACEN = os.environ.get("RUTA_ALMACEN", RUTA_ALMACEN_POR_OMISION)
# Lo que necesita la lectura y la calificación (fase 2 del OMR). El umbral es configuración y
# no un literal de `omr`: R-04 lo declara supuesto, y calibrarlo no debe pedir un despliegue de
# código. 70 es el valor inicial de EC-02. Se comprueba aquí, al arrancar: un valor fuera de la
# regla detiene el worker con un mensaje claro, en vez de dejar ilegible cada hoja.
RUTA_CLAVES = os.environ.get("RUTA_CLAVES", RUTA_CLAVES_POR_OMISION)
RUTA_RESULTADOS = os.environ.get("RUTA_RESULTADOS", RUTA_RESULTADOS_POR_OMISION)
UMBRAL_DE_CONFIANZA = comprobar_umbral_de_confianza(
    int(os.environ.get("OMR_UMBRAL_DE_CONFIANZA", "70"))
)
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
    claves = ClavesEnDisco(Path(RUTA_CLAVES))
    resultados = ResultadosEnDisco(Path(RUTA_RESULTADOS))
    logger.info(
        "Worker escuchando la cola", extra={"evento": "worker_iniciado", "cola": NOMBRE_COLA}
    )
    recuperar = True
    while True:
        try:
            if recuperar:
                _recuperar(cliente, NOMBRE_COLA)
                recuperar = False
            atender_una_vez(cliente, NOMBRE_COLA, almacen, claves, resultados)
        except redis.exceptions.RedisError as error:
            logger.warning(
                "Fallo transitorio de Redis, reintentando",
                extra={"evento": "fallo_de_la_cola", "error": str(error)},
            )
            time.sleep(ESPERA_TRAS_ERROR_SEGUNDOS)
            # Lo que estaba en curso cuando Redis falló no se pudo confirmar ni reintentar.
            recuperar = True


def _recuperar(cliente: redis.Redis, cola: str) -> None:
    """Lo que quedó en curso vuelve a la cola con un intento más, o a fallidos si ya los gastó
    (R-36): una hoja que mata al worker no lo vuelve a matar para siempre."""
    recuperacion = recuperar_en_curso(cliente, cola)
    if recuperacion.a_la_cola:
        logger.warning(
            "Trabajos que quedaron en curso vuelven a la cola",
            extra={
                "evento": "trabajos_recuperados",
                "cola": cola,
                "cantidad": recuperacion.a_la_cola,
            },
        )
    if recuperacion.a_fallidos:
        logger.error(
            "Trabajos que el worker no pudo terminar en ningún intento, a la lista de fallidos",
            extra={
                "evento": "trabajo_a_fallidos",
                "cola": cola,
                "cantidad": recuperacion.a_fallidos,
                "motivo": MOTIVO_EL_WORKER_MURIO,
            },
        )


def atender_una_vez(
    cliente: redis.Redis,
    cola: str,
    almacen: AlmacenDeImagenes,
    claves: FuenteDeClaves,
    resultados: RegistroDeResultados,
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
        return _reintentar_o_descartar(cliente, cola, crudo, trabajo, motivo, reloj, azar)

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
    try:
        leer_y_calificar(contenido, trabajo, claves, resultados, UMBRAL_DE_CONFIANZA, almacen)
    except OSError as error:
        motivo = f"No se pudo leer la clave o guardar el resultado: {type(error).__name__}: {error}"
        return _reintentar_o_descartar(cliente, cola, crudo, trabajo, motivo, reloj, azar)
    except Exception as error:
        # Un defecto del lector, o una imagen que lo hace fallar de una manera que nadie previó.
        # Dejarlo subir tumbaría el worker, y al arrancar recuperaría el mismo mensaje y volvería a
        # caer. Reintentarlo daría lo mismo. Va a fallidos con el motivo, y se reencola cuando el
        # defecto esté corregido (ADR-0020).
        motivo = f"Error inesperado al leer la hoja: {type(error).__name__}: {error}"
        enviar_a_fallidos(cliente, cola, crudo, motivo, intentos=trabajo.intento)
        logger.error(
            "Error inesperado al leer la hoja, a la lista de fallidos",
            extra={"evento": "trabajo_a_fallidos", **rastro, "motivo": motivo},
            exc_info=True,
        )
        return FALLIDO
    marcar_procesado(cliente, trabajo.id)
    confirmar(cliente, cola, crudo)
    return PROCESADO


def _reintentar_o_descartar(
    cliente: redis.Redis,
    cola: str,
    crudo: str,
    trabajo: Trabajo,
    motivo: str,
    reloj: Callable[[], float],
    azar: Callable[[], float],
) -> str:
    """Un fallo transitorio: reintento con espera creciente, o a fallidos si se agotaron los
    intentos (ADR-0020)."""
    rastro = {"trabajo": trabajo.id, "hoja": trabajo.payload.get("hoja_id"), "intento": trabajo.intento}
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


def leer_y_calificar(
    contenido: bytes,
    trabajo: Trabajo,
    claves: FuenteDeClaves,
    resultados: RegistroDeResultados,
    umbral_de_confianza: int,
    almacen: AlmacenDeImagenes | None = None,
) -> str:
    """El paso que sigue a abrir la imagen: `omr` lee, `calificacion` califica y el resultado
    queda en el registro. Devuelve el estado final de la hoja: `CALIFICADA`, `EN_REVISION`,
    `SIN_CLAVE_HABILITADA` o `ILEGIBLE`.

    - Con `almacen`, la fila de cada pregunta en revisión se guarda recortada en el almacén, y el
      registro anota dónde quedó: es lo que el profesor mira para resolverla (RF-08). El recorte
      no muestra el código del estudiante. Un `OSError` al guardarlo es transitorio, como el de
      escribir el registro.

    - Una `LecturaImposible` no se reintenta: leer otra vez la misma imagen da lo mismo. Se
      registra con su motivo y la hoja queda `ILEGIBLE`.
    - Sin clave, con la clave sin habilitar o mal escrita (sin la forma de una clave, o que no
      cabe en la hoja), la lectura se guarda igual y la hoja queda `SIN_CLAVE_HABILITADA`, con el
      motivo. Calificarla cuando la clave esté lista es un trabajo nuevo de la misma hoja
      (ADR-0018, punto 2).
    - Un `OSError` al leer la clave o al escribir el registro es transitorio y sube, para que
      `atender_una_vez` lo trate como el de leer la imagen: reintento con espera creciente
      (ADR-0020).
    - El evento del log, `hoja_procesada`, lleva `trabajo`, `hoja`, el estado, la nota en
      décimas, cuántas preguntas quedaron por revisar y lo que tardó la lectura. **Nunca el
      código del estudiante.**

    `atender_una_vez` la llama después del evento `hoja_recibida` y antes de `marcar_procesado`:
    si el registro falla, el trabajo no se confirma y vuelve a entregarse."""
    datos = trabajo.payload
    # Un mensaje anterior a ADR-0018 no trae `hoja_id`: entonces el trabajo era la hoja, la misma
    # regla con que la bitácora lee sus líneas viejas.
    hoja_id = datos.get("hoja_id") or trabajo.id
    examen_id = datos["examen_id"]
    rastro = {"trabajo": trabajo.id, "hoja": hoja_id, "intento": trabajo.intento}

    try:
        lectura, recortes = leer_hoja_con_recortes(contenido, umbral_de_confianza)
    except LecturaImposible as error:
        resultados.registrar_lectura_imposible(hoja_id, trabajo.id, examen_id, error.motivo)
        logger.warning(
            "Hoja ilegible, hay que volver a escanearla",
            extra={
                "evento": "hoja_procesada",
                **rastro,
                "examen": examen_id,
                "estado": ILEGIBLE,
                "motivo": error.motivo,
            },
        )
        return ILEGIBLE

    calificacion: CalificacionDeHoja | None = None
    motivo_sin_nota: str | None = None
    detalle: str | None = None
    try:
        clave = claves.clave_del_examen(examen_id)
        if clave is None:
            motivo_sin_nota = SIN_CLAVE
        else:
            calificacion = calificar(lectura, clave)
    except ClaveNoHabilitada:
        motivo_sin_nota = CLAVE_SIN_HABILITAR
    except (ClaveMalEscrita, ClaveIncompatible) as error:
        # El detalle dice qué corregir (un número de pregunta, una opción) y no trae datos del
        # estudiante: va al log, para quien arregle la clave.
        motivo_sin_nota, detalle = CLAVE_MAL_ESCRITA, str(error)

    referencias = (
        {}
        if almacen is None
        else {
            numero: almacen.guardar(examen_id, f"recorte-{hoja_id}-pregunta-{numero}.png", png)
            for numero, png in recortes.items()
        }
    )
    resultados.registrar_lectura(
        hoja_id, trabajo.id, examen_id, lectura, calificacion, motivo_sin_nota, referencias
    )
    estado = estado_tras_la_lectura(calificacion)
    evento = {
        "evento": "hoja_procesada",
        **rastro,
        "examen": examen_id,
        "estado": estado,
        "duracion_lectura_ms": round(lectura.duracion_ms, 1),
    }
    if calificacion is None:
        logger.warning(
            "Hoja leída sin nota: el examen no tiene una clave habilitada",
            extra={**evento, "motivo": motivo_sin_nota, "detalle": detalle},
        )
    else:
        logger.info(
            "Hoja leída y calificada",
            extra={
                **evento,
                "nota_en_decimas": calificacion.nota_en_decimas,
                "por_revisar": sum(
                    1 for resultado in calificacion.preguntas if resultado.veredicto == POR_REVISAR
                ),
                "codigo_por_revisar": calificacion.codigo_por_revisar,
            },
        )
    return estado


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
