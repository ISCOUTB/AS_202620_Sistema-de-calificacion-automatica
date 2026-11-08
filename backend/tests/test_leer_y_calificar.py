"""El paso del worker que lee y califica una hoja (A-02 y A-03) y deja el resultado en el registro.

`leer_hoja_con_recortes` se reemplaza por una lectura fija: estas pruebas son del worker (qué estado sale, qué
queda registrado, qué va al log y qué se reintenta), no de la visión, que tiene las suyas. Lo que
cuidan, además, es que el código del estudiante nunca llegue al log (RNF-12)."""

import json
import logging
import uuid
from datetime import datetime, timezone

import pytest

import worker.main as worker_main
from infraestructura.almacen import AlmacenEnDisco
from infraestructura.claves import ClaveMalEscrita
from infraestructura.cola import Trabajo, publicar
from infraestructura.consumo import clave_en_curso, clave_fallidos, clave_reintentos
from infraestructura.modelo import (
    CALIFICADA,
    CODIGO_COMPLETO,
    DUDOSA,
    EN_REVISION,
    ILEGIBLE,
    SIN_CLAVE_HABILITADA,
    UNA_MARCA,
    ClaveDeRespuestas,
    Habilitacion,
    LecturaDeHoja,
    LecturaDelCodigo,
    LecturaDePregunta,
    PreguntaDeLaClave,
)
from infraestructura.resultados import (
    CLAVE_MAL_ESCRITA,
    CLAVE_SIN_HABILITAR,
    SIN_CLAVE,
    ResultadosEnDisco,
)
from omr import MarcasDeRegistroNoEncontradas
from herramientas.hojas_sinteticas import fotografiar, hoja_marcada, patron

EXAMEN = "examen-sintetico"
CODIGO = "T12345678"
HABILITADA = Habilitacion(por="Docente de prueba", en=datetime(2026, 11, 3, tzinfo=timezone.utc))
TRABAJO = Trabajo(
    id="t-1",
    payload={
        "hoja_id": "h-1",
        "examen_id": EXAMEN,
        "referencia": f"{EXAMEN}/h1.jpg",
        "nombre_archivo": "h1.jpg",
    },
)


def _lectura(*estados: str) -> LecturaDeHoja:
    """Una lectura con una fila por estado; las de una marca marcan la A."""
    return LecturaDeHoja(
        version_del_formato="quantia-hoja-v1",
        codigo=LecturaDelCodigo(CODIGO_COMPLETO, CODIGO),
        preguntas=tuple(
            LecturaDePregunta(n, estado, "A" if estado == UNA_MARCA else None, 90, ())
            for n, estado in enumerate(estados, start=1)
        ),
        umbral_de_confianza=70,
        duracion_ms=840.0,
    )


def _clave(*numeros: int, habilitacion: Habilitacion | None = HABILITADA) -> ClaveDeRespuestas:
    return ClaveDeRespuestas(
        EXAMEN, tuple(PreguntaDeLaClave(n, "A") for n in numeros), habilitacion
    )


class Claves:
    """Una fuente de claves en memoria, o una que falla con el error que se le dé."""

    def __init__(self, clave: ClaveDeRespuestas | None = None, error: Exception | None = None):
        self.clave, self.error = clave, error

    def clave_del_examen(self, examen_id: str) -> ClaveDeRespuestas | None:
        if self.error is not None:
            raise self.error
        return self.clave


class RegistroQueFalla:
    def registrar_lectura(self, *args, **kwargs) -> None:
        raise OSError("disco lleno")

    def registrar_lectura_imposible(self, *args, **kwargs) -> None:
        raise OSError("disco lleno")


@pytest.fixture
def leer(monkeypatch):
    """Fija lo que devuelve (o lanza) la lectura dentro del worker, sin recortes."""

    def fijar(resultado):
        def leer_hoja_con_recortes(
            contenido: bytes, umbral_de_confianza: int
        ) -> tuple[LecturaDeHoja, dict[int, bytes]]:
            if isinstance(resultado, Exception):
                raise resultado
            return resultado, {}

        monkeypatch.setattr(worker_main, "leer_hoja_con_recortes", leer_hoja_con_recortes)

    return fijar


def _procesar(tmp_path, claves, trabajo: Trabajo = TRABAJO):
    ruta = tmp_path / "resultados.jsonl"
    estado = worker_main.leer_y_calificar(b"imagen", trabajo, claves, ResultadosEnDisco(ruta), 70)
    hechos = [json.loads(linea) for linea in ruta.read_text(encoding="utf-8").splitlines()]
    return estado, hechos


def _evento(caplog) -> logging.LogRecord:
    [registro] = [r for r in caplog.records if getattr(r, "evento", None) == "hoja_procesada"]
    return registro


def test_una_hoja_clara_con_clave_habilitada_queda_calificada(tmp_path, leer, caplog):
    leer(_lectura(UNA_MARCA, UNA_MARCA))

    with caplog.at_level(logging.INFO):
        estado, [hecho] = _procesar(tmp_path, Claves(_clave(1, 2)))

    assert estado == hecho["estado"] == CALIFICADA
    assert hecho["calificacion"]["nota_en_decimas"] == 50
    evento = _evento(caplog)
    assert (evento.trabajo, evento.hoja, evento.estado) == ("t-1", "h-1", CALIFICADA)
    assert (evento.nota_en_decimas, evento.por_revisar) == (50, 0)


def test_una_hoja_con_una_dudosa_queda_en_revision(tmp_path, leer, caplog):
    leer(_lectura(UNA_MARCA, DUDOSA))

    with caplog.at_level(logging.INFO):
        estado, [hecho] = _procesar(tmp_path, Claves(_clave(1, 2)))

    assert estado == hecho["estado"] == EN_REVISION
    assert _evento(caplog).por_revisar == 1


@pytest.mark.parametrize(
    "claves, motivo",
    [
        (Claves(None), SIN_CLAVE),
        (Claves(_clave(1, 2, habilitacion=None)), CLAVE_SIN_HABILITAR),
        (Claves(_clave(1, 5)), CLAVE_MAL_ESCRITA),
        (Claves(error=ClaveMalEscrita("no es JSON")), CLAVE_MAL_ESCRITA),
    ],
    ids=["sin-clave", "sin-habilitar", "no-cabe-en-la-hoja", "sin-forma-de-clave"],
)
def test_sin_una_clave_utilizable_la_lectura_se_guarda_sin_nota(tmp_path, leer, claves, motivo):
    leer(_lectura(UNA_MARCA, UNA_MARCA))

    estado, [hecho] = _procesar(tmp_path, claves)

    assert estado == hecho["estado"] == SIN_CLAVE_HABILITADA
    assert hecho["motivo_sin_nota"] == motivo
    assert hecho["lectura"]["preguntas"]


def test_una_clave_mal_escrita_dice_en_el_log_que_corregir(tmp_path, leer, caplog):
    leer(_lectura(UNA_MARCA, UNA_MARCA))

    with caplog.at_level(logging.INFO):
        _procesar(tmp_path, Claves(_clave(1, 5)))

    assert "5" in _evento(caplog).detalle


def test_una_hoja_ilegible_se_registra_con_el_motivo_y_no_se_reintenta(tmp_path, leer, caplog):
    leer(MarcasDeRegistroNoEncontradas("faltan dos marcas"))

    with caplog.at_level(logging.INFO):
        estado, [hecho] = _procesar(tmp_path, Claves(_clave(1, 2)))

    assert estado == hecho["estado"] == ILEGIBLE
    assert hecho["motivo"] == "marcas_de_registro_no_encontradas"
    assert _evento(caplog).motivo == "marcas_de_registro_no_encontradas"


def test_un_fallo_al_escribir_el_registro_sube_para_reintentarse(leer):
    leer(_lectura(UNA_MARCA))

    with pytest.raises(OSError):
        worker_main.leer_y_calificar(b"imagen", TRABAJO, Claves(_clave(1)), RegistroQueFalla(), 70)


def test_un_fallo_al_leer_la_clave_sube_para_reintentarse(tmp_path, leer):
    leer(_lectura(UNA_MARCA))

    with pytest.raises(OSError):
        _procesar(tmp_path, Claves(error=PermissionError("sin permiso")))


def test_un_mensaje_anterior_a_la_identidad_de_la_hoja_usa_el_trabajo(tmp_path, leer):
    leer(_lectura(UNA_MARCA))
    viejo = Trabajo(id="t-viejo", payload={"examen_id": EXAMEN, "referencia": "r"})

    _, [hecho] = _procesar(tmp_path, Claves(_clave(1)), viejo)

    assert hecho["hoja_id"] == "t-viejo"


@pytest.mark.parametrize("estados", [(UNA_MARCA,), (DUDOSA,)])
def test_el_codigo_del_estudiante_nunca_llega_al_log(tmp_path, leer, caplog, estados):
    leer(_lectura(*estados))

    with caplog.at_level(logging.DEBUG):
        _procesar(tmp_path, Claves(_clave(1)))

    assert CODIGO not in caplog.text
    assert all(CODIGO not in str(vars(registro)) for registro in caplog.records)


# --- Con la lectura de verdad -----------------------------------------------------------------


def test_una_hoja_sintetica_pasa_por_omr_y_calificacion_y_queda_calificada(tmp_path):
    """Sin reemplazar nada: la imagen la lee `omr`, la califica `calificacion` y queda en el
    registro. Todas bien menos la 3, con 40 preguntas de peso 1: 39 de 40, nota 4,9."""
    respuestas = {n: patron(n) for n in range(1, 41)}
    respuestas[3] = "A"
    imagen = fotografiar(hoja_marcada(respuestas, "12345678"))
    clave = ClaveDeRespuestas(
        EXAMEN, tuple(PreguntaDeLaClave(n, patron(n)) for n in range(1, 41)), HABILITADA
    )

    estado, [hecho] = _procesar_imagen(tmp_path, imagen, Claves(clave))

    assert estado == hecho["estado"] == CALIFICADA
    assert hecho["calificacion"]["nota_en_decimas"] == 49
    assert hecho["lectura"]["codigo"]["valor"] == CODIGO


def test_la_fila_de_cada_pregunta_en_revision_queda_recortada_en_el_almacen(tmp_path):
    """Lo que el profesor mira para resolverla (RF-08). El registro anota dónde quedó cada
    recorte, por número de pregunta, y el recorte se lee del almacén como un PNG."""
    respuestas = {n: patron(n) for n in range(1, 41) if n != 7}
    imagen = fotografiar(hoja_marcada(respuestas, "12345678", a_medias=((7, "C"),)))
    clave = ClaveDeRespuestas(
        EXAMEN, tuple(PreguntaDeLaClave(n, patron(n)) for n in range(1, 41)), HABILITADA
    )
    almacen = AlmacenEnDisco(tmp_path / "almacen")
    ruta = tmp_path / "resultados.jsonl"

    estado = worker_main.leer_y_calificar(
        imagen, TRABAJO, Claves(clave), ResultadosEnDisco(ruta), 70, almacen
    )

    [hecho] = [json.loads(linea) for linea in ruta.read_text(encoding="utf-8").splitlines()]
    assert estado == EN_REVISION
    assert list(hecho["recortes"]) == ["7"]
    assert almacen.leer(hecho["recortes"]["7"])[:4] == bytes([0x89]) + b"PNG"


def test_una_imagen_que_no_es_una_hoja_queda_ilegible_con_el_motivo(tmp_path):
    estado, [hecho] = _procesar_imagen(tmp_path, b"no es una imagen", Claves(_clave(1)))

    assert estado == hecho["estado"] == ILEGIBLE
    assert hecho["motivo"] == "formato_no_soportado"


def _procesar_imagen(tmp_path, imagen: bytes, claves):
    ruta = tmp_path / "resultados.jsonl"
    estado = worker_main.leer_y_calificar(imagen, TRABAJO, claves, ResultadosEnDisco(ruta), 70)
    return estado, [json.loads(linea) for linea in ruta.read_text(encoding="utf-8").splitlines()]


# --- Dentro del ciclo del worker (con Redis) ----------------------------------------------------


@pytest.fixture
def cola_con_una_hoja(cliente, tmp_path):
    """Una cola de prueba con un trabajo publicado y su imagen en el almacén."""
    nombre = f"prueba-lectura-{uuid.uuid4()}"
    trabajo = Trabajo(id=str(uuid.uuid4()), payload=dict(TRABAJO.payload))
    (tmp_path / EXAMEN).mkdir()
    (tmp_path / EXAMEN / "h1.jpg").write_bytes(b"\xff\xd8\xff" + b"\x00" * 32)
    publicar(cliente, nombre, trabajo)
    yield nombre, trabajo
    cliente.delete(nombre, clave_en_curso(nombre), clave_reintentos(nombre),
                   clave_fallidos(nombre), f"trabajo-visto:{trabajo.id}")


def test_un_error_inesperado_del_lector_va_a_fallidos_y_no_tumba_el_worker(
    cliente, cola_con_una_hoja, tmp_path, leer, caplog
):
    """Si subiera, el worker se caería y al arrancar recuperaría el mismo mensaje: caería siempre."""
    nombre, trabajo = cola_con_una_hoja
    leer(ZeroDivisionError("defecto del lector"))

    with caplog.at_level(logging.INFO):
        resultado = worker_main.atender_una_vez(
            cliente, nombre, AlmacenEnDisco(tmp_path), Claves(_clave(1)), RegistroQueFalla()
        )

    assert resultado == worker_main.FALLIDO
    assert cliente.llen(clave_fallidos(nombre)) == 1
    assert cliente.llen(clave_en_curso(nombre)) == 0
    [evento] = [r for r in caplog.records if getattr(r, "evento", None) == "trabajo_a_fallidos"]
    assert "ZeroDivisionError" in evento.motivo


def test_un_fallo_al_guardar_el_resultado_se_reintenta(cliente, cola_con_una_hoja, tmp_path, leer):
    nombre, _ = cola_con_una_hoja
    leer(_lectura(UNA_MARCA))

    resultado = worker_main.atender_una_vez(
        cliente, nombre, AlmacenEnDisco(tmp_path), Claves(_clave(1)), RegistroQueFalla()
    )

    assert resultado == worker_main.REINTENTO
    assert cliente.zcard(clave_reintentos(nombre)) == 1
