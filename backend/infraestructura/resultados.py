"""Registro de lo que el worker leyó y calificó en cada hoja, detrás de un puerto.

**Por qué un registro propio y no la bitácora de recepción.** La bitácora la escribe la API, y
`BitacoraEnDisco` es un adaptador honesto para un solo proceso: si el worker, que en el servidor
del laboratorio es otro contenedor, agregara líneas al mismo archivo, dos procesos escribirían a la
vez sobre él. Aquí el único que escribe es el worker.

**Lo que precisa de ADR-0018.** ADR-0018 declara la bitácora como la fuente de verdad del estado
de cada hoja. Con este registro, el estado después de procesarla (`CALIFICADA`, `EN_REVISION`,
`SIN_CLAVE_HABILITADA`, `ILEGIBLE`) sale de aquí y no de la bitácora: el estado de una hoja es el
último hecho entre los dos registros, cada uno con su único escritor (ADR-0023, punto 9).

**Quien lo lee lo hace por otro puerto**, `LectorDeResultados`: la API, para mostrarle al profesor
cómo quedó cada hoja (`dashboard`). El worker escribe y la API lee; nadie más escribe.

**Igual que la bitácora, de solo agregado.** Cada línea es un hecho referido por `hoja_id`
(ADR-0018, punto 3). Volver a calificar una hoja es un trabajo nuevo que agrega otra línea; la
nota vigente es la última, y las anteriores quedan como historia. Mismo punto de aislamiento que
el almacén (arc42 §4.1): cuando R-06 elija un medio, cambia el adaptador.

**El código del estudiante viaja dentro de la lectura**, que es donde tiene que quedar para saber
de quién es la nota. Este registro lo guarda; el log no.

**Cada hecho lleva el estado en que dejó a la hoja.** No es una columna que se reescribe: es parte
de un hecho que no cambia, y el estado vigente es el del último hecho de la hoja. Lo deduce
`estado_tras_la_lectura`, la misma función que usa el worker para su log. Desde RF-08, lo que
resuelva el profesor va en otro registro (`infraestructura.revisiones`) y se aplica encima.

**Los recortes de las preguntas en revisión** son imágenes que el worker guarda en el almacén al
leer la hoja; aquí va solo su referencia, por número de pregunta. Muestran la fila de burbujas, sin
el código del estudiante.
"""

import json
import os
from collections.abc import Mapping
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

from infraestructura.modelo import (
    CALIFICADA,
    EN_REVISION,
    ILEGIBLE,
    SIN_CLAVE_HABILITADA,
    CalificacionDeHoja,
    LecturaDeHoja,
    ResultadoDePregunta,
)

__all__ = [
    "RegistroDeResultados",
    "LectorDeResultados",
    "ResultadosEnDisco",
    "RUTA_RESULTADOS_POR_OMISION",
    "SIN_CLAVE",
    "CLAVE_SIN_HABILITAR",
    "CLAVE_MAL_ESCRITA",
    "estado_tras_la_lectura",
    "calificacion_del_hecho",
]

# Dónde está el registro si no lo dice `RUTA_RESULTADOS`.
RUTA_RESULTADOS_POR_OMISION = "resultados/resultados-de-lectura.jsonl"

# Por qué una hoja leída se quedó sin nota. El estado es el mismo, `SIN_CLAVE_HABILITADA`, pero lo
# que hay que hacer cambia: escribir la clave, habilitarla o corregirla.
SIN_CLAVE = "sin_clave"
CLAVE_SIN_HABILITAR = "clave_sin_habilitar"
CLAVE_MAL_ESCRITA = "clave_mal_escrita"


def calificacion_del_hecho(hecho: Mapping[str, Any]) -> CalificacionDeHoja | None:
    """La calificación que guardó un hecho `leida`, tal como la escribió `registrar_lectura`, o
    None si la hoja se leyó sin nota."""
    datos = hecho.get("calificacion")
    if datos is None:
        return None
    return CalificacionDeHoja(
        examen_id=datos["examen_id"],
        nota_en_decimas=datos["nota_en_decimas"],
        puntos=datos["puntos"],
        puntos_posibles=datos["puntos_posibles"],
        provisional=datos["provisional"],
        codigo_por_revisar=datos["codigo_por_revisar"],
        preguntas=tuple(
            ResultadoDePregunta(
                numero=pregunta["numero"],
                veredicto=pregunta["veredicto"],
                marcada=pregunta["marcada"],
                correcta=pregunta["correcta"],
                peso=pregunta["peso"],
                puntos=pregunta["puntos"],
                resuelta_por_el_profesor=pregunta.get("resuelta_por_el_profesor", False),
            )
            for pregunta in datos["preguntas"]
        ),
    )


def estado_tras_la_lectura(calificacion: CalificacionDeHoja | None) -> str:
    """El estado de una hoja leída: sin nota, con nota provisional (algo espera al profesor) o
    calificada."""
    if calificacion is None:
        return SIN_CLAVE_HABILITADA
    return EN_REVISION if calificacion.provisional else CALIFICADA


class RegistroDeResultados(Protocol):
    """El puerto. El worker depende de esta forma, no de dónde quede escrito."""

    def registrar_lectura(
        self,
        hoja_id: str,
        trabajo_id: str,
        examen_id: str,
        lectura: LecturaDeHoja,
        calificacion: CalificacionDeHoja | None,
        motivo_sin_nota: str | None = None,
        recortes: Mapping[int, str] | None = None,
    ) -> None:
        """Deja constancia de una hoja leída. Si `calificacion` es None, `motivo_sin_nota` dice
        por qué (`SIN_CLAVE`, `CLAVE_SIN_HABILITAR` o `CLAVE_MAL_ESCRITA`). `recortes` son las
        referencias en el almacén de las filas en revisión, por número de pregunta."""
        ...

    def registrar_lectura_imposible(
        self, hoja_id: str, trabajo_id: str, examen_id: str, motivo: str
    ) -> None:
        """Deja constancia de una hoja que no se pudo leer, con el motivo estable del error de
        `omr` (por ejemplo `marcas_de_registro_no_encontradas`)."""
        ...


class LectorDeResultados(Protocol):
    """El puerto de lectura. Quien muestra los resultados depende de esta forma."""

    def hechos_del_examen(self, examen_id: str) -> list[dict[str, Any]]:
        """Los hechos de las hojas de un examen, en el orden en que se escribieron."""
        ...


class ResultadosEnDisco:
    """Adaptador **provisional** de solo agregado sobre un archivo JSON Lines.

    Como `BitacoraEnDisco`: cada línea se descarga a disco con `fsync` antes de devolver el
    control, y nada se reescribe. Un error del disco sube como `OSError`, que el worker trata como
    transitorio (ADR-0020)."""

    def __init__(self, ruta: Path) -> None:
        self.ruta = Path(ruta)
        self.ruta.parent.mkdir(parents=True, exist_ok=True)

    def registrar_lectura(
        self,
        hoja_id: str,
        trabajo_id: str,
        examen_id: str,
        lectura: LecturaDeHoja,
        calificacion: CalificacionDeHoja | None,
        motivo_sin_nota: str | None = None,
        recortes: Mapping[int, str] | None = None,
    ) -> None:
        if (calificacion is None) == (motivo_sin_nota is None):
            raise ValueError("Una hoja leída lleva calificación o motivo para no tenerla, no ambos")
        self._agregar(
            {
                "hecho": "leida",
                "hoja_id": hoja_id,
                "trabajo_id": trabajo_id,
                "examen_id": examen_id,
                "estado": estado_tras_la_lectura(calificacion),
                "motivo_sin_nota": motivo_sin_nota,
                "lectura": asdict(lectura),
                "calificacion": None if calificacion is None else asdict(calificacion),
                "recortes": {str(numero): ref for numero, ref in (recortes or {}).items()},
                "momento": datetime.now(timezone.utc).isoformat(),
            }
        )

    def registrar_lectura_imposible(
        self, hoja_id: str, trabajo_id: str, examen_id: str, motivo: str
    ) -> None:
        self._agregar(
            {
                "hecho": "ilegible",
                "hoja_id": hoja_id,
                "trabajo_id": trabajo_id,
                "examen_id": examen_id,
                "estado": ILEGIBLE,
                "motivo": motivo,
                "momento": datetime.now(timezone.utc).isoformat(),
            }
        )

    def hechos_del_examen(self, examen_id: str) -> list[dict[str, Any]]:
        """Recorre el archivo línea por línea y solo decodifica las que nombran al examen.

        Una línea que no se puede leer se salta: puede ser la que el worker, en otro proceso, está
        escribiendo en ese momento. Recorrer el archivo entero en cada consulta es lo que tiene de
        provisional: con R-06 es una consulta a una tabla con índice."""
        if not self.ruta.exists():
            return []
        nombre = json.dumps(examen_id, ensure_ascii=False)
        hechos = []
        with open(self.ruta, encoding="utf-8", errors="replace") as archivo:
            for linea in archivo:
                if nombre not in linea:
                    continue
                try:
                    hecho = json.loads(linea)
                except ValueError:
                    continue
                if isinstance(hecho, dict) and hecho.get("examen_id") == examen_id:
                    hechos.append(hecho)
        return hechos

    def _agregar(self, hecho: dict) -> None:
        linea = json.dumps(hecho, ensure_ascii=False) + "\n"
        with open(self.ruta, "a", encoding="utf-8") as archivo:
            archivo.write(linea)
            archivo.flush()
            os.fsync(archivo.fileno())
