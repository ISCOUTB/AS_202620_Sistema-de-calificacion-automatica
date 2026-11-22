"""Dónde se relee la clave de un examen, detrás de un puerto.

**Por qué en `infraestructura` y no en `calificacion`.** `calificacion` no puede importar
`autoria`, que es la dueña de la clave (ADR-0007), y tampoco necesita saber de dónde sale: recibe
la `ClaveDeRespuestas` como parámetro, y quien la busca es el worker. Lo que sí hace falta es leerla
de algún lado sin que nadie fuera de este archivo sepa si es un JSON, una tabla o lo que decida el
ADR de persistencia (R-06). Es el mismo punto de aislamiento que el almacén y la bitácora (arc42
§4.1, ADR-0006), no uno nuevo.

**Por qué el adaptador no decide si la clave está habilitada.** Devuelve la clave tal como se
registró, habilitada o no. La regla de no calificar sin habilitación (RF-07) es de dominio y la
aplica `calificacion`; si el adaptador filtrara, un cambio de medio podría perderla sin que
ninguna prueba del dominio lo notara.

**Un adaptador que relee no es un segundo dueño** (ADR-0007, punto 5): `ClavesEnDisco` devuelve
los campos que se escribieron, sin corregir ni completar ninguno. Escribir claves es de `autoria`
y llega con A-04; hasta entonces, la clave de un examen sintético se escribe a mano.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

from infraestructura.almacen import directorio_del_examen
from infraestructura.modelo import ClaveDeRespuestas, Habilitacion, PreguntaDeLaClave

__all__ = [
    "CatalogoDeClaves",
    "FuenteDeClaves",
    "ClavesEnDisco",
    "ClaveMalEscrita",
    "RUTA_CLAVES_POR_OMISION",
]

# Dónde están las claves si no lo dice `RUTA_CLAVES`. Igual que `RUTA_ALMACEN_POR_OMISION`, se
# declara una sola vez aquí para que el worker y las herramientas no repitan el literal.
RUTA_CLAVES_POR_OMISION = "claves_de_respuestas"


class ClaveMalEscrita(ValueError):
    """El archivo de la clave existe pero no tiene la forma de una clave. Para el worker es como
    no tener clave: la hoja queda `SIN_CLAVE_HABILITADA`, con este motivo."""


class FuenteDeClaves(Protocol):
    """El puerto. El worker depende de esta forma, no de dónde esté guardada la clave."""

    def clave_del_examen(self, examen_id: str) -> ClaveDeRespuestas | None:
        """La clave registrada para el examen, habilitada o no, o None si no hay ninguna."""
        ...


class CatalogoDeClaves(Protocol):
    """El puerto de la pantalla de carga: qué exámenes tienen una clave registrada, para que el
    docente elija el suyo de una lista en vez de escribir el identificador de memoria. Es un
    puerto aparte del de arriba porque el worker no lo necesita."""

    def claves_registradas(self) -> tuple[ClaveDeRespuestas, ...]:
        """Las claves que `clave_del_examen` devolvería, habilitadas o no."""
        ...


class ClavesEnDisco:
    """Adaptador **provisional**: un JSON por examen en `directorio`.

    El nombre del archivo sale de `directorio_del_examen`, la misma regla del almacén: el
    `examen_id` llega en el mensaje de la cola y no puede elegir una ruta fuera del directorio.
    Un archivo que no cumple la forma de la clave es `ClaveMalEscrita`, no None: no es lo mismo
    un examen sin clave que una clave mal escrita.

    La forma, con `peso` opcional (vale lo que diga el modelo, 1,0) y `habilitacion` nula
    mientras el profesor no habilite:

        {"examen_id": "CALC-2026-01",
         "preguntas": [{"numero": 1, "correcta": "A", "peso": 1.0}, ...],
         "habilitacion": {"por": "...", "en": "2026-11-03T12:00:00+00:00"}}

    Aquí solo se comprueba la forma. Que la clave quepa en la hoja (números, opciones, pesos) lo
    decide `calificacion`, que es donde vive esa regla."""

    def __init__(self, directorio: Path) -> None:
        self.directorio = Path(directorio)

    def clave_del_examen(self, examen_id: str) -> ClaveDeRespuestas | None:
        """Lee `<directorio>/<directorio_del_examen(examen_id)>.json`.

        Un error del disco que no sea la ausencia del archivo sube como `OSError`: es transitorio
        y el worker lo reintenta (ADR-0020)."""
        ruta = self.directorio / f"{directorio_del_examen(examen_id)}.json"
        try:
            texto = ruta.read_text(encoding="utf-8")
        except FileNotFoundError:
            return None
        try:
            datos = json.loads(texto)
        except json.JSONDecodeError as error:
            raise ClaveMalEscrita(f"La clave de {examen_id} no es JSON válido: {error}") from error
        return _clave_desde(datos, examen_id)

    def claves_registradas(self) -> tuple[ClaveDeRespuestas, ...]:
        """Cada clave del directorio que `clave_del_examen` encontraría con su propio `examen_id`.

        Deja fuera, sin fallar, lo que no es una clave legible: un archivo mal escrito y uno cuyo
        nombre no corresponde a su `examen_id`, que el worker nunca leería. Un directorio que no
        existe todavía es un catálogo vacío."""
        claves = []
        for ruta in sorted(self.directorio.glob("*.json")):
            try:
                datos = json.loads(ruta.read_text(encoding="utf-8"))
            except FileNotFoundError:
                continue  # Se borró entre el listado y la lectura.
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
            examen_id = datos.get("examen_id") if isinstance(datos, dict) else None
            if not isinstance(examen_id, str):
                continue
            if ruta.name != f"{directorio_del_examen(examen_id)}.json":
                continue
            try:
                claves.append(_clave_desde(datos, examen_id))
            except ClaveMalEscrita:
                continue
        return tuple(claves)


def _clave_desde(datos: Any, examen_id: str) -> ClaveDeRespuestas:
    if not isinstance(datos, dict):
        raise ClaveMalEscrita(f"La clave de {examen_id} no es un objeto JSON")
    if datos.get("examen_id") != examen_id:
        # Un archivo copiado con el nombre de otro examen calificaría con la clave equivocada.
        raise ClaveMalEscrita(
            f"El archivo de la clave de {examen_id} dice ser de {datos.get('examen_id')!r}"
        )
    preguntas = datos.get("preguntas")
    if not isinstance(preguntas, list):
        raise ClaveMalEscrita(f"La clave de {examen_id} no trae la lista de preguntas")
    return ClaveDeRespuestas(
        examen_id=examen_id,
        preguntas=tuple(_pregunta_desde(pregunta, examen_id) for pregunta in preguntas),
        habilitacion=_habilitacion_desde(datos.get("habilitacion"), examen_id),
    )


def _pregunta_desde(datos: Any, examen_id: str) -> PreguntaDeLaClave:
    if not isinstance(datos, dict):
        raise ClaveMalEscrita(f"Una pregunta de la clave de {examen_id} no es un objeto")
    numero, correcta = datos.get("numero"), datos.get("correcta")
    peso = datos.get("peso", 1.0)
    # `bool` es un `int` en Python, y `true` no es un número de pregunta ni un peso.
    if not isinstance(numero, int) or isinstance(numero, bool):
        raise ClaveMalEscrita(f"Una pregunta de la clave de {examen_id} no trae un número entero")
    if not isinstance(correcta, str):
        raise ClaveMalEscrita(f"La pregunta {numero} de la clave de {examen_id} no trae la correcta")
    if not isinstance(peso, int | float) or isinstance(peso, bool):
        raise ClaveMalEscrita(f"La pregunta {numero} de la clave de {examen_id} no trae un peso")
    return PreguntaDeLaClave(numero=numero, correcta=correcta, peso=float(peso))


def _habilitacion_desde(datos: Any, examen_id: str) -> Habilitacion | None:
    if datos is None:
        return None
    if not isinstance(datos, dict) or not isinstance(datos.get("por"), str):
        raise ClaveMalEscrita(f"La habilitación de la clave de {examen_id} no dice quién")
    try:
        en = datetime.fromisoformat(datos["en"])
    except (KeyError, TypeError, ValueError) as error:
        raise ClaveMalEscrita(
            f"La habilitación de la clave de {examen_id} no trae una fecha ISO 8601"
        ) from error
    if en.tzinfo is None:
        raise ClaveMalEscrita(
            f"La fecha de habilitación de la clave de {examen_id} no dice su zona horaria"
        )
    return Habilitacion(por=datos["por"], en=en)
