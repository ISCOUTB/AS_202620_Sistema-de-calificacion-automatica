# Medición de la lectura OMR (A-02 y A-03)

Este documento es la evidencia de calidad de los aspectos [A-02](../aspectos.md#a-02) (leer la hoja)
y [A-03](../aspectos.md#a-03) (calificarla). Contiene lo que mostró la hoja del prototipo (R-05), las
mediciones de los cuatro escenarios que les tocan y el procedimiento para repetirlas, la revisión
manual de las preguntas dudosas (RF-08) con las mismas fotos, y lo que pasa con una imagen que pide
más memoria de la que tiene el worker. La decisión que explica cada corte es
[ADR-0023](../adr/0023-leer-las-hojas-en-posiciones-fijas-y-mandar-a-revision-lo-que-no-se-ve-bien.md).

---

## Resultado

| Escenario | Umbral | Medido | Sobre qué | |
|---|---|---|---|---|
| [EC-01](../arc42/arc42-template-ES.md#ec-01) · marcas claras bien leídas | ≥98 % | **100 %** (9 406 de 9 406) | 300 hojas sintéticas | cumple, con la salvedad de abajo |
| [EC-02](../arc42/arc42-template-ES.md#ec-02) · marcas ambiguas a revisión | ≥99 % | **100 %** (1 026 de 1 026) | Las mismas 300 hojas | cumple |
| Respuestas leídas mal sin aviso (QG-3) | 0 | **0** | Las 300 hojas y las 3 fotos del prototipo | cumple |
| [EC-03](../arc42/arc42-template-ES.md#ec-03) · de la carga al resultado, por hoja, sin lote en curso | ≤5 s (p95) | **1,7 s** (p95); 2,5 s el máximo | 20 hojas sueltas, sistema completo con los límites del servidor | cumple |
| [EC-04](../arc42/arc42-template-ES.md#ec-04) · lote de 200 hojas | ≤10 min | **3,6 min** (214 s), 200 de 200 procesadas | Un lote, el mismo sistema | cumple |

**La salvedad de EC-01.** El escenario pide 300 hojas **escaneadas con etiquetado manual** (R-01), y
ese conjunto no existe todavía. Las 300 de esta medición son sintéticas: la plantilla real, marcada
al azar y «fotografiada» con condiciones al azar. Miden la lógica dentro de esas condiciones, no el
papel arrugado ni una luz cualquiera. Para eso están las fotos del prototipo, abajo.

---

## 1. La hoja del prototipo (R-05)

Se imprimió la plantilla en carta y se marcaron las 40 preguntas, con el código `T12345678`, inventado:

- **Preguntas 1 a 30:** una marca clara, de la 1 a la 20 con lápiz y de la 21 a la 30 con esfero.
- **Preguntas 31 a 40, una por caso:**
  - en blanco;
  - doble marca;
  - tenue;
  - una marca borrada y otra encima;
  - una marca borrada sola;
  - un chulo;
  - una marca que se sale del círculo;
  - media burbuja;
  - una X;
  - una marca clara.

Se tomaron tres fotos de celular, de noche y con un foco: desde arriba (11,3 px/mm), inclinada unos
30° (11,7 px/mm) y con una sombra sobre las preguntas 29 a 40 (13,0 px/mm).

| Foto | Respuestas | Código | Mal leídas sin aviso |
|---|---|---|---|
| Desde arriba | Las 40 como se esperaba | Las 8 columnas a revisión, por el brillo del lápiz | 0 |
| Inclinada | 1 a 12 (lápiz con brillo), 32 y 37 a revisión; el resto, bien | Completo | 0 |
| Con sombra | Las 40 como se esperaba | Completo | 0 |

La tenue (33) se leyó como B en dos fotos: un lápiz suave que cubre todo el círculo cuenta como
marca, como decidió el equipo. Giradas 90° y 180°, las tres dan lo mismo. Con JPEG de calidad 40,
también. Desenfocadas 4 o 6 px, o reducidas a un tercio o un cuarto, quedan ilegibles con el motivo.

Las fotos no están en el repositorio: son de celular y pesan unos 4 MB cada una. La prueba
`tests/test_lectura_fotos_r05.py` las lee si `OMR_FOTOS_R05` apunta a su carpeta.

**Lo que mostraron**, y que cambió el diseño (cada punto está en ADR-0023):

| Lo que pasó | Lo que se decidió |
|---|---|
| Con un umbral para toda la hoja, las burbujas vacías bajo la sombra salían llenas | Cada burbuja se mide contra un anillo de papel a 3,0-3,5 mm de su centro |
| Enderezada con las cuatro marcas, la hoja quedó corrida hasta 1,1 mm, y el contorno impreso entraba en la zona medida | Cada burbuja se busca a ±1,5 mm por su contorno, y el corrimiento se suaviza con el de las vecinas |
| Una marca de lápiz con el reflejo del foco rellenó 0,06, como el papel | Una burbuja con el interior desparejo (dispersión de 0,07 o más) no se da por vacía |
| Girada 180°, las columnas de respuestas calzan con otras columnas | La orientación sale del parecido de la hoja entera con la plantilla |

---

## 2. EC-01 y EC-02: 300 hojas sintéticas

**Cómo se generan.** Cada pregunta se marca al azar con una de estas formas:

| Forma de marcar | Frecuencia | Lo correcto |
|---|---|---|
| Clara: lápiz o esfero del 45 % al 80 % más oscuro que el papel, del 80 % al 112 % del círculo, corrida hasta 0,4 mm | 78 % | Leer la opción |
| En blanco | 8 % | Sin marca |
| Doble marca | 2 % | Revisión |
| Media burbuja | 2 % | Revisión |
| Tenue, del 15 % al 25 % más oscura que el papel | 2 % | Revisión |
| Chulo | 1,5 % | Revisión |
| X | 1,5 % | Revisión |
| Borrada sola | 2 % | Sin marca, o revisión |
| Borrada y otra encima | 2 % | Leer la otra, o revisión |
| Con brillo, como el del prototipo | 1 % | Leer la opción, o revisión |

**La foto de cada hoja** sale de estas condiciones, al azar dentro de lo que la lectura acepta:

- resolución de 9,4 a 13 px/mm, la de una foto de celular de la hoja entera;
- perspectiva hasta un 15 %;
- giro de 90°, 180° o 270° en el 30 % de las hojas;
- sombra en el 30 % de las hojas;
- desenfoque hasta 1,2 px, ruido de 2 a 6 niveles y JPEG de calidad 65 a 95.

**Resultado** (`medicion-lectura-ec01-ec02.json`, semilla 2026):

| Forma | Bien | A revisión sin necesitarlo | Error silencioso |
|---|---|---|---|
| Clara | 9 406 | 0 | 0 |
| En blanco | 970 | 0 | 0 |
| Doble marca | 247 | | 0 |
| Media burbuja | 215 | | 0 |
| Tenue | 207 | | 0 |
| Chulo | 181 | | 0 |
| X | 176 | | 0 |
| Borrada sola | 239 | 0 | 0 |
| Borrada y otra encima | 222 | 0 | 0 |
| Con brillo | 0 | 137 | 0 |

- **Códigos:** los 300 completos y bien leídos.
- **Hojas ilegibles:** ninguna.
- **Preguntas a revisión sin necesitarlo:** 0,46 por hoja en promedio, todas por el brillo.
- **Tiempo de lectura, en un núcleo sin límite:** p50 de 378 ms, p95 de 459 ms.

**El brillo y la resolución.** Las marcas con brillo se generaron como las de las fotos: un 30 % de
granos que reflejan y el resto entre un 8 % y un 30 % más oscuro que el papel. Con eso se fijó la
resolución mínima. Desde 7,9 px/mm, la dispersión de una marca con brillo no bajó de 0,077, aun con
1,2 px de desenfoque. A 5,9 px/mm bajó a 0,060, por debajo del corte, y se perdió hasta el 21 % de
esas marcas. Por eso la lectura rechaza las hojas por debajo de 7,5 px/mm.

**Para repetirla**, desde `backend/`:

    python -m herramientas.medir_lectura --hojas 300 --semilla 2026 --json medicion.json

Termina con código 1 si hubo algún error silencioso.

---

## 3. EC-03 y EC-04: el sistema completo

**Dónde.** `docker compose` local con `redis`, `postgres`, `api` y `worker`, construidos con el
Dockerfile del proyecto, y los límites de `deploy/compose.lab.yaml`: el worker con 96 MB y 0,25 CPU,
y la API con 384 MB y 0,5 CPU. La clave de cada examen se copió a mano al volumen, porque A-04
todavía no la registra.

**Las hojas** son como un escaneo a 200 DPI en gris: 8,5 px/mm, derechas, sin sombra, marcadas al
azar como las de la sección 2. Pesaron 456 KB en promedio.

**Cómo se mide el tiempo.** Con el registro de los dos procesos:

- **por hoja**, de `trabajo_publicado`, que la API escribe al dejarla en la cola, antes de
  confirmar, a `hoja_procesada`, que el worker escribe cuando el resultado quedó guardado;
- **por lote**, de `lote_confirmado` al último `hoja_procesada` del examen.

| | EC-03: 20 hojas sueltas, una cada 8 s | EC-04: un lote de 200 |
|---|---|---|
| Procesadas | 20 de 20 | 200 de 200 |
| De la carga al resultado, p50 / p95 / máximo | 1,2 s / **1,7 s** / 2,5 s | No aplica: cada hoja espera detrás de las demás |
| Lote completo | | **214 s (3,6 min)** |
| Lectura en el worker, p50 / p95 | 1,19 s / 1,69 s | 1,01 s / 1,41 s |
| Estado de las hojas | 20 en revisión | 195 en revisión, 5 calificadas |

Casi todas quedan en revisión porque las hojas sintéticas traen marcas ambiguas a propósito, en
promedio unas cuatro por hoja. En un examen real, la proporción depende de cómo marquen los
estudiantes y de la luz de la foto.

**CPU y memoria durante el lote** (`docker stats` cada 2 s, 69 muestras):

| | CPU, máximo | Memoria de trabajo, máximo |
|---|---|---|
| Worker (0,25 CPU, 96 MiB) | 26 % de un núcleo: **todo su límite** mientras procesa | 78 MiB, el 81 % de su límite |
| API (0,5 CPU, 384 MiB) | 14 % de un núcleo, el 28 % de su límite | 57 MiB, el 15 % de su límite |

- Ni reinicios ni procesos muertos por memoria.
- El contador total del contenedor del worker sí llegó a los 96 MiB, porque incluye la caché de
  disco de las imágenes leídas, y el kernel la libera cuando hace falta.
- EC-04 pide la CPU y la memoria **del servidor** por debajo del 85 %. El worker usa todo su cuarto
  de CPU porque ese es su tope, que lo deja en ese cuarto aunque haya más hojas. Lo que pide el
  escenario se mide en el servidor del laboratorio.

**Para repetirla**, desde `backend/`, con el sistema arriba en el puerto 8010:

    python -m herramientas.medir_procesamiento cargar --url http://localhost:8010 \
        --examen MEDICION-EC03 --hojas 20 --pausa 8 --clave MEDICION-EC03.json
    python -m herramientas.medir_procesamiento cargar --url http://localhost:8010 \
        --examen MEDICION-EC04 --hojas 200 --semilla 4 --clave MEDICION-EC04.json
    docker compose logs --no-log-prefix api worker > registro.jsonl
    python -m herramientas.medir_procesamiento analizar registro.jsonl --examen MEDICION-EC04

Antes de subir las hojas, la clave de cada examen se copia a `RUTA_CLAVES` dentro del volumen.

---

## 4. La revisión manual con las fotos del prototipo (RF-08)

**Qué se hizo.** Las tres fotos del prototipo pasaron por el mismo paso del worker
(`leer_y_calificar`, sin la cola) con la clave `PROTOTIPO-R05`, y quedaron tres hojas en revisión.
La API local y el sitio, en Edge sin ventana, leyeron ese registro.

| Foto | Nota provisional | Preguntas por revisar | Código |
|---|---|---|---|
| Desde arriba | 3,9 | 32, 36, 38 y 39 | Incompleto, por el brillo |
| Inclinada | 2,3 | 19: de la 1 a la 12 (lápiz con brillo) y siete de los casos difíciles (32 a 34 y 36 a 39) | Completo |
| Con sombra | 3,8 | 32, 34, 36, 38 y 39 | Completo |

**Lo que mostró.**

- `GET /examenes/PROTOTIPO-R05/revision` devolvió las tres hojas con el recorte de cada fila, lo
  que se ve en cada burbuja y su confianza, y **ningún campo con la respuesta correcta**.
- En la hoja de arriba se resolvieron las cuatro: la 32 como «Ninguna», la 36 como C, la 38 como B y
  la 39 como D. `calificacion` dio una correcta, dos incorrectas y una anulada, y la nota pasó de
  3,9 a 4,0. Siguió provisional, porque el código quedó incompleto.
- El registro de revisiones guardó cada resolución con el nombre escrito y la hora. El log de la
  API registró `revision_guardada` sin el nombre.
- `GET /examenes/PROTOTIPO-R05/resultados` mostró la hoja con su nota nueva y `revisada: true`. La
  automática sigue en el registro de resultados (RNF-15).

![La pantalla de revisión después de guardar la hoja 1: la hoja 1 revisada con 4,0, y la hoja 2
abierta en su pregunta 1, con el recorte de la fila y las opciones A a D y «Ninguna»](rf-08-revision.png)

**Cuánto pesa lo que se relee.** Cada hecho del registro de resultados ocupó unos 21 KB (la lectura
de las 160 burbujas y del código, más la nota). Un examen de 200 hojas son unos 4 MB, y la pantalla
de carga los vuelve a leer cada 3 s mientras espera notas (R-26).

---

## 5. Imágenes que piden más memoria de la que tiene el worker

**Lo que se encontró.** OpenCV decodifica un JPEG grande a la mitad o a la cuarta parte sin armar la
imagen entera, pero un PNG no: lo arma entero y después lo achica. Un PNG blanco de
10 000 × 10 000 px pesa 120 KB, pasa la comprobación de la carga (es un PNG de verdad y está lejos
de los 20 MB) y pide más de 100 MB al decodificarse.

| Prueba, en un contenedor con la imagen del worker, 96 MB y 0,25 CPU | Antes | Después |
|---|---|---|
| PNG blanco de 4 000 × 4 000 px (21 KB) | Se decodifica | Se decodifica |
| PNG blanco de 10 000 × 10 000 px (120 KB) | **Muerto por memoria (salida 137)** | `ImagenIlegible`, sin decodificar |
| PNG blanco de 20 000 × 20 000 px (440 KB) | No se probó: en Windows, el mismo paso llegó a 446 MiB | `ImagenIlegible`, sin decodificar |

**Por qué era grave.** Un trabajo cuyo worker muere vuelve a la cola sin contar el intento
(ADR-0020): el worker se reiniciaba, tomaba la misma hoja y volvía a morir, y ninguna otra hoja se
habría leído.

**El arreglo** (ADR-0023, punto 3): `vision.tamano_del_encabezado` lee el ancho y el alto del
encabezado del PNG o del JPEG antes de decodificar. Un PNG de más de 16 megapíxeles o un JPEG de
más de 256 queda ilegible con su motivo. Cinco pruebas en `test_vision.py`; sin el tope fallan las
dos de las imágenes enormes.

**Lo que sí cabe**, medido con el contador de memoria del mismo contenedor
(`/sys/fs/cgroup/memory.peak`):

- una hoja sintética de 16 megapíxeles en JPEG, leída completa con sus recortes: 69 MiB;
- un JPEG de 15 000 × 15 000 px (225 megapíxeles, por debajo del tope), decodificado a la cuarta
  parte: 77 MiB.

Las fotos que prepara el sitio tienen 3 200 px de lado mayor, así que el tope solo alcanza a quien
llama a la API directamente.

**Y para cualquier otra causa (R-36, ADR-0023, punto 11).** Si el worker muere por otra razón con
una hoja en la mano, esa hoja ya no vuelve igual: cada vuelta desde la lista en curso cuenta como un
intento, y después de cuatro va a la lista de fallidos con el motivo, mientras las demás se leen.
Tres pruebas en `test_mensajeria.py`, contra Redis; sin la suma del intento falla la de la hoja que
mata al worker, que se queda tomándola para siempre.

---

## 6. Lo que queda abierto

- **R-01 y R-04.** EC-01 sobre 300 hojas escaneadas y etiquetadas a mano, y calibrar el umbral de
  70 con ellas.
- **El servidor del laboratorio.** Repetir EC-03 y EC-04 en el entorno desplegado y medir la CPU del
  servidor, que es lo que EC-04 pide.
- **El tamaño de lo que se sube.** Un lote de 200 hojas como estas pesó 91 MB, cerca del tope de
  100 MB por petición, y una foto de celular pesa de 3,5 a 4,6 MB. Se decidió que la pantalla de
  carga pase las fotos a gris, les deje 3 200 px en el lado mayor y las mande en tandas de hasta
  90 MB (ADR-0023). Pasadas así, las tres fotos del prototipo quedaron de 610 a 740 KB y se leyeron
  igual, burbuja por burbuja. Con 200 fotos de unos 650 KB, el presupuesto diario de 256 MB
  (ADR-0022) alcanza para un examen por día.
- **Fotos de día.** Las del prototipo se tomaron de noche con un foco, que es la luz que más brillo
  le saca al grafito.
- **Una hoja subida dos veces se califica dos veces (R-24).** Cada carga le da a la hoja un
  `hoja_id` nuevo, y la pantalla la muestra dos veces.
- **Quién resuelve una revisión (AM-02).** El nombre que queda en el registro no se verifica, y
  cualquiera con la URL puede resolver; vale solo con hojas sintéticas, hasta A-05.
