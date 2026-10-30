"""Sigue un mensaje de la cola de punta a punta, del productor al consumidor, a partir del registro.

Es la métrica de seguimiento del taller de mensajería (ADR-0020). La API y el worker escriben una
línea JSON por evento (`infraestructura/registro.py`), y todos los eventos de un mensaje llevan el
mismo `trabajo` y la misma `hoja`: `trabajo_publicado` en `ingesta`, y `trabajo_tomado`,
`reintento_programado`, `trabajo_repetido`, `trabajo_a_fallidos` y `hoja_recibida` en el worker.
Esta herramienta los junta en orden y dice cómo terminó y cuánto tardó.

Uso, desde backend/, con el registro guardado en un archivo dentro del repositorio (en local, la
salida de error de la API y del worker):

    python -m herramientas.seguir_trabajo registro.log --trabajo <trabajo_id>
    python -m herramientas.seguir_trabajo registro.log --hoja <hoja_id>
    python -m herramientas.seguir_trabajo registro.log --todos

La herramienta no abre archivos de fuera del repositorio, para que una ruta manipulada no la ponga
a leer cualquier archivo de la máquina. Un registro de otra parte, como el que se copia de Logs en
el panel del servidor del laboratorio (uno por contenedor, `api` y `worker`, uno detrás del otro),
entra por la entrada estándar:

    python -m herramientas.seguir_trabajo - --todos < <registro copiado>

Cada línea se lee desde su primera llave, así que la marca de tiempo que el panel antepone no
estorba; las que no traen JSON (lo que imprime uvicorn antes de configurar el registro) se ignoran.
"""

import argparse
import json
import os
import sys
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path
from typing import Any

# Cada evento del rastro con su lugar en el ciclo de un mensaje, para ordenar los que caen en el
# mismo milisegundo: el worker puede tomar un trabajo en el mismo milisegundo en que la API lo
# publica.
EVENTOS_DEL_RASTRO = {
    "trabajo_publicado": 0,
    "trabajo_tomado": 1,
    "reintento_programado": 2,
    "trabajo_repetido": 2,
    "trabajo_a_fallidos": 3,
    "hoja_recibida": 3,
}
FINALES = {"hoja_recibida": "procesado", "trabajo_a_fallidos": "en la lista de fallidos"}
CARPETA_DEL_REPOSITORIO = Path(__file__).resolve().parent.parent.parent


def _ruta_del_registro(nombre: str) -> str:
    """Ruta del registro dentro del repositorio. Se resuelve la ruta canónica y se comprueba que
    siga dentro, con el separador al final para que una carpeta hermana con el mismo prefijo no
    pase la comprobación."""
    base = os.path.realpath(CARPETA_DEL_REPOSITORIO)
    ruta = os.path.realpath(nombre)
    if not ruta.startswith(base + os.sep):
        raise SystemExit(
            f"el registro tiene que estar dentro del repositorio: {nombre!r}. Si está en otra "
            "parte, pásalo por la entrada estándar: - < ruta"
        )
    return ruta


def leer_eventos(lineas: Iterable[str]) -> list[dict[str, Any]]:
    """Los eventos del rastro de los mensajes, en el orden del registro. El JSON se lee desde la
    primera llave, porque el panel del servidor antepone a cada línea su propia marca de tiempo
    (`2026-10-30T04:38:08.792Z {...}`): leída entera, la línea no es JSON y el evento se perdía."""
    eventos = []
    for linea in lineas:
        inicio = linea.find("{")
        if inicio < 0:
            continue
        try:
            evento = json.loads(linea[inicio:])
        except ValueError:
            continue
        if isinstance(evento, dict) and evento.get("evento") in EVENTOS_DEL_RASTRO:
            eventos.append(evento)
    return eventos


def rastro(eventos: list[dict[str, Any]], trabajo: str | None = None,
           hoja: str | None = None) -> list[dict[str, Any]]:
    """Los eventos de un trabajo, o de todos los trabajos de una hoja, en el orden en que pasaron:
    por `momento` y, dentro del mismo milisegundo, por su lugar en el ciclo. El orden del registro
    no basta, porque el panel del servidor muestra el de cada contenedor por separado y, al
    juntarlos, el worker puede quedar antes que la API. `momento` es ISO 8601 en UTC con
    milisegundos (`infraestructura/registro.py`), así que ordenarlo como texto es ordenarlo en el
    tiempo."""
    elegidos = [
        e for e in eventos
        if (trabajo is not None and e.get("trabajo") == trabajo)
        or (hoja is not None and e.get("hoja") == hoja)
    ]
    return sorted(elegidos, key=lambda e: (e.get("momento", ""), EVENTOS_DEL_RASTRO[e["evento"]]))


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
        with open(_ruta_del_registro(args.registro), encoding="utf-8") as archivo:
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
