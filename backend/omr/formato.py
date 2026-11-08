"""El formato de la hoja de respuestas, como datos (RNF-02).

RNF-02 pide una hoja de formato fijo, con las casillas en posiciones conocidas y marcas de
registro para corregir la inclinación. Este archivo es esa definición, y de ella salen las dos
cosas que no pueden divergir: la hoja que se imprime (`plantilla`) y las posiciones donde se lee
(`lectura`). Cambiar una medida es cambiar la versión: una hoja impresa con la v1 se lee con la v1.

Todo está en milímetros sobre una hoja carta vertical (215,9 × 279,4 mm), el papel en que se
imprime en Colombia, con el origen en la esquina superior izquierda.
La imagen rectificada se lleva a `dpi` puntos por pulgada, así que una medida en milímetros es
`mm * dpi / 25,4` píxeles. Las medidas de la v1 son una primera propuesta: se confirman con la
primera hoja impresa y fotografiada (riesgo R-05) antes de dar el formato por cerrado.
"""

from dataclasses import dataclass

__all__ = ["Cuadricula", "FormatoDeHoja", "FORMATO_V1", "PREFIJO_DEL_CODIGO"]

Punto = tuple[float, float]

# Todos los códigos de estudiante de la UTB empiezan con esta letra: la hoja la imprime y la
# lectura la antepone a los ocho dígitos marcados.
PREFIJO_DEL_CODIGO = "T"


@dataclass(frozen=True)
class Cuadricula:
    """Burbujas en filas y columnas regulares.

    En un bloque de respuestas, cada fila es una pregunta y cada columna una opción. En el código
    del estudiante, cada columna es una posición del código y cada fila un dígito, del 0 al 9.
    `origen_mm` es el centro de la burbuja de la primera fila y la primera columna."""

    origen_mm: Punto
    paso_columnas_mm: float
    paso_filas_mm: float
    filas: int
    columnas: int


@dataclass(frozen=True)
class FormatoDeHoja:
    """Una versión del formato.

    `centros_de_las_marcas_mm` va en el orden en que se emparejan con lo detectado: superior
    izquierda, superior derecha, inferior derecha e inferior izquierda. Los bloques de
    `respuestas` se numeran seguidos: el segundo empieza donde termina el primero."""

    version: str
    ancho_mm: float
    alto_mm: float
    dpi: int
    lado_de_la_marca_mm: float
    centros_de_las_marcas_mm: tuple[Punto, Punto, Punto, Punto]
    radio_de_la_burbuja_mm: float
    codigo: Cuadricula
    respuestas: tuple[Cuadricula, ...]

    def numero_de_preguntas(self) -> int:
        """Cuántas preguntas imprime el formato: la suma de las filas de sus bloques."""
        return sum(bloque.filas for bloque in self.respuestas)

    def tamano_en_px(self) -> tuple[int, int]:
        """Ancho y alto de la imagen rectificada, en píxeles."""
        return (round(self.ancho_mm * self._px_por_mm()), round(self.alto_mm * self._px_por_mm()))

    def a_px(self, punto_mm: Punto) -> Punto:
        """Lleva un punto de milímetros a píxeles de la imagen rectificada."""
        x, y = punto_mm
        return (x * self._px_por_mm(), y * self._px_por_mm())

    def mm_a_px(self, medida_mm: float) -> float:
        """Lleva una longitud (un radio, un lado) de milímetros a píxeles."""
        return medida_mm * self._px_por_mm()

    def centro_de_la_respuesta_mm(self, pregunta: int, columna: int) -> Punto:
        """El centro de la burbuja de una opción (columna 0 es A) de una pregunta, que se numera
        desde 1 como en la hoja. Lanza `ValueError` si la hoja no imprime esa burbuja."""
        fila = pregunta - 1
        if fila >= 0:
            for bloque in self.respuestas:
                if fila < bloque.filas:
                    return _centro(bloque, fila, columna)
                fila -= bloque.filas
        raise ValueError(f"La hoja {self.version} no imprime la pregunta {pregunta}")

    def centro_del_digito_mm(self, posicion: int, digito: int) -> Punto:
        """El centro de la burbuja de un dígito (0 a 9) en una posición del código (1 a 8).
        Lanza `ValueError` si la hoja no imprime esa burbuja."""
        if not 1 <= posicion <= self.codigo.columnas:
            raise ValueError(f"El código de la hoja {self.version} no tiene la posición {posicion}")
        return _centro(self.codigo, digito, posicion - 1)

    def _px_por_mm(self) -> float:
        return self.dpi / 25.4


def _centro(cuadricula: Cuadricula, fila: int, columna: int) -> Punto:
    if not (0 <= fila < cuadricula.filas and 0 <= columna < cuadricula.columnas):
        raise ValueError(f"La cuadrícula no tiene burbuja en la fila {fila}, columna {columna}")
    x, y = cuadricula.origen_mm
    return (x + columna * cuadricula.paso_columnas_mm, y + fila * cuadricula.paso_filas_mm)


# Carta a 300 DPI: 2550 × 3300 píxeles. Una hoja A4 impresa en carta al 100 % pierde los
# últimos 18 mm, y con ellos las marcas de abajo. Las marcas son cuadrados de 10 mm a 10 mm de
# los bordes, fuera del margen que la mayoría de impresoras no alcanza. El código ocupa la esquina
# superior derecha (una `T` impresa y ocho columnas), y las 40 preguntas van en dos bloques de
# 20. Burbujas de 5 mm de diámetro: 8 o 10 mm entre columnas y 7 mm entre filas. Los dos
# bloques, con sus números de pregunta, quedan centrados en el ancho de la hoja.
FORMATO_V1 = FormatoDeHoja(
    version="quantia-hoja-v1",
    ancho_mm=215.9,
    alto_mm=279.4,
    dpi=300,
    lado_de_la_marca_mm=10.0,
    centros_de_las_marcas_mm=((15.0, 15.0), (200.9, 15.0), (200.9, 264.4), (15.0, 264.4)),
    radio_de_la_burbuja_mm=2.5,
    codigo=Cuadricula(
        origen_mm=(130.0, 43.0), paso_columnas_mm=8.0, paso_filas_mm=7.0, filas=10, columnas=8
    ),
    respuestas=(
        Cuadricula(
            origen_mm=(58.0, 122.0), paso_columnas_mm=10.0, paso_filas_mm=7.0, filas=20, columnas=4
        ),
        Cuadricula(
            origen_mm=(138.0, 122.0), paso_columnas_mm=10.0, paso_filas_mm=7.0, filas=20, columnas=4
        ),
    ),
)
