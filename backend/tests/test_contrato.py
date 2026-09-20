"""Prueba 7: el contrato publicado y la API que corre no se pueden separar.

Un documento OpenAPI versionado sirve de poco si nadie comprueba que sigue describiendo a la
aplicacion. Sin esta prueba, `docs/contrato/openapi.json` seria una promesa que envejece en
silencio: alguien renombra un campo, la API cambia, el documento no, y el consumidor se entera
cuando su cliente se rompe en produccion.

Las tres cosas que verifica, en orden de fuerza
-----------------------------------------------
1. Que el documento versionado es **exactamente** el que genera la aplicacion de hoy. Esta es
   la que atrapa cualquier cambio, compatible o no, y obliga a que todo cambio del contrato sea
   deliberado y quede commiteado junto al codigo que lo produce.
2. Que el contrato sigue prometiendo lo que el sistema depende de prometer: las dos rutas, los
   campos obligatorios de la respuesta de carga, y los dos unicos estados que puede tener una
   hoja. Estas existen para que el fallo diga **que** se rompio y no solo que algo difiere.
3. Que una respuesta real de la API cabe en el esquema publicado, campo por campo. Esta se lee
   desde el archivo versionado y no desde los modelos, asi que no es circular: comprueba que la
   aplicacion honra el documento, no que el documento se parece a si mismo.

Como se ve fallar
-----------------
Cualquier cambio incompatible la pone en rojo. Por ejemplo, renombrar `nombre_archivo` a
`archivo` en `api/esquemas.py`, quitar un campo de `RespuestaDeCarga`, o anadir un tercer valor
a los estados de una hoja. El mensaje de fallo dice que ruta o que esquema difiere, sin volcar
el documento entero.

Si el cambio era intencional, se regenera el contrato y se commitea el diff:

    python -m herramientas.exportar_contrato
"""

import json
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from api.esquemas import VERSION_DEL_CONTRATO
from api.main import app, obtener_almacen, obtener_cliente_cola
from herramientas.exportar_contrato import (
    RUTA_CONTRATO,
    documento_openapi,
    serializar,
)
from infraestructura.almacen import AlmacenEnDisco
from infraestructura.modelo import ENCOLADA, PENDIENTE_DE_ENCOLAR
from tests.test_recepcion import JPG, ColaFalsa

RUTA_CARGA = "/examenes/{examen_id}/hojas"


@pytest.fixture(scope="module")
def contrato_publicado() -> dict:
    """El documento tal como esta versionado en el repositorio.

    Se lee del archivo y no de la aplicacion a proposito: es la copia que ve un consumidor que
    clona el repositorio, y es la que tiene que ser verdad."""
    if not RUTA_CONTRATO.exists():
        raise AssertionError(
            f"No existe {RUTA_CONTRATO}. El contrato se genera con "
            "'python -m herramientas.exportar_contrato' desde backend/."
        )
    return json.loads(RUTA_CONTRATO.read_text(encoding="utf-8"))


@pytest.fixture
def cliente_http(tmp_path) -> Iterator[TestClient]:
    """Cliente contra la app real, con almacen y cola sustituidos, igual que en
    `test_carga_hojas.py`: la prueba de contrato no necesita Redis ni el volumen real."""
    app.dependency_overrides[obtener_almacen] = lambda: AlmacenEnDisco(tmp_path)
    app.dependency_overrides[obtener_cliente_cola] = lambda: ColaFalsa()
    yield TestClient(app)
    app.dependency_overrides.clear()


def _diferencias(publicado: dict, generado: dict) -> list[str]:
    """Compara los dos documentos y describe en texto donde difieren.

    Existe para que el fallo sea legible. Un `assert publicado == generado` volcaria diez mil
    caracteres de JSON y quien lo lea no sabria que cambio; esto nombra la ruta, el metodo o el
    esquema afectado, que es lo que hace falta para decidir si el cambio era intencional."""
    partes: list[str] = []

    if publicado.get("info", {}).get("version") != generado.get("info", {}).get("version"):
        partes.append(
            f"  version: el archivo dice {publicado.get('info', {}).get('version')!r} "
            f"y la aplicacion genera {generado.get('info', {}).get('version')!r}"
        )

    rutas_publicadas = set(publicado.get("paths", {}))
    rutas_generadas = set(generado.get("paths", {}))
    for ruta in sorted(rutas_generadas - rutas_publicadas):
        partes.append(f"  ruta nueva, no esta en el contrato: {ruta}")
    for ruta in sorted(rutas_publicadas - rutas_generadas):
        partes.append(f"  ruta eliminada, sigue en el contrato: {ruta}")
    for ruta in sorted(rutas_publicadas & rutas_generadas):
        if publicado["paths"][ruta] != generado["paths"][ruta]:
            partes.append(f"  ruta cambiada: {ruta}")

    esquemas_publicados = publicado.get("components", {}).get("schemas", {})
    esquemas_generados = generado.get("components", {}).get("schemas", {})
    for nombre in sorted(set(esquemas_generados) - set(esquemas_publicados)):
        partes.append(f"  esquema nuevo, no esta en el contrato: {nombre}")
    for nombre in sorted(set(esquemas_publicados) - set(esquemas_generados)):
        partes.append(f"  esquema eliminado, sigue en el contrato: {nombre}")
    for nombre in sorted(set(esquemas_publicados) & set(esquemas_generados)):
        if esquemas_publicados[nombre] != esquemas_generados[nombre]:
            campos_p = set(esquemas_publicados[nombre].get("properties", {}))
            campos_g = set(esquemas_generados[nombre].get("properties", {}))
            detalle = ""
            if campos_p != campos_g:
                quitados = sorted(campos_p - campos_g)
                puestos = sorted(campos_g - campos_p)
                detalle = f" (campos quitados: {quitados or 'ninguno'}; nuevos: {puestos or 'ninguno'})"
            partes.append(f"  esquema cambiado: {nombre}{detalle}")

    if not partes:
        partes.append("  difieren en algun detalle fuera de rutas y esquemas (info, tags, ...)")
    return partes


def test_el_contrato_versionado_es_el_que_genera_la_aplicacion(contrato_publicado):
    """La prueba fuerte: cualquier cambio del contrato tiene que estar commiteado.

    Compara el texto serializado, no solo los diccionarios, usando la misma funcion que el
    exportador. Asi, si esta prueba pasa, el archivo del repositorio es byte a byte el que
    produce `python -m herramientas.exportar_contrato`, y no hay forma de que el diff quede a
    medias."""
    generado = documento_openapi()

    if serializar(contrato_publicado) != serializar(generado):
        detalle = "\n".join(_diferencias(contrato_publicado, generado))
        raise AssertionError(
            "El contrato versionado ya no describe a esta aplicacion:\n"
            f"{detalle}\n\n"
            "Si el cambio era intencional, regeneralo y commitea el diff:\n"
            "  cd backend && python -m herramientas.exportar_contrato\n"
            "Si no lo era, el cambio rompe a quien ya consume la API."
        )


def test_la_version_del_contrato_es_la_declarada_en_el_codigo(contrato_publicado):
    """El numero del documento y el de `api/esquemas.py` son el mismo dato.

    Si se separan, el documento publica una version que el codigo no reconoce, y un consumidor
    que decida por ese numero si puede actualizar estaria decidiendo sobre una mentira."""
    assert contrato_publicado["info"]["version"] == VERSION_DEL_CONTRATO


def test_el_contrato_declara_las_dos_rutas_que_la_api_expone(contrato_publicado):
    """Las rutas son lo primero que un consumidor busca; que desaparezca una es el cambio
    incompatible mas obvio que existe."""
    rutas = contrato_publicado["paths"]

    assert set(rutas) == {"/health", RUTA_CARGA}
    assert "get" in rutas["/health"]
    assert "post" in rutas[RUTA_CARGA]


def test_la_respuesta_de_carga_exige_los_cuatro_campos_del_reporte(contrato_publicado):
    """EC-07 promete que el docente ve que entro y que no. Esa promesa son cuatro campos, y los
    cuatro tienen que ser obligatorios: uno opcional deja al consumidor sin saber si la ausencia
    significa cero hojas o un error."""
    esquema = contrato_publicado["components"]["schemas"]["RespuestaDeCarga"]

    assert set(esquema["required"]) == {
        "examen_id",
        "total_procesados",
        "aceptadas",
        "rechazados",
    }


def test_el_contrato_publica_los_dos_unicos_estados_de_una_hoja(contrato_publicado):
    """Los estados del contrato y los del dominio son el mismo conjunto.

    Es la contraparte publica de la comprobacion que `api/esquemas.py` hace al importar: alli se
    verifica contra las constantes, aqui contra lo que el documento le promete a quien lo lee."""
    estado = contrato_publicado["components"]["schemas"]["HojaAceptadaEnRespuesta"][
        "properties"
    ]["estado"]

    assert set(estado["enum"]) == {ENCOLADA, PENDIENTE_DE_ENCOLAR}


def test_una_respuesta_real_trae_exactamente_los_campos_del_contrato(
    contrato_publicado, cliente_http
):
    """Que la aplicacion honre el documento, no solo que el documento se le parezca.

    Se ejerce el endpoint de verdad con un lote mixto (una hoja valida y un archivo rechazado)
    para que la respuesta traiga las dos listas con contenido, y se comparan los nombres de los
    campos contra los que declara el archivo versionado. Un campo de mas es tan grave como uno
    de menos: significa que la API filtra algo que el contrato no anuncia."""
    esquemas = contrato_publicado["components"]["schemas"]

    respuesta = cliente_http.post(
        "/examenes/CALC-2026-01/hojas",
        files=[
            ("archivos", ("hoja.jpg", JPG, "image/jpeg")),
            ("archivos", ("apuntes.txt", b"texto plano", "text/plain")),
        ],
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()

    assert set(cuerpo) == set(esquemas["RespuestaDeCarga"]["properties"])

    assert cuerpo["aceptadas"], "el lote traia una hoja valida y la respuesta no reporto ninguna"
    for hoja in cuerpo["aceptadas"]:
        assert set(hoja) == set(esquemas["HojaAceptadaEnRespuesta"]["properties"])

    assert cuerpo["rechazados"], "el lote traia un archivo invalido y no se reporto el rechazo"
    for rechazado in cuerpo["rechazados"]:
        assert set(rechazado) == set(esquemas["ArchivoRechazadoEnRespuesta"]["properties"])
