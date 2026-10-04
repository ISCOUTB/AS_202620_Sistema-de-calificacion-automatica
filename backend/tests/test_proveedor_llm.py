"""Prueba 10: el adaptador al proveedor de LLM, sin red (RF-11, RNF-13, EC-08, ADR-0013).

Se ejerce el adaptador completo con `httpx.MockTransport`, que responde en lugar del proveedor.
Así se comprueban las dos promesas que no se pueden dejar a la buena fe del modelo:

1. **RNF-13.** La solicitud que sale lleva el modelo, las instrucciones fijas y los tres campos
   de la pregunta, y nada más: ningún dato del curso tiene por dónde colarse.
2. **La degradación de EC-08.** Tiempo agotado, cuota agotada, clave rechazada, error del
   proveedor y respuesta ilegible terminan todos en `ProveedorNoDisponible` con un motivo para
   el profesor, nunca en una excepción que tumbe la ruta.
"""

import json
import logging

import httpx
import pytest

from autoria.distractores import PreguntaParaDistractores, ProveedorNoDisponible
from autoria.proveedor_llm import (
    INSTRUCCIONES_DEL_SISTEMA,
    MENSAJE_PARA_EL_MODELO,
    GeneradorCompatibleConOpenAI,
)
from infraestructura.registro import FormateadorJSON

URL_BASE = "https://proveedor.invalid/openai/v1"
PREGUNTA = PreguntaParaDistractores("Derivada de x·sin(x)", "sin(x) + x·cos(x)", cantidad=3)


def _respuesta_del_modelo(contenido: str, uso: dict | None = None) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "choices": [{"message": {"role": "assistant", "content": contenido}}],
            "usage": uso or {"prompt_tokens": 196, "completion_tokens": 637},
        },
    )


def _evento(caplog: pytest.LogCaptureFixture, nombre: str) -> dict:
    """El evento tal como sale al registro: pasa por el formateador real, así que la prueba
    también falla si deja de ser JSON."""
    [registro] = [r for r in caplog.records if getattr(r, "evento", None) == nombre]
    return json.loads(FormateadorJSON().format(registro))


def _generador(manejador) -> GeneradorCompatibleConOpenAI:
    return GeneradorCompatibleConOpenAI(
        URL_BASE, "modelo-de-prueba", "clave-de-prueba",
        tiempo_de_espera=1.0, transporte=httpx.MockTransport(manejador),
    )


def test_la_solicitud_solo_lleva_la_pregunta_y_las_instrucciones_fijas() -> None:
    enviadas: list[httpx.Request] = []

    def manejador(peticion: httpx.Request) -> httpx.Response:
        enviadas.append(peticion)
        return _respuesta_del_modelo('{"distractores": []}')

    _generador(manejador).proponer(PREGUNTA)

    assert len(enviadas) == 1
    peticion = enviadas[0]
    assert str(peticion.url) == f"{URL_BASE}/chat/completions"
    assert peticion.headers["authorization"] == "Bearer clave-de-prueba"
    cuerpo = json.loads(peticion.content)
    assert cuerpo == {
        "model": "modelo-de-prueba",
        "messages": [
            {"role": "system", "content": INSTRUCCIONES_DEL_SISTEMA},
            {
                "role": "user",
                "content": MENSAJE_PARA_EL_MODELO.format(
                    enunciado="Derivada de x·sin(x)",
                    respuesta_correcta="sin(x) + x·cos(x)",
                    cantidad=3,
                ),
            },
        ],
        "response_format": {"type": "json_object"},
    }


def test_traduce_la_respuesta_del_modelo_a_propuestas_del_dominio() -> None:
    contenido = json.dumps({"distractores": [
        {"expresion": "cos(x)", "error": "Se omitió la regla del producto"},
        {"expresion": " x·cos(x) ", "error": None},
    ]})

    propuestas = _generador(lambda _: _respuesta_del_modelo(contenido)).proponer(PREGUNTA)

    assert [(p.expresion, p.error) for p in propuestas] == [
        ("cos(x)", "Se omitió la regla del producto"),
        ("x·cos(x)", ""),
    ]


def test_registra_la_metrica_de_ec08_con_duracion_y_tokens(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger="autoria")

    _generador(lambda _: _respuesta_del_modelo('{"distractores": []}')).proponer(PREGUNTA)

    evento = _evento(caplog, "distractores_propuestos")
    assert evento["tokens_entrada"] == 196
    assert evento["tokens_salida"] == 637
    assert evento["duracion_ms"] >= 0
    assert evento["modelo"] == "modelo-de-prueba"


def _falla_con(manejador) -> str:
    with pytest.raises(ProveedorNoDisponible) as falla:
        _generador(manejador).proponer(PREGUNTA)
    return falla.value.motivo


def test_el_tiempo_agotado_no_tumba_la_solicitud() -> None:
    def manejador(peticion: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("sin respuesta", request=peticion)

    assert "no respondió" in _falla_con(manejador)


def test_sin_conexion_con_el_proveedor() -> None:
    def manejador(peticion: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("conexión rechazada", request=peticion)

    assert "No se pudo contactar" in _falla_con(manejador)


@pytest.mark.parametrize(
    ("codigo", "en_el_motivo"),
    [(429, "cuota"), (401, "clave"), (403, "clave"), (500, "500"), (503, "503")],
)
def test_un_codigo_de_error_del_proveedor_se_explica_al_profesor(
    codigo: int, en_el_motivo: str
) -> None:
    assert en_el_motivo in _falla_con(lambda _: httpx.Response(codigo, json={"error": "x"}))


@pytest.mark.parametrize(
    "respuesta",
    [
        httpx.Response(200, text="no es JSON"),
        httpx.Response(200, json={"choices": []}),
        _respuesta_del_modelo("tampoco es JSON"),
        _respuesta_del_modelo('{"otra_cosa": []}'),
        _respuesta_del_modelo('{"distractores": "cos(x)"}'),
        _respuesta_del_modelo('{"distractores": ["cos(x)"]}'),
    ],
)
def test_una_respuesta_sin_la_forma_esperada_se_reporta_como_ilegible(
    respuesta: httpx.Response,
) -> None:
    motivo = _falla_con(lambda _: respuesta)

    assert "ilegible" in motivo or "forma de una lista" in motivo


def test_la_falla_deja_su_evento_con_el_motivo(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO, logger="autoria")

    _falla_con(lambda _: httpx.Response(429, json={"error": "x"}))

    assert "cuota" in _evento(caplog, "proveedor_no_disponible")["motivo"]
