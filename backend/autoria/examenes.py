"""Los exámenes de cada docente (ADR-0028): crearlos con un nombre, comprobar de quién son y
listarlos con su clave.

**El identificador no es el nombre.** El docente escribe un nombre («Parcial 1») y el sistema acuña
el identificador (`000001`). Dos docentes pueden llamar igual a sus exámenes; cada uno tiene el
suyo. Un mismo docente no repite nombre: pedir crear uno que ya tiene devuelve el que ya existe, y
así la pantalla de la clave puede pedirlo sin preguntar antes si existe.

**Un examen ajeno no existe.** `examen_del_docente` responde igual a un examen que no existe y a uno
de otro docente, para que nadie pueda averiguar qué identificadores usan los demás.

**Los exámenes anteriores a ADR-0028** no tenían dueño. `adoptar_examenes_sin_dueno` los registra
con su identificador viejo como nombre, para que sus hojas y resultados no se pierdan ni queden a la
vista de todos: a nombre de quien habilitó su clave, si ese docente sigue teniendo cuenta, y si no a
nombre de un docente elegido que ya tiene cuenta.

Lo de la clave sigue siendo como en ADR-0026: es una vista **sin las respuestas**. Para elegir el
examen basta con su identificador, su nombre y saber si la clave está habilitada.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime

from infraestructura.claves import CatalogoDeClaves, FuenteDeClaves
from infraestructura.examenes import RegistroDeExamenes
from infraestructura.modelo import Examen

__all__ = [
    "ExamenConClave",
    "ExamenNoEncontrado",
    "NombreDeExamenInvalido",
    "LARGO_MAXIMO_DEL_NOMBRE",
    "adoptar_examenes_sin_dueno",
    "clave_del_nombre",
    "crear_examen",
    "examen_del_docente",
    "examenes_con_clave",
    "examenes_del_docente",
]

LARGO_MAXIMO_DEL_NOMBRE = 80


@dataclass(frozen=True)
class ExamenConClave:
    examen_id: str
    habilitada: bool
    nombre: str = ""


class NombreDeExamenInvalido(ValueError):
    """El nombre está vacío, es demasiado largo o trae caracteres que no se imprimen."""


class ExamenNoEncontrado(LookupError):
    """El examen no existe o es de otro docente: para quien pregunta, es lo mismo."""


def _nombre_limpio(nombre: str) -> str:
    return " ".join(nombre.split())


def clave_del_nombre(nombre: str) -> str:
    """Cómo se comparan dos nombres: sin espacios de más y sin distinguir mayúsculas, para que
    «Parcial 1» y «parcial  1» sean el mismo examen del docente."""
    return _nombre_limpio(nombre).casefold()


def crear_examen(
    nombre: str, docente: str, en: datetime, registro: RegistroDeExamenes
) -> tuple[Examen, bool]:
    """El examen del docente con ese nombre: uno nuevo con su identificador (y `True`), o el que ya
    tenía con ese nombre (y `False`). Lanza `NombreDeExamenInvalido`."""
    limpio = _nombre_limpio(nombre)
    if not limpio:
        raise NombreDeExamenInvalido("Escriba el nombre del examen.")
    if len(limpio) > LARGO_MAXIMO_DEL_NOMBRE:
        raise NombreDeExamenInvalido(
            f"El nombre del examen puede tener hasta {LARGO_MAXIMO_DEL_NOMBRE} caracteres."
        )
    if not limpio.isprintable():
        raise NombreDeExamenInvalido("El nombre del examen trae caracteres que no se pueden leer.")
    return registro.crear(limpio, clave_del_nombre(limpio), docente, en)


def examen_del_docente(examen_id: str, docente: str, registro: RegistroDeExamenes) -> Examen:
    """El examen, si es del docente. Si no existe o es de otro, `ExamenNoEncontrado`."""
    examen = registro.examen(examen_id)
    if examen is None or examen.docente != docente:
        raise ExamenNoEncontrado(f"{examen_id} no es un examen suyo.")
    return examen


def examenes_del_docente(
    docente: str, registro: RegistroDeExamenes, claves: FuenteDeClaves
) -> tuple[ExamenConClave, ...]:
    """Los exámenes del docente que ya tienen clave, ordenados por identificador (el más antiguo
    primero). Uno creado cuya clave no se llegó a guardar no aparece: no se le pueden subir hojas
    con nota, y la pantalla de la clave lo vuelve a encontrar por su nombre."""
    lista = []
    for examen in registro.examenes_del_docente(docente):
        try:
            clave = claves.clave_del_examen(examen.examen_id)
        except ValueError:
            # Una clave mal escrita no se ofrece, como en `examenes_con_clave`.
            continue
        if clave is not None:
            lista.append(
                ExamenConClave(
                    examen.examen_id, habilitada=clave.habilitacion is not None, nombre=examen.nombre
                )
            )
    return tuple(lista)


def examenes_con_clave(catalogo: CatalogoDeClaves) -> tuple[ExamenConClave, ...]:
    """Todas las claves registradas, de cualquier docente, ordenadas por identificador. La ruta ya
    no la usa (publica solo las del docente); queda para las herramientas y la adopción."""
    return tuple(
        sorted(
            (
                ExamenConClave(
                    clave.examen_id,
                    habilitada=clave.habilitacion is not None,
                    nombre=clave.examen_id,
                )
                for clave in catalogo.claves_registradas()
            ),
            key=lambda examen: examen.examen_id,
        )
    )


def adoptar_examenes_sin_dueno(
    mencionados: Iterable[str],
    docente: str,
    en: datetime,
    registro: RegistroDeExamenes,
    duenos_probables: Mapping[str, str] | None = None,
) -> tuple[str, ...]:
    """Registra cada examen de `mencionados` que todavía no tiene dueño y devuelve los que adoptó,
    ordenados. Va a nombre de su dueño probable si se conoce (quien habilitó su clave, que desde
    ADR-0026 queda guardado con el correo de la sesión) y si no, a nombre de `docente`. Los que ya
    tienen dueño no se tocan, así que se puede llamar las veces que sea."""
    probables = duenos_probables or {}
    return tuple(
        examen_id
        for examen_id in sorted(set(mencionados))
        if examen_id and registro.adoptar(examen_id, probables.get(examen_id, docente), en)
    )
