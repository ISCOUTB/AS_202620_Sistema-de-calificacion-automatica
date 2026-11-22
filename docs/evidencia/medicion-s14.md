# Medición de atributos de calidad (S14)

Es la evidencia de la S14: el resultado de medir los escenarios de la lectura y la calificación
(EC-01 a EC-04) contrastado con el umbral que declara la
[sección 10 del arc42](../arc42/arc42-template-ES.md#102-escenarios-de-calidad-priorizados), con
tres repeticiones de cada uno. Parte de la medición del 6-nov
([`medicion-lectura-omr.md`](medicion-lectura-omr.md)), que tenía una corrida por escenario, la
repite en otra máquina y dice en qué entorno se midió, qué se sabe, qué se asume y qué se ignora.
Es la línea base del reto de corte. Los artefactos están en
[`medicion-s14/`](medicion-s14/).

**La revisión entre pares de la S14 no se hizo:** el profesor estuvo incapacitado esa semana y no
hubo clases, así que el equipo no recibió señalamientos que incorporar (sección 9 y
[arc42 §11.2](../arc42/arc42-template-ES.md#112-revisión-entre-pares-s14)).

---

## Resultado

| Escenario | Umbral (arc42 §10) | Medido en la S14 | Repeticiones | Conclusión |
|---|---|---|---|---|
| [EC-01](../arc42/arc42-template-ES.md#ec-01) · marcas claras bien leídas | ≥98 % | **100 %**: 28 127 de 28 127 | 3 × 300 hojas | **Cumple bajo una condición:** hojas sintéticas, no las 300 escaneadas y etiquetadas a mano que pide la medida (R-01) |
| [EC-02](../arc42/arc42-template-ES.md#ec-02) · marcas ambiguas a revisión | ≥99 % | **100 %**: 3 134 de 3 134, y 0 errores silenciosos en 36 000 preguntas | Las mismas 3 × 300 | **Cumple bajo dos condiciones:** las mismas hojas sintéticas, y el umbral inicial de 70, sin calibrar con hojas reales (R-04) |
| [EC-03](../arc42/arc42-template-ES.md#ec-03) · de la carga al resultado, sin lote en curso | ≤5 s (p95) | **1,22 s** (p95 de 60 hojas); 1,42 s el máximo | 3 × 20 hojas sueltas | **Cumple en local**, con los límites de CPU del servidor. En el entorno desplegado no se midió |
| [EC-04](../arc42/arc42-template-ES.md#ec-04) · lote de 200 hojas | 100 % en ≤10 min, con CPU y memoria del servidor <85 % | **3,5 a 3,6 min** (208 a 214 s); 600 de 600 hojas | 3 lotes de 200 | **Cumple en tiempo y en hojas procesadas, en local.** La condición de CPU y memoria **del servidor** no se midió: el worker usa todo su cuarto de CPU, que es su tope, y 66 MiB de sus 96 |

Las tres repeticiones dieron lo mismo que la medición del 6-nov dentro del margen esperable, y en
ninguna el resultado se acercó al umbral: EC-03 y EC-04 quedan a un cuarto y a un tercio de lo que
permiten.

---

## 1. Los escenarios y su umbral, como están en la sección 10

Los umbrales se juzgan **tal como están declarados** en la
[sección 10.2 del arc42](../arc42/arc42-template-ES.md#102-escenarios-de-calidad-priorizados), sin
cambios desde que se escribieron en la S2 (commit
[`5555ff9`](https://github.com/ISCOUTB/AS_202620_Sistema-de-calificacion-automatica/commit/5555ff9),
23-ago-2026). Ningún ADR los movió.

| Escenario | Medida de respuesta, textual | Aspecto |
|---|---|---|
| EC-01 | «≥98% de exactitud en la detección de la marca correcta, sobre un dataset de prueba de 300 hojas escaneadas con etiquetado manual de referencia» | [A-02](../aspectos.md#a-02) |
| EC-02 | «El sistema clasifica correctamente como ambigua ≥99% de las marcas cuyo contraste de llenado no supera el umbral de confianza definido (valor inicial 70%, sujeto a calibración)» | A-02 |
| EC-03 | «Tiempo end-to-end ≤5 segundos por examen (percentil 95), medido desde la confirmación de carga hasta la disponibilidad del resultado» | [A-03](../aspectos.md#a-03) |
| EC-04 | «100% de las hojas procesadas correctamente en ≤10 minutos desde la confirmación de recepción, con uso de CPU y memoria del servidor por debajo del 85% durante todo el proceso» | A-03 |

**Cómo se leyó cada medida**, para que nadie tenga que adivinarlo:

- **EC-01:** una marca clara es la que el generador hizo con lápiz o esfero, del 45 % al 80 % más
  oscura que el papel. Exactitud es que la lectura dé esa opción.
- **EC-02:** las marcas ambiguas son las cinco formas que una persona mandaría a revisión: doble
  marca, media burbuja, tenue, chulo y X. Cumplir es que vayan a revisión y no salgan con una
  respuesta.
- **EC-03:** el reloj arranca en `trabajo_publicado`, que la API escribe al dejar la hoja en la cola,
  **antes** de confirmar la carga, y para en `hoja_procesada`, que el worker escribe cuando el
  resultado quedó guardado y `GET /examenes/{id}/resultados` ya lo devuelve. Arrancar antes de la
  confirmación suma unos milisegundos: si algo, el número queda por encima del real.
- **EC-04:** de `lote_confirmado` al último `hoja_procesada` del examen.

---

## 2. Procedimiento

| | EC-01 y EC-02 | EC-03 | EC-04 |
|---|---|---|---|
| **Herramienta** | [`herramientas/medir_lectura.py`](../../backend/herramientas/medir_lectura.py) | [`herramientas/medir_procesamiento.py`](../../backend/herramientas/medir_procesamiento.py) `cargar` y `analizar`, con [`repetir-local.sh`](medicion-s14/repetir-local.sh) | Las mismas |
| **Qué ejercita** | La lectura (`omr.leer_hoja`), sin la API ni la cola | El sistema completo: la API, Redis, el worker, la lectura, la nota y el registro de resultados | Lo mismo |
| **Carga** | 300 hojas sintéticas por corrida, 40 preguntas cada una, «fotografiadas» con perspectiva, giro, sombra, desenfoque, ruido y JPEG al azar | 20 hojas sueltas, una cada 8 s, como un escaneo a 200 DPI | Un lote de 200 hojas como esas, 91,3 MB, en una sola petición |
| **Repeticiones** | 3, semillas 2026, 2027 y 2028 | 3, semillas 2026, 2027 y 2028 | 3, semillas 4, 5 y 6 |
| **Sistema por repetición** | No aplica | Nuevo y vacío en cada una | Nuevo y vacío en cada una |
| **Resultado de cada una** | `ec01-ec02-semilla-<n>.json` | `ec03-semilla-<n>.json`, con su registro y sus muestras | `ec04-semilla-<n>.json`, con su registro y sus muestras |

**Los límites del servidor, sin Docker.** La máquina de la S14 no tiene Docker, así que
[`limitar.py`](medicion-s14/limitar.py) aplica los mismos topes de CPU de
[`deploy/compose.lab.yaml`](../../deploy/compose.lab.yaml): 0,25 CPU al worker y 0,5 a la API. Lo
hace como `cpulimit`: en cada período de 100 ms deja correr el proceso esa fracción y lo detiene el
resto. Cada proceso va fijo a un núcleo, porque OpenCV lee con dos hilos y, sin eso, los dos
correrían a la vez en la fracción permitida, con más CPU de la que da Docker. Redis va con el tope
del servidor: 32 MB, `noeviction`, sin persistencia. La memoria no se limita, se mide: es lo que
EC-04 pide.

**La clave de cada examen** se escribe en el volumen antes de subir las hojas, como en el servidor,
porque A-04 todavía no la registra (R-35).

---

## 3. EC-01 y EC-02: tres corridas de 300 hojas

| Forma de marcar | Semilla 2026 | Semilla 2027 | Semilla 2028 | Error silencioso |
|---|---|---|---|---|
| Clara, bien leída | 9 406 de 9 406 | 9 379 de 9 379 | 9 342 de 9 342 | 0 |
| En blanco, sin marca | 970 | 962 | 969 | 0 |
| Doble marca, a revisión | 247 | 234 | 239 | 0 |
| Media burbuja, a revisión | 215 | 234 | 220 | 0 |
| Tenue, a revisión | 207 | 236 | 228 | 0 |
| Chulo, a revisión | 181 | 180 | 186 | 0 |
| X, a revisión | 176 | 153 | 198 | 0 |
| Borrada sola, bien | 239 | 236 | 238 | 0 |
| Borrada y otra encima, bien | 222 | 248 | 255 | 0 |
| Con brillo, a revisión sin necesitarlo | 137 | 138 | 125 | 0 |

- **EC-01:** 28 127 de 28 127 marcas claras, el 100 %, contra ≥98 %.
- **EC-02:** 3 134 de 3 134 marcas ambiguas a revisión (1 026, 1 037 y 1 071), el 100 %, contra
  ≥99 %.
- **Errores silenciosos** (QG-3): ninguno en 36 000 preguntas.
- **Códigos de estudiante:** los 900, completos y bien leídos. **Hojas ilegibles:** ninguna.
- **A revisión sin necesitarlo:** 0,46, 0,46 y 0,42 preguntas por hoja, todas por el brillo del
  lápiz. Le cuestan tiempo al profesor, pero no son errores.
- **Tiempo de lectura, sin límite de CPU:** p50 de 226 a 244 ms y p95 de 285 a 341 ms. El 6-nov dio
  378 y 459 ms en otra máquina: el tiempo depende del procesador, el resultado no.

---

## 4. EC-03: tres corridas de 20 hojas sueltas

| | Semilla 2026 | Semilla 2027 | Semilla 2028 | Las 60 juntas | El 6-nov, con Docker |
|---|---|---|---|---|---|
| Procesadas | 20 de 20 | 20 de 20 | 20 de 20 | 60 de 60 | 20 de 20 |
| De la carga al resultado, p50 | 1,04 s | 1,02 s | 1,00 s | 1,02 s | 1,24 s |
| **p95** | **1,21 s** | **1,15 s** | **1,30 s** | **1,22 s** | **1,71 s** |
| Máximo | 1,21 s | 1,42 s | 1,34 s | 1,42 s | 2,51 s |
| Lectura en el worker, p50 | 1,01 s | 1,00 s | 0,97 s | | 1,19 s |

**Contra el umbral:** p95 de 1,22 s contra ≤5 s. **Cumple**, con margen: la peor hoja de las 60
tardó 1,42 s. Casi todo es la lectura en el cuarto de CPU del worker; la cola, la API, la nota y el
registro suman 56 ms en la mediana y 151 ms en la peor hoja.

**Las hojas quedaron en revisión**, las 60, porque las sintéticas traen a propósito unas cuatro
marcas ambiguas por hoja. El tiempo es el mismo: la hoja queda con su nota provisional y sus
preguntas por revisar.

---

## 5. EC-04: tres lotes de 200 hojas

| | Semilla 4 | Semilla 5 | Semilla 6 | El 6-nov, semilla 4, con Docker |
|---|---|---|---|---|
| Procesadas | 200 de 200 | 200 de 200 | 200 de 200 | 200 de 200 |
| **Lote completo** | **208,8 s (3,5 min)** | **213,9 s (3,6 min)** | **207,6 s (3,5 min)** | 214,5 s (3,6 min) |
| Lectura en el worker, p50 / p95 | 1,01 / 1,19 s | 1,01 / 1,22 s | 1,00 / 1,20 s | 1,01 / 1,41 s |
| Estado de las hojas | 195 en revisión, 5 calificadas | 200 en revisión | 197 en revisión, 3 calificadas | 195 en revisión, 5 calificadas |

**Contra el umbral:** 600 de 600 hojas en 3,5 a 3,6 min, contra el 100 % en ≤10 min. **Cumple en
tiempo y en hojas procesadas.** La semilla 4 son las mismas hojas del 6-nov, y quedaron en los
mismos estados: 195 en revisión y 5 calificadas.

**CPU y memoria durante los lotes** (muestras cada 2 s, de 122 a 127 por lote):

| | CPU | Memoria propia del proceso (RssAnon), máximo | Memoria residente (VmRSS), máximo |
|---|---|---|---|
| Worker (tope: 0,25 CPU, 96 MiB) | **Todo su tope** mientras hay hojas; las muestras llegan a 0,27-0,29 por el corte de cada período | **63 MiB**, el 66 % de su tope; 66 MiB el máximo de las seis corridas | 107 MiB |
| API (tope: 0,5 CPU, 384 MiB) | Hasta 0,29 mientras recibe el lote | **137 MiB**, el 36 % de su tope, con el lote de 91 MB entrando | 154 MiB |

- **Por qué dos memorias.** VmRSS cuenta también las páginas de NumPy y OpenCV, unos 44 MiB que se
  leen del disco y el kernel puede soltar; Docker las cuenta como caché, igual que la de las
  imágenes. RssAnon es la que el proceso no puede soltar, la que se compara con el tope. El 6-nov,
  `docker stats` dio 78 MiB de memoria de trabajo: una medida intermedia entre las dos.
- **La CPU del servidor no se midió.** EC-04 pide la CPU y la memoria **del servidor** por debajo del
  85 %. Aquí, la máquina entera llegó al 65 % de sus dos núcleos, pero en ese número está también el
  programa que genera y sube las hojas, que en el escenario es el computador del profesor. Y el
  worker no puede pasar de su cuarto de CPU, haya las hojas que haya: lo que el escenario pregunta se
  mide en el servidor del laboratorio, que es compartido (R-31).

**Conclusión de EC-04:** cumple en tiempo y en hojas procesadas, en local y con los topes del
servidor. La condición de CPU y memoria del servidor queda **sin medir** (R-37).

---

## 6. Entorno de la medición

**Todo se midió en local, no en el entorno desplegado.**

| | La medición del 6-nov | La de la S14 |
|---|---|---|
| Dónde | Un computador del equipo, con `docker compose` | Una máquina Linux de 2 núcleos, sin Docker |
| Sistema | `redis`, `postgres`, `api` y `worker`, con las imágenes del proyecto | Redis, la API y el worker como procesos, con las dependencias de `requirements.txt` y Python 3.12 |
| Topes | Los de `compose.lab.yaml`, aplicados por Docker | Los de CPU de `compose.lab.yaml`, aplicados por `limitar.py`; la memoria se mide |
| Repeticiones | 1 por escenario | 3 por escenario |

**Por qué no en el servidor.** Medir EC-03 y EC-04 allá exige dos cosas que el equipo no puede
hacer todavía desde fuera del panel: copiar la clave de cada examen al volumen del servidor (R-35)
y leer el registro del worker para calcular los tiempos, que en el servidor solo se ve en el panel
del curso. Además, el servidor es compartido con los demás equipos (R-31): un lote de 200 hojas de
medición le quita CPU a todos.

**Qué cambia en el significado del número:**

- **EC-03** es un escenario de latencia del sistema desplegado. En local falta la red: desde fuera de
  la universidad, `/health` del servidor tardó 0,28 s de mediana y 0,53 s en el p95
  ([`despliegue-iscoutb.md`](despliegue-iscoutb.md)), y la carga de la hoja sube más bytes. Falta
  también la carga de los demás equipos. Con 1,22 s de p95 hay margen para las dos cosas, pero no se
  midieron.
- **EC-04** se mide desde la confirmación, así que la red solo cuenta en la subida, que no entra en
  los 10 min. Lo que falta es la condición de CPU y memoria del servidor (sección 5).
- **EC-01 y EC-02** no dependen del entorno: la misma semilla da exactamente el mismo resultado en
  las dos máquinas (sección 7).

---

## 7. Reproducibilidad

- **La misma semilla da el mismo resultado en otra máquina.** La corrida de EC-01 y EC-02 con la
  semilla 2026 dio, forma por forma y código por código, lo mismo que el informe del 6-nov
  ([`medicion-lectura-ec01-ec02.json`](medicion-lectura-ec01-ec02.json)); solo cambiaron los
  tiempos de lectura. El lote de EC-04 con la semilla 4 dejó las hojas en los mismos estados.
- **Todo lo que hace falta está versionado:** las dos herramientas, el script que arranca el sistema
  con sus topes y los informes, los registros y las muestras de cada corrida, en
  [`medicion-s14/`](medicion-s14/).
- **Se puede rehacer el cálculo sin volver a medir:** `analizar` sobre el registro de una corrida
  devuelve su informe.

---

## 8. Lo que se conoce, lo que se asume y lo que se ignora

| | Qué | Dónde queda |
|---|---|---|
| **Se conoce** | Las cifras de las secciones 3 a 5, con tres repeticiones, y que la misma semilla las reproduce | Este documento |
| **Se conoce** | El worker usa todo su cuarto de CPU mientras hay hojas: el lote de 200 tarda lo que tarda por ese tope, y un segundo worker lo bajaría (ADR-0017, R-29) | Sección 5 |
| **Se asume** | Que las hojas sintéticas representan bien las escaneadas. Las fotos del prototipo (R-05) dieron 0 errores silenciosos, pero son tres | R-01 |
| **Se asume** | Que el umbral de 70 es adecuado. Con las sintéticas no hubo errores, pero no se calibró con hojas reales | R-04 |
| **Se asume** | Que los topes aplicados en local se parecen a los del servidor. La CPU es otra: la lectura tardó 1,0 s en esta máquina y 1,2 s en la del 6-nov, con el mismo tope | Sección 6 |
| **Se asume** | Que el resultado está «disponible» cuando el worker lo guardó. La pantalla de carga lo muestra en su siguiente consulta, cada 3 s | Sección 1 |
| **Se ignora** | Cuánto tardan EC-03 y EC-04 en el servidor desplegado, con su red y con la carga de los demás equipos | R-37 |
| **Se ignora** | La CPU y la memoria del servidor durante un lote, que es la condición de EC-04 | R-37 |
| **Se ignora** | Qué parte de las preguntas va a revisión con exámenes reales. Con las sintéticas fueron unas cuatro por hoja, puestas a propósito | R-04 |
| **Se ignora** | Cómo se leen fotos de celular tomadas de día: las del prototipo son de noche, con un foco | R-01 |

---

## 9. La revisión entre pares

La ficha de la S14 pide incorporar a la sección 11 del arc42 lo que señaló la revisión de los pares.
**Esa revisión no se hizo:** el profesor estuvo incapacitado la semana 14 y no hubo clases, así que
la actividad individual de revisión entre pares no ocurrió y el equipo no recibió ningún
señalamiento.

No se inventa: la [sección 11.2 del arc42](../arc42/arc42-template-ES.md#112-revisión-entre-pares-s14)
lo dice y deja la tabla preparada con las columnas de origen, señalamiento, respuesta y estado. Lo
que sí llegó a la sección 11 es lo que dejó esta medición, separado en lo que se conoce, se asume y
se ignora ([§11.3](../arc42/arc42-template-ES.md#113-lo-que-dejó-la-medición-de-la-s14)).

---

## 10. Cómo repetirla

Desde `backend/`, con el entorno del proyecto (`pip install --require-hashes -r requirements.txt`):

    # EC-01 y EC-02: unos 6 minutos por corrida
    python -m herramientas.medir_lectura --hojas 300 --semilla 2026 --json ec01-ec02.json

    # EC-03 y EC-04: un sistema nuevo por corrida, con redis-server, curl y taskset instalados
    SALIDA=resultados bash ../docs/evidencia/medicion-s14/repetir-local.sh ec03 2026
    SALIDA=resultados bash ../docs/evidencia/medicion-s14/repetir-local.sh ec04 4

    # Rehacer el cálculo con un registro ya versionado
    python -m herramientas.medir_procesamiento analizar \
        ../docs/evidencia/medicion-s14/ec04-semilla-4-registro.jsonl --examen S14-EC04-S4

Con Docker, la medición del 6-nov se repite como dice
[`medicion-lectura-omr.md`, sección 3](medicion-lectura-omr.md#3-ec-03-y-ec-04-el-sistema-completo).
`medir_lectura` termina con código 1 si hubo algún error silencioso.
