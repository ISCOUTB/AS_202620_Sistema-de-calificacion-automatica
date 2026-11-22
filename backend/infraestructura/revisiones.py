"""Registro de lo que el profesor resolvió en las preguntas en revisión (RF-08), detrás de un puerto.

**Por qué un registro propio.** El de resultados lo escribe solo el worker, y la bitácora, solo la
API al recibir. Lo que decide el profesor llega por la API, así que va en un tercer registro que
solo escribe la API: cada registro conserva su único escritor (ADR-0018 y ADR-0023, punto 9). La
nota vigente de una hoja es la última lectura con las resoluciones de este registro encima, y la
calcula `calificacion` en cada consulta.

**Quién y cuándo (RF-10, RNF-15).** Cada resolución lleva `por` y `en`. Hoy `por` es el nombre que
escribe el profesor, **sin verificar**, igual que la habilitación de la clave: la identidad
autenticada llega con A-05. Lo que sí queda desde ya es que una nota corregida a mano se distingue
de una automática, porque sus resoluciones están aquí.

**De solo agregado, como los otros dos.** Cambiar de opinión sobre una pregunta es otra línea; la
última manda y las anteriores quedan como historia. Cuando R-06 elija un medio, cambia el adaptador.
"""

import json
import os
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

from infraestructura.modelo import ResolucionDelProfesor

__all__ = [
    "RegistroDeRevisiones",
    "LectorDeRevisiones",
    "RevisionesDelProfesor",
    "RevisionesEnDisco",
    "RUTA_REVISIONES_POR_OMISION",
]

# Dónde está el registro si no lo dice `RUTA_REVISIONES`.
RUTA_REVISIONES_POR_OMISION = "resultados/revisiones-del-profesor.jsonl"


class RegistroDeRevisiones(Protocol):
    """El puerto de escritura. Solo la API lo usa."""

    def registrar_resoluciones(
        self, hoja_id: str, examen_id: str, resoluciones: Iterable[ResolucionDelProfesor]
    ) -> None:
        """Deja constancia de lo que el profesor resolvió en una hoja, todo junto."""
        ...


class LectorDeRevisiones(Protocol):
    """El puerto de lectura."""

    def resoluciones_del_examen(
        self, examen_id: str
    ) -> dict[str, tuple[ResolucionDelProfesor, ...]]:
        """Las resoluciones de cada hoja del examen, por `hoja_id`, en el orden en que se
        escribieron."""
        ...


class RevisionesDelProfesor(RegistroDeRevisiones, LectorDeRevisiones, Protocol):
    """Los dos puertos juntos, que es lo que necesita la ruta que resuelve: leer lo anterior y
    agregar lo nuevo."""


class RevisionesEnDisco:
    """Adaptador **provisional** de solo agregado sobre un archivo JSON Lines, como
    `ResultadosEnDisco`: cada línea se descarga a disco con `fsync` antes de devolver el control."""

    def __init__(self, ruta: Path) -> None:
        self.ruta = Path(ruta)

    def registrar_resoluciones(
        self, hoja_id: str, examen_id: str, resoluciones: Iterable[ResolucionDelProfesor]
    ) -> None:
        lista = [
            {
                "numero": resolucion.numero,
                "veredicto": resolucion.veredicto,
                "opcion": resolucion.opcion,
                "por": resolucion.por,
                "en": resolucion.en.isoformat(),
            }
            for resolucion in resoluciones
        ]
        if not lista:
            raise ValueError("No hay resoluciones que registrar")
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        linea = json.dumps(
            {
                "hecho": "resuelta",
                "hoja_id": hoja_id,
                "examen_id": examen_id,
                "resoluciones": lista,
                "momento": datetime.now(timezone.utc).isoformat(),
            },
            ensure_ascii=False,
        )
        with open(self.ruta, "a", encoding="utf-8") as archivo:
            archivo.write(linea + "\n")
            archivo.flush()
            os.fsync(archivo.fileno())

    def resoluciones_del_examen(
        self, examen_id: str
    ) -> dict[str, tuple[ResolucionDelProfesor, ...]]:
        """Recorre el archivo y se queda con las líneas del examen. Una línea que no se puede leer
        se salta: solo puede ser la última, truncada al morir el proceso que la escribía."""
        if not self.ruta.exists():
            return {}
        nombre = json.dumps(examen_id, ensure_ascii=False)
        por_hoja: dict[str, list[ResolucionDelProfesor]] = {}
        with open(self.ruta, encoding="utf-8", errors="replace") as archivo:
            for linea in archivo:
                if nombre not in linea:
                    continue
                try:
                    hecho = json.loads(linea)
                    if hecho.get("examen_id") != examen_id:
                        continue
                    resoluciones = [_resolucion_desde(datos) for datos in hecho["resoluciones"]]
                except (ValueError, KeyError, TypeError, AttributeError):
                    continue
                por_hoja.setdefault(hecho["hoja_id"], []).extend(resoluciones)
        return {hoja_id: tuple(lista) for hoja_id, lista in por_hoja.items()}


def _resolucion_desde(datos: dict[str, Any]) -> ResolucionDelProfesor:
    return ResolucionDelProfesor(
        numero=int(datos["numero"]),
        veredicto=str(datos["veredicto"]),
        opcion=datos["opcion"],
        por=str(datos["por"]),
        en=datetime.fromisoformat(datos["en"]),
    )
