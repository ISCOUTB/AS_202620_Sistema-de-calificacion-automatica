"""Sigue un mensaje de la cola de punta a punta, del productor al consumidor, a partir del registro.

Es la métrica de seguimiento del taller de mensajería (ADR-0020). La API y el worker escriben una
línea JSON por evento (`infraestructura/registro.py`), y todos los eventos de un mensaje llevan el
mismo `trabajo` y la misma `hoja`: `trabajo_publicado` en `ingesta`, y `trabajo_tomado`,
`reintento_programado`, `trabajo_repetido`, `trabajo_a_fallidos` y `hoja_recibida` en el worker.
Esta herramienta los junta en orden y dice cómo terminó y cuánto tardó.

Uso, desde backend/, con el registro guardado en un archivo (en local, la salida de error de la API
y del worker; en Render, lo que se descarga de Logs):

    python -m herramientas.seguir_trabajo registro.log --trabajo <trabajo_id>
    python -m herramientas.seguir_trabajo registro.log --hoja <hoja_id>
    python -m herramientas.seguir_trabajo registro.log --todos

Las líneas que no son JSON (lo que imprime uvicorn antes de configurar el registro) se ignoran.
"""

import argparse
import json
import sys
from collections.abc import Iterable
from datetime import datetime
from typing import Any

EVENTOS_DEL_RASTRO = {
    "trabajo_publicado",
    "trabajo_tomado",
    "reintento_programado",
    "trabajo_repetido",
    "trabajo_a_fallidos",
    "hoja_recibida",
}
FINALES = {"hoja_recibida": "procesado", "trabajo_a_fallidos": "en la lista de fallidos"}


def leer_eventos(lineas: Iterable[str]) -> list[dict[str, Any]]:
    """Los eventos del rastro de los mensajes, en el orden del registro."""
    eventos = []
    for linea in lineas:
        try:
            evento = json.loads(linea)
        except ValueError:
            continue
        if isinstance(evento, dict) and evento.get("evento") in EVENTOS_DEL_RASTRO:
            eventos.append(evento)
    return eventos


def rastro(eventos: list[dict[str, Any]], trabajo: str | None = None,
           hoja: str | None = None) -> list[dict[str, Any]]:
    """Los eventos de un trabajo, o de todos los trabajos de una hoja."""
    return [
        e for e in eventos
        if (trabajo is not None and e.get("trabajo") == trabajo)
        or (hoja is not None and e.get("hoja") == hoja)
    ]


def resumen(eventos: list[dict[str, Any]]) -> dict[str, Any]:
    """Cómo terminó un trabajo: el último estado, los intentos y el tiempo de punta a punta."""
    if not eventos:
        return {"estado": "sin eventos"}
    estado = "en camino"
    for evento in eventos:
        if evento["evento"] in FINALES:
            estado = FINALES[evento["evento"]]
        elif evento["evento"] == "trabajo_repetido":
            estado = estado if estado != "en camino" else "repetido"
    intentos = max((e.get("intento", 1) for e in eventos if "intento" in e), default=0)
    momentos = [datetime.fromisoformat(e["momento"]) for e in eventos if "momento" in e]
    total_ms = (
        round((momentos[-1] - momentos[0]).total_seconds() * 1000, 1) if len(momentos) > 1 else 0
    )
    return {
        "trabajo": eventos[0].get("trabajo"),
        "hoja": eventos[0].get("hoja"),
        "estado": estado,
        "intentos": intentos,
        "de_punta_a_punta_ms": total_ms,
        "eventos": [e["evento"] for e in eventos],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sigue un mensaje de la cola en el registro.")
    parser.add_argument("registro", help="archivo con las líneas JSON del registro, o - para stdin")
    grupo = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--trabajo", help="el trabajo_id que se quiere seguir")
    grupo.add_argument("--hoja", help="el hoja_id: muestra todos sus trabajos")
    grupo.add_argument("--todos", action="store_true", help="un resumen por trabajo")
    args = parser.parse_args(argv)

    if args.registro == "-":
        eventos = leer_eventos(sys.stdin)
    else:
        with open(args.registro, encoding="utf-8") as archivo:
            eventos = leer_eventos(archivo)

    if args.todos:
        trabajos = list(dict.fromkeys(e.get("trabajo") for e in eventos if e.get("trabajo")))
        resumenes = [resumen(rastro(eventos, trabajo=t)) for t in trabajos]
        print(json.dumps(resumenes, ensure_ascii=False, indent=2))
        return 0

    elegidos = rastro(eventos, trabajo=args.trabajo, hoja=args.hoja)
    for evento in elegidos:
        detalle = {k: v for k, v in evento.items()
                   if k in {"intento", "espera_en_cola_ms", "espera_s", "motivo", "bytes"}}
        datos = json.dumps(detalle, ensure_ascii=False)
        print(f"{evento.get('momento', '?')}  {evento['evento']:<22} {datos}")
    print(json.dumps(resumen(elegidos), ensure_ascii=False, indent=2))
    return 0 if elegidos else 1


if __name__ == "__main__":
    raise SystemExit(main())
