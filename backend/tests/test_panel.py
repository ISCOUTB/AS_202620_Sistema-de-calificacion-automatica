"""Las cifras del panel de un examen (RF-05, ADR-0028): `dashboard.panel_del_examen` y la ruta
`GET /examenes/{examen_id}/panel` que la publica.

Las hojas son sintéticas y las lee el OMR de verdad; los hechos se escriben con el mismo registro
que usa el worker, y la revisión del profesor con la misma función que la ruta. Así el panel se
prueba con la forma exacta que tienen los datos en el servidor.

El examen tiene 40 preguntas con la clave A, B, C, D, A...:

- h-1: todo bien. Nota 5,0.
- h-2: bien de la 1 a la 20 y mal de la 21 a la 40 (la letra siguiente). Nota 2,5.
- h-3: la 7 marcada a medias (dudosa), la 8 con dos marcas, la 9 en blanco y el resto bien.
  37 de 40: nota 4,6, provisional.
- h-4: ilegible.
- h-5: leída sin clave, con la 7 a medias.
- h-6: recibida y todavía sin leer.
"""

import statistics
from collections.abc import Iterator
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from api.main import (
    app,
    obtener_lector_de_recepciones,
    obtener_lector_de_resultados,
    obtener_revisiones,
)
from calificacion import calificar, resolver_preguntas
from dashboard import panel_del_examen
from herramientas.hojas_sinteticas import fotografiar, hoja_marcada, patron
from infraestructura.bitacora import BitacoraEnMemoria
from infraestructura.modelo import (
    ClaveDeRespuestas,
    EntradaDeBitacora,
    Habilitacion,
    PreguntaDeLaClave,
)
from infraestructura.resultados import SIN_CLAVE, ResultadosEnDisco
from infraestructura.revisiones import RevisionesEnDisco
from omr import leer_hoja

EXAMEN = "000001"
CODIGO = "20261123"
EN = datetime(2026, 11, 23, 9, 0, tzinfo=timezone.utc)
CLAVE = ClaveDeRespuestas(
    EXAMEN,
    tuple(PreguntaDeLaClave(n, patron(n)) for n in range(1, 41)),
    Habilitacion(por="ana@utb.edu.co", en=EN),
)


def _siguiente(letra: str) -> str:
    return "ABCD"[("ABCD".index(letra) + 1) % 4]


def _leer(respuestas: dict[int, str], a_medias=()):
    return leer_hoja(fotografiar(hoja_marcada(respuestas, CODIGO, a_medias=a_medias)), 70)


@pytest.fixture(scope="module")
def lecturas():
    todas = {n: patron(n) for n in range(1, 41)}
    mitad = {n: patron(n) if n <= 20 else _siguiente(patron(n)) for n in range(1, 41)}
    con_problemas = {n: patron(n) for n in range(1, 41) if n not in (7, 9)}
    con_problemas[8] = "AB"
    return {
        "h-1": _leer(todas),
        "h-2": _leer(mitad),
        "h-3": _leer(con_problemas, a_medias=((7, "C"),)),
        "h-5": _leer({n: patron(n) for n in range(1, 41) if n != 7}, a_medias=((7, "C"),)),
    }


@pytest.fixture
def registros(tmp_path, lecturas):
    resultados = ResultadosEnDisco(tmp_path / "resultados.jsonl")
    for hoja in ("h-1", "h-2", "h-3"):
        lectura = lecturas[hoja]
        resultados.registrar_lectura(hoja, f"t{hoja}", EXAMEN, lectura, calificar(lectura, CLAVE))
    resultados.registrar_lectura_imposible("h-4", "t-h-4", EXAMEN, "imagen_ilegible")
    resultados.registrar_lectura("h-5", "t-h-5", EXAMEN, lecturas["h-5"], None, SIN_CLAVE)
    # Otra hoja de otro examen, que no cuenta.
    resultados.registrar_lectura("h-9", "t-h-9", "000002", lecturas["h-1"], None, SIN_CLAVE)
    recepciones = BitacoraEnMemoria()
    for n in range(1, 7):
        recepciones.registrar(
            EntradaDeBitacora(f"t-h-{n}", EXAMEN, f"{EXAMEN}/h{n}.jpg", f"h{n}.jpg", f"h-{n}")
        )
    revisiones = RevisionesEnDisco(tmp_path / "revisiones.jsonl")
    return resultados, revisiones, recepciones


def test_la_lectura_de_las_hojas_sinteticas_es_la_que_el_panel_supone(lecturas):
    """Si el OMR cambiara, esta prueba lo dice antes que las cifras."""
    estados = {p.numero: p.estado for p in lecturas["h-3"].preguntas}
    assert (estados[7], estados[8], estados[9]) == ("dudosa", "doble_marca", "sin_marca")


def test_el_resumen_cuenta_las_hojas_y_las_notas(registros):
    panel = panel_del_examen(EXAMEN, *registros)
    resumen = panel.resumen

    assert panel.notas_en_decimas == (25, 46, 50)
    assert (resumen.hojas_recibidas, resumen.hojas_leidas, resumen.hojas_con_nota) == (6, 5, 3)
    assert (resumen.hojas_sin_nota, resumen.hojas_ilegibles) == (1, 1)
    # h-3 espera por la 7 y la 8; h-5, sin clave, por la 7.
    assert (resumen.hojas_en_revision, resumen.preguntas_por_revisar) == (2, 3)
    assert resumen.aprobados == 2
    assert resumen.promedio_en_decimas == round(statistics.mean([25, 46, 50]), 2)
    assert resumen.desviacion_en_decimas == round(statistics.pstdev([25, 46, 50]), 2)
    assert resumen.nota_aprobatoria_en_decimas == 30


def test_cada_pregunta_de_cada_hoja_con_nota_queda_en_una_sola_categoria(registros):
    marcas = panel_del_examen(EXAMEN, *registros).marcas

    assert (marcas.correctas, marcas.incorrectas) == (40 + 20 + 37, 20)
    assert (marcas.tenues_o_dudosas, marcas.dobles, marcas.en_blanco) == (1, 1, 1)
    assert marcas.total == 3 * 40
    assert marcas.pendientes == 2


def test_los_aciertos_por_pregunta_dicen_que_marco_el_grupo(registros):
    preguntas = {p.numero: p for p in panel_del_examen(EXAMEN, *registros).preguntas}

    assert len(preguntas) == 40
    assert (preguntas[1].aciertos, preguntas[1].hojas) == (3, 3)
    # La 21 es A: h-1 y h-3 la aciertan, h-2 marcó B.
    assert (preguntas[21].correcta, preguntas[21].aciertos) == ("A", 2)
    assert preguntas[21].marcadas == {"A": 2, "B": 1, "C": 0, "D": 0}
    # La 9 quedó en blanco en h-3.
    assert (preguntas[9].aciertos, preguntas[9].en_blanco) == (2, 1)
    assert (preguntas[8].dobles, preguntas[7].dudosas) == (1, 1)


def test_lo_que_resuelve_el_profesor_sube_la_nota_y_baja_lo_pendiente(registros):
    resultados, revisiones, recepciones = registros
    resolver_preguntas(EXAMEN, "h-3", {7: "C"}, "ana@utb.edu.co", EN, resultados, revisiones)

    panel = panel_del_examen(EXAMEN, resultados, revisiones, recepciones)

    # 38 de 40 = 4,75, que redondea a 4,8.
    assert panel.notas_en_decimas == (25, 48, 50)
    assert panel.marcas.pendientes == 1
    # La categoría describe cómo se marcó la hoja: la 7 sigue siendo dudosa.
    assert panel.marcas.tenues_o_dudosas == 1
    preguntas = {p.numero: p for p in panel.preguntas}
    assert preguntas[7].aciertos == 3


def test_un_examen_sin_hojas_tiene_todo_en_cero_y_sin_promedio(tmp_path):
    panel = panel_del_examen(
        EXAMEN,
        ResultadosEnDisco(tmp_path / "r.jsonl"),
        RevisionesEnDisco(tmp_path / "v.jsonl"),
        BitacoraEnMemoria(),
    )

    assert panel.notas_en_decimas == ()
    assert panel.resumen.promedio_en_decimas is None
    assert panel.resumen.desviacion_en_decimas is None
    assert panel.marcas.total == 0
    assert panel.preguntas == ()


@pytest.fixture
def cliente(registros) -> Iterator[TestClient]:
    resultados, revisiones, recepciones = registros
    sustituciones = {
        obtener_lector_de_resultados: lambda: resultados,
        obtener_revisiones: lambda: revisiones,
        obtener_lector_de_recepciones: lambda: recepciones,
    }
    app.dependency_overrides.update(sustituciones)
    yield TestClient(app)
    for dependencia in sustituciones:
        app.dependency_overrides.pop(dependencia, None)


def test_la_ruta_publica_el_panel_sin_codigos_ni_archivos(cliente):
    respuesta = cliente.get(f"/examenes/{EXAMEN}/panel")

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["examen_id"] == EXAMEN
    assert cuerpo["notas_en_decimas"] == [25, 46, 50]
    assert cuerpo["resumen"]["hojas_recibidas"] == 6
    assert cuerpo["marcas"]["dobles"] == 1
    assert len(cuerpo["preguntas"]) == 40
    assert CODIGO not in respuesta.text
    assert "h1.jpg" not in respuesta.text
