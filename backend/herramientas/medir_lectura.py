"""Mide EC-01 y EC-02 de la lectura OMR (A-02) sobre hojas sintéticas.

- **EC-01:** ≥98 % de exactitud en la marca correcta, sobre 300 hojas.
- **EC-02:** ≥99 % de las marcas ambiguas (doble marca, tenue, media burbuja, chulo, X) va a
  revisión manual, sin calificaciones erróneas silenciosas.

Qué mide y qué no
-----------------
EC-01 pide 300 hojas escaneadas con etiquetado manual (R-01), y ese conjunto no existe todavía.
Mientras tanto, esta herramienta genera hojas con la plantilla real, marca cada pregunta con un
tipo de marca al azar y la «fotografía» con condiciones al azar: perspectiva, giro, sombra,
desenfoque, ruido, compresión y resolución. Como la hoja se genera, la respuesta correcta se
conoce sin etiquetar a mano.

Lo que no reproduce es lo que un generador no sabe imitar: el papel arrugado, la tinta real y el
brillo del grafito bajo una luz cualquiera. Para eso están las fotos del prototipo (R-05), que se
prueban aparte (`tests/test_lectura_fotos_r05.py`). Estas cifras dicen si la lógica de la lectura
cumple dentro de las condiciones que se generaron, no que cumpla con cualquier foto.

Cada pregunta termina en uno de tres resultados:

- **bien:** lo que debía leerse (la opción marcada, sin marca, doble marca o a revisión);
- **a revisión:** fue a revisión manual sin necesitarlo. Cuesta tiempo al profesor, pero no es un
  error;
- **error silencioso:** una respuesta asignada que no era, o una marca leída como vacía. Es lo que
  EC-02 y QG-3 prohíben.

Uso, desde backend/
-------------------
    python -m herramientas.medir_lectura                       # 300 hojas, semilla 2026
    python -m herramientas.medir_lectura --hojas 50 --json medicion.json
"""

import argparse
import json
import statistics
import sys
import time
from collections import Counter
from dataclasses import dataclass

import numpy as np

from herramientas.hojas_sinteticas import (
    BORRADA,
    BRILLO,
    CHULO,
    COMPLETA,
    EQUIS,
    MEDIA,
    TENUE,
    Foto,
    Marca,
    fotografiar,
    hoja_en_blanco,
    marcar,
)
from infraestructura.modelo import DOBLE_MARCA, DUDOSA, SIN_MARCA, UNA_MARCA
from omr import FORMATO_V1, LecturaImposible, leer_hoja

UMBRAL = 70
OPCIONES = "ABCD"

# Cómo se marcó cada pregunta y con qué frecuencia. Las claras son la mayoría, como en un examen.
CLARA = "clara"
EN_BLANCO = "en_blanco"
DOBLE = "doble"
BORRADA_Y_OTRA = "borrada_y_otra"
SOLO_BORRADA = "solo_borrada"
CON_BRILLO = "con_brillo"
CASOS = {
    CLARA: 0.78,
    EN_BLANCO: 0.08,
    DOBLE: 0.02,
    MEDIA: 0.02,
    TENUE: 0.02,
    CHULO: 0.015,
    EQUIS: 0.015,
    SOLO_BORRADA: 0.02,
    BORRADA_Y_OTRA: 0.02,
    CON_BRILLO: 0.01,
}
# Las marcas que EC-02 llama ambiguas: no se puede saber, sin mirar, qué quiso el estudiante.
AMBIGUAS = {DOBLE, MEDIA, TENUE, CHULO, EQUIS}

# Las condiciones de la foto, al azar entre estos extremos y dentro de lo que la lectura acepta:
# la resolución va de 9,4 a 13 px/mm, la de una foto de celular de la hoja entera, y con la
# perspectiva el lado más angosto no baja de 8. La lectura rechaza por debajo de 7,5.
ESCALA = (0.8, 1.1)
PERSPECTIVA = (0.0, 0.15)
DESENFOQUE_PX = (0.0, 1.2)
RUIDO = (2.0, 6.0)
CALIDAD_JPEG = (65, 95)
PROBABILIDAD_DE_SOMBRA = 0.3
SOMBRA = (0.4, 0.8)
PROBABILIDAD_DE_GIRO = 0.3


@dataclass(frozen=True)
class Pregunta:
    caso: str
    opcion: str | None  # la que el estudiante quiso marcar, si hay una


def _marca_clara(azar: np.random.Generator) -> Marca:
    """Lápiz o esfero, más o menos cargado, que no siempre llena el círculo ni queda centrado."""
    return Marca(
        COMPLETA,
        oscuridad=float(azar.uniform(0.45, 0.8)),
        tamano=float(azar.uniform(0.8, 1.12)),
        corrimiento_mm=(float(azar.uniform(-0.4, 0.4)), float(azar.uniform(-0.4, 0.4))),
    )


def generar_hoja(
    azar: np.random.Generator, foto: Foto | None = None
) -> tuple[bytes, list[Pregunta], str]:
    """Una hoja marcada y fotografiada, con lo que debía leerse: las preguntas y el código. Sin
    `foto`, las condiciones de la foto también salen al azar."""
    hoja = hoja_en_blanco()
    codigo = "".join(str(d) for d in azar.integers(0, 10, 8))
    for posicion, digito in enumerate(codigo, start=1):
        marcar(hoja, FORMATO_V1.centro_del_digito_mm(posicion, int(digito)), _marca_clara(azar), azar)

    preguntas = []
    casos, pesos = list(CASOS), np.array(list(CASOS.values()))
    for numero in range(1, FORMATO_V1.numero_de_preguntas() + 1):
        caso = str(azar.choice(casos, p=pesos / pesos.sum()))
        a, b = (OPCIONES[int(i)] for i in azar.choice(4, 2, replace=False))

        def en(letra: str, marca: Marca) -> None:
            marcar(hoja, FORMATO_V1.centro_de_la_respuesta_mm(numero, OPCIONES.index(letra)),
                   marca, azar)

        opcion: str | None = a
        if caso == CLARA:
            en(a, _marca_clara(azar))
        elif caso == EN_BLANCO:
            opcion = None
        elif caso == DOBLE:
            en(a, _marca_clara(azar))
            en(b, _marca_clara(azar))
            opcion = None
        elif caso == MEDIA:
            en(a, Marca(MEDIA, oscuridad=float(azar.uniform(0.45, 0.8)),
                        giro=float(azar.uniform(0, 2 * np.pi))))
        elif caso == TENUE:
            # Por debajo del corte de tinta: entre 15 % y 25 % más oscura que el papel.
            en(a, Marca(TENUE, oscuridad=float(azar.uniform(0.15, 0.25))))
        elif caso in (CHULO, EQUIS):
            en(a, Marca(caso, oscuridad=float(azar.uniform(0.45, 0.8))))
        elif caso == SOLO_BORRADA:
            en(a, Marca(BORRADA, oscuridad=float(azar.uniform(0.03, 0.09))))
            opcion = None
        elif caso == BORRADA_Y_OTRA:
            en(b, Marca(BORRADA, oscuridad=float(azar.uniform(0.03, 0.09))))
            en(a, _marca_clara(azar))
        elif caso == CON_BRILLO:
            # Entre la del código de la foto desde arriba y la más oscura de las fotos.
            en(a, Marca(BRILLO, oscuridad=float(azar.uniform(0.15, 0.3))))
        preguntas.append(Pregunta(caso, opcion))

    if foto is not None:
        return fotografiar(hoja, foto), preguntas, codigo
    foto = Foto(
        giro=int(azar.integers(1, 4)) if azar.random() < PROBABILIDAD_DE_GIRO else 0,
        perspectiva=float(azar.uniform(*PERSPECTIVA)),
        sombra=float(azar.uniform(*SOMBRA)) if azar.random() < PROBABILIDAD_DE_SOMBRA else 1.0,
        escala=float(azar.uniform(*ESCALA)),
        desenfoque_px=float(azar.uniform(*DESENFOQUE_PX)),
        ruido=float(azar.uniform(*RUIDO)),
        calidad_jpeg=int(azar.integers(CALIDAD_JPEG[0], CALIDAD_JPEG[1] + 1)),
        semilla=int(azar.integers(0, 2**31)),
    )
    return fotografiar(hoja, foto), preguntas, codigo


def juzgar(pregunta: Pregunta, estado: str, opcion: str | None) -> str:
    """`bien`, `a_revision` o `error_silencioso` para lo que se leyó en una pregunta."""
    leida = (estado, opcion)
    if pregunta.caso in (CLARA, BORRADA_Y_OTRA, CON_BRILLO):
        if leida == (UNA_MARCA, pregunta.opcion):
            return "bien"
        return "a_revision" if estado in (DUDOSA, DOBLE_MARCA) else "error_silencioso"
    if pregunta.caso in (EN_BLANCO, SOLO_BORRADA):
        if estado == SIN_MARCA:
            return "bien"
        return "a_revision" if estado in (DUDOSA, DOBLE_MARCA) else "error_silencioso"
    # Las ambiguas: lo bien es que vayan a revisión. Asignarlas o darlas por vacías es silencioso.
    return "bien" if estado in (DUDOSA, DOBLE_MARCA) else "error_silencioso"


def medir(hojas: int = 300, semilla: int = 2026) -> dict:
    azar = np.random.default_rng(semilla)
    resultados: dict[str, Counter[str]] = {caso: Counter() for caso in CASOS}
    silenciosos = []
    ilegibles: Counter[str] = Counter()
    codigos: Counter[str] = Counter()
    duraciones = []
    for indice in range(hojas):
        imagen, preguntas, codigo = generar_hoja(azar)
        inicio = time.perf_counter()
        try:
            lectura = leer_hoja(imagen, UMBRAL)
        except LecturaImposible as error:
            ilegibles[error.motivo] += 1
            continue
        duraciones.append((time.perf_counter() - inicio) * 1000)
        for pregunta, leida in zip(preguntas, lectura.preguntas, strict=True):
            juicio = juzgar(pregunta, leida.estado, leida.opcion)
            resultados[pregunta.caso][juicio] += 1
            if juicio == "error_silencioso":
                silenciosos.append({"hoja": indice, "pregunta": leida.numero, "caso": pregunta.caso,
                                    "esperada": pregunta.opcion, "leida": [leida.estado, leida.opcion]})
        valor = lectura.codigo.valor or ""
        if valor == "T" + codigo:
            codigos["completo_y_correcto"] += 1
        elif all(leido in ("?", esperado) for leido, esperado in zip(valor, "T" + codigo)):
            codigos["con_columnas_a_revision"] += 1
        else:
            codigos["con_un_digito_mal_leido"] += 1

    def total(casos, juicio=None):
        return sum(resultados[c][juicio] if juicio else sum(resultados[c].values()) for c in casos)

    claras = total([CLARA])
    ambiguas = total(AMBIGUAS)
    leidas = len(duraciones)
    return {
        "hojas_generadas": hojas,
        "semilla": semilla,
        "umbral_de_confianza": UMBRAL,
        "hojas_ilegibles": dict(ilegibles),
        "ec01_exactitud_en_marcas_claras": round(total([CLARA], "bien") / claras, 4) if claras else None,
        "ec01_cumple": claras > 0 and total([CLARA], "bien") / claras >= 0.98,
        "ec02_ambiguas_a_revision": round(total(AMBIGUAS, "bien") / ambiguas, 4) if ambiguas else None,
        "ec02_cumple": ambiguas > 0 and total(AMBIGUAS, "bien") / ambiguas >= 0.99,
        "errores_silenciosos": len(silenciosos),
        "preguntas_a_revision_por_hoja": round(
            sum(r["a_revision"] for r in resultados.values()) / leidas, 2) if leidas else None,
        "por_caso": {caso: dict(conteo) for caso, conteo in resultados.items()},
        "codigos": dict(codigos),
        "lectura_ms": {
            "p50": round(statistics.median(duraciones), 1) if duraciones else None,
            "p95": round(float(np.percentile(duraciones, 95)), 1) if duraciones else None,
        },
        "detalle_de_los_errores_silenciosos": silenciosos[:50],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Mide EC-01 y EC-02 sobre hojas sintéticas.")
    parser.add_argument("--hojas", type=int, default=300)
    parser.add_argument("--semilla", type=int, default=2026)
    parser.add_argument("--json", help="dónde guardar el informe")
    args = parser.parse_args(argv)
    informe = medir(args.hojas, args.semilla)
    texto = json.dumps(informe, ensure_ascii=False, indent=2)
    print(texto)
    if args.json:
        with open(args.json, "w", encoding="utf-8") as archivo:
            archivo.write(texto + "\n")
    return 0 if informe["errores_silenciosos"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
