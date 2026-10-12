"""Presupuesto de solicitudes al proveedor de LLM (escenario del segundo corte, EC-09, ADR-0015).

`POST /distractores` es pública y cada solicitud gasta cuota del proveedor (R-17). La línea base
medida en el entorno desplegado (`docs/evidencia/presupuesto-antes.json`) mostró que una sola
ráfaga de 20 solicitudes llega entera al proveedor y agota su límite por minuto: 8 de las 20 se
cortaron con un 503 por cuota, y durante ese minuto ningún profesor pudo pedir distractores.

Este archivo pone el freno del lado del sistema: antes de salir a la red, cada solicitud tiene que
caber en dos ventanas deslizantes, una de un minuto y otra de veinticuatro horas. Si no cabe, la
solicitud se rechaza sin tocar al proveedor y se dice cuántos segundos faltan para que haya cupo.

Dos decisiones de forma:

1. **Es un adaptador del puerto, no un cambio de la regla.** `GeneradorConPresupuesto` implementa
   `GeneradorDeDistractores` envolviendo al adaptador real: la regla de `distractores.py` y el
   adaptador de `proveedor_llm.py` no se enteran de que existe.
2. **Cuenta solicitudes enviadas, no tokens.** Los tokens solo se conocen cuando el proveedor ya
   respondió, y para entonces ya se gastaron. Los límites por omisión salen del peor caso medido
   en la evaluación de EC-08 (1 323 tokens por solicitud): 6 por minuto son como mucho 7 938
   tokens, debajo de los 8 000 por minuto de Groq, y 150 por día son como mucho 198 450, debajo de
   los 200 000 por día.

Vive en memoria del proceso: es correcto con la única instancia de la API que hay hoy (ADR-0009) y
se vacía con cada reinicio. Los dos límites de eso están en la sección 11 del arc42 (R-18).

Solo depende de la biblioteca estándar.
"""

import math
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone

from autoria.distractores import (
    DistractorPropuesto,
    GeneradorDeDistractores,
    PreguntaParaDistractores,
)

__all__ = [
    "EstadoDelPresupuesto",
    "PresupuestoAgotado",
    "PresupuestoDeSolicitudes",
    "GeneradorConPresupuesto",
    "SOLICITUDES_POR_MINUTO",
    "SOLICITUDES_POR_DIA",
]

SOLICITUDES_POR_MINUTO = 6
SOLICITUDES_POR_DIA = 150

_UN_MINUTO = 60.0
_UN_DIA = 24 * 60 * 60.0


@dataclass(frozen=True)
class EstadoDelPresupuesto:
    """Cuánto del presupuesto se ha usado, para `GET /metricas` y para el registro.

    `usadas_en_el_ultimo_minuto` y `usadas_en_las_ultimas_24_horas` son las ventanas deslizantes
    que deciden si una solicitud cabe. Los dos contadores `desde_el_arranque` no deciden nada: son
    la observabilidad del escenario, y vuelven a cero cuando el proceso se reinicia."""

    limite_por_minuto: int
    limite_por_dia: int
    usadas_en_el_ultimo_minuto: int
    usadas_en_las_ultimas_24_horas: int
    enviadas_desde_el_arranque: int
    rechazadas_desde_el_arranque: int
    arrancado_en: datetime


class PresupuestoAgotado(Exception):
    """La solicitud no cabe en el presupuesto y no se envió al proveedor.

    Lleva el motivo redactado para el profesor y los segundos que faltan para que vuelva a haber
    cupo, que la API publica en la cabecera `Retry-After` del 429."""

    def __init__(self, motivo: str, reintentar_en_segundos: int, ventana: str) -> None:
        super().__init__(motivo)
        self.motivo = motivo
        self.reintentar_en_segundos = reintentar_en_segundos
        self.ventana = ventana


class PresupuestoDeSolicitudes:
    """Dos ventanas deslizantes, de un minuto y de veinticuatro horas, sobre las solicitudes
    enviadas al proveedor.

    `reservar` es atómica: la ruta de distractores es una función `def` que FastAPI corre en su
    grupo de hilos, así que dos solicitudes pueden llegar a la vez, y sin el candado las dos
    podrían ver el último cupo libre. `reloj` existe para las pruebas: con un reloj falso se
    comprueban las ventanas sin esperar un minuto."""

    def __init__(
        self,
        por_minuto: int = SOLICITUDES_POR_MINUTO,
        por_dia: int = SOLICITUDES_POR_DIA,
        reloj: Callable[[], float] = time.monotonic,
    ) -> None:
        if por_minuto < 1 or por_dia < 1:
            raise ValueError("Los límites del presupuesto tienen que ser de al menos 1.")
        self._por_minuto = por_minuto
        self._por_dia = por_dia
        self._reloj = reloj
        self._candado = threading.Lock()
        self._en_el_minuto: deque[float] = deque()
        self._en_el_dia: deque[float] = deque()
        self._enviadas = 0
        self._rechazadas = 0
        self._arrancado_en = datetime.now(timezone.utc)

    def _olvidar_lo_vencido(self, ahora: float) -> None:
        while self._en_el_minuto and ahora - self._en_el_minuto[0] >= _UN_MINUTO:
            self._en_el_minuto.popleft()
        while self._en_el_dia and ahora - self._en_el_dia[0] >= _UN_DIA:
            self._en_el_dia.popleft()

    def reservar(self) -> None:
        """Reserva un cupo para una solicitud, o levanta `PresupuestoAgotado` sin reservar nada.

        Se revisa primero el límite por día: si los dos están llenos, el profesor necesita saber
        que no hay cupo hasta mañana, no que falta un minuto."""
        with self._candado:
            ahora = self._reloj()
            self._olvidar_lo_vencido(ahora)
            if len(self._en_el_dia) >= self._por_dia:
                self._rechazadas += 1
                segundos = _segundos_hasta_que_venza(self._en_el_dia[0], _UN_DIA, ahora)
                raise PresupuestoAgotado(
                    f"Se agotó el presupuesto diario de {self._por_dia} solicitudes al "
                    f"proveedor. Habrá cupo en unos {math.ceil(segundos / 3600)} h; mientras "
                    "tanto, los distractores se pueden escribir a mano.",
                    segundos,
                    "dia",
                )
            if len(self._en_el_minuto) >= self._por_minuto:
                self._rechazadas += 1
                segundos = _segundos_hasta_que_venza(self._en_el_minuto[0], _UN_MINUTO, ahora)
                raise PresupuestoAgotado(
                    f"Se alcanzó el límite de {self._por_minuto} solicitudes por minuto al "
                    f"proveedor. Puede volver a pedirlo en {segundos} s.",
                    segundos,
                    "minuto",
                )
            self._en_el_minuto.append(ahora)
            self._en_el_dia.append(ahora)
            self._enviadas += 1

    def estado(self) -> EstadoDelPresupuesto:
        with self._candado:
            self._olvidar_lo_vencido(self._reloj())
            return EstadoDelPresupuesto(
                limite_por_minuto=self._por_minuto,
                limite_por_dia=self._por_dia,
                usadas_en_el_ultimo_minuto=len(self._en_el_minuto),
                usadas_en_las_ultimas_24_horas=len(self._en_el_dia),
                enviadas_desde_el_arranque=self._enviadas,
                rechazadas_desde_el_arranque=self._rechazadas,
                arrancado_en=self._arrancado_en,
            )


def _segundos_hasta_que_venza(mas_antigua: float, ventana: float, ahora: float) -> int:
    """Segundos enteros hasta que la solicitud más antigua salga de la ventana. Se redondea hacia
    arriba y nunca baja de 1: un `Retry-After: 0` invita a reintentar en el acto y volver a
    chocar."""
    return max(1, math.ceil(mas_antigua + ventana - ahora))


class GeneradorConPresupuesto:
    """Implementa `GeneradorDeDistractores` reservando un cupo antes de delegar.

    Si no hay cupo, levanta `PresupuestoAgotado` y el generador de adentro no se llama: la
    solicitud no sale a la red y no gasta cuota del proveedor. Una solicitud que sí sale cuenta
    aunque el proveedor falle después, porque ya pudo gastar tokens."""

    def __init__(
        self, generador: GeneradorDeDistractores, presupuesto: PresupuestoDeSolicitudes
    ) -> None:
        self._generador = generador
        self._presupuesto = presupuesto

    def proponer(self, pregunta: PreguntaParaDistractores) -> list[DistractorPropuesto]:
        self._presupuesto.reservar()
        return self._generador.proponer(pregunta)
