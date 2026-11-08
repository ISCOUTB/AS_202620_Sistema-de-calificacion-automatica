"""
Responsabilidad: Detección de marcas y cálculo del nivel de confianza; clasificación de ambigüedad.
Requisitos: RF-02, RF-03
Importa: infraestructura, identidad
Posee: LecturaDeBurbuja, LecturaDePregunta, LecturaDelCodigo, LecturaDeHoja
"""

from omr.decision import comprobar_umbral_de_confianza
from omr.errores import (
    FormatoNoSoportado,
    HojaNoReconocida,
    ImagenIlegible,
    LecturaImposible,
    MarcasDeRegistroNoEncontradas,
)
from omr.formato import FORMATO_V1, Cuadricula, FormatoDeHoja
from omr.lectura import leer_hoja, leer_hoja_con_recortes
from omr.plantilla import plantilla_pdf, plantilla_png

# Interfaz pública del módulo. `vision` y `decision` son internos: el worker y `calificacion`
# usan `leer_hoja` y los tipos de `infraestructura.modelo`, nunca los pasos sueltos.
__all__ = [
    "leer_hoja",
    "leer_hoja_con_recortes",
    "comprobar_umbral_de_confianza",
    "FormatoDeHoja",
    "Cuadricula",
    "FORMATO_V1",
    "plantilla_png",
    "plantilla_pdf",
    "LecturaImposible",
    "FormatoNoSoportado",
    "ImagenIlegible",
    "MarcasDeRegistroNoEncontradas",
    "HojaNoReconocida",
]
