"""Esquemas de la interfaz HTTP: la forma exacta del cuerpo que la API promete devolver.

Viven en `api` y no en `infraestructura/modelo.py` a proposito. Las dataclasses del modelo son
el vocabulario del dominio y solo dependen de la biblioteca estandar; estas clases son el
contrato de una puerta concreta, saben de Pydantic y de OpenAPI, y cambian cuando cambia la API
aunque el dominio no se mueva. Declararlas alla obligaria a `infraestructura` a importar
Pydantic y romperia su linea `Importa: ninguno`, que es lo que verifica `test_fronteras.py`.

Lo que gana el contrato al declararlas: sin `response_model`, `/openapi.json` describe cada
respuesta como un objeto vacio, porque las dos rutas estaban anotadas `-> dict`. Con estas
clases el documento dice campo por campo que devuelve cada ruta y de que tipo, que es lo que un
consumidor necesita para generar su cliente y lo que la prueba de contrato compara.
"""

from datetime import datetime
from typing import Literal, get_args

from pydantic import BaseModel, ConfigDict, Field

from infraestructura.modelo import ENCOLADA, PENDIENTE_DE_ENCOLAR

# Version del contrato, no del proyecto. Se declara aqui, junto a los esquemas que versiona,
# para que cambiar uno sin tocar la otra sea visible en el mismo diff.
VERSION_DEL_CONTRATO = "1.0.0"

EstadoDeHoja = Literal["encolada", "pendiente_de_encolar"]

# `Literal` exige literales, asi que el tipo de arriba no puede construirse desde las constantes
# del dominio. Se comprueba aqui que no se separen: si alguien renombra un estado en
# `modelo.py`, esto falla al importar en vez de publicar un contrato que miente sobre los
# valores que el docente va a recibir.
if set(get_args(EstadoDeHoja)) != {ENCOLADA, PENDIENTE_DE_ENCOLAR}:
    raise RuntimeError(
        "Los estados declarados en el contrato HTTP no coinciden con los de "
        "infraestructura/modelo.py. Actualiza EstadoDeHoja y la version del contrato."
    )


class RespuestaDeSalud(BaseModel):
    """Lo que devuelve la sonda de vida. Hoy tiene un unico valor posible y el esquema lo dice
    asi: declararlo como texto libre prometeria una variedad que la ruta no tiene."""

    status: Literal["ok"] = Field(description="Unico valor posible mientras la API responde.")


class HojaAceptadaEnRespuesta(BaseModel):
    """Una hoja que paso la validacion y quedo almacenada.

    No lleva `examen_id` porque ya viaja una sola vez en la raiz de la respuesta, y repetirlo
    por hoja invitaria a un consumidor a suponer que un lote puede mezclar examenes. La
    dataclass del dominio si lo trae, y `model_validate` lo descarta al construir esta."""

    model_config = ConfigDict(from_attributes=True)

     archivo: str = Field(description="Nombre con el que el docente envio el archivo.")
    referencia: str = Field(
        description=(
            "Ubicacion que devolvio el almacen. Opaca a proposito: el consumidor no debe "
            "suponer que es una ruta de disco, porque el ADR de persistencia (R-06) puede "
            "convertirla en una clave de objeto sin que este contrato cambie."
        )
    )
    trabajo_id: str = Field(
        description=(
            "Identificador del trabajo de procesamiento. Se acuna antes de tocar la cola, asi "
            "que existe tambien cuando el estado es pendiente_de_encolar."
        )
    )
    recibida_en: datetime = Field(description="Momento en que el sistema acepto la hoja.")
    estado: EstadoDeHoja = Field(
        description=(
            "encolada: su trabajo llego a la cola. pendiente_de_encolar: la hoja esta "
            "almacenada y registrada en la bitacora, pero su trabajo no llego a la cola y el "
            "sistema debe reintentarlo (ADR-0006)."
        )
    )


class ArchivoRechazadoEnRespuesta(BaseModel):
    """Un archivo que no se admitio, con el motivo en texto legible para el docente.

    El motivo es obligatorio: EC-07 exige que ningun archivo desaparezca sin dejar traza, y un
    rechazo sin explicacion es indistinguible de una perdida desde el lado del usuario."""

    model_config = ConfigDict(from_attributes=True)

    nombre_archivo: str = Field(description="Nombre con el que el docente envio el archivo.")
    motivo: str = Field(description="Por que no se admitio, redactado para el docente.")


class RespuestaDeCarga(BaseModel):
    """Lo que responde la carga de hojas: que entro y que no.

    La invariante que promete es la de EC-07: `total_procesados` es igual al numero de
    elementos de `aceptadas` mas los de `rechazados`, y ese numero es el de archivos que el
    docente envio. Ningun archivo se pierde en silencio."""

    examen_id: str = Field(description="Examen al que se cargaron las hojas.")
    total_procesados: int = Field(
        description="Aceptadas mas rechazados. Igual al numero de archivos enviados (EC-07)."
    )
    aceptadas: list[HojaAceptadaEnRespuesta]
    rechazados: list[ArchivoRechazadoEnRespuesta]
