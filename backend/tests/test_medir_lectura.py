"""La herramienta que mide EC-01 y EC-02 (`herramientas/medir_lectura.py`) sigue corriendo contra el
código de hoy, como la de EC-07: una evidencia que nadie ejecuta se rompe sin que se note.

Corre pocas hojas. No mide nada: comprueba que el procedimiento llega al final, que cada pregunta
generada termina juzgada y que las cifras salen con el sentido que tienen en la evidencia."""

from herramientas.medir_lectura import (
    AMBIGUAS,
    CASOS,
    CLARA,
    Pregunta,
    juzgar,
    medir,
)
from infraestructura.modelo import DOBLE_MARCA, DUDOSA, SIN_MARCA, UNA_MARCA


def test_la_medicion_juzga_todas_las_preguntas_de_todas_las_hojas():
    informe = medir(hojas=3, semilla=1)

    juzgadas = sum(sum(conteo.values()) for conteo in informe["por_caso"].values())
    leidas = 3 - sum(informe["hojas_ilegibles"].values())
    assert juzgadas == 40 * leidas
    assert informe["errores_silenciosos"] == 0
    assert set(informe["por_caso"]) == set(CASOS)


def test_una_marca_ambigua_asignada_es_un_error_silencioso_y_a_revision_esta_bien():
    for caso in AMBIGUAS:
        pregunta = Pregunta(caso, "B")
        assert juzgar(pregunta, DUDOSA, None) == "bien"
        assert juzgar(pregunta, DOBLE_MARCA, None) == "bien"
        assert juzgar(pregunta, UNA_MARCA, "B") == "error_silencioso"
        assert juzgar(pregunta, SIN_MARCA, None) == "error_silencioso"


def test_una_marca_clara_que_va_a_revision_cuesta_tiempo_pero_no_es_un_error():
    pregunta = Pregunta(CLARA, "C")

    assert juzgar(pregunta, UNA_MARCA, "C") == "bien"
    assert juzgar(pregunta, DUDOSA, None) == "a_revision"
    assert juzgar(pregunta, UNA_MARCA, "A") == "error_silencioso"
    assert juzgar(pregunta, SIN_MARCA, None) == "error_silencioso"
