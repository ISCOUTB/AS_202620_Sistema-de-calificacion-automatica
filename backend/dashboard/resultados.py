"""Los resultados de un examen tal como los ve el profesor: el estado vigente de cada hoja leída.

Es una proyección del registro de resultados (ADR-0018 y ADR-0023, punto 9): el último hecho de
cada hoja manda, y los anteriores quedan como historia. No guarda nada; se calcula en cada consulta.

**Sin el código del estudiante.** La API no tiene inicio de sesión hasta A-05, y el modelo de
amenazas de la S13 aceptó ese riesgo solo mientras no entren hojas reales (AM-02). Esta proyección
no lleva el código: dice si se leyó completo, y nada más. Mostrarlo, o exportar las notas con él,
llega con A-05. El código sigue en el registro, que es donde hace falta para saber de quién es la
nota.

**Las hojas se reconocen por su `hoja_id`**, que la API le devolvió al profesor al recibir cada
una junto con el nombre de su archivo (ADR-0018). La pantalla une las dos cosas.

**Lo que resolvió el profesor se aplica encima** (RF-08): la nota de una hoja con resoluciones la
recalcula `calificacion` con ellas, y `revisada` lo dice, para que una nota corregida a mano se
distinga de una automática (RNF-15).
"""

from dataclasses import dataclass
from typing import Any

from calificacion import recalcular, resoluciones_vigentes
from infraestructura.modelo import (
    CODIGO_COMPLETO,
    DOBLE_MARCA,
    DUDOSA,
    ILEGIBLE,
    POR_REVISAR,
    ResolucionDelProfesor,
)
from infraestructura.resultados import (
    LectorDeResultados,
    calificacion_del_hecho,
    estado_tras_la_lectura,
)
from infraestructura.revisiones import LectorDeRevisiones

__all__ = ["ResultadoDeHoja", "ResultadosDelExamen", "resultados_del_examen"]


@dataclass(frozen=True)
class ResultadoDeHoja:
    """Cómo quedó una hoja después de leerla.

    `motivo` dice por qué no tiene nota (`sin_clave`, `clave_sin_habilitar`, `clave_mal_escrita`)
    o por qué no se pudo leer (`imagen_ilegible`, `marcas_de_registro_no_encontradas`...).
    `preguntas_por_revisar` son las que esperan al profesor: con nota, las que quedaron por
    revisar; sin clave, las dudosas y las de doble marca de la lectura. `codigo_completo` es None
    en una hoja ilegible. `revisada` dice si la nota incluye resoluciones del profesor."""

    hoja_id: str
    estado: str
    motivo: str | None
    nota_en_decimas: int | None
    provisional: bool
    preguntas_por_revisar: tuple[int, ...]
    codigo_completo: bool | None
    momento: str
    revisada: bool = False


@dataclass(frozen=True)
class ResultadosDelExamen:
    """Las hojas leídas de un examen, en el orden en que se leyó cada una por primera vez."""

    examen_id: str
    hojas: tuple[ResultadoDeHoja, ...]


def resultados_del_examen(
    examen_id: str, lector: LectorDeResultados, revisiones: LectorDeRevisiones | None = None
) -> ResultadosDelExamen:
    """El último hecho de cada hoja del examen, con lo que resolvió el profesor encima. Una hoja
    que se volvió a leer conserva su lugar en la lista y muestra la lectura nueva."""
    vigentes: dict[str, dict[str, Any]] = {}
    for hecho in lector.hechos_del_examen(examen_id):
        vigentes[hecho["hoja_id"]] = hecho
    resueltas = {} if revisiones is None else revisiones.resoluciones_del_examen(examen_id)
    return ResultadosDelExamen(
        examen_id=examen_id,
        hojas=tuple(
            _resultado(hecho, resueltas.get(hoja_id, ())) for hoja_id, hecho in vigentes.items()
        ),
    )


def _resultado(
    hecho: dict[str, Any], resoluciones: tuple[ResolucionDelProfesor, ...] = ()
) -> ResultadoDeHoja:
    momento = str(hecho.get("momento", ""))
    if hecho.get("estado") == ILEGIBLE:
        return ResultadoDeHoja(
            hoja_id=hecho["hoja_id"],
            estado=ILEGIBLE,
            motivo=hecho.get("motivo"),
            nota_en_decimas=None,
            provisional=False,
            preguntas_por_revisar=(),
            codigo_completo=None,
            momento=momento,
        )
    lectura = hecho.get("lectura") or {}
    calificacion = calificacion_del_hecho(hecho)
    revisada = False
    estado = hecho["estado"]
    if calificacion is not None:
        vigentes = resoluciones_vigentes(calificacion, resoluciones)
        if vigentes:
            calificacion = recalcular(calificacion, vigentes)
            estado = estado_tras_la_lectura(calificacion)
            revisada = True
        por_revisar = tuple(
            p.numero for p in calificacion.preguntas if p.veredicto == POR_REVISAR
        )
        nota = calificacion.nota_en_decimas
        provisional = calificacion.provisional
    else:
        por_revisar = tuple(
            p["numero"]
            for p in lectura.get("preguntas", ())
            if p.get("estado") in (DUDOSA, DOBLE_MARCA)
        )
        nota, provisional = None, False
    return ResultadoDeHoja(
        hoja_id=hecho["hoja_id"],
        estado=estado,
        motivo=hecho.get("motivo_sin_nota"),
        nota_en_decimas=nota,
        provisional=provisional,
        preguntas_por_revisar=por_revisar,
        codigo_completo=(lectura.get("codigo") or {}).get("estado") == CODIGO_COMPLETO,
        momento=momento,
        revisada=revisada,
    )
