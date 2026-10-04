"""Prueba 9: ninguna propuesta que repita la respuesta correcta llega al profesor (RF-11, EC-08).

Es la medida M1 de EC-08 y el defecto que esta prueba cubre: si la regla de
`autoria/distractores.py` deja pasar una «opción incorrecta» igual a la correcta, la pregunta
queda con dos respuestas válidas y el estudiante que respondió bien pierde el punto. Un modelo
de lenguaje puede proponer eso, así que no basta con confiar en él.

El generador es un sustituto que devuelve una lista fija: la regla se prueba sin red y sin
proveedor, que es para lo que existe el puerto `GeneradorDeDistractores`.
"""

import pytest

from autoria.distractores import (
    DistractorPropuesto,
    PreguntaParaDistractores,
    ProveedorNoDisponible,
    normalizar,
    proponer_distractores,
)

PREGUNTA = PreguntaParaDistractores(
    enunciado="Derivada de x·sin(x)",
    respuesta_correcta="sin(x) + x·cos(x)",
    cantidad=3,
)


class GeneradorFalso:
    """Devuelve siempre las mismas propuestas, o levanta la falla que se le indique."""

    def __init__(
        self,
        propuestas: list[DistractorPropuesto] | None = None,
        falla: ProveedorNoDisponible | None = None,
    ) -> None:
        self.propuestas = propuestas or []
        self.falla = falla
        self.preguntas: list[PreguntaParaDistractores] = []

    def proponer(self, pregunta: PreguntaParaDistractores) -> list[DistractorPropuesto]:
        self.preguntas.append(pregunta)
        if self.falla is not None:
            raise self.falla
        return list(self.propuestas)


def _expresiones(resultado) -> list[str]:
    return [propuesta.expresion for propuesta in resultado.propuestos]


def test_la_respuesta_correcta_nunca_llega_como_distractor() -> None:
    generador = GeneradorFalso([
        DistractorPropuesto("cos(x)", "Se omitió la regla del producto"),
        DistractorPropuesto("sin(x) + x·cos(x)", "Ninguno"),
        DistractorPropuesto("sin(x) - x·cos(x)", "Error de signo"),
    ])

    resultado = proponer_distractores(PREGUNTA, generador)

    assert _expresiones(resultado) == ["cos(x)", "sin(x) - x·cos(x)"]
    assert [d.expresion for d in resultado.descartados] == ["sin(x) + x·cos(x)"]
    assert "respuesta correcta" in resultado.descartados[0].motivo


def test_la_respuesta_correcta_escrita_de_otra_forma_tambien_se_descarta() -> None:
    """Espacios, mayúsculas y `*` en lugar de `·` no cambian la expresión: si la regla solo
    comparara el texto tal cual, el modelo la burlaría escribiendo `SIN(x)+x*cos(x)`."""
    generador = GeneradorFalso([
        DistractorPropuesto("SIN(x)+x*cos(x)", "Ninguno"),
        DistractorPropuesto("x·cos(x)", "La regla del producto se aplicó a medias"),
    ])

    resultado = proponer_distractores(PREGUNTA, generador)

    assert _expresiones(resultado) == ["x·cos(x)"]
    assert len(resultado.descartados) == 1


def test_un_exponente_escrito_con_circunflejo_es_el_mismo_que_en_superindice() -> None:
    """El profesor escribe `5x⁴` y el modelo suele escribir `5x^4`. Sin igualar las dos
    notaciones, la respuesta correcta pasaría como distractor."""
    pregunta = PreguntaParaDistractores("Derivada de x⁵", "5x⁴", cantidad=3)
    generador = GeneradorFalso([
        DistractorPropuesto("5x^4", "Ninguno"),
        DistractorPropuesto("x^4", "No se multiplicó por el exponente"),
    ])

    resultado = proponer_distractores(pregunta, generador)

    assert _expresiones(resultado) == ["x^4"]


def test_una_propuesta_repetida_o_sin_etiqueta_se_descarta_con_su_motivo() -> None:
    generador = GeneradorFalso([
        DistractorPropuesto("cos(x)", "Se omitió la regla del producto"),
        DistractorPropuesto("cos (x)", "Otra vez lo mismo"),
        DistractorPropuesto("x·cos(x)", ""),
        DistractorPropuesto("   ", "Vacía"),
    ])

    resultado = proponer_distractores(PREGUNTA, generador)

    assert _expresiones(resultado) == ["cos(x)"]
    motivos = [d.motivo for d in resultado.descartados]
    assert motivos == [
        "Repite otra propuesta.",
        "No dice qué error de procedimiento representa.",
        "Llegó vacía.",
    ]


def test_no_llegan_mas_propuestas_que_las_pedidas() -> None:
    pregunta = PreguntaParaDistractores("Derivada de x²", "2x", cantidad=2)
    generador = GeneradorFalso([
        DistractorPropuesto("x", "Se bajó el exponente sin multiplicar"),
        DistractorPropuesto("2", "Se derivó como si fuera lineal"),
        DistractorPropuesto("x²", "No se derivó"),
    ])

    resultado = proponer_distractores(pregunta, generador)

    assert _expresiones(resultado) == ["x", "2"]
    assert resultado.descartados[0].motivo == "Sobra: se pidieron 2."


def test_al_generador_solo_le_llega_la_pregunta() -> None:
    """RNF-13 desde el lado del dominio: lo único que cruza el puerto es la pregunta."""
    generador = GeneradorFalso([])

    proponer_distractores(PREGUNTA, generador)

    assert generador.preguntas == [PREGUNTA]


def test_la_falla_del_proveedor_llega_a_quien_llama_con_su_motivo() -> None:
    generador = GeneradorFalso(falla=ProveedorNoDisponible("El proveedor no respondió."))

    with pytest.raises(ProveedorNoDisponible) as error:
        proponer_distractores(PREGUNTA, generador)

    assert error.value.motivo == "El proveedor no respondió."


@pytest.mark.parametrize(
    ("escrita", "comun"),
    [
        ("x · cos(x)", "x*cos(x)"),
        ("1 − cos²(x)", "1-cos^2(x)"),
        ("X**2", "x^2"),
        ("5x⁴", "5x^4"),
        ("eˣ", "e^x"),
        ("x⁻¹", "x^-1"),
    ],
)
def test_normalizar_quita_solo_diferencias_de_escritura(escrita: str, comun: str) -> None:
    assert normalizar(escrita) == comun
