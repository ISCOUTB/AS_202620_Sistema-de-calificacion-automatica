"""
Responsabilidad: Bancos de preguntas y clave de respuestas, generación opcional de distractores diagnósticos con apoyo de LLM, y habilitación del examen.
Requisitos: RF-06, RF-07, RF-11
Importa: infraestructura, identidad
Posee: PreguntaParaDistractores, DistractorPropuesto, PropuestaDescartada, ResultadoDePropuesta
"""

from autoria.distractores import (
    DistractorPropuesto,
    GeneradorDeDistractores,
    PreguntaParaDistractores,
    PropuestaDescartada,
    ProveedorNoDisponible,
    ResultadoDePropuesta,
    proponer_distractores,
)
from autoria.proveedor_llm import GeneradorCompatibleConOpenAI

# Interfaz pública del módulo, como en `ingesta`: quien use `autoria` importa de aquí y no de
# sus archivos internos. La línea `Posee:` de arriba nombra las entidades cuyo contenido decide
# este módulo, con la regla de dueño único de arc42 §8.3.
__all__ = [
    "DistractorPropuesto",
    "GeneradorCompatibleConOpenAI",
    "GeneradorDeDistractores",
    "PreguntaParaDistractores",
    "PropuestaDescartada",
    "ProveedorNoDisponible",
    "ResultadoDePropuesta",
    "proponer_distractores",
]
