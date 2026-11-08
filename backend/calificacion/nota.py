"""La nota de una hoja: la lectura comparada contra la clave habilitada (RF-04), y su recálculo
cuando el profesor resuelve lo que quedó en revisión (RF-08).

**La clave llega como parámetro.** `calificacion` no importa `autoria`, que es su dueña, ni sabe
dónde está guardada: el worker la busca con `infraestructura.claves` y se la pasa. Así las dos
funciones de este archivo son puras y se prueban sin disco.

**Reglas que siguen a la pantalla de revisión del frontend**, para que la nota del backend y la
que el docente ve no se contradigan:

- La nota va de 0 a 50 décimas: `puntos * 50 / puntos_posibles`, redondeada con la mitad hacia
  arriba, como el `round()` de Dart. No con el `round()` de Python, que redondea al par.
- `SIN_MARCA` es incorrecta, no dudosa.
- Una pregunta `DUDOSA` o con `DOBLE_MARCA` queda `POR_REVISAR` y suma 0 hasta que el profesor la
  resuelva: la nota provisional es la «tentativa» de la pantalla, y resolver solo puede subirla.
- `ANULADA` no suma ni resta, y los puntos posibles no cambian.
- Al resolver, el profesor elige entre lo que la pantalla le ofrece: la opción de la clave
  (`CORRECTA`), otra opción (`INCORRECTA`) o anular, sin opción (`ANULADA`).
- **La pantalla de la aplicación no muestra la clave.** El profesor dice qué marcó el estudiante (una
  opción, o ninguna si está en blanco o tiene dos), y `resolucion_con_opcion` lo convierte en el
  veredicto. Así la ruta pública de revisión no publica las respuestas (AM-02).
- **La última resolución de cada pregunta manda.** Las anteriores quedan como historia, igual que
  las notas (ADR-0018). El veredicto se vuelve a deducir de la opción con la calificación vigente:
  si la hoja se califica otra vez con la clave corregida, lo que el profesor vio sigue valiendo.
"""

import math
from collections.abc import Iterable
from dataclasses import replace
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

from infraestructura.modelo import (
    ANULADA,
    CODIGO_COMPLETO,
    CORRECTA,
    DOBLE_MARCA,
    DUDOSA,
    INCORRECTA,
    OPCIONES_DE_RESPUESTA,
    POR_REVISAR,
    SIN_MARCA,
    UNA_MARCA,
    CalificacionDeHoja,
    ClaveDeRespuestas,
    LecturaDeHoja,
    LecturaDePregunta,
    PreguntaDeLaClave,
    ResolucionDelProfesor,
    ResultadoDePregunta,
)

__all__ = [
    "ClaveNoHabilitada",
    "ClaveIncompatible",
    "calificar",
    "recalcular",
    "resolucion_con_opcion",
    "resoluciones_vigentes",
    "nota_vigente",
]

# 5,0 en décimas, como `notaMaximaDecimas` del frontend.
NOTA_MAXIMA_EN_DECIMAS = 50


class ClaveNoHabilitada(ValueError):
    """La clave existe pero el profesor no ha habilitado el examen (RF-07, EC-05)."""


class ClaveIncompatible(ValueError):
    """La clave no cabe en la lectura: pide una pregunta que la hoja no imprime, repite un número
    o usa una opción fuera de A a D. Es un error de quien registró la clave, no de la hoja."""


def calificar(lectura: LecturaDeHoja, clave: ClaveDeRespuestas) -> CalificacionDeHoja:
    """Compara cada pregunta de la clave con la fila del mismo número en la lectura.

    Las filas que la clave no menciona se ignoran. La nota es provisional si alguna pregunta queda
    `POR_REVISAR` o si el código del estudiante está incompleto, porque sin código no se sabe de
    quién es la nota.

    Lanza `ClaveNoHabilitada` si la clave no tiene habilitación y `ClaveIncompatible` si no cabe
    en la lectura."""
    if clave.habilitacion is None:
        raise ClaveNoHabilitada(f"El examen {clave.examen_id} no está habilitado para calificar")
    filas = {fila.numero: fila for fila in lectura.preguntas}
    _comprobar_que_la_clave_cabe(clave, filas)
    resultados = tuple(
        _comparar(filas[pregunta.numero], pregunta)
        for pregunta in sorted(clave.preguntas, key=lambda pregunta: pregunta.numero)
    )
    return _calificacion(
        clave.examen_id, resultados, codigo_por_revisar=lectura.codigo.estado != CODIGO_COMPLETO
    )


def recalcular(
    calificacion: CalificacionDeHoja, resoluciones: tuple[ResolucionDelProfesor, ...]
) -> CalificacionDeHoja:
    """Aplica lo que el profesor resolvió y devuelve una calificación nueva; la anterior no se
    modifica y queda como historia (ADR-0018, punto 3).

    Solo se resuelven preguntas `POR_REVISAR`; resolver otra es `ValueError`. La nota deja de
    ser provisional cuando no queda ninguna pregunta por revisar y el código está completo. El
    código no se corrige aquí: eso es de la identidad del estudiante (A-05)."""
    por_numero: dict[int, ResolucionDelProfesor] = {}
    for resolucion in resoluciones:
        if resolucion.numero in por_numero:
            raise ValueError(f"La pregunta {resolucion.numero} se resolvió dos veces")
        por_numero[resolucion.numero] = resolucion
    resultados = []
    for resultado in calificacion.preguntas:
        resolucion_de_esta = por_numero.pop(resultado.numero, None)
        resultados.append(
            resultado if resolucion_de_esta is None else _resolver(resultado, resolucion_de_esta)
        )
    if por_numero:
        raise ValueError(f"La calificación no tiene las preguntas {sorted(por_numero)}")
    return _calificacion(
        calificacion.examen_id, tuple(resultados), calificacion.codigo_por_revisar
    )


def resolucion_con_opcion(
    resultado: ResultadoDePregunta, opcion: str | None, por: str, en: datetime
) -> ResolucionDelProfesor:
    """Lo que el profesor vio marcado en una pregunta en revisión, hecho veredicto con la clave:
    la opción de la clave es `CORRECTA`, otra opción es `INCORRECTA`, y ninguna (en blanco o con
    dos marcas) es `ANULADA`. Una opción que la hoja no imprime es `ValueError`."""
    if opcion is None:
        veredicto = ANULADA
    elif opcion not in OPCIONES_DE_RESPUESTA:
        raise ValueError(f"La pregunta {resultado.numero} no tiene la opción {opcion!r}")
    elif opcion == resultado.correcta:
        veredicto = CORRECTA
    else:
        veredicto = INCORRECTA
    return ResolucionDelProfesor(resultado.numero, veredicto, opcion, por, en)


def resoluciones_vigentes(
    calificacion: CalificacionDeHoja, resoluciones: Iterable[ResolucionDelProfesor]
) -> tuple[ResolucionDelProfesor, ...]:
    """La última resolución de cada pregunta que `calificacion` dejó en revisión, en el orden de
    las preguntas, con el veredicto deducido otra vez de la opción.

    Una resolución de una pregunta que ya no está en revisión (la hoja se volvió a leer y ahora se
    ve bien) no aplica, y queda como historia."""
    en_revision = {
        resultado.numero: resultado
        for resultado in calificacion.preguntas
        if resultado.veredicto == POR_REVISAR
    }
    ultimas: dict[int, ResolucionDelProfesor] = {}
    for resolucion in resoluciones:
        resultado = en_revision.get(resolucion.numero)
        if resultado is not None:
            ultimas[resolucion.numero] = resolucion_con_opcion(
                resultado, resolucion.opcion, resolucion.por, resolucion.en
            )
    return tuple(ultimas[numero] for numero in sorted(ultimas))


def nota_vigente(
    calificacion: CalificacionDeHoja, resoluciones: Iterable[ResolucionDelProfesor]
) -> CalificacionDeHoja:
    """La calificación automática con lo que el profesor resolvió hasta ahora (RF-08)."""
    return recalcular(calificacion, resoluciones_vigentes(calificacion, resoluciones))


def _comprobar_que_la_clave_cabe(
    clave: ClaveDeRespuestas, filas: dict[int, LecturaDePregunta]
) -> None:
    if not clave.preguntas:
        raise ClaveIncompatible(f"La clave del examen {clave.examen_id} no tiene preguntas")
    vistas: set[int] = set()
    for pregunta in clave.preguntas:
        numero = pregunta.numero
        if numero in vistas:
            raise ClaveIncompatible(f"La pregunta {numero} aparece dos veces en la clave")
        vistas.add(numero)
        if numero not in filas:
            raise ClaveIncompatible(f"La hoja no imprime la pregunta {numero}")
        if pregunta.correcta not in OPCIONES_DE_RESPUESTA:
            raise ClaveIncompatible(
                f"La respuesta de la pregunta {numero} es {pregunta.correcta!r}, que no es una "
                "opción de la hoja"
            )
        if not (math.isfinite(pregunta.peso) and pregunta.peso > 0):
            raise ClaveIncompatible(
                f"La pregunta {numero} pesa {pregunta.peso}, y el peso tiene que ser positivo"
            )


def _comparar(fila: LecturaDePregunta, pregunta: PreguntaDeLaClave) -> ResultadoDePregunta:
    if fila.estado == UNA_MARCA:
        acierta = fila.opcion == pregunta.correcta
        return ResultadoDePregunta(
            numero=pregunta.numero,
            veredicto=CORRECTA if acierta else INCORRECTA,
            marcada=fila.opcion,
            correcta=pregunta.correcta,
            peso=pregunta.peso,
            puntos=pregunta.peso if acierta else 0.0,
        )
    if fila.estado == SIN_MARCA:
        veredicto = INCORRECTA
    elif fila.estado in (DUDOSA, DOBLE_MARCA):
        veredicto = POR_REVISAR
    else:
        raise ValueError(f"La fila {fila.numero} trae un estado desconocido: {fila.estado!r}")
    return ResultadoDePregunta(
        numero=pregunta.numero,
        veredicto=veredicto,
        marcada=None,
        correcta=pregunta.correcta,
        peso=pregunta.peso,
        puntos=0.0,
    )


def _resolver(
    resultado: ResultadoDePregunta, resolucion: ResolucionDelProfesor
) -> ResultadoDePregunta:
    numero = resultado.numero
    if resultado.veredicto != POR_REVISAR:
        raise ValueError(f"La pregunta {numero} no está en revisión")
    if resolucion.veredicto == CORRECTA:
        if resolucion.opcion != resultado.correcta:
            raise ValueError(
                f"La pregunta {numero} se resolvió como correcta con {resolucion.opcion!r}, y la "
                f"clave dice {resultado.correcta!r}"
            )
        puntos = resultado.peso
    elif resolucion.veredicto == INCORRECTA:
        if (
            resolucion.opcion not in OPCIONES_DE_RESPUESTA
            or resolucion.opcion == resultado.correcta
        ):
            raise ValueError(
                f"La pregunta {numero} se resolvió como incorrecta con {resolucion.opcion!r}, que "
                "no es una opción distinta de la clave"
            )
        puntos = 0.0
    elif resolucion.veredicto == ANULADA:
        if resolucion.opcion is not None:
            raise ValueError(f"La pregunta {numero} se anuló, y una anulada no lleva opción")
        puntos = 0.0
    else:
        raise ValueError(
            f"El profesor no puede resolver la pregunta {numero} como {resolucion.veredicto!r}"
        )
    return replace(
        resultado,
        veredicto=resolucion.veredicto,
        marcada=resolucion.opcion,
        puntos=puntos,
        resuelta_por_el_profesor=True,
    )


def _calificacion(
    examen_id: str, resultados: tuple[ResultadoDePregunta, ...], codigo_por_revisar: bool
) -> CalificacionDeHoja:
    puntos = sum(resultado.puntos for resultado in resultados)
    posibles = sum(resultado.peso for resultado in resultados)
    return CalificacionDeHoja(
        examen_id=examen_id,
        nota_en_decimas=_en_decimas(puntos, posibles),
        puntos=puntos,
        puntos_posibles=posibles,
        provisional=codigo_por_revisar
        or any(resultado.veredicto == POR_REVISAR for resultado in resultados),
        codigo_por_revisar=codigo_por_revisar,
        preguntas=resultados,
    )


def _en_decimas(puntos: float, posibles: float) -> int:
    """La misma cuenta que `notaEnDecimas` del frontend, en el mismo orden. `Decimal` toma el
    valor exacto del flotante y lo redondea con la mitad hacia arriba, que es lo que hace Dart
    con un número positivo."""
    exacta = Decimal(puntos * NOTA_MAXIMA_EN_DECIMAS / posibles)
    redondeada = int(exacta.quantize(Decimal(1), rounding=ROUND_HALF_UP))
    return min(max(redondeada, 0), NOTA_MAXIMA_EN_DECIMAS)
