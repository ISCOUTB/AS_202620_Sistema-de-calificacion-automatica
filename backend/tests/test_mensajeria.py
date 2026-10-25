"""Prueba 17: el contrato del mensaje de la cola de trabajos (taller de mensajería, ADR-0020).

La operación es real: cada hoja aceptada viaja como un mensaje de la API al worker por la cola de
Redis (ADR-0002). Estas pruebas sostienen el contrato de ese mensaje y su criterio de
compatibilidad: el archivo versionado es el que genera el código; todo mensaje que publica la
recepción lo cumple; quien lee ignora los campos que no conoce y lee los mensajes anteriores al
contrato; y una versión que no conoce no se lee.

La de lo que publica la recepción corre contra el Redis del CI (o el de `docker compose up -d
redis`) y se salta con un mensaje si no hay uno, como `test_encolado.py`.

Validadas provocando la falla: con el archivo del contrato editado a mano, falla la primera; con
`serializar_trabajo` sin el campo `version`, falla la de lo que publica la recepción; con `leer_trabajo`
exigiendo `hoja_id`, falla la de los mensajes anteriores; aceptando cualquier versión, falla la de
la versión desconocida.
"""

import json
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest

from herramientas.exportar_contrato import (
    RUTA_CONTRATO_DEL_TRABAJO,
    documento_del_trabajo,
    serializar,
)
from infraestructura.almacen import AlmacenEnDisco
from infraestructura.bitacora import BitacoraEnMemoria
from infraestructura.cola import (
    ESQUEMA_DEL_TRABAJO,
    VERSION_DEL_TRABAJO,
    MensajeInvalido,
    Trabajo,
    leer_trabajo,
    serializar_trabajo,
)
from infraestructura.modelo import ArchivoCargado
from ingesta import recibir_lote

JPG = b"\xff\xd8\xff" + b"\x00" * 32
EXAMEN = "CALC-2026-01"


# --- Utilidades --------------------------------------------------------------------------------


def _cumple_el_esquema(valor, esquema: dict, ruta: str = "$") -> list[str]:
    """Un validador mínimo de JSON Schema para lo que usa el contrato del trabajo: `type`,
    `required`, `properties`, `const` y `minimum`. Sin dependencias nuevas (jsonschema no está en
    el lock), y suficiente para comprobar que un mensaje real cumple el archivo publicado."""
    errores: list[str] = []
    tipos = {"object": dict, "string": str, "integer": int}
    if "const" in esquema and valor != esquema["const"]:
        errores.append(f"{ruta}: vale {valor!r} y debe valer {esquema['const']!r}")
    tipo = esquema.get("type")
    if tipo and not isinstance(valor, tipos[tipo]):
        return errores + [f"{ruta}: no es {tipo}"]
    if "minimum" in esquema and valor < esquema["minimum"]:
        errores.append(f"{ruta}: es menor que {esquema['minimum']}")
    if tipo == "object":
        for campo in esquema.get("required", []):
            if campo not in valor:
                errores.append(f"{ruta}: falta {campo}")
        for campo, subesquema in esquema.get("properties", {}).items():
            if campo in valor:
                errores += _cumple_el_esquema(valor[campo], subesquema, f"{ruta}.{campo}")
    return errores


@pytest.fixture
def cola(cliente) -> Iterator[str]:
    nombre = f"prueba-mensajeria-{uuid.uuid4()}"
    yield nombre
    cliente.delete(nombre)


def _publicar_una_hoja(cliente, cola: str, raiz: Path) -> Trabajo:
    """Publica como lo hace la API: por `recibir_lote`, con la hoja guardada en el almacén."""
    recibir_lote(
        EXAMEN, [ArchivoCargado("h1.jpg", JPG)], AlmacenEnDisco(raiz), cliente, cola,
        BitacoraEnMemoria(),
    )
    return leer_trabajo(cliente.lindex(cola, -1))


# --- El contrato del mensaje -------------------------------------------------------------------


def test_el_contrato_versionado_del_mensaje_es_el_que_genera_el_codigo():
    """Como la prueba de contrato de la API: el archivo de `docs/contrato/` no se edita a mano."""
    assert RUTA_CONTRATO_DEL_TRABAJO.exists(), (
        "Falta el contrato del mensaje. Se genera con 'python -m herramientas.exportar_contrato'."
    )
    assert RUTA_CONTRATO_DEL_TRABAJO.read_text(encoding="utf-8") == serializar(
        documento_del_trabajo()
    )
    assert RUTA_CONTRATO_DEL_TRABAJO.name == f"trabajo-v{VERSION_DEL_TRABAJO}.schema.json"


def test_todo_mensaje_que_publica_la_recepcion_cumple_el_contrato(cliente, cola, tmp_path):
    _publicar_una_hoja(cliente, cola, tmp_path)

    [crudo] = cliente.lrange(cola, 0, -1)
    publicado = json.loads(RUTA_CONTRATO_DEL_TRABAJO.read_text(encoding="utf-8"))

    assert _cumple_el_esquema(json.loads(crudo), publicado) == []


def test_quien_lee_ignora_lo_que_no_conoce_y_lee_los_mensajes_anteriores_al_contrato():
    """Compatibilidad hacia adelante: un productor más nuevo puede agregar campos. Y hacia atrás:
    un mensaje sin versión, publicado antes del taller, se lee como versión 1 y su `id` hace de
    hoja si no trae `hoja_id` (la regla de ADR-0018)."""
    con_un_campo_nuevo = json.loads(serializar_trabajo(Trabajo(
        id="t-1", payload={"hoja_id": "h-1", "referencia": "r", "examen_id": "e",
                           "nombre_archivo": "n", "prioridad": "alta"},
    )))
    con_un_campo_nuevo["origen"] = "api-v2"
    anterior = {"id": "t-2", "payload": {"referencia": "r", "examen_id": "e",
                                         "nombre_archivo": "n"}}

    nuevo = leer_trabajo(json.dumps(con_un_campo_nuevo))
    viejo = leer_trabajo(json.dumps(anterior))

    assert nuevo.payload["hoja_id"] == "h-1"
    assert (viejo.version, viejo.intento, viejo.payload["hoja_id"]) == (1, 1, "t-2")


@pytest.mark.parametrize(
    "texto",
    [
        json.dumps({"id": "t-1", "version": 2, "payload": {"referencia": "r"}}),
        json.dumps({"version": 1, "payload": {"referencia": "r"}}),
        "esto no es JSON",
    ],
    ids=["version-desconocida", "sin-id", "no-es-json"],
)
def test_un_mensaje_fuera_del_contrato_no_se_lee(texto):
    with pytest.raises(MensajeInvalido):
        leer_trabajo(texto)


def test_el_esquema_del_codigo_exige_los_campos_que_lee_el_consumidor():
    """`leer_trabajo` necesita `id`, `payload` y la `referencia`; el contrato publicado no puede
    exigir menos que eso, o un productor que lo cumpla podría mandar algo que no se lee."""
    assert {"id", "payload"} <= set(ESQUEMA_DEL_TRABAJO["required"])
    assert "referencia" in ESQUEMA_DEL_TRABAJO["properties"]["payload"]["required"]
