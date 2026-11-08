"""La lectura de una hoja de punta a punta (A-02, RF-02, RF-03, EC-02), con hojas sintéticas.

Cada prueba marca la plantilla, la «fotografía» con perspectiva, giro o sombra, y comprueba lo que
lee `leer_hoja`. Lo que cuidan es EC-02: una marca clara se lee sola, lo dudoso va a revisión y
nada se lee mal sin avisar. Las fotos reales del prototipo están en `test_lectura_fotos_r05.py`."""

import cv2
import numpy as np
import pytest

from infraestructura.modelo import (
    CODIGO_COMPLETO,
    CODIGO_INCOMPLETO,
    DOBLE_MARCA,
    DUDOSA,
    SIN_MARCA,
    UNA_MARCA,
    LecturaDeHoja,
)
from omr import (
    FORMATO_V1,
    FormatoNoSoportado,
    HojaNoReconocida,
    ImagenIlegible,
    MarcasDeRegistroNoEncontradas,
    leer_hoja,
    leer_hoja_con_recortes,
)
from omr.plantilla import NEGRO
from herramientas.hojas_sinteticas import LAPIZ, PAPEL, fotografiar, hoja_marcada, patron

UMBRAL = 70
CODIGO = "20261104"
TODAS = {n: patron(n) for n in range(1, 41)}


def _estados(lectura: LecturaDeHoja) -> dict[int, tuple[str, str | None]]:
    return {p.numero: (p.estado, p.opcion) for p in lectura.preguntas}


@pytest.fixture(scope="module")
def hoja_completa():
    return hoja_marcada(TODAS, CODIGO)


def test_lee_las_40_respuestas_y_el_codigo_de_una_hoja_derecha(hoja_completa):
    lectura = leer_hoja(fotografiar(hoja_completa), UMBRAL)

    assert lectura.version_del_formato == FORMATO_V1.version
    assert _estados(lectura) == {n: (UNA_MARCA, patron(n)) for n in range(1, 41)}
    assert (lectura.codigo.estado, lectura.codigo.valor) == (CODIGO_COMPLETO, "T" + CODIGO)
    assert lectura.umbral_de_confianza == UMBRAL
    assert lectura.duracion_ms > 0


@pytest.mark.parametrize("giro", [1, 2, 3], ids=["de-lado", "de-cabeza", "del-otro-lado"])
def test_lee_igual_una_foto_girada_y_en_perspectiva(hoja_completa, giro):
    """Girada 180°, casi todas las burbujas caen sobre otras: la orientación tiene que salir de la
    hoja entera, o la lectura saldría corrida sin aviso."""
    lectura = leer_hoja(fotografiar(hoja_completa, giro=giro, perspectiva=0.15), UMBRAL)

    assert _estados(lectura) == {n: (UNA_MARCA, patron(n)) for n in range(1, 41)}
    assert lectura.codigo.valor == "T" + CODIGO


def test_una_sombra_no_inventa_marcas_ni_borra_las_que_hay():
    respuestas = {n: patron(n) for n in range(1, 41) if n % 3}
    lectura = leer_hoja(fotografiar(hoja_marcada(respuestas, CODIGO), sombra=0.45), UMBRAL)

    esperadas = {n: (UNA_MARCA, respuestas[n]) if n in respuestas else (SIN_MARCA, None)
                 for n in range(1, 41)}
    assert _estados(lectura) == esperadas


def test_una_fila_en_blanco_es_sin_marca_y_dos_marcas_son_doble_marca():
    lectura = leer_hoja(fotografiar(hoja_marcada({1: "B", 2: "AC"})), UMBRAL)

    estados = _estados(lectura)
    assert estados[1] == (UNA_MARCA, "B")
    assert estados[2] == (DOBLE_MARCA, None)
    assert estados[3] == (SIN_MARCA, None)


def test_media_burbuja_va_a_revision():
    lectura = leer_hoja(fotografiar(hoja_marcada({}, a_medias=((5, "C"),))), UMBRAL)

    assert _estados(lectura)[5] == (DUDOSA, None)


def test_las_filas_en_revision_salen_recortadas_y_solo_ellas():
    """Lo que mira el profesor para resolverlas (RF-08): la fila, desde su número hasta la última
    burbuja y de la altura de una fila. Las demás filas, y el código, no se recortan."""
    foto = fotografiar(hoja_marcada({1: "B", 2: "AC"}, CODIGO, a_medias=((5, "C"),)))

    lectura, recortes = leer_hoja_con_recortes(foto, UMBRAL)

    assert lectura.preguntas == leer_hoja(foto, UMBRAL).preguntas
    assert set(recortes) == {2, 5}
    for png in recortes.values():
        fila = cv2.imdecode(np.frombuffer(png, np.uint8), cv2.IMREAD_GRAYSCALE)
        alto, ancho = fila.shape
        assert alto == pytest.approx(FORMATO_V1.mm_a_px(2 * 3.4), abs=3)
        assert ancho == pytest.approx(FORMATO_V1.mm_a_px(12 + 30 + 5), abs=40)
        assert fila.min() < (PAPEL + LAPIZ) / 2, "la fila trae las marcas"


def test_el_grafito_con_brillo_no_se_lee_como_vacio():
    """El caso de R-05: con el reflejo, la marca se ve casi del color del papel. Leerla vacía
    sería una incorrecta que nadie revisa."""
    hoja = hoja_marcada({}, con_brillo=((7, "D"),))
    lectura = leer_hoja(fotografiar(hoja, escala=1.0), UMBRAL)

    assert _estados(lectura)[7] == (DUDOSA, None)
    assert _estados(lectura)[8] == (SIN_MARCA, None)


def test_una_mancha_que_tapa_la_burbuja_y_su_papel_no_se_lee_como_vacia():
    """Sin papel alrededor no hay con qué comparar: la burbuja se ve igual que su anillo, como una
    vacía. Lo que la delata es que su contorno impreso no se ve."""
    hoja = hoja_marcada({})
    x, y = (round(v) for v in FORMATO_V1.a_px(FORMATO_V1.centro_de_la_respuesta_mm(9, 1)))
    medio = round(FORMATO_V1.mm_a_px(4.5))
    hoja[y - medio : y + medio, x - medio : x + medio] = LAPIZ

    lectura = leer_hoja(fotografiar(hoja), UMBRAL)

    assert _estados(lectura)[9] == (DUDOSA, None)


def test_un_codigo_con_una_columna_en_blanco_queda_incompleto_y_dice_cual():
    hoja = hoja_marcada(TODAS, CODIGO)
    # La columna 4 sin marcar: se vuelve a dibujar la plantilla encima de esa columna.
    limpia = hoja_marcada(TODAS)
    x, _ = FORMATO_V1.a_px(FORMATO_V1.centro_del_digito_mm(4, 0))
    medio = round(FORMATO_V1.mm_a_px(4))
    hoja[:, round(x) - medio : round(x) + medio] = limpia[:, round(x) - medio : round(x) + medio]

    lectura = leer_hoja(fotografiar(hoja), UMBRAL)

    assert lectura.codigo.estado == CODIGO_INCOMPLETO
    assert lectura.codigo.columnas_por_revisar == (4,)
    assert lectura.codigo.valor == "T202?1104"


def test_el_codigo_no_sale_en_el_repr_de_la_lectura(hoja_completa):
    lectura = leer_hoja(fotografiar(hoja_completa), UMBRAL)

    assert CODIGO not in repr(lectura)


# --- Hojas que no se pueden leer -------------------------------------------------------------


@pytest.mark.parametrize(
    "contenido",
    [b"%PDF-1.4\n...", b"", b"no es una imagen"],
    ids=["pdf", "vacio", "texto"],
)
def test_lo_que_no_es_una_imagen_es_formato_no_soportado(contenido):
    with pytest.raises(FormatoNoSoportado):
        leer_hoja(contenido, UMBRAL)


def _png(imagen) -> bytes:
    return cv2.imencode(".png", imagen)[1].tobytes()


def test_una_imagen_sin_contraste_es_ilegible():
    with pytest.raises(ImagenIlegible):
        leer_hoja(_png(np.full((1500, 1200), 200, np.uint8)), UMBRAL)


def test_una_imagen_demasiado_chica_es_ilegible(hoja_completa):
    with pytest.raises(ImagenIlegible):
        leer_hoja(fotografiar(hoja_completa, escala=0.2), UMBRAL)


def test_una_foto_movida_es_ilegible(hoja_completa):
    borrosa = cv2.GaussianBlur(hoja_completa, (0, 0), 9)

    with pytest.raises(ImagenIlegible):
        leer_hoja(fotografiar(borrosa), UMBRAL)


def test_una_hoja_sin_las_marcas_no_se_lee(hoja_completa):
    sin_marcas = hoja_completa.copy()
    for centro in FORMATO_V1.centros_de_las_marcas_mm:
        x, y = (round(v) for v in FORMATO_V1.a_px(centro))
        medio = round(FORMATO_V1.mm_a_px(7))
        sin_marcas[y - medio : y + medio, x - medio : x + medio] = PAPEL

    with pytest.raises(MarcasDeRegistroNoEncontradas):
        leer_hoja(fotografiar(sin_marcas), UMBRAL)


def test_otra_hoja_con_cuatro_marcas_no_se_reconoce():
    otra = np.full((3300, 2550), PAPEL, np.uint8)
    for centro in FORMATO_V1.centros_de_las_marcas_mm:
        x, y = (round(v) for v in FORMATO_V1.a_px(centro))
        medio = round(FORMATO_V1.mm_a_px(5))
        otra[y - medio : y + medio, x - medio : x + medio] = NEGRO
    for renglon in range(20):
        cv2.putText(otra, "Taller de calculo diferencial", (300, 500 + 120 * renglon),
                    cv2.FONT_HERSHEY_SIMPLEX, 3, NEGRO, 6)

    with pytest.raises(HojaNoReconocida):
        leer_hoja(fotografiar(otra), UMBRAL)


@pytest.mark.parametrize("umbral", [50, 101])
def test_un_umbral_fuera_de_rango_es_un_error_de_configuracion(hoja_completa, umbral):
    with pytest.raises(ValueError):
        leer_hoja(fotografiar(hoja_completa), umbral)
