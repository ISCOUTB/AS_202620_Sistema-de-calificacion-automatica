"""Los exámenes que el docente puede elegir al subir las hojas: los que tienen una clave registrada.

Es una vista de la clave **sin las respuestas**: para elegir el examen al subir las hojas, el
docente solo necesita su identificador y saber si la clave ya está habilitada; sin habilitar, las
hojas se leen pero no reciben nota (RF-07). Vive aquí porque `autoria` es la dueña de la clave
(ADR-0007), que desde ADR-0026 se registra desde la aplicación (`registro_de_claves.py`).
"""

from dataclasses import dataclass

from infraestructura.claves import CatalogoDeClaves


@dataclass(frozen=True)
class ExamenConClave:
    examen_id: str
    habilitada: bool


def examenes_con_clave(catalogo: CatalogoDeClaves) -> tuple[ExamenConClave, ...]:
    """Los exámenes con clave registrada, ordenados por identificador."""
    return tuple(
        sorted(
            (
                ExamenConClave(clave.examen_id, habilitada=clave.habilitacion is not None)
                for clave in catalogo.claves_registradas()
            ),
            key=lambda examen: examen.examen_id,
        )
    )
