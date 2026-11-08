"""Mide EC-03 y EC-04 sobre el sistema corriendo: la API, la cola, el worker y el registro.

- **EC-03:** ≤5 s por hoja (p95), desde la confirmación de la carga hasta que el resultado está,
  sin un lote en curso.
- **EC-04:** 200 hojas procesadas en ≤10 min desde la confirmación del lote, con la CPU y la
  memoria por debajo del 85 %.

Son dos pasos, porque los tiempos los dicen los registros de los dos procesos:

1. `cargar` genera hojas sintéticas y las sube a la API: una por una, con una pausa entre ellas
   (EC-03), o todas en un lote (EC-04). Escribe además la clave del examen, que se copia a mano a
   `RUTA_CLAVES` porque A-04 todavía no la registra.
2. `analizar` lee el registro de la API y del worker juntos y calcula los tiempos:
   - por hoja, de `trabajo_publicado` (la API la dejó en la cola, antes de confirmar) a
     `hoja_procesada` (el resultado quedó guardado);
   - por lote, de `lote_confirmado` al último `hoja_procesada` de ese examen.

La CPU y la memoria no salen del registro: se miden aparte, con `docker stats`, y así se reportan.

Las hojas son como un escaneo a 200 DPI en gris (8,5 px/mm) y pesan unos 300 KB: 200 caben en una
petición (100 MB) y en el presupuesto diario de carga (256 MB). Una foto de celular pesa de 3 a
5 MB, y 200 no caben.

Uso, desde backend/
-------------------
    python -m herramientas.medir_procesamiento cargar --url http://localhost:8000 \\
        --examen MEDICION-EC03 --hojas 20 --pausa 8 --clave clave.json
    python -m herramientas.medir_procesamiento cargar --url http://localhost:8000 \\
        --examen MEDICION-EC04 --hojas 200 --clave clave.json
    docker compose logs --no-log-prefix api worker | \\
        python -m herramientas.medir_procesamiento analizar - --examen MEDICION-EC04
"""

import argparse
import json
import statistics
import sys
import time
from collections.abc import Iterable
from datetime import datetime
from typing import Any

import httpx
import numpy as np

from herramientas.hojas_sinteticas import Foto, patron
from herramientas.medir_lectura import generar_hoja

ESCANEO = Foto(escala=0.72, ruido=2.0, calidad_jpeg=80)  # 8,5 px/mm, como 200 DPI
UMBRAL_EC03_MS = 5000
UMBRAL_EC04_MS = 10 * 60 * 1000


def hojas_escaneadas(cantidad: int, semilla: int) -> list[bytes]:
    """Hojas marcadas al azar, escaneadas: derechas, sin sombra ni perspectiva."""
    azar = np.random.default_rng(semilla)
    return [generar_hoja(azar, ESCANEO)[0] for _ in range(cantidad)]


def clave(examen_id: str) -> dict[str, Any]:
    """La clave del examen, habilitada, en la forma que lee `ClavesEnDisco`. Las hojas se marcan
    al azar, así que la nota da igual: lo que se mide es el tiempo."""
    return {
        "examen_id": examen_id,
        "preguntas": [{"numero": n, "correcta": patron(n), "peso": 1.0} for n in range(1, 41)],
        "habilitacion": {"por": "Medición de EC-03 y EC-04", "en": "2026-11-05T00:00:00+00:00"},
    }


def cargar(url: str, examen_id: str, hojas: list[bytes], pausa_s: float | None) -> list[dict]:
    """Sube las hojas: todas en un lote, o de a una con `pausa_s` entre ellas. Devuelve las
    respuestas de la API."""
    respuestas = []
    lotes = [[hoja] for hoja in hojas] if pausa_s is not None else [hojas]
    with httpx.Client(base_url=url, timeout=120) as cliente:
        for numero, lote in enumerate(lotes):
            archivos = [
                ("archivos", (f"hoja-{numero:03d}-{i:03d}.jpg", contenido, "image/jpeg"))
                for i, contenido in enumerate(lote)
            ]
            respuesta = cliente.post(f"/examenes/{examen_id}/hojas", files=archivos)
            respuesta.raise_for_status()
            respuestas.append(respuesta.json())
            if pausa_s is not None and numero < len(lotes) - 1:
                time.sleep(pausa_s)
    return respuestas


def leer_lineas(lineas: Iterable[str]) -> list[dict[str, Any]]:
    """Los eventos JSON del registro. Cada línea se lee desde su primera llave, como en
    `seguir_trabajo`, para que el prefijo del panel o de docker no estorbe."""
    eventos = []
    for linea in lineas:
        inicio = linea.find("{")
        if inicio < 0:
            continue
        try:
            evento = json.loads(linea[inicio:])
        except ValueError:
            continue
        if isinstance(evento, dict) and "evento" in evento and "momento" in evento:
            eventos.append(evento)
    return eventos


def analizar(eventos: list[dict[str, Any]], examen_id: str) -> dict[str, Any]:
    def momento(evento: dict[str, Any]) -> datetime:
        return datetime.fromisoformat(evento["momento"])

    publicados = {e["trabajo"]: e for e in eventos
                  if e["evento"] == "trabajo_publicado" and e.get("examen") == examen_id}
    procesadas = {e["trabajo"]: e for e in eventos
                  if e["evento"] == "hoja_procesada" and e.get("trabajo") in publicados}
    tiempos = [(momento(procesadas[t]) - momento(publicados[t])).total_seconds() * 1000
               for t in procesadas]
    lecturas = [e["duracion_lectura_ms"] for e in procesadas.values() if "duracion_lectura_ms" in e]
    estados: dict[str, int] = {}
    for evento in procesadas.values():
        estados[evento["estado"]] = estados.get(evento["estado"], 0) + 1
    lotes = [e for e in eventos if e["evento"] == "lote_confirmado" and e.get("examen") == examen_id]
    informe: dict[str, Any] = {
        "examen": examen_id,
        "hojas_publicadas": len(publicados),
        "hojas_procesadas": len(procesadas),
        "estados": estados,
        "por_hoja_ms": {
            "p50": round(statistics.median(tiempos), 1) if tiempos else None,
            "p95": round(float(np.percentile(tiempos, 95)), 1) if tiempos else None,
            "maximo": round(max(tiempos), 1) if tiempos else None,
        },
        "lectura_en_el_worker_ms": {
            "p50": round(statistics.median(lecturas), 1) if lecturas else None,
            "p95": round(float(np.percentile(lecturas, 95)), 1) if lecturas else None,
        },
    }
    # EC-03 es sin lote en curso: con un lote, el tiempo de cada hoja incluye la espera en la cola
    # detrás de las demás, y lo que se juzga es el lote (EC-04).
    if len(lotes) != 1:
        informe["ec03_cumple"] = bool(tiempos) and float(np.percentile(tiempos, 95)) <= UMBRAL_EC03_MS
    # Las cifras del lote solo tienen sentido con un lote: las hojas sueltas de EC-03 traen una
    # confirmación cada una.
    if len(lotes) == 1 and procesadas:
        inicio = min(momento(e) for e in lotes)
        fin = max(momento(e) for e in procesadas.values())
        total_ms = (fin - inicio).total_seconds() * 1000
        informe["lote_ms"] = round(total_ms, 1)
        informe["ec04_cumple"] = (
            len(procesadas) == len(publicados) and total_ms <= UMBRAL_EC04_MS
        )
    return informe


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Mide EC-03 y EC-04 sobre el sistema corriendo.")
    pasos = parser.add_subparsers(dest="paso", required=True)
    subir = pasos.add_parser("cargar", help="genera y sube hojas sintéticas")
    subir.add_argument("--url", required=True)
    subir.add_argument("--examen", required=True)
    subir.add_argument("--hojas", type=int, default=200)
    subir.add_argument("--pausa", type=float, help="segundos entre hojas sueltas (EC-03)")
    subir.add_argument("--semilla", type=int, default=2026)
    subir.add_argument("--clave", help="dónde escribir la clave del examen")
    leer = pasos.add_parser("analizar", help="calcula los tiempos con el registro")
    leer.add_argument("registro", help="- para la entrada estándar")
    leer.add_argument("--examen", required=True)
    args = parser.parse_args(argv)

    if args.paso == "cargar":
        if args.clave:
            with open(args.clave, "w", encoding="utf-8") as archivo:
                json.dump(clave(args.examen), archivo, ensure_ascii=False, indent=2)
        hojas = hojas_escaneadas(args.hojas, args.semilla)
        print(f"{len(hojas)} hojas, {sum(map(len, hojas)) / 2**20:.1f} MB", file=sys.stderr)
        for respuesta in cargar(args.url, args.examen, hojas, args.pausa):
            print(json.dumps({k: v for k, v in respuesta.items() if k != "hojas"},
                             ensure_ascii=False))
        return 0

    if args.registro == "-":
        eventos = leer_lineas(sys.stdin)
    else:
        with open(args.registro, encoding="utf-8") as archivo:
            eventos = leer_lineas(archivo)
    print(json.dumps(analizar(eventos, args.examen), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
