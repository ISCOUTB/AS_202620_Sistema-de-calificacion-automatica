"""
Responsabilidad: Bancos de preguntas y clave de respuestas, generación opcional de distractores diagnósticos con apoyo de LLM, y habilitación del examen.
Requisitos: RF-06, RF-07, RF-11
Importa: infraestructura, identidad
Posee: PreguntaParaDistractores, DistractorPropuesto, PropuestaDescartada, ResultadoDePropuesta, EstadoDelPresupuesto, EstadoDeLaCache, ClaveDeRespuestas, PreguntaDeLaClave, Habilitacion, ExamenConClave, Examen
"""

from autoria.cache import (
    CacheDePropuestas,
    EstadoDeLaCache,
    GeneradorConCache,
)
from autoria.distractores import (
    DistractorPropuesto,
    GeneradorDeDistractores,
    PreguntaParaDistractores,
    PropuestaDescartada,
    ProveedorNoDisponible,
    ResultadoDePropuesta,
    proponer_distractores,
)
from autoria.examenes import (
    LARGO_MAXIMO_DEL_NOMBRE,
    ExamenConClave,
    ExamenNoEncontrado,
    NombreDeExamenInvalido,
    adoptar_examenes_sin_dueno,
    clave_del_nombre,
    crear_examen,
    examen_del_docente,
    examenes_con_clave,
    examenes_del_docente,
)
from autoria.presupuesto import (
    SOLICITUDES_POR_DIA,
    SOLICITUDES_POR_MINUTO,
    EstadoDelPresupuesto,
    GeneradorConPresupuesto,
    PresupuestoAgotado,
    PresupuestoDeSolicitudes,
)
from autoria.proveedor_llm import HUELLA_DE_LAS_INSTRUCCIONES, GeneradorCompatibleConOpenAI
from autoria.registro_de_claves import (
    MAXIMO_DE_PREGUNTAS,
    ClaveInvalida,
    ClaveYaUsada,
    ExamenSinClave,
    clave_se_puede_cambiar,
    habilitar_clave,
    registrar_clave,
)

# Interfaz pública del módulo, como en `ingesta`: quien use `autoria` importa de aquí y no de
# sus archivos internos. La línea `Posee:` de arriba nombra las entidades cuyo contenido decide
# este módulo, con la regla de dueño único de arc42 §8.3.
__all__ = [
    "CacheDePropuestas",
    "ClaveInvalida",
    "ClaveYaUsada",
    "DistractorPropuesto",
    "EstadoDeLaCache",
    "GeneradorConCache",
    "HUELLA_DE_LAS_INSTRUCCIONES",
    "MAXIMO_DE_PREGUNTAS",
    "EstadoDelPresupuesto",
    "ExamenConClave",
    "ExamenSinClave",
    "GeneradorCompatibleConOpenAI",
    "GeneradorConPresupuesto",
    "GeneradorDeDistractores",
    "PreguntaParaDistractores",
    "PresupuestoAgotado",
    "PresupuestoDeSolicitudes",
    "PropuestaDescartada",
    "ProveedorNoDisponible",
    "ResultadoDePropuesta",
    "clave_se_puede_cambiar",
    "examenes_con_clave",
    "examenes_del_docente",
    "examen_del_docente",
    "crear_examen",
    "clave_del_nombre",
    "adoptar_examenes_sin_dueno",
    "ExamenNoEncontrado",
    "NombreDeExamenInvalido",
    "LARGO_MAXIMO_DEL_NOMBRE",
    "habilitar_clave",
    "proponer_distractores",
    "registrar_clave",
    "SOLICITUDES_POR_DIA",
    "SOLICITUDES_POR_MINUTO",
]
