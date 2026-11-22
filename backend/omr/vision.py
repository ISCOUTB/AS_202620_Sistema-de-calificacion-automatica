"""El procesamiento de imagen. Con `plantilla`, que los usa para dibujar la hoja, es el único
archivo del sistema que importa OpenCV y numpy.

Recibe píxeles y devuelve píxeles o números; no sabe qué es una pregunta, una clave ni una nota.
Separarlo así deja que las decisiones (`decision`) se prueben con números escritos a mano, sin
imágenes, y que cambiar de técnica de visión no toque la calificación.

**Por qué se lee en posiciones fijas y no buscando círculos.** Detectar los contornos de las
burbujas y ordenarlos tiene un modo de fallo silencioso: si una burbuja no se detecta, todas las
siguientes se corren un lugar y la hoja sale mal calificada sin que nadie lo note, que es lo que
EC-02 prohíbe. Con las marcas de registro, la imagen se lleva a las coordenadas de la plantilla y
cada burbuja se mide donde el formato dice que está.

**Lo que enseñaron las fotos del prototipo (R-05).** Tres fotos de celular de una misma hoja
(desde arriba, inclinada unos 30° y con una sombra encima) fijaron las decisiones de este archivo:

- Un umbral para toda la hoja no sirve: con la sombra, burbujas vacías salían llenas. Cada burbuja
  se mide contra el papel que la rodea, que está bajo la misma luz.
- Las cuatro marcas dejan errores de hasta 1 mm, porque la hoja no queda plana, y con eso el
  contorno impreso entra en la zona que se mide. Cada burbuja se ajusta buscando su contorno cerca
  de donde debería estar, y el corrimiento se suaviza con el de las vecinas: una burbuja rellena,
  que no muestra el contorno, toma el de las de al lado. La búsqueda llega a 1,5 mm y las burbujas
  están a 7 mm o más, así que el ajuste no puede saltar a la burbuja vecina.
- El grafito brilla: con la luz de frente, una marca de lápiz puede verse casi tan clara como el
  papel. Lo que no pierde es la textura: granos que reflejan y granos oscuros, mientras que una
  burbuja vacía, o bien borrada, es pareja. `medir_burbuja` mide esa dispersión y `decision` no
  da por vacía una burbuja despareja.
- En una hoja girada 180°, casi todas las burbujas de respuesta caen sobre otras burbujas. Por eso
  la orientación no se deduce de las burbujas sino del parecido de la hoja entera con la plantilla.

Cada corte de este archivo es una constante con nombre, con el dato que la fijó.
"""

import functools
import math
from typing import NamedTuple

import cv2
import numpy as np
import numpy.typing as npt

from omr.errores import (
    FormatoNoSoportado,
    HojaNoReconocida,
    ImagenIlegible,
    MarcasDeRegistroNoEncontradas,
)
from omr.formato import FormatoDeHoja, Punto

__all__ = [
    "Imagen",
    "Cuadrilatero",
    "Comparable",
    "CentroAjustado",
    "MedidaDeBurbuja",
    "tamano_del_encabezado",
    "decodificar",
    "comprobar_calidad",
    "localizar_marcas_de_registro",
    "orientar",
    "rectificar",
    "ajustar_centros",
    "medir_burbuja",
    "preparar_para_comparar",
    "recortar_fila",
]

# Una imagen en escala de grises, como la maneja OpenCV.
Imagen = npt.NDArray[np.uint8]
# Las cuatro marcas: en la imagen, en el orden de las agujas del reloj desde la de arriba a la
# izquierda; después de `orientar`, en el orden de `centros_de_las_marcas_mm`.
Cuadrilatero = tuple[Punto, Punto, Punto, Punto]
# Una hoja reducida y filtrada para compararla con la plantilla (`preparar_para_comparar`).
Comparable = npt.NDArray[np.float32]

# --- Decodificar y calidad -------------------------------------------------------------------

# Una foto de 48 megapíxeles ocupa 48 MB en gris, y el worker tiene 96 MB. Más allá de este
# tamaño, el JPEG se decodifica a la mitad o a la cuarta parte, que la biblioteca hace sin armar
# la imagen completa; las fotos del prototipo (7,6 a 9,9 megapíxeles) se leen enteras.
PIXELES_MAXIMOS = 16_000_000
# Un PNG, en cambio, no se decodifica reducido: OpenCV arma la imagen entera y después la achica.
# Un PNG blanco de 10 000 × 10 000 px pesa 120 KB y pide más de 100 MB al decodificarse: en un
# contenedor de 96 MB el worker moría por memoria y, al reiniciarse, volvía a tomar la misma hoja.
# Por eso el tamaño se lee del encabezado antes de decodificar: un PNG puede tener hasta
# `PIXELES_MAXIMOS`, y un JPEG hasta 16 veces eso, que a la cuarta parte de lado vuelve a ser
# `PIXELES_MAXIMOS`. Las fotos que prepara el sitio tienen 3 200 px de lado mayor, en JPEG.
PIXELES_MAXIMOS_DE_UN_JPEG = 16 * PIXELES_MAXIMOS
# Los marcadores de un JPEG que dicen el tamaño de la imagen (SOF0 a SOF15, sin DHT, JPG ni DAC).
_MARCADORES_DE_TAMANO_JPEG = frozenset(
    {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}
)
# Por debajo de esto ni la hoja entera alcanza la resolución mínima: hay 186 mm entre las marcas.
LADO_MINIMO_PX = 1450
# Diferencia mínima entre los grises más oscuros y los más claros (percentiles 1 y 99). Una foto
# oscurecida al 15 % todavía se leyó bien con unos 35 niveles; una tapada o en blanco no llega.
CONTRASTE_MINIMO = 20

# --- Marcas de registro ----------------------------------------------------------------------

# Las marcas se buscan en una copia reducida: alcanza para encontrarlas y cuesta poco.
LADO_DE_DETECCION_PX = 1200
# Lado de una marca, como fracción del lado mayor de la copia reducida. En las fotos del
# prototipo fue 0,035, con la hoja llenando la foto; el mínimo admite una hoja que ocupe un
# tercio del alto.
LADO_MINIMO_DE_UNA_MARCA = 0.012
LADO_MAXIMO_DE_UNA_MARCA = 0.08
# Un cuadrado lleno ocupa casi todo su rectángulo; un círculo, el 79 %. En las fotos, las marcas
# dieron de 0,95 a 0,99.
EXTENSION_MINIMA_DE_UNA_MARCA = 0.85
# Tinta dentro del contorno: separa las marcas de las casillas del código, que son cuadrados
# huecos. Las marcas dieron 1,0.
TINTA_MINIMA_DE_UNA_MARCA = 0.85
# Una inclinación de 30° deja el cuadrado en 1,2 a 1. Dos a uno ya no es la marca.
ASPECTO_MAXIMO_DE_UNA_MARCA = 2.0

# --- Orientación y resolución ----------------------------------------------------------------

# La hoja se compara con la plantilla a un octavo de la resolución, sin las marcas y sin las
# variaciones de luz (se resta un desenfoque de 4 mm). Derecha, las tres fotos dieron de 0,51 a
# 0,60; en las otras tres orientaciones, 0,08 como mucho, y una hoja con las cuatro marcas y
# otro contenido, 0,03.
ESCALA_DE_LA_COMPARACION = 8
PARECIDO_MINIMO_CON_LA_PLANTILLA = 0.30
# Píxeles por milímetro en el lado más corto, en perspectiva, entre dos marcas. Lo fija el brillo
# del grafito: sus granos, de unos 0,3 mm, tienen que verse para que la marca no parezca vacía.
# En hojas sintéticas con el brillo de las fotos, desde 7,9 px/mm la dispersión de una marca con
# brillo no bajó de 0,077, aun desenfocada 1,2 px; a 5,9 px/mm bajó a 0,060, debajo del corte de
# `decision`. Una foto de celular de la hoja entera da de 11 a 13 px/mm, y un escaneo a 200 DPI,
# 7,9. Un escaneo a 150 DPI o una foto recomprimida no alcanzan, y la hoja queda ilegible con el
# motivo: es mejor que una incorrecta que nadie revisa.
RESOLUCION_MINIMA_PX_POR_MM = 7.5

# --- Ajuste fino de cada burbuja --------------------------------------------------------------

# Hasta dónde se busca el contorno de cada burbuja alrededor de su posición. Las fotos se corrieron
# hasta 1,1 mm.
BUSQUEDA_DEL_AJUSTE_MM = 1.5
# Las burbujas cuyo corrimiento se promedia (con la mediana) para ajustar una.
RADIO_DE_LOS_VECINOS_MM = 15.0
# Parecido mínimo del contorno encontrado para que cuente como vecino.
PARECIDO_MINIMO_DE_UN_VECINO = 0.5
# Mediana del parecido de todos los contornos: es la medida de nitidez de la hoja. Las fotos
# dieron de 0,75 a 0,81; desenfocadas 2 px, de 0,64 a 0,67, y 4 px, de 0,39 a 0,43. Con 6 px, la
# foto inclinada leyó siete marcas como vacías.
NITIDEZ_MINIMA = 0.50

# --- Medida de una burbuja --------------------------------------------------------------------

# Se mide el interior hasta este radio, para dejar fuera el contorno impreso aun con un resto de
# corrimiento.
FRACCION_DEL_RADIO_QUE_SE_MIDE = 0.75
# El papel de referencia: un anillo alrededor de la burbuja, fuera de su contorno y antes del de
# las vecinas (que está a 4,5 mm del centro). Se toma la mediana, que no se deja llevar por la
# tinta de una marca que se sale.
PAPEL_DESDE_MM = 3.0
PAPEL_HASTA_MM = 3.5
# Cuánto cuenta cada píxel según cuánto más oscuro que el papel es: nada hasta el 10 %, todo desde
# el 35 %, y en proporción entre los dos. En las fotos, el interior de una burbuja vacía quedó por
# debajo del 5 %, y el lápiz y el esfero sin brillo, entre el 45 % y el 75 %.
OSCURIDAD_DEL_PAPEL = 0.10
OSCURIDAD_DE_LA_TINTA = 0.35


class CentroAjustado(NamedTuple):
    """Dónde quedó una burbuja después del ajuste fino, en píxeles de la hoja rectificada, y cuánto
    se parece a un contorno impreso lo mejor que se encontró cerca (de -1 a 1)."""

    centro: Punto
    contorno: float


class MedidaDeBurbuja(NamedTuple):
    """`relleno`: cuánto del interior está cubierto, de 0 a 1, contando cada píxel por su
    oscuridad. `dispersion`: la desviación estándar de esa oscuridad, que dice si el interior es
    parejo (papel, o tinta pareja) o desparejo (grafito con brillo, un trazo)."""

    relleno: float
    dispersion: float


def tamano_del_encabezado(contenido: bytes) -> tuple[str, int, int] | None:
    """El formato (`"png"` o `"jpeg"`) y el ancho y el alto que declara el encabezado de la
    imagen, sin decodificarla, o None si no es un PNG ni un JPEG cuyo tamaño se pueda leer.

    En un PNG, el tamaño va siempre en el mismo lugar, en el bloque IHDR. En un JPEG va en el
    primer marcador SOF, después de los bloques de metadatos, que se saltan por su largo: así no
    se confunde con el de la miniatura que trae el EXIF de una foto, que va dentro de uno de
    ellos."""
    if contenido.startswith(b"\x89PNG\r\n\x1a\n") and contenido[12:16] == b"IHDR":
        if len(contenido) < 24:
            return None
        ancho = int.from_bytes(contenido[16:20], "big")
        alto = int.from_bytes(contenido[20:24], "big")
        return "png", ancho, alto
    if not contenido.startswith(b"\xff\xd8"):
        return None
    posicion = 2
    while posicion + 4 <= len(contenido):
        if contenido[posicion] != 0xFF:
            return None
        marcador = contenido[posicion + 1]
        if marcador == 0xFF:
            # Bytes de relleno entre marcadores.
            posicion += 1
            continue
        if marcador == 0x01 or 0xD0 <= marcador <= 0xD7:
            # Marcadores sin largo.
            posicion += 2
            continue
        if marcador in (0xD9, 0xDA):
            # El fin de la imagen o el comienzo de los datos, sin haber dicho el tamaño.
            return None
        largo = int.from_bytes(contenido[posicion + 2 : posicion + 4], "big")
        if marcador in _MARCADORES_DE_TAMANO_JPEG:
            if posicion + 9 > len(contenido):
                return None
            alto = int.from_bytes(contenido[posicion + 5 : posicion + 7], "big")
            ancho = int.from_bytes(contenido[posicion + 7 : posicion + 9], "big")
            return "jpeg", ancho, alto
        if largo < 2:
            return None
        posicion += 2 + largo
    return None


def decodificar(contenido: bytes) -> Imagen:
    """Decodifica PNG o JPG y devuelve la imagen en gris, ya girada según su EXIF.

    Lanza `FormatoNoSoportado` si los bytes no son una imagen que OpenCV decodifique, y también
    si son un PDF: `ingesta` lo acepta, pero rasterizarlo pide otra dependencia y queda fuera de
    esta versión. Lanza `ImagenIlegible`, sin decodificar nada, si el encabezado declara más
    píxeles de los que el worker puede armar (`PIXELES_MAXIMOS` en un PNG,
    `PIXELES_MAXIMOS_DE_UN_JPEG` en un JPEG)."""
    if contenido.startswith(b"%PDF"):
        raise FormatoNoSoportado("La lectura de PDF queda fuera de esta versión")
    if not contenido:
        raise FormatoNoSoportado("El archivo está vacío")
    encabezado = tamano_del_encabezado(contenido)
    if encabezado is None:
        raise FormatoNoSoportado("No se pudo leer el tamaño de la imagen en su encabezado")
    formato, ancho, alto = encabezado
    tope = PIXELES_MAXIMOS if formato == "png" else PIXELES_MAXIMOS_DE_UN_JPEG
    if ancho * alto > tope:
        raise ImagenIlegible(
            f"La imagen mide {ancho} × {alto} px; un {formato.upper()} puede tener hasta "
            f"{tope // 1_000_000} megapíxeles"
        )
    datos = np.frombuffer(contenido, np.uint8)
    try:
        # Primero a un octavo, que es barato, para saber el tamaño sin armar la imagen entera.
        muestra = cv2.imdecode(datos, cv2.IMREAD_REDUCED_GRAYSCALE_8)
        if muestra is None:
            raise FormatoNoSoportado("OpenCV no reconoce el archivo como imagen")
        pixeles = muestra.shape[0] * muestra.shape[1] * 64
        modo = cv2.IMREAD_GRAYSCALE
        if pixeles > PIXELES_MAXIMOS:
            modo = cv2.IMREAD_REDUCED_GRAYSCALE_2
        if pixeles > 4 * PIXELES_MAXIMOS:
            modo = cv2.IMREAD_REDUCED_GRAYSCALE_4
        gris = cv2.imdecode(datos, modo)
    except cv2.error as error:
        raise FormatoNoSoportado(f"OpenCV no pudo decodificar el archivo: {error}") from error
    if gris is None:
        raise FormatoNoSoportado("OpenCV no reconoce el archivo como imagen")
    return np.asarray(gris, np.uint8)


def comprobar_calidad(gris: Imagen) -> None:
    """Lanza `ImagenIlegible` si la imagen es demasiado chica o no tiene contraste (una foto
    tapada, en blanco o quemada). La nitidez se comprueba después, en `ajustar_centros`, con los
    contornos impresos de las burbujas, que dicen más que cualquier medida de la foto entera."""
    if min(gris.shape) < LADO_MINIMO_PX:
        raise ImagenIlegible(
            f"La imagen mide {gris.shape[1]} × {gris.shape[0]} px; hace falta al menos "
            f"{LADO_MINIMO_PX} px de lado"
        )
    histograma = cv2.calcHist([gris], [0], None, [256], [0, 256]).ravel().cumsum()
    total = histograma[-1]
    oscuro = int(np.searchsorted(histograma, 0.01 * total))
    claro = int(np.searchsorted(histograma, 0.99 * total))
    if claro - oscuro < CONTRASTE_MINIMO:
        raise ImagenIlegible(f"La imagen no tiene contraste: {claro - oscuro} niveles de gris")


def localizar_marcas_de_registro(gris: Imagen) -> Cuadrilatero:
    """Encuentra los centros de las cuatro marcas, en el orden de la imagen.

    Busca cuadrados llenos en una copia reducida, con la luz emparejada (se divide por el fondo
    estimado con un máximo local). Entre los que pasan los filtros, toma el más cercano a cada
    esquina. Lanza `MarcasDeRegistroNoEncontradas` si no hay cuatro."""
    # Se compara el lado en píxeles, que es entero, y no la escala: comparar flotantes con `==`
    # depende del redondeo (SonarCloud, S1244). Las dos condiciones dicen lo mismo.
    escala = min(1.0, LADO_DE_DETECCION_PX / max(gris.shape))
    chica = gris if max(gris.shape) <= LADO_DE_DETECCION_PX else cv2.resize(
        gris, None, fx=escala, fy=escala, interpolation=cv2.INTER_AREA
    )
    lado = max(chica.shape)
    # El fondo es el máximo en una ventana mayor que una marca: borra la tinta y deja la luz.
    nucleo = max(3, lado // 15)
    fondo = cv2.dilate(chica, cv2.getStructuringElement(cv2.MORPH_RECT, (nucleo, nucleo)))
    fondo = cv2.GaussianBlur(fondo, (0, 0), nucleo / 4)
    pareja = cv2.divide(chica, fondo, scale=255)
    _, tinta = cv2.threshold(pareja, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
    contornos, _ = cv2.findContours(tinta, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    candidatos: list[Punto] = []
    area_minima = (LADO_MINIMO_DE_UNA_MARCA * lado) ** 2
    area_maxima = (LADO_MAXIMO_DE_UNA_MARCA * lado) ** 2
    for contorno in contornos:
        area = cv2.contourArea(contorno)
        if not area_minima <= area <= area_maxima:
            continue
        aproximado = cv2.approxPolyDP(contorno, 0.04 * cv2.arcLength(contorno, True), True)
        if len(aproximado) != 4 or not cv2.isContourConvex(aproximado):
            continue
        _, (ancho, alto), _ = cv2.minAreaRect(contorno)
        if area < EXTENSION_MINIMA_DE_UNA_MARCA * ancho * alto:
            continue
        if max(ancho, alto) > ASPECTO_MAXIMO_DE_UNA_MARCA * min(ancho, alto):
            continue
        x, y, w, h = cv2.boundingRect(contorno)
        mascara = np.zeros((h, w), np.uint8)
        cv2.drawContours(mascara, [contorno - np.array([x, y])], -1, 255, cv2.FILLED)
        if cv2.mean(tinta[y : y + h, x : x + w], mascara)[0] < 255 * TINTA_MINIMA_DE_UNA_MARCA:
            continue
        momentos = cv2.moments(contorno)
        candidatos.append((momentos["m10"] / momentos["m00"], momentos["m01"] / momentos["m00"]))

    if len(candidatos) < 4:
        raise MarcasDeRegistroNoEncontradas(f"Se encontraron {len(candidatos)} de las 4 marcas")
    esquinas = (
        min(candidatos, key=lambda p: p[0] + p[1]),
        max(candidatos, key=lambda p: p[0] - p[1]),
        max(candidatos, key=lambda p: p[0] + p[1]),
        min(candidatos, key=lambda p: p[0] - p[1]),
    )
    if len(set(esquinas)) < 4:
        raise MarcasDeRegistroNoEncontradas("Las marcas encontradas no forman las cuatro esquinas")
    sup_izq, sup_der, inf_der, inf_izq = ((x / escala, y / escala) for x, y in esquinas)
    return (sup_izq, sup_der, inf_der, inf_izq)


def orientar(
    gris: Imagen,
    marcas: Cuadrilatero,
    formato: FormatoDeHoja,
    plantilla: Comparable,
) -> Cuadrilatero:
    """Reordena las marcas como las del formato, eligiendo de las cuatro orientaciones posibles la
    que más se parece a la plantilla (`preparar_para_comparar`). Así se lee igual una foto de lado
    o de cabeza.

    Lanza `HojaNoReconocida` si ninguna orientación se parece lo suficiente, e `ImagenIlegible` si
    la hoja quedó con menos resolución de la que hace falta."""
    # La foto se reduce con promedio antes de enderezarla: llevarla directo a un octavo con la
    # homografía tomaría un píxel de cada ocho y perdería los contornos finos. Se deja al doble de
    # la resolución de la comparación; el perímetro de las marcas no depende de la orientación.
    perimetro_mm = _perimetro(formato.centros_de_las_marcas_mm)
    objetivo = 2 * formato.dpi / 25.4 / ESCALA_DE_LA_COMPARACION
    factor = min(1.0, objetivo * perimetro_mm / _perimetro(marcas))
    reducida = gris
    if factor < 1.0:
        reducida = np.asarray(
            cv2.resize(gris, None, fx=factor, fy=factor, interpolation=cv2.INTER_AREA), np.uint8
        )
    parecidos = []
    for giro in range(4):
        orden = marcas[giro:] + marcas[:giro]
        cuadrilatero: Cuadrilatero = (orden[0], orden[1], orden[2], orden[3])
        reducido: Cuadrilatero = (
            _escalar(orden[0], factor),
            _escalar(orden[1], factor),
            _escalar(orden[2], factor),
            _escalar(orden[3], factor),
        )
        parecidos.append((_parecido(reducida, reducido, formato, plantilla), cuadrilatero))
    mejor, orientadas = max(parecidos, key=lambda par: par[0])
    if mejor < PARECIDO_MINIMO_CON_LA_PLANTILLA:
        raise HojaNoReconocida(
            f"La hoja se parece {mejor:.2f} a la plantilla {formato.version}; el mínimo es "
            f"{PARECIDO_MINIMO_CON_LA_PLANTILLA}"
        )
    resolucion = min(
        math.dist(orientadas[i], orientadas[(i + 1) % 4])
        / math.dist(formato.centros_de_las_marcas_mm[i], formato.centros_de_las_marcas_mm[(i + 1) % 4])
        for i in range(4)
    )
    if resolucion < RESOLUCION_MINIMA_PX_POR_MM:
        raise ImagenIlegible(
            f"La hoja quedó a {resolucion:.1f} px/mm; el mínimo es {RESOLUCION_MINIMA_PX_POR_MM}"
        )
    return orientadas


def rectificar(gris: Imagen, marcas: Cuadrilatero, formato: FormatoDeHoja) -> Imagen:
    """Lleva la hoja a las coordenadas de la plantilla con una homografía. Corrige tanto la
    inclinación de un escaneo como la perspectiva de una foto. Lo que queda fuera de la foto
    sale blanco."""
    homografia = cv2.getPerspectiveTransform(
        np.array(marcas, np.float32), _marcas_en_px(formato, 1.0)
    )
    rectificada = cv2.warpPerspective(
        gris,
        homografia,
        formato.tamano_en_px(),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=255,
    )
    return np.asarray(rectificada, np.uint8)


def ajustar_centros(
    hoja: Imagen, centros: list[Punto], formato: FormatoDeHoja
) -> list[CentroAjustado]:
    """Corrige la posición de cada burbuja con su contorno impreso y el de sus vecinas.

    Lanza `ImagenIlegible` si los contornos, en conjunto, no se distinguen: la imagen está
    borrosa y medir el relleno ya no es confiable."""
    anillo = _anillo(formato)
    busqueda = round(formato.mm_a_px(BUSQUEDA_DEL_AJUSTE_MM))
    medio = anillo.shape[0] // 2 + busqueda
    crudos = []
    for x, y in centros:
        cx, cy = round(x), round(y)
        ventana = hoja[cy - medio : cy + medio + 1, cx - medio : cx + medio + 1]
        if ventana.shape != (2 * medio + 1, 2 * medio + 1):
            crudos.append((0, 0, -1.0))
            continue
        oscuridad = 255 - ventana.astype(np.float32)
        resultado = cv2.matchTemplate(oscuridad, anillo, cv2.TM_CCOEFF_NORMED)
        _, mejor, _, (bx, by) = cv2.minMaxLoc(resultado)
        # Una ventana pareja (papel liso o tinta pareja) no tiene contorno que comparar.
        crudos.append((bx - busqueda, by - busqueda, mejor if math.isfinite(mejor) else -1.0))

    corrimientos = np.array([(dx, dy) for dx, dy, _ in crudos], np.float32)
    parecidos = np.array([parecido for _, _, parecido in crudos], np.float32)
    nitidez = float(np.median(parecidos))
    if nitidez < NITIDEZ_MINIMA:
        raise ImagenIlegible(
            f"Los contornos de las burbujas no se distinguen ({nitidez:.2f}; el mínimo es "
            f"{NITIDEZ_MINIMA}): la imagen está borrosa"
        )
    puntos = np.array(centros, np.float32)
    distancias = np.hypot(
        puntos[:, None, 0] - puntos[None, :, 0], puntos[:, None, 1] - puntos[None, :, 1]
    )
    vecinos = (distancias <= formato.mm_a_px(RADIO_DE_LOS_VECINOS_MM)) & (
        parecidos[None, :] >= PARECIDO_MINIMO_DE_UN_VECINO
    )
    ajustados = []
    for i, (x, y) in enumerate(centros):
        dx, dy = (0.0, 0.0)
        if vecinos[i].any():
            dx, dy = (float(v) for v in np.median(corrimientos[vecinos[i]], axis=0))
        ajustados.append(CentroAjustado((x + dx, y + dy), float(parecidos[i])))
    return ajustados


def medir_burbuja(hoja: Imagen, centro: Punto, formato: FormatoDeHoja) -> MedidaDeBurbuja:
    """Mide una burbuja de la hoja rectificada contra el papel que la rodea."""
    x, y = centro
    afuera = formato.mm_a_px(PAPEL_HASTA_MM)
    x0, y0 = max(0, math.floor(x - afuera) - 1), max(0, math.floor(y - afuera) - 1)
    x1, y1 = math.ceil(x + afuera) + 2, math.ceil(y + afuera) + 2
    parche = hoja[y0:y1, x0:x1].astype(np.float32)
    filas, columnas = np.ogrid[y0 : y0 + parche.shape[0], x0 : x0 + parche.shape[1]]
    distancia = np.hypot(columnas - x, filas - y)
    papel = float(
        np.median(parche[(distancia >= formato.mm_a_px(PAPEL_DESDE_MM)) & (distancia <= afuera)])
    )
    radio = FRACCION_DEL_RADIO_QUE_SE_MIDE * formato.mm_a_px(formato.radio_de_la_burbuja_mm)
    oscuridad = 1 - parche[distancia <= radio] / max(papel, 1.0)
    cobertura = np.clip(
        (oscuridad - OSCURIDAD_DEL_PAPEL) / (OSCURIDAD_DE_LA_TINTA - OSCURIDAD_DEL_PAPEL), 0, 1
    )
    return MedidaDeBurbuja(
        relleno=float(cobertura.mean()),
        dispersion=float(oscuridad.std()),
    )


# --- Recortes para la revisión ----------------------------------------------------------------

# La fila de una pregunta en revisión, como la ve el profesor (RF-08): desde el número impreso, que
# termina 5,5 mm antes de la burbuja A, hasta un poco después de la última. Hacia arriba y hacia
# abajo, la mitad de la distancia entre filas (7 mm) y un poco menos, para no mostrar las vecinas.
MARGEN_ANTES_DE_LA_FILA_MM = 12.0
MARGEN_DESPUES_DE_LA_FILA_MM = 5.0
MEDIA_ALTURA_DE_LA_FILA_MM = 3.4


def recortar_fila(hoja: Imagen, centros: list[Punto], formato: FormatoDeHoja) -> bytes | None:
    """La fila de burbujas cuyos centros ajustados (en píxeles de la hoja rectificada) se dan, en
    PNG. Solo la fila: el código del estudiante está en otra parte de la hoja. None si no se pudo
    codificar."""
    xs = [x for x, _ in centros]
    y = sum(y for _, y in centros) / len(centros)
    alto, ancho = hoja.shape[:2]
    izquierda = max(0, int(min(xs) - formato.mm_a_px(MARGEN_ANTES_DE_LA_FILA_MM)))
    derecha = min(ancho, int(max(xs) + formato.mm_a_px(MARGEN_DESPUES_DE_LA_FILA_MM)))
    arriba = max(0, int(y - formato.mm_a_px(MEDIA_ALTURA_DE_LA_FILA_MM)))
    abajo = min(alto, int(y + formato.mm_a_px(MEDIA_ALTURA_DE_LA_FILA_MM)))
    if derecha <= izquierda or abajo <= arriba:
        return None
    correcto, png = cv2.imencode(".png", hoja[arriba:abajo, izquierda:derecha])
    return bytes(png) if correcto else None


def preparar_para_comparar(hoja: Imagen, formato: FormatoDeHoja) -> Comparable:
    """Una hoja en coordenadas de la plantilla (la plantilla misma, en la lectura), reducida y
    filtrada como la compara `orientar`."""
    ancho, alto = _tamano_de_comparacion(formato)
    chica = cv2.resize(hoja, (ancho, alto), interpolation=cv2.INTER_AREA)
    return _filtrar(np.asarray(chica, np.uint8), formato)


def _parecido(
    gris: Imagen, marcas: Cuadrilatero, formato: FormatoDeHoja, plantilla: Comparable
) -> float:
    escala = 1 / ESCALA_DE_LA_COMPARACION
    homografia = cv2.getPerspectiveTransform(
        np.array(marcas, np.float32), _marcas_en_px(formato, escala)
    )
    chica = cv2.warpPerspective(
        gris,
        homografia,
        _tamano_de_comparacion(formato),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=255,
    )
    resultado = cv2.matchTemplate(
        _filtrar(np.asarray(chica, np.uint8), formato), plantilla, cv2.TM_CCOEFF_NORMED
    )
    return float(resultado[0, 0])


def _filtrar(chica: Imagen, formato: FormatoDeHoja) -> Comparable:
    """Resta las variaciones lentas de luz (un desenfoque de unos 4 mm), suaviza un poco y borra
    las marcas, que se parecen en cualquier orientación."""
    flotante = chica.astype(np.float32)
    sigma = 4 * formato.dpi / 25.4 / ESCALA_DE_LA_COMPARACION
    detalle = flotante - cv2.GaussianBlur(flotante, (0, 0), sigma)
    return cv2.GaussianBlur(detalle, (0, 0), 1.0) * _sin_marcas(formato)


@functools.lru_cache(maxsize=4)
def _sin_marcas(formato: FormatoDeHoja) -> npt.NDArray[np.float32]:
    ancho, alto = _tamano_de_comparacion(formato)
    mascara = np.ones((alto, ancho), np.float32)
    escala = 1 / ESCALA_DE_LA_COMPARACION
    medio = formato.mm_a_px(formato.lado_de_la_marca_mm / 2 + 3) * escala
    for x, y in _marcas_en_px(formato, escala):
        mascara[
            max(0, int(y - medio)) : int(y + medio) + 1, max(0, int(x - medio)) : int(x + medio) + 1
        ] = 0
    return mascara


def _perimetro(puntos: Cuadrilatero) -> float:
    return sum(math.dist(puntos[i], puntos[(i + 1) % 4]) for i in range(4))


def _escalar(punto: Punto, factor: float) -> Punto:
    return (punto[0] * factor, punto[1] * factor)


def _tamano_de_comparacion(formato: FormatoDeHoja) -> tuple[int, int]:
    ancho, alto = formato.tamano_en_px()
    return (round(ancho / ESCALA_DE_LA_COMPARACION), round(alto / ESCALA_DE_LA_COMPARACION))


def _marcas_en_px(formato: FormatoDeHoja, escala: float) -> npt.NDArray[np.float32]:
    return np.array(
        [formato.a_px(centro) for centro in formato.centros_de_las_marcas_mm], np.float32
    ) * np.float32(escala)


@functools.lru_cache(maxsize=4)
def _anillo(formato: FormatoDeHoja) -> npt.NDArray[np.float32]:
    """El patrón con que se busca el contorno de una burbuja: el contorno impreso (radio ±
    0,15 mm) oscuro, y una franja de papel claro por fuera y por dentro de él."""
    radio = formato.mm_a_px(formato.radio_de_la_burbuja_mm)
    medio = math.ceil(radio + formato.mm_a_px(0.6)) + 2
    filas, columnas = np.mgrid[-medio : medio + 1, -medio : medio + 1]
    separacion = np.abs(np.hypot(columnas, filas) - radio)
    patron = np.zeros(separacion.shape, np.float32)
    patron[separacion <= formato.mm_a_px(0.15)] = 1.0
    patron[(separacion > formato.mm_a_px(0.3)) & (separacion <= formato.mm_a_px(0.6))] = -0.5
    patron -= patron.mean()
    return patron
