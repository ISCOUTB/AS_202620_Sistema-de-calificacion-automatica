"""Mira y opera la cola de trabajos: cuántos hay en cada lista, qué hay en la de fallidos y, cuando
la causa se corrigió, devolverlos a la cola (taller de mensajería, ADR-0020).

La lista de fallidos no se vacía sola a propósito: lo que llega ahí no se arregla insistiendo, y
alguien tiene que mirarlo. Esta herramienta es esa mirada.

Uso, desde backend/, con `REDIS_URL` apuntando a la cola:

    python -m herramientas.cola_de_fallidos                 # cuántos hay en cada lista
    python -m herramientas.cola_de_fallidos --ver           # los fallidos, con su motivo
    python -m herramientas.cola_de_fallidos --reencolar     # los devuelve a la cola

`--reencolar` solo devuelve los que cumplen el contrato del mensaje, con el intento en 1.
"""

import argparse
import json
import os

from infraestructura.cola import cliente_redis
from infraestructura.consumo import clave_fallidos, estado_de_la_cola, reencolar_fallidos


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Estado de la cola y de su lista de fallidos.")
    parser.add_argument("--cola", default=os.environ.get("NOMBRE_COLA", "procesamiento"))
    accion = parser.add_mutually_exclusive_group()
    accion.add_argument("--ver", action="store_true", help="muestra los fallidos con su motivo")
    accion.add_argument(
        "--reencolar", action="store_true",
        help="devuelve a la cola los fallidos que cumplen el contrato, con el intento en 1",
    )
    args = parser.parse_args(argv)
    cliente = cliente_redis()

    if args.ver:
        for registro in cliente.lrange(clave_fallidos(args.cola), 0, -1):
            print(json.dumps(json.loads(registro), ensure_ascii=False))
    elif args.reencolar:
        print(f"Devueltos a la cola: {reencolar_fallidos(cliente, args.cola)}")
    print(json.dumps(estado_de_la_cola(cliente, args.cola), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
