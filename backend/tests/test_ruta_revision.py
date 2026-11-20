"""La revisión manual de punta a punta (RF-08): las rutas que muestran lo que espera al profesor,
el recorte de cada pregunta y la que guarda lo que resolvió.

La hoja es sintética y se lee de verdad: todas las respuestas bien menos la 7, marcada a medias.
Lo que cuidan, además de la nota, es que las rutas públicas no publiquen la clave (AM-02), que
quede quién resolvió y cuándo (RF-10), que una solicitud que no cuadra no deje nada escrito y que
cada hoja diga de qué estudiante es (su código), con qué nombre y a qué hora llegó, para que el
profesor sepa cuál es."""

import json
import logging
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from api.main import (
    app,
    obtener_almacen,
    obtener_lector_de_recepciones,
    obtener_lector_de_resultados,
    obtener_revisiones,
)
from calificacion import calificar
from herramientas.hojas_sinteticas import fotografiar, hoja_marcada, patron
from infraestructura.almacen import AlmacenEnDisco
from infraestructura.bitacora import BitacoraEnDisco, BitacoraEnMemoria, RecepcionDeHoja
from infraestructura.modelo import (
    CALIFICADA,
    CODIGO_INCOMPLETO,
    EN_REVISION,
    ClaveDeRespuestas,
    EntradaDeBitacora,
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
NOMBRE = "foto inclinada.jpg"


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
    bitacora = BitacoraEnDisco(tmp_path / "bitacora.jsonl")
    bitacora.registrar(EntradaDeBitacora("t-1", EXAMEN, "referencia-h-1", NOMBRE, "h-1"))

    app.dependency_overrides[obtener_lector_de_resultados] = lambda: resultados
    app.dependency_overrides[obtener_revisiones] = lambda: revisiones
    app.dependency_overrides[obtener_almacen] = lambda: almacen
    app.dependency_overrides[obtener_lector_de_recepciones] = lambda: bitacora
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


def test_cada_hoja_dice_con_que_nombre_y_a_que_hora_llego(cliente):
    [hoja] = cliente.get(f"/examenes/{EXAMEN}/revision").json()["hojas"]

    assert hoja["nombre_archivo"] == NOMBRE
    recibida = datetime.fromisoformat(hoja["recibida_en"])
    assert recibida.tzinfo is not None
    assert abs(datetime.now(timezone.utc) - recibida) < timedelta(minutes=5)


def test_sin_su_linea_en_la_bitacora_la_hoja_sale_sin_nombre_ni_hora(cliente):
    app.dependency_overrides[obtener_lector_de_recepciones] = BitacoraEnMemoria

    [hoja] = cliente.get(f"/examenes/{EXAMEN}/revision").json()["hojas"]

    assert (hoja["hoja_id"], hoja["nombre_archivo"], hoja["recibida_en"]) == ("h-1", None, None)


def test_la_bitacora_da_la_primera_llegada_de_cada_hoja_del_examen(tmp_path):
    def recibida(hoja: str | None, trabajo: str, nombre: str, momento: str, examen=EXAMEN):
        linea = {"hecho": "recibida", "trabajo_id": trabajo, "examen_id": examen,
                 "referencia": "r", "nombre_archivo": nombre, "momento": momento}
        return json.dumps(linea if hoja is None else linea | {"hoja_id": hoja})

    ruta = tmp_path / "bitacora.jsonl"
    ruta.write_text(
        "\n".join([
            recibida("h-1", "t-1", "hoja1.jpg", "2026-11-16T19:32:00+00:00"),
            json.dumps({"hecho": "encolada", "trabajo_id": "t-1", "momento": "2026-11-16T19:33Z"}),
            # El mismo nombre en otro examen no entra.
            recibida("h-9", "t-9", "hoja1.jpg", "2026-11-16T19:32:00+00:00", examen="OTRO"),
            # Anterior a ADR-0018, sin `hoja_id`: su trabajo es la hoja.
            recibida(None, "t-2", "hoja2.jpg", "2026-11-16T19:33:00+00:00"),
            # La misma hoja registrada otra vez: vale cuando llegó.
            recibida("h-1", "t-3", "otra.jpg", "2026-11-17T08:00:00+00:00"),
            # Truncada por una caída: se salta.
            f'{{"hecho": "recibida", "examen_id": "{EXAMEN}", "hoja_id": "h-',
        ]),
        encoding="utf-8",
    )

    assert BitacoraEnDisco(ruta).recepciones_del_examen(EXAMEN) == {
        "h-1": RecepcionDeHoja("hoja1.jpg", datetime(2026, 11, 16, 19, 32, tzinfo=timezone.utc)),
        "t-2": RecepcionDeHoja("hoja2.jpg", datetime(2026, 11, 16, 19, 33, tzinfo=timezone.utc)),
    }


def test_la_bitacora_en_memoria_tambien_dice_como_llego_cada_hoja():
    bitacora = BitacoraEnMemoria()
    bitacora.registrar(EntradaDeBitacora("t-1", EXAMEN, "r", "hoja1.jpg", "h-1"))
    bitacora.registrar(EntradaDeBitacora("t-9", "OTRO", "r", "hoja1.jpg", "h-9"))

    [(hoja_id, recepcion)] = bitacora.recepciones_del_examen(EXAMEN).items()

    assert (hoja_id, recepcion.nombre_archivo) == ("h-1", "hoja1.jpg")
    assert recepcion.recibida_en is not None


def test_la_revision_trae_la_opcion_sugerida(cliente):
    """ADR-0024: la 7, marcada a medias en la C, llega con la C para preseleccionarla."""
    [hoja] = cliente.get(f"/examenes/{EXAMEN}/revision").json()["hojas"]

    [pregunta] = hoja["preguntas"]
    assert (pregunta["opcion_sugerida"], pregunta["resuelta"]) == ("C", False)
    assert hoja["provisional"] is True


def test_una_hoja_leida_antes_del_corte_llega_sin_sugerencia(cliente, tmp_path):
    """Las hojas leídas antes de ADR-0024 no traen la sugerencia en el registro: la revisión las
    muestra igual, sin nada preseleccionado."""
    ruta = tmp_path / "resultados.jsonl"
    hechos = [json.loads(linea) for linea in ruta.read_text(encoding="utf-8").splitlines()]
    for hecho in hechos:
        lectura = hecho.get("lectura") or {}
        lectura.pop("corte_de_intencion", None)
        for fila in lectura.get("preguntas", ()):
            fila.pop("opcion_sugerida", None)
    ruta.write_text("".join(json.dumps(hecho) + "\n" for hecho in hechos), encoding="utf-8")

    respuesta = cliente.get(f"/examenes/{EXAMEN}/revision")

    assert respuesta.status_code == 200
    [pregunta] = respuesta.json()["hojas"][0]["preguntas"]
    assert pregunta["opcion_sugerida"] is None


def test_la_revision_no_publica_la_clave(cliente):
    texto = cliente.get(f"/examenes/{EXAMEN}/revision").text

    assert "correcta" not in texto


def test_la_revision_trae_el_codigo_del_estudiante(cliente):
    """El docente reconoce la hoja por el código, no por el nombre del archivo. Hasta A-05 la ruta
    es pública, como las demás: por eso solo entran hojas sintéticas (AM-02)."""
    [hoja] = cliente.get(f"/examenes/{EXAMEN}/revision").json()["hojas"]

    assert hoja["codigo"] == "T" + CODIGO


def test_un_codigo_incompleto_llega_con_lo_que_se_leyo(cliente, tmp_path):
    """Los dígitos que no se leyeron llegan como `?`, y una lectura sin código llega nula."""
    ruta = tmp_path / "resultados.jsonl"
    hechos = [json.loads(linea) for linea in ruta.read_text(encoding="utf-8").splitlines()]
    hechos[0]["lectura"]["codigo"] = {
        "estado": CODIGO_INCOMPLETO, "valor": "T2026?105", "columnas_por_revisar": [5],
    }
    ruta.write_text("".join(json.dumps(hecho) + "\n" for hecho in hechos), encoding="utf-8")

    [hoja] = cliente.get(f"/examenes/{EXAMEN}/revision").json()["hojas"]
    assert (hoja["codigo"], hoja["codigo_completo"]) == ("T2026?105", False)

    del hechos[0]["lectura"]["codigo"]
    ruta.write_text("".join(json.dumps(hecho) + "\n" for hecho in hechos), encoding="utf-8")

    [hoja] = cliente.get(f"/examenes/{EXAMEN}/revision").json()["hojas"]
    assert hoja["codigo"] is None


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
