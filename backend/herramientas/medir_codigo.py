"""Mide cómo lee el código del estudiante la regla de ADR-0024, con marcas difíciles en el código.

Por qué una medición aparte
---------------------------
Desde ADR-0024, una columna del código se acepta con el dígito si exactamente una burbuja llega al
corte de intención (40 por omisión), aunque la marca sea tenue, un chulo o una X. A diferencia de
una pregunta, ese dígito no pasa por el profesor: si se acepta uno equivocado, la nota se le asigna
a otro estudiante sin que nadie lo vea. Por eso la cifra que importa aquí es **cero dígitos mal
aceptados**.

`medir_lectura` no lo pone a prueba: marca el código solo con marcas claras, y cambiar eso movería
las cifras publicadas de EC-01 y EC-02 (semilla 2026). Esta herramienta genera sus propias hojas,
con otra semilla: marca cada columna del código con un caso al azar y fotografía la hoja con las
mismas condiciones al azar que `medir_lectura`.

Cada columna termina en uno de tres resultados:

- **aceptado_bien:** el dígito que se quiso marcar;
- **por_revisar:** la columna quedó con `?`. Es lo correcto donde no hay una sola intención (en
  blanco, solo un borrón, dos marcas) y cuesta tiempo donde la había, pero no es un error;
- **aceptado_mal:** un dígito distinto del que se quiso, o un dígito donde no se quiso ninguno.

**Los borrones fuertes.** El borrón de `medir_lectura` (oscuridad de 0,03 a 0,09) da menos de 10
de confianza, y en las fotos del prototipo lo borrado llegó a 35: justo el tramo bajo el corte
donde la regla del código se expone sin profesor. Por eso hay dos casos más, un borrón fuerte solo
y uno al lado de la marca, con la oscuridad que reproduce ese tramo. Como el código no expone la
confianza de sus burbujas, el informe la mide con los mismos borrones fuertes en diez filas de
preguntas de cada hoja (`confianza_de_los_borrones_fuertes`).

Lo que no reproduce es lo mismo que en `medir_lectura`: papel arrugado, tinta real y brillo bajo
una luz cualquiera. Son hojas generadas, no hojas de estudiantes.

Uso, desde backend/
-------------------
    python -m herramientas.medir_codigo                        # 300 hojas, semilla 2027
    python -m herramientas.medir_codigo --hojas 50 --semilla 2028 --json informe.json
"""

import argparse
import json
import sys
from collections import Counter

import numpy as np

from herramientas.hojas_sinteticas import (
    BORRADA,
    BRILLO,
    CHULO,
    EQUIS,
    MEDIA,
    TENUE,
    Foto,
    Marca,
    fotografiar,
    hoja_en_blanco,
    marcar,
)
from herramientas.medir_lectura import (
    BORRADA_Y_OTRA,
    CALIDAD_JPEG,
    CLARA,
    CON_BRILLO,
    DESENFOQUE_PX,
    DOBLE,
    EN_BLANCO,
    ESCALA,
    PERSPECTIVA,
    PROBABILIDAD_DE_GIRO,
    PROBABILIDAD_DE_SOMBRA,
    RUIDO,
    SOLO_BORRADA,
    SOMBRA,
    UMBRAL,
    _marca_clara,
)
from herramientas.rutas import ruta_en_el_repositorio
from omr import CORTE_DE_INTENCION_POR_OMISION, FORMATO_V1, LecturaImposible, leer_hoja

CORTE = CORTE_DE_INTENCION_POR_OMISION
COLUMNAS = 8

SOLO_BORRON_FUERTE = "solo_borron_fuerte"
BORRON_FUERTE_Y_OTRA = "borron_fuerte_y_otra"
# Con esta oscuridad, un borrón sintético da de 28 a 37 de confianza (calibrado leyendo los mismos
# borrones en filas de preguntas); en las fotos del prototipo lo borrado llegó a 35.
OSCURIDAD_DEL_BORRON_FUERTE = (0.12, 0.14)
FILAS_DE_CALIBRACION = 10

# Cómo se marca cada columna. A diferencia de `medir_lectura`, los casos difíciles son la mayoría:
# lo que se pone a prueba es la regla nueva, no un examen típico.
CASOS = {
    CLARA: 0.2,
    TENUE: 0.08,
    MEDIA: 0.08,
    CHULO: 0.08,
    EQUIS: 0.08,
    BORRADA_Y_OTRA: 0.12,
    CON_BRILLO: 0.08,
    DOBLE: 0.1,
    SOLO_BORRADA: 0.1,
    EN_BLANCO: 0.08,
    SOLO_BORRON_FUERTE: 0.1,
    BORRON_FUERTE_Y_OTRA: 0.1,
}


def juzgar_columna(quiso: str | None, leido: str) -> str:
    """`aceptado_bien`, `por_revisar` o `aceptado_mal` para lo que se leyó en una columna."""
    if leido == "?":
        return "por_revisar"
    return "aceptado_bien" if leido == quiso else "aceptado_mal"


def _foto_al_azar(azar: np.random.Generator) -> Foto:
    """Las condiciones de la foto, entre los mismos extremos que `medir_lectura`."""
    return Foto(
        giro=int(azar.integers(1, 4)) if azar.random() < PROBABILIDAD_DE_GIRO else 0,
        perspectiva=float(azar.uniform(*PERSPECTIVA)),
        sombra=float(azar.uniform(*SOMBRA)) if azar.random() < PROBABILIDAD_DE_SOMBRA else 1.0,
        escala=float(azar.uniform(*ESCALA)),
        desenfoque_px=float(azar.uniform(*DESENFOQUE_PX)),
        ruido=float(azar.uniform(*RUIDO)),
        calidad_jpeg=int(azar.integers(CALIDAD_JPEG[0], CALIDAD_JPEG[1] + 1)),
        semilla=int(azar.integers(0, 2**31)),
    )


def _borron_fuerte(azar: np.random.Generator) -> Marca:
    return Marca(BORRADA, oscuridad=float(azar.uniform(*OSCURIDAD_DEL_BORRON_FUERTE)))


def generar_hoja(azar: np.random.Generator) -> tuple[bytes, list[tuple[str, str | None]]]:
    """Una hoja con el código marcado con casos al azar, fotografiada, con el caso y el dígito que
    se quiso marcar en cada columna (None si no se quiso ninguno). Las primeras
    `FILAS_DE_CALIBRACION` preguntas llevan un borrón fuerte cada una, para medir su confianza; las
    demás quedan en blanco."""
    hoja = hoja_en_blanco()
    for numero in range(1, FILAS_DE_CALIBRACION + 1):
        letra = int(azar.integers(0, 4))
        marcar(hoja, FORMATO_V1.centro_de_la_respuesta_mm(numero, letra), _borron_fuerte(azar),
               azar)
    casos, pesos = list(CASOS), np.array(list(CASOS.values()))
    columnas: list[tuple[str, str | None]] = []
    for posicion in range(1, COLUMNAS + 1):
        caso = str(azar.choice(casos, p=pesos / pesos.sum()))
        a, b = (int(d) for d in azar.choice(10, 2, replace=False))

        def en(digito: int, marca: Marca) -> None:
            marcar(hoja, FORMATO_V1.centro_del_digito_mm(posicion, digito), marca, azar)

        quiso: str | None = str(a)
        if caso == CLARA:
            en(a, _marca_clara(azar))
        elif caso == TENUE:
            en(a, Marca(TENUE, oscuridad=float(azar.uniform(0.15, 0.25))))
        elif caso == MEDIA:
            en(a, Marca(MEDIA, oscuridad=float(azar.uniform(0.45, 0.8)),
                        giro=float(azar.uniform(0, 2 * np.pi))))
        elif caso in (CHULO, EQUIS):
            en(a, Marca(caso, oscuridad=float(azar.uniform(0.45, 0.8))))
        elif caso == BORRADA_Y_OTRA:
            en(b, Marca(BORRADA, oscuridad=float(azar.uniform(0.03, 0.09))))
            en(a, _marca_clara(azar))
        elif caso == CON_BRILLO:
            en(a, Marca(BRILLO, oscuridad=float(azar.uniform(0.15, 0.3))))
        elif caso == DOBLE:
            en(a, _marca_clara(azar))
            en(b, _marca_clara(azar))
            quiso = None
        elif caso == SOLO_BORRADA:
            en(a, Marca(BORRADA, oscuridad=float(azar.uniform(0.03, 0.09))))
            quiso = None
        elif caso == EN_BLANCO:
            quiso = None
        elif caso == SOLO_BORRON_FUERTE:
            en(a, _borron_fuerte(azar))
            quiso = None
        elif caso == BORRON_FUERTE_Y_OTRA:
            en(b, _borron_fuerte(azar))
            en(a, _marca_clara(azar))
        columnas.append((caso, quiso))
    return fotografiar(hoja, _foto_al_azar(azar)), columnas


def medir(hojas: int = 300, semilla: int = 2027) -> dict:
    azar = np.random.default_rng(semilla)
    resultados: dict[str, Counter[str]] = {caso: Counter() for caso in CASOS}
    mal = []
    ilegibles: Counter[str] = Counter()
    completos = 0
    fuertes: list[int] = []
    for indice in range(hojas):
        imagen, columnas = generar_hoja(azar)
        try:
            lectura = leer_hoja(imagen, UMBRAL, corte_de_intencion=CORTE)
        except LecturaImposible as error:
            ilegibles[error.motivo] += 1
            continue
        fuertes += [
            max(burbuja.confianza for burbuja in pregunta.burbujas)
            for pregunta in lectura.preguntas[:FILAS_DE_CALIBRACION]
        ]
        leidos = (lectura.codigo.valor or "T" + "?" * COLUMNAS)[1:]
        todas_bien = True
        for posicion, ((caso, quiso), leido) in enumerate(zip(columnas, leidos, strict=True), 1):
            juicio = juzgar_columna(quiso, leido)
            resultados[caso][juicio] += 1
            todas_bien = todas_bien and juicio == "aceptado_bien"
            if juicio == "aceptado_mal":
                mal.append({"hoja": indice, "columna": posicion, "caso": caso, "quiso": quiso,
                            "leido": leido})
        completos += todas_bien
    return {
        "hojas_generadas": hojas,
        "semilla": semilla,
        "umbral_de_confianza": UMBRAL,
        "corte_de_intencion": CORTE,
        "hojas_ilegibles": dict(ilegibles),
        "hojas_con_el_codigo_completo_y_correcto": completos,
        "por_caso": {caso: dict(conteo) for caso, conteo in resultados.items()},
        "confianza_de_los_borrones_fuertes": {
            "medidos": len(fuertes),
            "minima": min(fuertes, default=0),
            "mediana": int(np.median(fuertes)) if fuertes else 0,
            "p95": int(np.percentile(fuertes, 95)) if fuertes else 0,
            "maxima": max(fuertes, default=0),
        },
        "mal": len(mal),
        "detalle_de_los_mal_aceptados": mal[:50],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Mide el código del estudiante con marcas difíciles (ADR-0024)."
    )
    parser.add_argument("--hojas", type=int, default=300)
    parser.add_argument("--semilla", type=int, default=2027)
    parser.add_argument("--json", help="dónde guardar el informe, dentro del repositorio")
    args = parser.parse_args(argv)
    destino = ruta_en_el_repositorio(args.json, "--json") if args.json else None
    informe = medir(args.hojas, args.semilla)
    texto = json.dumps(informe, ensure_ascii=False, indent=2)
    print(texto)
    if destino:
        with open(destino, "w", encoding="utf-8") as archivo:
            archivo.write(texto + "\n")
    return 0 if informe["mal"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
