"""La lectura sobre las fotos reales de la hoja del prototipo (R-05).

Las fotos no están en el repositorio: son de celular y pesan unos 4 MB cada una. La prueba corre si
`OMR_FOTOS_R05` apunta a la carpeta con ellas, y se omite si no.

La hoja tiene 30 preguntas con una marca clara (lápiz y esfero, patrón A, B, C, D), el código
T12345678 y diez casos difíciles en las preguntas 31 a 40. Lo que se exige es EC-02: ninguna
respuesta leída mal sin aviso. Que una pregunta vaya a revisión está permitido."""

import os
import pathlib

import pytest

from infraestructura.modelo import DOBLE_MARCA, DUDOSA, SIN_MARCA, UNA_MARCA, LecturaDePregunta
from omr import leer_hoja

CARPETA = os.environ.get("OMR_FOTOS_R05")
FOTOS = sorted(pathlib.Path(CARPETA).glob("*.jpg")) if CARPETA else []

# Lo que se acepta en cada pregunta difícil, además de que vaya a revisión.
ACEPTADO: dict[int, set[tuple[str, str | None]]] = {
    31: {(SIN_MARCA, None)},  # en blanco
    32: {(DOBLE_MARCA, None)},  # A y C
    33: {(UNA_MARCA, "B")},  # B tenue, rellena con lápiz suave
    34: {(UNA_MARCA, "B")},  # D bien borrada y B marcada
    35: {(SIN_MARCA, None)},  # A rellena y borrada
    36: set(),  # un chulo dentro de C
    37: {(UNA_MARCA, "C")},  # C, saliéndose del círculo
    38: set(),  # B rellena a medias
    39: set(),  # una X sobre D
    40: {(UNA_MARCA, "A")},
}


def _aceptable(pregunta: LecturaDePregunta) -> bool:
    if pregunta.estado == DUDOSA:
        return True
    leida = (pregunta.estado, pregunta.opcion)
    if pregunta.numero <= 30:
        return leida == (UNA_MARCA, "ABCD"[(pregunta.numero - 1) % 4])
    return leida in ACEPTADO[pregunta.numero]


@pytest.mark.skipif(not FOTOS, reason="OMR_FOTOS_R05 no apunta a las fotos del prototipo")
@pytest.mark.parametrize("foto", FOTOS, ids=[foto.stem for foto in FOTOS])
def test_ninguna_respuesta_se_lee_mal_sin_avisar(foto):
    lectura = leer_hoja(foto.read_bytes(), 70)

    mal_leidas = [p for p in lectura.preguntas if not _aceptable(p)]
    assert mal_leidas == []
    assert lectura.codigo.valor is not None
    assert all(leido in ("?", esperado) for leido, esperado in zip(lectura.codigo.valor, "T12345678"))
