"""Adaptador hacia el proveedor de LLM: la capa anticorrupción de la relación 5 del mapa de
contextos (arc42 §8.1), del lado de afuera del puerto `GeneradorDeDistractores`.

Habla el protocolo de chat de OpenAI, que es el que exponen Groq, Gemini y OpenRouter: cambiar
de proveedor es cambiar la URL base, el modelo y la clave (ADR-0013), no este archivo.
Traduce en las dos direcciones y nada más: la pregunta del dominio a una solicitud, y el JSON
del modelo a `DistractorPropuesto`. El formato del proveedor no sale de aquí.

Qué hace cuando el proveedor falla (ADR-0013)
---------------------------------------------
Espera como máximo `TIEMPO_DE_ESPERA_SEGUNDOS` y **no reintenta**: reintentar duplicaría la cuota
gastada y la espera del profesor, y es él quien decide si vuelve a pedir. Cualquier falla, sea
tiempo agotado, cuota agotada, clave rechazada o una respuesta que no se puede leer, sale como
`ProveedorNoDisponible` con un motivo para el profesor. Nada de esto toca la calificación: el LLM
solo participa en la autoría (ADR-0005).

Qué registra
------------
Cada solicitud deja un evento JSON: `distractores_propuestos`, con la duración y los tokens, o
`proveedor_no_disponible`, con el motivo y la duración. Es la métrica de EC-08, como
`lote_confirmado` lo es de EC-07.

Usa `httpx`, que ya es dependencia directa del backend (`requirements.in`): este archivo no
agrega ninguna.
"""

import json
import logging
import time
from typing import Any

import httpx

from autoria.distractores import (
    DistractorPropuesto,
    PreguntaParaDistractores,
    ProveedorNoDisponible,
)

__all__ = ["GeneradorCompatibleConOpenAI", "TIEMPO_DE_ESPERA_SEGUNDOS"]

logger = logging.getLogger("autoria")

TIEMPO_DE_ESPERA_SEGUNDOS = 20.0

INSTRUCCIONES_DEL_SISTEMA = (
    "Ayudas a un profesor de cálculo diferencial a construir preguntas de opción múltiple. "
    "Respondes solo con JSON."
)

# Todo lo que se le dice al modelo sobre la pregunta sale de esta plantilla y de los tres campos
# de `PreguntaParaDistractores`. Por eso RNF-13 se puede probar: no hay otro lugar por donde un
# dato del curso pudiera colarse en la solicitud.
MENSAJE_PARA_EL_MODELO = (
    "Pregunta: {enunciado}\n"
    "Respuesta correcta: {respuesta_correcta}\n\n"
    "Propón {cantidad} distractores diagnósticos: opciones incorrectas que correspondan, cada "
    "una, a un error de procedimiento identificable que un estudiante podría cometer. Ninguna "
    "puede ser equivalente a la respuesta correcta. Escribe las expresiones en texto plano, como "
    "x·cos(x) o e^(2x). Responde solo con un objeto JSON de la forma "
    '{{"distractores": [{{"expresion": "...", "error": "..."}}]}}.'
)


class GeneradorCompatibleConOpenAI:
    """Implementa `GeneradorDeDistractores` sobre un endpoint `/chat/completions`.

    `transporte` existe para las pruebas: con `httpx.MockTransport` se ejerce todo el adaptador
    sin red. En operación se deja en `None` y httpx usa su transporte normal."""

    def __init__(
        self,
        url_base: str,
        modelo: str,
        clave: str,
        tiempo_de_espera: float = TIEMPO_DE_ESPERA_SEGUNDOS,
        transporte: httpx.BaseTransport | None = None,
    ) -> None:
        self._url = url_base.rstrip("/") + "/chat/completions"
        self._modelo = modelo
        self._clave = clave
        self._tiempo_de_espera = tiempo_de_espera
        self._transporte = transporte

    def proponer(self, pregunta: PreguntaParaDistractores) -> list[DistractorPropuesto]:
        inicio = time.perf_counter()
        try:
            datos = self._pedir(pregunta)
            propuestas = _leer_propuestas(datos)
        except ProveedorNoDisponible as falla:
            logger.warning(
                "Proveedor no disponible",
                extra={
                    "evento": "proveedor_no_disponible",
                    "modelo": self._modelo,
                    "motivo": falla.motivo,
                    "duracion_ms": _milisegundos_desde(inicio),
                },
            )
            raise

        uso = datos.get("usage")
        if not isinstance(uso, dict):
            uso = {}
        logger.info(
            "Distractores propuestos",
            extra={
                "evento": "distractores_propuestos",
                "modelo": self._modelo,
                "propuestas_recibidas": len(propuestas),
                "duracion_ms": _milisegundos_desde(inicio),
                "tokens_entrada": uso.get("prompt_tokens"),
                "tokens_salida": uso.get("completion_tokens"),
            },
        )
        return propuestas

    def _pedir(self, pregunta: PreguntaParaDistractores) -> dict[str, Any]:
        cuerpo = {
            "model": self._modelo,
            "messages": [
                {"role": "system", "content": INSTRUCCIONES_DEL_SISTEMA},
                {
                    "role": "user",
                    "content": MENSAJE_PARA_EL_MODELO.format(
                        enunciado=pregunta.enunciado,
                        respuesta_correcta=pregunta.respuesta_correcta,
                        cantidad=pregunta.cantidad,
                    ),
                },
            ],
            "response_format": {"type": "json_object"},
        }
        try:
            with httpx.Client(
                transport=self._transporte, timeout=self._tiempo_de_espera
            ) as cliente:
                respuesta = cliente.post(
                    self._url,
                    json=cuerpo,
                    headers={"Authorization": f"Bearer {self._clave}"},
                )
        except httpx.TimeoutException as error:
            raise ProveedorNoDisponible(
                f"El proveedor no respondió en {self._tiempo_de_espera:g} s. "
                "Puede volver a pedirlo o escribir los distractores a mano."
            ) from error
        except httpx.HTTPError as error:
            raise ProveedorNoDisponible(
                "No se pudo contactar al proveedor. "
                "Puede volver a pedirlo más tarde o escribir los distractores a mano."
            ) from error

        if respuesta.status_code == 429:
            raise ProveedorNoDisponible(
                "Se agotó la cuota gratuita del proveedor por ahora. "
                "Puede volver a pedirlo en unos minutos o escribir los distractores a mano."
            )
        if respuesta.status_code in (401, 403):
            raise ProveedorNoDisponible("El proveedor rechazó la clave configurada.")
        if respuesta.status_code != 200:
            raise ProveedorNoDisponible(
                f"El proveedor respondió con el código {respuesta.status_code}."
            )
        try:
            datos = respuesta.json()
        except ValueError as error:
            raise ProveedorNoDisponible("El proveedor devolvió una respuesta ilegible.") from error
        if not isinstance(datos, dict):
            raise ProveedorNoDisponible("El proveedor devolvió una respuesta ilegible.")
        return datos


def _leer_propuestas(datos: dict[str, Any]) -> list[DistractorPropuesto]:
    """Traduce la respuesta del modelo a propuestas del dominio, sin juzgarlas.

    Solo exige la forma: un objeto con la lista `distractores`. Que una propuesta venga vacía,
    sin etiqueta o repetida no es asunto del adaptador, sino de la regla de
    `autoria/distractores.py`, que la descarta con su motivo."""
    try:
        contenido = datos["choices"][0]["message"]["content"]
        lista = json.loads(contenido)["distractores"]
    except (KeyError, IndexError, TypeError, ValueError) as error:
        raise ProveedorNoDisponible(
            "El proveedor devolvió algo que no tiene la forma de una lista de distractores."
        ) from error
    if not isinstance(lista, list) or not all(isinstance(item, dict) for item in lista):
        raise ProveedorNoDisponible(
            "El proveedor devolvió algo que no tiene la forma de una lista de distractores."
        )
    return [
        DistractorPropuesto(
            expresion=str(item.get("expresion") or "").strip(),
            error=str(item.get("error") or "").strip(),
        )
        for item in lista
    ]


def _milisegundos_desde(inicio: float) -> float:
    return round((time.perf_counter() - inicio) * 1000, 1)
