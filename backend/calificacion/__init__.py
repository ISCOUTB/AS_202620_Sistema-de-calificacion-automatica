"""
Responsabilidad: Comparación contra la clave habilitada por el profesor y cálculo de notas; recálculo tras revisión manual.
Requisitos: RF-04, RF-08
Importa: infraestructura, identidad, omr
Posee: ResultadoDePregunta, CalificacionDeHoja, ResolucionDelProfesor
"""

from calificacion.nota import (
    ClaveIncompatible,
    ClaveNoHabilitada,
    calificar,
    nota_vigente,
    recalcular,
    resolucion_con_opcion,
    resoluciones_vigentes,
)
from calificacion.revision import HojaSinNotaQueRevisar, resolver_preguntas

# Interfaz pública del módulo. La lectura y la clave son tipos de `infraestructura.modelo`:
# `calificacion` los recibe, no los construye.
__all__ = [
    "calificar",
    "recalcular",
    "resolucion_con_opcion",
    "resoluciones_vigentes",
    "nota_vigente",
    "resolver_preguntas",
    "ClaveNoHabilitada",
    "ClaveIncompatible",
    "HojaSinNotaQueRevisar",
]
