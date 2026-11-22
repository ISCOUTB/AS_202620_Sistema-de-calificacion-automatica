"""Las herramientas de medición no leen ni escriben fuera del repositorio, ni piden a otro servidor
que no sea la API (`herramientas/rutas.py`). Son los hallazgos S8707 y S8703 de SonarCloud: con
argumentos manipulados, una herramienta que acepta cualquier ruta o URL podría leer o pisar
cualquier archivo, o hacer peticiones a cualquier parte. Y la comprobación va antes del trabajo
largo: medir 300 hojas tarda unos 6 minutos, y no se pierden para fallar al final."""

import json

import pytest

from herramientas import medir_lectura, medir_procesamiento, rutas


@pytest.fixture
def repositorio(tmp_path, monkeypatch):
    """Un repositorio de mentira, con una carpeta hermana que empieza con el mismo nombre."""
    dentro, hermana = tmp_path / "repo", tmp_path / "repo-otro"
    for carpeta in (dentro, hermana):
        carpeta.mkdir()
        (carpeta / "registro.jsonl").write_text("", encoding="utf-8")
    monkeypatch.setattr(rutas, "CARPETA_DEL_REPOSITORIO", dentro)
    return dentro


def _afuera(repositorio):
    """Fuera del repositorio: la carpeta hermana con el mismo prefijo, y la misma con `..`."""
    return (
        repositorio.parent / "repo-otro" / "registro.jsonl",
        repositorio / ".." / "repo-otro" / "registro.jsonl",
    )


def test_una_ruta_dentro_del_repositorio_se_acepta_y_sale_canonica(repositorio):
    ruta = rutas.ruta_en_el_repositorio(str(repositorio / "sub" / ".." / "informe.json"), "--json")

    assert ruta == str((repositorio / "informe.json").resolve())


def test_una_ruta_fuera_del_repositorio_se_rechaza(repositorio):
    for afuera in _afuera(repositorio):
        with pytest.raises(SystemExit, match="dentro del repositorio"):
            rutas.ruta_en_el_repositorio(str(afuera), "--json")


@pytest.mark.parametrize("url", [
    "http://localhost:8000",
    "http://127.0.0.1:8010",
    "https://api-calificacion.iscoutb.dev",
])
def test_la_url_de_la_api_en_local_o_en_el_servidor_se_acepta(url):
    assert rutas.url_de_la_api(url) == url
    assert rutas.url_de_la_api(url + "/") == url


def test_la_url_que_sale_es_la_de_la_lista_y_no_el_argumento():
    """Es lo que cierra el hallazgo S8703 de `--url`: lo que llega a `httpx` es la cadena de
    `APIS_PERMITIDAS`, no la que vino por la línea de comandos."""
    pedida = "http://localhost:8010/"

    assert any(rutas.url_de_la_api(pedida) is permitida for permitida in rutas.APIS_PERMITIDAS)


@pytest.mark.parametrize("url", [
    "http://localhost.otro.example:8000",   # empieza con un host permitido
    "http://localhost:8000.otro.example",   # empieza con una dirección permitida
    "http://otro.example/?h=localhost",     # la contiene
    "http://localhost@otro.example",        # la lleva como usuario
    "http://localhost:9000",                # un puerto que no está en la lista
    "http://localhost:8000/admin",          # una ruta: solo se acepta la raíz de la API
    "http://169.254.169.254/latest",        # metadatos de una nube
    "file:///etc/passwd",
    "ftp://localhost/",
    "localhost:8000",                       # sin esquema
])
def test_cualquier_otra_url_se_rechaza(url):
    with pytest.raises(SystemExit, match="--url"):
        rutas.url_de_la_api(url)


def test_medir_lectura_rechaza_el_json_antes_de_medir(repositorio, monkeypatch):
    def no_medir(*_):
        raise AssertionError("midió antes de comprobar la ruta")

    monkeypatch.setattr(medir_lectura, "medir", no_medir)
    for afuera in _afuera(repositorio):
        with pytest.raises(SystemExit, match="--json"):
            medir_lectura.main(["--hojas", "1", "--json", str(afuera)])


def test_medir_lectura_escribe_el_json_dentro_del_repositorio(repositorio, monkeypatch, capsys):
    monkeypatch.setattr(medir_lectura, "medir", lambda *_: {"errores_silenciosos": 0})

    assert medir_lectura.main(["--hojas", "1", "--json", str(repositorio / "informe.json")]) == 0
    assert json.loads((repositorio / "informe.json").read_text(encoding="utf-8")) == json.loads(
        capsys.readouterr().out
    )


def test_cargar_rechaza_la_url_y_la_clave_antes_de_generar_las_hojas(repositorio, monkeypatch):
    def no_generar(*_):
        raise AssertionError("generó las hojas antes de comprobar los argumentos")

    monkeypatch.setattr(medir_procesamiento, "hojas_escaneadas", no_generar)
    base = ["cargar", "--examen", "X", "--hojas", "1"]
    with pytest.raises(SystemExit, match="--url"):
        medir_procesamiento.main([*base, "--url", "http://otro.example"])
    for afuera in _afuera(repositorio):
        with pytest.raises(SystemExit, match="--clave"):
            medir_procesamiento.main([*base, "--url", "http://localhost:8000",
                                      "--clave", str(afuera)])
    assert not (repositorio.parent / "repo-otro" / "X.json").exists()


def test_analizar_no_abre_un_registro_de_fuera_del_repositorio(repositorio, capsys):
    assert medir_procesamiento.main(
        ["analizar", str(repositorio / "registro.jsonl"), "--examen", "X"]
    ) == 0
    assert json.loads(capsys.readouterr().out)["hojas_publicadas"] == 0
    for afuera in _afuera(repositorio):
        with pytest.raises(SystemExit, match="dentro del repositorio"):
            medir_procesamiento.main(["analizar", str(afuera), "--examen", "X"])


def test_el_paso_clave_escribe_la_clave_en_la_salida_estandar(capsys):
    assert medir_procesamiento.main(["clave", "--examen", "LOTE"]) == 0

    assert json.loads(capsys.readouterr().out) == medir_procesamiento.clave("LOTE")
