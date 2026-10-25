# Taller de mensajería: la cola de trabajos

El taller pide elegir una operación real con desacoplamiento temporal, reintento o procesamiento en
segundo plano, y demostrar sobre ella siete cosas: el contrato del mensaje, la garantía de entrega,
el manejo de duplicados, la política de reintentos, pruebas de un duplicado y de un fallo
recuperable, cómo seguir un mensaje del productor al consumidor y un ADR frente a la alternativa
síncrona. Este documento las recorre, con la evidencia de una ejecución real y los límites del
experimento.

- **Decisión:** [ADR-0020](../adr/0020-entregar-los-trabajos-al-menos-una-vez-con-reintentos-y-lista-de-fallidos.md).
- **Contrato:** [`docs/contrato/trabajo-v1.schema.json`](../contrato/trabajo-v1.schema.json).
- **Pruebas:** [`test_mensajeria.py`](../../backend/tests/test_mensajeria.py) (15) y las del worker en
  [`test_modos_de_fallo.py`](../../backend/tests/test_modos_de_fallo.py).
- **Ejecución:** la carpeta [`taller-mensajeria/`](taller-mensajeria/), con el script que la produjo.
- **Fecha:** 2026-10-25.

## La operación

Cuando el docente sube un lote, la API guarda cada hoja, la registra en la bitácora y **publica un
mensaje en la cola de Redis** por cada una; el worker, otro proceso, **lo consume después**
([ADR-0002](../adr/0002-procesar-calificacion-de-forma-asincrona.md), [ADR-0006](../adr/0006-registrar-la-recepcion-en-una-bitacora-antes-de-encolar.md)).
La API confirma el lote sin esperar a que se procese ninguna hoja: es desacoplamiento temporal y
procesamiento en segundo plano en el sistema de verdad, desplegado en Render desde la S8. Por eso no
hay prototipo aparte.

| Papel | Quién | Dónde |
|---|---|---|
| Productor | `ingesta.recibir_lote`, en la API | [`recepcion.py`](../../backend/ingesta/recepcion.py) y `cola.publicar` |
| Canal | Una lista de Redis, `procesamiento`, en el Key Value de Render | [`cola.py`](../../backend/infraestructura/cola.py) |
| Consumidor | El worker, segundo proceso de la misma instancia | [`worker/main.py`](../../backend/worker/main.py) y [`consumo.py`](../../backend/infraestructura/consumo.py) |

## 1. Contrato del mensaje y criterio de compatibilidad

El mensaje es un `Trabajo` en JSON, **versión 1**. Su forma está declarada en código
(`ESQUEMA_DEL_TRABAJO`, en `cola.py`) y publicada como JSON Schema en
[`trabajo-v1.schema.json`](../contrato/trabajo-v1.schema.json), que genera
`python -m herramientas.exportar_contrato`, igual que el OpenAPI. Una prueba falla si el archivo y
el código se separan.

| Campo | Tipo | Qué es |
|---|---|---|
| `id` | texto (UUID) | La identidad del encargo, el `trabajo_id`. La conserva cada reintento |
| `version` | `1` | La versión del contrato |
| `tipo` | `"hoja_recibida"` | Qué pide el mensaje |
| `emitido_en` | fecha y hora UTC | Cuándo lo acuñó el productor; con él se mide la espera en la cola |
| `intento` | entero ≥ 1 | 1 al publicarse; lo sube cada reintento |
| `payload.hoja_id` | texto | La identidad de la hoja ([ADR-0018](../adr/0018-dar-a-la-hoja-una-identidad-propia-y-derivar-su-estado-de-la-bitacora.md)) |
| `payload.examen_id`, `payload.nombre_archivo` | texto | De qué examen es y cómo se llamaba |
| `payload.referencia` | texto | Dónde está la imagen en el almacén, opaca para el consumidor |

**Criterio de compatibilidad:**

- **Agregar** un campo opcional no cambia la versión. Quien lee es tolerante: ignora lo que no
  conoce (`leer_trabajo`).
- **Quitar, renombrar o cambiar el tipo o el significado** de un campo obligatorio es una versión
  nueva, en un archivo nuevo (`trabajo-v2.schema.json`). Quien lee rechaza las versiones que no
  conoce, y ese mensaje va a la lista de fallidos sin reintentarse: el mismo texto daría el mismo
  error.
- **Los mensajes anteriores al contrato** (sin `version`, todavía en la cola al desplegar) se leen
  como versión 1; si no traen `hoja_id`, su `id` hace de hoja, la misma regla de la bitácora.
- **Orden de despliegue:** la API y el worker van en la misma imagen y se despliegan juntos. Si se
  separan, primero el consumidor.

## 2. Garantía de entrega: al menos una vez

**Antes**, el worker retiraba el mensaje con `BLPOP`: si moría antes de terminarlo, el mensaje ya no
estaba en la cola y se perdía (MF-06, R-22). Era **como mucho una vez**.

**Ahora** el worker lo **mueve** a `procesamiento:en-curso` con `BLMOVE`, en un solo paso atómico, y
solo sale de ahí con el **acuse** (`confirmar`), con un reintento programado o hacia la lista de
fallidos. Si el worker muere en medio, el mensaje sigue en curso, y al volver a arrancar
`recuperar_en_curso` lo devuelve a la cola. Es **al menos una vez**.

**Consecuencias asumidas:**

- **Un mensaje puede llegar dos veces**: si el worker muere después de procesar y antes del acuse,
  o si alguien lo vuelve a publicar. Lo absorbe la idempotencia (sección 3).
- **La recuperación supone un solo consumidor** (R-29): devuelve a la cola todo lo que está en
  curso, lo que con dos workers le quitaría al otro lo que está procesando. Antes de un segundo
  worker, esto pasa a Redis Streams.
- **Todo vive en un Redis sin persistencia** (R-28): si el Key Value se reinicia, se pierden la cola,
  lo que está en curso, los reintentos y los fallidos.
- **Exactamente una vez no se ofrece**: exigiría que procesar y confirmar fueran una sola transacción
  con la cola, y entre Redis y un disco no la hay.

## 3. Duplicados: idempotencia por `trabajo_id`

Antes de procesar, el worker pregunta si el trabajo ya se procesó (`ya_procesado`). Al terminar lo
marca (`marcar_procesado`, `trabajo-visto:<id>` por 7 días) y **solo después** confirma. El orden es
lo que importa:

| Si el worker muere… | Con la marca **antes** de procesar (ADR-0016) | Con la marca **después** (ahora) |
|---|---|---|
| …antes de procesar | El mensaje vuelve, encuentra la marca y se descarta: **la hoja se pierde** | Vuelve y se procesa |
| …después de procesar, antes del acuse | Vuelve y se descarta (bien) | Vuelve, encuentra la marca y solo se confirma |

Dos workers con el mismo mensaje a la vez podrían procesarlo los dos; con uno solo no pasa, y cuando
A-03 guarde notas lo hará por `hoja_id`, así que procesar dos veces escribe lo mismo.

## 4. Reintentos, espera creciente y lista de fallidos

| Situación | Qué pasa |
|---|---|
| La imagen no se puede leer (`OSError`): fallo **recuperable** | Se reintenta hasta completar **4 intentos**, con esperas de **5, 10 y 20 s** más una variación al azar de hasta el 20 %, para que muchos fallos a la vez no vuelvan juntos |
| Se agotaron los intentos | Va a `procesamiento:fallidos` con el mensaje original, el motivo y los intentos |
| El mensaje no cumple el contrato, o su versión no se conoce: fallo **permanente** | Va a fallidos en el primer intento, sin esperar |
| La referencia apunta fuera del almacén | Permanente: a fallidos |
| Redis falla | El worker registra `fallo_de_la_cola`, espera 5 s y devuelve a la cola lo que tenía en curso |

**La espera no se hace dentro del worker.** El mensaje entra a `procesamiento:reintentos`, un
conjunto ordenado por la hora de su próximo intento, y el worker lo devuelve a la cola cuando le
toca. Así la espera no bloquea a los demás mensajes ni se pierde si el worker muere. Cada movimiento
entre listas es una transacción de Redis.

**La lista de fallidos no se vacía sola**: lo que llega ahí no se arregla insistiendo.
`python -m herramientas.cola_de_fallidos --ver` la muestra, y `--reencolar` devuelve a la cola, con
el intento en 1, los que cumplen el contrato, cuando alguien corrigió la causa.

## 5. Pruebas automatizadas

En [`test_mensajeria.py`](../../backend/tests/test_mensajeria.py), contra el Redis del CI:

| Lo que prueba | Prueba |
|---|---|
| **Un duplicado** | `test_si_murio_despues_de_procesar_la_entrega_que_vuelve_no_se_procesa_otra_vez`, y el mismo mensaje publicado dos veces en `test_el_trabajo_que_llega_dos_veces_se_procesa_una_sola_vez` ([`test_modos_de_fallo.py`](../../backend/tests/test_modos_de_fallo.py)) |
| **Un fallo recuperable** | `test_un_fallo_recuperable_se_reintenta_con_espera_y_se_procesa_al_recuperarse`: la imagen falla dos veces, espera 5 y 10 s con un reloj falso, y se procesa al tercer intento con el mismo `trabajo_id` |
| Al menos una vez | `test_un_trabajo_que_quedo_en_curso_vuelve_a_la_cola_al_arrancar_y_se_procesa` |
| Lista de fallidos | `test_un_fallo_que_no_se_recupera_termina_en_fallidos_con_el_motivo`, `test_lo_que_esta_en_fallidos_se_puede_reencolar_cuando_se_corrige_la_causa`, `test_una_referencia_fuera_del_almacen_no_se_reintenta` |
| Contrato y compatibilidad | `test_el_contrato_versionado_del_mensaje_es_el_que_genera_el_codigo`, `test_todo_mensaje_que_publica_la_recepcion_cumple_el_contrato`, `test_quien_lee_ignora_lo_que_no_conoce_y_lee_los_mensajes_anteriores_al_contrato`, y los tres casos de `test_un_mensaje_fuera_del_contrato_va_a_fallidos_sin_reintentarse` |
| Seguimiento | `test_un_mensaje_se_sigue_de_la_api_al_worker_con_el_mismo_trabajo_y_la_misma_hoja` |

**Se validaron provocando la falla**, una mutación a la vez, y el docstring del archivo dice cuál
pone en rojo cada una. La más reveladora: con la marca antes de procesar, como estaba en ADR-0016,
fallan cuatro, entre ellas la del fallo recuperable, porque el reintento se descarta como repetido y
la hoja nunca se procesa.

## 6. Seguir un mensaje del productor al consumidor

Cada evento del registro JSON lleva el mismo `trabajo` y la misma `hoja`, desde la API hasta el
worker:

| Evento | Quién | Datos |
|---|---|---|
| `trabajo_publicado` | API (`ingesta`) | `trabajo`, `hoja`, `examen`, `cola` |
| `trabajo_tomado` | worker | `intento` y **`espera_en_cola_ms`**: cuánto pasó desde que el productor lo acuñó |
| `reintento_programado` | worker | `siguiente_intento`, `espera_s`, `motivo` |
| `trabajo_repetido` | worker | — |
| `trabajo_a_fallidos` | worker | `motivo` |
| `hoja_recibida` | worker | `bytes`, `referencia`: el mensaje se procesó |
| `trabajos_recuperados` | worker | `cantidad` devuelta a la cola al arrancar |

`python -m herramientas.seguir_trabajo registro.jsonl --trabajo <id>` muestra el recorrido de un
mensaje y su resumen (estado final, intentos y tiempo de punta a punta); `--todos` lo hace para
cada mensaje del registro.

## 7. Evidencia de ejecución

La API (uvicorn), el worker y Redis de verdad, en local, con
[`ensayo.sh`](taller-mensajeria/ensayo.sh). El script sube por HTTP un lote de tres hojas y, antes de
arrancar el worker, provoca los cuatro casos: publica otra vez el mensaje de la hoja 1 (duplicado);
mueve un mensaje de la hoja 1 a la lista en curso, como si un worker anterior lo hubiera tomado y
muerto; aparta la imagen de la hoja 2 durante 7 s (fallo recuperable); y borra la de la hoja 3, como
haría un despliegue en Render (fallo que no se recupera).

Archivos de la ejecución (las rutas de la máquina se reemplazaron por `<almacén>`):
[`respuesta-de-la-carga.json`](taller-mensajeria/respuesta-de-la-carga.json),
[`pasos.txt`](taller-mensajeria/pasos.txt) (el estado de las cuatro listas en cada paso),
[`registro.jsonl`](taller-mensajeria/registro.jsonl) (las líneas JSON de la API y del worker) y
[`seguimiento.json`](taller-mensajeria/seguimiento.json) (la salida de `seguir_trabajo --todos`).

| Hoja | Lo provocado | Recorrido en el registro | Resultado |
|---|---|---|---|
| 1 | Un worker caído la dejó en curso, y además se publicó dos veces | `trabajos_recuperados` (1) → `trabajo_tomado` → `hoja_recibida` → `trabajo_tomado` → `trabajo_repetido` | Procesada **una vez**; la copia, confirmada como repetida |
| 2 | La imagen falta los primeros 7 s | tomado → reintento (5,5 s) → tomado → reintento (10,9 s) → tomado → `hoja_recibida` | Procesada en el **intento 3**, 17,8 s después de publicarse |
| 3 | La imagen se borró | tomado → reintento (5,2 s) → reintento (11,3 s) → reintento (23,7 s) → tomado → `trabajo_a_fallidos` | En **fallidos** al intento 4, a los 43 s, con `FileNotFoundError` como motivo |

Al final, `pasos.txt` registra `{"pendientes": 0, "en_curso": 0, "esperando_reintento": 0,
"fallidos": 1}`: nada quedó a medias y lo único sin procesar está a la vista, con su motivo.

## 8. Límites del experimento

- **Es una ejecución en local, no en Render.** Los mismos procesos y el mismo código, con Redis 7 en
  la máquina; el Key Value de Render es compatible, pero el ensayo no se corrió contra él.
- **El procesamiento es abrir la imagen y registrarla.** El OMR (A-02) no existe; los fallos
  recuperables que se probaron son de lectura del almacén, y los de un OMR real pueden ser otros.
- **Un solo worker.** La recuperación de lo que quedó en curso lo supone (R-29); con dos, no vale.
- **La caída del worker se simuló** moviendo un mensaje a la lista en curso antes de arrancarlo, no
  matando el proceso en el instante exacto. Las pruebas cubren los dos momentos que importan (antes y
  después de procesar) con el código real.
- **Redis sin persistencia** (R-28): un reinicio del Key Value se lleva las cuatro listas y las
  marcas. El experimento no lo cubre porque la decisión no lo resuelve.
- **Las esperas de 5, 10 y 20 s no se calibraron** con fallos reales: son un punto de partida. Y
  la cola de fallidos solo se observa con la herramienta; no hay alerta.
