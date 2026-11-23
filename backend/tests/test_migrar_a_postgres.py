"""La copia de los registros `.jsonl` a Postgres (`herramientas/migrar_a_postgres.py`, ADR-0027).

Lo que cuida es que, después de migrar, los adaptadores de Postgres devuelvan lo mismo que los de
disco devolvían con los archivos, y que la herramienta no duplique hechos si se corre dos veces.
Como `test_base_de_datos.py`, corre con `DATABASE_URL_PRUEBAS` y se salta sin ella."""

import pytest

from herramientas.migrar_a_postgres import migrar
from infraestructura.base_de_datos import (
    BitacoraEnPostgres,
    ResultadosEnPostgres,
    RevisionesEnPostgres,
)
from infraestructura.bitacora import BitacoraEnDisco
from infraestructura.modelo import CORRECTA, ResolucionDelProfesor
from infraestructura.resultados import ResultadosEnDisco
from infraestructura.revisiones import RevisionesEnDisco
from tests.test_base_de_datos import CALIFICACION, EN, LECTURA, _entrada, con_base, url  # noqa: F401


@con_base
def test_la_migracion_deja_en_postgres_lo_mismo_que_habia_en_disco(url, tmp_path):
    bitacora = BitacoraEnDisco(tmp_path / "b.jsonl")
    for n in (1, 2):
        bitacora.registrar(_entrada(n))
    bitacora.confirmar_encolada("t-1")
    resultados = ResultadosEnDisco(tmp_path / "r.jsonl")
    resultados.registrar_lectura("h-1", "t-1", "P1", LECTURA, CALIFICACION)
    resultados.registrar_lectura_imposible("h-2", "t-2", "P1", "x")
    revisiones = RevisionesEnDisco(tmp_path / "v.jsonl")
    revisiones.registrar_resoluciones(
        "h-1", "P1", [ResolucionDelProfesor(7, CORRECTA, "C", por="Docente", en=EN)]
    )
    with open(tmp_path / "r.jsonl", "a", encoding="utf-8") as archivo:
        archivo.write('{"hecho": "leida", "trunc')

    cuenta = migrar(url, tmp_path / "b.jsonl", tmp_path / "r.jsonl", tmp_path / "v.jsonl", False)

    assert cuenta == {"bitacora": 3, "resultados": 2, "revisiones": 1, "lineas_saltadas": 1}
    assert ResultadosEnPostgres(url).hechos_del_examen("P1") == resultados.hechos_del_examen("P1")
    assert RevisionesEnPostgres(url).resoluciones_del_examen(
        "P1"
    ) == revisiones.resoluciones_del_examen("P1")
    assert BitacoraEnPostgres(url).pendientes() == bitacora.pendientes()
    assert BitacoraEnPostgres(url).recepciones_del_examen("P1") == bitacora.recepciones_del_examen(
        "P1"
    )
    with pytest.raises(SystemExit):
        migrar(url, tmp_path / "b.jsonl", tmp_path / "r.jsonl", tmp_path / "v.jsonl", False)


@con_base
def test_al_arrancar_migra_una_sola_vez_aunque_el_worker_ya_haya_escrito(url, tmp_path):
    """En el servidor, la API migra sola al arrancar (`--si-hace-falta`). La señal es la bitácora de
    la base vacía: solo la API la escribe, y todavía no atiende. El worker pudo guardar un
    resultado antes, y eso no debe impedir la migración."""
    bitacora = BitacoraEnDisco(tmp_path / "b.jsonl")
    bitacora.registrar(_entrada(1))
    bitacora.confirmar_encolada("t-1")
    ResultadosEnDisco(tmp_path / "r.jsonl").registrar_lectura(
        "h-1", "t-1", "P1", LECTURA, CALIFICACION
    )
    ResultadosEnPostgres(url).registrar_lectura_imposible("h-9", "t-9", "P1", "del worker")
    rutas = (tmp_path / "b.jsonl", tmp_path / "r.jsonl", tmp_path / "v.jsonl")

    primera = migrar(url, *rutas, False, si_hace_falta=True)
    segunda = migrar(url, *rutas, False, si_hace_falta=True)

    assert (primera["bitacora"], primera["resultados"]) == (2, 1)
    assert segunda == {"omitida": "la bitácora de la base ya tiene datos"}
    assert len(ResultadosEnPostgres(url).hechos_del_examen("P1")) == 2
