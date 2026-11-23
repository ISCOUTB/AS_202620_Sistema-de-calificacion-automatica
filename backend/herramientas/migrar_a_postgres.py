"""Copia a Postgres lo que ya está en los registros `.jsonl` (ADR-0027).

Al poner `DATABASE_URL`, la API y el worker dejan de leer los archivos: sin este paso, las hojas
que ya se habían subido desaparecerían de las pantallas (las imágenes siguen en el volumen). Esta
herramienta lee la bitácora, los resultados y las revisiones, hecho por hecho y en orden, y los
inserta en las tablas con su misma fecha. No borra ni cambia los archivos.

Se corre **una sola vez**, con las tablas vacías: si ya tienen filas se niega, para no duplicar
hechos (`--forzar` la obliga). Una línea que no se puede leer se salta, como hacen los adaptadores
de disco, y se cuenta.

En el servidor no hay que correrla a mano: la API la corre al arrancar con `--si-hace-falta`
(`deploy/compose.lab.yaml`). En ese modo migra solo si la bitácora de la base está vacía, que es la
señal de que nunca se migró: solo la API la escribe, y todavía no atiende. El worker pudo guardar
algún resultado antes, y eso no impide migrar. Si ya tiene datos, no hace nada.

Uso, desde backend/ (o dentro del contenedor de la API, que ya tiene las variables):

    python -m herramientas.migrar_a_postgres
    docker compose exec api python -m herramientas.migrar_a_postgres
"""

import argparse
import json
import os
import sys
from pathlib import Path

import psycopg
from psycopg.types.json import Jsonb

from infraestructura.almacen import RUTA_ALMACEN_POR_OMISION
from infraestructura.base_de_datos import crear_esquema
from infraestructura.resultados import RUTA_RESULTADOS_POR_OMISION
from infraestructura.revisiones import RUTA_REVISIONES_POR_OMISION

TABLAS = ("bitacora_de_recepcion", "resultados_de_lectura", "revisiones_del_profesor")


def _hechos(ruta: Path) -> tuple[list[dict], int]:
    if not ruta.exists():
        return [], 0
    hechos, malas = [], 0
    for linea in ruta.read_text(encoding="utf-8", errors="replace").splitlines():
        if not linea.strip():
            continue
        try:
            hecho = json.loads(linea)
        except ValueError:
            malas += 1
            continue
        if isinstance(hecho, dict):
            hechos.append(hecho)
        else:
            malas += 1
    return hechos, malas


def migrar(
    url: str,
    bitacora: Path,
    resultados: Path,
    revisiones: Path,
    forzar: bool,
    si_hace_falta: bool = False,
) -> dict:
    crear_esquema(url)
    cuenta = {"bitacora": 0, "resultados": 0, "revisiones": 0, "lineas_saltadas": 0}
    with psycopg.connect(url) as conexion:
        if si_hace_falta:
            fila = conexion.execute(
                "SELECT EXISTS (SELECT 1 FROM bitacora_de_recepcion)"
            ).fetchone()
            if fila is not None and fila[0]:
                return {"omitida": "la bitácora de la base ya tiene datos"}
        ocupadas = []
        for tabla in TABLAS:
            fila = conexion.execute(f"SELECT EXISTS (SELECT 1 FROM {tabla})").fetchone()
            if fila is not None and fila[0]:
                ocupadas.append(tabla)
        if ocupadas and not (forzar or si_hace_falta):
            raise SystemExit(
                f"Las tablas {', '.join(ocupadas)} ya tienen datos: no se migra para no duplicar. "
                "Usa --forzar si de verdad quieres agregar todo otra vez."
            )

        hechos, malas = _hechos(bitacora)
        cuenta["lineas_saltadas"] += malas
        for hecho in hechos:
            if hecho.get("hecho") not in ("recibida", "encolada") or "trabajo_id" not in hecho:
                cuenta["lineas_saltadas"] += 1
                continue
            conexion.execute(
                "INSERT INTO bitacora_de_recepcion (hecho, trabajo_id, hoja_id, examen_id,"
                " referencia, nombre_archivo, momento)"
                " VALUES (%s, %s, %s, %s, %s, %s, COALESCE(%s::timestamptz, now()))",
                (
                    hecho["hecho"],
                    hecho["trabajo_id"],
                    hecho.get("hoja_id"),
                    hecho.get("examen_id"),
                    hecho.get("referencia"),
                    hecho.get("nombre_archivo"),
                    hecho.get("momento"),
                ),
            )
            cuenta["bitacora"] += 1

        hechos, malas = _hechos(resultados)
        cuenta["lineas_saltadas"] += malas
        for hecho in hechos:
            calificacion = hecho.get("calificacion") or {}
            try:
                conexion.execute(
                    "INSERT INTO resultados_de_lectura (hecho, hoja_id, trabajo_id, examen_id,"
                    " estado, nota_en_decimas, provisional, documento, momento)"
                    " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, COALESCE(%s::timestamptz, now()))",
                    (
                        hecho["hecho"],
                        hecho["hoja_id"],
                        hecho["trabajo_id"],
                        hecho["examen_id"],
                        hecho["estado"],
                        calificacion.get("nota_en_decimas"),
                        calificacion.get("provisional"),
                        Jsonb(hecho),
                        hecho.get("momento"),
                    ),
                )
            except KeyError:
                cuenta["lineas_saltadas"] += 1
                continue
            cuenta["resultados"] += 1

        hechos, malas = _hechos(revisiones)
        cuenta["lineas_saltadas"] += malas
        for hecho in hechos:
            try:
                conexion.execute(
                    "INSERT INTO revisiones_del_profesor (hoja_id, examen_id, documento, momento)"
                    " VALUES (%s, %s, %s, COALESCE(%s::timestamptz, now()))",
                    (hecho["hoja_id"], hecho["examen_id"], Jsonb(hecho), hecho.get("momento")),
                )
            except KeyError:
                cuenta["lineas_saltadas"] += 1
                continue
            cuenta["revisiones"] += 1
    return cuenta


def main(argv: list[str] | None = None) -> int:
    almacen = os.environ.get("RUTA_ALMACEN", RUTA_ALMACEN_POR_OMISION)
    parser = argparse.ArgumentParser(description="Copia los registros .jsonl a Postgres.")
    parser.add_argument("--url", default=os.environ.get("DATABASE_URL", ""))
    parser.add_argument(
        "--bitacora",
        default=os.environ.get(
            "RUTA_BITACORA", os.path.join(almacen, "bitacora-de-recepcion.jsonl")
        ),
    )
    parser.add_argument(
        "--resultados", default=os.environ.get("RUTA_RESULTADOS", RUTA_RESULTADOS_POR_OMISION)
    )
    parser.add_argument(
        "--revisiones", default=os.environ.get("RUTA_REVISIONES", RUTA_REVISIONES_POR_OMISION)
    )
    parser.add_argument("--forzar", action="store_true")
    parser.add_argument(
        "--si-hace-falta",
        action="store_true",
        help="migra solo si la bitácora de la base está vacía; si no, no hace nada",
    )
    args = parser.parse_args(argv)
    if not args.url:
        if args.si_hace_falta:
            return 0
        print("Falta DATABASE_URL (o --url).", file=sys.stderr)
        return 2
    cuenta = migrar(
        args.url,
        Path(args.bitacora),
        Path(args.resultados),
        Path(args.revisiones),
        args.forzar,
        args.si_hace_falta,
    )
    print(json.dumps(cuenta, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
