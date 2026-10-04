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
#
# 1.1.0 agrega la ruta de distractores (RF-11). Sube la version menor y no la mayor porque solo
# agrega: las dos rutas de 1.0.0 y sus esquemas siguen identicos, asi que nadie que ya consuma la
# API tiene que cambiar nada.
VERSION_DEL_CONTRATO = "1.1.0"

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

    nombre_archivo: str = Field(description="Nombre con el que el docente envio el archivo.")
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


class SolicitudDeDistractores(BaseModel):
    """Lo que el profesor envia para pedir distractores diagnosticos (RF-11).

    Son los mismos tres campos de `PreguntaParaDistractores` y ninguno mas: es lo unico que puede
    llegar al proveedor de LLM, y por eso RNF-13 se cumple desde la puerta. Los limites de largo
    acotan lo que cuesta cada solicitud en tokens."""

    enunciado: str = Field(
        min_length=1, max_length=1000, description="Enunciado de la pregunta, en texto plano."
    )
    respuesta_correcta: str = Field(
        min_length=1, max_length=300, description="La respuesta correcta de la clave."
    )
    cantidad: int = Field(
        default=3, ge=1, le=5, description="Cuantos distractores se piden. Entre 1 y 5."
    )


class DistractorEnRespuesta(BaseModel):
    """Una opcion incorrecta propuesta, con el error de procedimiento que representa. Es una
    propuesta: no entra a ningun examen hasta que el profesor la acepte y lo habilite (RF-07)."""

    model_config = ConfigDict(from_attributes=True)

    expresion: str = Field(description="La opcion incorrecta, en texto plano.")
    error: str = Field(description="El error de procedimiento que la produce.")


class DescartadoEnRespuesta(BaseModel):
    """Una propuesta del modelo que no llego al profesor, con el motivo."""

    model_config = ConfigDict(from_attributes=True)

    expresion: str = Field(description="Lo que propuso el modelo.")
    motivo: str = Field(description="Por que no se muestra, redactado para el profesor.")


class RespuestaDeDistractores(BaseModel):
    """Lo que responde la solicitud de distractores: lo que paso la regla y lo que no.

    Ninguna propuesta de `distractores` repite la respuesta correcta (medida M1 de EC-08). Las
    descartadas se devuelven con su motivo para que el profesor sepa por que recibio menos de lo
    que pidio."""

    distractores: list[DistractorEnRespuesta]
    descartados: list[DescartadoEnRespuesta]


class ProveedorNoDisponibleEnRespuesta(BaseModel):
    """Cuerpo del 503: el proveedor no esta configurado, no respondio a tiempo o fallo.

    Usa el campo `detail` de los errores de FastAPI para que un cliente lea igual este error y
    los demas."""

    detail: str = Field(description="Que paso, redactado para el profesor.")
