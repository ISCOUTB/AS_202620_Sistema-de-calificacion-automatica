"""Dónde se guardan las preguntas que cada docente agrega en Pauta, detrás de un puerto (ADR-0030).

**Por qué hace falta.** Hasta ADR-0030, la lista de preguntas de Pauta era de ejemplo y una
pregunta escrita en el generador se perdía al salir. Este registro guarda las que el docente
agrega, a su nombre: es el comienzo del banco de preguntas (RF-06).

**La pregunta llega como llave**, como en los distractores guardados (ADR-0029): el adaptador no
sabe cómo se reconoce una pregunta, recibe la `llave` ya calculada en `autoria`. Agregar una llave
que el docente ya tiene no cambia nada y devuelve False.

Dos adaptadores con el mismo comportamiento: un JSON en disco cuando no hay `DATABASE_URL` y la
tabla `preguntas_del_docente` en Postgres cuando la hay (`base_de_datos.py`). Solo la API escribe
aquí.
"""

import json
import os
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Protocol

from infraestructura.modelo import PreguntaDelDocente

__all__ = ["RegistroDePreguntas", "PreguntasEnDisco", "PreguntasEnMemoria", "en_orden"]

# Una pregunta con la llave que la reconoce.
ConLlave = tuple[str, PreguntaDelDocente]


class RegistroDePreguntas(Protocol):
    """El puerto. La API depende de esta forma, no de dónde se guarden."""

    def agregar(self, llave: str, pregunta: PreguntaDelDocente) -> bool:
        """Agrega la pregunta a las del docente. False, sin cambiar nada, si ya la tenía."""
        ...

    def del_docente(self, docente: str) -> list[ConLlave]:
        """Las preguntas del docente con su llave, de la más reciente a la más antigua: la
        pantalla pone arriba la última que agregó."""
        ...

    def eliminar(self, docente: str, llave: str) -> bool:
        """Quita la pregunta de las del docente. False si no la tenía."""
        ...


def en_orden(preguntas: list[ConLlave]) -> list[ConLlave]:
    """De la más reciente a la más antigua; la llave desempata, para que el orden no dependa del
    adaptador."""
    return sorted(preguntas, key=lambda par: (-par[1].agregada_en.timestamp(), par[0]))


def _a_json(llave: str, pregunta: PreguntaDelDocente) -> dict:
    return {
        "docente": pregunta.docente,
        "llave": llave,
        "enunciado": pregunta.enunciado,
        "respuesta_correcta": pregunta.respuesta_correcta,
        "agregada_en": pregunta.agregada_en.isoformat(),
    }


def _desde_json(datos: dict) -> PreguntaDelDocente:
    return PreguntaDelDocente(
        docente=datos["docente"],
        enunciado=datos["enunciado"],
        respuesta_correcta=datos["respuesta_correcta"],
        agregada_en=datetime.fromisoformat(datos["agregada_en"]),
    )


class PreguntasEnDisco:
    """Adaptador sobre un único archivo JSON, que se reescribe entero con `os.replace` (atómico),
    como los distractores guardados. Un candado por proceso ordena las escrituras."""

    _candado = threading.Lock()

    def __init__(self, ruta: Path) -> None:
        self.ruta = Path(ruta)

    def _leer(self) -> list[dict]:
        try:
            datos = json.loads(self.ruta.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return []
        preguntas = datos.get("preguntas") if isinstance(datos, dict) else None
        return preguntas if isinstance(preguntas, list) else []

    def _escribir(self, preguntas: list[dict]) -> None:
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        temporal = self.ruta.with_name(f".{self.ruta.name}.{uuid.uuid4().hex}.tmp")
        try:
            temporal.write_text(
                json.dumps({"preguntas": preguntas}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            os.replace(temporal, self.ruta)
        finally:
            temporal.unlink(missing_ok=True)

    def agregar(self, llave: str, pregunta: PreguntaDelDocente) -> bool:
        with self._candado:
            preguntas = self._leer()
            if any(d["docente"] == pregunta.docente and d["llave"] == llave for d in preguntas):
                return False
            preguntas.append(_a_json(llave, pregunta))
            self._escribir(preguntas)
            return True

    def del_docente(self, docente: str) -> list[ConLlave]:
        return en_orden(
            [(d["llave"], _desde_json(d)) for d in self._leer() if d["docente"] == docente]
        )

    def eliminar(self, docente: str, llave: str) -> bool:
        with self._candado:
            preguntas = self._leer()
            quedan = [d for d in preguntas if not (d["docente"] == docente and d["llave"] == llave)]
            if len(quedan) == len(preguntas):
                return False
            self._escribir(quedan)
            return True


class PreguntasEnMemoria:
    """Adaptador para pruebas: el mismo comportamiento, sin disco."""

    def __init__(self) -> None:
        self._preguntas: dict[tuple[str, str], PreguntaDelDocente] = {}

    def agregar(self, llave: str, pregunta: PreguntaDelDocente) -> bool:
        if (pregunta.docente, llave) in self._preguntas:
            return False
        self._preguntas[(pregunta.docente, llave)] = pregunta
        return True

    def del_docente(self, docente: str) -> list[ConLlave]:
        return en_orden([(llave, p) for (d, llave), p in self._preguntas.items() if d == docente])

    def eliminar(self, docente: str, llave: str) -> bool:
        return self._preguntas.pop((docente, llave), None) is not None
