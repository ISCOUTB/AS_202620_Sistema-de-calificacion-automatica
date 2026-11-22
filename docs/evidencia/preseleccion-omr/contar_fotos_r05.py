"""Cuenta cómo llega a la revisión cada pregunta dudosa de las fotos del prototipo (R-05), con la
preselección de ADR-0024: preseleccionada con lo que se marcó, confusa (sin sugerencia) o con una
sugerencia equivocada. Dice también si el código del estudiante se leyó completo.

Las fotos no están en el repositorio (pesan unos 4 MB cada una). Se corre desde backend/, con
`OMR_FOTOS_R05` apuntando a la carpeta de las fotos, como `tests/test_lectura_fotos_r05.py`:

    OMR_FOTOS_R05=/ruta/a/las/fotos PYTHONPATH=. python ../docs/evidencia/preseleccion-omr/contar_fotos_r05.py

Escribe el informe en la salida estándar; `fotos-r05.json` es esa salida.
"""

import json
import os
import pathlib
import sys

from infraestructura.modelo import CODIGO_COMPLETO, DOBLE_MARCA, DUDOSA
from omr import CORTE_DE_INTENCION_POR_OMISION, leer_hoja

UMBRAL = 70
# Lo que quiso marcar el estudiante en las preguntas difíciles de la hoja (31 a 40); de la 1 a la
# 30 es el patrón A, B, C, D. None donde no quiso nada: en blanco, dos marcas, una marca borrada.
INTENCION: dict[int, str | None] = {
    31: None, 32: None, 33: "B", 34: "B", 35: None, 36: "C", 37: "C", 38: "B", 39: "D", 40: "A",
}


def intencion(numero: int) -> str | None:
    return "ABCD"[(numero - 1) % 4] if numero <= 30 else INTENCION[numero]


def contar(carpeta: pathlib.Path) -> dict:
    informe: dict = {
        "umbral_de_confianza": UMBRAL,
        "corte_de_intencion": CORTE_DE_INTENCION_POR_OMISION,
        "fotos": {},
    }
    for foto in sorted(carpeta.glob("*.jpg")):
        lectura = leer_hoja(foto.read_bytes(), UMBRAL)
        filas = []
        for pregunta in lectura.preguntas:
            if pregunta.estado not in (DUDOSA, DOBLE_MARCA):
                continue
            sugerida = pregunta.opcion_sugerida
            if sugerida is None:
                juicio = "confusa"
            elif sugerida == intencion(pregunta.numero):
                juicio = "preseleccionada_bien"
            else:
                juicio = "equivocada"
            filas.append({
                "pregunta": pregunta.numero,
                "estado": pregunta.estado,
                "sugerida": sugerida,
                "juicio": juicio,
                "confianzas": {b.opcion: b.confianza for b in pregunta.burbujas},
            })
        valor = lectura.codigo.valor or ""
        informe["fotos"][foto.stem] = {
            "en_revision": len(filas),
            "preseleccionadas_bien": sum(f["juicio"] == "preseleccionada_bien" for f in filas),
            "confusas": sum(f["juicio"] == "confusa" for f in filas),
            "equivocadas": sum(f["juicio"] == "equivocada" for f in filas),
            "codigo_completo": lectura.codigo.estado == CODIGO_COMPLETO,
            "codigo_coincide_con_la_hoja": all(
                leido in ("?", esperado) for leido, esperado in zip(valor, "T12345678")
            ),
            "columnas_del_codigo_por_revisar": list(lectura.codigo.columnas_por_revisar),
            "preguntas": filas,
        }
    fotos = informe["fotos"].values()
    informe["total"] = {
        clave: sum(f[clave] for f in fotos)
        for clave in ("en_revision", "preseleccionadas_bien", "confusas", "equivocadas")
    }
    return informe


def main() -> int:
    carpeta = os.environ.get("OMR_FOTOS_R05")
    if not carpeta:
        print("Falta OMR_FOTOS_R05: la carpeta con las fotos del prototipo.", file=sys.stderr)
        return 2
    informe = contar(pathlib.Path(carpeta))
    print(json.dumps(informe, ensure_ascii=False, indent=2))
    return 0 if informe["total"]["equivocadas"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
