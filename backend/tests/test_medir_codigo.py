"""La herramienta que mide el código del estudiante con casos difíciles
(`herramientas/medir_codigo.py`) sigue corriendo contra el código de hoy.

Corre pocas hojas. No mide nada: comprueba que cada columna generada termina juzgada y que el
juicio dice lo que dice la evidencia (ADR-0024)."""

from herramientas.medir_codigo import (
    BORRON_FUERTE_Y_OTRA,
    CASOS,
    SOLO_BORRON_FUERTE,
    juzgar_columna,
    medir,
)


def test_la_medicion_juzga_las_ocho_columnas_de_cada_hoja():
    informe = medir(hojas=3, semilla=1)

    juzgadas = sum(sum(conteo.values()) for conteo in informe["por_caso"].values())
    leidas = 3 - sum(informe["hojas_ilegibles"].values())
    assert juzgadas == 8 * leidas
    assert set(informe["por_caso"]) == set(CASOS)
    assert informe["mal"] == len(informe["detalle_de_los_mal_aceptados"])
    assert informe["corte_de_intencion"] == 40


def test_la_medicion_pone_a_prueba_borrones_tan_fuertes_como_los_de_las_fotos():
    """En las fotos del prototipo lo borrado llegó a 35 de confianza. La medición incluye borrones
    de ese tamaño y dice qué confianza alcanzaron, leídos en filas de preguntas de las mismas
    hojas: el código no expone la confianza de sus burbujas."""
    informe = medir(hojas=3, semilla=1)

    assert {SOLO_BORRON_FUERTE, BORRON_FUERTE_Y_OTRA} <= set(CASOS)
    calibracion = informe["confianza_de_los_borrones_fuertes"]
    assert calibracion["medidos"] > 0
    assert 0 < calibracion["minima"] <= calibracion["mediana"] <= calibracion["maxima"] < 40


def test_una_columna_se_juzga_contra_el_digito_que_se_quiso_marcar():
    assert juzgar_columna("3", "3") == "aceptado_bien"
    assert juzgar_columna("3", "?") == "por_revisar"
    assert juzgar_columna("3", "7") == "aceptado_mal"
    # Sin intención (en blanco, solo un borrón o dos marcas), aceptar un dígito es un error.
    assert juzgar_columna(None, "?") == "por_revisar"
    assert juzgar_columna(None, "5") == "aceptado_mal"
