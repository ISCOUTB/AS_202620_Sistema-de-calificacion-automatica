"""Dónde se guarda cada examen con su dueño, detrás de un puerto (ADR-0028).

**Por qué hace falta.** Hasta ADR-0028 un examen no existía como tal: era el `examen_id` que el
docente escribía al registrar la clave, y todo (hojas, resultados, revisiones) se buscaba solo por
ese texto. Nada decía de quién era, así que cualquier docente con cuenta veía y cambiaba lo de los
demás, y dos docentes que escribieran `parcial-1` compartían el mismo examen. Este registro guarda
el examen con su dueño y con un identificador que acuña el sistema, distinto del nombre.

**Qué no cambia.** Los demás registros siguen guardando solo el `examen_id`: el dueño se deduce de
aquí. Así ni el worker, ni la cola, ni las tablas que ya tienen datos tienen que migrarse.

**El nombre se compara normalizado.** El adaptador recibe ya calculada la `clave_del_nombre` (la
regla vive en `autoria`) y garantiza que un mismo docente no tenga dos exámenes con la misma.
Docentes distintos sí pueden.

Dos adaptadores con el mismo comportamiento: un JSON en disco cuando no hay `DATABASE_URL` y la
tabla `examenes` en Postgres cuando la hay (`base_de_datos.py`). Solo la API escribe aquí.
"""

import json
import os
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Protocol

from infraestructura.modelo import Examen

__all__ = [
    "RegistroDeExamenes",
    "ExamenesEnDisco",
    "ExamenesEnMemoria",
    "siguiente_identificador",
    "DIGITOS_DEL_IDENTIFICADOR",
]

# `000001`: seis dígitos alcanzan para casi un millón de exámenes, y con ceros a la izquierda los
# identificadores se ordenan igual como texto que como número.
DIGITOS_DEL_IDENTIFICADOR = 6


def siguiente_identificador(existentes: set[str]) -> str:
    """El primer identificador numérico libre después del mayor que ya existe. Los identificadores
    anteriores a ADR-0028 (`PARCIAL-1`) no son números y no cuentan."""
    numeros = [int(i) for i in existentes if i.isdigit()]
    siguiente = max(numeros, default=0) + 1
    while f"{siguiente:0{DIGITOS_DEL_IDENTIFICADOR}d}" in existentes:
        siguiente += 1
    return f"{siguiente:0{DIGITOS_DEL_IDENTIFICADOR}d}"


class RegistroDeExamenes(Protocol):
    """El puerto. La API depende de esta forma, no de dónde se guarden los exámenes."""

    def crear(
        self, nombre: str, clave_del_nombre: str, docente: str, en: datetime
    ) -> tuple[Examen, bool]:
        """Crea el examen con un identificador nuevo y lo devuelve con `True`. Si el docente ya
        tiene uno con la misma `clave_del_nombre`, devuelve ese con `False` y no crea nada."""
        ...

    def examen(self, examen_id: str) -> Examen | None:
        """El examen con ese identificador, de quien sea, o None."""
        ...

    def examenes_del_docente(self, docente: str) -> tuple[Examen, ...]:
        """Los exámenes del docente, ordenados por identificador."""
        ...

    def adoptar(self, examen_id: str, docente: str, en: datetime) -> bool:
        """Registra a nombre de `docente` un examen anterior a ADR-0028, con su identificador viejo
        como nombre. Si ya estaba registrado no lo toca y devuelve False."""
        ...


class ExamenesEnDisco:
    """Adaptador sobre un único archivo JSON, que se reescribe entero con `os.replace` (atómico):
    quien lee ve el registro anterior o el nuevo, nunca uno a medias. Un candado por proceso
    ordena las escrituras; solo la API escribe, y corre en un proceso."""

    _candado = threading.Lock()

    def __init__(self, ruta: Path) -> None:
        self.ruta = Path(ruta)

    def _leer(self) -> list[dict]:
        try:
            datos = json.loads(self.ruta.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return []
        examenes = datos.get("examenes") if isinstance(datos, dict) else None
        return examenes if isinstance(examenes, list) else []

    def _escribir(self, examenes: list[dict]) -> None:
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        temporal = self.ruta.with_name(f".{self.ruta.name}.{uuid.uuid4().hex}.tmp")
        try:
            temporal.write_text(
                json.dumps({"examenes": examenes}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            os.replace(temporal, self.ruta)
        finally:
            temporal.unlink(missing_ok=True)

    def crear(
        self, nombre: str, clave_del_nombre: str, docente: str, en: datetime
    ) -> tuple[Examen, bool]:
        with self._candado:
            examenes = self._leer()
            for datos in examenes:
                if datos["docente"] == docente and datos["clave_del_nombre"] == clave_del_nombre:
                    return _examen_desde(datos), False
            datos = {
                "examen_id": siguiente_identificador({d["examen_id"] for d in examenes}),
                "nombre": nombre,
                "clave_del_nombre": clave_del_nombre,
                "docente": docente,
                "creado_en": en.isoformat(),
            }
            examenes.append(datos)
            self._escribir(examenes)
            return _examen_desde(datos), True

    def examen(self, examen_id: str) -> Examen | None:
        for datos in self._leer():
            if datos["examen_id"] == examen_id:
                return _examen_desde(datos)
        return None

    def examenes_del_docente(self, docente: str) -> tuple[Examen, ...]:
        return tuple(
            sorted(
                (_examen_desde(d) for d in self._leer() if d["docente"] == docente),
                key=lambda examen: examen.examen_id,
            )
        )

    def adoptar(self, examen_id: str, docente: str, en: datetime) -> bool:
        with self._candado:
            examenes = self._leer()
            if any(d["examen_id"] == examen_id for d in examenes):
                return False
            # El nombre del examen adoptado es su identificador viejo. Si el docente ya tiene uno
            # con ese nombre (no debería), la clave lleva el identificador para no chocar.
            clave = examen_id.casefold()
            if any(d["docente"] == docente and d["clave_del_nombre"] == clave for d in examenes):
                clave = f"{clave}#{examen_id}"
            examenes.append(
                {
                    "examen_id": examen_id,
                    "nombre": examen_id,
                    "clave_del_nombre": clave,
                    "docente": docente,
                    "creado_en": en.isoformat(),
                }
            )
            self._escribir(examenes)
            return True


class ExamenesEnMemoria:
    """Adaptador para pruebas: el mismo comportamiento, sin disco."""

    def __init__(self) -> None:
        self._examenes: list[tuple[Examen, str]] = []
        self._candado = threading.Lock()

    def crear(
        self, nombre: str, clave_del_nombre: str, docente: str, en: datetime
    ) -> tuple[Examen, bool]:
        with self._candado:
            for examen, clave in self._examenes:
                if examen.docente == docente and clave == clave_del_nombre:
                    return examen, False
            examen = Examen(
                siguiente_identificador({e.examen_id for e, _ in self._examenes}),
                nombre,
                docente,
                en,
            )
            self._examenes.append((examen, clave_del_nombre))
            return examen, True

    def examen(self, examen_id: str) -> Examen | None:
        return next((e for e, _ in self._examenes if e.examen_id == examen_id), None)

    def examenes_del_docente(self, docente: str) -> tuple[Examen, ...]:
        return tuple(
            sorted(
                (e for e, _ in self._examenes if e.docente == docente),
                key=lambda examen: examen.examen_id,
            )
        )

    def adoptar(self, examen_id: str, docente: str, en: datetime) -> bool:
        with self._candado:
            if any(e.examen_id == examen_id for e, _ in self._examenes):
                return False
            self._examenes.append(
                (Examen(examen_id, examen_id, docente, en), examen_id.casefold())
            )
            return True


def _examen_desde(datos: dict) -> Examen:
    return Examen(
        examen_id=datos["examen_id"],
        nombre=datos["nombre"],
        docente=datos["docente"],
        creado_en=datetime.fromisoformat(datos["creado_en"]),
    )
