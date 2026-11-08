"""La hoja imprimible, dibujada a partir de la misma definición con que se lee.

Si la hoja se dibujara a mano en un editor, cualquier ajuste del formato obligaría a mantener dos
copias de las mismas medidas. Aquí la plantilla sale de `FormatoDeHoja`, y la imagen que se
dibuja es también la base del generador de hojas sintéticas de las pruebas.

**Dentro de la burbuja no se imprime nada.** La letra de cada opción va encima de su columna y el
dígito de cada fila del código, a su izquierda. Una burbuja vacía es solo un contorno fino, y la
lectura mide el interior: así una burbuja sin marcar no se confunde con una marca tenue.

**El texto usa la API de fuentes de OpenCV 5** (`FontFace`), que escribe UTF-8 con una fuente que
trae la biblioteca. Las fuentes Hershey de las versiones anteriores no tienen tildes.

**PDF sin dependencias nuevas.** OpenCV escribe PNG pero no PDF. En vez de sumar Pillow solo para
eso, `plantilla_pdf` envuelve la imagen en un PDF de una página escrito con `zlib` de la
biblioteca estándar; es un formato pequeño y fijo para un solo objeto de imagen.
"""

import zlib

import cv2
import numpy as np

from infraestructura.modelo import OPCIONES_DE_RESPUESTA
from omr.formato import FORMATO_V1, PREFIJO_DEL_CODIGO, FormatoDeHoja, Punto
from omr.vision import Imagen

__all__ = ["dibujar_plantilla", "plantilla_png", "plantilla_pdf"]

NEGRO = 0
BLANCO = 255
# 0,25 mm, unos 3 píxeles a 300 DPI. Más grueso, el contorno de una burbuja vacía empieza a pesar
# en lo que mide la lectura.
GROSOR_DEL_CONTORNO_MM = 0.25
GROSOR_DE_LAS_LINEAS_MM = 0.2
LADO_DE_LA_CASILLA_MM = 6.0
# Los centros en milímetros caen entre píxeles. OpenCV acepta coordenadas con bits de fracción
# (`shift`), y con cuatro el dibujo queda a 1/16 de píxel de donde la lectura va a medir.
_BITS_DE_FRACCION = 4
_FUENTE = "sans"
_NORMAL = 400
_NEGRITA = 700


def dibujar_plantilla(formato: FormatoDeHoja = FORMATO_V1) -> Imagen:
    """La hoja en blanco a la resolución del formato: marcas, burbujas con su letra o dígito,
    números de pregunta, la `T` del código y los textos para el nombre y el examen."""
    ancho, alto = formato.tamano_en_px()
    hoja: Imagen = np.full((alto, ancho), BLANCO, dtype=np.uint8)
    _dibujar_marcas(hoja, formato)
    _dibujar_encabezado(hoja, formato)
    _dibujar_codigo(hoja, formato)
    _dibujar_respuestas(hoja, formato)
    # La versión, entre las dos marcas de abajo: quien tenga una hoja en la mano sabe con qué
    # formato se lee.
    _escribir(
        hoja, formato, formato.version, (formato.ancho_mm / 2, formato.centros_de_las_marcas_mm[3][1]),
        2.8, alinear="centro", centrar_en_y=True,
    )
    return hoja


def plantilla_png(formato: FormatoDeHoja = FORMATO_V1) -> bytes:
    """La plantilla codificada como PNG."""
    codificada, png = cv2.imencode(".png", dibujar_plantilla(formato))
    if not codificada:
        raise RuntimeError("OpenCV no pudo codificar la plantilla como PNG")
    return png.tobytes()


def plantilla_pdf(formato: FormatoDeHoja = FORMATO_V1) -> bytes:
    """La plantilla como PDF de una página del tamaño del formato (carta en la v1), para
    imprimirla al 100 % sin que la impresora la reescale ni la recorte."""
    hoja = dibujar_plantilla(formato)
    alto_px, ancho_px = hoja.shape
    ancho_pt = formato.ancho_mm * 72 / 25.4
    alto_pt = formato.alto_mm * 72 / 25.4
    objetos = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {ancho_pt:.2f} {alto_pt:.2f}] "
            "/Resources << /XObject << /Hoja 4 0 R >> >> /Contents 5 0 R >>"
        ).encode("ascii"),
        _flujo(
            f"/Type /XObject /Subtype /Image /Width {ancho_px} /Height {alto_px} "
            "/ColorSpace /DeviceGray /BitsPerComponent 8 /Filter /FlateDecode",
            zlib.compress(hoja.tobytes(), 9),
        ),
        # La imagen ocupa la página entera: la escala del PDF lleva sus píxeles a los milímetros
        # del formato.
        _flujo("", f"q {ancho_pt:.2f} 0 0 {alto_pt:.2f} 0 0 cm /Hoja Do Q".encode("ascii")),
    ]
    # La segunda línea, con bytes altos, avisa que el archivo es binario.
    pdf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    posiciones = []
    for numero, cuerpo in enumerate(objetos, start=1):
        posiciones.append(len(pdf))
        pdf += b"%d 0 obj\n" % numero + cuerpo + b"\nendobj\n"
    inicio_de_la_tabla = len(pdf)
    pdf += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objetos) + 1)
    for posicion in posiciones:
        pdf += b"%010d 00000 n \n" % posicion
    pdf += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
        len(objetos) + 1,
        inicio_de_la_tabla,
    )
    return bytes(pdf)


def _flujo(diccionario: str, datos: bytes) -> bytes:
    cabecera = f"<< {diccionario} /Length {len(datos)} >>\nstream\n".encode("ascii")
    return cabecera + datos + b"\nendstream"


def _dibujar_marcas(hoja: Imagen, formato: FormatoDeHoja) -> None:
    medio = formato.lado_de_la_marca_mm / 2
    for x, y in formato.centros_de_las_marcas_mm:
        cv2.rectangle(
            hoja,
            _punto(formato, (x - medio, y - medio)),
            _punto(formato, (x + medio, y + medio)),
            NEGRO,
            cv2.FILLED,
            cv2.LINE_8,
            _BITS_DE_FRACCION,
        )


def _dibujar_encabezado(hoja: Imagen, formato: FormatoDeHoja) -> None:
    """El título, los campos que llena el estudiante a mano y las instrucciones, a la izquierda
    del código. Nada de esto se lee: sirve a quien llena la hoja y a quien la revisa en papel."""
    marca_x, marca_y = formato.centros_de_las_marcas_mm[0]
    x = marca_x + formato.lado_de_la_marca_mm
    # Los textos terminan dos columnas antes del código, que lleva su leyenda de dígitos a la
    # izquierda de la primera columna.
    hasta = formato.codigo.origen_mm[0] - 2 * formato.codigo.paso_columnas_mm
    y = marca_y + 13
    _escribir(hoja, formato, "QuantIA", (x, y), 8.0, peso=_NEGRITA)
    _escribir(hoja, formato, "Hoja de respuestas", (x, y + 8), 4.5)
    for i, campo in enumerate(("Nombre", "Examen", "Fecha")):
        renglon = y + 21 + 9 * i
        _escribir(hoja, formato, f"{campo}:", (x, renglon), 3.6)
        _linea(hoja, formato, (x + 17, renglon + 0.6), (hasta, renglon + 0.6))
    instrucciones = (
        "Rellena el círculo por completo,",
        "con lápiz o esfero oscuro.",
        "Una sola opción por pregunta.",
        "Para cambiarla, borra bien.",
        "No marques fuera de los círculos.",
    )
    for i, renglon_de_texto in enumerate(instrucciones):
        _escribir(hoja, formato, renglon_de_texto, (x, y + 51 + 5 * i), 3.4)


def _dibujar_codigo(hoja: Imagen, formato: FormatoDeHoja) -> None:
    """Las casillas para escribir el código a mano, la `T` impresa (`PREFIJO_DEL_CODIGO`) y una
    columna de burbujas del 0 al 9 por cada dígito."""
    codigo = formato.codigo
    x_inicial, y_inicial = codigo.origen_mm
    # La `T` y la leyenda de los dígitos van en la columna anterior a la primera.
    x_leyenda = x_inicial - codigo.paso_columnas_mm
    y_casillas = y_inicial - codigo.paso_filas_mm - 2
    x_final, _ = formato.centro_del_digito_mm(codigo.columnas, 0)
    _escribir(
        hoja, formato, "Código del estudiante", ((x_leyenda + x_final) / 2, y_casillas - 7),
        3.6, alinear="centro", peso=_NEGRITA,
    )
    _casilla(hoja, formato, (x_leyenda, y_casillas))
    _escribir(
        hoja, formato, PREFIJO_DEL_CODIGO, (x_leyenda, y_casillas), 4.2,
        alinear="centro", centrar_en_y=True, peso=_NEGRITA,
    )
    for posicion in range(1, codigo.columnas + 1):
        x, _ = formato.centro_del_digito_mm(posicion, 0)
        _casilla(hoja, formato, (x, y_casillas))
    for digito in range(codigo.filas):
        _, y = formato.centro_del_digito_mm(1, digito)
        _escribir(
            hoja, formato, str(digito), (x_leyenda, y), 3.4, alinear="centro", centrar_en_y=True
        )
        for posicion in range(1, codigo.columnas + 1):
            _burbuja(hoja, formato, formato.centro_del_digito_mm(posicion, digito))


def _dibujar_respuestas(hoja: Imagen, formato: FormatoDeHoja) -> None:
    pregunta = 1
    for bloque in formato.respuestas:
        if bloque.columnas > len(OPCIONES_DE_RESPUESTA):
            raise ValueError(
                f"El formato {formato.version} imprime {bloque.columnas} opciones y solo hay "
                f"{len(OPCIONES_DE_RESPUESTA)}"
            )
        x_inicial, y_inicial = bloque.origen_mm
        for columna in range(bloque.columnas):
            _escribir(
                hoja, formato, OPCIONES_DE_RESPUESTA[columna],
                (x_inicial + columna * bloque.paso_columnas_mm, y_inicial - bloque.paso_filas_mm),
                3.6, alinear="centro", centrar_en_y=True, peso=_NEGRITA,
            )
        for _ in range(bloque.filas):
            _, y = formato.centro_de_la_respuesta_mm(pregunta, 0)
            _escribir(
                hoja, formato, str(pregunta), (x_inicial - 5.5, y), 3.6,
                alinear="derecha", centrar_en_y=True,
            )
            for columna in range(bloque.columnas):
                _burbuja(hoja, formato, formato.centro_de_la_respuesta_mm(pregunta, columna))
            pregunta += 1


def _burbuja(hoja: Imagen, formato: FormatoDeHoja, centro_mm: Punto) -> None:
    cv2.circle(
        hoja,
        _punto(formato, centro_mm),
        _fraccion(formato.mm_a_px(formato.radio_de_la_burbuja_mm)),
        NEGRO,
        _grosor(formato, GROSOR_DEL_CONTORNO_MM),
        cv2.LINE_AA,
        _BITS_DE_FRACCION,
    )


def _casilla(hoja: Imagen, formato: FormatoDeHoja, centro_mm: Punto) -> None:
    x, y = centro_mm
    medio = LADO_DE_LA_CASILLA_MM / 2
    cv2.rectangle(
        hoja,
        _punto(formato, (x - medio, y - medio)),
        _punto(formato, (x + medio, y + medio)),
        NEGRO,
        _grosor(formato, GROSOR_DE_LAS_LINEAS_MM),
        cv2.LINE_AA,
        _BITS_DE_FRACCION,
    )


def _linea(hoja: Imagen, formato: FormatoDeHoja, desde_mm: Punto, hasta_mm: Punto) -> None:
    cv2.line(
        hoja,
        _punto(formato, desde_mm),
        _punto(formato, hasta_mm),
        NEGRO,
        _grosor(formato, GROSOR_DE_LAS_LINEAS_MM),
        cv2.LINE_AA,
        _BITS_DE_FRACCION,
    )


def _escribir(
    hoja: Imagen,
    formato: FormatoDeHoja,
    texto: str,
    punto_mm: Punto,
    tamano_mm: float,
    alinear: str = "izquierda",
    centrar_en_y: bool = False,
    peso: int = _NORMAL,
) -> None:
    """Escribe `texto` con la línea base en `punto_mm`, o con su caja centrada en esa altura si
    `centrar_en_y`. `alinear` dice qué borde del texto (o su centro) cae en la `x` del punto.

    La alineación se calcula aquí con `getTextSize`: los indicadores de alineación de `putText`
    no movieron el texto en la prueba con OpenCV 5.0."""
    fuente = cv2.FontFace(_FUENTE)
    tamano = round(formato.mm_a_px(tamano_mm))
    x, y = formato.a_px(punto_mm)
    alto_de_la_hoja, ancho_de_la_hoja = hoja.shape
    izquierda, arriba, ancho, alto = cv2.getTextSize(
        (ancho_de_la_hoja, alto_de_la_hoja), texto, (0, 0), fuente, tamano, peso
    )
    if alinear == "centro":
        x -= izquierda + ancho / 2
    elif alinear == "derecha":
        x -= izquierda + ancho
    if centrar_en_y:
        y -= arriba + alto / 2
    cv2.putText(hoja, texto, (round(x), round(y)), NEGRO, fuente, tamano, peso)


def _punto(formato: FormatoDeHoja, punto_mm: Punto) -> tuple[int, int]:
    x, y = formato.a_px(punto_mm)
    return (_fraccion(x), _fraccion(y))


def _fraccion(medida_px: float) -> int:
    return round(medida_px * 2**_BITS_DE_FRACCION)


def _grosor(formato: FormatoDeHoja, medida_mm: float) -> int:
    return max(1, round(formato.mm_a_px(medida_mm)))
