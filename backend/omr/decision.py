"""Las decisiones de la lectura: de proporciones de relleno a marcas, preguntas y código.

No importa OpenCV ni numpy: trabaja con los números que mide `vision`, y por eso se prueba con
números escritos a mano. Aquí vive la tensión T-1 (arc42): un umbral permisivo produce errores
silenciosos y uno estricto manda tanto a revisión que el sistema deja de ahorrar tiempo.

**El umbral llega como parámetro** y lo decide quien llama: el worker lo lee de
`OMR_UMBRAL_DE_CONFIANZA`, con 70 por omisión (EC-02). No es una constante de este archivo porque
R-04 lo declara supuesto y se va a calibrar. Tiene que pasar de 50: con 50 o menos, una misma
burbuja contaría como intencional y como no intencional a la vez.

**La confianza de una burbuja** es la que muestra la pantalla de revisión: la probabilidad, en
porcentaje, de que la marca sea una respuesta intencional. Sale del relleno con una curva por
tramos que pasa por los cortes de vacía y de completa.

**La regla de una pregunta**, con `c1` y `c2` las confianzas de las dos burbujas más llenas y `u`
el umbral:

- `c1 >= u` y `c2 >= u`: `DOBLE_MARCA`, porque las dos son intencionales.
- `c1 >= u` y `100 - c2 >= u`: `UNA_MARCA`. La primera es intencional y la segunda, con la misma
  exigencia, no lo es. Una marca completa al lado de una burbuja bien borrada se asigna sola; al
  lado de un borrón que se ve, va a revisión.
- `100 - c1 >= u`: `SIN_MARCA`, porque ni la más llena parece intencional.
- Cualquier otro caso: `DUDOSA`.

La confianza de la pregunta es la de la decisión que se tomó. En una `DUDOSA` es la de la mejor
decisión posible, que no llegó al umbral; si solo hay una burbuja con algo, coincide con la de esa
burbuja, que es como la muestra la pantalla («la de su lectura más fuerte»). El sistema nunca
elige entre candidatas (RF-03): `UNA_MARCA` exige descartar las demás con la misma confianza con
que se acepta la elegida.
"""

from infraestructura.modelo import (
    BORRON,
    CODIGO_COMPLETO,
    CODIGO_INCOMPLETO,
    COMPLETA,
    DOBLE_MARCA,
    DUDOSA,
    SIN_MARCA,
    TENUE,
    UNA_MARCA,
    VACIA,
    LecturaDeBurbuja,
    LecturaDelCodigo,
    LecturaDePregunta,
)
from omr.formato import PREFIJO_DEL_CODIGO

__all__ = [
    "clasificar_burbuja",
    "decidir_pregunta",
    "decidir_codigo",
    "comprobar_umbral_de_confianza",
]

# Hasta qué relleno una burbuja se ve vacía y desde cuál se ve completa. Con el relleno que mide
# `vision`, en las tres fotos del prototipo (R-05) las burbujas en blanco dieron 0,00 y las marcas
# completas de lápiz o esfero sin brillo, de 0,69 a 1.
RELLENO_MAXIMO_DE_UNA_VACIA = 0.08
RELLENO_MINIMO_DE_UNA_COMPLETA = 0.65
# Entre los dos, un borrón deja menos tinta que una marca tenue. En las fotos, lo que quedó al
# borrar dio de 0,01 a 0,15, y un chulo, una X o media burbuja, de 0,31 a 0,57. Para la nota da
# igual: con el umbral por omisión, los dos tipos van a revisión.
RELLENO_MINIMO_DE_UNA_TENUE = 0.25
# La confianza en los cortes de vacía y de completa. Con el umbral por omisión (70), una burbuja
# completa se acepta sola y una vacía se descarta sola.
CONFIANZA_EN_EL_CORTE_DE_VACIA = 30
CONFIANZA_EN_EL_CORTE_DE_COMPLETA = 70
# **Cuándo una burbuja que se ve vacía no se da por vacía.** Una `SIN_MARCA` cuenta como
# incorrecta sin pasar por el profesor, así que leer vacía una burbuja marcada es un error
# silencioso. En las fotos aparecieron dos maneras de que pase:
# - El grafito brilla. Una marca con el reflejo de la luz se vio tan clara como el papel (relleno
#   0,06), pero con el interior desparejo: granos que reflejan y granos oscuros. La dispersión de
#   su oscuridad fue de 0,10 a 0,16 en las marcas que se veían casi vacías; en las burbujas en
#   blanco no pasó de 0,061 (una cruzada por el borde de la sombra) y en las borradas, de 0,049.
#   En hojas sintéticas con ese brillo no bajó de 0,077 desde la resolución mínima de `vision`.
# - Algo tapa la burbuja: si el contorno impreso no se ve, el papel de referencia tampoco es papel.
#   Una burbuja en blanco siempre muestra su contorno, y una rellena se ve rellena.
# En los dos casos la burbuja queda en la mitad: confianza 50, que con cualquier umbral válido
# manda la pregunta a revisión.
DISPERSION_MINIMA_PARA_DUDAR = 0.07
CONTORNO_MINIMO_DE_UNA_VACIA = 0.3
CONFIANZA_DE_UNA_BURBUJA_EN_DUDA = 50


def clasificar_burbuja(
    opcion: str, relleno: float, dispersion: float = 0.0, contorno: float = 1.0
) -> LecturaDeBurbuja:
    """Asigna el tipo (`VACIA`, `TENUE`, `BORRON` o `COMPLETA`) y su confianza a una burbuja, a
    partir de su relleno. `dispersion` (cuán desparejo es el interior) y `contorno` (cuánto se ve
    el contorno impreso, de -1 a 1) solo cuentan para no dar por vacía una burbuja que no se puede
    ver bien. Lanza `ValueError` si el relleno no está entre 0 y 1 o la dispersión es negativa."""
    if not 0.0 <= relleno <= 1.0:
        raise ValueError(f"El relleno de una burbuja va de 0 a 1, y llegó {relleno}")
    if not dispersion >= 0.0:
        raise ValueError(f"La dispersión de una burbuja no es negativa, y llegó {dispersion}")
    confianza = _confianza(relleno)
    if confianza < CONFIANZA_DE_UNA_BURBUJA_EN_DUDA and (
        dispersion >= DISPERSION_MINIMA_PARA_DUDAR or contorno < CONTORNO_MINIMO_DE_UNA_VACIA
    ):
        confianza = CONFIANZA_DE_UNA_BURBUJA_EN_DUDA
    # El tipo se deduce de la confianza ya redondeada, no del relleno, para que en los bordes no
    # haya una burbuja `COMPLETA` que el umbral por omisión no acepte, ni una `VACIA` que no
    # descarte.
    if confianza <= CONFIANZA_EN_EL_CORTE_DE_VACIA:
        tipo = VACIA
    elif confianza >= CONFIANZA_EN_EL_CORTE_DE_COMPLETA:
        tipo = COMPLETA
    elif relleno >= RELLENO_MINIMO_DE_UNA_TENUE:
        tipo = TENUE
    else:
        tipo = BORRON
    return LecturaDeBurbuja(opcion, relleno, tipo, confianza)


def decidir_pregunta(
    numero: int, burbujas: tuple[LecturaDeBurbuja, ...], umbral_de_confianza: int
) -> LecturaDePregunta:
    """Decide una fila: `UNA_MARCA` con su opción, `SIN_MARCA`, `DOBLE_MARCA` o `DUDOSA`."""
    comprobar_umbral_de_confianza(umbral_de_confianza)
    estado, opcion, confianza = _decidir(burbujas, umbral_de_confianza)
    return LecturaDePregunta(numero, estado, opcion, confianza, burbujas)


def decidir_codigo(
    columnas: tuple[tuple[LecturaDeBurbuja, ...], ...], umbral_de_confianza: int
) -> LecturaDelCodigo:
    """Decide el código del estudiante, columna por columna, con la misma regla que una pregunta.

    Si alguna columna no queda con una sola marca confiable, el código es `CODIGO_INCOMPLETO` y la
    columna va en `columnas_por_revisar`. El valor es la `T` seguida de los ocho dígitos; en un
    código incompleto lleva `?` en las columnas por revisar, para que el profesor vea lo que sí se
    leyó."""
    comprobar_umbral_de_confianza(umbral_de_confianza)
    if not columnas:
        raise ValueError("Un código sin columnas no se puede decidir")
    digitos = []
    por_revisar = []
    for posicion, burbujas in enumerate(columnas, start=1):
        estado, digito, _ = _decidir(burbujas, umbral_de_confianza)
        if estado == UNA_MARCA and digito is not None:
            digitos.append(digito)
        else:
            digitos.append("?")
            por_revisar.append(posicion)
    return LecturaDelCodigo(
        estado=CODIGO_INCOMPLETO if por_revisar else CODIGO_COMPLETO,
        valor=PREFIJO_DEL_CODIGO + "".join(digitos),
        columnas_por_revisar=tuple(por_revisar),
    )


def _confianza(relleno: float) -> int:
    tramos = (
        (0.0, 0),
        (RELLENO_MAXIMO_DE_UNA_VACIA, CONFIANZA_EN_EL_CORTE_DE_VACIA),
        (RELLENO_MINIMO_DE_UNA_COMPLETA, CONFIANZA_EN_EL_CORTE_DE_COMPLETA),
        (1.0, 100),
    )
    for (x0, y0), (x1, y1) in zip(tramos, tramos[1:]):
        if relleno <= x1:
            return round(y0 + (relleno - x0) * (y1 - y0) / (x1 - x0))
    return 100


def _decidir(
    burbujas: tuple[LecturaDeBurbuja, ...], umbral: int
) -> tuple[str, str | None, int]:
    """El estado, la opción (solo con `UNA_MARCA`) y la confianza de una fila de burbujas."""
    if not burbujas:
        raise ValueError("Una fila sin burbujas no se puede decidir")
    orden = sorted(burbujas, key=lambda burbuja: burbuja.confianza, reverse=True)
    c1 = orden[0].confianza
    c2 = orden[1].confianza if len(orden) > 1 else 0
    if c1 >= umbral and c2 >= umbral:
        return DOBLE_MARCA, None, min(c1, c2)
    una_marca = min(c1, 100 - c2)
    sin_marca = 100 - c1
    if una_marca >= umbral:
        return UNA_MARCA, orden[0].opcion, una_marca
    if sin_marca >= umbral:
        return SIN_MARCA, None, sin_marca
    return DUDOSA, None, max(una_marca, sin_marca)


def comprobar_umbral_de_confianza(umbral: int) -> int:
    """Devuelve el umbral si la regla lo admite, o lanza `ValueError`. El worker la llama al
    arrancar, para que un valor mal configurado lo detenga a él y no falle hoja por hoja."""
    if not 50 < umbral <= 100:
        raise ValueError(f"El umbral de confianza va de 51 a 100, y llegó {umbral}")
    return umbral
