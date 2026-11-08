"""Los pasos de `vision` sueltos: el ajuste fino de cada burbuja y la medida contra el papel
local, que son las dos piezas que salieron de las fotos del prototipo (R-05)."""

import zlib

import cv2
import numpy as np
import pytest

from omr import FORMATO_V1, FormatoNoSoportado, ImagenIlegible, vision
from omr.decision import DISPERSION_MINIMA_PARA_DUDAR, RELLENO_MAXIMO_DE_UNA_VACIA
from omr.vision import OSCURIDAD_DE_LA_TINTA, ajustar_centros, medir_burbuja
from herramientas.hojas_sinteticas import LAPIZ, PAPEL, hoja_marcada

F = FORMATO_V1


def _centros_de_respuesta() -> list[tuple[float, float]]:
    return [F.a_px(F.centro_de_la_respuesta_mm(n, c)) for n in range(1, 41) for c in range(4)]


def _correr(hoja, dx_mm: float, dy_mm: float):
    desplazamiento = np.array([[1, 0, F.mm_a_px(dx_mm)], [0, 1, F.mm_a_px(dy_mm)]], np.float32)
    alto, ancho = hoja.shape
    return cv2.warpAffine(hoja, desplazamiento, (ancho, alto), borderValue=PAPEL)


def test_el_ajuste_encuentra_las_burbujas_corridas_un_milimetro():
    """Lo que dejó la hoja sin aplanar en las fotos: hasta 1,1 mm de corrimiento."""
    hoja = _correr(hoja_marcada({n: "A" for n in range(1, 41)}), 1.0, -0.8)
    centros = _centros_de_respuesta()

    ajustados = ajustar_centros(hoja, centros, F)

    for (x, y), ajustado in zip(centros, ajustados):
        assert ajustado.centro[0] - x == pytest.approx(F.mm_a_px(1.0), abs=1.5)
        assert ajustado.centro[1] - y == pytest.approx(F.mm_a_px(-0.8), abs=1.5)


def test_una_hoja_borrosa_es_ilegible():
    borrosa = cv2.GaussianBlur(hoja_marcada({}), (0, 0), 8)

    with pytest.raises(ImagenIlegible):
        ajustar_centros(borrosa, _centros_de_respuesta(), F)


def test_una_burbuja_en_blanco_mide_cero_y_una_rellena_mide_uno():
    hoja = hoja_marcada({1: "A"})

    vacia = medir_burbuja(hoja, F.a_px(F.centro_de_la_respuesta_mm(1, 1)), F)
    llena = medir_burbuja(hoja, F.a_px(F.centro_de_la_respuesta_mm(1, 0)), F)

    assert vacia.relleno == pytest.approx(0, abs=0.02)
    assert llena.relleno == pytest.approx(1, abs=0.02)
    assert vacia.dispersion < 0.03


def test_la_medida_es_contra_el_papel_de_alrededor_y_no_contra_la_hoja():
    """Bajo una sombra pareja, la burbuja en blanco sigue en blanco: lo que se compara es el
    interior con el papel que está bajo la misma luz."""
    hoja = (hoja_marcada({1: "A"}).astype(np.float32) * 0.4).astype(np.uint8)

    vacia = medir_burbuja(hoja, F.a_px(F.centro_de_la_respuesta_mm(1, 1)), F)
    llena = medir_burbuja(hoja, F.a_px(F.centro_de_la_respuesta_mm(1, 0)), F)

    assert vacia.relleno == pytest.approx(0, abs=0.02)
    assert llena.relleno > 0.9


def test_media_burbuja_mide_la_mitad():
    hoja = hoja_marcada({}, a_medias=((3, "B"),))

    medida = medir_burbuja(hoja, F.a_px(F.centro_de_la_respuesta_mm(3, 1)), F)

    assert medida.relleno == pytest.approx(0.5, abs=0.1)


def test_el_grafito_con_brillo_casi_no_rellena_pero_deja_el_interior_desparejo():
    hoja = hoja_marcada({}, con_brillo=((2, "C"),))

    medida = medir_burbuja(hoja, F.a_px(F.centro_de_la_respuesta_mm(2, 2)), F)

    assert medida.relleno < RELLENO_MAXIMO_DE_UNA_VACIA
    assert medida.dispersion > DISPERSION_MINIMA_PARA_DUDAR


def test_el_lapiz_de_las_hojas_sinteticas_es_mas_oscuro_que_el_corte_de_tinta():
    """Guarda de la propia prueba: si alguien aclara el lápiz sintético, las demás dejan de medir
    lo que dicen medir."""
    assert 1 - LAPIZ / PAPEL > OSCURIDAD_DE_LA_TINTA


# --- El tamaño se lee del encabezado antes de decodificar --------------------------------------


def _png_que_dice_medir(ancho: int, alto: int) -> bytes:
    """Un PNG cuyo encabezado declara ese tamaño. Los datos no importan: lo que se prueba es que
    no se llegue a decodificarlos."""
    ihdr = ancho.to_bytes(4, "big") + alto.to_bytes(4, "big") + bytes([8, 0, 0, 0, 0])
    bloque = b"IHDR" + ihdr
    crc = zlib.crc32(bloque).to_bytes(4, "big")
    return b"\x89PNG\r\n\x1a\n" + len(ihdr).to_bytes(4, "big") + bloque + crc


def _jpeg_que_dice_medir(ancho: int, alto: int) -> bytes:
    """Un JPEG con un bloque de metadatos y después el marcador que dice su tamaño."""
    app0 = b"\xff\xe0" + (16).to_bytes(2, "big") + b"JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    sof0 = (
        b"\xff\xc0"
        + (11).to_bytes(2, "big")
        + bytes([8])
        + alto.to_bytes(2, "big")
        + ancho.to_bytes(2, "big")
        + bytes([1, 1, 0x11, 0])
    )
    return b"\xff\xd8" + app0 + sof0 + b"\xff\xd9"


@pytest.fixture
def sin_decodificar(monkeypatch):
    """Falla si alguien llega a llamar a OpenCV para decodificar."""

    def no_decodificar(*_args, **_kwargs):
        raise AssertionError("se decodificó una imagen que debía rechazarse por su encabezado")

    monkeypatch.setattr(vision.cv2, "imdecode", no_decodificar)


def test_un_png_enorme_queda_ilegible_sin_decodificarse(sin_decodificar):
    """Un PNG blanco de 10 000 × 10 000 px pesa 120 KB y mataba por memoria al worker de 96 MB,
    que al reiniciarse volvía a tomar la misma hoja."""
    with pytest.raises(ImagenIlegible, match="10000 × 10000"):
        vision.decodificar(_png_que_dice_medir(10_000, 10_000))


def test_un_jpeg_enorme_queda_ilegible_sin_decodificarse(sin_decodificar):
    with pytest.raises(ImagenIlegible, match="20000 × 20000"):
        vision.decodificar(_jpeg_que_dice_medir(20_000, 20_000))


def test_un_jpeg_de_48_megapixeles_si_se_decodifica():
    """Una foto de celular de 48 MP se lee a la mitad: el tope no la alcanza."""
    assert 8000 * 6000 <= vision.PIXELES_MAXIMOS_DE_UN_JPEG
    assert vision.tamano_del_encabezado(_jpeg_que_dice_medir(8000, 6000)) == ("jpeg", 8000, 6000)


def test_el_encabezado_de_imagenes_reales_dice_su_tamano():
    gris = np.full((30, 40), 200, np.uint8)
    _, png = cv2.imencode(".png", gris)
    _, jpg = cv2.imencode(".jpg", gris)

    assert vision.tamano_del_encabezado(png.tobytes()) == ("png", 40, 30)
    assert vision.tamano_del_encabezado(jpg.tobytes()) == ("jpeg", 40, 30)


def test_sin_un_tamano_legible_no_se_decodifica(sin_decodificar):
    with pytest.raises(FormatoNoSoportado):
        vision.decodificar(b"\xff\xd8\xff")
    with pytest.raises(FormatoNoSoportado):
        vision.decodificar(b"no es una imagen")
