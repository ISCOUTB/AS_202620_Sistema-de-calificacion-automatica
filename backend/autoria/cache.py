"""Caché de las propuestas del proveedor de LLM (RF-11, ADR-0019).

**Qué guarda y por qué.** Cada solicitud a `POST /distractores` gasta un cupo del presupuesto
(ADR-0015) y unos 2,1 s de espera del profesor (la mediana medida en EC-08). La misma pregunta se
pide más de una vez: el docente vuelve a abrir la pregunta, el navegador reenvía, otro profesor del
curso arma el mismo parcial. Las propuestas para una pregunta no envejecen por sí solas (la derivada de `x·sin(x)` no
cambia), así que repetir la solicitud solo cuesta. Esta caché guarda lo que devolvió el proveedor y
lo entrega otra vez sin salir a la red ni gastar cupo.

**Qué no guarda.** Ningún dato de una hoja, de un estudiante ni de una nota: el estado de una hoja
se lee de su fuente de verdad, la bitácora (ADR-0018). Tampoco guarda fallos: un 503 o un 429 no
entran, para que la siguiente solicitud vuelva a intentarlo.

**La política de invalidación**, que es lo que hace que una caché diga la verdad:

1. **Por versión, en la clave.** La clave incluye el modelo y la huella de las instrucciones que
   se le mandan. Si cualquiera de los dos cambia, las claves son otras y lo guardado deja de
   leerse; no hace falta borrar nada a mano.
2. **La regla no entra en la caché.** Se guarda lo que devolvió el proveedor, sin filtrar, y la
   regla de `distractores.py` corre en cada lectura. Un arreglo de la regla vale desde la primera
   solicitud siguiente, sin invalidar nada.
3. **Por tiempo.** Una entrada vence a las 24 horas de guardada, la misma ventana del presupuesto
   diario. Leerla no la renueva: lo más viejo que puede recibir el profesor tiene un día.
4. **Por capacidad.** Como mucho `CAPACIDAD` entradas; con la caché llena sale la que lleva más
   tiempo sin leerse.
5. **A pedido del profesor.** «Pedir otras propuestas» manda `otras: true`: la solicitud no lee la
   caché, sale al proveedor y reemplaza lo guardado, así que la siguiente vez se recibe lo nuevo.
6. **Por reinicio.** Vive en la memoria del proceso de la API, como el presupuesto, y se vacía con
   cada despliegue.

Es un adaptador del puerto, como `GeneradorConPresupuesto`: la regla y el adaptador de Groq no se
enteran de que existe. Va por fuera del presupuesto, así que un acierto no gasta cupo.

Solo depende de la biblioteca estándar.
"""

import hashlib
import json
import threading
import time
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass

from autoria.distractores import (
    DistractorPropuesto,
    GeneradorDeDistractores,
    PreguntaParaDistractores,
)

__all__ = [
    "CAPACIDAD",
    "VIGENCIA_SEGUNDOS",
    "CacheDePropuestas",
    "EstadoDeLaCache",
    "GeneradorConCache",
    "clave_de_la_pregunta",
]

# 256 preguntas son más que los bancos de un curso entero, y cada entrada son unas pocas
# propuestas de una línea: del orden de 1 KB, así que la caché llena ocupa menos de 1 MB de los
# 512 MB de la instancia.
CAPACIDAD = 256
VIGENCIA_SEGUNDOS = 24 * 60 * 60


def clave_de_la_pregunta(pregunta: PreguntaParaDistractores, version: str) -> str:
    """La clave con la que se guarda lo que el proveedor propuso para una pregunta.

    Lleva la `version` (el modelo y la huella de las instrucciones), el enunciado y la respuesta
    correcta con los espacios normalizados, y la cantidad pedida. Los espacios se normalizan
    porque no cambian la pregunta; lo demás se deja tal cual, porque el proveedor recibe el texto
    tal cual y dos escrituras distintas pueden darle propuestas distintas."""
    partes = [
        version,
        " ".join(pregunta.enunciado.split()),
        " ".join(pregunta.respuesta_correcta.split()),
        pregunta.cantidad,
    ]
    texto = json.dumps(partes, ensure_ascii=False)
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class EstadoDeLaCache:
    """Lo que publica `GET /metricas` de la caché. Son cuentas desde el arranque del proceso."""

    capacidad: int
    vigencia_segundos: int
    entradas: int
    aciertos: int
    fallos: int
    guardadas: int
    vencidas: int
    expulsadas: int


class CacheDePropuestas:
    """Las propuestas guardadas, por clave, con su vigencia y su capacidad.

    Segura entre hilos: la ruta de distractores corre en el grupo de hilos de FastAPI. Dos
    solicitudes iguales que fallan a la vez salen las dos al proveedor; no se coordinan, porque con
    6 solicitudes por minuto no hay una avalancha que valga la complejidad (ADR-0019)."""

    def __init__(
        self,
        capacidad: int = CAPACIDAD,
        vigencia_segundos: float = VIGENCIA_SEGUNDOS,
        reloj: Callable[[], float] = time.monotonic,
    ) -> None:
        self._capacidad = capacidad
        self._vigencia = vigencia_segundos
        self._reloj = reloj
        self._candado = threading.Lock()
        self._entradas: OrderedDict[str, tuple[float, tuple[DistractorPropuesto, ...]]] = (
            OrderedDict()
        )
        self._aciertos = 0
        self._fallos = 0
        self._guardadas = 0
        self._vencidas = 0
        self._expulsadas = 0

    def leer(self, clave: str) -> tuple[DistractorPropuesto, ...] | None:
        """Lo guardado con esa clave, o None si no hay nada vigente."""
        with self._candado:
            entrada = self._entradas.get(clave)
            if entrada is None:
                self._fallos += 1
                return None
            guardada_en, propuestas = entrada
            if self._reloj() - guardada_en >= self._vigencia:
                del self._entradas[clave]
                self._vencidas += 1
                self._fallos += 1
                return None
            self._entradas.move_to_end(clave)
            self._aciertos += 1
            return propuestas

    def guardar(self, clave: str, propuestas: list[DistractorPropuesto]) -> None:
        """Guarda o reemplaza, con la vigencia contada desde ahora."""
        with self._candado:
            self._entradas[clave] = (self._reloj(), tuple(propuestas))
            self._entradas.move_to_end(clave)
            self._guardadas += 1
            while len(self._entradas) > self._capacidad:
                self._entradas.popitem(last=False)
                self._expulsadas += 1

    def estado(self) -> EstadoDeLaCache:
        with self._candado:
            return EstadoDeLaCache(
                capacidad=self._capacidad,
                vigencia_segundos=int(self._vigencia),
                entradas=len(self._entradas),
                aciertos=self._aciertos,
                fallos=self._fallos,
                guardadas=self._guardadas,
                vencidas=self._vencidas,
                expulsadas=self._expulsadas,
            )


class GeneradorConCache:
    """Implementa `GeneradorDeDistractores` leyendo de la caché antes de delegar.

    Con `leer=False` (lo que pide «Pedir otras propuestas») no lee: va al generador de adentro y
    reemplaza lo guardado. Solo se guarda una respuesta con propuestas; una lista vacía o una
    falla no entran. `desde_la_cache` queda en True si la última respuesta salió de la caché, para
    que la API lo diga en la respuesta."""

    def __init__(
        self,
        generador: GeneradorDeDistractores,
        cache: CacheDePropuestas,
        version: str,
        leer: bool = True,
    ) -> None:
        self._generador = generador
        self._cache = cache
        self._version = version
        self._leer = leer
        self.desde_la_cache = False

    def proponer(self, pregunta: PreguntaParaDistractores) -> list[DistractorPropuesto]:
        clave = clave_de_la_pregunta(pregunta, self._version)
        if self._leer:
            guardadas = self._cache.leer(clave)
            if guardadas is not None:
                self.desde_la_cache = True
                return list(guardadas)
        self.desde_la_cache = False
        propuestas = self._generador.proponer(pregunta)
        if propuestas:
            self._cache.guardar(clave, propuestas)
        return propuestas
