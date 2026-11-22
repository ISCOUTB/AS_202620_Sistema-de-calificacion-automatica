# 0023 · Leer las hojas en posiciones fijas y mandar a revisión lo que no se ve bien

- **Estado:** aceptado
- **Fecha:** 2026-11-05
- **Decide:** Josué Ortega De Arco, María Restrepo Licona, Sebastián Cañas Plata, Susana Rosales Castellar
- **Escenarios de calidad relacionados:** [EC-01](../arc42/arc42-template-ES.md#ec-01) (exactitud), [EC-02](../arc42/arc42-template-ES.md#ec-02) (marcas ambiguas), [EC-03](../arc42/arc42-template-ES.md#ec-03) (tiempo por hoja), [EC-04](../arc42/arc42-template-ES.md#ec-04) (lote de 200)
- **Riesgos:** R-04 (el umbral de 70 es un supuesto), R-05 (sin experiencia con OpenCV: el prototipo), R-07 (costo de una hoja), R-36 (una hoja que mata al worker)
- **Restricciones que lo acotan:** RNF-01 (la calificación es OMR, sin LLM), RNF-02 (hoja de formato fijo con marcas de registro), RNF-12 (el código del estudiante no va al log), RNF-16 (US$0); el worker tiene 96 MB y 0,25 CPU en el servidor del laboratorio ([ADR-0021](0021-desplegar-en-el-servidor-del-laboratorio-con-el-sitio-compilado-en-el-ci.md)); R-06 sigue abierto
- **Relación con otros ADR:** es el ADR que arc42 §4 anunciaba «al calibrar el umbral (R-04)». Precisa el punto 4 de [ADR-0018](0018-dar-a-la-hoja-una-identidad-propia-y-derivar-su-estado-de-la-bitacora.md) (el estado de una hoja ya no sale solo de la bitácora) sin reemplazarlo. Pone la clave y los resultados detrás de puertos, en el mismo punto de aislamiento que el almacén y la bitácora ([ADR-0002](0002-procesar-calificacion-de-forma-asincrona.md) §4, [ADR-0006](0006-registrar-la-recepcion-en-una-bitacora-antes-de-encolar.md)). Usa los reintentos de [ADR-0020](0020-entregar-los-trabajos-al-menos-una-vez-con-reintentos-y-lista-de-fallidos.md) y precisa su recuperación (punto 11) sin reemplazarlo

**La decisión, en una frase:** el worker lee cada hoja en las posiciones que fija el formato v1
(carta, 40 preguntas, código `T` + 8 dígitos), mide cada burbuja contra el papel que la rodea,
asigna una respuesta solo si la confianza de marcarla y la de descartar las demás llegan al umbral
(70, configurable de 51 a 100), manda a revisión todo lo demás, también lo que no se ve bien, y deja
el resultado en un registro de resultados de solo agregado, aparte de la bitácora, hasta R-06.

---

## Contexto

Hasta el 2-nov, `omr` y `calificacion` solo tenían su `__init__.py`: el worker abría la imagen de
cada hoja y la registraba, nada más (A-02 y A-03, Declarados). R-05 pedía un prototipo antes de
especificar la lectura, «aunque sea sobre una sola hoja, para convertir la incertidumbre en
información».

**El prototipo.** Se imprimió la plantilla y se marcaron 40 preguntas: 30 con una marca clara (20 con
lápiz y 10 con esfero), y diez casos difíciles (en blanco, doble marca, tenue, borrada, chulo, X,
media burbuja, una que se sale del círculo). Se tomaron tres fotos de celular, de noche y con un
foco: desde arriba, inclinada unos 30° y con una sombra encima. Lo que mostraron cambió el diseño
(`docs/evidencia/medicion-lectura-omr.md`):

- Con un umbral para toda la hoja, las burbujas vacías bajo la sombra salían llenas.
- La hoja no queda plana: después de enderezarla con las cuatro marcas quedan corrimientos de hasta
  1,1 mm, y el contorno impreso entra en la zona que se mide.
- El grafito brilla con la luz de frente: una marca de lápiz se vio con un relleno de 0,06, tan
  clara como el papel. Leerla como vacía es una incorrecta que nadie revisa.
- Girada 180°, casi todas las burbujas de respuesta caen sobre otras burbujas.

**Fuerzas:**

- **EC-02 y QG-3:** ninguna calificación errónea silenciosa. Una `SIN_MARCA` cuenta como incorrecta
  sin pasar por el profesor, así que leer vacía una burbuja marcada es tan grave como inventar una
  respuesta.
- **RF-03:** el sistema nunca elige entre candidatas.
- **La pantalla de revisión ya existe** (`frontend/lib/features/revision`) y fija los tipos de marca
  (vacía, tenue, borrón, completa), la confianza como «probabilidad de que la marca sea
  intencional» y la nota en décimas.
- **El worker tiene 96 MB y 0,25 CPU**, y con OpenCV importado ya ocupa 62 MiB antes de leer nada.
- **`calificacion` no puede importar `autoria`**, que es la dueña de la clave (ADR-0007).
- **R-06 está abierto:** no hay base de datos donde guardar la nota.

## Alternativas consideradas

### 1. Cómo encontrar las burbujas

| Alternativa | A favor | En contra | Resultado |
|---|---|---|---|
| **Detectar los círculos y ordenarlos** | No depende de un formato | Si uno no se detecta, todos los siguientes se corren un lugar y la hoja sale mal calificada sin aviso | Descartada |
| **Posiciones fijas: cuatro marcas, una homografía y cada burbuja donde el formato dice** | Un error de detección no corre a las demás | Exige un formato fijo, que RNF-02 ya pide | **Elegida** |
| **Lo mismo, con un ajuste fino de cada burbuja** | Corrige la hoja que no queda plana | Si el ajuste pudiera saltar a la burbuja vecina, volvería el corrimiento silencioso | **Elegida, acotada:** se busca a ±1,5 mm, y las burbujas están a 7 mm o más |

### 2. Contra qué se mide cada burbuja

| Alternativa | A favor | En contra | Resultado |
|---|---|---|---|
| **Un umbral para toda la hoja (Otsu)** | Simple | Con la sombra del prototipo, burbujas vacías salían llenas | Descartada |
| **La hoja con la luz emparejada** (dividida por un fondo estimado) | Corrige la luz que cambia despacio | No sigue el borde de una sombra: en el prototipo dejó vacías por encima del corte de completa | Descartada para medir; se usa para encontrar las marcas |
| **El papel que rodea cada burbuja** (un anillo a 3,0-3,5 mm) | Está bajo la misma luz que la burbuja | Una marca que se sale del círculo oscurece la referencia: se toma la mediana | **Elegida** |

### 3. Cómo se decide una pregunta

| Alternativa | A favor | En contra | Resultado |
|---|---|---|---|
| **La burbuja más llena** | Siempre da una respuesta | Elige entre candidatas (RF-03) | Descartada |
| **Una marca si su confianza llega al umbral y la de las demás no** | Simple | Una segunda burbuja con confianza 60 se descartaría sin la exigencia con que se aceptó la primera | Descartada |
| **Una marca si la confianza de marcarla y la de descartar a la segunda llegan al umbral; si no, revisión** | Una sola exigencia para aceptar y para descartar | Con un umbral de 50 o menos, una burbuja contaría como marcada y como vacía a la vez | **Elegida**, con el umbral de 51 a 100 |

### 4. Qué se hace con lo que no se ve bien

| Alternativa | A favor | En contra | Resultado |
|---|---|---|---|
| **Confiar en el relleno** | Una sola medida | Una marca con brillo, o tapada por una mancha, se lee vacía | Descartada |
| **Contar los puntos más claros que el papel** (el reflejo) | Se separó bien en las fotos: 14-21 % en las marcas con brillo, 2 % en las vacías | Con poca resolución o un poco de desenfoque, los reflejos se promedian y desaparecen | Descartada después de medirla |
| **La dispersión del interior y la visibilidad del contorno impreso** | Una burbuja vacía es pareja y muestra su contorno; la que brilla queda despareja aun desenfocada, y la tapada no muestra contorno | Una burbuja vacía cruzada por el borde de una sombra puede ir a revisión sin necesitarlo | **Elegida** |

### 5. Cómo se sabe la orientación

| Alternativa | A favor | En contra | Resultado |
|---|---|---|---|
| **Suponer la hoja derecha** | Nada que hacer | Una foto de cabeza se lee corrida | Descartada |
| **Por las burbujas** | Ya se miden | Girada 180°, las columnas de respuestas caen a menos de 0,5 mm de otras | Descartada |
| **Por el parecido de la hoja entera con la plantilla, en las cuatro orientaciones** | La hoja derecha dio de 0,51 a 0,60; girada, 0,08 o menos; otra hoja con las cuatro marcas, 0,03 | Una comparación más por hoja (a un octavo de la resolución, unos milisegundos) | **Elegida**, con el mínimo en 0,30 |

### 6. Dónde queda el resultado

| Alternativa | A favor | En contra | Resultado |
|---|---|---|---|
| **En la bitácora** | Una sola fuente de verdad, como dice ADR-0018 | La bitácora tiene un solo escritor, la API (V-4): el worker escribiendo en el mismo archivo rompe la regla que la hace segura | Descartada |
| **Esperar a R-06** | Sin transición | Deja A-02 y A-03 sin dónde guardar nada hasta que haya base de datos | Descartada |
| **Un registro de resultados aparte, de solo agregado, detrás de un puerto** | El mismo patrón que la bitácora, con su propio escritor (el worker); Postgres entra después como otro adaptador | El estado de una hoja queda en dos registros (tres, desde el punto 12) | **Elegida**, hasta R-06 |

### 7. El papel

La primera plantilla era A4, como pedía el prompt de partida. Al imprimir apareció que en Colombia
se usa carta: una A4 al 100 % en carta pierde los últimos 18 mm, y con ellos las marcas de abajo.
**El formato v1 es carta.** Siguió siendo la v1 porque no se había impreso ninguna hoja con la A4.

## Decisión

1. **Formato v1** (`omr/formato.py`): carta vertical, cuatro marcas cuadradas de 10 mm a 10 mm de
   los bordes, 40 preguntas en dos bloques de 20 con opciones A a D, y el código como una `T`
   impresa y ocho columnas del 0 al 9. La plantilla imprimible (`omr/plantilla.py`) sale de la misma
   definición con que se lee. Cambiar una medida es cambiar la versión.
   **Este semestre, la v1 es el único formato**: otro papel, más de 40 preguntas o una quinta opción
   quedan fuera. Un examen sí puede tener menos de 40 preguntas, porque solo se califican las que
   trae la clave (`test_las_filas_que_la_clave_no_menciona_no_cuentan`). Las razones:
   - **Cada corte se midió con la v1:** el anillo de papel a 3,0-3,5 mm, el ajuste de ±1,5 mm (que no
     salta a la vecina porque las burbujas están a 7 mm o más) y el parecido mínimo de 0,30 para la
     orientación. Un formato sin medir es una hoja que puede leerse mal sin aviso (QG-3).
   - **La única hoja impresa y fotografiada es la v1 en carta** (el prototipo de R-05). Ningún otro
     papel se ha probado.
   - **Varios formatos piden que cada examen diga el suyo**, y eso es parte de registrar la clave
     (A-04), que no existe. Una quinta opción toca además el modelo, el contrato y la pantalla de
     revisión.
   - **Queda poco semestre**, y A-04 y A-05 van primero: A-05 es la condición para usar hojas
     reales (AM-02).
2. **Lectura** (`omr/vision.py`), en este orden: leer el tamaño en el encabezado del archivo,
   decodificar en gris (a la mitad o la cuarta parte si la foto pasa de 16 megapíxeles), comprobar
   contraste y tamaño, encontrar las cuatro marcas, elegir la orientación por el parecido con la
   plantilla, comprobar la resolución, enderezar, ajustar cada burbuja con su contorno y el de sus
   vecinas, comprobar la nitidez y medir cada burbuja contra su anillo de papel.
3. **Una hoja que no se puede leer queda `ILEGIBLE` con su motivo y no se reintenta**: formato no
   soportado (incluido el PDF), imagen ilegible (contraste, tamaño, resolución o nitidez), marcas no
   encontradas u hoja no reconocida. Leer otra vez la misma imagen da lo mismo. También queda
   ilegible, sin decodificarse, la imagen cuyo encabezado declara más píxeles de los que el worker
   puede armar: un PNG de más de 16 megapíxeles, porque OpenCV no lo decodifica reducido, o un JPEG
   de más de 256.
4. **Decisión de cada pregunta** (`omr/decision.py`), con `c1` y `c2` las confianzas de las dos
   burbujas más llenas y `u` el umbral: doble marca si las dos llegan a `u`; una marca si `c1` y
   `100 − c2` llegan a `u`; sin marca si `100 − c1` llega a `u`; en cualquier otro caso, dudosa. El
   código usa la misma regla por columna; una columna que no queda clara lleva `?` y el código queda
   incompleto.
5. **Una burbuja que se ve vacía no se da por vacía** si su interior está desparejo (dispersión de
   0,07 o más) o su contorno impreso no se ve: queda con confianza 50, que con cualquier umbral
   válido manda la pregunta a revisión.
6. **El umbral es configuración** (`OMR_UMBRAL_DE_CONFIANZA`, 70 por omisión). El worker lo comprueba
   al arrancar: fuera de 51 a 100 no arranca.
7. **La nota** (`calificacion/nota.py`) va en décimas, de 0 a 50, redondeada a la mitad hacia arriba
   como en la pantalla de revisión. Una dudosa o una doble marca queda por revisar, con 0 puntos
   hasta que el profesor la resuelva, y la nota es provisional mientras haya alguna; una sin marca
   cuenta como incorrecta; una anulada da 0 puntos y no cambia el total posible. Sin una clave
   habilitada no hay nota (RF-07); una clave mal escrita cuenta como si no hubiera clave, con el
   motivo.
8. **La clave entra por un puerto** (`infraestructura/claves.py`): el worker la busca y se la pasa a
   `calificar`, que no sabe de dónde salió. Hasta A-04, la clave es un JSON por examen en
   `RUTA_CLAVES`, escrito a mano.
9. **El resultado va a un registro de resultados** (`infraestructura/resultados.py`): un hecho por
   hoja procesada, de solo agregado, con el `hoja_id`, el trabajo, el estado en que quedó la hoja
   (calificada, en revisión, sin clave habilitada o ilegible), el motivo si no tiene nota, la lectura
   y la nota. **Precisa el punto 4 de ADR-0018:** el estado de una hoja es el último hecho entre los
   registros, cada uno con su único escritor: la bitácora dice cómo se recibió, el registro de
   resultados cómo se leyó y, desde el punto 12, el de revisiones qué resolvió el profesor. El
   código del estudiante va en el registro de resultados, que es donde hace falta, y nunca en el
   log.
10. **En el worker**, un fallo de disco al leer la clave o al guardar el resultado se reintenta como
    el de leer la imagen (ADR-0020), y cualquier otro error va a la lista de fallidos, sin tumbar el
    ciclo.
11. **La muerte del worker cuenta como un intento.** Un trabajo que vuelve de la lista en curso al
    arrancar el worker vuelve con un intento más, y el que ya gastó los cuatro va a la lista de
    fallidos con el motivo, salvo que ya se haya procesado. **Precisa la recuperación de
    ADR-0020**, que lo devolvía igual: una hoja que mata al worker lo mataba en cada reinicio, y
    como vuelve a la cabeza de la cola, ninguna otra hoja se leía (R-36).
12. **La revisión manual (RF-08).** El profesor ve el recorte de la fila de cada pregunta en
    revisión y dice qué marcó el estudiante (A, B, C, D o ninguna); `calificacion` convierte eso en
    un veredicto con la clave y recalcula la nota. La respuesta correcta no sale de la API. Cada
    resolución es un hecho nuevo en un registro de revisiones, con el nombre que escribe el
    profesor y la hora, y solo lo escribe la API; la última resolución de cada pregunta manda, y
    la nota automática queda como historia.

Cada corte de los puntos 2 y 5 es una constante con nombre en su archivo, con el dato que la fijó.

## Consecuencias

### Positivas

- **Ninguna respuesta leída mal sin aviso** en las tres fotos del prototipo, ni en 300 hojas
  sintéticas con perspectiva, giro, sombra, desenfoque, ruido y compresión al azar. En esas 300:
  EC-01, 9 406 de 9 406 marcas claras bien leídas (100 %; pide ≥98 %); EC-02, 1 026 de 1 026 marcas
  ambiguas a revisión (100 %; pide ≥99 %); los 300 códigos bien leídos.
- **EC-03:** con los límites del servidor, de la carga al resultado, p95 de 1,7 s y máximo de 2,5 s
  por hoja suelta (pide ≤5 s).
- **EC-04:** un lote de 200 hojas, procesado entero en 3,6 min (pide ≤10 min), sin ninguna fallida.
  La memoria de trabajo del worker llegó a 78 MiB, el 81 % de su límite.
- **R-07:** una hoja cuesta de 1,0 a 1,7 s del cuarto de CPU del worker, que la usa entera mientras
  procesa. Su pico de memoria fue de 75 MiB con fotos de celular y de 82 MiB con una de 48
  megapíxeles, dentro de los 96 MiB. Con un worker, un lote de 200 tarda unos 3,6 min.
- **La lectura es una función pura** (`leer_hoja`): bytes dentro, lectura fuera. Se prueba sin cola
  ni disco, y cambiar de técnica de visión no toca la calificación.

### Negativas y consecuencias asumidas

- **El brillo del grafito manda mucho a revisión con luz directa.** En la foto desde arriba, el
  código entero; en la inclinada, 12 de las 30 marcas claras. Es lo correcto, porque no se puede
  saber qué hay debajo del reflejo, pero cuesta tiempo al profesor. El aviso de tomar la foto sin
  luz directa va en la pantalla de carga y en la guía del profesor.
- **Hace falta resolución.** Por debajo de 7,5 px/mm la hoja queda ilegible: un escaneo a 150 DPI o
  una foto recomprimida no alcanzan. Una foto de celular de la hoja entera da de 11 a 13 px/mm, y un
  escaneo a 200 DPI, 7,9.
- **Las fotos se preparan en el navegador antes de subirlas.** Una foto de celular pesa de 3,5 a
  4,6 MB: 200 no entraban en una petición (100 MB) ni en el presupuesto diario de carga (256 MB,
  ADR-0022). Para que el profesor siga tomando las fotos como siempre, la pantalla de carga las pasa
  a gris, les deja 3 200 px en el lado mayor (unos 650 KB, y la lectura da lo mismo, burbuja por
  burbuja) y las manda en tandas de hasta 90 MB y 250 hojas. Con 3 200 px, la hoja tiene que ocupar
  al menos dos tercios de la foto, y la pantalla lo pide junto con evitar la luz directa. La
  alternativa de que el profesor escaneara se descartó: pide un escáner a mano. La pantalla ya no
  ofrece PDF, que la lectura de esta versión no lee.
- **Las 300 hojas son sintéticas.** Miden la lógica dentro de las condiciones que se generaron, no
  el papel arrugado ni una luz cualquiera. EC-01 sigue pidiendo 300 hojas escaneadas con etiquetado
  manual (R-01), y R-04 sigue abierto: el 70 no se ha calibrado contra hojas reales.
- **El margen de memoria del worker es de unos 14 MiB.** Una foto de 48 megapíxeles ya se decodifica
  a la mitad para caber. Un PNG, en cambio, se decodifica entero: uno blanco de 10 000 × 10 000 px
  pesa 120 KB, entra por la ruta pública y, en un contenedor de 96 MB, mataba al worker por memoria
  (salida 137). Como un trabajo cuyo worker muere volvía a la cola sin contar el intento
  (ADR-0020), lo habría vuelto a tomar en cada reinicio, y ninguna otra hoja se habría leído. Por
  eso el tope por encabezado del punto 3, y por eso el punto 11, para cualquier otra causa que
  mate al worker. Con el tope, medido con el contador del contenedor de 96 MB: una hoja de 16
  megapíxeles leída completa llega a 69 MiB, y un JPEG de 225 megapíxeles, a 77.
- **El estado de una hoja queda en tres registros** hasta R-06, cada uno con un solo escritor: la
  bitácora (la API, al recibir), los resultados (el worker, al leer) y las revisiones (la API, cuando
  el profesor resuelve). Quien quiera el estado vigente tiene que leer los tres.
- **La clave se copia a mano** al volumen hasta A-04.
- **Las notas se ven sin el código del estudiante.** `GET /examenes/{examen_id}/resultados`
  (contrato 1.6.0) publica el último resultado de cada hoja, y la pantalla de carga lo muestra
  junto a cada archivo a medida que el worker avanza. La ruta es tan pública como las demás hasta
  A-05, y el modelo de amenazas aceptó ese riesgo solo mientras no entren hojas reales (AM-02): por
  eso dice si el código se leyó completo y nada más. Mostrar el código y exportar las notas llegan
  con A-05.
- **El profesor resuelve las preguntas en revisión desde la aplicación (RF-08) antes de A-05**
  (contrato 1.8.0). Al leer la hoja, el worker guarda un recorte de la fila de cada pregunta en
  revisión, sin el código del estudiante. El profesor dice qué marcó el estudiante, nunca ve la
  clave, y `calificacion` decide si es correcto y recalcula la nota. Cada decisión queda con el
  nombre que escribe el profesor y la hora (RF-10); la nota automática queda como historia y la
  corregida se marca `revisada` (RNF-15). Lo que cuesta hacerlo antes de A-05: **el nombre no se
  verifica**, y como las rutas son públicas, cualquiera podría resolver una revisión o deducir la
  clave probando opciones. Es la misma condición de AM-02, que este cambio amplía: vale solo con
  hojas sintéticas, y la cierra A-05.

## Reversión

- Los cortes son constantes con nombre: calibrarlos (R-04) es cambiar un número y volver a correr
  `herramientas/medir_lectura.py` y la prueba de las fotos.
- El formato está versionado: una v2 convive con la v1, porque cada lectura guarda su versión.
- La lectura se puede reemplazar sin tocar `calificacion`, que solo recibe una `LecturaDeHoja`.
- El registro de resultados y la fuente de claves son puertos: Postgres (R-06) y A-04 entran como
  adaptadores. Los hechos ya escritos se migran tal cual, porque ya son una tabla de hechos.
- Que la muerte del worker cuente como un intento es una función, `recuperar_en_curso`: volver a la
  recuperación de ADR-0020 es quitarle la suma.

## Qué dato haría revisar esta decisión

- **Una sola respuesta leída mal sin aviso** en hojas reales, o menos del 98 % de exactitud en el
  conjunto de R-01.
- **Más de tres preguntas por hoja a revisión** en un examen real: el sistema dejaría de ahorrar
  tiempo (T-1).
- **Un worker que muere por memoria** en el servidor.
- **Fotos de día** con un brillo muy distinto del de las fotos de noche.
- **Un profesor que necesite otro papel, más de 40 preguntas o cinco opciones.** Se resuelve con un
  formato nuevo, que conviva con la v1: con su propia hoja impresa y fotografiada, su medición y el
  formato declarado por examen.

## Trazabilidad

- **Código:** `backend/omr/` (formato, plantilla, vision, decision, lectura, errores),
  `backend/calificacion/nota.py` y `revision.py`, `backend/infraestructura/claves.py`,
  `resultados.py` y `revisiones.py`, `backend/autoria/examenes.py`, `backend/worker/main.py`
  (`leer_y_calificar`), `backend/infraestructura/consumo.py` (`recuperar_en_curso`, punto 11),
  `backend/dashboard/resultados.py` y `revision.py`, y las rutas de exámenes, resultados y revisión
  en `backend/api/main.py`; en el frontend, `features/carga/data/` (preparar y subir las fotos, la
  lista de exámenes, consultar los resultados), el reporte de la pantalla de carga y
  `features/revision/` (la pantalla de revisión y su servicio).
- **Pruebas:** `test_plantilla.py`, `test_vision.py`, `test_decision.py`, `test_lectura.py`,
  `test_lectura_fotos_r05.py` (corre con `OMR_FOTOS_R05`), `test_calificacion.py`,
  `test_claves.py`, `test_resultados.py`, `test_leer_y_calificar.py`,
  `test_ruta_resultados.py`, `test_ruta_examenes.py`, `test_revisiones.py`,
  `test_ruta_revision.py` y las tres de la recuperación en `test_mensajeria.py`; en el frontend,
  `preparacion_de_hojas_test.dart`, `servicio_resultados_test.dart`, `servicio_examenes_test.dart`,
  `servicio_revision_test.dart`, `revision_test.dart` y las de la pantalla de carga.
- **Medición:** `herramientas/medir_lectura.py` (EC-01 y EC-02), `herramientas/medir_procesamiento.py`
  (EC-03 y EC-04), `herramientas/hojas_sinteticas.py`.
- **Evidencia:** `docs/evidencia/medicion-lectura-omr.md` y sus informes JSON.
