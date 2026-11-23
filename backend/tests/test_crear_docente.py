"""`python -m herramientas.crear_docente` arma la línea de un docente para la variable `DOCENTES`
de Dokploy (ADR-0025). Lo que imprime tiene que leerse con `leer_docentes` y dejar entrar con esa
contraseña, y nada más."""

import pytest

from herramientas import crear_docente
from identidad import autenticar, leer_docentes


def test_la_linea_se_lee_como_lista_y_deja_entrar_con_esa_contrasena():
    linea = crear_docente.linea_del_docente(" Profe@UTB.edu.co ", "calculo-diferencial")

    docentes = leer_docentes(linea)

    assert list(docentes) == ["profe@utb.edu.co"]
    assert autenticar("profe@utb.edu.co", "calculo-diferencial", docentes) == "profe@utb.edu.co"
    assert "calculo-diferencial" not in linea


@pytest.mark.parametrize(
    ("correo", "contrasena"),
    [("sin-arroba", "calculo-diferencial"), ("profe@utb.edu.co", "corta"), ("a=b@c", "calculo-x1")],
)
def test_un_correo_invalido_o_una_contrasena_corta_no_genera_linea(correo, contrasena):
    with pytest.raises(ValueError):
        crear_docente.linea_del_docente(correo, contrasena)


def test_el_comando_pide_la_contrasena_dos_veces_e_imprime_solo_la_linea(monkeypatch, capsys):
    respuestas = iter(["calculo-diferencial", "calculo-diferencial"])
    monkeypatch.setattr(crear_docente.getpass, "getpass", lambda _: next(respuestas))

    assert crear_docente.main(["profe@utb.edu.co"]) == 0

    salida = capsys.readouterr()
    assert salida.out.startswith("profe@utb.edu.co=scrypt:")
    assert salida.out.count("\n") == 1


def test_si_las_dos_contrasenas_no_coinciden_no_imprime_nada(monkeypatch, capsys):
    respuestas = iter(["calculo-diferencial", "calculo-integral"])
    monkeypatch.setattr(crear_docente.getpass, "getpass", lambda _: next(respuestas))

    assert crear_docente.main(["profe@utb.edu.co"]) == 1

    salida = capsys.readouterr()
    assert salida.out == ""
    assert "no coinciden" in salida.err
