"""Resolver lo que quedó en revisión en una hoja y recalcular su nota (RF-08).

La ruta de la API solo traduce: aquí se busca la última lectura de la hoja, se convierte lo que el
profesor vio en resoluciones, se comprueba que la nota se pueda recalcular con ellas y, solo
entonces, se escriben. Si algo no cuadra, no se escribe nada.

Los registros llegan por sus puertos (`infraestructura.resultados` e `infraestructura.revisiones`):
este archivo no sabe si son archivos, tablas u otra cosa.
"""

from collections.abc import Mapping
from datetime import datetime

from calificacion.nota import nota_vigente, resolucion_con_opcion
from infraestructura.modelo import POR_REVISAR, CalificacionDeHoja
from infraestructura.resultados import LectorDeResultados, calificacion_del_hecho
from infraestructura.revisiones import RevisionesDelProfesor

__all__ = ["HojaSinNotaQueRevisar", "resolver_preguntas"]

# El nombre que escribe el profesor. Sin verificar hasta A-05; el tope evita que una línea del
# registro cargue un texto arbitrariamente largo.
LARGO_MAXIMO_DEL_NOMBRE = 80


class HojaSinNotaQueRevisar(LookupError):
    """La hoja no está en el examen, no se pudo leer o se leyó sin clave: no hay una nota que
    recalcular."""


def resolver_preguntas(
    examen_id: str,
    hoja_id: str,
    opciones: Mapping[int, str | None],
    por: str,
    en: datetime,
    resultados: LectorDeResultados,
    revisiones: RevisionesDelProfesor,
) -> CalificacionDeHoja:
    """Registra lo que el profesor vio marcado en cada pregunta (`None` si ninguna opción vale) y
    devuelve la nota vigente de la hoja.

    Lanza `HojaSinNotaQueRevisar` si la hoja no tiene una nota, y `ValueError` si una pregunta no
    estaba en revisión, si una opción no existe o si falta el nombre de quien resuelve."""
    nombre = por.strip()
    if not nombre or len(nombre) > LARGO_MAXIMO_DEL_NOMBRE:
        raise ValueError(
            f"Quien resuelve tiene que escribir su nombre, de 1 a {LARGO_MAXIMO_DEL_NOMBRE} letras"
        )
    if not opciones:
        raise ValueError("No hay ninguna pregunta que resolver")

    automatica = _calificacion_de_la_hoja(examen_id, hoja_id, resultados)
    por_numero = {resultado.numero: resultado for resultado in automatica.preguntas}
    nuevas = []
    for numero, opcion in sorted(opciones.items()):
        resultado = por_numero.get(numero)
        if resultado is None or resultado.veredicto != POR_REVISAR:
            raise ValueError(f"La pregunta {numero} no está en revisión en esta hoja")
        nuevas.append(resolucion_con_opcion(resultado, opcion, nombre, en))

    anteriores = revisiones.resoluciones_del_examen(examen_id).get(hoja_id, ())
    vigente = nota_vigente(automatica, (*anteriores, *nuevas))
    revisiones.registrar_resoluciones(hoja_id, examen_id, nuevas)
    return vigente


def _calificacion_de_la_hoja(
    examen_id: str, hoja_id: str, resultados: LectorDeResultados
) -> CalificacionDeHoja:
    ultimo = None
    for hecho in resultados.hechos_del_examen(examen_id):
        if hecho.get("hoja_id") == hoja_id:
            ultimo = hecho
    calificacion = None if ultimo is None else calificacion_del_hecho(ultimo)
    if calificacion is None:
        raise HojaSinNotaQueRevisar(
            f"La hoja {hoja_id} del examen {examen_id} no tiene una nota que revisar"
        )
    return calificacion
