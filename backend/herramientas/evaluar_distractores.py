"""Evalúa la propuesta de distractores diagnósticos frente a EC-08 y deja el informe en
`docs/evidencia/`.

Es la medición de la porción de la S9 (RF-11, aspecto A-06): el conjunto de evaluación con sus
resultados, la latencia y los tokens con los que se estima el costo por operación. Convierte en
cifras las tres medidas de EC-08 (arc42 §10.3):

- **M1.** Ninguna propuesta que repita la respuesta correcta llega al profesor (0 %).
- **M2.** El p95 de la latencia de la ruta, sobre el conjunto de evaluación, es de 15 s o menos.
- **M3.** Con el proveedor caído o lento, la ruta responde 503 en 21 s o menos.

Qué mide
--------
1. **Normal.** Cada pregunta de `docs/evidencia/conjunto-evaluacion-distractores.json` pasa por
   la ruta real `POST /distractores` con el proveedor configurado en el entorno (`LLM_URL_BASE`,
   `LLM_MODELO` y `LLM_API_KEY`, las mismas variables que lee la API). Registra la latencia de la
   ruta, los tokens que informa el proveedor, lo propuesto y lo descartado. Entre una pregunta y
   la siguiente espera `--pausa` segundos, para no pasar el límite de tokens por minuto de la capa
   gratuita.
2. **Proveedor caído.** La misma ruta, con el adaptador apuntando a un puerto local donde no
   escucha nadie.
3. **Proveedor lento.** La misma ruta, con el adaptador apuntando a un servidor local que tarda
   más que el tiempo de espera del adaptador.

Qué no mide
-----------
La calidad pedagógica de cada propuesta: si es incorrecta, si su etiqueta describe el error que
la produce y si es plausible lo califica el equipo a mano, y el informe trae todas las
propuestas para eso. Tampoco la red del profesor: la ruta se ejerce dentro del proceso con
`TestClient`, como en `medir_ec07.py`, así que la latencia es la de la API más la del proveedor.

A qué apunta y dónde escribe
----------------------------
La URL del proveedor sale de la misma configuración que usa la API, nunca de la línea de
comandos, y los dos casos degradados apuntan a destinos locales fijos (`http` sin cifrar porque
no salen de esta máquina). El informe se escribe solo dentro de `docs/evidencia/`, y `--json`
recibe el nombre del archivo, no una ruta. Es la misma regla de `medir_arranque_en_frio.py`, que
nació de los hallazgos de SonarQube Cloud sobre herramientas que un agente de IA podría invocar
con argumentos manipulados. La clave no se imprime ni se escribe en el informe.

Uso
---
    python -m herramientas.evaluar_distractores --escenario degradado
    python -m herramientas.evaluar_distractores --escenario todos --pasadas 1 --pausa 8 \\
        --json evaluacion-distractores.json
"""

from __future__ import annotations

import argparse
import http.server
import json
import logging
import math
import os
import platform
import statistics
import sys
import threading
import time
from collections import Counter
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx
from fastapi.testclient import TestClient

from api.main import app, obtener_generador
from api.settings import LLM_API_KEY, LLM_MODELO, LLM_URL_BASE
from autoria import GeneradorCompatibleConOpenAI
from autoria.distractores import normalizar
from autoria.proveedor_llm import TIEMPO_DE_ESPERA_SEGUNDOS

UMBRAL_M2_P95_SEGUNDOS = 15.0
UMBRAL_M3_SEGUNDOS = TIEMPO_DE_ESPERA_SEGUNDOS + 1.0
CARTAGENA = timezone(timedelta(hours=-5))

CARPETA_DE_EVIDENCIA = Path(__file__).resolve().parent.parent.parent / "docs" / "evidencia"
CONJUNTO = CARPETA_DE_EVIDENCIA / "conjunto-evaluacion-distractores.json"

# Destinos fijos de los casos degradados. Al puerto 9 no lo atiende nadie en una máquina de
# desarrollo, así que la conexión se rechaza de inmediato.
PROVEEDOR_CAIDO = "http://127.0.0.1:9/v1"


def _ruta_del_informe(nombre: str) -> Path:
    """Ruta del informe dentro de `docs/evidencia/`, con la misma comprobación que
    `medir_arranque_en_frio.py`: la ruta canónica tiene que seguir dentro de esa carpeta."""
    base = os.path.realpath(CARPETA_DE_EVIDENCIA)
    ruta = os.path.realpath(os.path.join(base, nombre))
    if not ruta.startswith(base + os.sep):
        raise SystemExit(
            f"--json tiene que ser un nombre de archivo dentro de docs/evidencia/: {nombre!r}"
        )
    return Path(ruta)


def _p95(valores: list[float]) -> float:
    """Percentil 95 por rango más cercano: con 20 muestras es la segunda peor."""
    ordenados = sorted(valores)
    return ordenados[max(0, math.ceil(0.95 * len(ordenados)) - 1)]


def _resumen(valores: list[float]) -> dict[str, Any]:
    if not valores:
        return {"muestras": 0}
    return {
        "muestras": len(valores),
        "mediana_segundos": round(statistics.median(valores), 3),
        "p95_segundos": round(_p95(valores), 3),
        "peor_segundos": round(max(valores), 3),
    }


def _ahora() -> dict[str, str]:
    momento = datetime.now(timezone.utc)
    return {
        "utc": momento.isoformat(timespec="seconds"),
        "cartagena": momento.astimezone(CARTAGENA).isoformat(timespec="seconds"),
    }


class _CapturaDeEventos(logging.Handler):
    """Guarda los eventos que deja el adaptador: la métrica de EC-08 se lee del mismo registro
    que produce la API en operación, no de un contador aparte."""

    def __init__(self) -> None:
        super().__init__()
        self.eventos: list[dict[str, Any]] = []

    def emit(self, record: logging.LogRecord) -> None:
        evento = getattr(record, "evento", None)
        if evento in ("distractores_propuestos", "proveedor_no_disponible"):
            campos = ("evento", "duracion_ms", "tokens_entrada", "tokens_salida", "motivo")
            self.eventos.append({campo: getattr(record, campo, None) for campo in campos})


@contextmanager
def _capturar_eventos() -> Iterator[_CapturaDeEventos]:
    captura = _CapturaDeEventos()
    registro = logging.getLogger("autoria")
    registro.addHandler(captura)
    try:
        yield captura
    finally:
        registro.removeHandler(captura)


def _pedir(cliente: TestClient, enunciado: str, respuesta_correcta: str) -> tuple[Any, float]:
    inicio = time.perf_counter()
    respuesta = cliente.post(
        "/distractores",
        json={"enunciado": enunciado, "respuesta_correcta": respuesta_correcta, "cantidad": 3},
    )
    return respuesta, round(time.perf_counter() - inicio, 3)


def _cargar_conjunto() -> list[dict[str, Any]]:
    if not CONJUNTO.exists():
        raise SystemExit(f"No existe el conjunto de evaluación: {CONJUNTO}")
    preguntas = json.loads(CONJUNTO.read_text(encoding="utf-8"))["preguntas"]
    for pregunta in preguntas:
        if not pregunta.get("enunciado") or not pregunta.get("respuesta_correcta"):
            raise SystemExit(f"Pregunta sin enunciado o sin respuesta correcta: {pregunta}")
    return preguntas


def medir_normal(pasadas: int, pausa: float) -> dict[str, Any]:
    if not LLM_API_KEY:
        raise SystemExit(
            "Falta LLM_API_KEY en el entorno. El escenario normal llama al proveedor real."
        )
    preguntas = _cargar_conjunto()
    muestras: list[dict[str, Any]] = []
    with _capturar_eventos() as captura, TestClient(app) as cliente:
        for pasada in range(1, pasadas + 1):
            for pregunta in preguntas:
                if muestras:
                    time.sleep(pausa)
                antes = len(captura.eventos)
                respuesta, segundos = _pedir(
                    cliente, pregunta["enunciado"], pregunta["respuesta_correcta"]
                )
                evento = captura.eventos[-1] if len(captura.eventos) > antes else {}
                cuerpo = respuesta.json()
                muestra: dict[str, Any] = {
                    "pasada": pasada,
                    "id": pregunta.get("id"),
                    "enunciado": pregunta["enunciado"],
                    "respuesta_correcta": pregunta["respuesta_correcta"],
                    "codigo": respuesta.status_code,
                    "segundos": segundos,
                    "tokens_entrada": evento.get("tokens_entrada"),
                    "tokens_salida": evento.get("tokens_salida"),
                }
                if respuesta.status_code == 200:
                    muestra["distractores"] = cuerpo["distractores"]
                    muestra["descartados"] = cuerpo["descartados"]
                else:
                    muestra["detalle"] = cuerpo.get("detail")
                muestras.append(muestra)
                print(f"  pasada {pasada}, pregunta {pregunta.get('id')}: "
                      f"{respuesta.status_code} en {segundos} s", file=sys.stderr, flush=True)

    respondidas = [m for m in muestras if m["codigo"] == 200]
    latencias = [m["segundos"] for m in respondidas]
    repiten_la_correcta = sum(
        1
        for m in respondidas
        for d in m["distractores"]
        if normalizar(d["expresion"]) == normalizar(m["respuesta_correcta"])
    )
    entregados = sum(len(m["distractores"]) for m in respondidas)
    tokens_entrada = [m["tokens_entrada"] for m in respondidas if m["tokens_entrada"] is not None]
    tokens_salida = [m["tokens_salida"] for m in respondidas if m["tokens_salida"] is not None]
    return {
        "muestras": muestras,
        "resumen": {
            "solicitudes": len(muestras),
            "codigos": dict(Counter(str(m["codigo"]) for m in muestras)),
            "latencia_de_las_respondidas": _resumen(latencias),
            "distractores_entregados": entregados,
            "descartados_por_motivo": dict(Counter(
                d["motivo"] for m in respondidas for d in m["descartados"]
            )),
            "entregados_que_repiten_la_respuesta_correcta": repiten_la_correcta,
            "tokens_entrada_promedio": (
                round(statistics.mean(tokens_entrada), 1) if tokens_entrada else None
            ),
            "tokens_salida_promedio": (
                round(statistics.mean(tokens_salida), 1) if tokens_salida else None
            ),
        },
    }


class _ProveedorLento(http.server.BaseHTTPRequestHandler):
    """Acepta la conexión y no contesta antes de que se agote la espera del adaptador."""

    def do_POST(self) -> None:  # noqa: N802 (nombre que exige http.server)
        time.sleep(TIEMPO_DE_ESPERA_SEGUNDOS + 5)
        try:
            self.send_response(200)
            self.end_headers()
        except OSError:
            pass  # el adaptador ya cerró la conexión, que es lo esperado

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        pass


def _medir_degradado(url_base: str, muestras: int) -> list[dict[str, Any]]:
    app.dependency_overrides[obtener_generador] = lambda: GeneradorCompatibleConOpenAI(
        url_base, "modelo-de-prueba", "clave-de-prueba"
    )
    resultados = []
    try:
        with TestClient(app) as cliente:
            for n in range(1, muestras + 1):
                respuesta, segundos = _pedir(cliente, "Derivada de x²", "2x")
                resultados.append({
                    "muestra": n,
                    "codigo": respuesta.status_code,
                    "segundos": segundos,
                    "detalle": respuesta.json().get("detail"),
                    "salud_durante_la_falla": cliente.get("/health").status_code,
                })
                print(f"  degradado {n}: {respuesta.status_code} en {segundos} s",
                      file=sys.stderr, flush=True)
    finally:
        app.dependency_overrides.pop(obtener_generador, None)
    return resultados


def medir_degradado(muestras: int) -> dict[str, Any]:
    caido = _medir_degradado(PROVEEDOR_CAIDO, muestras)

    servidor = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _ProveedorLento)
    servidor.daemon_threads = True
    hilo = threading.Thread(target=servidor.serve_forever, daemon=True)
    hilo.start()
    try:
        lento = _medir_degradado(f"http://127.0.0.1:{servidor.server_address[1]}/v1", muestras)
    finally:
        servidor.shutdown()
        servidor.server_close()

    todas = caido + lento
    return {
        "proveedor_caido": caido,
        "proveedor_lento": lento,
        "resumen": {
            "todas_responden_503": all(m["codigo"] == 503 for m in todas),
            "peor_segundos": max(m["segundos"] for m in todas),
            "la_salud_siguio_en_200": all(m["salud_durante_la_falla"] == 200 for m in todas),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Evalúa la propuesta de distractores diagnósticos frente a EC-08.")
    parser.add_argument("--escenario", choices=["normal", "degradado", "todos"],
                        default="degradado")
    parser.add_argument("--pasadas", type=int, default=1,
                        help="veces que se recorre el conjunto en el escenario normal")
    parser.add_argument("--pausa", type=float, default=8.0,
                        help="segundos entre solicitudes al proveedor real")
    parser.add_argument("--muestras-degradadas", type=int, default=2)
    parser.add_argument("--json", default=None,
                        help="nombre del archivo del informe, que se escribe en docs/evidencia/")
    args = parser.parse_args(argv)
    ruta_del_informe = _ruta_del_informe(args.json) if args.json else None

    inicio = _ahora()
    normal = (medir_normal(args.pasadas, args.pausa)
              if args.escenario in ("normal", "todos") else None)
    degradado = (medir_degradado(args.muestras_degradadas)
                 if args.escenario in ("degradado", "todos") else None)

    resultado: dict[str, Any] = {}
    if normal is not None:
        resumen = normal["resumen"]
        latencia = resumen["latencia_de_las_respondidas"]
        resultado["m1_cumple"] = resumen["entregados_que_repiten_la_respuesta_correcta"] == 0
        resultado["m2_p95_segundos"] = latencia.get("p95_segundos")
        resultado["m2_cumple"] = (
            latencia.get("p95_segundos") is not None
            and latencia["p95_segundos"] <= UMBRAL_M2_P95_SEGUNDOS
        )
    if degradado is not None:
        resultado["m3_peor_segundos"] = degradado["resumen"]["peor_segundos"]
        resultado["m3_cumple"] = (
            degradado["resumen"]["todas_responden_503"]
            and degradado["resumen"]["peor_segundos"] <= UMBRAL_M3_SEGUNDOS
        )

    informe: dict[str, Any] = {
        "escenario": "EC-08 - Propuesta de distractores diagnosticos (RF-11)",
        "inicio": inicio,
        "fin": _ahora(),
        "entorno": {
            "url_base_del_proveedor": LLM_URL_BASE,
            "modelo": LLM_MODELO,
            "tiempo_de_espera_del_adaptador_segundos": TIEMPO_DE_ESPERA_SEGUNDOS,
            "pasadas": args.pasadas,
            "pausa_entre_solicitudes_segundos": args.pausa,
            "python": platform.python_version(),
            "httpx": httpx.__version__,
            "medido": "dentro del proceso, con TestClient: sin la red del profesor",
        },
        "umbrales": {
            "m1_entregados_que_repiten_la_respuesta_correcta": 0,
            "m2_p95_segundos": UMBRAL_M2_P95_SEGUNDOS,
            "m3_segundos": UMBRAL_M3_SEGUNDOS,
        },
        "normal": normal,
        "degradado": degradado,
        "resultado": resultado,
    }

    texto = json.dumps(informe, indent=2, ensure_ascii=False)
    print(texto)
    if ruta_del_informe is not None:
        with open(ruta_del_informe, "w", encoding="utf-8", newline="\n") as salida:
            salida.write(texto + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
