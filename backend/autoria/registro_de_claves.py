"""Registrar la clave de un examen y habilitarla desde la aplicación (A-04, RF-07, ADR-0026).

`autoria` es la dueña de la clave (ADR-0007): aquí se decide qué es una clave válida y cuándo se
puede cambiar. Guardarla es del adaptador, por el puerto `RegistroDeClaves`; leerla para calificar
sigue siendo del worker, sin cambios.

Una clave se puede cambiar mientras ninguna hoja de su examen tenga nota: las notas se calculan al
leer cada hoja y no se recalculan solas, así que cambiarla después dejaría hojas calificadas con
dos claves distintas. Cambiarla la deja sin habilitar, porque la habilitación certifica unas
respuestas concretas."""

import re
from collections.abc import Sequence
from dataclasses import replace
from datetime import datetime
from typing import Protocol

from infraestructura.claves import FuenteDeClaves, RegistroDeClaves
from infraestructura.modelo import (
    OPCIONES_DE_RESPUESTA,
    ClaveDeRespuestas,
    Habilitacion,
    PreguntaDeLaClave,
)

# Las preguntas que imprime la hoja v1 (`omr.FORMATO_V1`). `autoria` no puede importar `omr`, así
# que el número se repite aquí, y una prueba comprueba que no se separen.
MAXIMO_DE_PREGUNTAS = 40

# El identificador es el nombre del archivo de la clave y lo que se elige en la carga: letras sin
# acento, dígitos, guion y guion bajo, como `CALC-2026-02`.
_IDENTIFICADOR = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}")


class ClaveInvalida(ValueError):
    """La clave no cabe en la hoja o el identificador del examen no sirve. El mensaje es para el
    docente."""


class ClaveYaUsada(Exception):
    """Ya hay hojas del examen calificadas con esta clave, así que no se puede cambiar."""


class ExamenSinClave(LookupError):
    """El examen no tiene una clave registrada que habilitar."""


class HechosDeResultados(Protocol):
    """Lo que hace falta del registro de resultados: los hechos de las hojas de un examen."""

    def hechos_del_examen(self, examen_id: str) -> list[dict]: ...


def clave_se_puede_cambiar(examen_id: str, resultados: HechosDeResultados) -> bool:
    """Si ninguna hoja del examen tiene nota. Una hoja leída sin clave habilitada no la tiene."""
    return not any(hecho.get("calificacion") for hecho in resultados.hechos_del_examen(examen_id))


def _clave_desde(examen_id: str, respuestas: Sequence[str]) -> ClaveDeRespuestas:
    if not _IDENTIFICADOR.fullmatch(examen_id):
        raise ClaveInvalida(
            "El identificador del examen solo puede tener letras sin acento, dígitos, guiones y "
            "guiones bajos, hasta 64, como CALC-2026-02."
        )
    if not respuestas:
        raise ClaveInvalida("La clave necesita al menos una pregunta.")
    if len(respuestas) > MAXIMO_DE_PREGUNTAS:
        raise ClaveInvalida(
            f"La hoja tiene {MAXIMO_DE_PREGUNTAS} preguntas, y la clave trae {len(respuestas)}."
        )
    preguntas = []
    for numero, respuesta in enumerate(respuestas, start=1):
        correcta = respuesta.strip().upper()
        if correcta not in OPCIONES_DE_RESPUESTA:
            raise ClaveInvalida(f"La pregunta {numero} no tiene una respuesta entre A, B, C y D.")
        preguntas.append(PreguntaDeLaClave(numero=numero, correcta=correcta, peso=1.0))
    return ClaveDeRespuestas(examen_id=examen_id, preguntas=tuple(preguntas))


def registrar_clave(
    examen_id: str,
    respuestas: Sequence[str],
    registro: RegistroDeClaves,
    resultados: HechosDeResultados,
) -> ClaveDeRespuestas:
    """Guarda la clave del examen, sin habilitar: la respuesta de la pregunta 1 primero. Lanza
    `ClaveInvalida` si no cabe en la hoja y `ClaveYaUsada` si ya hay hojas calificadas."""
    clave = _clave_desde(examen_id, respuestas)
    if not clave_se_puede_cambiar(examen_id, resultados):
        raise ClaveYaUsada(
            f"Ya hay hojas de {examen_id} calificadas con esta clave: no se puede cambiar."
        )
    registro.guardar(clave)
    return clave


def habilitar_clave(
    examen_id: str,
    por: str,
    en: datetime,
    claves: "_FuenteYRegistro",
) -> ClaveDeRespuestas:
    """Habilita la clave del examen a nombre de `por` (RF-07). Si ya estaba habilitada, queda como
    estaba: quién y cuándo la habilitaron no cambia por volver a pedirlo."""
    clave = claves.clave_del_examen(examen_id)
    if clave is None:
        raise ExamenSinClave(f"{examen_id} no tiene una clave registrada.")
    if clave.habilitacion is not None:
        return clave
    habilitada = replace(clave, habilitacion=Habilitacion(por=por, en=en))
    claves.guardar(habilitada)
    return habilitada


class _FuenteYRegistro(FuenteDeClaves, RegistroDeClaves, Protocol):
    """Habilitar lee la clave y la vuelve a guardar."""
