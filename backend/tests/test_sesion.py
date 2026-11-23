"""El inicio de sesión de la API (A-05, ADR-0025): `POST /sesion` da un token, y todas las rutas
salvo `/health`, `/metricas` y la de entrar lo piden.

Estas pruebas quitan la sustitución de `conftest.py`, así que hablan con la dependencia de verdad.
La lista de rutas protegidas no se escribe a mano: sale de la aplicación, para que una ruta nueva
que se olvide la sesión falle aquí (EC-06 pide cubrir todas las rutas que exponen datos)."""

import logging
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from api.main import (
    app,
    docente_de_la_sesion,
    obtener_catalogo_de_claves,
    obtener_docentes,
    obtener_secreto_de_sesion,
)
from api.settings import ALLOWED_ORIGIN
from identidad import cifrar, emitir_sesion
from infraestructura.claves import ClavesEnDisco

SECRETO = "secreto-de-las-pruebas-de-sesion"
CORREO = "profe@utb.edu.co"
CONTRASENA = "calculo-diferencial"
PUBLICAS = {("GET", "/health"), ("HEAD", "/health"), ("POST", "/sesion"), ("GET", "/metricas")}


@pytest.fixture(scope="module")
def docentes() -> dict[str, str]:
    return {CORREO: cifrar(CONTRASENA)}


@pytest.fixture
def cliente(docentes, tmp_path) -> Iterator[TestClient]:
    app.dependency_overrides.pop(docente_de_la_sesion, None)
    app.dependency_overrides[obtener_secreto_de_sesion] = lambda: SECRETO
    app.dependency_overrides[obtener_docentes] = lambda: docentes
    app.dependency_overrides[obtener_catalogo_de_claves] = lambda: ClavesEnDisco(tmp_path)
    yield TestClient(app)
    app.dependency_overrides.clear()


def _entrar(cliente, correo=CORREO, contrasena=CONTRASENA):
    return cliente.post("/sesion", json={"correo": correo, "contrasena": contrasena})


def _con(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_con_la_contrasena_correcta_da_un_token_que_abre_las_rutas(cliente):
    respuesta = _entrar(cliente, correo=" Profe@UTB.edu.co ")

    assert respuesta.status_code == 200
    sesion = respuesta.json()
    assert sesion["correo"] == CORREO
    vence = datetime.fromisoformat(sesion["vence"])
    assert timedelta(hours=11) < vence - datetime.now(timezone.utc) <= timedelta(hours=12)
    assert cliente.get("/examenes", headers=_con(sesion["token"])).status_code == 200


@pytest.mark.parametrize(
    ("correo", "contrasena"),
    [(CORREO, "otra-contrasena"), ("nadie@utb.edu.co", CONTRASENA)],
    ids=["contrasena-equivocada", "correo-sin-cuenta"],
)
def test_una_entrada_equivocada_no_dice_si_el_correo_existe(cliente, correo, contrasena):
    respuesta = _entrar(cliente, correo, contrasena)

    assert respuesta.status_code == 401
    assert respuesta.json() == {"detail": "Correo o contraseña incorrectos."}


@pytest.mark.parametrize(
    ("secreto", "lista"), [("", True), (SECRETO, False)], ids=["sin-secreto", "sin-docentes"]
)
def test_sin_configurar_nadie_entra_y_la_api_sigue_viva(cliente, docentes, secreto, lista):
    """Falla cerrado: 503 al entrar, 401 en lo demás, y la sonda de vida igual."""
    app.dependency_overrides[obtener_secreto_de_sesion] = lambda: secreto
    app.dependency_overrides[obtener_docentes] = lambda: docentes if lista else {}

    assert _entrar(cliente).status_code == 503
    assert cliente.get("/examenes").status_code == 401
    assert cliente.get("/health").status_code == 200


def _rutas_protegidas() -> list[tuple[str, str]]:
    rutas = []
    for ruta in app.routes:
        if isinstance(ruta, APIRoute):
            for metodo in ruta.methods or ():
                if (metodo, ruta.path) not in PUBLICAS:
                    rutas.append((metodo, ruta.path))
    return sorted(rutas)


def test_la_lista_de_rutas_protegidas_no_esta_vacia():
    """Si la aplicación cambiara de forma de declarar rutas, la prueba de abajo pasaría sin
    probar nada."""
    assert len(_rutas_protegidas()) >= 7


@pytest.mark.parametrize(("metodo", "ruta"), _rutas_protegidas())
def test_toda_ruta_que_no_es_publica_pide_la_sesion(cliente, metodo, ruta):
    camino = ruta.format(examen_id="EXAMEN", hoja_id="h-1", numero=1, llave="0" * 64)

    respuesta = cliente.request(metodo, camino)

    assert respuesta.status_code == 401
    assert respuesta.headers["www-authenticate"] == "Bearer"
    assert respuesta.json() == {"detail": "Inicia sesión para continuar."}


@pytest.mark.parametrize("ruta", ["/health", "/metricas"])
def test_la_sonda_de_vida_y_las_metricas_no_piden_sesion(cliente, ruta):
    """`/metricas` publica solo cuentas (EC-09), y la consulta el monitoreo del servidor."""
    assert cliente.get(ruta).status_code == 200


def _token(correo=CORREO, ahora=None, duracion=timedelta(hours=1), secreto=SECRETO) -> str:
    return emitir_sesion(correo, ahora or datetime.now(timezone.utc), duracion, secreto)[0]


@pytest.mark.parametrize(
    "token",
    [
        pytest.param(_token(ahora=datetime.now(timezone.utc) - timedelta(hours=2)), id="vencido"),
        pytest.param(_token(secreto="otro-secreto-cualquiera-largo"), id="otro-secreto"),
        pytest.param(_token() + "x", id="alterado"),
        pytest.param("no-es-un-token", id="basura"),
    ],
)
def test_un_token_que_no_vale_da_401(cliente, token):
    assert cliente.get("/examenes", headers=_con(token)).status_code == 401


def test_un_docente_que_se_quita_de_la_lista_pierde_su_sesion(cliente):
    """El token no se puede revocar, pero la API comprueba en cada petición que el correo siga en
    la lista: quitarlo de DOCENTES y desplegar le cierra la puerta sin esperar a que venza."""
    token = _entrar(cliente).json()["token"]
    app.dependency_overrides[obtener_docentes] = lambda: {"otro@utb.edu.co": cifrar(CONTRASENA)}

    assert cliente.get("/examenes", headers=_con(token)).status_code == 401


def test_el_navegador_puede_mandar_el_encabezado_de_la_sesion(cliente):
    """El sitio y la API están en orígenes distintos: sin permiso en el preflight de CORS, el
    navegador no deja salir ninguna petición con `Authorization`."""
    respuesta = cliente.options(
        "/examenes",
        headers={
            "Origin": ALLOWED_ORIGIN,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization",
        },
    )

    assert respuesta.status_code == 200
    assert "authorization" in respuesta.headers["access-control-allow-headers"].lower()


def test_el_registro_no_lleva_el_correo_ni_la_contrasena(cliente, caplog):
    """Quién entró no va al log, que lee cualquiera con acceso al panel del servidor, igual que el
    nombre de quien resuelve una revisión."""
    with caplog.at_level(logging.INFO):
        _entrar(cliente)
        _entrar(cliente, contrasena="otra-contrasena")

    eventos = [getattr(r, "evento", None) for r in caplog.records]
    assert "sesion_iniciada" in eventos
    assert "entrada_rechazada" in eventos
    texto = " ".join(str(vars(registro)) for registro in caplog.records)
    assert CORREO not in texto
    assert CONTRASENA not in texto
