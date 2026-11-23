"""Los adaptadores de Postgres (`infraestructura.base_de_datos`, ADR-0027).

Lo que cuidan estas pruebas es que **cada adaptador de Postgres devuelva exactamente lo mismo que
su par en disco** para la misma secuencia de hechos: es lo que permite cambiar de adaptador sin
tocar a quien usa el puerto. Corren contra una base real cuando existe `DATABASE_URL_PRUEBAS`
(el CI la levanta como servicio); sin ella se saltan, salvo la del fallo de conexión, que no
necesita base. La base de pruebas se vacía antes de cada prueba: no apuntes la variable a la de
producción."""

import os
from datetime import datetime, timezone

import pytest

from infraestructura.base_de_datos import (
    BitacoraEnPostgres,
    ResultadosEnPostgres,
    RevisionesEnPostgres,
    crear_esquema,
)
from infraestructura.bitacora import BitacoraEnDisco
from infraestructura.modelo import (
    CODIGO_COMPLETO,
    CORRECTA,
    INCORRECTA,
    CalificacionDeHoja,
    EntradaDeBitacora,
    LecturaDeHoja,
    LecturaDelCodigo,
    ResolucionDelProfesor,
)
from infraestructura.resultados import SIN_CLAVE, ResultadosEnDisco
from infraestructura.revisiones import RevisionesEnDisco

URL = os.environ.get("DATABASE_URL_PRUEBAS", "")
con_base = pytest.mark.skipif(not URL, reason="sin DATABASE_URL_PRUEBAS")

EN = datetime(2026, 11, 22, 21, 0, tzinfo=timezone.utc)
LECTURA = LecturaDeHoja(
    version_del_formato="quantia-hoja-v1",
    codigo=LecturaDelCodigo(CODIGO_COMPLETO, "T12345678"),
    preguntas=(),
    umbral_de_confianza=70,
    duracion_ms=12.5,
)
CALIFICACION = CalificacionDeHoja(
    examen_id="P1",
    nota_en_decimas=40,
    puntos=4.0,
    puntos_posibles=5.0,
    provisional=True,
    codigo_por_revisar=False,
    preguntas=(),
)


@pytest.fixture
def url():
    import psycopg

    crear_esquema(URL)
    with psycopg.connect(URL) as conexion:
        conexion.execute(
            "TRUNCATE bitacora_de_recepcion, resultados_de_lectura, revisiones_del_profesor"
        )
    return URL


def _sin_momento(hechos: list[dict]) -> list[dict]:
    return [{k: v for k, v in hecho.items() if k != "momento"} for hecho in hechos]


def _entrada(n: int, examen: str = "P1") -> EntradaDeBitacora:
    return EntradaDeBitacora(f"t-{n}", examen, f"{examen}/h{n}.jpg", f"h{n}.jpg", f"h-{n}")


@con_base
def test_resultados_devuelve_lo_mismo_que_en_disco(url, tmp_path):
    registros = [ResultadosEnDisco(tmp_path / "r.jsonl"), ResultadosEnPostgres(url)]
    for registro in registros:
        registro.registrar_lectura("h-1", "t-1", "P1", LECTURA, CALIFICACION, recortes={7: "r7"})
        registro.registrar_lectura("h-2", "t-2", "P1", LECTURA, None, motivo_sin_nota=SIN_CLAVE)
        registro.registrar_lectura_imposible("h-3", "t-3", "P1", "marcas_no_encontradas")
        registro.registrar_lectura_imposible("h-9", "t-9", "OTRO", "marcas_no_encontradas")

    en_disco, en_postgres = (_sin_momento(r.hechos_del_examen("P1")) for r in registros)

    assert en_postgres == en_disco
    assert [hecho["hoja_id"] for hecho in en_postgres] == ["h-1", "h-2", "h-3"]
    assert ResultadosEnPostgres(url).hechos_del_examen("NADA") == []


@con_base
def test_resultados_guarda_la_nota_en_su_columna(url):
    import psycopg

    ResultadosEnPostgres(url).registrar_lectura("h-1", "t-1", "P1", LECTURA, CALIFICACION)
    with psycopg.connect(url) as conexion:
        fila = conexion.execute(
            "SELECT estado, nota_en_decimas, provisional FROM resultados_de_lectura"
        ).fetchone()
    assert fila == ("en_revision", 40, True)


@con_base
def test_una_hoja_leida_sin_nota_y_sin_motivo_no_se_registra(url):
    with pytest.raises(ValueError):
        ResultadosEnPostgres(url).registrar_lectura("h-1", "t-1", "P1", LECTURA, None)


@con_base
def test_revisiones_devuelve_lo_mismo_que_en_disco(url, tmp_path):
    def resolucion(numero, veredicto, opcion):
        return ResolucionDelProfesor(numero, veredicto, opcion, por="Docente", en=EN)

    registros = [RevisionesEnDisco(tmp_path / "v.jsonl"), RevisionesEnPostgres(url)]
    for registro in registros:
        registro.registrar_resoluciones("h-1", "P1", [resolucion(7, CORRECTA, "C")])
        registro.registrar_resoluciones("h-2", "P1", [resolucion(3, INCORRECTA, None)])
        registro.registrar_resoluciones("h-1", "P1", [resolucion(7, INCORRECTA, "B")])
        registro.registrar_resoluciones("h-9", "OTRO", [resolucion(1, CORRECTA, "A")])

    en_disco, en_postgres = (r.resoluciones_del_examen("P1") for r in registros)

    assert en_postgres == en_disco
    assert len(en_postgres["h-1"]) == 2
    with pytest.raises(ValueError):
        RevisionesEnPostgres(url).registrar_resoluciones("h-1", "P1", [])


@con_base
def test_bitacora_devuelve_lo_mismo_que_en_disco(url, tmp_path):
    bitacoras = [BitacoraEnDisco(tmp_path / "b.jsonl"), BitacoraEnPostgres(url)]
    for bitacora in bitacoras:
        for n in (1, 2, 3):
            bitacora.registrar(_entrada(n))
        bitacora.registrar(_entrada(4, "OTRO"))
        bitacora.confirmar_encolada("t-2")

    en_disco, en_postgres = bitacoras

    assert en_postgres.pendientes() == en_disco.pendientes()
    assert [e.trabajo_id for e in en_postgres.pendientes()] == ["t-1", "t-3", "t-4"]
    recepciones = en_postgres.recepciones_del_examen("P1")
    assert {h: r.nombre_archivo for h, r in recepciones.items()} == {
        h: r.nombre_archivo for h, r in en_disco.recepciones_del_examen("P1").items()
    }
    assert all(r.recibida_en is not None for r in recepciones.values())


@con_base
def test_los_datos_sobreviven_a_otro_objeto(url):
    """Lo que en disco era releer el archivo: otro proceso ve lo que el primero confirmó."""
    BitacoraEnPostgres(url).registrar(_entrada(1))
    assert [e.trabajo_id for e in BitacoraEnPostgres(url).pendientes()] == ["t-1"]


@con_base
def test_cien_operaciones_no_abren_cien_conexiones(url, monkeypatch):
    """Con una conexión por operación, un lote de 200 hojas tardó 8,8 s en confirmarse con la API
    en media CPU y pasó el plazo de 8 s de la recepción: 55 hojas quedaron pendientes de encolar.
    Las conexiones se reusan."""
    import infraestructura.base_de_datos as base

    abiertas = []
    conectar = base.psycopg.connect

    def contar(*args, **kwargs):
        abiertas.append(1)
        return conectar(*args, **kwargs)

    monkeypatch.setattr(base.psycopg, "connect", contar)
    bitacora = BitacoraEnPostgres(url)
    for n in range(50):
        bitacora.registrar(_entrada(n))
        bitacora.confirmar_encolada(f"t-{n}")

    assert len(abiertas) <= 2


@con_base
def test_si_la_base_corta_una_conexion_la_siguiente_operacion_abre_otra(url):
    """Una conexión guardada puede morir si la base se reinicia; la siguiente operación no debe
    fallar por eso."""
    import psycopg

    bitacora = BitacoraEnPostgres(url)
    bitacora.registrar(_entrada(1))
    with psycopg.connect(url, autocommit=True) as administracion:
        administracion.execute(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity"
            " WHERE datname = current_database() AND pid <> pg_backend_pid()"
        )
    bitacora.registrar(_entrada(2))

    assert [e.trabajo_id for e in bitacora.pendientes()] == ["t-1", "t-2"]


def test_sin_base_el_fallo_sube_como_oserror_para_que_el_worker_reintente():
    registro = ResultadosEnPostgres("postgresql://nadie@127.0.0.1:1/nada")
    with pytest.raises(OSError):
        registro.registrar_lectura_imposible("h-1", "t-1", "P1", "x")
