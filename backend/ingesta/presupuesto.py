"""Presupuesto de carga: cuántas hojas caben en un lote y cuántos bytes en un día (S13, ADR-0022).

`POST /examenes/{examen_id}/hojas` es pública y sin autenticación (R-14), y lo que acepta queda en
el volumen del almacén, sobre el disco de 200 GB que comparten los 23 equipos del servidor del
laboratorio (R-31). Hasta la S13 el único tope era el de una hoja (20 MB): nada limitaba cuántas
hojas traía un lote ni cuántos lotes llegaban en un día, así que unas 2 000 peticiones de 100 MB,
lo que deja pasar Cloudflare, llenaban el disco del servidor entero. Es la amenaza AM-01 del modelo
de amenazas, la primera en prioridad.

Este archivo pone dos topes delante del almacén, antes de leer la primera hoja:

1. **Hojas por lote.** Un lote con más hojas que el tope no entra. 250 deja un cuarto de margen
   sobre las 200 hojas de un corte (EC-07).
2. **Bytes por día.** Una ventana deslizante de 24 horas sobre los bytes de los lotes que entraron.
   256 MB son entre tres y seis lotes de un corte con escaneos de 200 a 400 KB (40 a 80 MB cada
   uno). En el peor caso, el tope lleno todos los días hasta el 30-nov, son unos 7,5 GB: menos de
   lo que le toca a cada equipo del disco compartido (200 GB entre 23, unos 8,7 GB).

Dos decisiones de forma:

- **Se cuenta el lote entero, y antes de procesarlo.** El lote cabe completo o no entra ninguna
  hoja: una respuesta a medias obligaría al docente a averiguar cuáles faltan, que es lo que EC-07
  evita. Cuentan también los archivos que la validación rechace después, porque igual viajaron.
- **Vive en memoria del proceso**, como el presupuesto del proveedor de LLM (ADR-0015): es correcto
  con la única instancia de la API, y se vacía con cada reinicio y cada despliegue. Ese límite y el
  de que el cupo sea de todos y no de cada docente están en ADR-0022.

Solo depende de la biblioteca estándar.
"""

import math
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone

__all__ = [
    "CargaDiariaAgotada",
    "EstadoDelPresupuestoDeCarga",
    "LoteDemasiadoGrande",
    "LoteFueraDePresupuesto",
    "PresupuestoDeCarga",
    "HOJAS_POR_LOTE",
    "MB_POR_DIA",
]

HOJAS_POR_LOTE = 250
MB_POR_DIA = 256

_UN_MB = 1024 * 1024
_UN_DIA = 24 * 60 * 60.0


@dataclass(frozen=True)
class EstadoDelPresupuestoDeCarga:
    """Cuánto del presupuesto de carga se ha usado, para `GET /metricas` y para el registro.

    `bytes_en_las_ultimas_24_horas` es la ventana que decide si un lote cabe. Los dos contadores
    `desde_el_arranque` no deciden nada: son la observabilidad de la mitigación, y vuelven a cero
    cuando el proceso se reinicia."""

    limite_de_hojas_por_lote: int
    limite_de_bytes_por_dia: int
    bytes_en_las_ultimas_24_horas: int
    lotes_admitidos_desde_el_arranque: int
    lotes_rechazados_desde_el_arranque: int
    arrancado_en: datetime


class LoteFueraDePresupuesto(Exception):
    """El lote no cabe en el presupuesto de carga y no se leyó ninguna de sus hojas.

    Lleva el motivo redactado para el docente."""

    def __init__(self, motivo: str) -> None:
        super().__init__(motivo)
        self.motivo = motivo


class LoteDemasiadoGrande(LoteFueraDePresupuesto):
    """El lote no cabría nunca: trae más hojas que el tope, o pesa más que el cupo de un día.
    Esperar no sirve; hay que dividirlo."""


class CargaDiariaAgotada(LoteFueraDePresupuesto):
    """El lote cabría en un día vacío, pero no en lo que queda del cupo de las últimas 24 horas.

    Lleva además los segundos que faltan para que quepa, que la API publica en la cabecera
    `Retry-After` del 429."""

    def __init__(self, motivo: str, reintentar_en_segundos: int) -> None:
        super().__init__(motivo)
        self.reintentar_en_segundos = reintentar_en_segundos


class PresupuestoDeCarga:
    """El tope de hojas por lote y una ventana deslizante de veinticuatro horas sobre los bytes.

    `reservar` es atómica: la ruta de carga confirma cada lote en un hilo aparte, así que dos lotes
    pueden llegar a la vez, y sin el candado los dos podrían ver el mismo cupo libre. `reloj`
    existe para las pruebas: con un reloj falso se comprueba la ventana sin esperar un día."""

    def __init__(
        self,
        hojas_por_lote: int = HOJAS_POR_LOTE,
        mb_por_dia: int = MB_POR_DIA,
        reloj: Callable[[], float] = time.monotonic,
    ) -> None:
        if hojas_por_lote < 1 or mb_por_dia < 1:
            raise ValueError("Los límites del presupuesto de carga tienen que ser de al menos 1.")
        self._hojas_por_lote = hojas_por_lote
        self._mb_por_dia = mb_por_dia
        self._bytes_por_dia = mb_por_dia * _UN_MB
        self._reloj = reloj
        self._candado = threading.Lock()
        self._lotes_en_el_dia: deque[tuple[float, int]] = deque()
        self._bytes_en_el_dia = 0
        self._admitidos = 0
        self._rechazados = 0
        self._arrancado_en = datetime.now(timezone.utc)

    def _olvidar_lo_vencido(self, ahora: float) -> None:
        while self._lotes_en_el_dia and ahora - self._lotes_en_el_dia[0][0] >= _UN_DIA:
            _, tamano = self._lotes_en_el_dia.popleft()
            self._bytes_en_el_dia -= tamano

    def reservar(self, hojas: int, bytes_del_lote: int) -> None:
        """Reserva el cupo de un lote entero, o levanta `LoteFueraDePresupuesto` sin reservar nada.

        Primero va lo que no se arregla esperando: si el lote es demasiado grande, el docente
        necesita saber que tiene que dividirlo, no cuántas horas faltan."""
        with self._candado:
            if hojas > self._hojas_por_lote:
                self._rechazados += 1
                raise LoteDemasiadoGrande(
                    f"El lote trae {hojas} hojas y el máximo es {self._hojas_por_lote}. "
                    "No entró ninguna: divídalo en lotes más pequeños y súbalos por separado."
                )
            if bytes_del_lote > self._bytes_por_dia:
                self._rechazados += 1
                raise LoteDemasiadoGrande(
                    f"El lote pesa {math.ceil(bytes_del_lote / _UN_MB)} MB y el máximo por día "
                    f"es {self._mb_por_dia} MB. No entró ninguna hoja: divídalo en lotes más "
                    "pequeños."
                )
            ahora = self._reloj()
            self._olvidar_lo_vencido(ahora)
            if self._bytes_en_el_dia + bytes_del_lote > self._bytes_por_dia:
                self._rechazados += 1
                segundos = self._segundos_hasta_que_quepa(bytes_del_lote, ahora)
                raise CargaDiariaAgotada(
                    f"Se alcanzó el máximo de {self._mb_por_dia} MB de hojas en 24 horas. No "
                    f"entró ninguna hoja de este lote; habrá cupo para él en unos "
                    f"{math.ceil(segundos / 3600)} h.",
                    segundos,
                )
            self._lotes_en_el_dia.append((ahora, bytes_del_lote))
            self._bytes_en_el_dia += bytes_del_lote
            self._admitidos += 1

    def _segundos_hasta_que_quepa(self, bytes_del_lote: int, ahora: float) -> int:
        """Segundos enteros hasta que salgan de la ventana los lotes que hacen falta para que este
        quepa. Se redondea hacia arriba y nunca baja de 1, como en el presupuesto del proveedor:
        un `Retry-After: 0` invita a reintentar en el acto y volver a chocar."""
        sobrante = self._bytes_en_el_dia + bytes_del_lote - self._bytes_por_dia
        for momento, tamano in self._lotes_en_el_dia:
            sobrante -= tamano
            if sobrante <= 0:
                return max(1, math.ceil(momento + _UN_DIA - ahora))
        # No se llega aquí: un lote más grande que el cupo entero ya salió como demasiado grande.
        return max(1, math.ceil(_UN_DIA))

    def estado(self) -> EstadoDelPresupuestoDeCarga:
        with self._candado:
            self._olvidar_lo_vencido(self._reloj())
            return EstadoDelPresupuestoDeCarga(
                limite_de_hojas_por_lote=self._hojas_por_lote,
                limite_de_bytes_por_dia=self._bytes_por_dia,
                bytes_en_las_ultimas_24_horas=self._bytes_en_el_dia,
                lotes_admitidos_desde_el_arranque=self._admitidos,
                lotes_rechazados_desde_el_arranque=self._rechazados,
                arrancado_en=self._arrancado_en,
            )
