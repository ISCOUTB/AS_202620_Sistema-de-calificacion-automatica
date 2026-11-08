"""La lectura de una hoja de punta a punta: bytes de imagen dentro, `LecturaDeHoja` fuera.

Es pura: no toca disco, red, cola ni log. Quien llama (el worker) trae la imagen del almacén,
decide el umbral, registra el resultado y escribe en el log, sin el código del estudiante.
No hay modelo de lenguaje en este camino (RNF-01).
"""

import functools
import time
from typing import NamedTuple

from infraestructura.modelo import (
    DOBLE_MARCA,
    DUDOSA,
    OPCIONES_DE_RESPUESTA,
    LecturaDeBurbuja,
    LecturaDeHoja,
)
from omr import vision
from omr.decision import (
    clasificar_burbuja,
    comprobar_umbral_de_confianza,
    decidir_codigo,
    decidir_pregunta,
)
from omr.formato import FORMATO_V1, FormatoDeHoja, Punto
from omr.plantilla import dibujar_plantilla

__all__ = ["leer_hoja", "leer_hoja_con_recortes"]

_PREGUNTA = "pregunta"
_CODIGO = "codigo"


class _Posicion(NamedTuple):
    """Una burbuja del formato: a qué fila pertenece (una pregunta por su número, o una columna
    del código por su posición), qué opción es y dónde está."""

    fila: tuple[str, int]
    opcion: str
    centro_mm: Punto


def leer_hoja(
    contenido: bytes, umbral_de_confianza: int, formato: FormatoDeHoja = FORMATO_V1
) -> LecturaDeHoja:
    """Lee el código del estudiante y todas las filas de respuestas de la hoja. Es
    `leer_hoja_con_recortes` sin los recortes."""
    return _leer(contenido, umbral_de_confianza, formato, recortar=False)[0]


def leer_hoja_con_recortes(
    contenido: bytes, umbral_de_confianza: int, formato: FormatoDeHoja = FORMATO_V1
) -> tuple[LecturaDeHoja, dict[int, bytes]]:
    """Lee la hoja como `leer_hoja` y, además, recorta en PNG la fila de cada pregunta que quedó
    dudosa o con doble marca, por número: es lo que el profesor mira para resolverla (RF-08). Se
    recorta de la hoja ya rectificada, que está en memoria, así que no cuesta otra lectura."""
    return _leer(contenido, umbral_de_confianza, formato, recortar=True)


def _leer(
    contenido: bytes, umbral_de_confianza: int, formato: FormatoDeHoja, recortar: bool
) -> tuple[LecturaDeHoja, dict[int, bytes]]:
    """Lee el código del estudiante y todas las filas de respuestas de la hoja.

    Recorre `vision` (decodificar, comprobar la calidad, encontrar y orientar las marcas,
    rectificar, ajustar y medir cada burbuja) y `decision` (clasificar cada burbuja y decidir cada
    pregunta y el código), y mide cuánto tarda (EC-03).

    Lanza una subclase de `LecturaImposible` si la hoja no se puede leer, y `ValueError` si el
    umbral no está entre 51 y 100, que es un error de configuración y no de la hoja."""
    comprobar_umbral_de_confianza(umbral_de_confianza)
    inicio = time.perf_counter()
    gris = vision.decodificar(contenido)
    vision.comprobar_calidad(gris)
    marcas = vision.localizar_marcas_de_registro(gris)
    marcas = vision.orientar(gris, marcas, formato, _plantilla_para_orientar(formato))
    hoja = vision.rectificar(gris, marcas, formato)
    # La foto ocupa más memoria que la hoja rectificada, y el worker tiene poca.
    del gris

    posiciones = _posiciones(formato)
    ajustados = vision.ajustar_centros(
        hoja, [formato.a_px(posicion.centro_mm) for posicion in posiciones], formato
    )
    filas: dict[tuple[str, int], list[LecturaDeBurbuja]] = {}
    centros: dict[tuple[str, int], list[Punto]] = {}
    for posicion, ajustado in zip(posiciones, ajustados, strict=True):
        centros.setdefault(posicion.fila, []).append(ajustado.centro)
        medida = vision.medir_burbuja(hoja, ajustado.centro, formato)
        burbuja = clasificar_burbuja(
            posicion.opcion,
            round(medida.relleno, 3),
            round(medida.dispersion, 3),
            ajustado.contorno,
        )
        filas.setdefault(posicion.fila, []).append(burbuja)

    preguntas = tuple(
        decidir_pregunta(numero, tuple(burbujas), umbral_de_confianza)
        for (grupo, numero), burbujas in filas.items()
        if grupo == _PREGUNTA
    )
    codigo = decidir_codigo(
        tuple(tuple(burbujas) for (grupo, _), burbujas in filas.items() if grupo == _CODIGO),
        umbral_de_confianza,
    )
    lectura = LecturaDeHoja(
        version_del_formato=formato.version,
        codigo=codigo,
        preguntas=preguntas,
        umbral_de_confianza=umbral_de_confianza,
        duracion_ms=round((time.perf_counter() - inicio) * 1000, 1),
    )
    recortes: dict[int, bytes] = {}
    if recortar:
        for pregunta in preguntas:
            if pregunta.estado not in (DUDOSA, DOBLE_MARCA):
                continue
            png = vision.recortar_fila(hoja, centros[(_PREGUNTA, pregunta.numero)], formato)
            if png is not None:
                recortes[pregunta.numero] = png
    return lectura, recortes


@functools.lru_cache(maxsize=4)
def _posiciones(formato: FormatoDeHoja) -> tuple[_Posicion, ...]:
    """Todas las burbujas del formato: primero las preguntas en orden, cada una de la A en
    adelante; después el código, posición por posición, del 0 al 9."""
    posiciones = []
    numero = 1
    for bloque in formato.respuestas:
        for _ in range(bloque.filas):
            for columna in range(bloque.columnas):
                posiciones.append(
                    _Posicion(
                        (_PREGUNTA, numero),
                        OPCIONES_DE_RESPUESTA[columna],
                        formato.centro_de_la_respuesta_mm(numero, columna),
                    )
                )
            numero += 1
    for posicion in range(1, formato.codigo.columnas + 1):
        for digito in range(formato.codigo.filas):
            posiciones.append(
                _Posicion(
                    (_CODIGO, posicion), str(digito), formato.centro_del_digito_mm(posicion, digito)
                )
            )
    return tuple(posiciones)


@functools.lru_cache(maxsize=4)
def _plantilla_para_orientar(formato: FormatoDeHoja) -> vision.Comparable:
    """La plantilla tal como la compara `vision.orientar`. Se dibuja una vez por proceso."""
    return vision.preparar_para_comparar(dibujar_plantilla(formato), formato)
