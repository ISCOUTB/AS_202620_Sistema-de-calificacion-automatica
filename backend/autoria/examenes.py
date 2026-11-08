"""Los exámenes que el docente puede elegir al subir las hojas: los que tienen una clave registrada.

Es una vista de la clave **sin las respuestas**. La ruta que la publica es pública hasta A-05
(AM-02), y para elegir el examen el docente solo necesita su identificador y saber si la clave ya
está habilitada: sin habilitar, las hojas se leen pero no reciben nota (RF-07). Vive aquí porque
`autoria` es la dueña de la clave (ADR-0007), aunque hasta A-04 la clave se escriba a mano.
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
