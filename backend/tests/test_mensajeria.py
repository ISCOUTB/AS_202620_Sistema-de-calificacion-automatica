"""Prueba 17: el taller de mensajería sobre la cola de trabajos (ADR-0020).

La operación es real: cada hoja aceptada viaja como un mensaje de la API al worker por la cola de
Redis (ADR-0002). Estas pruebas sostienen lo que el taller pide demostrar:

1. **El contrato del mensaje y su compatibilidad.** El archivo versionado es el que genera el
   código; todo mensaje que publica la recepción lo cumple; quien lee ignora los campos que no
   conoce y lee los mensajes anteriores al contrato; una versión desconocida no se reintenta.
2. **Al menos una vez.** Un trabajo que el worker tomó y no confirmó, porque murió, vuelve a la
   cola al arrancar y se procesa.
3. **Duplicados.** Si el worker murió después de procesar y antes de confirmar, la entrega que
   vuelve se confirma sin procesarse otra vez.
4. **Reintentos con espera creciente y lista de fallidos.** Un fallo recuperable se reintenta con
   esperas de 5 y 10 s y se procesa cuando se recupera; uno que no se recupera termina, después de
   cuatro intentos, en la lista de fallidos con el motivo; y desde ahí se puede reencolar.
5. **Seguir un mensaje de productor a consumidor.** Los eventos de la API y del worker llevan el
   mismo `trabajo` y la misma `hoja`, y `herramientas/seguir_trabajo.py` arma el rastro.

Corren contra el Redis del CI (o el de `docker compose up -d redis`) y se saltan con un mensaje si
no hay uno, como `test_encolado.py`: `BLMOVE`, los conjuntos ordenados y las transacciones son lo
que se prueba, y un sustituto en memoria probaría el sustituto. Cada prueba usa una cola con nombre
propio y la borra al terminar.

Validadas provocando la falla, una mutación a la vez:

- el archivo del contrato editado a mano: falla la del contrato versionado;
- `serializar_trabajo` sin el campo `version`: falla la de lo que publica la recepción;
- `leer_trabajo` exigiendo `hoja_id`: falla la de los mensajes anteriores al contrato;
- `recuperar_en_curso` sin devolver nada: fallan la de al menos una vez y la del duplicado, y la de
  Redis que falla a mitad en `test_modos_de_fallo.py`;
- la marca puesta antes de procesar, como en ADR-0016: fallan cuatro, entre ellas la del fallo
  recuperable, porque el reintento se descarta como repetido y la hoja nunca se procesa;
- la marca puesta después del acuse: falla la del duplicado, que se procesa dos veces;
- la espera sin duplicarse: fallan la de las esperas y la del fallo recuperable;
- sin el tope de intentos: fallan la de fallidos y la de reencolar, que reintentan para siempre;
- aceptando cualquier versión del contrato: falla la de la versión desconocida;
- sin el evento `trabajo_publicado`: falla la del rastro.
"""

import json
import logging
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest

import worker.main as worker_main
from herramientas.exportar_contrato import (
    RUTA_CONTRATO_DEL_TRABAJO,
    documento_del_trabajo,
    serializar,
)
from herramientas.seguir_trabajo import leer_eventos, rastro, resumen
from infraestructura.almacen import AlmacenEnDisco
from infraestructura.bitacora import BitacoraEnMemoria
from infraestructura.cola import (
    ESQUEMA_DEL_TRABAJO,
    VERSION_DEL_TRABAJO,
    MensajeInvalido,
    Trabajo,
    leer_trabajo,
    publicar,
    serializar_trabajo,
)
from infraestructura.consumo import (
    ESPERA_BASE_SEGUNDOS,
    MAXIMO_DE_INTENTOS,
    clave_en_curso,
    clave_fallidos,
    clave_reintentos,
    espera_antes_del_intento,
    estado_de_la_cola,
    reencolar_fallidos,
    tomar,
)
from infraestructura.modelo import ArchivoCargado
from infraestructura.registro import FormateadorJSON
from ingesta import recibir_lote

JPG = b"\xff\xd8\xff" + b"\x00" * 32
EXAMEN = "CALC-2026-01"
SIN_AZAR = lambda: 0.0  # noqa: E731 (las esperas exactas: 5, 10, 20 s)


# --- Utilidades --------------------------------------------------------------------------------


def _cumple_el_esquema(valor, esquema: dict, ruta: str = "$") -> list[str]:
    """Un validador mínimo de JSON Schema para lo que usa el contrato del trabajo: `type`,
    `required`, `properties`, `const` y `minimum`. Sin dependencias nuevas (jsonschema no está en
    el lock), y suficiente para comprobar que un mensaje real cumple el archivo publicado."""
    errores: list[str] = []
    tipos = {"object": dict, "string": str, "integer": int}
    if "const" in esquema and valor != esquema["const"]:
        errores.append(f"{ruta}: vale {valor!r} y debe valer {esquema['const']!r}")
    tipo = esquema.get("type")
    if tipo and not isinstance(valor, tipos[tipo]):
        return errores + [f"{ruta}: no es {tipo}"]
    if "minimum" in esquema and valor < esquema["minimum"]:
        errores.append(f"{ruta}: es menor que {esquema['minimum']}")
    if tipo == "object":
        for campo in esquema.get("required", []):
            if campo not in valor:
                errores.append(f"{ruta}: falta {campo}")
        for campo, subesquema in esquema.get("properties", {}).items():
            if campo in valor:
                errores += _cumple_el_esquema(valor[campo], subesquema, f"{ruta}.{campo}")
    return errores


class AlmacenQueFalla:
    """Un almacén en disco que no puede leer las primeras `fallas` veces: un disco ocupado, un
    volumen que todavía no montó. Es el fallo recuperable que el worker reintenta."""

    def __init__(self, raiz: Path, fallas: int) -> None:
        self._real = AlmacenEnDisco(raiz)
        self.fallas = fallas
        self.lecturas = 0

    def guardar(self, examen_id: str, nombre_archivo: str, contenido: bytes) -> str:
        return self._real.guardar(examen_id, nombre_archivo, contenido)

    def leer(self, referencia: str) -> bytes:
        self.lecturas += 1
        if self.lecturas <= self.fallas:
            raise OSError("Recurso temporalmente no disponible")
        return self._real.leer(referencia)


class Reloj:
    def __init__(self) -> None:
        self.ahora = 1_000_000.0

    def __call__(self) -> float:
        return self.ahora


# Los trabajos que cada cola publicó, para borrar sus marcas al terminar: si no, quedan 7 días
# en el Redis de desarrollo o del CI.
_PUBLICADOS: dict[str, list[str]] = {}


@pytest.fixture
def cola(cliente) -> Iterator[str]:
    nombre = f"prueba-mensajeria-{uuid.uuid4()}"
    yield nombre
    marcas = [f"trabajo-visto:{t}" for t in _PUBLICADOS.pop(nombre, [])]
    cliente.delete(nombre, clave_en_curso(nombre), clave_reintentos(nombre),
                   clave_fallidos(nombre), *marcas)


def _publicar_una_hoja(cliente, cola: str, raiz: Path) -> Trabajo:
    """Publica como lo hace la API: por `recibir_lote`, con la hoja guardada en el almacén."""
    resultado = recibir_lote(
        EXAMEN, [ArchivoCargado("h1.jpg", JPG)], AlmacenEnDisco(raiz), cliente, cola,
        BitacoraEnMemoria(),
    )
    [hoja] = resultado.aceptadas
    _PUBLICADOS.setdefault(cola, []).append(hoja.trabajo_id)
    return leer_trabajo(cliente.lindex(cola, -1))


def _eventos(caplog, nombre: str) -> list[logging.LogRecord]:
    return [r for r in caplog.records if getattr(r, "evento", None) == nombre]


# --- 1. El contrato del mensaje ----------------------------------------------------------------


def test_el_contrato_versionado_del_mensaje_es_el_que_genera_el_codigo():
    """Como la prueba de contrato de la API: el archivo de `docs/contrato/` no se edita a mano."""
    assert RUTA_CONTRATO_DEL_TRABAJO.exists(), (
        "Falta el contrato del mensaje. Se genera con 'python -m herramientas.exportar_contrato'."
    )
    assert RUTA_CONTRATO_DEL_TRABAJO.read_text(encoding="utf-8") == serializar(
        documento_del_trabajo()
    )
    assert RUTA_CONTRATO_DEL_TRABAJO.name == f"trabajo-v{VERSION_DEL_TRABAJO}.schema.json"


def test_todo_mensaje_que_publica_la_recepcion_cumple_el_contrato(cliente, cola, tmp_path):
    _publicar_una_hoja(cliente, cola, tmp_path)

    [crudo] = cliente.lrange(cola, 0, -1)
    publicado = json.loads(RUTA_CONTRATO_DEL_TRABAJO.read_text(encoding="utf-8"))

    assert _cumple_el_esquema(json.loads(crudo), publicado) == []


def test_quien_lee_ignora_lo_que_no_conoce_y_lee_los_mensajes_anteriores_al_contrato():
    """Compatibilidad hacia adelante: un productor más nuevo puede agregar campos. Y hacia atrás:
    un mensaje sin versión, publicado antes del taller, se lee como versión 1 y su `id` hace de
    hoja si no trae `hoja_id` (la regla de ADR-0018)."""
    con_un_campo_nuevo = json.loads(serializar_trabajo(Trabajo(
        id="t-1", payload={"hoja_id": "h-1", "referencia": "r", "examen_id": "e",
                           "nombre_archivo": "n", "prioridad": "alta"},
    )))
    con_un_campo_nuevo["origen"] = "api-v2"
    anterior = {"id": "t-2", "payload": {"referencia": "r", "examen_id": "e",
                                         "nombre_archivo": "n"}}

    nuevo = leer_trabajo(json.dumps(con_un_campo_nuevo))
    viejo = leer_trabajo(json.dumps(anterior))

    assert nuevo.payload["hoja_id"] == "h-1"
    assert (viejo.version, viejo.intento, viejo.payload["hoja_id"]) == (1, 1, "t-2")


@pytest.mark.parametrize(
    "texto",
    [
        json.dumps({"id": "t-1", "version": 2, "payload": {"referencia": "r"}}),
        json.dumps({"version": 1, "payload": {"referencia": "r"}}),
        "esto no es JSON",
    ],
    ids=["version-desconocida", "sin-id", "no-es-json"],
)
def test_un_mensaje_fuera_del_contrato_va_a_fallidos_sin_reintentarse(
    texto, cliente, cola, tmp_path, caplog
):
    with pytest.raises(MensajeInvalido):
        leer_trabajo(texto)
    cliente.rpush(cola, texto)

    with caplog.at_level(logging.INFO, logger="worker"):
        resultado = worker_main.atender_una_vez(cliente, cola, AlmacenEnDisco(tmp_path))

    assert resultado == worker_main.FALLIDO
    assert estado_de_la_cola(cliente, cola) == {
        "pendientes": 0, "en_curso": 0, "esperando_reintento": 0, "fallidos": 1,
    }
    [registro] = cliente.lrange(clave_fallidos(cola), 0, -1)
    assert json.loads(registro)["mensaje"] == texto


# --- 2 y 3. Al menos una vez, y el duplicado que eso produce ------------------------------------


def test_un_trabajo_que_quedo_en_curso_vuelve_a_la_cola_al_arrancar_y_se_procesa(
    cliente, cola, tmp_path, caplog
):
    """El worker tomó el trabajo y murió antes de confirmarlo (MF-06, R-22). Antes se perdía: el
    `BLPOP` ya lo había sacado. Ahora sigue en curso, y al arrancar vuelve a la cola."""
    trabajo = _publicar_una_hoja(cliente, cola, tmp_path)
    assert tomar(cliente, cola, timeout=1) is not None  # el worker que muere

    with caplog.at_level(logging.INFO, logger="worker"):
        worker_main._recuperar(cliente, cola)
        resultado = worker_main.atender_una_vez(cliente, cola, AlmacenEnDisco(tmp_path))

    assert resultado == worker_main.PROCESADO
    assert [vars(r)["trabajo"] for r in _eventos(caplog, "hoja_recibida")] == [trabajo.id]
    assert vars(_eventos(caplog, "trabajos_recuperados")[0])["cantidad"] == 1
    assert estado_de_la_cola(cliente, cola)["en_curso"] == 0


def test_si_murio_despues_de_procesar_la_entrega_que_vuelve_no_se_procesa_otra_vez(
    cliente, cola, tmp_path, monkeypatch, caplog
):
    """El caso que la entrega al menos una vez produce: el worker procesó y marcó, y murió antes
    del acuse. Al arrancar, el trabajo vuelve a la cola; la marca hace que solo se confirme."""
    trabajo = _publicar_una_hoja(cliente, cola, tmp_path)

    class _MuerteAntesDelAcuse(Exception):
        pass

    def morir(*_args):
        raise _MuerteAntesDelAcuse

    with monkeypatch.context() as parche:
        parche.setattr(worker_main, "confirmar", morir)
        with pytest.raises(_MuerteAntesDelAcuse):
            worker_main.atender_una_vez(cliente, cola, AlmacenEnDisco(tmp_path))

    caplog.clear()  # lo que registró la vuelta que murió no cuenta
    with caplog.at_level(logging.INFO, logger="worker"):
        worker_main._recuperar(cliente, cola)
        resultado = worker_main.atender_una_vez(cliente, cola, AlmacenEnDisco(tmp_path))

    assert resultado == worker_main.REPETIDO
    assert [vars(r)["trabajo"] for r in _eventos(caplog, "trabajo_repetido")] == [trabajo.id]
    assert _eventos(caplog, "hoja_recibida") == []
    assert estado_de_la_cola(cliente, cola)["en_curso"] == 0


# --- 4. Reintentos con espera creciente y lista de fallidos -------------------------------------


def test_las_esperas_se_duplican_y_varian_como_mucho_un_quinto():
    assert [espera_antes_del_intento(n, SIN_AZAR) for n in (2, 3, 4)] == [5.0, 10.0, 20.0]
    assert espera_antes_del_intento(2, lambda: 1.0) == pytest.approx(ESPERA_BASE_SEGUNDOS * 1.2)


def test_un_fallo_recuperable_se_reintenta_con_espera_y_se_procesa_al_recuperarse(
    cliente, cola, tmp_path, caplog
):
    """La imagen no se puede leer dos veces y a la tercera sí. El trabajo espera 5 s y después
    10 s, fuera de la cola, y se procesa en el tercer intento con el mismo `trabajo_id`."""
    trabajo = _publicar_una_hoja(cliente, cola, tmp_path)
    almacen = AlmacenQueFalla(tmp_path, fallas=2)
    reloj = Reloj()

    def vuelta():
        return worker_main.atender_una_vez(cliente, cola, almacen, reloj=reloj, azar=SIN_AZAR)

    with caplog.at_level(logging.INFO, logger="worker"):
        assert vuelta() == worker_main.REINTENTO
        reloj.ahora += 4.9
        assert vuelta() == worker_main.NADA  # todavía no le toca
        reloj.ahora += 0.1
        assert vuelta() == worker_main.REINTENTO
        reloj.ahora += 10
        assert vuelta() == worker_main.PROCESADO

    esperas = [vars(r)["espera_s"] for r in _eventos(caplog, "reintento_programado")]
    [procesada] = _eventos(caplog, "hoja_recibida")
    assert esperas == [5.0, 10.0]
    assert (vars(procesada)["trabajo"], vars(procesada)["intento"]) == (trabajo.id, 3)
    assert estado_de_la_cola(cliente, cola) == {
        "pendientes": 0, "en_curso": 0, "esperando_reintento": 0, "fallidos": 0,
    }


def test_un_fallo_que_no_se_recupera_termina_en_fallidos_con_el_motivo(
    cliente, cola, tmp_path, caplog
):
    """La imagen no está: es lo que pasaría con los trabajos pendientes después de un despliegue
    en Render, que borra el disco (ADR-0012). Antes el worker los daba por recibidos; ahora, al
    cuarto intento, van a la lista de fallidos con el motivo, y nadie los pierde de vista."""
    trabajo = _publicar_una_hoja(cliente, cola, tmp_path)
    (tmp_path / trabajo.payload["referencia"]).unlink()
    reloj = Reloj()

    with caplog.at_level(logging.INFO, logger="worker"):
        resultados = []
        for _ in range(MAXIMO_DE_INTENTOS):
            resultados.append(worker_main.atender_una_vez(
                cliente, cola, AlmacenEnDisco(tmp_path), reloj=reloj, azar=SIN_AZAR,
            ))
            reloj.ahora += 60

    assert resultados == [worker_main.REINTENTO] * 3 + [worker_main.FALLIDO]
    [registro] = cliente.lrange(clave_fallidos(cola), 0, -1)
    fallido = json.loads(registro)
    assert fallido["intentos"] == MAXIMO_DE_INTENTOS
    assert "FileNotFoundError" in fallido["motivo"]
    assert leer_trabajo(fallido["mensaje"]).id == trabajo.id
    assert estado_de_la_cola(cliente, cola)["en_curso"] == 0


def test_lo_que_esta_en_fallidos_se_puede_reencolar_cuando_se_corrige_la_causa(
    cliente, cola, tmp_path
):
    trabajo = _publicar_una_hoja(cliente, cola, tmp_path)
    ruta = tmp_path / trabajo.payload["referencia"]
    ruta.unlink()
    reloj = Reloj()
    for _ in range(MAXIMO_DE_INTENTOS):
        worker_main.atender_una_vez(cliente, cola, AlmacenEnDisco(tmp_path), reloj=reloj,
                                    azar=SIN_AZAR)
        reloj.ahora += 60
    cliente.rpush(clave_fallidos(cola), json.dumps({"mensaje": "no es JSON", "motivo": "x"}))

    ruta.write_bytes(JPG)  # alguien devolvió la imagen
    assert reencolar_fallidos(cliente, cola) == 1

    assert worker_main.atender_una_vez(cliente, cola, AlmacenEnDisco(tmp_path)) == (
        worker_main.PROCESADO
    )
    # El que no cumple el contrato se queda: reencolarlo lo traería de vuelta al mismo lugar.
    assert estado_de_la_cola(cliente, cola)["fallidos"] == 1


def test_una_referencia_fuera_del_almacen_no_se_reintenta(cliente, cola, tmp_path):
    cliente.rpush(cola, serializar_trabajo(Trabajo(id=str(uuid.uuid4()), payload={
        "hoja_id": "h", "examen_id": "e", "nombre_archivo": "n", "referencia": "../../etc/passwd",
    })))

    assert worker_main.atender_una_vez(cliente, cola, AlmacenEnDisco(tmp_path)) == (
        worker_main.FALLIDO
    )
    assert estado_de_la_cola(cliente, cola)["esperando_reintento"] == 0


# --- 5. Seguir un mensaje de productor a consumidor ---------------------------------------------


def test_un_mensaje_se_sigue_de_la_api_al_worker_con_el_mismo_trabajo_y_la_misma_hoja(
    cliente, cola, tmp_path, caplog
):
    """La métrica de seguimiento: las líneas JSON del registro, de los dos procesos, juntadas por
    `herramientas/seguir_trabajo.py`, cuentan el viaje entero de un mensaje, con un reintento."""
    almacen = AlmacenQueFalla(tmp_path, fallas=1)
    reloj = Reloj()
    with caplog.at_level(logging.INFO):
        trabajo = _publicar_una_hoja(cliente, cola, tmp_path)
        worker_main.atender_una_vez(cliente, cola, almacen, reloj=reloj, azar=SIN_AZAR)
        reloj.ahora += 5
        worker_main.atender_una_vez(cliente, cola, almacen, reloj=reloj, azar=SIN_AZAR)

    lineas = [FormateadorJSON().format(r) for r in caplog.records]
    eventos = rastro(leer_eventos(lineas), trabajo=trabajo.id)
    final = resumen(eventos)

    assert [e["evento"] for e in eventos] == [
        "trabajo_publicado", "trabajo_tomado", "reintento_programado", "trabajo_tomado",
        "hoja_recibida",
    ]
    assert {e["hoja"] for e in eventos} == {trabajo.payload["hoja_id"]}
    assert (final["estado"], final["intentos"]) == ("procesado", 2)
    assert all(e.get("espera_en_cola_ms") is not None
               for e in eventos if e["evento"] == "trabajo_tomado")


def test_el_esquema_del_codigo_exige_los_campos_que_lee_el_consumidor():
    """`leer_trabajo` necesita `id`, `payload` y la `referencia`; el contrato publicado no puede
    exigir menos que eso, o un productor que lo cumpla podría mandar algo que no se lee."""
    assert {"id", "payload"} <= set(ESQUEMA_DEL_TRABAJO["required"])
    assert "referencia" in ESQUEMA_DEL_TRABAJO["properties"]["payload"]["required"]
