# Consistencia de los datos y caché

La entrega pide tres cosas: una tabla que diga, operación por operación, qué garantía de
consistencia da el sistema; el diseño de una caché con su política de invalidación; y el ADR de la
decisión de datos más costosa de revertir. Este documento tiene las dos primeras y resume la
tercera; las decisiones completas están en los ADR.

- **Decisiones:** [ADR-0018](../adr/0018-dar-a-la-hoja-una-identidad-propia-y-derivar-su-estado-de-la-bitacora.md)
  (la identidad de la hoja y la fuente de verdad de su estado, la decisión más cara de revertir) y
  [ADR-0019](../adr/0019-guardar-en-cache-las-propuestas-de-distractores.md) (la caché de
  propuestas de distractores).
- **Pruebas:** [`test_identidad_de_la_hoja.py`](../../backend/tests/test_identidad_de_la_hoja.py)
  y [`test_cache_de_propuestas.py`](../../backend/tests/test_cache_de_propuestas.py), más las que
  la tabla cita en cada fila.
- **Riesgos:** R-26 y R-27 en la [sección 11 del arc42](../arc42/arc42-template-ES.md#11-risks-and-technical-debts).
- **Fecha:** 2026-10-24, sobre `master` después de los commits de esta entrega.

## 1. Los datos y dónde viven

QuantIA todavía no tiene base de datos (R-06). Los datos que existen viven en cinco sitios, y cada
uno dura distinto. La garantía de una operación depende de dónde escribe.

| Dato | Dónde vive | Dueño (arc42 §8.3) | Cuánto dura |
|---|---|---|---|
| La imagen de la hoja | Almacén en disco ([`almacen.py`](../../backend/infraestructura/almacen.py)) | `ingesta` | Sobrevive al proceso; no a un despliegue en Render, porque el disco es efímero ([ADR-0012](../adr/0012-mantener-el-almacen-en-el-disco-efimero-de-la-instancia-hasta-cerrar-r-06.md)) |
| Los hechos de la recepción: `recibida`, `encolada` | Bitácora JSON Lines con `fsync` por línea ([`bitacora.py`](../../backend/infraestructura/bitacora.py)) | `ingesta` | Igual que la imagen. **Es la fuente de verdad del estado de cada hoja** (ADR-0018) |
| El trabajo de procesar una hoja | Lista de Redis, el Key Value ([`cola.py`](../../backend/infraestructura/cola.py)) | `infraestructura` | Hasta que el worker lo toma; el Key Value gratuito no persiste ([ADR-0011](../adr/0011-consumir-la-cola-desde-la-instancia-de-la-api-con-el-key-value-gratuito.md)) |
| La marca `trabajo-visto:<id>` | Redis | `infraestructura` | 7 días, o hasta que el Key Value se reinicie ([ADR-0016](../adr/0016-acotar-la-espera-de-la-cola-y-hacer-idempotente-al-worker.md)) |
| El presupuesto del proveedor | Memoria del proceso de la API ([`presupuesto.py`](../../backend/autoria/presupuesto.py)) | `autoria` | Hasta el reinicio ([ADR-0015](../adr/0015-limitar-el-gasto-del-proveedor-de-llm-con-un-presupuesto-en-la-api.md)) |
| Las propuestas guardadas | Memoria del proceso de la API ([`cache.py`](../../backend/autoria/cache.py)) | `autoria` | 24 horas, o hasta el reinicio (ADR-0019) |
| El reporte de la carga | El navegador del docente | — | Es una copia del momento de la respuesta; no se actualiza |

## 2. Tabla operación → garantía de consistencia

Cada fila dice qué garantiza la operación, qué **no** garantiza (que es lo que un lector necesita
para no suponer de más), dónde se sostiene en el código y qué prueba se pone en rojo si se rompe.

| ID | Operación | Garantía que da | Lo que no garantiza | Dónde se sostiene | Prueba |
|---|---|---|---|---|---|
| **C-01** | **Cargar un lote** (`POST /examenes/{id}/hojas`) | **Lo confirmado está escrito.** Toda hoja que la respuesta da por aceptada ya está en el almacén y en la bitácora, con `fsync`, antes de que salga la respuesta. **Atómica por hoja, no por lote**: cada archivo termina aceptado o rechazado con motivo, y la suma es el lote entero (EC-07) | Que el lote entre completo o no entre: puede quedar en parte aceptado, en parte rechazado y en parte pendiente. Que sobreviva a un despliegue (disco efímero) | [`recepcion.py:190`](../../backend/ingesta/recepcion.py) (guardar), `:209` (registrar), [`bitacora.py:82`](../../backend/infraestructura/bitacora.py) (`fsync`) | `test_ningun_archivo_del_lote_desaparece` ([`test_recepcion.py`](../../backend/tests/test_recepcion.py)) · `test_la_suma_reportada_es_el_lote_completo_caiga_donde_caiga` ([`test_durabilidad_recepcion.py`](../../backend/tests/test_durabilidad_recepcion.py)) |
| **C-02** | **Llevar la hoja de la bitácora a la cola** | **Orden fijo y nunca al revés:** almacenar → registrar → publicar → confirmar. Puede haber hoja registrada sin trabajo en la cola (`pendiente_de_encolar`), pero nunca trabajo sin hoja registrada. **Consistencia eventual con recuperación hacia adelante**: lo pendiente se termina después desde la bitácora, con el mismo `trabajo_id` | Que la cola alcance a la bitácora sola: el reintento automático es de A-02. Que la confirmación en la bitácora llegue siempre (si falla, la hoja queda encolada y la bitácora la sigue dando por pendiente: el reintento sería un duplicado, y lo absorbe C-03) | [`recepcion.py:209-245`](../../backend/ingesta/recepcion.py) ([ADR-0006](../adr/0006-registrar-la-recepcion-en-una-bitacora-antes-de-encolar.md)) | `test_la_hoja_que_no_se_encolo_queda_pendiente_en_la_bitacora` · `test_ninguna_hoja_del_lote_queda_sin_reportar_si_la_cola_se_cae` ([`test_durabilidad_recepcion.py`](../../backend/tests/test_durabilidad_recepcion.py)) |
| **C-03** | **Procesar un trabajo** (worker) | **Como mucho una vez por `trabajo_id`** durante 7 días: la marca es un `SET NX` atómico, así que entre dos entregas o dos workers solo uno procesa | **Al menos una vez no**: si el worker muere después del `BLPOP`, el trabajo se pierde (MF-06, R-22). Si Redis falla al comprobar, se procesa igual (se prefiere un duplicado a una hoja perdida) | [`cola.py:126`](../../backend/infraestructura/cola.py) (`primera_entrega`), [`worker/main.py`](../../backend/worker/main.py) | `test_el_trabajo_que_llega_dos_veces_se_procesa_una_sola_vez` ([`test_modos_de_fallo.py`](../../backend/tests/test_modos_de_fallo.py)) |
| **C-04** | **Saber el estado de una hoja** | **La bitácora es la verdad** (ADR-0018): leerla devuelve todo lo que se escribió antes, porque cada línea se escribe completa y con `fsync` en un solo proceso. La copia `estado` del reporte es una instantánea del momento de la respuesta | Que el reporte que el docente tiene abierto se actualice. Que haya un solo escritor si la API se replica (V-4). Que leer siga siendo barato: hoy es releer todo el archivo (R-26) | [`bitacora.py:106`](../../backend/infraestructura/bitacora.py) (`pendientes`), [`modelo.py`](../../backend/infraestructura/modelo.py) (`HojaAceptada`) | `test_la_bitacora_en_disco_conserva_la_identidad_de_la_hoja_pendiente` ([`test_identidad_de_la_hoja.py`](../../backend/tests/test_identidad_de_la_hoja.py)) · `test_la_bitacora_en_disco_se_relee_desde_otro_objeto` |
| **C-05** | **Dar identidad a una hoja y a su trabajo** | **Única sin coordinación y estable**: `hoja_id` y `trabajo_id` son UUID distintos, acuñados una vez; el `hoja_id` es el mismo en el reporte, la bitácora y el trabajo de la cola. Una línea vieja de la bitácora conserva su identidad | Que la misma hoja subida dos veces se reconozca: son dos hojas (R-24) | [`recepcion.py:199`](../../backend/ingesta/recepcion.py), [`bitacora.py:133`](../../backend/infraestructura/bitacora.py) | Las seis de [`test_identidad_de_la_hoja.py`](../../backend/tests/test_identidad_de_la_hoja.py) |
| **C-06** | **Reservar un cupo** del presupuesto | **Linealizable dentro del proceso**: la reserva y la cuenta ocurren bajo un candado, así que ningún hilo pasa del límite | Nada entre instancias (cada una tendría el suyo, R-18). Que sobreviva a un reinicio | [`presupuesto.py:122`](../../backend/autoria/presupuesto.py) | `test_dos_hilos_a_la_vez_no_pasan_del_limite` ([`test_presupuesto.py`](../../backend/tests/test_presupuesto.py)) |
| **C-07** | **Proponer distractores** (lee la caché) | **Lectura acotada:** lo que sale de la caché tiene como mucho 24 horas, es del modelo y las instrucciones vigentes (van en la clave) y pasa por la regla vigente (se guarda sin filtrar). La respuesta dice `desde_la_cache` | Que dos instancias vean lo mismo. Que dos pedidos simultáneos de una pregunta nueva salgan una sola vez al proveedor (no se coordinan) | [`cache.py:124`](../../backend/autoria/cache.py) (`leer`), `:186` (`proponer`), [`api/main.py:348`](../../backend/api/main.py) | `test_la_misma_pregunta_sale_de_la_cache_sin_llamar_al_proveedor_ni_gastar_cupo` · `test_la_regla_corre_en_cada_lectura_y_no_queda_congelada_en_lo_guardado` ([`test_cache_de_propuestas.py`](../../backend/tests/test_cache_de_propuestas.py)) |
| **C-08** | **Pedir otras propuestas** (escribe la caché) | **Lee lo que escribiste**, dentro del proceso: la respuesta nueva reemplaza la guardada, y la siguiente solicitud de esa pregunta la recibe | Lo mismo en otra instancia | [`cache.py:141`](../../backend/autoria/cache.py) (`guardar`) | `test_pedir_otras_no_lee_la_cache_y_reemplaza_lo_guardado` |
| **C-09** | **Consultar las métricas** (`GET /metricas`) | **Instantánea coherente de cada componente**: el presupuesto y la caché se leen cada uno bajo su candado. Contadores que solo crecen hasta el reinicio | Que las dos instantáneas sean del mismo instante | [`api/main.py:403`](../../backend/api/main.py) | `test_las_metricas_publican_lo_usado_y_lo_cortado` · `test_las_metricas_publican_los_aciertos_y_los_fallos` |
| **C-10** | **Guardar la detección y la nota** (A-02 y A-03, sin código) | **Prevista** por ADR-0018: se escriben por `hoja_id`, con una nota vigente por hoja, en una transacción local de la base que elija R-06. El docente lee lo que escribió después de una revisión manual; el panel puede ir detrás, como proyección | Todo, hasta que exista: es la promesa que el código de A-02 y A-03 tiene que cumplir | — | — |

**Lo que la tabla no tiene, a propósito: transacciones entre sistemas.** No hay ninguna operación
que tenga que escribir en dos sistemas a la vez o en ninguno. La recepción escribe en el disco y
después publica en la cola, y si lo segundo falla no se deshace lo primero: se termina después.
Por eso no hay coordinador ni saga ([`modos-de-fallo.md`](modos-de-fallo.md#saga)).

## 3. Diseño de la caché

### Qué se guarda en caché, y qué no

Se evaluaron los datos que el sistema lee más de una vez:

| Candidato | ¿Caché? | Por qué |
|---|---|---|
| **Las propuestas del proveedor para una pregunta** | **Sí** | Es la única lectura cara: cada una gasta un cupo de 6 por minuto y unos 2,1 s (la mediana de EC-08). No envejece sola: las propuestas para la derivada de `x·sin(x)` sirven mañana igual. Y se repite: el docente vuelve a abrir la pregunta, el navegador reenvía, otro profesor arma el mismo parcial |
| El estado de una hoja | No | Es dato que el docente usa para decidir si volver a subir algo: tiene que salir de la fuente de verdad (C-04, ADR-0018). Hoy, además, ninguna ruta lo consulta |
| `GET /metricas` | No | Ya es una lectura en memoria de microsegundos |
| `GET /health` | No | Es una sonda: una respuesta guardada diría que la API vive aunque no viva |

### Cómo funciona

`GeneradorConCache` ([`autoria/cache.py`](../../backend/autoria/cache.py)) es otro adaptador del
puerto `GeneradorDeDistractores`, como el presupuesto, y va **por fuera** de él:

```
ruta /distractores → regla (filtrar_propuestas) → GeneradorConCache → GeneradorConPresupuesto → Groq
```

- **Clave:** el SHA-256 de la versión (modelo y huella de las instrucciones), el enunciado y la
  respuesta correcta con los espacios normalizados, y la cantidad.
- **Valor:** las propuestas tal como las devolvió el proveedor, sin filtrar.
- **Lectura:** si hay una entrada vigente, se devuelve sin llamar al presupuesto ni al proveedor.
- **Escritura:** después de una respuesta del proveedor con al menos una propuesta.

### Política de invalidación

| Qué la invalida | Cómo | Qué garantiza | Prueba |
|---|---|---|---|
| **Cambiar de modelo** (`LLM_MODELO`) **o de instrucciones** | Los dos van en la clave: la huella de las instrucciones es un SHA-256 de su texto (`HUELLA_DE_LAS_INSTRUCCIONES`). Lo guardado con la versión anterior deja de leerse solo | Nunca se sirve una propuesta de un modelo o un texto que ya no se usa, sin que nadie tenga que acordarse de vaciar nada | `test_cambiar_de_modelo_o_de_instrucciones_invalida_lo_guardado` · `test_las_instrucciones_entran_en_la_version_de_las_propuestas` |
| **Cambiar la regla** de qué llega al profesor | No hace falta invalidar: se guarda sin filtrar y la regla corre en cada lectura | Un arreglo de la regla (como los del 19-oct) vale desde la solicitud siguiente | `test_la_regla_corre_en_cada_lectura_y_no_queda_congelada_en_lo_guardado` |
| **El tiempo** | Vence a las 24 horas de guardada. Leerla no la renueva | Lo más viejo que puede recibir un profesor tiene un día | `test_una_entrada_vence_a_las_24_horas_y_leerla_no_la_renueva` |
| **La capacidad** | 256 entradas; con la caché llena sale la que lleva más tiempo sin leerse | La memoria está acotada: menos de 1 MB de los 512 MB de la instancia | `test_con_la_cache_llena_sale_la_que_lleva_mas_tiempo_sin_leerse` |
| **El profesor** | «Pedir otras propuestas» manda `otras: true`: no se lee la caché, se pide al proveedor y lo nuevo reemplaza lo guardado | Quien pide otras recibe otras, y desde ahí todos reciben las nuevas | `test_pedir_otras_no_lee_la_cache_y_reemplaza_lo_guardado` · en el sitio, `pauta_test.dart` |
| **Un reinicio o un despliegue** | Vive en la memoria del proceso | Nunca sobrevive a un cambio de código | — (es el comportamiento de cualquier objeto en memoria) |
| **Lo que nunca entra** | Un 503, un 429 o una respuesta sin propuestas no se guardan | Una falla momentánea no se repite durante 24 horas | `test_una_falla_del_proveedor_no_se_guarda` · `test_una_respuesta_sin_propuestas_no_se_guarda` |

### Por qué en memoria y no en Redis

Por la misma razón que el presupuesto (ADR-0015): hay una sola instancia de la API con un solo
proceso, el Key Value gratuito tampoco persiste (ADR-0011), y Redis agregaría una ida y vuelta de
red a cada solicitud, con sus tres modos de fallo de la S11. **Se revisa si la API corre en más de
una instancia:** la caché pasa a Redis con la misma clave y un `SET … EX 86400`, detrás del mismo
adaptador (R-27).

### Lo que no hace, a propósito

- **No coordina dos pedidos simultáneos de la misma pregunta nueva.** Los dos salen al proveedor y
  el segundo reemplaza al primero. Con 6 solicitudes por minuto no hay una avalancha que justifique
  la complejidad.
- **No sirve lo guardado cuando el proveedor falla.** Sería útil (las propuestas viejas son mejores
  que un 503), pero mezclaría la caché con la degradación de ADR-0013. Queda como mejora posible.
- **El sitio no muestra todavía si las propuestas vienen de la caché.** La API lo dice en
  `desde_la_cache`; mostrarlo es un cambio de pantalla.

### Cómo se observa

`GET /metricas` publica `cache_de_distractores`: capacidad, vigencia, entradas, aciertos, fallos,
guardadas, vencidas y expulsadas. La proporción de aciertos es lo que dice si la caché vale lo que
cuesta. **No se ha medido todavía en el entorno desplegado**, porque necesita tráfico real de
profesores; lo medido es que un acierto no llama al proveedor ni gasta cupo, en las pruebas.

## 4. La decisión de datos más costosa de revertir

Es la **identidad de la hoja y dónde vive su estado**, y la toma
[ADR-0018](../adr/0018-dar-a-la-hoja-una-identidad-propia-y-derivar-su-estado-de-la-bitacora.md).
El ADR recorre las demás decisiones de datos del sistema con lo que costaría revertir cada una: el
presupuesto y la caché viven en memoria y se revierten con un reinicio; las marcas de Redis vencen
solas; el formato de la bitácora y el medio de persistencia están detrás de un puerto. La identidad
no: todo lo que A-02 y A-03 guarden va a colgar de ella, el contrato la publica, y su costo crece
con cada registro. Hasta esta entrega era implícita (el `trabajo_id` hacía de identidad de la hoja)
y tenía un defecto: no se podía volver a procesar una hoja sin chocar con la idempotencia de
ADR-0016. Se separa ahora, cuando revertirla todavía es quitar un campo.

## 5. Qué tiene prueba y qué solo está descrito

**Con prueba que se pone en rojo si se rompe:** C-01 a C-09. Las de esta entrega se validaron
provocando la falla: las seis de `test_identidad_de_la_hoja.py` con cuatro mutaciones y las trece
de `test_cache_de_propuestas.py` con seis, una por regla de invalidación; los dos docstrings las
enumeran.

**Solo descrito:**

- **C-10**, la detección y la nota: no tienen código. ADR-0018 fija la promesa que deben cumplir.
- **La exclusión mutua de la caché entre hilos**: la prueba de los hilos comprueba que las cuentas
  cuadran, pero siguió en verde sin el candado en 10 de 10 corridas, y su docstring lo dice. El
  candado está; su prueba no.
- **El efecto de la caché en producción**: se observa en `GET /metricas`, sin una medición todavía.

## 6. Cómo se reproduce

Desde `backend/`, con el entorno del proyecto:

```
pytest -v tests/test_identidad_de_la_hoja.py tests/test_cache_de_propuestas.py
```

Ninguna de las dos necesita Redis ni sale a la red. Para ver la caché en el entorno desplegado:
pedir dos veces la misma pregunta desde la pantalla Pauta y distractores y consultar
https://quantia-utb-api.onrender.com/metricas: `aciertos` sube en uno y `enviadas_desde_el_arranque`
del presupuesto no.
