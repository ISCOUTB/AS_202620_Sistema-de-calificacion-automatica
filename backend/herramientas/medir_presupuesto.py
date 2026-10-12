"""Mide el escenario operativo del segundo corte: una ráfaga contra la ruta pública de distractores.

El escenario es de **límite de costo**: `POST /distractores` es pública y cada solicitud gasta cuota
del proveedor de LLM (R-17). La capa gratuita de Groq tiene 8 000 tokens por minuto y 200 000 por
día, y una solicitud gasta unos 856 (medido en la evaluación de EC-08). Esta herramienta lanza una
ráfaga de solicitudes seguidas y registra quién la detiene: nadie, el proveedor o la propia API.

Por cada solicitud guarda el código, el tiempo y el motivo de los rechazos, y la clasifica:

- `propuesta`: 200, el proveedor respondió;
- `limitada_por_la_api`: 429, la API la rechazó sin salir a la red (el presupuesto de ADR-0015);
- `limitada_por_el_proveedor`: 503 cuyo motivo es la cuota del proveedor (Groq respondió 429);
- `proveedor_no_disponible`: otro 503 (tiempo agotado, clave, error del proveedor);
- `otra`: cualquier otro código.

Antes, durante (cada 5 solicitudes) y después de la ráfaga consulta `GET /health`, para comprobar
que el resto de la API sigue atendiendo. Si la API publica `GET /metricas`, la lee antes y después.

Las preguntas son las del conjunto de evaluación de EC-08, en orden, para que la carga sea la
misma en cada corrida. Ningún argumento de la línea de comandos llega a la red ni al sistema de
archivos: `--destino` elige entre dos direcciones fijas, y **la herramienta no escribe archivos**.
El informe completo sale por la salida estándar en JSON (UTF-8) y el avance por la de error, así
que quien la corre decide dónde guardarlo. Es lo que pide SonarCloud (regla S8707) para las
herramientas que un agente de IA podría invocar: las dos versiones anteriores elegían el archivo
con un argumento, validado, y aun así quedaban marcadas.

Uso, desde backend/ (en Git Bash, que guarda la salida tal cual):

    python -m herramientas.medir_presupuesto --destino desplegada --solicitudes 20 \\
        --red "internet residencial, Cartagena" > ../docs/evidencia/presupuesto-despues.json
"""

import argparse
import io
import json
import math
import statistics
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx

API_DESPLEGADA = "https://quantia-utb-api.onrender.com"
API_LOCAL = "http://127.0.0.1:8000"
RAIZ_DEL_REPOSITORIO = Path(__file__).resolve().parent.parent.parent
CARPETA_DE_EVIDENCIA = RAIZ_DEL_REPOSITORIO / "docs" / "evidencia"
CONJUNTO = CARPETA_DE_EVIDENCIA / "conjunto-evaluacion-distractores.json"
CARTAGENA = timezone(timedelta(hours=-5))

# Tokens por solicitud medidos en la corrida oficial de EC-08 (243 de entrada y 613 de salida, en
# promedio). Sirve para estimar lo gastado: la API no devuelve el uso del proveedor.
TOKENS_POR_SOLICITUD = 856

# Espera máxima por solicitud: el adaptador se rinde a los 20 s (ADR-0013); el margen evita que
# la herramienta corte antes de recibir el 503 con su motivo.
ESPERA_POR_SOLICITUD = 30.0


def _url_del_destino(destino: str) -> str:
    """Una de las dos direcciones fijas, elegida con una condición: ningún argumento decide a qué
    servidor se le hacen las peticiones."""
    return API_LOCAL if destino == "local" else API_DESPLEGADA




def _ahora() -> dict[str, str]:
    momento = datetime.now(timezone.utc)
    return {
        "utc": momento.isoformat(timespec="seconds"),
        "cartagena": momento.astimezone(CARTAGENA).isoformat(timespec="seconds"),
    }


def _p95(valores: list[float]) -> float:
    ordenados = sorted(valores)
    return ordenados[max(0, math.ceil(0.95 * len(ordenados)) - 1)]


def _resumen_de_tiempos(valores: list[float]) -> dict[str, Any]:
    if not valores:
        return {"muestras": 0}
    return {
        "muestras": len(valores),
        "mediana_segundos": round(statistics.median(valores), 3),
        "p95_segundos": round(_p95(valores), 3),
        "peor_segundos": round(max(valores), 3),
    }


def _preguntas() -> list[dict[str, str]]:
    datos = json.loads(CONJUNTO.read_text(encoding="utf-8"))
    return [
        {"enunciado": p["enunciado"], "respuesta_correcta": p["respuesta_correcta"]}
        for p in datos["preguntas"]
    ]


def _clasificar(codigo: int, motivo: str) -> str:
    if codigo == 200:
        return "propuesta"
    if codigo == 429:
        return "limitada_por_la_api"
    if codigo == 503 and "cuota" in motivo.lower():
        return "limitada_por_el_proveedor"
    if codigo == 503:
        return "proveedor_no_disponible"
    return "otra"


def _salud(cliente: httpx.Client, url: str, momento: str) -> dict[str, Any]:
    inicio = time.perf_counter()
    codigo: int | str
    try:
        codigo = cliente.get(f"{url}/health", timeout=15).status_code
    except httpx.HTTPError as error:
        codigo = f"error: {type(error).__name__}"
    return {
        "momento": momento,
        "codigo": codigo,
        "segundos": round(time.perf_counter() - inicio, 3),
        "hora": _ahora()["cartagena"],
    }


def _metricas(cliente: httpx.Client, url: str) -> Any:
    try:
        respuesta = cliente.get(f"{url}/metricas", timeout=15)
    except httpx.HTTPError as error:
        return {"error": type(error).__name__}
    if respuesta.status_code != 200:
        return {"codigo": respuesta.status_code}
    return respuesta.json()


def _solicitar(cliente: httpx.Client, url: str, numero: int, pregunta: dict[str, str]) -> dict[str, Any]:
    cuerpo = {**pregunta, "cantidad": 3}
    inicio = time.perf_counter()
    hora = _ahora()["cartagena"]
    try:
        respuesta = cliente.post(f"{url}/distractores", json=cuerpo, timeout=ESPERA_POR_SOLICITUD)
    except httpx.HTTPError as error:
        return {
            "numero": numero, "hora": hora, "codigo": None,
            "segundos": round(time.perf_counter() - inicio, 3),
            "clase": "otra", "motivo": f"{type(error).__name__}",
        }
    segundos = round(time.perf_counter() - inicio, 3)
    motivo = ""
    if respuesta.status_code != 200:
        try:
            motivo = str(respuesta.json().get("detail", ""))
        except ValueError:
            motivo = respuesta.text[:200]
    return {
        "numero": numero,
        "hora": hora,
        "codigo": respuesta.status_code,
        "segundos": segundos,
        "clase": _clasificar(respuesta.status_code, motivo),
        "motivo": motivo,
        "reintentar_en": respuesta.headers.get("retry-after"),
    }


def medir(url: str, solicitudes: int, pausa: float) -> dict[str, Any]:
    preguntas = _preguntas()
    resultados: list[dict[str, Any]] = []
    salud: list[dict[str, Any]] = []
    with httpx.Client() as cliente:
        salud.append(_salud(cliente, url, "antes"))
        metricas_antes = _metricas(cliente, url)
        inicio = _ahora()
        reloj = time.perf_counter()
        for numero in range(1, solicitudes + 1):
            pregunta = preguntas[(numero - 1) % len(preguntas)]
            resultado = _solicitar(cliente, url, numero, pregunta)
            resultados.append(resultado)
            print(f"  {numero:3} -> {resultado['codigo']} {resultado['clase']:26} {resultado['segundos']:6.2f} s",
                  file=sys.stderr)
            if numero % 5 == 0:
                salud.append(_salud(cliente, url, f"durante, tras la solicitud {numero}"))
            if pausa:
                time.sleep(pausa)
        duracion = round(time.perf_counter() - reloj, 1)
        fin = _ahora()
        salud.append(_salud(cliente, url, "después"))
        metricas_despues = _metricas(cliente, url)

    clases = ["propuesta", "limitada_por_la_api", "limitada_por_el_proveedor",
              "proveedor_no_disponible", "otra"]
    conteo = {clase: sum(1 for r in resultados if r["clase"] == clase) for clase in clases}
    llegaron = conteo["propuesta"] + conteo["limitada_por_el_proveedor"] + conteo["proveedor_no_disponible"]
    return {
        "inicio": inicio,
        "fin": fin,
        "duracion_de_la_rafaga_segundos": duracion,
        "resumen": {
            "solicitudes": solicitudes,
            "por_clase": conteo,
            "llegaron_al_proveedor": llegaron,
            "tokens_gastados_estimados": conteo["propuesta"] * TOKENS_POR_SOLICITUD,
            "tiempos_por_clase": {
                clase: _resumen_de_tiempos([r["segundos"] for r in resultados if r["clase"] == clase])
                for clase in clases
            },
            "salud_siempre_200": all(s["codigo"] == 200 for s in salud),
        },
        "salud": salud,
        "metricas_antes": metricas_antes,
        "metricas_despues": metricas_despues,
        "solicitudes": resultados,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Mide una ráfaga contra POST /distractores (escenario de límite de costo).")
    parser.add_argument("--destino", choices=["desplegada", "local"], default="desplegada",
                        help=f"desplegada: {API_DESPLEGADA} · local: {API_LOCAL}")
    parser.add_argument("--solicitudes", type=int, default=20)
    parser.add_argument("--pausa", type=float, default=0.0,
                        help="segundos entre una solicitud y la siguiente")
    parser.add_argument("--red", default="sin declarar")
    parser.add_argument("--etiqueta", default="", help="por ejemplo «antes» o «después»")
    args = parser.parse_args(argv)

    url = _url_del_destino(args.destino)
    print(f"Ráfaga de {args.solicitudes} solicitudes contra {url}/distractores", file=sys.stderr)
    informe = {
        "herramienta": "backend/herramientas/medir_presupuesto.py",
        "etiqueta": args.etiqueta,
        "entorno": {"destino": args.destino, "url": url, "red": args.red,
                    "solicitudes": args.solicitudes, "pausa_segundos": args.pausa,
                    "tokens_por_solicitud_supuestos": TOKENS_POR_SOLICITUD},
        **medir(url, args.solicitudes, args.pausa),
    }
    # El resumen, para quien mira la consola; el informe completo, para quien lo guarda. UTF-8
    # aunque la consola de Windows use otra página de códigos: el JSON lleva tildes.
    print(json.dumps(informe["resumen"], ensure_ascii=False, indent=2), file=sys.stderr)
    salida = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", newline="\n")
    salida.write(json.dumps(informe, ensure_ascii=False, indent=2) + "\n")
    salida.flush()
    salida.detach()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
