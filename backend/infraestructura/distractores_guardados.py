"""Dónde se guardan los distractores que cada docente aprueba, detrás de un puerto (ADR-0029).

**Por qué hace falta.** El generador de RF-11 propone y el docente decide qué usa, pero hasta
ADR-0029 esa decisión vivía solo en la pantalla: al salir de Pauta se perdía. Este registro la
guarda a nombre del docente, para cada pregunta.

**La pregunta llega como llave.** El adaptador no sabe cómo se reconoce una pregunta: recibe la
`llave` ya calculada (la regla vive en `autoria`) y guarda una entrada por docente y llave.
Guardar otra vez con la misma llave reemplaza la entrada, y quitarla la borra. Lo del docente se
lista de lo más antiguo a lo más reciente, porque la pantalla lo pone al final de la lista de
preguntas.

Dos adaptadores con el mismo comportamiento: un JSON en disco cuando no hay `DATABASE_URL` y la
tabla `distractores_guardados` en Postgres cuando la hay (`base_de_datos.py`). Solo la API escribe
aquí.
"""

import json
import os
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Protocol

from infraestructura.modelo import DistractorGuardado, DistractoresGuardados

__all__ = ["RegistroDeDistractores", "DistractoresEnDisco", "DistractoresEnMemoria", "en_orden"]

# Lo guardado para una pregunta, con la llave que la reconoce.
ConLlave = tuple[str, DistractoresGuardados]


class RegistroDeDistractores(Protocol):
    """El puerto. La API depende de esta forma, no de dónde se guarden."""

    def guardar(self, llave: str, guardados: DistractoresGuardados) -> None:
        """Guarda los distractores del docente para la pregunta de `llave`, reemplazando los que
        tuviera."""
        ...

    def del_docente(self, docente: str) -> list[ConLlave]:
        """Lo que guardó el docente, con la llave de cada pregunta, de lo más antiguo a lo más
        reciente."""
        ...

    def eliminar(self, docente: str, llave: str) -> bool:
        """Quita lo guardado para esa pregunta. False si no había nada."""
        ...


def en_orden(guardados: list[ConLlave]) -> list[ConLlave]:
    """De lo más antiguo a lo más reciente; la llave desempata, para que el orden no dependa del
    adaptador."""
    return sorted(guardados, key=lambda par: (par[1].guardado_en.timestamp(), par[0]))


def _a_json(llave: str, guardados: DistractoresGuardados) -> dict:
    return {
        "docente": guardados.docente,
        "llave": llave,
        "enunciado": guardados.enunciado,
        "respuesta_correcta": guardados.respuesta_correcta,
        "distractores": [
            {"expresion": d.expresion, "error": d.error} for d in guardados.distractores
        ],
        "guardado_en": guardados.guardado_en.isoformat(),
    }


def _desde_json(datos: dict) -> DistractoresGuardados:
    return DistractoresGuardados(
        docente=datos["docente"],
        enunciado=datos["enunciado"],
        respuesta_correcta=datos["respuesta_correcta"],
        distractores=tuple(
            DistractorGuardado(d["expresion"], d["error"]) for d in datos["distractores"]
        ),
        guardado_en=datetime.fromisoformat(datos["guardado_en"]),
    )


class DistractoresEnDisco:
    """Adaptador sobre un único archivo JSON, que se reescribe entero con `os.replace` (atómico),
    como el registro de exámenes. Un candado por proceso ordena las escrituras."""

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

    def guardar(self, llave: str, guardados: DistractoresGuardados) -> None:
        with self._candado:
            preguntas = [
                d
                for d in self._leer()
                if not (d["docente"] == guardados.docente and d["llave"] == llave)
            ]
            preguntas.append(_a_json(llave, guardados))
            self._escribir(preguntas)

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


class DistractoresEnMemoria:
    """Adaptador para pruebas: el mismo comportamiento, sin disco."""

    def __init__(self) -> None:
        self._guardados: dict[tuple[str, str], DistractoresGuardados] = {}

    def guardar(self, llave: str, guardados: DistractoresGuardados) -> None:
        self._guardados[(guardados.docente, llave)] = guardados

    def del_docente(self, docente: str) -> list[ConLlave]:
        return en_orden([(llave, g) for (d, llave), g in self._guardados.items() if d == docente])

    def eliminar(self, docente: str, llave: str) -> bool:
        return self._guardados.pop((docente, llave), None) is not None
