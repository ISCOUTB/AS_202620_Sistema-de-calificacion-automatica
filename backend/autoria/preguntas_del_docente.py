"""Las preguntas que el docente agrega en Pauta, guardadas a su nombre (ADR-0030).

**Es el comienzo del banco de preguntas (RF-06).** La pregunta es su enunciado y su respuesta
correcta, sin tema y sin examen. Se reconoce como en ADR-0029 (`llave_de_la_pregunta`): la misma
pregunta con otros espacios no se agrega dos veces, y los distractores que se guarden para ella la
encuentran.
"""

from datetime import datetime

from autoria.distractores_guardados import llave_de_la_pregunta
from infraestructura.modelo import PreguntaDelDocente
from infraestructura.preguntas_del_docente import RegistroDePreguntas

__all__ = ["PreguntaInvalida", "PreguntaRepetida", "agregar_pregunta"]


class PreguntaInvalida(ValueError):
    """Falta el enunciado o la respuesta correcta. El mensaje va redactado para el docente."""


class PreguntaRepetida(ValueError):
    """El docente ya tiene esa pregunta. El mensaje va redactado para él."""


def agregar_pregunta(
    docente: str,
    enunciado: str,
    respuesta_correcta: str,
    en: datetime,
    registro: RegistroDePreguntas,
) -> tuple[str, PreguntaDelDocente]:
    """Agrega la pregunta a las del docente, con los espacios normalizados, y devuelve su llave.
    Lanza `PreguntaInvalida` si falta un texto y `PreguntaRepetida` si ya la tenía."""
    enunciado = " ".join(enunciado.split())
    respuesta_correcta = " ".join(respuesta_correcta.split())
    if not enunciado or not respuesta_correcta:
        raise PreguntaInvalida("Escriba el enunciado y la respuesta correcta.")
    pregunta = PreguntaDelDocente(
        docente=docente, enunciado=enunciado, respuesta_correcta=respuesta_correcta, agregada_en=en
    )
    llave = llave_de_la_pregunta(enunciado, respuesta_correcta)
    if not registro.agregar(llave, pregunta):
        raise PreguntaRepetida("Esa pregunta ya está en su lista.")
    return llave, pregunta
