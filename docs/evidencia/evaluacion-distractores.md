# Evaluación de EC-08: propuesta de distractores diagnósticos

Medición de la porción de la S9 (RF-11, aspecto [A-06](../aspectos.md#a-06)) contra
[EC-08](../arc42/arc42-template-ES.md#ec-08), y evaluación del componente generativo: su conjunto
de evaluación con resultados, el costo por operación y la latencia. El proveedor y la forma de
consumirlo los decide [ADR-0013](../adr/0013-consumir-groq-detras-de-un-puerto-y-degradar-sin-bloquear-la-autoria.md).

**Resultado:** las tres medidas de EC-08 se cumplen con margen. La calidad de las propuestas, que
EC-08 informa sin umbral porque decide el profesor, es la que calificó el equipo en la sección 3.

## 1. El montaje

| | |
|---|---|
| Conjunto | [`conjunto-evaluacion-distractores.json`](conjunto-evaluacion-distractores.json): 20 preguntas de cálculo diferencial (potencia, producto, cociente, cadena, trigonométricas, exponenciales y logaritmos), cada una con su respuesta correcta y dos o tres errores esperados. **8 tienen una forma equivalente conocida** de la respuesta correcta. Lo redactó Claude y lo revisó Josué, que no encontró errores ([`ia.md`](../ia.md#entrada-12), entrada 12) |
| Herramienta | [`herramientas/evaluar_distractores.py`](../../backend/herramientas/evaluar_distractores.py), con `--escenario todos --pasadas 2 --pausa 8 --muestras-degradadas 2` |
| Cuándo y desde dónde | 4-oct-2026, de 19:22 a 19:29 (−05:00), desde la red de la casa de Sebastián |
| Proveedor | Groq, `openai/gpt-oss-120b`, capa gratuita y sin tarjeta |
| Cómo se mide | Cada pregunta pasa por la ruta real `POST /distractores` con `TestClient`, dentro del proceso de la API, con 8 s entre solicitudes para no pasar el límite de tokens por minuto |
| Resultado completo | [`evaluacion-distractores.json`](evaluacion-distractores.json): las 40 solicitudes con sus propuestas, tiempos y tokens, y los casos degradados |

## 2. EC-08 contra sus umbrales

| Medida | Umbral | Resultado | |
|---|---|---|---|
| **M1:** propuestas entregadas que repiten textualmente la respuesta correcta | 0 % | **0 de 120** | Cumple |
| **M2:** p95 de la latencia de la ruta | 15 s o menos | **2,91 s** (mediana 2,09 s, peor 3,14 s), 40 de 40 solicitudes con 200 | Cumple |
| **M3:** proveedor caído o lento | 503 en 21 s o menos | Caído: 503 en **2,23 s** y **2,26 s**. Lento: 503 en **20,25 s** y **20,24 s**. `/health` siguió en 200 en los cuatro casos | Cumple |

M1 se cumple también porque en esta corrida el modelo no repitió la respuesta correcta escrita
igual: la regla no tuvo que descartar nada. Que la regla funciona si el modelo lo hace está
demostrado aparte, con la [prueba que falla ante el defecto](prueba-distractores-falla.md).

## 3. Calidad de las propuestas (calificación del equipo)

Se calificaron a mano, sin IA (en algunas preguntas, con apoyo de una calculadora de
derivadas), las 60 propuestas de la primera pasada (3 por pregunta), repartidas
entre Josué (preguntas 1 a 7), María (8 a 14) y Sebastián (15 a 20). Para cada propuesta: ¿es
incorrecta?, ¿la etiqueta describe el error que realmente la produce?, ¿es plausible para un
estudiante? Es **diagnóstica válida** si cumple las tres.

| | Josué (preguntas 1 a 7) | María (8 a 14) | Sebastián (15 a 20) | Total |
|---|---|---|---|---|
| Propuestas calificadas | 21 | 21 | 18 | 60 |
| **Diagnósticas válidas** | 14 | 16 | 14 | **44 (73 %)** |
| Equivalentes a la respuesta correcta | 0 | 0 | 0 | **0** |
| Etiqueta correcta | 17 | 17 | 14 | 48 (80 %) |
| Etiqueta a medias | 1 | 2 | 1 | 4 (7 %) |
| Etiqueta incorrecta | 3 | 2 | 3 | 8 (13 %) |
| Plausibles | 16 | 19 | 16 | 51 (85 %) |

**El error más común del modelo no es proponer algo equivalente, sino etiquetar mal el error.** De las 16 propuestas que no son válidas, 12 lo son por la etiqueta. Las 16, con el motivo y
la nota del calificador cuando la dejó:

| Propuesta | Expresión | Etiqueta del modelo | Por qué no es válida | Nota del calificador |
|---|---|---|---|---|
| 1b | `cos(x)+x·cos(x)` | Se derivó x como cos(x) en lugar de 1, intercambiando los derivados de los factores | La etiqueta no describe el error que la produce |  |
| 1c | `sin(x)·cos(x)+x` | Se multiplicaron las derivadas de cada factor (f'·g') y se sumó incorrectamente, en lugar de usar la suma de f·g' y f'·g | La etiqueta no describe el error que la produce; no es plausible para un estudiante |  |
| 2c | `5x^3` | Se restó 2 al exponente en lugar de 1 al aplicar la regla de potencias | No es plausible para un estudiante |  |
| 3a | `3x^2-4` | Olvidó derivar el término lineal -4x, manteniéndolo sin cambios | La etiqueta no describe el error que la produce; no es plausible para un estudiante |  |
| 4c | `2x·e^x + x^3·e^x` | Se calculó erróneamente la derivada de e^x como x·e^x | No es plausible para un estudiante |  |
| 7b | `3*sin(3x)` | Confundió la derivada de sin con la de cos | La etiqueta acierta a medias |  |
| 7c | `9*cos(3x)` | Aplicó la regla de la cadena pero multiplicó por 3 dos veces | No es plausible para un estudiante |  |
| 9a | `e^(2x)` | Se derivó e^(x^2) como si el exponente se derivara y se sustituyera directamente en el exponente, omitiendo la regla de la cadena. | La etiqueta acierta a medias |  |
| 9b | `2x·e^x` | Se trató e^(x^2) como (e^x)^2 y se aplicó la regla del producto en lugar de la regla de la cadena correcta. | La etiqueta no describe el error que la produce |  |
| 9c | `2·e^(x^2)` | Se aplicó la regla de la cadena pero se olvidó multiplicar por la derivada del exponente x, quedando solo el factor 2. | La etiqueta acierta a medias |  |
| 10c | `(x²+1)/(2x)` | Se invirtió la fracción resultante de la regla de la cadena, colocando el denominador en el numerador | No es plausible para un estudiante |  |
| 11c | `2·x·cos(x)` | Confundió sin²(x) con sin(x^2) y aplicó la regla de la cadena a x^2 | La etiqueta no describe el error que la produce; no es plausible para un estudiante |  |
| 15b | `cos^2(x)` | Aplicó incorrectamente la regla de la cadena, pensando que la derivada es el coseno al cuadrado | La etiqueta no describe el error que la produce | `tan(x)` no lleva regla de la cadena; `cos^2(x)` sale de `1/sec^2(x)`, confundiendo sec con cos, no del procedimiento descrito |
| 16a | `ln(x)` | Se olvidó derivar el factor x y se tomó ln(x) como constante | La etiqueta acierta a medias | El resultado y «ln(x) como constante» son correctos, pero «se olvidó derivar el factor x» dice lo contrario: lo que se omitió fue derivar ln(x) |
| 16c | `1 - ln(x)` | Se aplicó la regla del producto pero se restó en lugar de sumar la derivada de ln(x) | La etiqueta no describe el error que la produce; no es plausible para un estudiante | Restar la derivada de ln(x) da `ln(x) - 1`, no `1 - ln(x)`. Esa solo sale invirtiendo el orden (f·g' − f'·g), poco natural |
| 19c | `2·ln(2)` | Deriva solo la base y multiplica por ln(2), omitiendo la función 2^x. | La etiqueta no describe el error que la produce; no es plausible para un estudiante | Derivar solo la base da 0, y omitir 2^x dejaría ln(2); `2·ln(2)` no sale del procedimiento descrito, solo de recordar mal la fórmula como a·ln(a). Además es una constante, no una función |

**Las propuestas equivalentes a la respuesta correcta.** Ninguna de las 120 propuestas de la corrida oficial, en las dos pasadas, es equivalente a la respuesta correcta. Así lo marcaron los tres calificadores en las 60 de la primera pasada, y un prototipo con SymPy, fuera del sistema, lo confirmó en las 120 (ver la sección 7). Sí apareció una en la corrida de prueba previa, de 3 preguntas: `sin(2x)` como distractor de `2·sin(x)·cos(x)`, que es la misma expresión.

Es el problema 2 del proyecto, medido: el filtro solo detecta repeticiones textuales, porque
ADR-0004 retiró el cálculo simbólico. Por eso ninguna propuesta entra a un examen sin que el
profesor la acepte (ADR-0005), y ADR-0013 deja el criterio para reabrir la verificación
automática.

## 4. Costo por operación

| | |
|---|---|
| Tokens por solicitud, en promedio | 243,2 de entrada y 612,8 de salida (856 en total) |
| Precio de pago de Groq para `openai/gpt-oss-120b` | US$0,15 por millón de tokens de entrada y US$0,60 por millón de salida (https://console.groq.com/docs/models, consultado el 4-oct-2026) |
| **Costo por solicitud** | **US$0,0004** al precio de pago |
| Costo por examen de 20 preguntas | US$0,008 |
| Costo de 1 000 solicitudes | US$0,40 |
| **Costo en la capa gratuita** | **US$0**, sin tarjeta. El peor caso es agotar la cuota, nunca una factura (RNF-16) |

**Puntos de ruptura de la capa gratuita** (límites de https://console.groq.com/docs/rate-limits,
consultados el 4-oct-2026, con los 856 tokens por solicitud medidos):

| Límite | Valor | Alcanza para |
|---|---|---|
| Tokens por minuto | 8 000 | Unas 9 solicitudes por minuto. Por eso la herramienta espera 8 s entre una y otra |
| Tokens por día | 200 000 | **Unas 233 solicitudes por día: unos 11 exámenes de 20 preguntas.** Es el primer límite que se rompe |
| Solicitudes por día | 1 000 | No se alcanza antes que el de tokens |

La carga real de RF-11 son unas pocas solicitudes por examen, en la semana de preparación (ADR-0005):
queda muy por debajo de cualquiera de los tres.

## 5. Latencia

| Pasada | Mediana | p95 | Peor |
|---|---|---|---|
| 1 | 2,27 s | 2,91 s | 3,14 s |
| 2 | 1,95 s | 2,57 s | 2,98 s |
| Las dos (40 solicitudes) | 2,09 s | 2,91 s | 3,14 s |

Casi todo es el tiempo del modelo: la API solo valida, filtra y traduce. Con el proveedor caído la
respuesta tarda unos 2,2 s, lo que tarda el sistema en rechazar la conexión; con el proveedor lento
tarda lo que espera el adaptador, 20 s, y nada más del sistema se detiene.

En el entorno desplegado, la misma ruta respondió 200 en 1,34 s en una prueba del 4-oct a las 18:21
(−05:00), desde fuera de la universidad.

## 6. Límites de validez

- **Un proveedor y un modelo**, medidos un día. La latencia de una capa gratuita varía.
- **La latencia se midió dentro del proceso de la API**, sin la red del profesor. La prueba sobre el
  entorno desplegado es una sola solicitud.
- **Cada propuesta la calificó una sola persona**, sin medir el acuerdo entre calificadores. En
  algunas preguntas, los calificadores se apoyaron en una calculadora de derivadas
  (derivative-calculator.net), que no es IA.
- **20 preguntas, todas de derivadas.** No representan todo el curso de cálculo diferencial.
- **El modelo no es determinista:** las propuestas de la segunda pasada no son las mismas que las de
  la primera. La calidad se calificó sobre la primera.
- **El costo usa el precio de pago** para dar una cifra comparable. En la capa gratuita es US$0.

## 7. Qué se decide con esto

- **EC-08 se cumple** en sus tres medidas, con margen: la latencia es de unos 3 s contra 15 s, y la
  degradación queda en 20,25 s contra 21 s.
- **La calidad la decide el profesor.** El 73 % de las propuestas son diagnósticas válidas, y 12 de las 16 que no lo son fallan por la etiqueta: el profesor tiene que revisar la etiqueta tanto como la expresión antes de aceptar una propuesta (RF-07).
- **Verificación automática de equivalencias:** esta semana no se construye, porque no habría descartado ninguna propuesta (0 de 120). Un prototipo fuera del repositorio, que traduce la notación y compara con SymPy, detectó el caso de `sin(2x)`, tardó 15 ms por comparación y no pudo leer 1 de 121 expresiones (el modelo la escribió con llaves de LaTeX). El equipo prevé retomarla la próxima semana con su propio ADR, y ADR-0013 deja las condiciones que la vuelven obligatoria.
