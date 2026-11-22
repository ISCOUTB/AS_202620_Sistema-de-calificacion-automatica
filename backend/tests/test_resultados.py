"""El registro provisional de lo que el worker leyó y calificó (`infraestructura.resultados`).

Es de solo agregado, como la bitácora: cada hoja procesada es un hecho nuevo, con el estado en
que la dejó, y nada se reescribe."""

import json

import pytest

from infraestructura.modelo import (
    CALIFICADA,
    CODIGO_COMPLETO,
    EN_REVISION,
    ILEGIBLE,
    SIN_CLAVE_HABILITADA,
    CalificacionDeHoja,
    LecturaDeHoja,
    LecturaDelCodigo,
)
from infraestructura.resultados import SIN_CLAVE, ResultadosEnDisco, estado_tras_la_lectura

LECTURA = LecturaDeHoja(
    version_del_formato="quantia-hoja-v1",
    codigo=LecturaDelCodigo(CODIGO_COMPLETO, "T12345678"),
    preguntas=(),
    umbral_de_confianza=70,
    duracion_ms=12.5,
)


def _calificacion(provisional: bool) -> CalificacionDeHoja:
    return CalificacionDeHoja(
        examen_id="examen-sintetico",
        nota_en_decimas=40,
        puntos=4.0,
        puntos_posibles=5.0,
        provisional=provisional,
        codigo_por_revisar=False,
        preguntas=(),
    )


def _lineas(ruta) -> list[dict]:
    return [json.loads(linea) for linea in ruta.read_text(encoding="utf-8").splitlines()]


@pytest.mark.parametrize(
    "calificacion, estado",
    [(None, SIN_CLAVE_HABILITADA), (_calificacion(True), EN_REVISION),
     (_calificacion(False), CALIFICADA)],
)
def test_el_estado_de_una_hoja_leida_sale_de_su_calificacion(calificacion, estado):
    assert estado_tras_la_lectura(calificacion) == estado


def test_una_hoja_calificada_queda_con_su_lectura_y_su_nota(tmp_path):
    ruta = tmp_path / "resultados" / "resultados.jsonl"

    ResultadosEnDisco(ruta).registrar_lectura(
        "h-1", "t-1", "examen-sintetico", LECTURA, _calificacion(False)
    )

    [hecho] = _lineas(ruta)
    assert hecho["hecho"] == "leida"
    assert (hecho["hoja_id"], hecho["trabajo_id"], hecho["examen_id"]) == (
        "h-1", "t-1", "examen-sintetico"
    )
    assert hecho["estado"] == CALIFICADA
    assert hecho["calificacion"]["nota_en_decimas"] == 40
    # El registro sí guarda el código: sin él no se sabe de quién es la nota.
    assert hecho["lectura"]["codigo"]["valor"] == "T12345678"


def test_una_hoja_sin_nota_guarda_el_motivo(tmp_path):
    ruta = tmp_path / "resultados.jsonl"

    ResultadosEnDisco(ruta).registrar_lectura(
        "h-1", "t-1", "examen-sintetico", LECTURA, None, SIN_CLAVE
    )

    [hecho] = _lineas(ruta)
    assert (hecho["estado"], hecho["motivo_sin_nota"], hecho["calificacion"]) == (
        SIN_CLAVE_HABILITADA, SIN_CLAVE, None
    )


@pytest.mark.parametrize(
    "calificacion, motivo", [(None, None), (_calificacion(False), SIN_CLAVE)]
)
def test_lleva_nota_o_motivo_para_no_tenerla_pero_no_ambos(tmp_path, calificacion, motivo):
    with pytest.raises(ValueError):
        ResultadosEnDisco(tmp_path / "r.jsonl").registrar_lectura(
            "h-1", "t-1", "examen-sintetico", LECTURA, calificacion, motivo
        )


def test_una_hoja_ilegible_queda_con_el_motivo_de_omr(tmp_path):
    ruta = tmp_path / "resultados.jsonl"

    ResultadosEnDisco(ruta).registrar_lectura_imposible(
        "h-1", "t-1", "examen-sintetico", "marcas_de_registro_no_encontradas"
    )

    [hecho] = _lineas(ruta)
    assert (hecho["hecho"], hecho["estado"], hecho["motivo"]) == (
        "ilegible", ILEGIBLE, "marcas_de_registro_no_encontradas"
    )


def test_volver_a_procesar_agrega_un_hecho_y_no_toca_el_anterior(tmp_path):
    ruta = tmp_path / "resultados.jsonl"
    registro = ResultadosEnDisco(ruta)
    registro.registrar_lectura("h-1", "t-1", "examen-sintetico", LECTURA, None, SIN_CLAVE)
    primera = ruta.read_text(encoding="utf-8")

    registro.registrar_lectura("h-1", "t-2", "examen-sintetico", LECTURA, _calificacion(False))

    assert ruta.read_text(encoding="utf-8").startswith(primera)
    assert [h["estado"] for h in _lineas(ruta)] == [SIN_CLAVE_HABILITADA, CALIFICADA]


# --- La lectura del registro (lo que consulta la API) ------------------------------------------


def test_se_leen_los_hechos_de_un_examen_en_orden_y_solo_los_suyos(tmp_path):
    registro = ResultadosEnDisco(tmp_path / "resultados.jsonl")
    registro.registrar_lectura_imposible("h-1", "t-1", "examen-sintetico", "imagen_ilegible")
    registro.registrar_lectura("h-9", "t-9", "otro-examen", LECTURA, None, SIN_CLAVE)
    registro.registrar_lectura("h-1", "t-2", "examen-sintetico", LECTURA, _calificacion(False))

    hechos = registro.hechos_del_examen("examen-sintetico")

    assert [(h["hoja_id"], h["trabajo_id"]) for h in hechos] == [("h-1", "t-1"), ("h-1", "t-2")]


def test_una_linea_a_medio_escribir_se_salta_y_sin_registro_no_hay_hechos(tmp_path):
    """El worker escribe en otro proceso: la API puede leer justo cuando la última línea todavía
    no está completa."""
    ruta = tmp_path / "resultados.jsonl"
    registro = ResultadosEnDisco(ruta)
    assert registro.hechos_del_examen("examen-sintetico") == []

    registro.registrar_lectura("h-1", "t-1", "examen-sintetico", LECTURA, _calificacion(False))
    with open(ruta, "a", encoding="utf-8") as archivo:
        archivo.write('{"hecho": "leida", "hoja_id": "h-2", "examen_id": "examen-sintetico", "est')

    assert [h["hoja_id"] for h in registro.hechos_del_examen("examen-sintetico")] == ["h-1"]
