# La preselección en la revisión y el código del estudiante (ADR-0024)

Este documento es la evidencia de ADR-0024: una burbuja con 40 o más de confianza cuenta como
intención del estudiante; la pregunta en revisión con exactamente una intención llega al docente con
esa opción elegida, y la columna del código con exactamente una intención da su dígito. Lo que había
que mostrar es que esa regla **no sugiere lo que el estudiante no quiso** y que **no acepta un dígito
equivocado** en el código, donde ningún docente lo revisa.

Todo se midió con la hoja v1: las tres fotos de la hoja del prototipo (R-05) y hojas sintéticas
generadas y fotografiadas por el programa. **No son hojas de estudiantes reales.** Los informes están
en la carpeta [`preseleccion-omr/`](preseleccion-omr/).

---

## Resultado

| Qué | Sobre qué | Medido |
|---|---|---|
| Preguntas en revisión que llegan preseleccionadas con lo que se marcó | 3 fotos del prototipo | **25 de 28**; las otras 3, confusas |
| Sugerencias equivocadas en preguntas | Las 3 fotos y 1 163 preguntas en revisión de 300 hojas sintéticas | **0** |
| Dígitos del código aceptados mal | 7 200 columnas de 900 hojas sintéticas, en su mayoría con marcas difíciles | **0** |
| Código completo y correcto | Las 3 fotos | **3 de 3** |
| EC-01, EC-02 y errores silenciosos | Las mismas 300 hojas sintéticas de la medición de EC-01 y EC-02 | **Iguales** a lo publicado: 100 %, 100 % y 0 |

---

## 1. Las tres fotos del prototipo

La hoja del prototipo se marcó a mano con casos difíciles a propósito, y se fotografió desde arriba,
inclinada 30° y con sombra. Las fotos no están en el repositorio (unos 4 MB cada una).

| Foto | Preguntas en revisión | Preseleccionadas bien | Confusas | Equivocadas | Código |
|---|---|---|---|---|---|
| Desde arriba | 4 | 3 | 1 | 0 | completo y correcto |
| Inclinada 30° | 19 | 18 | 1 | 0 | completo y correcto |
| Con sombra | 5 | 4 | 1 | 0 | completo y correcto |
| **Total** | **28** | **25** | **3** | **0** | |

**Las 3 confusas son la misma pregunta**, la 32, donde el estudiante marcó la A y la C. En dos fotos
se leen las dos llenas (doble marca); en la inclinada, una en 50 y la otra en 54. En las tres hay
dos intenciones, así que llega sin nada elegido.

**Lo que separa una marca de lo que no lo es.** En las tres fotos, lo borrado quedó entre 2 y 35 de
confianza, y toda marca real en 50 o más. El caso más ajustado es la pregunta 34 de la foto con
sombra: la B llena (100) y la D borrada (35). La lectura la manda a revisión por el borrón, y llega
con la B elegida. Las preguntas 1 a 12 de la foto inclinada son marcas completas que la lectura no
ve bien por el brillo; todas quedaron entre 50 y 64, y llegan con la opción marcada.

**10 de las 25 preseleccionadas estaban en 50 exacto**, el valor que pone la lectura cuando no ve
bien una burbuja (por brillo o porque su contorno quedó tapado). En las tres fotos eran marcas
reales, pero es la parte que más depende de la luz: ADR-0024 lo deja como consecuencia asumida.

---

## 2. Las preguntas en 300 hojas sintéticas

Son las mismas 300 hojas de la medición de EC-01 y EC-02 (semilla 2026, umbral 70), con las mismas
formas de marcar y las mismas condiciones de foto: la generación no cambió. Por eso EC-01 (100 %),
EC-02 (100 %), los errores silenciosos (0) y las preguntas a revisión sin necesitarlo (0,46 por
hoja) dan lo mismo que lo publicado en
[la medición de la lectura](medicion-lectura-omr.md#2-ec-01-y-ec-02-300-hojas-sintéticas).

Lo nuevo es cómo llega cada pregunta en revisión:

| Forma de marcar | En revisión | Preseleccionada con lo que se marcó | Confusa | Sugerencia equivocada |
|---|---|---|---|---|
| Doble marca | 247 | | 247 | 0 |
| Media burbuja | 215 | 215 | | 0 |
| Tenue | 207 | 204 | 3 | 0 |
| Chulo | 181 | 181 | | 0 |
| X | 176 | 176 | | 0 |
| Con brillo | 137 | 137 | | 0 |
| **Total** | **1 163** | **913** | **250** | **0** |

Las 3 tenues que llegan confusas no alcanzaron el corte: el docente las elige como antes.

**Lo que esta parte no cubre.** El borrón de estas hojas es suave (menos de 10 de confianza) y nunca
llega a revisión. Una fila con solo un borrón fuerte, como el de 35 de la foto, no se generó aquí:
agregarla cambiaría las cifras publicadas de EC-01 y EC-02. Ese caso se midió en el código (sección
3), que usa la misma lectura.

---

## 3. El código del estudiante en 900 hojas sintéticas

En el código no hay docente que confirme: un dígito aceptado mal le asigna la nota a otro estudiante
sin que nadie lo vea. Por eso tenía que dar cero, y se midió con una herramienta propia,
`herramientas/medir_codigo.py`, con otras semillas (2027, 2028 y 2029, 300 hojas cada una).

**Cómo se marcan las ocho columnas.** Cada columna se marca al azar con uno de estos casos. Los
difíciles son la mayoría a propósito, porque lo que se pone a prueba es la regla, no un examen
típico. Las fotos salen de las mismas condiciones que en la sección 2.

| Caso | Frecuencia (redondeada) | Lo correcto |
|---|---|---|
| Clara | 17 % | El dígito |
| Tenue, media burbuja, chulo, X o con brillo | 7 % cada uno | El dígito |
| Borrón suave y otra marca | 10 % | El dígito de la otra marca |
| Borrón fuerte y otra marca | 8 % | El dígito de la otra marca |
| Doble marca | 8 % | `?` |
| Borrón suave solo | 8 % | `?` |
| Borrón fuerte solo | 8 % | `?` |
| En blanco | 7 % | `?` |

**Los borrones fuertes** se calibraron para llegar hasta donde llegó lo borrado en las fotos (35). Como
el código no muestra la confianza de sus burbujas, la herramienta pone los mismos borrones en diez
filas de preguntas de cada hoja y los mide ahí: dieron de 29 a 38 (mediana 34, 9 000 medidos).

**Resultado** (`codigo-semilla-2027.json`, `-2028.json` y `-2029.json`):

| Caso | Columnas | Dígito correcto | `?` | Dígito equivocado |
|---|---|---|---|---|
| Clara | 1 189 | 1 189 | | 0 |
| Tenue | 453 | 441 | 12 | 0 |
| Media burbuja | 483 | 483 | | 0 |
| Chulo | 482 | 482 | | 0 |
| X | 451 | 451 | | 0 |
| Con brillo | 497 | 496 | 1 | 0 |
| Borrón suave y otra marca | 739 | 739 | | 0 |
| Borrón fuerte y otra marca | 625 | 625 | | 0 |
| Doble marca | 592 | | 592 | 0 |
| Borrón suave solo | 608 | | 608 | 0 |
| Borrón fuerte solo | 590 | | 590 | 0 |
| En blanco | 491 | | 491 | 0 |
| **Total** | **7 200** | **4 906** | **2 294** | **0** |

Ninguna hoja fue ilegible. **Que solo 40 de las 900 hojas tengan el código completo y correcto no es
un problema de la regla:** con estas frecuencias, casi un tercio de las columnas no tiene una sola
intención y lo correcto es `?`, así que pocas hojas tienen las ocho bien. En una hoja de verdad, el
código se marca con cuidado.

---

## 4. Para repetirla

Desde `backend/`:

    python -m herramientas.medir_lectura --hojas 300 --semilla 2026 --json lectura.json
    python -m herramientas.medir_codigo --hojas 300 --semilla 2027 --json codigo.json

La primera suma al informe `preseleccion_por_caso` y `sugerencias_equivocadas`; la segunda termina
con código 1 si algún dígito se aceptó mal. Para las fotos, con `OMR_FOTOS_R05` apuntando a la
carpeta de las fotos:

    OMR_FOTOS_R05=/ruta/a/las/fotos PYTHONPATH=. python ../docs/evidencia/preseleccion-omr/contar_fotos_r05.py
    OMR_FOTOS_R05=/ruta/a/las/fotos python -m pytest tests/test_lectura_fotos_r05.py

La prueba de las fotos exige, además de lo de ADR-0023, que ninguna sugerencia contradiga lo que se
marcó en la hoja.

---

## 5. Lo que queda abierto

- **Hojas reales.** Todo lo de aquí es una hoja del prototipo y hojas generadas. El corte, como el
  umbral, se calibra con el conjunto de R-01 (R-04).
- **El margen con los borrones es corto:** el borrón real más fuerte llegó a 35 y el corte está en
  40. Un borrón real con 40 o más, o una marca real con menos, es el dato que haría revisar el corte.
- **El 50 de lo que no se ve bien** sostuvo 10 de las 25 preseleccionadas de las fotos. Unas fotos
  con otra luz podrían moverlo.
