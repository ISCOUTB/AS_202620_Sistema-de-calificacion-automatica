"""Prueba 14: la herramienta del arranque en frío solo cuenta como lote lo que se confirmó.

`herramientas/medir_arranque_en_frio.py` mide contra la API desplegada y tarda unas dos horas, así
que no se corre en el CI. Lo que sí se prueba es la parte que decide qué cuenta: antes, una
muestra fallida (un 502 mientras la instancia despierta, o un `error: ...`)
entraba en la latencia y en el veredicto de EC-07 como si fuera un lote confirmado. Se validó
provocando la falla: sin el filtro por código, la prueba falla.
"""

from herramientas.medir_arranque_en_frio import segundos_de_las_respondidas


def test_solo_las_muestras_con_200_cuentan_como_respondidas() -> None:
    muestras = [
        {"peticion": "POST lote", "codigo": 200, "segundos": 13.5},
        {"peticion": "POST lote", "codigo": 502, "segundos": 1.0},
        {"peticion": "POST lote", "codigo": "error: ReadTimeout", "segundos": 180.0},
        {"peticion": "POST lote", "codigo": 200, "segundos": 24.0},
    ]

    assert segundos_de_las_respondidas(muestras) == [13.5, 24.0]
