"""Prueba 18: el presupuesto de carga y el tope del cuerpo (S13, amenaza AM-01, ADR-0022).

Es la mitigación de la amenaza más alta del modelo de amenazas: la ruta pública de carga no puede
llenar el disco compartido del servidor. Lo que sostiene: un lote con más hojas que el tope, o que
no cabe en el cupo de bytes de las últimas 24 horas, no entra entero, ninguna de sus hojas llega al
almacén ni a la bitácora, y el 429 sabe decir cuándo cabrá. Y ninguna petición de más de 100 MB
llega a la ruta, la declare o no.

El reloj es falso: la ventana de un día se recorre sin esperar. Se validaron provocando la falla,
según la convención del equipo:

- sin la llamada a `reservar` en `cargar_hojas`, fallan cuatro de las cinco pruebas de la ruta
  (las dos del 413, la del 429 y la de `/metricas`); la del lote que cabe sigue en verde, como
  debe;
- sin la comprobación de bytes en `reservar`, fallan cinco: las cuatro de la regla que llenan el
  cupo y la del 429 de la ruta;
- sin `_olvidar_lo_vencido`, falla `test_la_ventana_libera_el_cupo_...`;
- sin la cuenta de bytes del middleware, falla `test_un_cuerpo_sin_content_length_...`;
- sin el middleware en `api/main.py`, falla `test_la_api_tiene_el_tope_...`;
- sin la comprobación del `Content-Length`, las pruebas **siguen en verde**: la cuenta corta el
  mismo cuerpo un poco después, al leerlo. Se deja escrito en vez de fingir que la prueba la cubre:
  la comprobación se conserva porque ahorra leer el cuerpo, no porque esta prueba demuestre que
  hace falta.
"""

from collections.abc import Iterator

import pytest
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

from api.limite_del_cuerpo import MB_DEL_CUERPO, LimiteDelCuerpo
from api.main import (
    app,
    obtener_almacen,
    obtener_bitacora,
    obtener_cliente_cola,
    obtener_presupuesto_de_carga,
)
from infraestructura.almacen import AlmacenEnDisco
from infraestructura.bitacora import BitacoraEnMemoria
from ingesta import (
    HOJAS_POR_LOTE,
    MB_POR_DIA,
    CargaDiariaAgotada,
    LoteDemasiadoGrande,
    PresupuestoDeCarga,
)
from tests.test_presupuesto import RelojFalso
from tests.test_recepcion import JPG, ColaFalsa

UN_MB = 1024 * 1024
UN_DIA = 24 * 60 * 60


# --- La regla, sin la API ---------------------------------------------------------------------


def test_los_topes_por_omision_son_los_del_adr() -> None:
    """250 hojas por lote y 256 MB por día: los números que ADR-0022 justifica. Si alguien los
    cambia aquí, esta prueba obliga a cambiarlos también allá."""
    assert (HOJAS_POR_LOTE, MB_POR_DIA) == (250, 256)


def test_un_lote_con_mas_hojas_que_el_tope_no_reserva_nada() -> None:
    presupuesto = PresupuestoDeCarga(hojas_por_lote=3, mb_por_dia=1)

    with pytest.raises(LoteDemasiadoGrande, match="trae 4 hojas y el máximo es 3"):
        presupuesto.reservar(hojas=4, bytes_del_lote=10)

    estado = presupuesto.estado()
    assert estado.bytes_en_las_ultimas_24_horas == 0
    assert estado.lotes_rechazados_desde_el_arranque == 1
    assert estado.lotes_admitidos_desde_el_arranque == 0


def test_un_lote_mas_pesado_que_el_cupo_de_un_dia_es_demasiado_grande_y_no_espera() -> None:
    """Esperar no lo arregla, así que no es un 429: el docente tiene que dividirlo."""
    presupuesto = PresupuestoDeCarga(hojas_por_lote=10, mb_por_dia=1)

    with pytest.raises(LoteDemasiadoGrande, match="pesa 2 MB y el máximo por día es 1 MB"):
        presupuesto.reservar(hojas=1, bytes_del_lote=2 * UN_MB)


def test_un_lote_que_no_cabe_en_el_dia_se_rechaza_sin_reservar_nada() -> None:
    presupuesto = PresupuestoDeCarga(hojas_por_lote=10, mb_por_dia=1, reloj=RelojFalso())
    presupuesto.reservar(hojas=1, bytes_del_lote=UN_MB // 2)
    presupuesto.reservar(hojas=1, bytes_del_lote=UN_MB // 4)

    with pytest.raises(CargaDiariaAgotada):
        presupuesto.reservar(hojas=1, bytes_del_lote=UN_MB // 2)

    estado = presupuesto.estado()
    assert estado.bytes_en_las_ultimas_24_horas == UN_MB // 2 + UN_MB // 4
    assert estado.lotes_admitidos_desde_el_arranque == 2
    assert estado.lotes_rechazados_desde_el_arranque == 1


def test_el_cupo_se_puede_llenar_hasta_el_ultimo_byte() -> None:
    presupuesto = PresupuestoDeCarga(hojas_por_lote=10, mb_por_dia=1, reloj=RelojFalso())

    presupuesto.reservar(hojas=1, bytes_del_lote=UN_MB)

    with pytest.raises(CargaDiariaAgotada):
        presupuesto.reservar(hojas=1, bytes_del_lote=1)


def test_la_ventana_libera_el_cupo_cuando_el_lote_cumple_un_dia() -> None:
    reloj = RelojFalso()
    presupuesto = PresupuestoDeCarga(hojas_por_lote=10, mb_por_dia=1, reloj=reloj)
    presupuesto.reservar(hojas=1, bytes_del_lote=UN_MB)

    reloj.ahora += UN_DIA - 1
    with pytest.raises(CargaDiariaAgotada):
        presupuesto.reservar(hojas=1, bytes_del_lote=1)

    reloj.ahora += 1
    presupuesto.reservar(hojas=1, bytes_del_lote=UN_MB)
    assert presupuesto.estado().bytes_en_las_ultimas_24_horas == UN_MB


def test_el_429_dice_cuando_cabe_contando_solo_los_lotes_que_hace_falta_que_salgan() -> None:
    """Con tres lotes en la ventana, un lote nuevo que solo necesita que salga el más antiguo
    cabe cuando ese cumpla un día, no cuando cumpla el último."""
    reloj = RelojFalso()
    presupuesto = PresupuestoDeCarga(hojas_por_lote=10, mb_por_dia=1, reloj=reloj)
    presupuesto.reservar(hojas=1, bytes_del_lote=UN_MB // 2)
    reloj.ahora += 3600
    presupuesto.reservar(hojas=1, bytes_del_lote=UN_MB // 4)
    reloj.ahora += 3600
    presupuesto.reservar(hojas=1, bytes_del_lote=UN_MB // 4)

    with pytest.raises(CargaDiariaAgotada) as agotada:
        presupuesto.reservar(hojas=1, bytes_del_lote=UN_MB // 2)

    # El más antiguo entró hace 2 h: cumple un día dentro de 22 h.
    assert agotada.value.reintentar_en_segundos == UN_DIA - 2 * 3600
    assert "en unos 22 h" in agotada.value.motivo


def test_los_limites_tienen_que_ser_de_al_menos_uno() -> None:
    with pytest.raises(ValueError):
        PresupuestoDeCarga(hojas_por_lote=0)
    with pytest.raises(ValueError):
        PresupuestoDeCarga(mb_por_dia=0)


# --- La ruta de carga -------------------------------------------------------------------------


class Ruta:
    """El cliente de la API con un presupuesto propio, y el almacén y la bitácora a la vista,
    para comprobar que un lote cortado no dejó nada en ninguno de los dos."""

    def __init__(self, presupuesto: PresupuestoDeCarga, almacen: AlmacenEnDisco) -> None:
        self.presupuesto = presupuesto
        self.almacen = almacen
        self.bitacora = BitacoraEnMemoria()
        self.cola = ColaFalsa()
        self.cliente = TestClient(app)

    def cargar(self, cantidad: int, contenido: bytes = JPG):
        archivos = [
            ("archivos", (f"hoja-{n}.jpg", contenido, "image/jpeg")) for n in range(cantidad)
        ]
        return self.cliente.post("/examenes/CALC-2026-01/hojas", files=archivos)

    def nada_entro(self) -> bool:
        return (
            not any(self.almacen.raiz.rglob("*.jpg"))
            and not self.bitacora.recibidas
            and not self.cola.empujados
        )


@pytest.fixture
def ruta(tmp_path) -> Iterator[Ruta]:
    ruta = Ruta(PresupuestoDeCarga(hojas_por_lote=3, mb_por_dia=1), AlmacenEnDisco(tmp_path))
    app.dependency_overrides[obtener_presupuesto_de_carga] = lambda: ruta.presupuesto
    app.dependency_overrides[obtener_almacen] = lambda: ruta.almacen
    app.dependency_overrides[obtener_bitacora] = lambda: ruta.bitacora
    app.dependency_overrides[obtener_cliente_cola] = lambda: ruta.cola
    yield ruta
    app.dependency_overrides.clear()


def test_un_lote_dentro_del_tope_entra_como_siempre(ruta: Ruta) -> None:
    respuesta = ruta.cargar(3)

    assert respuesta.status_code == 200
    assert len(respuesta.json()["aceptadas"]) == 3


def test_un_lote_con_mas_hojas_que_el_tope_responde_413_y_no_entra_ninguna(ruta: Ruta) -> None:
    respuesta = ruta.cargar(4)

    assert respuesta.status_code == 413
    assert "trae 4 hojas y el máximo es 3" in respuesta.json()["detail"]
    assert ruta.nada_entro()


def test_un_lote_mas_pesado_que_el_cupo_de_un_dia_responde_413(ruta: Ruta) -> None:
    respuesta = ruta.cargar(1, contenido=JPG + b"\0" * (2 * UN_MB))

    assert respuesta.status_code == 413
    assert ruta.nada_entro()


def test_un_lote_que_no_cabe_en_el_dia_responde_429_con_retry_after(ruta: Ruta) -> None:
    ruta.presupuesto.reservar(hojas=1, bytes_del_lote=UN_MB - 10)

    respuesta = ruta.cargar(1, contenido=JPG + b"\0" * 100)

    assert respuesta.status_code == 429
    assert int(respuesta.headers["Retry-After"]) >= 1
    assert "No entró ninguna hoja" in respuesta.json()["detail"]
    assert ruta.nada_entro()


def test_metricas_publica_lo_cargado_y_lo_cortado(ruta: Ruta) -> None:
    ruta.cargar(2)
    ruta.cargar(4)

    carga = ruta.cliente.get("/metricas").json()["presupuesto_de_carga"]

    assert carga["limite_de_hojas_por_lote"] == 3
    assert carga["limite_de_bytes_por_dia"] == UN_MB
    assert carga["bytes_en_las_ultimas_24_horas"] == 2 * len(JPG)
    assert carga["lotes_admitidos_desde_el_arranque"] == 1
    assert carga["lotes_rechazados_desde_el_arranque"] == 1


# --- El tope del cuerpo de la petición --------------------------------------------------------


def _app_con_tope(maximo_bytes: int) -> tuple[TestClient, list[int]]:
    """Una app mínima detrás del middleware, con un tope chico, y la lista de cuerpos que la ruta
    llegó a leer: si el middleware corta antes, la lista queda vacía."""
    leidos: list[int] = []
    interna = FastAPI()

    @interna.post("/")
    async def leer(request: Request) -> dict[str, int]:
        leidos.append(len(await request.body()))
        return {"bytes": leidos[-1]}

    interna.add_middleware(LimiteDelCuerpo, maximo_bytes=maximo_bytes)
    return TestClient(interna), leidos


def test_un_cuerpo_dentro_del_tope_pasa_entero() -> None:
    cliente, leidos = _app_con_tope(10)

    respuesta = cliente.post("/", content=b"x" * 10)

    assert respuesta.status_code == 200
    assert leidos == [10]


def test_un_content_length_mayor_que_el_tope_responde_413_sin_llegar_a_la_ruta() -> None:
    cliente, leidos = _app_con_tope(10)

    respuesta = cliente.post("/", content=b"x" * 11)

    assert respuesta.status_code == 413
    assert "No entró ninguna hoja" in respuesta.json()["detail"]
    assert leidos == []


def test_un_cuerpo_sin_content_length_se_corta_al_pasar_el_tope() -> None:
    """Es el camino directo al servidor, sin Cloudflare: nadie obliga a declarar el tamaño. Con
    un iterador, el cliente manda el cuerpo por partes y sin `Content-Length`."""
    cliente, leidos = _app_con_tope(10)

    respuesta = cliente.post("/", content=iter([b"x" * 6, b"x" * 6]))

    assert respuesta.status_code == 413
    assert leidos == []


def test_la_api_tiene_el_tope_de_100_mb_por_dentro_de_cors() -> None:
    """Por dentro de CORS, para que el 413 lleve sus cabeceras y el sitio lo pueda leer. Starlette
    pone primero el middleware de más afuera."""
    nombres = [getattr(middleware.cls, "__name__", "") for middleware in app.user_middleware]

    assert nombres.index(CORSMiddleware.__name__) < nombres.index(LimiteDelCuerpo.__name__)
    assert MB_DEL_CUERPO == 100
