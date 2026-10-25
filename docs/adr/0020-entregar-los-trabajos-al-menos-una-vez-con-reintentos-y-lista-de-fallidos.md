# 0020 · Entregar los trabajos al menos una vez, con reintentos y lista de fallidos

- **Estado:** aceptado
- **Fecha:** 2026-10-25
- **Decide:** Josué Ortega De Arco, María Restrepo Licona, Sebastián Cañas Plata, Susana Rosales Castellar
- **Escenarios de calidad relacionados:** [EC-07](../arc42/arc42-template-ES.md#ec-07) (confirmación del lote), [EC-03](../arc42/arc42-template-ES.md#ec-03) y [EC-04](../arc42/arc42-template-ES.md#ec-04) (calificar una hoja y un lote)
- **Origen:** el taller de mensajería, sobre la operación real del sistema con desacoplamiento temporal y procesamiento en segundo plano: cada hoja aceptada viaja como un mensaje de la API al worker por la cola de Redis. Cierra R-22 y R-23, que la S11 y la entrega de consistencia dejaron declarados
- **Restricciones que lo acotan:** RNF-16 (US$0 y sin tarjeta), el Key Value gratuito sin persistencia ([ADR-0011](0011-consumir-la-cola-desde-la-instancia-de-la-api-con-el-key-value-gratuito.md)), un solo worker ([ADR-0017](0017-no-extraer-ningun-modulo-del-monolito-todavia.md)), las hojas en el disco efímero ([ADR-0012](0012-mantener-el-almacen-en-el-disco-efimero-de-la-instancia-hasta-cerrar-r-06.md))
- **Relación con otros ADR:** confirma la decisión asíncrona de [ADR-0002](0002-procesar-calificacion-de-forma-asincrona.md) frente a la alternativa síncrona, con lo medido desde entonces; precisa [ADR-0016](0016-acotar-la-espera-de-la-cola-y-hacer-idempotente-al-worker.md) (la marca pasa a después de procesar, como su punto 5 preveía) sin reemplazarlo

**La decisión, en una frase:** el mensaje de la cola tiene un contrato versionado; el worker lo toma
moviéndolo a una lista en curso y lo confirma al terminar, con lo que la entrega pasa a ser al menos
una vez; los duplicados que eso produce los absorbe una marca de idempotencia puesta después de
procesar; un fallo recuperable se reintenta con espera creciente hasta cuatro intentos, y lo que no
se puede procesar va a una lista de fallidos con su motivo.

---

## Contexto

**La operación.** Cuando el docente sube un lote, la API almacena cada hoja, la registra en la
bitácora y publica un trabajo en la cola (ADR-0006); el worker lo toma después, en otro proceso. Es
desacoplamiento temporal real: la API confirma el lote sin esperar a que se procese ninguna hoja,
y el worker procesa a su ritmo. No hace falta un prototipo aparte.

**Lo que no estaba resuelto:**

- **El mensaje no tenía contrato.** Era un `id` y un `payload` sin forma declarada ni versión. Un
  cambio en lo que publica la API podía romper al worker sin que ninguna prueba lo notara.
- **La entrega era como mucho una vez.** El worker retiraba el trabajo con `BLPOP`; si moría
  antes de terminarlo, el trabajo ya no estaba en la cola y la bitácora lo daba por encolado (MF-06,
  R-22).
- **La marca de idempotencia iba antes de procesar** (ADR-0016). Con cualquier forma de volver a
  entregar un trabajo no terminado, la segunda entrega se descartaba como repetida (R-23).
- **No había reintentos ni lista de fallidos.** Si la imagen no estaba, el worker daba la hoja por
  recibida igual, porque no la abría. Es lo que pasaría con los trabajos pendientes después de un
  despliegue en Render, que borra el disco.
- **No se podía seguir un mensaje** de la API al worker: el productor no registraba nada por hoja.

## Alternativas consideradas

### 1. Síncrono o asíncrono

| Opción | A favor | En contra | |
|---|---|---|---|
| **Síncrona: la API procesa cada hoja dentro de la petición de carga** | Sin cola, sin worker, sin contrato de mensaje ni duplicados: el docente recibe el resultado en la misma respuesta, y un error se ve en el acto | EC-03 da hasta 5 s por hoja: un lote de 200 son 16,6 minutos dentro de una petición, contra los 10 s de EC-07 (el cálculo de ADR-0002). Hoy el lote de 200 confirma en menos de 2 s (EC-07) porque no procesa nada. Con 0,1 CPU, una carga ocuparía el único proceso de la API todo ese tiempo (lo que R-21 ya mostró con solo escribir en disco). Y si la petición se corta, no se sabe qué hojas se procesaron | Descartada |
| **Síncrona por hoja, desde el sitio**: el navegador sube y pide procesar una hoja a la vez | Sin cola | Lleva el lote al navegador: si el docente cierra la pestaña, el lote queda a medias, y nada lo retoma. Es la cola, pero en el lugar menos confiable | Descartada |
| **Asíncrona, con la cola de ADR-0002** | La carga confirma en segundos; el worker procesa a su ritmo; lo que falla se reintenta sin el docente | Exige lo que este ADR decide: contrato, garantía de entrega, duplicados, reintentos y seguimiento | **Elegida** |

### 2. Qué garantía de entrega

| Opción | | Por qué |
|---|---|---|
| Como mucho una vez (`BLPOP`, lo de antes) | Descartada | Pierde la hoja si el worker muere a mitad, sin que nada lo diga |
| **Al menos una vez, con idempotencia** | **Elegida** | Ninguna hoja se pierde por una caída del worker; el duplicado que produce lo absorbe la marca |
| Exactamente una vez | Descartada | Exige que el procesamiento y el acuse sean una sola transacción con la cola. Con Redis y un disco no la hay; lo que se consigue es «al menos una vez» más un efecto idempotente, que es lo elegido |

### 3. Con qué

| Opción | A favor | En contra | |
|---|---|---|---|
| **Listas de Redis con `BLMOVE` a una lista en curso, un conjunto ordenado para los reintentos y una lista de fallidos** | El patrón de «cola fiable» de Redis, sobre el mismo Key Value; no cambia lo que publica la API ni la herramienta de EC-07; cada movimiento es atómico | La recuperación de lo que quedó en curso supone un solo consumidor (R-29) | **Elegida** |
| Redis Streams con grupos de consumidores, `XACK` y `XAUTOCLAIM` | Acuse por consumidor y reclamo de lo abandonado, con varios workers | Cambia la estructura de la cola, lo que publica la API y la herramienta de EC-07, para resolver un problema (varios workers) que ADR-0017 decidió no tener todavía | Prevista si hay más de un worker |
| RabbitMQ, Kafka o un servicio administrado | Acuse, reintentos y cola de mensajes muertos de serie | Un servicio más: no cabe en las 750 h de Render ni en RNF-16, y ADR-0017 decidió no agregar piezas sin un dato que lo pida | Descartada |
| Reintentar con un `sleep` dentro del worker | Lo más simple | Bloquea al worker mientras espera, y si muere durante la espera el trabajo se pierde | Descartada |

## Decisión

1. **El contrato del mensaje es la versión 1** ([`trabajo-v1.schema.json`](../contrato/trabajo-v1.schema.json),
   generado desde [`cola.py`](../../backend/infraestructura/cola.py)): `id` (el `trabajo_id`),
   `version`, `tipo`, `emitido_en`, `intento` y el `payload` con `hoja_id`, `examen_id`, `referencia`
   y `nombre_archivo`.
2. **Criterio de compatibilidad.** Agregar un campo opcional no cambia la versión, y quien lee
   ignora lo que no conoce. Quitar, renombrar o cambiar el tipo de un campo obligatorio es una
   versión nueva, en un archivo nuevo. Quien lee rechaza las versiones que no conoce, y ese mensaje
   va a fallidos sin reintentarse. Un mensaje sin versión (anterior al contrato) se lee como la 1.
   Como la API y el worker se despliegan juntos, en la misma imagen, una versión nueva se
   despliega con su consumidor; si algún día se separan, primero el consumidor.
3. **Al menos una vez.** `tomar` mueve el trabajo a `<cola>:en-curso` con `BLMOVE`; sale de ahí con
   el acuse (`confirmar`), con un reintento programado o hacia fallidos, siempre en una operación
   atómica. Al arrancar, y después de un fallo de Redis, el worker devuelve a la cola lo que quedó
   en curso.
4. **Duplicados: idempotencia por `trabajo_id`, con la marca después de procesar.** Antes de
   procesar se pregunta si ya se procesó (`ya_procesado`); al terminar se marca (`marcar_procesado`,
   7 días) y, solo después, se confirma. Si el worker muere entre la marca y el acuse, la entrega
   que vuelve se confirma sin procesarse. Cuando A-03 guarde notas, lo hará por `hoja_id`
   (ADR-0018), con lo que también un procesamiento repetido escribe lo mismo.
5. **Reintentos.** Un fallo recuperable (la imagen no se puede leer) se reintenta hasta completar
   cuatro intentos, con esperas de 5, 10 y 20 s, más una variación al azar de hasta el 20 %. La
   espera vive en `<cola>:reintentos`, un conjunto ordenado por la hora del próximo intento, y no en
   el worker. El reintento conserva el `trabajo_id` y sube `intento`.
6. **Lista de fallidos.** Va a `<cola>:fallidos`, con el mensaje original, el motivo y los intentos:
   lo que agotó los intentos, lo que no cumple el contrato y una referencia que queda fuera del
   almacén. No se vacía sola; `herramientas/cola_de_fallidos.py` la muestra y reencola, con el
   intento en 1, los que cumplen el contrato cuando alguien corrigió la causa.
7. **Seguimiento.** `ingesta` registra `trabajo_publicado`, y el worker `trabajo_tomado` (con
   `espera_en_cola_ms`), `reintento_programado`, `trabajo_repetido`, `trabajo_a_fallidos` y
   `hoja_recibida`, todos con el mismo `trabajo` y la misma `hoja`. `herramientas/seguir_trabajo.py`
   arma el recorrido de un mensaje desde el registro.

**Por qué no reemplaza a ADR-0016.** Las esperas de la cola, los reintentos ocultos apagados y la
idempotencia por `trabajo_id` siguen. Lo que cambia es dónde va la marca, que el punto 5 de 0016 ya
decía que tenía que moverse cuando volver a entregar un trabajo fuera posible.

## Consecuencias

### Positivas

- **Ninguna hoja se pierde porque el worker muera a mitad** (cierra R-22), y la marca ya no descarta
  un trabajo que no se terminó (cierra R-23).
- **Lo que no se puede procesar se ve**: en la lista de fallidos, con el motivo, en vez de darse por
  recibido.
- **Un mensaje se sigue de punta a punta** con su `trabajo_id`.
- **La API no cambia**: lo que publica, la herramienta de EC-07 y la confirmación del lote siguen
  igual; el contrato solo le agrega campos al mensaje.

### Negativas y consecuencias asumidas

- **Un trabajo puede procesarse dos veces** si dos workers lo toman a la vez, o si el worker muere
  después de procesar y Redis pierde la marca. Es el precio de «al menos una vez»; lo absorbe que el
  procesamiento escriba por `hoja_id`.
- **La recuperación supone un solo consumidor** (R-29): con dos workers, uno devolvería a la cola lo
  que el otro está procesando. Antes de agregar un segundo worker, esto pasa a Redis Streams.
- **Todo vive en un Redis que no persiste** (R-28): un reinicio del Key Value se lleva la cola, lo
  que está en curso, los reintentos y los fallidos. La bitácora sigue diciendo «encolada» para esas
  hojas, y nada las reintenta.
- **El worker ahora abre cada imagen.** Antes solo registraba; ahora lee hasta 20 MB por hoja. Es lo
  que A-02 va a necesitar de todos modos.
- **Un fallo que dura más de unos 35 s termina en fallidos** y necesita a una persona. Se prefiere a
  reintentar para siempre.

## Reversión

Volver a `desencolar` en el worker, que se conserva, y dejar de llamar a `recuperar_en_curso`: el
contrato y las listas nuevas quedan sin uso y no estorban. La marca volvería a ir antes de procesar.

## Qué dato haría revisar esta decisión

- **Un segundo worker** (si EC-04 lo pide, ADR-0017): Redis Streams con `XAUTOCLAIM`.
- **Que R-06 elija un almacén persistente para la cola** o un Redis con persistencia: R-28 se
  cierra, y la vigencia de las marcas se revisa contra la retención.
- **Que la lista de fallidos crezca sin que nadie la mire**: una alerta, o un evento en
  `GET /metricas`.
- **Que los fallos recuperables reales duren más de 35 s** (por ejemplo, un almacén de objetos que
  tarda en mostrar lo que se escribió): se ajustan las esperas.

## Trazabilidad

- **Contrato:** [`docs/contrato/trabajo-v1.schema.json`](../contrato/trabajo-v1.schema.json),
  generado desde [`infraestructura/cola.py`](../../backend/infraestructura/cola.py).
- **Código:** [`infraestructura/consumo.py`](../../backend/infraestructura/consumo.py),
  [`worker/main.py`](../../backend/worker/main.py),
  [`ingesta/recepcion.py`](../../backend/ingesta/recepcion.py) (`trabajo_publicado`) e
  [`infraestructura/almacen.py`](../../backend/infraestructura/almacen.py) (`leer`).
- **Pruebas:** [`test_mensajeria.py`](../../backend/tests/test_mensajeria.py), validadas con una
  mutación por propiedad, y las del worker en
  [`test_modos_de_fallo.py`](../../backend/tests/test_modos_de_fallo.py).
- **Herramientas:** [`seguir_trabajo.py`](../../backend/herramientas/seguir_trabajo.py) y
  [`cola_de_fallidos.py`](../../backend/herramientas/cola_de_fallidos.py).
- **Evidencia de ejecución:** [`taller-mensajeria.md`](../evidencia/taller-mensajeria.md).
- **Riesgos:** cierra R-22 y R-23; abre R-28 y R-29 ([arc42 §11](../arc42/arc42-template-ES.md#11-risks-and-technical-debts)).
