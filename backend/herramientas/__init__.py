"""Herramientas de medición y diagnóstico. No forman parte del sistema.

No es uno de los siete módulos del dominio que fija ADR-0002: nada de `backend/` importa desde
aquí, y este paquete puede importar lo que necesite para medir. La prueba de fronteras
(`tests/test_fronteras.py`) recorre solo los siete módulos, así que este directorio queda fuera
de su alcance a propósito.
"""
