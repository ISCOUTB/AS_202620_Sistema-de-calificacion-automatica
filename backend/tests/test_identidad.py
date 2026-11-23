"""El módulo `identidad` (A-05, ADR-0025): contraseñas cifradas, el token de una sesión y la lista
de docentes que llega por el entorno.

Son funciones puras: ni red ni disco. La API las usa en `POST /sesion` y en cada ruta protegida
(`test_sesion.py`)."""

from datetime import datetime, timedelta, timezone

import pytest

from identidad import (
    ConfiguracionDeDocentesInvalida,
    autenticar,
    cifrar,
    emitir_sesion,
    leer_docentes,
    leer_sesion,
    verificar,
)

AHORA = datetime(2026, 11, 21, 18, 0, tzinfo=timezone.utc)
SECRETO = "un-secreto-de-prueba-largo-y-aleatorio"
DOCE_HORAS = timedelta(hours=12)


# ---- Contraseñas ----------------------------------------------------------------------------


def test_una_contrasena_cifrada_se_verifica_y_otra_no():
    cifrada = cifrar("calculo-diferencial")

    assert verificar("calculo-diferencial", cifrada)
    assert not verificar("calculo-integral", cifrada)


def test_la_cifrada_no_contiene_la_contrasena_ni_signos_que_dokploy_interprete():
    """La lista de docentes vive en una variable de Dokploy, y compose interpreta `$` en el `.env`:
    una cifrada con `$` llegaría cortada a la API. Tampoco puede llevar `,` ni `=`, que separan
    las entradas de la lista."""
    cifrada = cifrar("calculo-diferencial")

    assert "calculo-diferencial" not in cifrada
    assert not set("$,= \n") & set(cifrada)
    assert cifrada.startswith("scrypt:")


def test_la_misma_contrasena_se_cifra_distinto_cada_vez():
    """Cada cifrada lleva su sal: dos docentes con la misma contraseña no se delatan entre sí."""
    primera = cifrar("calculo-diferencial")
    segunda = cifrar("calculo-diferencial")

    assert primera != segunda


@pytest.mark.parametrize(
    "cifrada",
    ["", "texto-cualquiera", "bcrypt:1:2:3:00:00", "scrypt:16384:8:1:zz:00", "scrypt:a:b:c:d:e"],
)
def test_una_cifrada_mal_escrita_no_verifica_nada_ni_falla(cifrada):
    assert not verificar("calculo-diferencial", cifrada)


# ---- El token de la sesión --------------------------------------------------------------------


def test_un_token_recien_emitido_dice_quien_entro_y_hasta_cuando():
    token, sesion = emitir_sesion("profe@utb.edu.co", AHORA, DOCE_HORAS, SECRETO)

    leida = leer_sesion(token, AHORA + timedelta(hours=1), SECRETO)

    assert leida == sesion
    assert leida is not None
    assert leida.correo == "profe@utb.edu.co"
    assert leida.vence == AHORA + DOCE_HORAS


def test_un_token_vencido_no_vale():
    token, _ = emitir_sesion("profe@utb.edu.co", AHORA, DOCE_HORAS, SECRETO)

    assert leer_sesion(token, AHORA + DOCE_HORAS, SECRETO) is None


def test_un_token_firmado_con_otro_secreto_no_vale():
    token, _ = emitir_sesion("profe@utb.edu.co", AHORA, DOCE_HORAS, "otro-secreto-largo-y-distinto")

    assert leer_sesion(token, AHORA, SECRETO) is None


def test_un_token_con_el_correo_cambiado_no_vale():
    """Cambiar quién entró sin conocer el secreto: la firma ya no coincide."""
    token, _ = emitir_sesion("profe@utb.edu.co", AHORA, DOCE_HORAS, SECRETO)
    otro, _ = emitir_sesion("intruso@utb.edu.co", AHORA, DOCE_HORAS, SECRETO)
    version, _, firma = token.split(".")
    _, contenido_del_intruso, _ = otro.split(".")

    assert leer_sesion(f"{version}.{contenido_del_intruso}.{firma}", AHORA, SECRETO) is None


@pytest.mark.parametrize(
    "token", ["", "abc", "v1.x.y", "v1..", "v2.e30.AAAA", "a.b.c.d", "v1.é.ñ", "v1.e30.ñ"]
)
def test_un_token_mal_formado_no_vale_ni_falla(token):
    assert leer_sesion(token, AHORA, SECRETO) is None


def test_sin_secreto_no_se_emite_ni_se_acepta_ninguna_sesion():
    """Falla cerrado: si Dokploy no tiene el secreto, nadie entra, en vez de firmar con nada."""
    with pytest.raises(ValueError):
        emitir_sesion("profe@utb.edu.co", AHORA, DOCE_HORAS, "")

    token, _ = emitir_sesion("profe@utb.edu.co", AHORA, DOCE_HORAS, SECRETO)
    assert leer_sesion(token, AHORA, "") is None


# ---- La lista de docentes ---------------------------------------------------------------------


def test_la_lista_se_lee_con_el_correo_en_minusculas():
    cifrada = cifrar("calculo-diferencial")

    docentes = leer_docentes(f" Profe@UTB.edu.co={cifrada} ,\n ta@utb.edu.co={cifrada}\n")

    assert docentes == {"profe@utb.edu.co": cifrada, "ta@utb.edu.co": cifrada}


def test_una_lista_vacia_no_tiene_docentes():
    assert leer_docentes("") == {}
    assert leer_docentes("  \n ") == {}


@pytest.mark.parametrize(
    "texto",
    [
        "profe@utb.edu.co",
        "profe@utb.edu.co=",
        "sin-arroba=scrypt:16384:8:1:00:00",
        "profe@utb.edu.co=texto-en-claro",
        "profe@utb.edu.co=scrypt:16384:8:1:00:00,PROFE@utb.edu.co=scrypt:16384:8:1:00:00",
    ],
)
def test_una_lista_mal_escrita_se_rechaza_entera(texto):
    """Una entrada rota no se salta en silencio: el error dice cuál es, sin mostrar la cifrada."""
    with pytest.raises(ConfiguracionDeDocentesInvalida) as error:
        leer_docentes(texto)

    assert "scrypt:" not in str(error.value)
    assert "utb.edu.co" not in str(error.value).lower()


def test_autenticar_devuelve_el_correo_de_la_lista_solo_con_la_contrasena_correcta():
    docentes = {"profe@utb.edu.co": cifrar("calculo-diferencial")}

    assert autenticar(" PROFE@utb.edu.co ", "calculo-diferencial", docentes) == "profe@utb.edu.co"
    assert autenticar("profe@utb.edu.co", "otra-cosa", docentes) is None
    assert autenticar("nadie@utb.edu.co", "calculo-diferencial", docentes) is None
    assert autenticar("profe@utb.edu.co", "calculo-diferencial", {}) is None
