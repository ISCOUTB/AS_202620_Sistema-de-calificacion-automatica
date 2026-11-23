"""Los distractores que el docente aprueba, guardados a su nombre (ADR-0029).

**Qué se guarda.** Los que el docente eligió entre las propuestas del modelo (RF-11): la
expresión y el error de procedimiento que representa. El modelo propone y el docente decide
(RF-07); esto guarda la decisión, no la propuesta.

**Cómo se reconoce la pregunta.** Por el enunciado y la respuesta correcta que el docente
escribió, con los espacios normalizados como en la caché de propuestas (ADR-0019). Así se
reconoce también una pregunta agregada (ADR-0030), y Pauta pone al final de su lista las que
tienen distractores guardados.

**Las reglas son las mismas que filtran las propuestas** (`distractores.normalizar`): ninguno
repite la respuesta correcta ni a otro, y cada uno dice qué error representa. Y no caben más de
los que imprime la hoja: cuatro opciones, una correcta y tres distractores.
"""

import hashlib
import json
from collections.abc import Sequence
from datetime import datetime

from autoria.distractores import normalizar
from infraestructura.distractores_guardados import RegistroDeDistractores
from infraestructura.modelo import (
    OPCIONES_DE_RESPUESTA,
    DistractorGuardado,
    DistractoresGuardados,
)

__all__ = [
    "DISTRACTORES_POR_PREGUNTA",
    "DistractoresInvalidos",
    "guardar_distractores",
    "llave_de_la_pregunta",
]

DISTRACTORES_POR_PREGUNTA = len(OPCIONES_DE_RESPUESTA) - 1


class DistractoresInvalidos(ValueError):
    """Lo que se quiso guardar no cumple la regla. El mensaje va redactado para el docente."""


def llave_de_la_pregunta(enunciado: str, respuesta_correcta: str) -> str:
    """Cómo se reconoce una pregunta: el enunciado y la respuesta correcta sin espacios de más."""
    partes = [" ".join(enunciado.split()), " ".join(respuesta_correcta.split())]
    return hashlib.sha256(json.dumps(partes, ensure_ascii=False).encode("utf-8")).hexdigest()


def guardar_distractores(
    docente: str,
    enunciado: str,
    respuesta_correcta: str,
    distractores: Sequence[DistractorGuardado],
    en: datetime,
    registro: RegistroDeDistractores,
) -> DistractoresGuardados:
    """Guarda los distractores del docente para la pregunta, reemplazando los que tuviera. Lanza
    `DistractoresInvalidos` sin tocar lo guardado si alguno no cumple la regla."""
    limpios = tuple(DistractorGuardado(d.expresion.strip(), d.error.strip()) for d in distractores)
    if not limpios:
        raise DistractoresInvalidos("Elija al menos uno para guardar.")
    if len(limpios) > DISTRACTORES_POR_PREGUNTA:
        raise DistractoresInvalidos(
            f"Una pregunta lleva {DISTRACTORES_POR_PREGUNTA} distractores: la hoja tiene "
            f"{len(OPCIONES_DE_RESPUESTA)} opciones y una es la correcta."
        )
    correcta = normalizar(respuesta_correcta)
    vistas: set[str] = set()
    for distractor in limpios:
        forma = normalizar(distractor.expresion)
        if not forma or not distractor.error:
            raise DistractoresInvalidos(
                "Cada distractor necesita su expresión y el error que representa."
            )
        if forma == correcta:
            raise DistractoresInvalidos(
                f"«{distractor.expresion}» es la respuesta correcta escrita de otra forma."
            )
        if forma in vistas:
            raise DistractoresInvalidos(f"«{distractor.expresion}» está dos veces.")
        vistas.add(forma)

    guardados = DistractoresGuardados(
        docente=docente,
        enunciado=" ".join(enunciado.split()),
        respuesta_correcta=" ".join(respuesta_correcta.split()),
        distractores=limpios,
        guardado_en=en,
    )
    registro.guardar(llave_de_la_pregunta(enunciado, respuesta_correcta), guardados)
    return guardados
