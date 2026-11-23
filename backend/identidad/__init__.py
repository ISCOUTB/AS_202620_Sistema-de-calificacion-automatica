"""
Responsabilidad: Autenticación, roles y aislamiento de datos por curso.
Requisitos: RF-09, RF-10
Importa: infraestructura
Posee: Sesion

Desde ADR-0025 tiene la autenticación: contraseñas cifradas, el token de una sesión y la lista de
docentes que llega por el entorno. Los roles y el aislamiento por curso (EC-06) siguen sin código:
el sistema todavía no tiene cursos (A-04).
"""

from identidad.contrasenas import cifrar, verificar
from identidad.docentes import (
    ConfiguracionDeDocentesInvalida,
    autenticar,
    leer_docentes,
    normalizar_correo,
)
from identidad.sesiones import Sesion, emitir_sesion, leer_sesion

__all__ = [
    "ConfiguracionDeDocentesInvalida",
    "Sesion",
    "autenticar",
    "cifrar",
    "emitir_sesion",
    "leer_docentes",
    "leer_sesion",
    "normalizar_correo",
    "verificar",
]
