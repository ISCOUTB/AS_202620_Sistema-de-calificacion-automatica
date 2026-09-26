"""Mide las dos cifras del escenario EC-07 sobre el corte vertical del aspecto A-01.

EC-07 pide dos cosas de la carga de un lote de hasta 200 hojas escaneadas:

1. **Confirmación de recepción en <= 10 segundos.**
2. **0 % de pérdida silenciosa**: todo archivo cargado queda registrado como *aceptado* o
   como *rechazado con motivo*.

Este archivo existe para que esas dos cifras dejen de ser objetivos declarados y pasen a ser
resultados con procedimiento reproducible, que es lo que exige el reto del primer corte.

Qué recorre la medición y qué no
--------------------------------
Se ejerce el endpoint real `POST /examenes/{id}/hojas` a través de `TestClient`, de modo que
el recorrido pasa por `api` -> `ingesta` -> `infraestructura.almacen`. El almacén es el
adaptador real `AlmacenEnDisco`, así que las escrituras a disco son reales y cuentan en el
tiempo.

La cola es una sustituta en memoria, no un Redis real, por dos razones que conviene declarar
en vez de esconder: la medición debe poder repetirse sin levantar contenedores, y el objeto de
la medición 2 es el hueco entre almacenar y encolar, que se observa mejor cuando el fallo se
puede provocar en un punto exacto del lote. La consecuencia es que la cifra de latencia
**no incluye la ida y vuelta de red hacia Redis**: es una cota inferior del tiempo real, y
así se reporta.

Uso
---
    python -m herramientas.medir_ec07                     # lote de 200 hojas, 3 repeticiones
    python -m herramientas.medir_ec07 --json medicion.json
    python -m herramientas.medir_ec07 --hojas 200 --kb 200 --repeticiones 3 --fallar-en 100
"""

import argparse
import json
import platform
import shutil
import statistics
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import redis.exceptions
from fastapi.testclient import TestClient

from api.main import app, obtener_almacen, obtener_cliente_cola
from infraestructura.almacen import AlmacenEnDisco

try:  # pragma: no cover - la rama que se toma depende del estado del repositorio
    from api.main import obtener_bitacora
    from infraestructura.bitacora import BitacoraEnDisco

    HAY_BITACORA = True
except ImportError:
    # Estado anterior a ADR-0006: no existe la bitácora de recepción. La herramienta corre
    # igual, y es a propósito: la cifra de antes y la de después tienen que salir del mismo
    # procedimiento, o la comparación no vale nada.
    HAY_BITACORA = False

__all__ = ["medir_latencia", "medir_perdida_silenciosa", "ColaEnMemoria"]

UMBRAL_SEGUNDOS = 10.0
UMBRAL_PERDIDA = 0.0

# Cabecera JPEG real: `ingesta.recepcion` valida los primeros bytes, no solo la extensión, y
# una medición que usara relleno arbitrario mediría el camino de rechazo, no el de aceptación.
CABECERA_JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"


class ColaEnMemoria:
    """Sustituta de `redis.Redis` que solo entiende `rpush`, que es lo único que usa `publicar`.

    Tiene que aceptar la misma llamada que el cliente real, `rpush(nombre_de_la_cola, valor)`,
    porque `infraestructura/cola.py` la invoca así sin saber a quién le habla. Por eso `rpush`
    conserva el parámetro `cola` aunque su cuerpo no lo use: quitarlo rompe la herramienta, y
    `tests/test_medir_ec07.py` es la prueba que lo detecta.

    `fallar_en` provoca un `ConnectionError` de redis-py justo antes de encolar la hoja número
    N del lote. No es un caso rebuscado: es exactamente lo que ocurre si Redis se reinicia o
    la red se corta a mitad de una carga de doscientas hojas."""

    def __init__(self, fallar_en: int | None = None, demora_del_fallo: float = 0.0) -> None:
        self.encolados: list[str] = []
        self.fallar_en = fallar_en
        self.demora_del_fallo = demora_del_fallo
        self.intentos = 0

    # El parámetro `cola` no se usa en el cuerpo, pero es parte de la firma de redis-py que
    # `publicar` invoca. SonarQube lo marca como parámetro sin usar (python:S1172); quitarlo
    # rompió esta herramienta una vez, así que el aviso se suprime aquí a propósito.
    def rpush(self, cola: str, valor: str) -> int:  # NOSONAR
        self.intentos += 1
        if self.fallar_en is not None and len(self.encolados) >= self.fallar_en:
            # Un cliente de Redis que no encuentra servidor no falla al instante: agota el
            # tiempo de conexión primero. Sin simular esa demora, la medición del camino de
            # fallo sale optimista y no dice nada útil sobre el techo de 10 s del escenario.
            if self.demora_del_fallo:
                time.sleep(self.demora_del_fallo)
            raise redis.exceptions.ConnectionError(
                "Error 111 connecting to redis:6379. Connection refused."
            )
        self.encolados.append(valor)
        return len(self.encolados)


def _hojas(cantidad: int, kilobytes: int) -> list[tuple[str, tuple[str, bytes, str]]]:
    """Construye el lote multipart. Cada hoja es un JPEG sintético del tamaño pedido."""
    relleno = bytes(kilobytes * 1024 - len(CABECERA_JPEG))
    contenido = CABECERA_JPEG + relleno
    return [
        ("archivos", (f"hoja-{i:03d}.jpg", contenido, "image/jpeg"))
        for i in range(1, cantidad + 1)
    ]


def _cliente(raiz: Path, cola: ColaEnMemoria, propagar: bool) -> TestClient:
    app.dependency_overrides[obtener_almacen] = lambda: AlmacenEnDisco(raiz)
    app.dependency_overrides[obtener_cliente_cola] = lambda: cola
    if HAY_BITACORA:
        app.dependency_overrides[obtener_bitacora] = lambda: BitacoraEnDisco(
            raiz / "bitacora-de-recepcion.jsonl"
        )
    return TestClient(app, raise_server_exceptions=propagar)


def medir_latencia(hojas: int, kilobytes: int, repeticiones: int) -> dict:
    """Medición 1: cuánto tarda el sistema en confirmar un lote completo.

    Se cronometra la petición HTTP entera, que es lo que el docente espera frente a la
    pantalla, no el tiempo interno de una función."""
    lote = _hojas(hojas, kilobytes)
    tiempos: list[float] = []
    confirmadas = 0

    for _ in range(repeticiones):
        raiz = Path(tempfile.mkdtemp(prefix="ec07-latencia-"))
        cola = ColaEnMemoria()
        try:
            cliente = _cliente(raiz, cola, propagar=True)
            inicio = time.perf_counter()
            respuesta = cliente.post("/examenes/EC07-LAT/hojas", files=lote)
            tiempos.append(time.perf_counter() - inicio)
            respuesta.raise_for_status()
            confirmadas = respuesta.json()["total_procesados"]
        finally:
            app.dependency_overrides.clear()
            shutil.rmtree(raiz, ignore_errors=True)

    mediana = statistics.median(tiempos)
    return {
        "hojas_del_lote": hojas,
        "kb_por_hoja": kilobytes,
        "mb_del_lote": round(hojas * kilobytes / 1024, 1),
        "repeticiones": repeticiones,
        "tiempos_segundos": [round(t, 3) for t in tiempos],
        "mediana_segundos": round(mediana, 3),
        "peor_segundos": round(max(tiempos), 3),
        "hojas_confirmadas": confirmadas,
        "umbral_segundos": UMBRAL_SEGUNDOS,
        "cumple": max(tiempos) <= UMBRAL_SEGUNDOS,
    }


def medir_perdida_silenciosa(
    hojas: int, kilobytes: int, fallar_en: int, demora_del_fallo: float = 0.0
) -> dict:
    """Medición 2: cuántas hojas del lote quedan sin reportar cuando la cola falla a mitad.

    EC-07 no promete que la carga nunca falle. Promete que ningún archivo desaparezca sin
    dejar traza: cada uno sale como aceptado o como rechazado con motivo. Esta medición cuenta
    exactamente eso, y de paso cuenta cuántos trabajos alcanzaron a encolarse sin que el
    docente lo sepa, que es lo que se duplica cuando vuelve a subir el lote."""
    lote = _hojas(hojas, kilobytes)
    raiz = Path(tempfile.mkdtemp(prefix="ec07-perdida-"))
    cola = ColaEnMemoria(fallar_en=fallar_en, demora_del_fallo=demora_del_fallo)

    try:
        cliente = _cliente(raiz, cola, propagar=False)
        inicio = time.perf_counter()
        respuesta = cliente.post("/examenes/EC07-PERDIDA/hojas", files=lote)
        transcurrido = time.perf_counter() - inicio
        codigo = respuesta.status_code
        if codigo == 200:
            cuerpo = respuesta.json()
            reportadas = cuerpo["total_procesados"]
            aceptadas = len(cuerpo["aceptadas"])
            rechazadas = len(cuerpo["rechazados"])
        else:
            reportadas = aceptadas = rechazadas = 0
        pendientes = (
            len(BitacoraEnDisco(raiz / "bitacora-de-recepcion.jsonl").pendientes())
            if HAY_BITACORA
            else 0
        )
        en_disco = sum(1 for _ in raiz.rglob("*") if _.is_file())
    finally:
        app.dependency_overrides.clear()
        shutil.rmtree(raiz, ignore_errors=True)

    perdidas = hojas - reportadas
    return {
        "hojas_del_lote": hojas,
        "falla_de_la_cola_en_la_hoja": fallar_en + 1,
        "codigo_http": codigo,
        "hojas_reportadas": reportadas,
        "de_ellas_aceptadas": aceptadas,
        "de_ellas_rechazadas_con_motivo": rechazadas,
        "hojas_sin_reportar": perdidas,
        "porcentaje_de_perdida_silenciosa": round(100 * perdidas / hojas, 1),
        "trabajos_encolados": len(cola.encolados),
        "intentos_contra_la_cola": cola.intentos,
        "demora_simulada_del_fallo_segundos": demora_del_fallo,
        "segundos_hasta_la_confirmacion": round(transcurrido, 3),
        "cumple_el_umbral_de_tiempo": transcurrido <= UMBRAL_SEGUNDOS,
        "hojas_recuperables_desde_la_bitacora": pendientes if HAY_BITACORA else "no existe",
        "archivos_escritos_en_el_almacen": en_disco,
        "umbral_porcentaje": UMBRAL_PERDIDA,
        "cumple": perdidas == 0,
    }


def _tipo_de_sistema_de_archivos() -> str:
    """Importa para leer la cifra de latencia: no es lo mismo medir sobre un disco real que
    sobre `tmpfs`, que vive en memoria y regalaría el resultado."""
    try:
        import subprocess

        salida = subprocess.run(
            ["df", "-T", tempfile.gettempdir()], capture_output=True, text=True, timeout=5
        ).stdout.splitlines()
        return salida[-1].split()[1] if len(salida) > 1 else "desconocido"
    except Exception:
        return "desconocido"


def _entorno() -> dict:
    return {
        "medido_en": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "python": platform.python_version(),
        "sistema": f"{platform.system()} {platform.release()}",
        "procesador": platform.machine(),
        "almacen": "AlmacenEnDisco sobre directorio temporal (escrituras reales)",
        "sistema_de_archivos_del_almacen": _tipo_de_sistema_de_archivos(),
        "cola": "sustituta en memoria; la latencia no incluye la ida y vuelta hacia Redis",
        "bitacora_de_recepcion": "presente (ADR-0006)" if HAY_BITACORA else "ausente (estado anterior a ADR-0006)",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Mide las dos cifras de EC-07 sobre A-01.")
    parser.add_argument("--hojas", type=int, default=200)
    parser.add_argument("--kb", type=int, default=200)
    parser.add_argument("--repeticiones", type=int, default=3)
    parser.add_argument("--fallar-en", type=int, default=100)
    parser.add_argument(
        "--demora-del-fallo",
        type=float,
        default=7.1,
        help="Segundos que tarda la cola en rendirse. 7,1 es lo medido contra un contenedor "
        "de Redis detenido; 0 mide el fallo instantáneo.",
    )
    parser.add_argument("--json", type=Path, default=None)
    args = parser.parse_args(argv)

    informe = {
        "escenario": "EC-07 - Confirmacion fiable de recepcion del lote",
        "aspecto": "A-01",
        "entorno": _entorno(),
        "medicion_1_latencia_de_confirmacion": medir_latencia(
            args.hojas, args.kb, args.repeticiones
        ),
        "medicion_2_perdida_silenciosa": medir_perdida_silenciosa(
            args.hojas, args.kb, args.fallar_en, args.demora_del_fallo
        ),
    }

    texto = json.dumps(informe, indent=2, ensure_ascii=False)
    print(texto)
    if args.json:
        args.json.write_text(texto + "\n", encoding="utf-8")

    lat = informe["medicion_1_latencia_de_confirmacion"]
    per = informe["medicion_2_perdida_silenciosa"]
    print(
        f"\nLatencia: peor {lat['peor_segundos']} s contra umbral {UMBRAL_SEGUNDOS} s "
        f"-> {'CUMPLE' if lat['cumple'] else 'NO CUMPLE'}",
        file=sys.stderr,
    )
    print(
        f"Perdida silenciosa: {per['porcentaje_de_perdida_silenciosa']} % contra umbral "
        f"{UMBRAL_PERDIDA} % -> {'CUMPLE' if per['cumple'] else 'NO CUMPLE'}",
        file=sys.stderr,
    )
    print(
        f"Confirmacion con la cola caida: {per['segundos_hasta_la_confirmacion']} s con "
        f"{per['intentos_contra_la_cola']} intento(s) contra la cola, umbral "
        f"{UMBRAL_SEGUNDOS} s -> "
        f"{'CUMPLE' if per['cumple_el_umbral_de_tiempo'] else 'NO CUMPLE'}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
