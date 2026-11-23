"""Bitácora de recepción: el registro que hace recuperable lo que ya se almacenó.

**Qué problema resuelve.** `ingesta.recibir_lote` almacena la hoja y después encola su
procesamiento, y entre esas dos operaciones no hay transacción. Si la cola falla en medio de un
lote, las hojas ya almacenadas quedan huérfanas: nadie sabe que existen, el docente no recibe
reporte de ellas y volver a subirlas duplica las que sí alcanzaron a encolarse. Eso rompe la
promesa de EC-07 —0 % de pérdida silenciosa— y quedó medido antes de escribir este archivo
(ver `docs/evidencia/medicion-ec07.md`).

**Por qué una bitácora y no una transacción.** El almacén de imágenes y la cola son dos
sistemas distintos; no hay transacción que los abarque sin introducir un coordinador. Un
registro propio, escrito **antes** de encolar y confirmado **después**, deja el sistema en un
estado que siempre se puede leer y reparar: toda entrada sin confirmación es una hoja
almacenada cuyo procesamiento quedó pendiente. La decisión y sus alternativas están en
[ADR-0006](../../docs/adr/0006-registrar-la-recepcion-en-una-bitacora-antes-de-encolar.md).

**Por qué es de solo agregado.** No se reescribe ninguna línea: confirmar una entrada es
agregar otra que la referencia. Una escritura que sobrescribe puede dejar el archivo a medias
si el proceso muere en el momento equivocado, que es justamente el momento del que esta
bitácora tiene que sobrevivir.

**Las líneas llevan la identidad de la hoja** desde
[ADR-0018](../../docs/adr/0018-dar-a-la-hoja-una-identidad-propia-y-derivar-su-estado-de-la-bitacora.md),
que además declara esta bitácora como la fuente de verdad del estado de cada hoja: cualquier
otra copia (la respuesta al docente, una tabla futura, una caché) se deriva de lo que dice aquí.
Las líneas escritas antes no la traen, y se leen con el `trabajo_id` como identidad de la hoja,
que es lo que era entonces.

**Por qué hay puerto.** Igual que el almacén, y por la misma razón (arc42 §4.1, riesgo R-06):
cuando el ADR de persistencia definitiva elija un medio, cambia el adaptador y no cambian ni
`ingesta` ni el modelo. `BitacoraEnDisco` es un adaptador honesto para un solo proceso, no una
bitácora distribuida.

**Quien solo la lee lo hace por otro puerto**, `LectorDeRecepciones`, como el registro de
resultados: `dashboard` necesita saber con qué nombre y a qué hora llegó cada hoja para que el
profesor la reconozca en la revisión, y no tiene por qué poder registrar ni confirmar nada.
"""

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from infraestructura.modelo import EntradaDeBitacora

__all__ = [
    "BitacoraDeRecepcion",
    "LectorDeRecepciones",
    "RecepcionDeHoja",
    "BitacoraEnDisco",
    "BitacoraEnMemoria",
]


@dataclass(frozen=True)
class RecepcionDeHoja:
    """Cómo llegó una hoja: el nombre con que el docente subió el archivo y cuándo quedó
    registrada. El nombre puede ser el del estudiante si el docente los nombra así (arc42 §8.7).
    `recibida_en` es None solo si la línea no trae una fecha legible."""

    nombre_archivo: str
    recibida_en: datetime | None


class BitacoraDeRecepcion(Protocol):
    """El puerto. `ingesta` depende de esta forma, no de dónde se escriba el registro."""

    def registrar(self, entrada: EntradaDeBitacora) -> None:
        """Deja constancia de que la hoja está almacenada y su encolado va a intentarse."""
        ...

    def confirmar_encolada(self, trabajo_id: str) -> None:
        """Deja constancia de que el trabajo sí llegó a la cola."""
        ...

    def pendientes(self) -> list[EntradaDeBitacora]:
        """Entradas registradas y nunca confirmadas: hojas almacenadas sin encolar."""
        ...

    def examenes_mencionados(self) -> set[str]:
        """Cada `examen_id` que aparece en la bitácora (la adopción de ADR-0028)."""
        ...


class LectorDeRecepciones(Protocol):
    """El puerto de solo lectura. `dashboard` depende de esta forma."""

    def recepciones_del_examen(self, examen_id: str) -> dict[str, RecepcionDeHoja]:
        """Cómo llegó cada hoja del examen, por `hoja_id`. Si una hoja tiene más de una línea
        `recibida`, vale la primera: es cuando llegó."""
        ...


class BitacoraEnDisco:
    """Adaptador de solo agregado sobre un archivo JSON Lines.

    Cada línea es un hecho, no un estado: `recibida` cuando la hoja quedó almacenada,
    `encolada` cuando su trabajo llegó a la cola. El estado se obtiene releyendo el archivo, que
    es lo que hace `pendientes`.

    Cada línea se descarga a disco con `fsync` antes de devolver el control. Es lo que cuesta
    la durabilidad y se paga a propósito: una bitácora que vive en la caché del sistema
    operativo no sobrevive a la caída de la que tiene que dejar constancia."""

    def __init__(self, ruta: Path) -> None:
        self.ruta = Path(ruta)
        self.ruta.parent.mkdir(parents=True, exist_ok=True)

    def _agregar(self, hecho: dict) -> None:
        linea = json.dumps(hecho, ensure_ascii=False) + "\n"
        with open(self.ruta, "a", encoding="utf-8") as archivo:
            archivo.write(linea)
            archivo.flush()
            os.fsync(archivo.fileno())

    def registrar(self, entrada: EntradaDeBitacora) -> None:
        self._agregar(
            {
                "hecho": "recibida",
                "hoja_id": entrada.hoja_id,
                "trabajo_id": entrada.trabajo_id,
                "examen_id": entrada.examen_id,
                "referencia": entrada.referencia,
                "nombre_archivo": entrada.nombre_archivo,
                "momento": datetime.now(timezone.utc).isoformat(),
            }
        )

    def confirmar_encolada(self, trabajo_id: str) -> None:
        self._agregar(
            {
                "hecho": "encolada",
                "trabajo_id": trabajo_id,
                "momento": datetime.now(timezone.utc).isoformat(),
            }
        )

    def pendientes(self) -> list[EntradaDeBitacora]:
        if not self.ruta.exists():
            return []

        recibidas: dict[str, EntradaDeBitacora] = {}
        confirmadas: set[str] = set()

        for linea in self.ruta.read_text(encoding="utf-8").splitlines():
            if not linea.strip():
                continue
            try:
                hecho = json.loads(linea)
            except json.JSONDecodeError:
                # Una línea truncada solo puede ser la última, y significa que el proceso
                # murió escribiéndola. Se ignora: la hoja que describe no llegó a encolarse,
                # y el archivo que sí quedó en el almacén se detecta al conciliar contra él.
                continue

            if hecho.get("hecho") == "recibida":
                recibidas[hecho["trabajo_id"]] = EntradaDeBitacora(
                    trabajo_id=hecho["trabajo_id"],
                    examen_id=hecho["examen_id"],
                    referencia=hecho["referencia"],
                    nombre_archivo=hecho["nombre_archivo"],
                    # Una línea anterior a ADR-0018 no trae `hoja_id`: entonces el trabajo era
                    # la hoja, así que su identificador es el de la hoja. No se inventa uno
                    # nuevo, que dejaría a la misma hoja con dos identidades.
                    hoja_id=hecho.get("hoja_id", hecho["trabajo_id"]),
                )
            elif hecho.get("hecho") == "encolada":
                confirmadas.add(hecho["trabajo_id"])

        return [e for id_, e in recibidas.items() if id_ not in confirmadas]

    def examenes_mencionados(self) -> set[str]:
        """Cada `examen_id` que aparece en una línea `recibida`: lo usa la adopción de los
        exámenes anteriores a ADR-0028. Una línea truncada se salta."""
        if not self.ruta.exists():
            return set()
        examenes: set[str] = set()
        with open(self.ruta, encoding="utf-8", errors="replace") as archivo:
            for linea in archivo:
                try:
                    hecho = json.loads(linea)
                except ValueError:
                    continue
                if isinstance(hecho, dict) and isinstance(hecho.get("examen_id"), str):
                    examenes.add(hecho["examen_id"])
        return examenes

    def recepciones_del_examen(self, examen_id: str) -> dict[str, RecepcionDeHoja]:
        """Recorre el archivo y solo decodifica las líneas que nombran al examen, como
        `ResultadosEnDisco.hechos_del_examen`. Una línea truncada se salta."""
        if not self.ruta.exists():
            return {}
        nombre = json.dumps(examen_id, ensure_ascii=False)
        recepciones: dict[str, RecepcionDeHoja] = {}
        with open(self.ruta, encoding="utf-8", errors="replace") as archivo:
            for linea in archivo:
                if nombre not in linea:
                    continue
                try:
                    hecho = json.loads(linea)
                except ValueError:
                    continue
                if (
                    not isinstance(hecho, dict)
                    or hecho.get("hecho") != "recibida"
                    or hecho.get("examen_id") != examen_id
                ):
                    continue
                # Como en `pendientes`: antes de ADR-0018, el trabajo era la hoja.
                hoja_id = hecho.get("hoja_id", hecho.get("trabajo_id"))
                if not isinstance(hoja_id, str) or hoja_id in recepciones:
                    continue
                recepciones[hoja_id] = RecepcionDeHoja(
                    nombre_archivo=str(hecho.get("nombre_archivo", "")),
                    recibida_en=_instante(hecho.get("momento")),
                )
        return recepciones


def _instante(valor: object) -> datetime | None:
    """La fecha ISO 8601 de una línea, o None si falta o no se puede leer."""
    if not isinstance(valor, str):
        return None
    try:
        return datetime.fromisoformat(valor)
    except ValueError:
        return None


class BitacoraEnMemoria:
    """Adaptador para pruebas y para el arranque en desarrollo. No sobrevive al proceso, y por
    eso no sirve para lo que la bitácora existe; se ofrece para que una prueba que no mide
    durabilidad no tenga que tocar disco."""

    def __init__(self) -> None:
        self.recibidas: dict[str, EntradaDeBitacora] = {}
        self.confirmadas: set[str] = set()
        self.momentos: dict[str, datetime] = {}

    def registrar(self, entrada: EntradaDeBitacora) -> None:
        self.recibidas[entrada.trabajo_id] = entrada
        self.momentos.setdefault(entrada.trabajo_id, datetime.now(timezone.utc))

    def confirmar_encolada(self, trabajo_id: str) -> None:
        self.confirmadas.add(trabajo_id)

    def pendientes(self) -> list[EntradaDeBitacora]:
        return [e for i, e in self.recibidas.items() if i not in self.confirmadas]

    def examenes_mencionados(self) -> set[str]:
        return {entrada.examen_id for entrada in self.recibidas.values()}

    def recepciones_del_examen(self, examen_id: str) -> dict[str, RecepcionDeHoja]:
        recepciones: dict[str, RecepcionDeHoja] = {}
        for trabajo_id, entrada in self.recibidas.items():
            if entrada.examen_id == examen_id and entrada.hoja_id not in recepciones:
                recepciones[entrada.hoja_id] = RecepcionDeHoja(
                    entrada.nombre_archivo, self.momentos.get(trabajo_id)
                )
        return recepciones
