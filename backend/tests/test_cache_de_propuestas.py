"""Prueba 16: la caché de propuestas de distractores y su política de invalidación (ADR-0019).

Una caché que no se invalida bien es peor que no tener caché: devuelve algo viejo con la misma
seguridad con la que devolvería algo nuevo. Estas pruebas sostienen las dos cosas que la caché
promete, la que ahorra y la que no miente:

- **Ahorra.** La misma pregunta, pedida otra vez, no llama al proveedor ni gasta cupo, y se
  responde aunque el presupuesto del minuto esté agotado.
- **No miente.** Cada regla de invalidación de ADR-0019 tiene su prueba: la versión en la clave
  (cambiar de modelo o de instrucciones), la vigencia de 24 horas que leer no renueva, la
  capacidad, «Pedir otras propuestas», que no se guardan fallas ni respuestas vacías, y que la
  regla de qué llega al profesor corre en cada lectura y no queda congelada en lo guardado.

Ninguna sale a la red: el proveedor es un generador falso y el reloj de la caché es de mentira.

Validadas provocando la falla, una mutación por regla: sin leer la caché fallan cinco, entre ellas
las dos de ahorro; con la vigencia renovada al leer falla la de 24 horas; sin la versión en la clave
fallan la del cambio de modelo y la de la clave; leyendo la caché con `otras` falla la de pedir
otras; guardando la lista vacía falla la suya; guardando la respuesta ya filtrada, en vez de lo que
devolvió el proveedor, fallan cuatro, entre ellas la de la regla. Sin el candado, la de los hilos
siguió en verde en 10 de 10 corridas: comprueba que las cuentas cuadran, no que el candado exista,
y por eso no se cuenta como su prueba.
"""

import threading
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

import autoria.distractores
from api.main import (
    app,
    obtener_cache,
    obtener_generador,
    obtener_presupuesto,
    obtener_version_de_las_propuestas,
)
from autoria import (
    CacheDePropuestas,
    DistractorPropuesto,
    PreguntaParaDistractores,
    PresupuestoDeSolicitudes,
    ProveedorNoDisponible,
    ResultadoDePropuesta,
)
from autoria.cache import VIGENCIA_SEGUNDOS, clave_de_la_pregunta

SOLICITUD = {"enunciado": "Derivada de x·sin(x)", "respuesta_correcta": "sin(x) + x·cos(x)"}
OTRA_SOLICITUD = {"enunciado": "Derivada de x²", "respuesta_correcta": "2x"}

PRIMERAS = [
    DistractorPropuesto("cos(x)", "Se omitió la regla del producto"),
    DistractorPropuesto("x·cos(x)", "Se derivó solo el segundo factor"),
]
NUEVAS = [DistractorPropuesto("sin(x)", "Se derivó solo el primer factor")]


class RelojFalso:
    def __init__(self) -> None:
        self.ahora = 1000.0

    def __call__(self) -> float:
        return self.ahora


class GeneradorEnSecuencia:
    """Devuelve una respuesta distinta en cada llamada, o levanta la falla que toque, y cuenta
    cuántas veces lo llamaron: cada llamada es una solicitud que habría salido al proveedor."""

    def __init__(self, *respuestas: list[DistractorPropuesto] | Exception) -> None:
        self._respuestas = list(respuestas)
        self.llamadas = 0

    def proponer(self, pregunta: PreguntaParaDistractores) -> list[DistractorPropuesto]:
        respuesta = self._respuestas[min(self.llamadas, len(self._respuestas) - 1)]
        self.llamadas += 1
        if isinstance(respuesta, Exception):
            raise respuesta
        return list(respuesta)


@pytest.fixture
def presupuesto() -> PresupuestoDeSolicitudes:
    return PresupuestoDeSolicitudes()


@pytest.fixture
def cache() -> CacheDePropuestas:
    return CacheDePropuestas()


@pytest.fixture
def cliente(presupuesto, cache) -> Iterator[TestClient]:
    app.dependency_overrides[obtener_presupuesto] = lambda: presupuesto
    app.dependency_overrides[obtener_cache] = lambda: cache
    app.dependency_overrides[obtener_version_de_las_propuestas] = lambda: "modelo-a:huella-1"
    yield TestClient(app)
    app.dependency_overrides.clear()


def _con_generador(generador: GeneradorEnSecuencia) -> GeneradorEnSecuencia:
    app.dependency_overrides[obtener_generador] = lambda: generador
    return generador


def _expresiones(respuesta) -> list[str]:
    return [d["expresion"] for d in respuesta.json()["distractores"]]


# --- Ahorra ------------------------------------------------------------------------------------


def test_la_misma_pregunta_sale_de_la_cache_sin_llamar_al_proveedor_ni_gastar_cupo(
    cliente, presupuesto
):
    generador = _con_generador(GeneradorEnSecuencia(PRIMERAS, NUEVAS))

    primera = cliente.post("/distractores", json=SOLICITUD)
    # Los espacios de más no cambian la pregunta.
    con_espacios = {**SOLICITUD, "enunciado": " Derivada de  x·sin(x) "}
    segunda = cliente.post("/distractores", json=con_espacios)

    assert primera.status_code == segunda.status_code == 200
    assert primera.json()["desde_la_cache"] is False
    assert segunda.json()["desde_la_cache"] is True
    assert _expresiones(segunda) == _expresiones(primera)
    assert generador.llamadas == 1
    assert presupuesto.estado().enviadas_desde_el_arranque == 1


def test_con_el_cupo_agotado_la_pregunta_repetida_se_responde_igual(cliente):
    """La caché va por fuera del presupuesto: lo que ya se sabe no espera a que haya cupo. Una
    pregunta nueva, en cambio, sí choca con el 429."""
    un_cupo = PresupuestoDeSolicitudes(por_minuto=1, por_dia=150)
    app.dependency_overrides[obtener_presupuesto] = lambda: un_cupo
    _con_generador(GeneradorEnSecuencia(PRIMERAS))

    assert cliente.post("/distractores", json=SOLICITUD).status_code == 200
    assert cliente.post("/distractores", json=SOLICITUD).status_code == 200
    assert cliente.post("/distractores", json=OTRA_SOLICITUD).status_code == 429


# --- No miente ---------------------------------------------------------------------------------


def test_pedir_otras_no_lee_la_cache_y_reemplaza_lo_guardado(cliente):
    generador = _con_generador(GeneradorEnSecuencia(PRIMERAS, NUEVAS))

    cliente.post("/distractores", json=SOLICITUD)
    otras = cliente.post("/distractores", json={**SOLICITUD, "otras": True})
    despues = cliente.post("/distractores", json=SOLICITUD)

    assert otras.json()["desde_la_cache"] is False
    assert _expresiones(otras) == ["sin(x)"]
    assert generador.llamadas == 2
    # La siguiente vez se recibe lo último que se pidió, no lo de antes.
    assert despues.json()["desde_la_cache"] is True
    assert _expresiones(despues) == ["sin(x)"]


def test_cambiar_de_modelo_o_de_instrucciones_invalida_lo_guardado(cliente):
    generador = _con_generador(GeneradorEnSecuencia(PRIMERAS, NUEVAS))
    cliente.post("/distractores", json=SOLICITUD)

    app.dependency_overrides[obtener_version_de_las_propuestas] = lambda: "modelo-b:huella-1"
    respuesta = cliente.post("/distractores", json=SOLICITUD)

    assert respuesta.json()["desde_la_cache"] is False
    assert generador.llamadas == 2


def test_las_instrucciones_entran_en_la_version_de_las_propuestas():
    """La versión que usa la API de verdad lleva el modelo y la huella del texto que se le manda.
    Si alguien quita la huella, cambiar las instrucciones dejaría de invalidar la caché."""
    from api.main import obtener_version_de_las_propuestas as version_real
    from api.settings import LLM_MODELO
    from autoria import HUELLA_DE_LAS_INSTRUCCIONES

    assert version_real() == f"{LLM_MODELO}:{HUELLA_DE_LAS_INSTRUCCIONES}"
    assert len(HUELLA_DE_LAS_INSTRUCCIONES) == 12


def test_una_falla_del_proveedor_no_se_guarda(cliente):
    generador = _con_generador(
        GeneradorEnSecuencia(ProveedorNoDisponible("El proveedor no respondió."), PRIMERAS)
    )

    assert cliente.post("/distractores", json=SOLICITUD).status_code == 503
    segunda = cliente.post("/distractores", json=SOLICITUD)

    assert segunda.status_code == 200
    assert segunda.json()["desde_la_cache"] is False
    assert generador.llamadas == 2


def test_una_respuesta_sin_propuestas_no_se_guarda(cliente):
    generador = _con_generador(GeneradorEnSecuencia([], PRIMERAS))

    cliente.post("/distractores", json=SOLICITUD)
    segunda = cliente.post("/distractores", json=SOLICITUD)

    assert segunda.json()["desde_la_cache"] is False
    assert _expresiones(segunda) == ["cos(x)", "x·cos(x)"]
    assert generador.llamadas == 2


def test_la_regla_corre_en_cada_lectura_y_no_queda_congelada_en_lo_guardado(
    cliente, monkeypatch: pytest.MonkeyPatch
):
    """Se guarda lo que devolvió el proveedor, no lo que pasó la regla. Si la regla cambia (un
    arreglo como los del 19-oct), la respuesta que sale de la caché ya la cumple."""
    _con_generador(GeneradorEnSecuencia(PRIMERAS))
    assert _expresiones(cliente.post("/distractores", json=SOLICITUD)) == ["cos(x)", "x·cos(x)"]

    regla_anterior = autoria.distractores.filtrar_propuestas

    def regla_mas_estricta(pregunta, propuestas) -> ResultadoDePropuesta:
        resultado = regla_anterior(pregunta, propuestas)
        return ResultadoDePropuesta(resultado.propuestos[:1], resultado.descartados)

    monkeypatch.setattr(autoria.distractores, "filtrar_propuestas", regla_mas_estricta)
    respuesta = cliente.post("/distractores", json=SOLICITUD)

    assert respuesta.json()["desde_la_cache"] is True
    assert _expresiones(respuesta) == ["cos(x)"]


def test_una_entrada_vence_a_las_24_horas_y_leerla_no_la_renueva():
    reloj = RelojFalso()
    cache = CacheDePropuestas(reloj=reloj)
    cache.guardar("clave", PRIMERAS)

    reloj.ahora += VIGENCIA_SEGUNDOS - 1
    assert cache.leer("clave") is not None
    reloj.ahora += 1

    assert cache.leer("clave") is None
    assert cache.estado().vencidas == 1
    assert cache.estado().entradas == 0


def test_con_la_cache_llena_sale_la_que_lleva_mas_tiempo_sin_leerse():
    cache = CacheDePropuestas(capacidad=2)
    cache.guardar("a", PRIMERAS)
    cache.guardar("b", PRIMERAS)
    cache.leer("a")

    cache.guardar("c", PRIMERAS)

    assert cache.leer("b") is None
    assert cache.leer("a") is not None
    assert cache.leer("c") is not None
    assert cache.estado().expulsadas == 1


def test_la_clave_ignora_los_espacios_y_distingue_todo_lo_demas():
    pregunta = PreguntaParaDistractores("Derivada de x²", "2x")
    clave = clave_de_la_pregunta(pregunta, "v1")

    con_espacios = PreguntaParaDistractores(" Derivada  de x² ", "2x ")
    assert clave == clave_de_la_pregunta(con_espacios, "v1")
    assert clave != clave_de_la_pregunta(PreguntaParaDistractores("Derivada de x^2", "2x"), "v1")
    assert clave != clave_de_la_pregunta(PreguntaParaDistractores("Derivada de x²", "2x", 4), "v1")
    assert clave != clave_de_la_pregunta(pregunta, "v2")


def test_las_metricas_publican_los_aciertos_y_los_fallos(cliente):
    _con_generador(GeneradorEnSecuencia(PRIMERAS))
    cliente.post("/distractores", json=SOLICITUD)
    cliente.post("/distractores", json=SOLICITUD)
    cliente.post("/distractores", json=SOLICITUD)

    cache = cliente.get("/metricas").json()["cache_de_distractores"]

    assert cache["aciertos"] == 2
    assert cache["fallos"] == 1
    assert cache["guardadas"] == 1
    assert cache["entradas"] == 1
    assert cache["vigencia_segundos"] == VIGENCIA_SEGUNDOS


def test_las_cuentas_cuadran_con_varios_hilos_a_la_vez():
    """La ruta corre en el grupo de hilos de FastAPI. Cada lectura es un acierto o un fallo, y
    ninguna se pierde aunque ocho hilos lean y guarden a la vez."""
    cache = CacheDePropuestas(capacidad=8)
    lecturas_por_hilo = 500

    def trabajar(numero: int) -> None:
        for i in range(lecturas_por_hilo):
            clave = f"{(numero + i) % 12}"
            if cache.leer(clave) is None:
                cache.guardar(clave, PRIMERAS)

    hilos = [threading.Thread(target=trabajar, args=(n,)) for n in range(8)]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join()

    estado = cache.estado()
    assert estado.aciertos + estado.fallos == 8 * lecturas_por_hilo
    assert estado.entradas <= 8
