"""La revisión manual de punta a punta (RF-08): las rutas que muestran lo que espera al profesor,
el recorte de cada pregunta y la que guarda lo que resolvió.

La hoja es sintética y se lee de verdad: todas las respuestas bien menos la 7, marcada a medias.
Lo que cuidan, además de la nota, es que las rutas públicas no publiquen la clave ni el código del
estudiante (AM-02), que quede quién resolvió y cuándo (RF-10) y que una solicitud que no cuadra no
deje nada escrito."""

import logging
from collections.abc import Iterator
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from api.main import app, obtener_almacen, obtener_lector_de_resultados, obtener_revisiones
from calificacion import calificar
from herramientas.hojas_sinteticas import fotografiar, hoja_marcada, patron
from infraestructura.almacen import AlmacenEnDisco
from infraestructura.modelo import (
    CALIFICADA,
    EN_REVISION,
    ClaveDeRespuestas,
    Habilitacion,
    PreguntaDeLaClave,
)
from infraestructura.resultados import SIN_CLAVE, ResultadosEnDisco
from infraestructura.revisiones import RevisionesEnDisco
from omr import leer_hoja_con_recortes

EXAMEN = "CALC-2026-02"
CODIGO = "20261105"
CORRECTAS = {n: patron(n) for n in range(1, 41)} | {7: "C"}
CLAVE = ClaveDeRespuestas(
    EXAMEN,
    tuple(PreguntaDeLaClave(n, letra) for n, letra in CORRECTAS.items()),
    Habilitacion(por="Docente de prueba", en=datetime(2026, 11, 5, tzinfo=timezone.utc)),
)
DOCENTE = "Docente de prueba"


@pytest.fixture(scope="module")
def leida():
    respuestas = {n: letra for n, letra in CORRECTAS.items() if n != 7}
    foto = fotografiar(hoja_marcada(respuestas, CODIGO, a_medias=((7, "C"),)))
    return leer_hoja_con_recortes(foto, 70)


@pytest.fixture
def revisiones(tmp_path) -> RevisionesEnDisco:
    return RevisionesEnDisco(tmp_path / "revisiones.jsonl")


@pytest.fixture
def cliente(tmp_path, leida, revisiones) -> Iterator[TestClient]:
    lectura, recortes = leida
    almacen = AlmacenEnDisco(tmp_path / "almacen")
    referencias = {
        numero: almacen.guardar(EXAMEN, f"recorte-h-1-pregunta-{numero}.png", png)
        for numero, png in recortes.items()
    }
    resultados = ResultadosEnDisco(tmp_path / "resultados.jsonl")
    resultados.registrar_lectura(
        "h-1", "t-1", EXAMEN, lectura, calificar(lectura, CLAVE), recortes=referencias
    )
    # Leída sin clave: no tiene nota que recalcular, así que no entra a la revisión.
    resultados.registrar_lectura("h-2", "t-2", EXAMEN, lectura, None, SIN_CLAVE)

    app.dependency_overrides[obtener_lector_de_resultados] = lambda: resultados
    app.dependency_overrides[obtener_revisiones] = lambda: revisiones
    app.dependency_overrides[obtener_almacen] = lambda: almacen
    yield TestClient(app)
    app.dependency_overrides.clear()


def _resolver(cliente, *resoluciones, hoja="h-1", por=DOCENTE):
    return cliente.post(
        f"/examenes/{EXAMEN}/hojas/{hoja}/revision",
        json={
            "por": por,
            "resoluciones": [{"numero": n, "opcion": opcion} for n, opcion in resoluciones],
        },
    )


def test_la_revision_muestra_cada_pregunta_dudosa_con_sus_burbujas_y_su_recorte(cliente):
    respuesta = cliente.get(f"/examenes/{EXAMEN}/revision")

    assert respuesta.status_code == 200
    [hoja] = respuesta.json()["hojas"]
    assert (hoja["hoja_id"], hoja["nota_en_decimas"], hoja["provisional"]) == ("h-1", 49, True)
    [pregunta] = hoja["preguntas"]
    assert pregunta["numero"] == 7
    assert [b["opcion"] for b in pregunta["burbujas"]] == ["A", "B", "C", "D"]
    assert (pregunta["con_recorte"], pregunta["resuelta"]) == (True, False)


def test_la_revision_no_publica_la_clave_ni_el_codigo(cliente):
    texto = cliente.get(f"/examenes/{EXAMEN}/revision").text

    assert "correcta" not in texto
    assert CODIGO not in texto


def test_el_recorte_de_la_pregunta_es_un_png(cliente):
    respuesta = cliente.get(f"/examenes/{EXAMEN}/hojas/h-1/preguntas/7/recorte")

    assert respuesta.status_code == 200
    assert respuesta.headers["content-type"] == "image/png"
    assert respuesta.content.startswith(b"\x89PNG")


@pytest.mark.parametrize("ruta", ["h-1/preguntas/8", "h-9/preguntas/7", "h-2/preguntas/7"])
def test_sin_recorte_responde_404(cliente, ruta):
    assert cliente.get(f"/examenes/{EXAMEN}/hojas/{ruta}/recorte").status_code == 404


def test_resolver_recalcula_la_nota_y_la_marca_como_revisada(cliente, revisiones):
    respuesta = _resolver(cliente, (7, "C"))

    assert respuesta.status_code == 200
    hoja = respuesta.json()
    assert (hoja["estado"], hoja["nota_en_decimas"], hoja["provisional"]) == (CALIFICADA, 50, False)
    assert hoja["revisada"] is True

    # La pantalla de carga ve la misma nota, y la revisión dice quién la resolvió.
    [en_resultados] = [
        h for h in cliente.get(f"/examenes/{EXAMEN}/resultados").json()["hojas"]
        if h["hoja_id"] == "h-1"
    ]
    assert (en_resultados["nota_en_decimas"], en_resultados["revisada"]) == (50, True)
    [pregunta] = cliente.get(f"/examenes/{EXAMEN}/revision").json()["hojas"][0]["preguntas"]
    assert (pregunta["opcion_resuelta"], pregunta["resuelta_por"]) == ("C", DOCENTE)

    # Quién y cuándo quedan en el registro (RF-10).
    [resolucion] = revisiones.resoluciones_del_examen(EXAMEN)["h-1"]
    assert (resolucion.por, resolucion.en.tzinfo is not None) == (DOCENTE, True)


def test_el_log_de_la_revision_no_lleva_el_nombre_de_quien_resuelve(cliente, caplog):
    """El nombre queda en el registro de revisiones, que es donde hace falta (RF-10), y no en el
    log, que lee cualquiera con acceso al panel del servidor."""
    with caplog.at_level(logging.INFO):
        assert _resolver(cliente, (7, "C")).status_code == 200

    [guardada] = [r for r in caplog.records if getattr(r, "evento", None) == "revision_guardada"]
    assert guardada.preguntas == 1
    assert all(DOCENTE not in str(vars(registro)) for registro in caplog.records)


@pytest.mark.parametrize("opcion", ["B", None], ids=["otra-opcion", "ninguna"])
def test_cambiar_de_opinion_vuelve_a_recalcular(cliente, opcion):
    _resolver(cliente, (7, "C"))

    hoja = _resolver(cliente, (7, opcion)).json()

    assert (hoja["estado"], hoja["nota_en_decimas"]) == (CALIFICADA, 49)


def test_sin_resolver_la_hoja_sigue_en_revision(cliente):
    [en_resultados] = [
        h for h in cliente.get(f"/examenes/{EXAMEN}/resultados").json()["hojas"]
        if h["hoja_id"] == "h-1"
    ]
    assert (en_resultados["estado"], en_resultados["revisada"]) == (EN_REVISION, False)


@pytest.mark.parametrize(
    ("hoja", "resoluciones", "por", "codigo"),
    [
        ("h-1", [(8, "A")], DOCENTE, 422),
        ("h-1", [(7, "C"), (7, "B")], DOCENTE, 422),
        ("h-1", [(7, "C")], "   ", 422),
        ("h-1", [(7, "E")], DOCENTE, 422),
        ("h-9", [(7, "C")], DOCENTE, 404),
        ("h-2", [(7, "C")], DOCENTE, 404),
    ],
    ids=["no-esta-en-revision", "repetida", "sin-nombre", "opcion-inexistente", "otra-hoja",
         "sin-nota"],
)
def test_lo_que_no_cuadra_se_rechaza_sin_escribir_nada(
    cliente, revisiones, hoja, resoluciones, por, codigo
):
    respuesta = _resolver(cliente, *resoluciones, hoja=hoja, por=por)

    assert respuesta.status_code == codigo
    assert revisiones.resoluciones_del_examen(EXAMEN) == {}
