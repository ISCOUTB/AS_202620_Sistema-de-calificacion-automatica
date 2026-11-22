"""La herramienta que mide EC-03 y EC-04 (`herramientas/medir_procesamiento.py`).

La medición de verdad corre contra el sistema levantado; aquí se comprueba con un registro escrito a
mano que los tiempos salen de los eventos correctos, y que la clave que escribe la herramienta es
una que el worker sabe leer."""

import json

from herramientas.medir_procesamiento import analizar, clave, hojas_escaneadas, leer_lineas
from infraestructura.claves import ClavesEnDisco
from omr import leer_hoja

REGISTRO = [
    '{"momento": "2026-11-05T03:00:00.000+00:00", "evento": "trabajo_publicado", "trabajo": "t1", '
    '"hoja": "h1", "examen": "LOTE"}',
    '{"momento": "2026-11-05T03:00:00.100+00:00", "evento": "trabajo_publicado", "trabajo": "t2", '
    '"hoja": "h2", "examen": "LOTE"}',
    '{"momento": "2026-11-05T03:00:00.200+00:00", "evento": "lote_confirmado", "examen": "LOTE"}',
    '2026-11-05T03:00:01Z {"momento": "2026-11-05T03:00:01.500+00:00", "evento": '
    '"hoja_procesada", "trabajo": "t1", "examen": "LOTE", "estado": "calificada", '
    '"duracion_lectura_ms": 1200.0}',
    '{"momento": "2026-11-05T03:00:03.100+00:00", "evento": "hoja_procesada", "trabajo": "t2", '
    '"examen": "LOTE", "estado": "en_revision", "duracion_lectura_ms": 1400.0}',
    '{"momento": "2026-11-05T03:00:04.000+00:00", "evento": "trabajo_publicado", "trabajo": "t9", '
    '"hoja": "h9", "examen": "OTRO"}',
    "INFO:     Uvicorn running on http://0.0.0.0:8000",
]


def test_los_tiempos_salen_de_la_publicacion_al_resultado_y_del_lote_a_la_ultima_hoja():
    informe = analizar(leer_lineas(REGISTRO), "LOTE")

    assert (informe["hojas_publicadas"], informe["hojas_procesadas"]) == (2, 2)
    assert informe["estados"] == {"calificada": 1, "en_revision": 1}
    assert informe["por_hoja_ms"]["maximo"] == 3000.0
    assert informe["lote_ms"] == 2900.0
    assert informe["ec04_cumple"]
    # Con un lote en curso, EC-03 no aplica: cada hoja espera detrás de las demás.
    assert "ec03_cumple" not in informe


def test_con_hojas_sueltas_no_hay_cifras_de_lote():
    sueltas = [linea for linea in REGISTRO if "lote_confirmado" not in linea]
    sueltas += [linea.replace("03:00:00.200", "03:00:00.050") for linea in REGISTRO
                if "lote_confirmado" in linea] * 2

    informe = analizar(leer_lineas(sueltas), "LOTE")

    assert "lote_ms" not in informe
    assert informe["ec03_cumple"]


def test_la_clave_que_escribe_la_lee_el_worker(tmp_path):
    (tmp_path / "LOTE.json").write_text(json.dumps(clave("LOTE")), encoding="utf-8")

    leida = ClavesEnDisco(tmp_path).clave_del_examen("LOTE")

    assert leida is not None and leida.habilitacion is not None
    assert len(leida.preguntas) == 40


def test_las_hojas_escaneadas_se_leen():
    [hoja] = hojas_escaneadas(1, semilla=3)

    assert len(leer_hoja(hoja, 70).preguntas) == 40
