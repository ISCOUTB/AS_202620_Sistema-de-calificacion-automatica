"""Prueba 12: el presupuesto de solicitudes al proveedor de LLM (EC-09, ADR-0015).

Es la prueba del escenario del segundo corte, de límite de costo. Lo que sostiene: ninguna
solicitud sale al proveedor si no cabe en las dos ventanas deslizantes (un minuto y veinticuatro
horas), la que no cabe se rechaza sin llamar al generador, y el 429 sabe decir cuándo vuelve a
haber cupo.

El reloj es falso: las ventanas se recorren sin esperar un minuto ni un día. Se validaron
provocando la falla, según la convención del equipo:

- sin la comprobación del límite por minuto en `reservar`, fallan cinco de estas y tres de
  `test_ruta_distractores.py`;
- con `GeneradorConPresupuesto` delegando sin reservar, fallan
  `test_el_rechazo_no_llama_al_generador` y las tres de la ruta que dependen del corte;
- sin el candado de `reservar`, la prueba de los cuarenta hilos **sigue en verde**, en 20 de 20
  corridas. Con el GIL la carrera entre la comprobación y el `append` es improbable, y la prueba no
  la provoca. Se deja escrito en vez de fingir que la cubre: el candado se conserva porque la ruta
  corre en el grupo de hilos de FastAPI, no porque esta prueba demuestre que hace falta.
"""

import threading

import pytest

from autoria import (
    DistractorPropuesto,
    GeneradorConPresupuesto,
    PreguntaParaDistractores,
    PresupuestoAgotado,
    PresupuestoDeSolicitudes,
)
from tests.test_distractores import GeneradorFalso

PREGUNTA = PreguntaParaDistractores("Derivada de x²", "2x", cantidad=3)


class RelojFalso:
    """Un reloj que solo avanza cuando la prueba lo dice."""

    def __init__(self) -> None:
        self.ahora = 1000.0

    def __call__(self) -> float:
        return self.ahora

    def avanzar(self, segundos: float) -> None:
        self.ahora += segundos


def _presupuesto(
    por_minuto: int = 6, por_dia: int = 150
) -> tuple[PresupuestoDeSolicitudes, RelojFalso]:
    reloj = RelojFalso()
    return PresupuestoDeSolicitudes(por_minuto=por_minuto, por_dia=por_dia, reloj=reloj), reloj


def test_admite_hasta_el_limite_por_minuto_y_corta_la_siguiente() -> None:
    presupuesto, _ = _presupuesto(por_minuto=6)

    for _ in range(6):
        presupuesto.reservar()
    with pytest.raises(PresupuestoAgotado) as agotado:
        presupuesto.reservar()

    assert agotado.value.ventana == "minuto"
    assert agotado.value.reintentar_en_segundos == 60
    assert "6 solicitudes por minuto" in agotado.value.motivo


def test_el_cupo_vuelve_cuando_la_solicitud_mas_antigua_sale_de_la_ventana() -> None:
    """La ventana es deslizante: no se vacía de golpe a la hora en punto, se libera una
    solicitud a la vez, sesenta segundos después de que salió."""
    presupuesto, reloj = _presupuesto(por_minuto=2)
    presupuesto.reservar()
    reloj.avanzar(20)
    presupuesto.reservar()

    reloj.avanzar(30)
    with pytest.raises(PresupuestoAgotado) as agotado:
        presupuesto.reservar()
    assert agotado.value.reintentar_en_segundos == 10

    reloj.avanzar(10)
    presupuesto.reservar()


def test_el_limite_por_dia_corta_aunque_el_minuto_tenga_cupo() -> None:
    presupuesto, reloj = _presupuesto(por_minuto=6, por_dia=3)
    for _ in range(3):
        presupuesto.reservar()
        reloj.avanzar(61)

    with pytest.raises(PresupuestoAgotado) as agotado:
        presupuesto.reservar()

    assert agotado.value.ventana == "dia"
    assert "diario" in agotado.value.motivo


def test_el_rechazo_no_llama_al_generador() -> None:
    """Lo que el escenario promete: la solicitud cortada no sale a la red, así que no gasta
    cuota del proveedor."""
    presupuesto, _ = _presupuesto(por_minuto=1)
    generador = GeneradorFalso([DistractorPropuesto("x", "Se bajó el exponente sin multiplicar")])
    con_presupuesto = GeneradorConPresupuesto(generador, presupuesto)

    con_presupuesto.proponer(PREGUNTA)
    with pytest.raises(PresupuestoAgotado):
        con_presupuesto.proponer(PREGUNTA)

    assert generador.preguntas == [PREGUNTA]


def test_el_estado_cuenta_lo_enviado_y_lo_cortado() -> None:
    presupuesto, reloj = _presupuesto(por_minuto=2, por_dia=10)
    presupuesto.reservar()
    presupuesto.reservar()
    with pytest.raises(PresupuestoAgotado):
        presupuesto.reservar()
    reloj.avanzar(61)

    estado = presupuesto.estado()

    assert estado.limite_por_minuto == 2
    assert estado.limite_por_dia == 10
    assert estado.usadas_en_el_ultimo_minuto == 0
    assert estado.usadas_en_las_ultimas_24_horas == 2
    assert estado.enviadas_desde_el_arranque == 2
    assert estado.rechazadas_desde_el_arranque == 1


def test_dos_hilos_a_la_vez_no_pasan_del_limite() -> None:
    """La ruta corre en el grupo de hilos de FastAPI. Cuarenta reservas simultáneas contra un
    límite de seis tienen que dejar exactamente seis admitidas. Su alcance está en el docstring
    del archivo: comprueba el resultado, pero no detecta que falte el candado."""
    presupuesto, _ = _presupuesto(por_minuto=6)
    admitidas: list[int] = []
    salida = threading.Barrier(40)

    def intentar() -> None:
        salida.wait()
        try:
            presupuesto.reservar()
        except PresupuestoAgotado:
            return
        admitidas.append(1)

    hilos = [threading.Thread(target=intentar) for _ in range(40)]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join()

    assert len(admitidas) == 6
    assert presupuesto.estado().rechazadas_desde_el_arranque == 34


@pytest.mark.parametrize(("por_minuto", "por_dia"), [(0, 150), (6, 0)])
def test_un_limite_de_cero_es_un_error_de_configuracion(por_minuto: int, por_dia: int) -> None:
    """Un cero en la variable de entorno no puede convertirse en una ruta que nunca responde
    nada más que 429: se rechaza al arrancar."""
    with pytest.raises(ValueError):
        PresupuestoDeSolicitudes(por_minuto=por_minuto, por_dia=por_dia)
