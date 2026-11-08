"""El formato de la hoja (RNF-02) y la plantilla que se imprime a partir de él.

Lo que se imprime y lo que se lee salen de la misma definición, `FORMATO_V1`. Estas pruebas
cuidan que esa definición siga siendo imprimible y legible si alguien cambia una medida: que todo
quepa en la hoja, que ninguna burbuja toque una marca de registro y que una burbuja vacía no
tenga tinta adentro."""

import math
import re
import zlib

import cv2
import numpy as np
import pytest

from omr import FORMATO_V1, plantilla_pdf, plantilla_png
from omr.formato import Punto
from omr.plantilla import dibujar_plantilla
from omr.vision import Imagen

# Papel que tiene que quedar entre dos burbujas, o entre una burbuja y una marca, para que una
# marca que se sale un poco del círculo no caiga en la vecina.
SEPARACION_MINIMA_MM = 2.0
# Un cuarto de pulgada: el borde que casi ninguna impresora de oficina deja sin imprimir.
MARGEN_QUE_NO_IMPRIME_MM = 6.35


@pytest.fixture(scope="module")
def hoja() -> Imagen:
    return dibujar_plantilla()


def _todas_las_burbujas() -> list[Punto]:
    respuestas = [
        FORMATO_V1.centro_de_la_respuesta_mm(pregunta, columna)
        for pregunta in range(1, FORMATO_V1.numero_de_preguntas() + 1)
        for columna in range(4)
    ]
    codigo = [
        FORMATO_V1.centro_del_digito_mm(posicion, digito)
        for posicion in range(1, 9)
        for digito in range(10)
    ]
    return respuestas + codigo


def test_el_formato_v1_imprime_40_preguntas_en_una_hoja_carta_a_300_dpi():
    assert FORMATO_V1.numero_de_preguntas() == 40
    assert FORMATO_V1.tamano_en_px() == (2550, 3300)


def test_las_preguntas_se_numeran_seguidas_de_un_bloque_al_otro():
    assert FORMATO_V1.centro_de_la_respuesta_mm(1, 0) == FORMATO_V1.respuestas[0].origen_mm
    assert FORMATO_V1.centro_de_la_respuesta_mm(21, 0) == FORMATO_V1.respuestas[1].origen_mm
    x, y = FORMATO_V1.respuestas[0].origen_mm
    assert FORMATO_V1.centro_de_la_respuesta_mm(20, 3) == (x + 3 * 10.0, y + 19 * 7.0)


def test_el_codigo_tiene_ocho_posiciones_con_los_diez_digitos():
    assert FORMATO_V1.centro_del_digito_mm(1, 0) == FORMATO_V1.codigo.origen_mm
    x, y = FORMATO_V1.codigo.origen_mm
    assert FORMATO_V1.centro_del_digito_mm(8, 9) == (x + 7 * 8.0, y + 9 * 7.0)


@pytest.mark.parametrize("pregunta, columna", [(0, 0), (41, 0), (1, 4), (1, -1)])
def test_una_burbuja_que_la_hoja_no_imprime_es_un_error(pregunta, columna):
    with pytest.raises(ValueError):
        FORMATO_V1.centro_de_la_respuesta_mm(pregunta, columna)


@pytest.mark.parametrize("posicion, digito", [(0, 0), (9, 0), (1, 10), (1, -1)])
def test_un_digito_que_la_hoja_no_imprime_es_un_error(posicion, digito):
    with pytest.raises(ValueError):
        FORMATO_V1.centro_del_digito_mm(posicion, digito)


def test_todas_las_burbujas_caben_y_dejan_papel_hasta_las_marcas():
    radio = FORMATO_V1.radio_de_la_burbuja_mm
    medio_lado = FORMATO_V1.lado_de_la_marca_mm / 2
    for x, y in _todas_las_burbujas():
        assert radio <= x <= FORMATO_V1.ancho_mm - radio
        assert radio <= y <= FORMATO_V1.alto_mm - radio
        for mx, my in FORMATO_V1.centros_de_las_marcas_mm:
            # Distancia del centro de la burbuja al cuadrado de la marca (cero si cae adentro).
            dx = max(abs(x - mx) - medio_lado, 0.0)
            dy = max(abs(y - my) - medio_lado, 0.0)
            assert math.hypot(dx, dy) - radio >= SEPARACION_MINIMA_MM


def test_entre_dos_burbujas_queda_papel():
    burbujas = _todas_las_burbujas()
    minima = min(
        math.dist(a, b) for i, a in enumerate(burbujas) for b in burbujas[i + 1 :]
    )
    assert minima - 2 * FORMATO_V1.radio_de_la_burbuja_mm >= SEPARACION_MINIMA_MM


def test_la_plantilla_tiene_el_tamano_del_formato(hoja):
    ancho, alto = FORMATO_V1.tamano_en_px()
    assert hoja.shape == (alto, ancho)
    assert hoja.dtype == np.uint8


def test_nada_se_imprime_donde_la_impresora_no_llega(hoja):
    """Una marca de registro que la impresora recorta deja la hoja ilegible."""
    margen = round(FORMATO_V1.mm_a_px(MARGEN_QUE_NO_IMPRIME_MM))

    assert hoja[:margen].min() == hoja[-margen:].min() == 255
    assert hoja[:, :margen].min() == hoja[:, -margen:].min() == 255


def test_las_marcas_de_registro_son_cuadrados_negros(hoja):
    medio = FORMATO_V1.mm_a_px(FORMATO_V1.lado_de_la_marca_mm / 2) - 2
    for centro in FORMATO_V1.centros_de_las_marcas_mm:
        x, y = (round(v) for v in FORMATO_V1.a_px(centro))
        lado = round(medio)
        assert hoja[y - lado : y + lado, x - lado : x + lado].max() == 0


def test_una_burbuja_vacia_no_tiene_tinta_adentro_pero_si_contorno(hoja):
    radio = FORMATO_V1.mm_a_px(FORMATO_V1.radio_de_la_burbuja_mm)
    for centro in _todas_las_burbujas():
        x, y = FORMATO_V1.a_px(centro)
        interior = np.zeros_like(hoja)
        cv2.circle(interior, (round(x), round(y)), round(radio * 0.75), 255, cv2.FILLED)
        assert hoja[interior > 0].min() == 255
        assert hoja[round(y), round(x + radio)] < 128


def test_el_png_decodifica_a_la_misma_hoja(hoja):
    decodificada = cv2.imdecode(np.frombuffer(plantilla_png(), np.uint8), cv2.IMREAD_GRAYSCALE)

    assert np.array_equal(decodificada, hoja)


def test_el_pdf_es_una_hoja_carta_con_la_plantilla_entera_y_su_tabla_de_objetos_cuadra(hoja):
    pdf = plantilla_pdf()

    assert pdf.startswith(b"%PDF-1.4\n")
    assert pdf.endswith(b"%%EOF\n")
    # 8,5 × 11 pulgadas, a 72 puntos por pulgada.
    assert b"/MediaBox [0 0 612.00 792.00]" in pdf
    # Cada entrada de la tabla apunta al principio de su objeto.
    inicio_de_la_tabla = int(re.search(rb"startxref\n(\d+)\n", pdf).group(1))
    assert pdf[inicio_de_la_tabla:].startswith(b"xref\n0 6\n")
    entradas = re.findall(rb"(\d{10}) 00000 n \n", pdf[inicio_de_la_tabla:])
    assert len(entradas) == 5
    for numero, posicion in enumerate(entradas, start=1):
        assert pdf[int(posicion) :].startswith(b"%d 0 obj\n" % numero)
    # La imagen que lleva es la plantilla, píxel por píxel.
    largo = int(re.search(rb"/Subtype /Image .*?/Length (\d+) >>\nstream\n", pdf).group(1))
    inicio = pdf.index(b"stream\n") + len(b"stream\n")
    pixeles = zlib.decompress(pdf[inicio : inicio + largo])
    assert pixeles == hoja.tobytes()
