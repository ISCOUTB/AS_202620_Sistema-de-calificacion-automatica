"""El token con que las herramientas de medición hablan con una API que pide sesión (ADR-0025).

Va en la variable `QUANTIA_TOKEN` y no en un argumento, que quedaría en el historial de la
terminal. Se obtiene entrando con `POST /sesion`; vence a las `SESION_HORAS` del servidor. Las
herramientas que hablan con la aplicación dentro del mismo proceso (`TestClient`) no lo necesitan:
sustituyen la dependencia de la sesión, porque miden la ruta y no la entrada."""

import os
from datetime import datetime, timezone

from infraestructura.examenes import ExamenesEnMemoria
from infraestructura.modelo import Examen

# Con quién hablan las herramientas que sustituyen la sesión, para que se distinga en el registro
# de revisiones de un docente real.
DOCENTE_DE_MEDICION = "medicion@quantia"


def encabezados_de_sesion() -> dict[str, str]:
    """El encabezado `Authorization` con el token de `QUANTIA_TOKEN`, o nada si no hay token."""
    token = os.environ.get("QUANTIA_TOKEN", "").strip()
    return {"Authorization": f"Bearer {token}"} if token else {}


class RegistroDeMedicion(ExamenesEnMemoria):
    """El registro de exámenes de las herramientas que hablan con la aplicación en el mismo proceso
    (ADR-0028): todo examen que nombren es del docente de medición. Miden la recepción, no el
    dueño, y no deben escribir en el registro real."""

    def examen(self, examen_id: str) -> Examen | None:
        return super().examen(examen_id) or Examen(
            examen_id, examen_id, DOCENTE_DE_MEDICION, datetime.now(timezone.utc)
        )
