"""El panel de un examen (RF-05): cómo le fue al grupo, calculado con lo que el sistema leyó y
calificó. Reemplaza los datos de ejemplo con los que nació la pantalla del panel (ADR-0028).

**De dónde sale cada cifra.**

- *Hojas recibidas*: las que registró la bitácora de recepción, se hayan leído o no.
- *Promedio, aprobación, distribución de notas*: las hojas con nota, también las provisionales.
  Una nota provisional es la tentativa de la pantalla de revisión: lo que espera al profesor suma
  cero hasta que lo resuelva, así que resolver solo puede subirla. Se cuentan con lo que el
  profesor ya resolvió aplicado encima, como en los resultados.
- *Revisión pendiente*: las preguntas que esperan al profesor, en las hojas con nota y en las
  leídas sin clave.
- *Cómo se marcaron las respuestas*: cada pregunta de la clave en cada hoja con nota, en una sola
  categoría según lo que vio la lectura. Una marca clara se divide en correcta o incorrecta; las
  dudosas (tenue, borrón), las dobles y las en blanco van aparte aunque el profesor ya las haya
  resuelto, porque lo que se describe es cómo se marcó la hoja.
- *Aciertos por pregunta*: con la respuesta vigente, la que resolvió el profesor si la resolvió.
  Una pregunta anulada no cuenta ni como acierto ni en el total.

**No lleva el código del estudiante ni el nombre de los archivos**: el panel habla del grupo.
"""

import math
from dataclasses import dataclass
from typing import Any

from calificacion import nota_vigente
from infraestructura.bitacora import LectorDeRecepciones
from infraestructura.modelo import (
    ANULADA,
    CORRECTA,
    DOBLE_MARCA,
    DUDOSA,
    ILEGIBLE,
    OPCIONES_DE_RESPUESTA,
    POR_REVISAR,
    SIN_MARCA,
    UNA_MARCA,
)
from infraestructura.resultados import LectorDeResultados, calificacion_del_hecho
from infraestructura.revisiones import LectorDeRevisiones

__all__ = [
    "NOTA_APROBATORIA_EN_DECIMAS",
    "ResumenDelPanel",
    "MarcasDelExamen",
    "PreguntaDelPanel",
    "PanelDelExamen",
    "panel_del_examen",
]

# 3,0 en la escala de 0 a 5 de la UTB.
NOTA_APROBATORIA_EN_DECIMAS = 30


@dataclass(frozen=True)
class ResumenDelPanel:
    hojas_recibidas: int
    hojas_leidas: int
    hojas_con_nota: int
    hojas_sin_nota: int
    hojas_ilegibles: int
    hojas_en_revision: int
    preguntas_por_revisar: int
    aprobados: int
    promedio_en_decimas: float | None
    desviacion_en_decimas: float | None
    nota_aprobatoria_en_decimas: int = NOTA_APROBATORIA_EN_DECIMAS


@dataclass(frozen=True)
class MarcasDelExamen:
    """Cada pregunta de cada hoja con nota, en una sola de las cinco primeras categorías.
    `pendientes` cuenta, de las dudosas y las dobles, las que el profesor todavía no resolvió."""

    correctas: int
    incorrectas: int
    tenues_o_dudosas: int
    dobles: int
    en_blanco: int
    pendientes: int

    @property
    def total(self) -> int:
        return (
            self.correctas + self.incorrectas + self.tenues_o_dudosas + self.dobles + self.en_blanco
        )


@dataclass(frozen=True)
class PreguntaDelPanel:
    """Una pregunta de la clave en las hojas con nota. `hojas` no cuenta las que la anularon;
    `marcadas` dice cuántas veces quedó marcada cada opción, con lo resuelto por el profesor."""

    numero: int
    correcta: str
    aciertos: int
    hojas: int
    marcadas: dict[str, int]
    en_blanco: int
    dobles: int
    dudosas: int


@dataclass(frozen=True)
class PanelDelExamen:
    examen_id: str
    resumen: ResumenDelPanel
    marcas: MarcasDelExamen
    notas_en_decimas: tuple[int, ...]
    preguntas: tuple[PreguntaDelPanel, ...]


def panel_del_examen(
    examen_id: str,
    lector: LectorDeResultados,
    revisiones: LectorDeRevisiones,
    recepciones: LectorDeRecepciones,
) -> PanelDelExamen:
    """Las cifras del panel con el último hecho de cada hoja y lo que resolvió el profesor."""
    vigentes: dict[str, dict[str, Any]] = {}
    for hecho in lector.hechos_del_examen(examen_id):
        vigentes[hecho["hoja_id"]] = hecho
    resueltas = revisiones.resoluciones_del_examen(examen_id)

    notas: list[int] = []
    ilegibles = sin_nota = en_revision = preguntas_por_revisar = 0
    categorias = {"correctas": 0, "incorrectas": 0, "dudosas": 0, "dobles": 0, "en_blanco": 0}
    pendientes = 0
    por_pregunta: dict[int, dict[str, Any]] = {}

    for hoja_id, hecho in vigentes.items():
        if hecho.get("estado") == ILEGIBLE:
            ilegibles += 1
            continue
        lectura = {
            fila["numero"]: fila
            for fila in (hecho.get("lectura") or {}).get("preguntas", ())
            if isinstance(fila, dict) and "numero" in fila
        }
        calificacion = calificacion_del_hecho(hecho)
        if calificacion is None:
            sin_nota += 1
            dudosas_sin_nota = sum(
                1 for fila in lectura.values() if fila.get("estado") in (DUDOSA, DOBLE_MARCA)
            )
            preguntas_por_revisar += dudosas_sin_nota
            en_revision += 1 if dudosas_sin_nota else 0
            continue

        calificacion = nota_vigente(calificacion, resueltas.get(hoja_id, ()))
        notas.append(calificacion.nota_en_decimas)
        esperan = sum(1 for p in calificacion.preguntas if p.veredicto == POR_REVISAR)
        preguntas_por_revisar += esperan
        en_revision += 1 if esperan else 0

        for pregunta in calificacion.preguntas:
            estado_leido = (lectura.get(pregunta.numero) or {}).get("estado")
            if estado_leido == UNA_MARCA:
                categorias["correctas" if pregunta.veredicto == CORRECTA else "incorrectas"] += 1
            elif estado_leido == DUDOSA:
                categorias["dudosas"] += 1
            elif estado_leido == DOBLE_MARCA:
                categorias["dobles"] += 1
            elif estado_leido == SIN_MARCA:
                categorias["en_blanco"] += 1
            if pregunta.veredicto == POR_REVISAR:
                pendientes += 1

            datos = por_pregunta.setdefault(
                pregunta.numero,
                {
                    "correcta": pregunta.correcta,
                    "aciertos": 0,
                    "hojas": 0,
                    "marcadas": {opcion: 0 for opcion in OPCIONES_DE_RESPUESTA},
                    "en_blanco": 0,
                    "dobles": 0,
                    "dudosas": 0,
                },
            )
            if pregunta.veredicto != ANULADA:
                datos["hojas"] += 1
                datos["aciertos"] += 1 if pregunta.veredicto == CORRECTA else 0
            if pregunta.marcada in datos["marcadas"]:
                datos["marcadas"][pregunta.marcada] += 1
            if estado_leido == SIN_MARCA:
                datos["en_blanco"] += 1
            elif estado_leido == DOBLE_MARCA:
                datos["dobles"] += 1
            elif estado_leido == DUDOSA:
                datos["dudosas"] += 1

    promedio, desviacion = _media_y_desviacion(notas)
    return PanelDelExamen(
        examen_id=examen_id,
        resumen=ResumenDelPanel(
            hojas_recibidas=len(recepciones.recepciones_del_examen(examen_id)),
            hojas_leidas=len(vigentes),
            hojas_con_nota=len(notas),
            hojas_sin_nota=sin_nota,
            hojas_ilegibles=ilegibles,
            hojas_en_revision=en_revision,
            preguntas_por_revisar=preguntas_por_revisar,
            aprobados=sum(1 for nota in notas if nota >= NOTA_APROBATORIA_EN_DECIMAS),
            promedio_en_decimas=promedio,
            desviacion_en_decimas=desviacion,
        ),
        marcas=MarcasDelExamen(
            correctas=categorias["correctas"],
            incorrectas=categorias["incorrectas"],
            tenues_o_dudosas=categorias["dudosas"],
            dobles=categorias["dobles"],
            en_blanco=categorias["en_blanco"],
            pendientes=pendientes,
        ),
        notas_en_decimas=tuple(sorted(notas)),
        preguntas=tuple(
            PreguntaDelPanel(numero=numero, **datos)
            for numero, datos in sorted(por_pregunta.items())
        ),
    )


def _media_y_desviacion(notas: list[int]) -> tuple[float | None, float | None]:
    """La media y la desviación estándar poblacional: el panel describe al grupo entero que
    presentó el examen, no una muestra de él. Sin notas, ninguna de las dos."""
    if not notas:
        return None, None
    media = sum(notas) / len(notas)
    varianza = sum((nota - media) ** 2 for nota in notas) / len(notas)
    return round(media, 2), round(math.sqrt(varianza), 2)
