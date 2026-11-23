"""Un docente no ve ni toca lo de otro (ADR-0028). Es el error que se vio en el servidor: al entrar
con la cuenta de un profesor aparecían los exámenes y resultados que había cargado otro.

Dos docentes hablan con la API, con el registro de exámenes de verdad (en disco), las claves, la
bitácora, los resultados y las revisiones en carpetas de la prueba. Cada ruta de un examen se
recorre con el docente dueño (que sí puede) y con el otro (que recibe 404, igual que si el examen no
existiera)."""

from collections.abc import Callable, Iterator
from datetime import datetime, timezone
from typing import Any

import pytest
from fastapi.testclient import TestClient

import api.main as principal
from api.main import (
    app,
    docente_de_la_sesion,
    obtener_almacen,
    obtener_bitacora,
    obtener_catalogo_de_claves,
    obtener_cliente_cola,
    obtener_lector_de_recepciones,
    obtener_lector_de_resultados,
    obtener_registro_de_claves,
    obtener_registro_de_examenes,
    obtener_revisiones,
)
from identidad import cifrar
from infraestructura.almacen import AlmacenEnDisco
from infraestructura.bitacora import BitacoraEnMemoria
from infraestructura.claves import ClavesEnDisco
from infraestructura.examenes import ExamenesEnDisco
from infraestructura.modelo import (
    ClaveDeRespuestas,
    EntradaDeBitacora,
    Habilitacion,
    PreguntaDeLaClave,
)
from infraestructura.resultados import ResultadosEnDisco
from infraestructura.revisiones import RevisionesEnDisco
from tests.test_recepcion import JPG, ColaFalsa

ANA = "ana@utb.edu.co"
BETO = "beto@utb.edu.co"


class Docentes:
    """Cambia el docente de la sesión entre peticiones, como dos personas en dos navegadores."""

    def __init__(self) -> None:
        self.actual = ANA

    def __call__(self) -> str:
        return self.actual


@pytest.fixture
def docentes() -> Docentes:
    return Docentes()


@pytest.fixture
def cliente(tmp_path, docentes) -> Iterator[TestClient]:
    registro = ExamenesEnDisco(tmp_path / "examenes.json")
    claves = ClavesEnDisco(tmp_path / "claves")
    bitacora = BitacoraEnMemoria()
    resultados = ResultadosEnDisco(tmp_path / "resultados.jsonl")
    revisiones = RevisionesEnDisco(tmp_path / "revisiones.jsonl")
    sustituciones: dict[Callable[..., Any], Callable[..., Any]] = {
        docente_de_la_sesion: docentes,
        obtener_registro_de_examenes: lambda: registro,
        obtener_registro_de_claves: lambda: claves,
        obtener_catalogo_de_claves: lambda: claves,
        obtener_bitacora: lambda: bitacora,
        obtener_lector_de_recepciones: lambda: bitacora,
        obtener_lector_de_resultados: lambda: resultados,
        obtener_revisiones: lambda: revisiones,
        obtener_almacen: lambda: AlmacenEnDisco(tmp_path / "almacen"),
        obtener_cliente_cola: lambda: ColaFalsa(),
    }
    app.dependency_overrides.update(sustituciones)
    yield TestClient(app)
    for dependencia in sustituciones:
        app.dependency_overrides.pop(dependencia, None)


def _crear(cliente, nombre: str) -> str:
    respuesta = cliente.post("/examenes", json={"nombre": nombre})
    assert respuesta.status_code in (200, 201), respuesta.text
    return respuesta.json()["examen_id"]


def _con_clave(cliente, nombre: str) -> str:
    examen = _crear(cliente, nombre)
    assert cliente.put(f"/examenes/{examen}/clave", json={"respuestas": ["A", "B"]}).status_code == 200
    return examen


def test_dos_docentes_con_el_mismo_nombre_tienen_examenes_distintos(cliente, docentes):
    de_ana = _crear(cliente, "Parcial 1")
    docentes.actual = BETO
    respuesta = cliente.post("/examenes", json={"nombre": "Parcial 1"})

    assert respuesta.status_code == 201
    assert respuesta.json()["examen_id"] != de_ana
    assert respuesta.json()["nombre"] == "Parcial 1"


def test_pedir_otra_vez_el_mismo_nombre_devuelve_el_mismo_examen_con_200(cliente):
    primero = cliente.post("/examenes", json={"nombre": "Parcial 1"})
    segundo = cliente.post("/examenes", json={"nombre": "parcial 1"})

    assert (primero.status_code, segundo.status_code) == (201, 200)
    assert segundo.json() == primero.json()


def test_un_nombre_vacio_responde_422(cliente):
    respuesta = cliente.post("/examenes", json={"nombre": "   "})

    assert respuesta.status_code == 422
    assert "nombre" in respuesta.json()["detail"]


def test_cada_docente_ve_solo_sus_examenes_en_la_lista(cliente, docentes):
    de_ana = _con_clave(cliente, "Parcial 1")
    docentes.actual = BETO
    de_beto = _con_clave(cliente, "Parcial 1")

    assert [e["examen_id"] for e in cliente.get("/examenes").json()["examenes"]] == [de_beto]
    docentes.actual = ANA
    assert [e["examen_id"] for e in cliente.get("/examenes").json()["examenes"]] == [de_ana]


@pytest.mark.parametrize(
    ("metodo", "ruta", "cuerpo"),
    [
        ("get", "/examenes/{e}/clave", None),
        ("put", "/examenes/{e}/clave", {"respuestas": ["C"]}),
        ("post", "/examenes/{e}/clave/habilitacion", None),
        ("get", "/examenes/{e}/resultados", None),
        ("get", "/examenes/{e}/revision", None),
        ("get", "/examenes/{e}/panel", None),
        ("get", "/examenes/{e}/hojas/h-1/preguntas/7/recorte", None),
        ("post", "/examenes/{e}/hojas/h-1/revision", {"resoluciones": [{"numero": 1, "opcion": "A"}]}),
    ],
    ids=lambda valor: valor if isinstance(valor, str) else None,
)
def test_el_otro_docente_recibe_404_en_cada_ruta_del_examen(
    cliente, docentes, metodo, ruta, cuerpo
):
    de_ana = _con_clave(cliente, "Parcial 1")
    docentes.actual = BETO

    respuesta = getattr(cliente, metodo)(ruta.format(e=de_ana), **({"json": cuerpo} if cuerpo else {}))

    assert respuesta.status_code == 404
    assert respuesta.json()["detail"] == "Ese examen no existe en su cuenta."


def test_el_otro_docente_no_puede_subir_hojas_al_examen(cliente, docentes):
    de_ana = _con_clave(cliente, "Parcial 1")
    docentes.actual = BETO

    respuesta = cliente.post(
        f"/examenes/{de_ana}/hojas", files=[("archivos", ("h.jpg", JPG, "image/jpeg"))]
    )

    assert respuesta.status_code == 404


def test_la_clave_del_otro_docente_no_cambia(cliente, docentes):
    de_ana = _con_clave(cliente, "Parcial 1")
    docentes.actual = BETO
    cliente.put(f"/examenes/{de_ana}/clave", json={"respuestas": ["D", "D", "D"]})

    docentes.actual = ANA
    assert cliente.get(f"/examenes/{de_ana}/clave").json()["respuestas"] == ["A", "B"]


def test_un_examen_que_no_existe_responde_igual_que_uno_ajeno(cliente):
    respuesta = cliente.get("/examenes/999999/clave")

    assert respuesta.status_code == 404
    assert respuesta.json()["detail"] == "Ese examen no existe en su cuenta."


def test_el_dueno_sigue_pudiendo_usar_todas_las_rutas(cliente):
    de_ana = _con_clave(cliente, "Parcial 1")

    assert cliente.post(f"/examenes/{de_ana}/clave/habilitacion").status_code == 200
    subida = cliente.post(
        f"/examenes/{de_ana}/hojas", files=[("archivos", ("h.jpg", JPG, "image/jpeg"))]
    )
    assert subida.status_code == 200
    assert len(subida.json()["aceptadas"]) == 1
    for ruta in ("resultados", "revision", "panel"):
        assert cliente.get(f"/examenes/{de_ana}/{ruta}").status_code == 200
    assert cliente.get(f"/examenes/{de_ana}/panel").json()["resumen"]["hojas_recibidas"] == 1


# --- La adopción de los exámenes anteriores a ADR-0028 ---------------------------------------


@pytest.fixture
def sin_adopcion_previa(monkeypatch, tmp_path):
    """La adopción corre una vez por proceso: cada prueba empieza como un proceso nuevo, con
    claves y bitácora propias y una lista de dos docentes."""
    monkeypatch.setattr(principal, "_ADOPCION_HECHA", principal.threading.Event())
    monkeypatch.setattr(principal, "RUTA_CLAVES", str(tmp_path / "claves"))
    monkeypatch.setattr(
        principal, "DOCENTES", f"{ANA}={cifrar('clave-de-ana')},{BETO}={cifrar('clave-de-beto')}"
    )
    bitacora = BitacoraEnMemoria()
    bitacora.registrar(EntradaDeBitacora("t-1", "PARCIAL-1", "PARCIAL-1/h.jpg", "h.jpg", "h-1"))
    monkeypatch.setattr(principal, "obtener_bitacora", lambda: bitacora)
    ClavesEnDisco(tmp_path / "claves").guardar(
        ClaveDeRespuestas(
            "QUIZ-3",
            (PreguntaDeLaClave(1, "A"),),
        )
    )
    return ExamenesEnDisco(tmp_path / "examenes.json")


def test_los_examenes_anteriores_quedan_del_primer_docente_de_la_lista(
    sin_adopcion_previa, monkeypatch
):
    monkeypatch.setattr(principal, "DOCENTE_DE_LOS_EXAMENES_ANTERIORES", "")

    principal._adoptar_examenes_anteriores(sin_adopcion_previa)

    assert [e.examen_id for e in sin_adopcion_previa.examenes_del_docente(ANA)] == [
        "PARCIAL-1", "QUIZ-3"
    ]
    assert sin_adopcion_previa.examenes_del_docente(BETO) == ()


def test_los_examenes_anteriores_quedan_del_docente_configurado(sin_adopcion_previa, monkeypatch):
    monkeypatch.setattr(principal, "DOCENTE_DE_LOS_EXAMENES_ANTERIORES", " Beto@UTB.edu.co ")

    principal._adoptar_examenes_anteriores(sin_adopcion_previa)

    assert len(sin_adopcion_previa.examenes_del_docente(BETO)) == 2


def test_con_un_docente_configurado_que_no_tiene_cuenta_no_se_adopta_nada(
    sin_adopcion_previa, monkeypatch
):
    monkeypatch.setattr(principal, "DOCENTE_DE_LOS_EXAMENES_ANTERIORES", "nadie@utb.edu.co")

    principal._adoptar_examenes_anteriores(sin_adopcion_previa)

    assert sin_adopcion_previa.examen("PARCIAL-1") is None
    assert not principal._ADOPCION_HECHA.is_set()


def test_la_adopcion_corre_una_sola_vez_por_proceso(sin_adopcion_previa, monkeypatch, tmp_path):
    monkeypatch.setattr(principal, "DOCENTE_DE_LOS_EXAMENES_ANTERIORES", "")
    principal._adoptar_examenes_anteriores(sin_adopcion_previa)
    ClavesEnDisco(tmp_path / "claves").guardar(
        ClaveDeRespuestas(
            "TARDE-1",
            (PreguntaDeLaClave(1, "A"),),
        )
    )

    principal._adoptar_examenes_anteriores(sin_adopcion_previa)

    assert sin_adopcion_previa.examen("TARDE-1") is None


def test_un_examen_anterior_vuelve_a_quien_habilito_su_clave(sin_adopcion_previa, monkeypatch, tmp_path):
    """Con el código anterior, Beto registró y habilitó `QUIZ-B`: la habilitación guardó su correo."""
    monkeypatch.setattr(principal, "DOCENTE_DE_LOS_EXAMENES_ANTERIORES", "")
    ClavesEnDisco(tmp_path / "claves").guardar(
        ClaveDeRespuestas(
            "QUIZ-B",
            (PreguntaDeLaClave(1, "A"),),
            Habilitacion(por=BETO, en=datetime(2026, 11, 20, tzinfo=timezone.utc)),
        )
    )
    ClavesEnDisco(tmp_path / "claves").guardar(
        ClaveDeRespuestas(
            "VIEJO-SIN-CUENTA",
            (PreguntaDeLaClave(1, "A"),),
            Habilitacion(por="ya-no-esta@utb.edu.co", en=datetime(2026, 11, 20, tzinfo=timezone.utc)),
        )
    )

    principal._adoptar_examenes_anteriores(sin_adopcion_previa)

    assert [e.examen_id for e in sin_adopcion_previa.examenes_del_docente(BETO)] == ["QUIZ-B"]
    assert [e.examen_id for e in sin_adopcion_previa.examenes_del_docente(ANA)] == [
        "PARCIAL-1", "QUIZ-3", "VIEJO-SIN-CUENTA"
    ]
