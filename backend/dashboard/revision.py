"""Lo que espera al profesor en un examen (RF-08): cada hoja con preguntas en revisión, y en cada
pregunta lo que se midió en sus burbujas y lo que el profesor ya resolvió.

Es una proyección, como `dashboard.resultados`: se calcula en cada consulta a partir del registro de
resultados (el último hecho de cada hoja) y del de revisiones. Una hoja sigue apareciendo después de
resuelta, para que el profesor pueda cambiar de opinión.

**Sin la clave y sin el código del estudiante.** La ruta que la publica es pública hasta A-05
(AM-02): el profesor dice qué marcó el estudiante y `calificacion` decide si es correcto, así que
aquí no viaja la respuesta correcta. Solo entran las hojas con nota: sin clave no hay nada que
recalcular.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from calificacion import recalcular, resoluciones_vigentes
from infraestructura.modelo import CODIGO_COMPLETO, POR_REVISAR
from infraestructura.resultados import LectorDeResultados, calificacion_del_hecho
from infraestructura.revisiones import LectorDeRevisiones

__all__ = [
    "BurbujaEnRevision",
    "PreguntaEnRevision",
    "HojaEnRevision",
    "RevisionDelExamen",
    "revision_del_examen",
    "referencia_del_recorte",
]


@dataclass(frozen=True)
class BurbujaEnRevision:
    """Lo que se midió en una burbuja: `tipo` es vacía, tenue, borrón o completa."""

    opcion: str
    tipo: str
    confianza: int


@dataclass(frozen=True)
class PreguntaEnRevision:
    """Una pregunta que la lectura no pudo decidir. `opcion_resuelta` es la que el profesor vio
    marcada, o None si dijo que ninguna vale; solo tiene sentido con `resuelta`."""

    numero: int
    burbujas: tuple[BurbujaEnRevision, ...]
    con_recorte: bool
    resuelta: bool
    opcion_resuelta: str | None
    resuelta_por: str | None
    resuelta_en: datetime | None


@dataclass(frozen=True)
class HojaEnRevision:
    """Una hoja con preguntas en revisión y su nota vigente, con lo resuelto hasta ahora."""

    hoja_id: str
    nota_en_decimas: int
    provisional: bool
    codigo_completo: bool
    preguntas: tuple[PreguntaEnRevision, ...]


@dataclass(frozen=True)
class RevisionDelExamen:
    """Las hojas del examen que pasaron por revisión, en el orden en que se leyeron."""

    examen_id: str
    hojas: tuple[HojaEnRevision, ...]


def revision_del_examen(
    examen_id: str, lector: LectorDeResultados, revisiones: LectorDeRevisiones | None = None
) -> RevisionDelExamen:
    resueltas = {} if revisiones is None else revisiones.resoluciones_del_examen(examen_id)
    hojas = []
    for hoja_id, hecho in _ultimos_hechos(examen_id, lector).items():
        calificacion = calificacion_del_hecho(hecho)
        if calificacion is None:
            continue
        en_revision = [r.numero for r in calificacion.preguntas if r.veredicto == POR_REVISAR]
        if not en_revision:
            continue
        vigentes = resoluciones_vigentes(calificacion, resueltas.get(hoja_id, ()))
        nota = recalcular(calificacion, vigentes) if vigentes else calificacion
        por_numero = {resolucion.numero: resolucion for resolucion in vigentes}
        lectura = hecho.get("lectura") or {}
        filas = {fila["numero"]: fila for fila in lectura.get("preguntas", ())}
        recortes = hecho.get("recortes") or {}
        preguntas = []
        for numero in en_revision:
            resolucion = por_numero.get(numero)
            preguntas.append(
                PreguntaEnRevision(
                    numero=numero,
                    burbujas=tuple(
                        BurbujaEnRevision(b["opcion"], b["tipo"], b["confianza"])
                        for b in filas.get(numero, {}).get("burbujas", ())
                    ),
                    con_recorte=str(numero) in recortes,
                    resuelta=resolucion is not None,
                    opcion_resuelta=None if resolucion is None else resolucion.opcion,
                    resuelta_por=None if resolucion is None else resolucion.por,
                    resuelta_en=None if resolucion is None else resolucion.en,
                )
            )
        hojas.append(
            HojaEnRevision(
                hoja_id=hoja_id,
                nota_en_decimas=nota.nota_en_decimas,
                provisional=nota.provisional,
                codigo_completo=(lectura.get("codigo") or {}).get("estado") == CODIGO_COMPLETO,
                preguntas=tuple(preguntas),
            )
        )
    return RevisionDelExamen(examen_id=examen_id, hojas=tuple(hojas))


def referencia_del_recorte(
    examen_id: str, hoja_id: str, numero: int, lector: LectorDeResultados
) -> str | None:
    """Dónde quedó en el almacén el recorte de una pregunta, según la última lectura de la hoja.
    La referencia sale del registro, nunca de quien pide el recorte."""
    hecho = _ultimos_hechos(examen_id, lector).get(hoja_id)
    if hecho is None:
        return None
    referencia = (hecho.get("recortes") or {}).get(str(numero))
    return referencia if isinstance(referencia, str) else None


def _ultimos_hechos(examen_id: str, lector: LectorDeResultados) -> dict[str, dict[str, Any]]:
    ultimos: dict[str, dict[str, Any]] = {}
    for hecho in lector.hechos_del_examen(examen_id):
        ultimos[hecho["hoja_id"]] = hecho
    return ultimos
