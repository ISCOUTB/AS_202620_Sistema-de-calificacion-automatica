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

**Por qué hay puerto.** Igual que el almacén, y por la misma razón (arc42 §4.1, riesgo R-06):
cuando el ADR de persistencia definitiva elija un medio, cambia el adaptador y no cambian ni
`ingesta` ni el modelo. `BitacoraEnDisco` es un adaptador honesto para un solo proceso, no una
bitácora distribuida.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from infraestructura.modelo import EntradaDeBitacora

__all__ = ["BitacoraDeRecepcion", "BitacoraEnDisco", "BitacoraEnMemoria"]


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
                )
            elif hecho.get("hecho") == "encolada":
                confirmadas.add(hecho["trabajo_id"])

        return [e for id_, e in recibidas.items() if id_ not in confirmadas]


class BitacoraEnMemoria:
    """Adaptador para pruebas y para el arranque en desarrollo. No sobrevive al proceso, y por
    eso no sirve para lo que la bitácora existe; se ofrece para que una prueba que no mide
    durabilidad no tenga que tocar disco."""

    def __init__(self) -> None:
        self.recibidas: dict[str, EntradaDeBitacora] = {}
        self.confirmadas: set[str] = set()

    def registrar(self, entrada: EntradaDeBitacora) -> None:
        self.recibidas[entrada.trabajo_id] = entrada

    def confirmar_encolada(self, trabajo_id: str) -> None:
        self.confirmadas.add(trabajo_id)

    def pendientes(self) -> list[EntradaDeBitacora]:
        return [e for i, e in self.recibidas.items() if i not in self.confirmadas]
