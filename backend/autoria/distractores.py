"""Distractores diagnósticos a solicitud del profesor (RF-11, aspecto A-06, escenario EC-08).

Un distractor diagnóstico es una opción incorrecta que corresponde a un error de procedimiento
identificable: para la derivada de `x·sin(x)`, `cos(x)` es olvidar la regla del producto. Este
archivo define qué se le pide al proveedor de LLM, qué devuelve y qué propuestas llegan al
profesor. No conoce HTTP ni al proveedor: eso es del adaptador (`autoria/proveedor_llm.py`), que
este archivo solo ve a través del puerto `GeneradorDeDistractores`.

Dos decisiones de forma:

1. **Ninguna propuesta que repita la respuesta correcta llega al profesor** (medida M1 de
   EC-08). Una «opción incorrecta» igual a la correcta deja la pregunta con dos respuestas
   válidas, que es el problema 2 del proyecto. La comparación es textual, después de quitar las
   diferencias de escritura que no cambian la expresión (espacios, mayúsculas, `·` o `*`, `x²` o
   `x^2`). Una equivalencia algebraica como `1 − cos²(x)` frente a `sin²(x)` no se detecta aquí,
   porque ADR-0004 retiró el cómputo simbólico: la detecta el profesor, que decide cuáles
   acepta (ADR-0005).
2. **Lo que se descarta se cuenta, no se esconde.** El resultado dice qué se descartó y por qué,
   para que el profesor sepa que el modelo devolvió menos de lo que pidió.

Solo depende de la biblioteca estándar: es dominio, y no sabe por qué puerta llegó la pregunta.
"""

import re
from dataclasses import dataclass
from typing import Protocol

__all__ = [
    "PreguntaParaDistractores",
    "DistractorPropuesto",
    "PropuestaDescartada",
    "ResultadoDePropuesta",
    "GeneradorDeDistractores",
    "ProveedorNoDisponible",
    "normalizar",
    "filtrar_propuestas",
    "proponer_distractores",
]


@dataclass(frozen=True)
class PreguntaParaDistractores:
    """Lo único que viaja hacia el proveedor: el enunciado y la respuesta correcta.

    RNF-13 se cumple por construcción: esta clase no tiene dónde llevar un nombre, un curso ni
    una nota, y es todo lo que el adaptador recibe para armar la solicitud."""

    enunciado: str
    respuesta_correcta: str
    cantidad: int = 3


@dataclass(frozen=True)
class DistractorPropuesto:
    """Una opción incorrecta propuesta, con la etiqueta del error de procedimiento que
    representa. Sin la etiqueta no es diagnóstica, así que no se le muestra al profesor."""

    expresion: str
    error: str


@dataclass(frozen=True)
class PropuestaDescartada:
    """Una propuesta que no pasó la regla, con el motivo en texto legible para el profesor."""

    expresion: str
    motivo: str


@dataclass(frozen=True)
class ResultadoDePropuesta:
    """Lo que se le devuelve al profesor: las propuestas que pasaron y las que no, con motivo."""

    propuestos: tuple[DistractorPropuesto, ...]
    descartados: tuple[PropuestaDescartada, ...]


class ProveedorNoDisponible(Exception):
    """El proveedor no respondió a tiempo, rechazó la solicitud o devolvió algo ilegible.

    Lleva el motivo redactado para el profesor. Que el proveedor falle no es un error del
    sistema: RF-11 es opcional y el registro manual de preguntas no depende de él (ADR-0005)."""

    def __init__(self, motivo: str) -> None:
        super().__init__(motivo)
        self.motivo = motivo


class GeneradorDeDistractores(Protocol):
    """El puerto hacia el proveedor de LLM.

    Es el aislamiento hexagonal que el arc42 aplica solo en `autoria` (§4.1), y el lado del
    dominio de la capa anticorrupción de la relación 5 del mapa de contextos (§8.1). Quien lo
    implemente devuelve las propuestas tal como llegaron, sin filtrar: la regla de qué se
    muestra es del dominio y vive en `filtrar_propuestas`. Si el proveedor falla, levanta
    `ProveedorNoDisponible`."""

    def proponer(self, pregunta: PreguntaParaDistractores) -> list[DistractorPropuesto]: ...


# Diferencias de escritura que no cambian la expresión. La comparación sigue siendo textual:
# esto solo evita que `x·cos(x)` y `x*cos(x)` pasen por distintas.
_EQUIVALENCIAS_DE_ESCRITURA = {
    "·": "*",  # punto medio
    "×": "*",  # signo de multiplicación
    "−": "-",  # signo menos
    "**": "^",
}

# El profesor escribe `x²` y el modelo suele escribir `x^2`. Un exponente en superíndice pasa a
# la forma con `^`, para que la respuesta correcta escrita en la otra notación no se cuele.
_SUPERINDICES = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹⁻ˣ", "0123456789-x")
_EXPONENTE_EN_SUPERINDICE = re.compile("[⁰¹²³⁴⁵⁶⁷⁸⁹⁻ˣ]+")


def normalizar(expresion: str) -> str:
    """Forma de comparación de una expresión: sin espacios, en minúsculas y con una sola
    escritura para la multiplicación, la resta y la potencia."""
    texto = "".join(expresion.split()).lower()
    texto = _EXPONENTE_EN_SUPERINDICE.sub(
        lambda exponente: "^" + exponente.group().translate(_SUPERINDICES), texto
    )
    for escrita, comun in _EQUIVALENCIAS_DE_ESCRITURA.items():
        texto = texto.replace(escrita, comun)
    return texto


def filtrar_propuestas(
    pregunta: PreguntaParaDistractores, propuestas: list[DistractorPropuesto]
) -> ResultadoDePropuesta:
    """Aplica la regla de qué propuestas llegan al profesor, en el orden en que llegaron.

    Se descarta, con su motivo, la propuesta vacía, la que no trae la etiqueta del error, la que
    repite la respuesta correcta, la que repite otra propuesta y la que sobra de lo pedido."""
    correcta = normalizar(pregunta.respuesta_correcta)
    vistas: set[str] = set()
    propuestos: list[DistractorPropuesto] = []
    descartados: list[PropuestaDescartada] = []

    for propuesta in propuestas:
        forma = normalizar(propuesta.expresion)
        if not forma:
            descartados.append(PropuestaDescartada(propuesta.expresion, "Llegó vacía."))
            continue
        if not propuesta.error.strip():
            descartados.append(
                PropuestaDescartada(
                    propuesta.expresion, "No dice qué error de procedimiento representa."
                )
            )
            continue
        if forma == correcta:
            descartados.append(
                PropuestaDescartada(
                    propuesta.expresion,
                    "Repite la respuesta correcta: la pregunta quedaría con dos respuestas.",
                )
            )
            continue
        if forma in vistas:
            descartados.append(
                PropuestaDescartada(propuesta.expresion, "Repite otra propuesta.")
            )
            continue
        if len(propuestos) == pregunta.cantidad:
            descartados.append(
                PropuestaDescartada(
                    propuesta.expresion, f"Sobra: se pidieron {pregunta.cantidad}."
                )
            )
            continue
        vistas.add(forma)
        propuestos.append(propuesta)

    return ResultadoDePropuesta(tuple(propuestos), tuple(descartados))


def proponer_distractores(
    pregunta: PreguntaParaDistractores, generador: GeneradorDeDistractores
) -> ResultadoDePropuesta:
    """Pide propuestas al generador y devuelve solo las que pasan la regla.

    `ProveedorNoDisponible` no se atrapa aquí: quien llama decide qué hacer con la falla (la
    API responde 503 con el motivo), y el dominio no tiene una respuesta mejor que inventar."""
    return filtrar_propuestas(pregunta, generador.proponer(pregunta))
