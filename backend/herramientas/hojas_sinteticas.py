"""Hojas sintéticas: la plantilla marcada a gusto y «fotografiada» con perspectiva, giro, sombra,
desenfoque, ruido y compresión.

Las usan las pruebas de la lectura y la medición de EC-01 y EC-02 (`medir_lectura`). No llevan
datos de nadie (RNF-12): las marcas y el código los decide quien las genera.

Los tonos salen de las fotos del prototipo (R-05): el papel de una foto no es blanco puro, y el
lápiz y el esfero quedaron entre un 45 % y un 75 % más oscuros que el papel. La oscuridad de cada
marca se da así, como fracción del papel, que es como la mide `omr.vision`.
"""

import functools
import math
from dataclasses import dataclass

import cv2
import numpy as np

from omr.formato import FORMATO_V1, FormatoDeHoja, Punto
from omr.plantilla import dibujar_plantilla
from omr.vision import Imagen

# El papel de una foto no es blanco puro: deja lugar para un reflejo más claro que él. En las fotos
# del prototipo los reflejos llegaron a un 19 % por encima del papel; 255 sobre 215 es un 18 %.
PAPEL = 215
LAPIZ = 70

COMPLETA = "completa"
MEDIA = "media"
TENUE = "tenue"
BORRADA = "borrada"
CHULO = "chulo"
EQUIS = "equis"
BRILLO = "brillo"


@dataclass(frozen=True)
class Marca:
    """Lo que hizo el estudiante en una burbuja. `oscuridad` es la del trazo frente al papel (0 es
    papel, 1 es negro); `tamano`, el radio del relleno como fracción del de la burbuja;
    `corrimiento_mm`, cuánto se aleja del centro; `giro`, hacia dónde (media burbuja, chulo)."""

    tipo: str = COMPLETA
    oscuridad: float = 1 - LAPIZ / PAPEL
    tamano: float = 0.92
    corrimiento_mm: Punto = (0.0, 0.0)
    giro: float = 0.0


@dataclass(frozen=True)
class Foto:
    """Cómo se toma la foto de la hoja. `escala` lleva los 300 DPI de la plantilla a los píxeles
    de la foto (1,0 da 11,8 px/mm; la escala por omisión, 0,8, da 9,4). `perspectiva` angosta el borde de arriba, como fracción
    del ancho. `sombra` oscurece la mitad derecha a esa fracción de la luz (1 es sin sombra)."""

    giro: int = 0
    perspectiva: float = 0.0
    sombra: float = 1.0
    escala: float = 0.8
    desenfoque_px: float = 0.0
    ruido: float = 3.0
    calidad_jpeg: int = 90
    fondo: int = 90
    semilla: int = 7


@functools.lru_cache(maxsize=2)
def _plantilla_en_papel(formato: FormatoDeHoja) -> Imagen:
    return (dibujar_plantilla(formato).astype(np.float32) * (PAPEL / 255)).astype(np.uint8)


def hoja_en_blanco(formato: FormatoDeHoja = FORMATO_V1) -> Imagen:
    """La plantilla con el tono del papel de una foto, lista para marcar."""
    return _plantilla_en_papel(formato).copy()


def marcar(
    hoja: Imagen,
    centro_mm: Punto,
    marca: Marca,
    generador: np.random.Generator | None = None,
    formato: FormatoDeHoja = FORMATO_V1,
) -> None:
    """Dibuja una marca en la burbuja de centro `centro_mm`."""
    generador = generador or np.random.default_rng(5)
    x, y = formato.a_px(
        (centro_mm[0] + marca.corrimiento_mm[0], centro_mm[1] + marca.corrimiento_mm[1])
    )
    radio = formato.mm_a_px(formato.radio_de_la_burbuja_mm)
    lado = math.ceil(radio * 1.5)
    cx, cy = round(x), round(y)
    cuadro = hoja[cy - lado : cy + lado + 1, cx - lado : cx + lado + 1]
    filas, columnas = np.ogrid[-lado : lado + 1, -lado : lado + 1]
    filas = filas + (cy - y)
    columnas = columnas + (cx - x)
    distancia = np.hypot(filas, columnas)
    tono = PAPEL * (1 - marca.oscuridad)
    # El grafito no es parejo: un poco de grano alrededor del tono.
    grano = generador.normal(0, 6, cuadro.shape)
    trazo = np.clip(tono + grano, 0, 255)

    if marca.tipo in (COMPLETA, TENUE, BORRADA):
        dentro = distancia <= radio * marca.tamano
    elif marca.tipo == MEDIA:
        angulo = np.arctan2(filas, columnas) - marca.giro
        dentro = (distancia <= radio * marca.tamano) & (np.cos(angulo) <= 0)
    elif marca.tipo in (CHULO, EQUIS):
        lienzo = np.zeros(cuadro.shape, np.uint8)
        grosor = max(2, round(formato.mm_a_px(0.5)))
        r = radio * 1.1
        if marca.tipo == CHULO:
            puntos = np.array([[-0.6 * r, 0.0], [-0.1 * r, 0.6 * r], [0.9 * r, -0.9 * r]])
            cv2.polylines(lienzo, [np.round(puntos + lado).astype(np.int32)], False, 255, grosor)
        else:
            for a, b in (((-r, -r), (r, r)), ((-r, r), (r, -r))):
                cv2.line(lienzo, (round(a[0] + lado), round(a[1] + lado)),
                         (round(b[0] + lado), round(b[1] + lado)), 255, grosor)
        dentro = lienzo > 0
    elif marca.tipo == BRILLO:
        # Granos de un tercio de milímetro: un 30 % refleja la luz (un 18 % más claro que el papel)
        # y el resto queda entre un 8 % y `oscuridad` más oscuro que él. En las fotos del
        # prototipo, el percentil 90 de una marca con brillo fue de 0,14 a 0,26: con 0,15 la marca
        # casi no rellena, como la del código en la foto desde arriba (0,06). Un reflejo de un
        # píxel suelto no sobrevive al JPEG, y en las fotos no los hay.
        dentro = distancia <= radio * marca.tamano
        forma = (cuadro.shape[0] // 4 + 1, cuadro.shape[1] // 4 + 1)
        tope = max(0.08, marca.oscuridad)
        granos = np.where(
            generador.random(forma) < 0.3, 255.0, PAPEL * (1 - generador.uniform(0.08, tope, forma))
        )
        tonos = np.kron(granos, np.ones((4, 4)))[: cuadro.shape[0], : cuadro.shape[1]]
        cuadro[dentro] = tonos[dentro].astype(np.uint8)
        return
    else:
        raise ValueError(f"Marca desconocida: {marca.tipo}")
    cuadro[dentro] = np.minimum(cuadro[dentro], trazo[dentro]).astype(np.uint8)


def hoja_marcada(
    respuestas: dict[int, str],
    codigo: str | None = None,
    a_medias: tuple[tuple[int, str], ...] = (),
    con_brillo: tuple[tuple[int, str], ...] = (),
    formato: FormatoDeHoja = FORMATO_V1,
) -> Imagen:
    """La plantilla con marcas de lápiz completas, para las pruebas.

    `respuestas` lleva, por número de pregunta, las letras marcadas («AC» es doble marca).
    `codigo` son los ocho dígitos, sin la `T`. `a_medias` rellena solo media burbuja, y
    `con_brillo` la rellena con el reflejo del grafito, en el caso más claro que se vio."""
    hoja = hoja_en_blanco(formato)
    for numero, letras in respuestas.items():
        for letra in letras:
            marcar(hoja, formato.centro_de_la_respuesta_mm(numero, "ABCD".index(letra)), Marca())
    if codigo is not None:
        for posicion, digito in enumerate(codigo, start=1):
            marcar(hoja, formato.centro_del_digito_mm(posicion, int(digito)), Marca())
    for numero, letra in a_medias:
        marcar(hoja, formato.centro_de_la_respuesta_mm(numero, "ABCD".index(letra)),
               Marca(MEDIA))
    for numero, letra in con_brillo:
        marcar(hoja, formato.centro_de_la_respuesta_mm(numero, "ABCD".index(letra)),
               Marca(BRILLO, oscuridad=0.15))
    return hoja


def fotografiar(hoja: Imagen, foto: Foto | None = None, **campos: float) -> bytes:
    """La hoja como una foto de celular, en JPEG: reducida, sobre una mesa, en perspectiva, con
    sombra, desenfoque y ruido si se piden, y girada `giro` cuartos de vuelta. Los campos sueltos
    (`giro=2`, `sombra=0.45`...) reemplazan los de `foto`."""
    foto = foto or Foto()
    if campos:
        foto = Foto(**{**foto.__dict__, **campos})
    # Primero se reduce con promedio, como la óptica de una cámara; la perspectiva se aplica a la
    # hoja ya reducida.
    chica = np.asarray(
        cv2.resize(hoja, None, fx=foto.escala, fy=foto.escala, interpolation=cv2.INTER_AREA),
        np.uint8,
    )
    alto, ancho = chica.shape
    a, h = float(ancho), float(alto)
    margen = 0.08 * h
    lienzo = (round(a + 2 * margen), round(h + 2 * margen))
    entrada = 0.5 * foto.perspectiva * a
    destino = np.array(
        [[margen + entrada, margen], [margen + a - entrada, margen], [margen + a, margen + h],
         [margen, margen + h]],
        np.float32,
    )
    origen = np.array([[0, 0], [ancho, 0], [ancho, alto], [0, alto]], np.float32)
    imagen = cv2.warpPerspective(
        chica, cv2.getPerspectiveTransform(origen, destino), lienzo,
        flags=cv2.INTER_LINEAR, borderValue=foto.fondo,
    ).astype(np.float32)
    if foto.sombra < 1:
        luz = np.ones(imagen.shape, np.float32)
        luz[:, imagen.shape[1] // 2 :] = foto.sombra
        imagen *= np.asarray(cv2.GaussianBlur(luz, (0, 0), 0.02 * imagen.shape[1]), np.float32)
    if foto.desenfoque_px > 0:
        imagen = np.asarray(cv2.GaussianBlur(imagen, (0, 0), foto.desenfoque_px), np.float32)
    imagen = np.rot90(imagen, -foto.giro)
    imagen = imagen + np.random.default_rng(foto.semilla).normal(0, foto.ruido, imagen.shape)
    final = np.clip(imagen, 0, 255).astype(np.uint8)
    return cv2.imencode(".jpg", final, [cv2.IMWRITE_JPEG_QUALITY, foto.calidad_jpeg])[1].tobytes()


def patron(numero: int) -> str:
    """La respuesta de la pregunta en el patrón A, B, C, D, A… de la hoja del prototipo."""
    return "ABCD"[(numero - 1) % 4]
