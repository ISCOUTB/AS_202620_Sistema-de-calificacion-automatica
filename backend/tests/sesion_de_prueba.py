"""El docente con el que las pruebas de las rutas hablan con la API (`conftest.py`)."""

from datetime import datetime, timezone

from infraestructura.examenes import ExamenesEnMemoria
from infraestructura.modelo import Examen

DOCENTE_DE_PRUEBA = "docente@quantia.test"


class RegistroDondeTodoEsDelDocente(ExamenesEnMemoria):
    """El registro de exámenes de las pruebas que no tratan del dueño (ADR-0028): un examen que no
    se creó es del docente de prueba, con su identificador como nombre. Así las pruebas escritas
    antes de que los exámenes tuvieran dueño siguen probando lo suyo con `PARCIAL-1` y compañía.

    Que un docente no vea lo de otro lo prueban `test_examenes_del_docente.py` y
    `test_aislamiento_entre_docentes.py`, con el registro de verdad."""

    def examen(self, examen_id: str) -> Examen | None:
        return super().examen(examen_id) or Examen(
            examen_id, examen_id, DOCENTE_DE_PRUEBA, datetime(2026, 11, 1, tzinfo=timezone.utc)
        )
