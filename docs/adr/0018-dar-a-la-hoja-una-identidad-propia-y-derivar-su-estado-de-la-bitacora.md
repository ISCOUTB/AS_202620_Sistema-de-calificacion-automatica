# 0018 · Dar a la hoja una identidad propia y derivar su estado de la bitácora

- **Estado:** aceptado
- **Fecha:** 2026-10-24
- **Decide:** Josué Ortega De Arco, María Restrepo Licona, Sebastián Cañas Plata, Susana Rosales Castellar
- **Escenarios de calidad relacionados:** [EC-07](../arc42/arc42-template-ES.md#ec-07) (0 % de pérdida silenciosa), y los que todavía no tienen código y van a depender de esta decisión: [EC-03](../arc42/arc42-template-ES.md#ec-03) y [EC-04](../arc42/arc42-template-ES.md#ec-04) (calificar las hojas), [EC-02](../arc42/arc42-template-ES.md#ec-02) (revisión manual)
- **Origen:** la entrega de consistencia y caché, que pide el ADR de la decisión de datos más costosa de revertir; y la violación V-3 del [arc42 §8.3](../arc42/arc42-template-ES.md#83-propiedad-de-datos) («el estado de una hoja vive en dos sitios»)
- **Restricciones que lo acotan:** R-06 abierto (no hay base de datos ni medio definitivo), la bitácora de un solo escritor (V-4) en el disco efímero ([ADR-0012](0012-mantener-el-almacen-en-el-disco-efimero-de-la-instancia-hasta-cerrar-r-06.md)), el contrato publicado que ya consume el sitio
- **Relación con otros ADR:** precisa [ADR-0006](0006-registrar-la-recepcion-en-una-bitacora-antes-de-encolar.md) (la bitácora pasa de registro de recepción a fuente de verdad del estado) y [ADR-0016](0016-acotar-la-espera-de-la-cola-y-hacer-idempotente-al-worker.md) (la idempotencia sigue siendo por trabajo, y ahora se dice por qué) sin reemplazarlos; deja R-06 abierto

**La decisión, en una frase:** cada hoja aceptada recibe un `hoja_id` propio, acuñado una sola vez
por `ingesta` y distinto del `trabajo_id`, que es la identidad a la que se referirá todo lo que se
sepa de ella; y su estado se deriva de la bitácora de hechos, que es la única fuente de verdad, de
la que cualquier otra copia es una proyección.

---

## Contexto

### Cuál es la decisión de datos más cara de revertir

Se revisaron todas las decisiones de datos que el sistema ya tomó, explícitas o no, con una sola
pregunta: si mañana hubiera que cambiarla, ¿qué habría que tocar?

| Decisión de datos | Dónde vive | Qué costaría revertirla |
|---|---|---|
| El presupuesto del proveedor en memoria ([ADR-0015](0015-limitar-el-gasto-del-proveedor-de-llm-con-un-presupuesto-en-la-api.md)) | `autoria/presupuesto.py` | Casi nada: no hay nada guardado; un reinicio lo vacía |
| La caché de propuestas en memoria ([ADR-0019](0019-guardar-en-cache-las-propuestas-de-distractores.md)) | `autoria/cache.py` | Nada: se vacía sola y ninguna nota depende de ella |
| Las marcas de idempotencia en Redis ([ADR-0016](0016-acotar-la-espera-de-la-cola-y-hacer-idempotente-al-worker.md)) | El Key Value | Nada que migrar: vencen solas a los 7 días |
| El formato de la bitácora, JSON Lines ([ADR-0006](0006-registrar-la-recepcion-en-una-bitacora-antes-de-encolar.md)) | `infraestructura/bitacora.py` | Un adaptador del puerto y convertir un archivo |
| El medio de las imágenes y de la persistencia (R-06, [ADR-0012](0012-mantener-el-almacen-en-el-disco-efimero-de-la-instancia-hasta-cerrar-r-06.md)) | Detrás de los puertos `AlmacenDeImagenes` y `BitacoraDeRecepcion` | Caro en volumen (copiar los datos), barato en código: un adaptador. La `referencia` es opaca a propósito para que el cambio no se note afuera |
| **La identidad de la hoja y dónde vive su estado** | Hoy, implícita: el `trabajo_id` | **Todo lo que se guarde de una hoja la referencia**: la detección (A-02), la nota (A-03), la revisión manual (RF-08), la auditoría de quién cambió qué (RF-10), el panel. Cambiarla es migrar cada registro, rehacer cada referencia, cambiar el contrato con una versión mayor y cada cliente con él. Y si alguna vez dos hojas compartieron identidad, o una tuvo dos, no hay forma de separarlas después sin los datos originales |

La última es la única cuyo costo **crece con cada registro** y la única que no está detrás de un
puerto: un puerto aísla dónde se guarda un dato, no cómo se llama. Hoy no hay ningún registro que la
use fuera de la bitácora de demostración, que vive en un disco efímero. Es el momento más barato
que va a tener.

### El defecto de la identidad implícita

Hasta esta decisión, la hoja no tenía identidad propia: el reporte, la bitácora y el worker la
reconocían por el `trabajo_id`, el identificador del encargo que viaja por la cola. Eso funciona
mientras cada hoja tenga exactamente un encargo, y deja de funcionar en tres casos que el sistema ya
tiene escritos:

1. **Recalificar.** Cuando el docente corrija la clave o resuelva una marca ambigua (RF-08), la hoja
   se vuelve a procesar. Si ese segundo encargo lleva un `trabajo_id` nuevo, la nota queda colgada
   de dos identidades distintas para la misma hoja; si lleva el mismo, la marca de idempotencia de
   ADR-0016 lo descarta como repetido durante 7 días. Con un solo identificador hay que elegir entre
   poder reprocesar y no procesar dos veces el mismo encargo.
2. **Reconocer una hoja ya recibida** (R-24). El diseño previsto responde «ya recibida» con la
   identidad de la hoja original. Un `trabajo_id` es la de un intento, no la de la hoja.
3. **Saber el estado vigente** (V-3). La copia de `estado` que viajó en la respuesta no se actualiza
   nunca, y para preguntarle a la bitácora por una hoja hace falta una identidad estable con la
   cual preguntar.

## Alternativas consideradas

### 1. Cuál es la identidad de una hoja

| Opción | A favor | En contra | |
|---|---|---|---|
| **Seguir usando el `trabajo_id`** (statu quo) | Cero cambios | Los tres casos de arriba. Y el costo de separarlas después crece con cada registro | Descartada |
| **Una clave natural: el SHA-256 del contenido y el examen** | Detecta las hojas repetidas sin estructura aparte | Dos archivos idénticos serían una sola hoja: con hojas sintéticas o en blanco, dos estudiantes se fundirían en uno, y esa pérdida no se puede deshacer. Además ata la identidad a una función que podría cambiar | Descartada como identidad; **se usará como atributo** para R-24 |
| **Una clave compuesta: examen y nombre del archivo** | Legible | Los nombres se repiten (`hoja1.jpg` en cada lote) y el docente los controla | Descartada |
| **Un número consecutivo por examen** | Legible para el docente | Necesita un coordinador que entregue el siguiente número, que no existe sin base de datos; con dos instancias chocarían (V-4) | Descartada como identidad; puede ser un atributo de presentación |
| **Un UUID acuñado por `ingesta` al aceptar la hoja, distinto del `trabajo_id`** | Estable, no depende del contenido ni del medio, no necesita coordinación, sirve de clave primaria en cualquier base que elija R-06 | Un campo más en el modelo, la bitácora, la cola y el contrato | **Elegida** |

### 2. Dónde vive el estado de una hoja

| Opción | A favor | En contra | |
|---|---|---|---|
| **Un estado que se sobrescribe** (una columna `estado`) | Una lectura y listo | Pierde la historia, que RF-10 va a pedir; y sobrescribir es justo lo que ADR-0006 evitó para sobrevivir a una caída a mitad de escritura | Descartada |
| **El registro de hechos de solo agregado (la bitácora) como fuente de verdad, y toda otra representación como proyección** | Ya es la forma de la bitácora; la historia sale gratis; una tabla de estado futura se puede reconstruir desde los hechos | Leer el estado es releer los hechos, que con un archivo crece; se resuelve con una proyección cuando haga falta | **Elegida** |
| **Un registro de eventos completo, con un broker** | Escala a varios consumidores | Agrega una pieza que ADR-0017 decidió no agregar todavía, sin un consumidor que la necesite | Descartada |

## Decisión

1. **`hoja_id` es la identidad de la hoja.** Un UUID que `ingesta` acuña una sola vez, al aceptar la
   hoja ([`recepcion.py`](../../backend/ingesta/recepcion.py)). Nunca se reutiliza ni se deriva del
   contenido, del nombre o del orden.
2. **`trabajo_id` es la identidad de un encargo de procesarla.** Una hoja puede tener varios
   trabajos, y todos llevan su `hoja_id` en el payload. El reintento desde la bitácora conserva el
   mismo `trabajo_id`, y por eso el worker es idempotente por trabajo (ADR-0016); volver a procesar
   la hoja, para recalificarla, es un trabajo nuevo de la misma hoja.
3. **Todo dato futuro sobre una hoja se referencia por `hoja_id`**: la detección (A-02), la nota
   (A-03), la revisión manual (RF-08) y la auditoría (RF-10). Una hoja tiene como mucho una nota
   vigente; las anteriores quedan como historia.
4. **La bitácora es la fuente de verdad del estado de cada hoja.** `HojaAceptada.estado`, el reporte
   que ve el docente, una tabla futura o cualquier caché son proyecciones; si discrepan, gana la
   bitácora. Cuando R-06 elija una base de datos, la bitácora pasa a ella como una tabla de hechos
   de solo agregado, no como una columna de estado.
5. **El estado de una hoja no se guarda en caché.** La única caché del sistema guarda propuestas de
   distractores, que no son de ninguna hoja ([ADR-0019](0019-guardar-en-cache-las-propuestas-de-distractores.md)).
6. **Compatibilidad hacia atrás.** Una línea de bitácora escrita antes de esta decisión no trae
   `hoja_id` y se lee con su `trabajo_id` como identidad de la hoja, que es lo que era. No se
   inventa una nueva, que dejaría a la misma hoja con dos.
7. **El contrato pasa a 1.3.0** y publica `hoja_id` como obligatorio en cada hoja aceptada. Solo
   agrega: `trabajo_id` sigue igual.

**Por qué no reemplaza a ADR-0006 ni a ADR-0016.** La bitácora sigue siendo de solo agregado, con el
mismo orden de pasos; lo que cambia es que ahora se dice que es la fuente de verdad del estado, que
ADR-0006 no decía. El worker sigue marcando por `trabajo_id`; lo que cambia es que ahora se sabe por
qué es la clave correcta: es la del encargo, no la de la hoja.

## Consecuencias

### Positivas

- **Recalificar y no procesar dos veces dejan de chocar**: son dos identidades distintas.
- **La identidad no depende de R-06**: un UUID sirve de clave primaria en cualquier base, y no
  necesita un coordinador, así que tampoco choca con más de una instancia.
- **V-3 queda decidida**: hay una fuente de verdad y una identidad con la que preguntarle.
- **Se fijó antes de que haya datos que migrar**: revertirla hoy es quitar un campo.

### Negativas

- **Un campo más** en el modelo, la bitácora, la cola y el contrato, y una línea de compatibilidad
  en la lectura de la bitácora.
- **La fuente de verdad sigue siendo frágil** mientras R-06 esté abierto: un solo escritor (V-4) en
  un disco que se borra con cada despliegue (ADR-0012). Esta decisión dice cuál es la verdad, no la
  hace durable.
- **Leer el estado es releer los hechos.** Con un archivo que crece, preguntar por una hoja cuesta
  más cada día. Cuando haya una consulta de estado, va con una proyección (R-26).
- **El sitio todavía muestra el `trabajo_id`** en el reporte de carga. Mostrar el `hoja_id` es un
  cambio de pantalla que queda para cuando el docente pueda consultar una hoja.

## Reversión

Hoy, quitar el campo: no hay registros fuera de la bitácora de demostración. Cada registro que A-02
o A-03 guarden con esta identidad hace la reversión más cara, que es exactamente por lo que se
decidió ahora. Si hiciera falta, el camino sería el contrario al de la compatibilidad: leer
`hoja_id` y escribir `trabajo_id`, con una versión mayor del contrato.

## Qué dato haría revisar esta decisión

- **Que R-06 elija un medio**: `hoja_id` pasa a clave primaria de la tabla de hojas y la bitácora a
  tabla de hechos. Si el medio elegido no maneja bien UUID como clave, se revisa el formato, no la
  separación.
- **Que el docente necesite un número legible por hoja** («la 17 del parcial»): es un atributo de
  presentación que se agrega, no un cambio de identidad.
- **Que la detección de duplicados (R-24) encuentre dos archivos idénticos que sí son hojas
  distintas**: confirma que el contenido no puede ser la identidad.

## Trazabilidad

- **Código:** [`ingesta/recepcion.py`](../../backend/ingesta/recepcion.py) (acuña el `hoja_id`),
  [`infraestructura/modelo.py`](../../backend/infraestructura/modelo.py) (`HojaAceptada` y
  `EntradaDeBitacora`), [`infraestructura/bitacora.py`](../../backend/infraestructura/bitacora.py)
  (lo escribe, lo relee y lee las líneas viejas), [`worker/main.py`](../../backend/worker/main.py)
  y [`api/esquemas.py`](../../backend/api/esquemas.py) (contrato 1.3.0).
- **Pruebas:** [`test_identidad_de_la_hoja.py`](../../backend/tests/test_identidad_de_la_hoja.py),
  validadas provocando la falla, y [`test_contrato.py`](../../backend/tests/test_contrato.py).
- **Consistencia:** la [tabla de operaciones y garantías](../evidencia/consistencia-y-cache.md).
- **Riesgos:** precisa la acción correctiva de V-3 y abre R-26 ([arc42 §11](../arc42/arc42-template-ES.md#11-risks-and-technical-debts)).
