"""El registro de lo que resuelve el profesor (`infraestructura.revisiones`, RF-08).

Lo escribe solo la API y es de solo agregado, como los otros dos registros. Lo que cuidan estas
pruebas es que relea exactamente lo que se escribió, con quién y cuándo (RF-10), y que una línea
truncada no tumbe la lectura."""

from datetime import datetime, timezone

import pytest

from infraestructura.modelo import CORRECTA, INCORRECTA, ResolucionDelProfesor
from infraestructura.revisiones import RevisionesEnDisco

EN = datetime(2026, 11, 5, 21, 0, tzinfo=timezone.utc)


def _resolucion(numero: int, veredicto: str, opcion: str | None) -> ResolucionDelProfesor:
    return ResolucionDelProfesor(numero, veredicto, opcion, por="Docente de prueba", en=EN)


def test_relee_lo_que_se_escribio_por_hoja_y_en_orden(tmp_path):
    registro = RevisionesEnDisco(tmp_path / "revisiones.jsonl")
    registro.registrar_resoluciones("h-1", "P1", [_resolucion(7, CORRECTA, "C")])
    registro.registrar_resoluciones("h-2", "P1", [_resolucion(3, INCORRECTA, "A")])
    registro.registrar_resoluciones("h-1", "P1", [_resolucion(7, INCORRECTA, "B")])
    registro.registrar_resoluciones("h-9", "OTRO", [_resolucion(1, CORRECTA, "A")])

    resueltas = registro.resoluciones_del_examen("P1")

    assert resueltas == {
        "h-1": (_resolucion(7, CORRECTA, "C"), _resolucion(7, INCORRECTA, "B")),
        "h-2": (_resolucion(3, INCORRECTA, "A"),),
    }


def test_sin_archivo_no_hay_resoluciones(tmp_path):
    assert RevisionesEnDisco(tmp_path / "no-existe.jsonl").resoluciones_del_examen("P1") == {}


def test_una_linea_truncada_se_salta(tmp_path):
    ruta = tmp_path / "revisiones.jsonl"
    registro = RevisionesEnDisco(ruta)
    registro.registrar_resoluciones("h-1", "P1", [_resolucion(7, CORRECTA, "C")])
    with open(ruta, "a", encoding="utf-8") as archivo:
        archivo.write('{"hecho": "resuelta", "examen_id": "P1", "hoja_id": "h-2", "resol')

    assert list(registro.resoluciones_del_examen("P1")) == ["h-1"]


def test_no_se_registra_una_lista_vacia(tmp_path):
    with pytest.raises(ValueError):
        RevisionesEnDisco(tmp_path / "r.jsonl").registrar_resoluciones("h-1", "P1", [])
