"""Prueba 2: los siete módulos del dominio se importan sin error y sin ciclos."""

import importlib

import pytest

MODULOS = [
    "autoria",
    "ingesta",
    "omr",
    "calificacion",
    "dashboard",
    "identidad",
    "infraestructura",
]


@pytest.mark.parametrize("nombre_modulo", MODULOS)
def test_modulo_se_importa_sin_error(nombre_modulo):
    modulo = importlib.import_module(nombre_modulo)

    assert modulo is not None
