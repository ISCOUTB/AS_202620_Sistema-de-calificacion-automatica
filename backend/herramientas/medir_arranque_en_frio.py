"""Mide el arranque en frío de la API desplegada frente al umbral de EC-07.

Existe para el taller de despliegue de la semana 8, cuya condición operativa es el **patrón de
carga**: la API de QuantIA recibe la carga en ráfagas (un lote de hojas justo después de cada
examen) separadas por días sin uso. En la capa gratuita de Render el servicio se apaga tras
15 minutos sin tráfico, así que la primera petición de cada ráfaga paga el arranque. Este
archivo convierte esa frase en una cifra medida con procedimiento reproducible.

Qué mide
--------
1. **En frío.** Antes de cada muestra espera sin enviar nada (16 minutos por omisión, uno más
   que el apagado de Render) y luego manda una sola petición: `GET /health`, o un lote real a
   `POST /examenes/{id}/hojas`, alternando. Registra hora, código y segundos.
2. **En caliente.** Con el servicio ya despierto, una serie de `GET /health` y otra de lotes,
   seguidas, de las que saca la mediana, el p95 y el peor caso.

Contra qué se compara
---------------------
- **EC-07: confirmación del lote en <= 10 s** (arc42 §10.3).
- **La espera de 5 s de la pantalla de inicio** (`frontend/lib/servicio_salud.dart`): si
  `/health` tarda más, la pantalla dice que el backend no responde y no ofrece cargar hojas.

Qué no mide
-----------
El tiempo de un lote se toma desde el cliente, así que incluye la subida de los archivos por
la red de quien mide. Por eso se reporta también la diferencia entre el lote en frío y la
mediana en caliente con el mismo lote y desde la misma red: esa diferencia es lo que añade el
arranque, y no depende del ancho de banda de subida. Las hojas son JPEG sintéticos, como en
`medir_ec07.py`: el entorno desplegado es de demostración y no recibe hojas de estudiantes.

Para que la medición en frío sea válida, **nadie más puede usar el servicio durante las
esperas** y cualquier monitor que lo mantenga despierto tiene que estar apagado.

A qué apunta y dónde escribe
----------------------------
La URL no se recibe por la línea de comandos: `--destino` elige entre la API desplegada y la que
corre en local, y las dos direcciones están escritas abajo, en `API_DESPLEGADA` y `API_LOCAL`. El
informe se escribe solo dentro de `docs/evidencia/`, y `--json` recibe el nombre del archivo, no
una ruta. Las dos cosas cierran los hallazgos de SonarQube Cloud sobre herramientas de línea de
comandos que un agente de IA podría invocar con argumentos manipulados: con una URL libre, la
herramienta podía usarse para hacer peticiones a cualquier servidor, y con una ruta libre, para
escribir en cualquier archivo. Si la URL de la API cambia, se cambia aquí y en `render.yaml`.

Uso
---
    python -m herramientas.medir_arranque_en_frio --json medicion-arranque-en-frio.json
    python -m herramientas.medir_arranque_en_frio --destino desplegada \\
        --frio-salud 3 --frio-lote 2 --espera-min 16 --caliente 30 --lote-hojas 20 --kb 200 \\
        --red "datos moviles, fuera de la red de la universidad" --json medicion.json

Con los valores por omisión tarda unas dos horas: cada muestra en frío espera 16 minutos.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import platform
import statistics
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx

UMBRAL_EC07_SEGUNDOS = 10.0
ESPERA_DE_LA_PANTALLA_SEGUNDOS = 5.0
APAGADO_DE_RENDER_MINUTOS = 15
CABECERA_JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
CARTAGENA = timezone(timedelta(hours=-5))

API_DESPLEGADA = "https://quantia-utb-api.onrender.com"
API_LOCAL = "http://127.0.0.1:8000"
CARPETA_DE_EVIDENCIA = Path(__file__).resolve().parent.parent.parent / "docs" / "evidencia"


def _url_del_destino(destino: str) -> str:
    """Devuelve una de las dos direcciones fijas. Se elige con una condición y no se arma con lo
    que llega por la línea de comandos, para que ningún argumento decida a qué servidor se le
    hacen las peticiones."""
    return API_LOCAL if destino == "local" else API_DESPLEGADA


def _ruta_del_informe(nombre: str) -> Path:
    """Ruta del informe dentro de `docs/evidencia/`. Se resuelve la ruta canónica y se comprueba
    que siga dentro de esa carpeta, con el separador al final para que una carpeta hermana con el
    mismo prefijo no pase la comprobación."""
    base = os.path.realpath(CARPETA_DE_EVIDENCIA)
    ruta = os.path.realpath(os.path.join(base, nombre))
    if not ruta.startswith(base + os.sep):
        raise SystemExit(
            f"--json tiene que ser un nombre de archivo dentro de docs/evidencia/: {nombre!r}"
        )
    return Path(ruta)


def _p95(valores: list[float]) -> float:
    """Percentil 95 por rango más cercano: el valor que deja por debajo al 95 % de las
    muestras. Con 20 muestras es la segunda peor, que es lo que un p95 significa."""
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
        "mejor_segundos": round(min(valores), 3),
    }


def _ahora() -> dict[str, str]:
    momento = datetime.now(timezone.utc)
    return {
        "utc": momento.isoformat(timespec="seconds"),
        "cartagena": momento.astimezone(CARTAGENA).isoformat(timespec="seconds"),
    }


def _lote(hojas: int, kilobytes: int) -> list[tuple[str, tuple[str, bytes, str]]]:
    contenido = CABECERA_JPEG + bytes(kilobytes * 1024 - len(CABECERA_JPEG))
    return [
        ("archivos", (f"hoja-{i:03d}.jpg", contenido, "image/jpeg"))
        for i in range(1, hojas + 1)
    ]


def _pedir_salud(cliente: httpx.Client, url: str) -> dict[str, Any]:
    inicio = time.perf_counter()
    try:
        respuesta = cliente.get(f"{url}/health")
        codigo: int | str = respuesta.status_code
    except httpx.HTTPError as error:
        codigo = f"error: {type(error).__name__}"
    return {"peticion": "GET /health", "codigo": codigo,
            "segundos": round(time.perf_counter() - inicio, 3)}


def _pedir_lote(cliente: httpx.Client, url: str, hojas: int, kilobytes: int) -> dict[str, Any]:
    archivos = _lote(hojas, kilobytes)
    inicio = time.perf_counter()
    detalle: dict[str, Any] = {}
    try:
        respuesta = cliente.post(f"{url}/examenes/medicion-arranque/hojas", files=archivos)
        codigo: int | str = respuesta.status_code
        if respuesta.status_code == 200:
            cuerpo = respuesta.json()
            aceptadas = cuerpo.get("aceptadas", [])
            detalle = {
                "aceptadas": len(aceptadas),
                "rechazados": len(cuerpo.get("rechazados", [])),
                "pendientes_de_encolar": sum(
                    1 for hoja in aceptadas if hoja.get("estado") == "pendiente_de_encolar"
                ),
            }
    except httpx.HTTPError as error:
        codigo = f"error: {type(error).__name__}"
    return {"peticion": f"POST lote de {hojas} hojas de {kilobytes} KB", "codigo": codigo,
            "segundos": round(time.perf_counter() - inicio, 3), **detalle}


def _esperar(minutos: float, motivo: str) -> None:
    fin = datetime.now(CARTAGENA) + timedelta(minutes=minutos)
    print(f"  esperando {minutos:g} min sin tráfico ({motivo}); sigue a las "
          f"{fin:%H:%M:%S} de Cartagena", file=sys.stderr, flush=True)
    time.sleep(minutos * 60)


def medir_en_frio(cliente: httpx.Client, url: str, salud: int, lotes: int, espera_min: float,
                  hojas: int, kilobytes: int) -> list[dict[str, Any]]:
    # Alterna los dos tipos de petición para que ninguno quede concentrado en una misma hora.
    orden = []
    for i in range(max(salud, lotes)):
        if i < salud:
            orden.append("salud")
        if i < lotes:
            orden.append("lote")
    muestras = []
    for n, tipo in enumerate(orden, start=1):
        _esperar(espera_min, f"muestra en frío {n} de {len(orden)}")
        momento = _ahora()
        resultado = (_pedir_salud(cliente, url) if tipo == "salud"
                     else _pedir_lote(cliente, url, hojas, kilobytes))
        muestras.append({"muestra": n, **momento, **resultado})
        print(f"  frío {n}: {resultado['peticion']} -> {resultado['codigo']} en "
              f"{resultado['segundos']} s", file=sys.stderr, flush=True)
    return muestras


def medir_en_caliente(cliente: httpx.Client, url: str, salud: int, lotes: int, hojas: int,
                      kilobytes: int) -> dict[str, Any]:
    despertar = _pedir_salud(cliente, url)
    print(f"  despertar: {despertar['codigo']} en {despertar['segundos']} s",
          file=sys.stderr, flush=True)
    series_salud = [_pedir_salud(cliente, url) for _ in range(salud)]
    series_lote = [_pedir_lote(cliente, url, hojas, kilobytes) for _ in range(lotes)]
    return {
        "inicio": _ahora(),
        "peticion_para_despertar": despertar,
        "salud": series_salud,
        "lotes": series_lote,
    }


def _entorno(args: argparse.Namespace, url: str) -> dict[str, Any]:
    return {
        "medido_desde_la_red": args.red,
        "url": url,
        "python": platform.python_version(),
        "httpx": httpx.__version__,
        "espera_antes_de_cada_muestra_en_frio_min": args.espera_min,
        "apagado_por_inactividad_de_render_min": APAGADO_DE_RENDER_MINUTOS,
        "lote": {"hojas": args.lote_hojas, "kb_por_hoja": args.kb,
                 "megabytes": round(args.lote_hojas * args.kb / 1024, 2)},
        "hojas": "JPEG sintéticos; el entorno de demostración no recibe hojas de estudiantes",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Mide el arranque en frío de la API desplegada frente a EC-07.")
    parser.add_argument("--destino", choices=["desplegada", "local"], default="desplegada",
                        help=f"desplegada: {API_DESPLEGADA} · local: {API_LOCAL}")
    parser.add_argument("--frio-salud", type=int, default=3)
    parser.add_argument("--frio-lote", type=int, default=2)
    parser.add_argument("--espera-min", type=float, default=16.0)
    parser.add_argument("--caliente", type=int, default=30, help="GET /health en caliente")
    parser.add_argument("--caliente-lotes", type=int, default=5)
    parser.add_argument("--lote-hojas", type=int, default=20)
    parser.add_argument("--kb", type=int, default=200)
    parser.add_argument("--red", default="sin declarar")
    parser.add_argument("--json", default=None,
                        help="nombre del archivo del informe, que se escribe en docs/evidencia/")
    args = parser.parse_args(argv)
    url = _url_del_destino(args.destino)
    ruta_del_informe = _ruta_del_informe(args.json) if args.json else None

    inicio = _ahora()
    with httpx.Client(timeout=httpx.Timeout(180.0),
                      headers={"User-Agent": "quantia-medir-arranque-en-frio/1.0"}) as cliente:
        frio = medir_en_frio(cliente, url, args.frio_salud, args.frio_lote, args.espera_min,
                             args.lote_hojas, args.kb)
        caliente = medir_en_caliente(cliente, url, args.caliente, args.caliente_lotes,
                                     args.lote_hojas, args.kb)

    frio_salud = [m["segundos"] for m in frio if m["peticion"] == "GET /health"]
    frio_lote = [m["segundos"] for m in frio if m["peticion"].startswith("POST")]
    caliente_salud = [m["segundos"] for m in caliente["salud"]]
    caliente_lote = [m["segundos"] for m in caliente["lotes"]]
    base_lote = statistics.median(caliente_lote) if caliente_lote else None

    informe: dict[str, Any] = {
        "escenario": "EC-07 - Confirmacion fiable de recepcion del lote (<= 10 s)",
        "condicion_operativa": "patron de carga",
        "pieza": "API (servicio api)",
        "inicio": inicio,
        "fin": _ahora(),
        "entorno": _entorno(args, url),
        "muestras_en_frio": frio,
        "muestras_en_caliente": caliente,
        "resumen": {
            "salud_en_frio": _resumen(frio_salud),
            "salud_en_caliente": _resumen(caliente_salud),
            "lote_en_frio": _resumen(frio_lote),
            "lote_en_caliente": _resumen(caliente_lote),
            "segundos_que_agrega_el_arranque_al_lote": (
                [round(s - base_lote, 3) for s in frio_lote] if base_lote is not None else None
            ),
            "umbral_ec07_segundos": UMBRAL_EC07_SEGUNDOS,
            "espera_de_la_pantalla_de_inicio_segundos": ESPERA_DE_LA_PANTALLA_SEGUNDOS,
            "salud_en_frio_supera_la_espera_de_la_pantalla": (
                max(frio_salud) > ESPERA_DE_LA_PANTALLA_SEGUNDOS if frio_salud else None
            ),
            "lote_en_frio_cumple_ec07": (
                max(frio_lote) <= UMBRAL_EC07_SEGUNDOS if frio_lote else None
            ),
            "lote_en_caliente_p95_cumple_ec07": (
                _p95(caliente_lote) <= UMBRAL_EC07_SEGUNDOS if caliente_lote else None
            ),
        },
    }

    texto = json.dumps(informe, indent=2, ensure_ascii=False)
    print(texto)
    if ruta_del_informe is not None:
        with open(ruta_del_informe, "w", encoding="utf-8", newline="\n") as salida:
            salida.write(texto + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
