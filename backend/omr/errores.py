"""Por qué una hoja no se pudo leer.

Todos son **permanentes**: leer otra vez la misma imagen da el mismo resultado. Por eso el worker
no los reintenta, igual que un mensaje fuera del contrato (ADR-0020), y la hoja queda `ILEGIBLE`
con el `motivo` para que el docente la vuelva a escanear. Un fallo para leer el archivo del
almacén es otra cosa, transitoria, y lo sigue atendiendo el worker como hasta ahora.

`motivo` es estable y en minúsculas: lo guardan el registro de resultados y el log, y lo va a
mostrar la pantalla de revisión. El mensaje de la excepción es para quien depura.
"""

__all__ = [
    "LecturaImposible",
    "FormatoNoSoportado",
    "ImagenIlegible",
    "MarcasDeRegistroNoEncontradas",
    "HojaNoReconocida",
]


class LecturaImposible(Exception):
    """La raíz: cualquier razón por la que una hoja no produce una lectura."""

    motivo = "lectura_imposible"


class FormatoNoSoportado(LecturaImposible):
    """El archivo no es una imagen que la lectura sepa decodificar. Incluye el PDF, que `ingesta`
    acepta pero que esta versión de la lectura deja fuera."""

    motivo = "formato_no_soportado"


class ImagenIlegible(LecturaImposible):
    """La imagen se decodificó pero no sirve para leer marcas: borrosa, o demasiado oscura o
    clara."""

    motivo = "imagen_ilegible"


class MarcasDeRegistroNoEncontradas(LecturaImposible):
    """No aparecen las cuatro marcas de las esquinas: la hoja está recortada, no es la hoja de
    QuantIA o la foto no la contiene."""

    motivo = "marcas_de_registro_no_encontradas"


class HojaNoReconocida(LecturaImposible):
    """Hay cuatro cuadrados en las esquinas, pero lo que queda entre ellos no se parece a la
    plantilla del formato en ninguna orientación: es otra hoja, u otra versión del formato."""

    motivo = "hoja_no_reconocida"
