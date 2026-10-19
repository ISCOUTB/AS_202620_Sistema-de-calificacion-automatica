# 0016 · Acotar la espera de la cola y hacer idempotente al worker

- **Estado:** aceptado
- **Fecha:** 2026-10-18
- **Decide:** Josué Ortega De Arco, María Restrepo Licona, Sebastián Cañas Plata, Susana Rosales Castellar
- **Escenario de calidad relacionado:** [EC-07](../arc42/arc42-template-ES.md#ec-07) (confirmación fiable de recepción del lote)
- **Origen:** la tabla de modos de fallo de la S11 ([`modos-de-fallo.md`](../evidencia/modos-de-fallo.md)), modos MF-02 y MF-03
- **Restricciones que lo acotan:** RNF-16 (US$0 y sin tarjeta), el Key Value gratuito sin persistencia ([ADR-0011](0011-consumir-la-cola-desde-la-instancia-de-la-api-con-el-key-value-gratuito.md)) y R-06 abierto
- **Relación con otros ADR:** precisa [ADR-0006](0006-registrar-la-recepcion-en-una-bitacora-antes-de-encolar.md) sin reemplazarlo, y responde al dato que ADR-0006 dejó escrito para revisarlo; cumple la condición que [ADR-0011](0011-consumir-la-cola-desde-la-instancia-de-la-api-con-el-key-value-gratuito.md) puso para reconsiderar dónde corre el consumidor, que se evalúa en [ADR-0017](0017-no-extraer-ningun-modulo-del-monolito-todavia.md)

**La decisión, en una frase:** la API espera a Redis 2 s y el worker 10 s, sin que el cliente
reintente por su cuenta; y el worker procesa cada trabajo una sola vez, marcando su identificador
con un `SET NX EX` atómico en Redis antes de procesarlo.

---

## Contexto

**La integración principal.** La cola de trabajos es la columna de
[ADR-0002](0002-procesar-calificacion-de-forma-asincrona.md): toda hoja aceptada pasa por ella,
de la API (`RPUSH`) al worker (`BLPOP`). La S11 pide, para la integración principal, qué pasa
cuando el otro lado **no responde**, **responde tarde** o **responde dos veces**. El primer caso lo
resolvió [ADR-0006](0006-registrar-la-recepcion-en-una-bitacora-antes-de-encolar.md) en el primer
corte: la hoja queda en la bitácora como `pendiente_de_encolar` y el lote deja de insistir. Los
otros dos no tenían respuesta.

**Responde tarde: medido, y rompía EC-07.** Contra un servidor que acepta la conexión TCP y nunca
contesta (un Redis vivo pero lento, que es lo que se ve con la red saturada o con el Key Value
reiniciándose), con el código de `58147b8`:

| Medida | Antes (`58147b8`) | Después (esta decisión) | Umbral |
|---|---|---|---|
| Una publicación | 10,012 s | 2,004 s | — |
| Lote de 200 hojas, con la cola lenta desde la primera | **10,017 s** | 2,017 s | ≤ 10 s (EC-07) |

La causa: la API y el worker usaban el mismo cliente, con un `socket_timeout` de 10 s pensado para
el `BLPOP` del worker. Con eso solo, un lote se pasaba del techo de EC-07 antes de contar la
lectura de los archivos y la red. Es exactamente el dato que ADR-0006 escribió en «Qué dato haría
revisar esta decisión»: *que el tiempo de espera del cliente de Redis suba por encima de 9 s*.

**Responde dos veces: posible por construcción.** Un `RPUSH` cuyo tiempo de espera vence en el
cliente puede haber quedado guardado en Redis: el cliente no sabe si llegó. La hoja queda
`pendiente_de_encolar` y, cuando se reintente desde la bitácora (A-02), se publica otra vez con
**el mismo `trabajo_id`**. Lo mismo pasaría si el cliente de Redis reintentara solo. El worker
recibiría el trabajo dos veces. Hoy eso cuesta una línea de log repetida; cuando A-02 califique,
serían dos calificaciones de la misma hoja.

**Lo que acota la decisión:**
- **El worker necesita una espera larga.** Su `BLPOP` bloquea hasta 5 s en el servidor; si el
  socket se rinde antes, cada espera sin trabajos termina en error.
- **El Key Value gratuito no persiste** ([ADR-0011](0011-consumir-la-cola-desde-la-instancia-de-la-api-con-el-key-value-gratuito.md)):
  nada que se guarde en Redis sobrevive a un reinicio.
- **Sin dependencias nuevas.** `redis-py` 8.1.0 ya trae `Retry` y `NoBackoff`.

## Alternativas consideradas

### 1. Cuánto esperar a Redis

| Opción | A favor | En contra | |
|---|---|---|---|
| **Dejar 10 s para los dos** (statu quo) | Cero cambios | Medido: 10,017 s por lote con la cola lenta, fuera de EC-07 | Descartada |
| **Una espera corta para los dos** | Un solo valor | Por debajo de 5 s, cada `BLPOP` sin trabajo termina en `TimeoutError` y el registro del worker se llena de falsos errores | Descartada |
| **Esperas separadas por lado** | La API se rinde rápido y el worker conserva la suya; cada lado tiene la que su operación necesita | Dos constantes que hay que mantener explicadas | **Elegida** |
| **Reintentos con *backoff* en el cliente** | Absorbe un parpadeo de la red | Reintentar un `RPUSH` que pudo haber entrado es justamente una vía para el duplicado, y cada reintento suma tiempo contra EC-07. La bitácora ya es el reintento, con el estado a la vista | Descartada |

### 2. Qué hacer con el trabajo que llega dos veces

| Opción | A favor | En contra | |
|---|---|---|---|
| **Aceptar el duplicado** | Cero código | Dos calificaciones de una hoja cuando exista A-02 | Descartada |
| **Que la API no publique dos veces** | Corta el problema en el origen | No es posible: después de un tiempo agotado, la API no puede saber si el `RPUSH` entró | Descartada |
| **Redis Streams con grupos de consumidores y `XACK`** | Entrega con acuse de recibo, que también cubre al worker que muere a mitad (MF-06) | Cambia la estructura de la cola y la herramienta de EC-07; ADR-0006 ya la descartó para el primer corte, y con el Key Value sin persistencia no gana durabilidad real | Prevista para A-02 |
| **Marcar el identificador en Redis con `SET NX EX`** | Atómico: entre dos workers, solo uno recibe «primera vez». Una operación, sin dependencias, sobre el Redis que ya existe | La marca vive en Redis: si se pierde (reinicio del Key Value), un duplicado posterior pasaría. Ocupa memoria mientras dura | **Elegida** |

## Decisión

1. **Esperas separadas**, en [`infraestructura/cola.py`](../../backend/infraestructura/cola.py):
   `ESPERA_AL_PUBLICAR_SEGUNDOS = 2.0`, `ESPERA_AL_CONSUMIR_SEGUNDOS = 10.0` y
   `ESPERA_DE_CONEXION_SEGUNDOS = 2.0`. `cliente_redis()` recibe la espera; la API pide la corta en
   `obtener_cliente_cola()` ([`api/main.py`](../../backend/api/main.py)) y el worker usa la larga.
2. **El cliente no reintenta por su cuenta:** `retry=Retry(NoBackoff(), 0)`, explícito para que no
   dependa del valor por omisión de la versión de `redis-py`.
3. **El worker es idempotente por `trabajo_id`.** `primera_entrega()` hace
   `SET trabajo-visto:<id> 1 NX EX 604800` (7 días) y devuelve verdadero solo la primera vez.
   [`worker/main.py`](../../backend/worker/main.py) la consulta antes de procesar; la repetida se
   registra como `trabajo_repetido` y no se procesa.
4. **Si no se puede comprobar, se procesa.** Si Redis falla en ese `SET`, el worker procesa el
   trabajo y registra `idempotencia_sin_comprobar`. El trabajo ya salió de la cola: descartarlo
   sería perder la hoja, que es peor que procesarla dos veces.
5. **La marca va antes de procesar, mientras procesar sea registrar.** Cuando A-02 procese la hoja
   de verdad, la marca pasa a después de terminar, o una caída a mitad dejaría el trabajo marcado
   y sin hacer. Está escrito en el docstring del worker para que no se olvide.
6. **Los 7 días** cubren de sobra la ventana en que una hoja pendiente se reintenta desde la
   bitácora, y son finitos para que las marcas no llenen el Key Value: cada una ocupa del orden
   de cien bytes, así que 10 000 hojas en una semana son cerca de 1 MB de los 25 MB.

**Por qué no hace falta una saga.** No hay una transacción que cruce servicios: la recepción es
una escritura local (almacén y bitácora) seguida de una publicación, y si la publicación falla no
hay nada que compensar, solo algo que terminar después (recuperación hacia adelante, desde la
bitácora). La propuesta de distractores no guarda estado. El argumento completo está en
[`modos-de-fallo.md`](../evidencia/modos-de-fallo.md#saga).

**Por qué no reemplaza a ADR-0006.** La bitácora, el orden de los cuatro pasos y el corte del lote
ante el primer `ColaNoDisponible` siguen igual. Esta decisión cambia cuánto tarda ese primer
`ColaNoDisponible` en llegar y agrega lo que hace el otro extremo de la cola: lo precisa, con el
mismo criterio con el que 0006 precisa a 0002.

## Consecuencias

### Positivas

- **EC-07 se cumple también con la cola lenta:** 2,017 s para el lote de 200. La prueba lo fija
  con 100 hojas: todas pendientes en la bitácora, una sola conexión y menos de 10 s.
- **Ningún reintento oculto:** la prueba cuenta las conexiones que recibe el servidor.
- **Un trabajo repetido se procesa una vez**, probado contra un Redis real.
- **Se cumple la condición de ADR-0011** para reconsiderar dónde corre el consumidor: el worker ya
  es idempotente. La reconsideración está en [ADR-0017](0017-no-extraer-ningun-modulo-del-monolito-todavia.md).

### Negativas

- **Una API con la red lenta hacia Redis da por pendientes hojas que habrían entrado en 3 s.** Se
  prefiere: la hoja no se pierde, queda en la bitácora, y el lote cumple su techo.
- **La marca se pierde si el Key Value se reinicia**, porque no persiste. Un duplicado que llegue
  después de un reinicio pasaría. Es la misma ventana que ya tiene la cola (ADR-0011) y se cierra
  con el mismo cambio: un Redis con persistencia.
- **Con A-02, la marca tiene que moverse** (punto 5). Queda escrito en el código y en R-23.
- **El worker que muere después del `BLPOP` y antes de terminar pierde el trabajo** (MF-06): la
  lista no tiene acuse de recibo. Esta decisión no lo resuelve; lo declara como R-22, con su plan.

## Reversión

1. **Ajustar las esperas** es cambiar dos constantes de `infraestructura/cola.py`; las pruebas de
   `test_modos_de_fallo.py` fijan el techo de una publicación en 3 s como número, para que subirla
   las ponga en rojo.
2. **Quitar la idempotencia** es quitar la consulta a `_es_primera_entrega` del worker; las marcas
   vencen solas en 7 días.

## Qué dato haría revisar esta decisión

- **Que una publicación sana a Redis tarde más de 1 s** en el entorno desplegado: la espera de 2 s
  quedaría sin margen y habría que medir antes de subirla.
- **Que se construya A-02:** la marca pasa a después de procesar, y se evalúa `XACK` o `BLMOVE`
  para cerrar MF-06.
- **Que el Key Value pase a tener persistencia**, o que la cola se mude: la vigencia de la marca se
  revisa contra la retención que se decida en R-06.

## Trazabilidad

- **Escenario:** [EC-07](../arc42/arc42-template-ES.md#ec-07).
- **Modos de fallo:** MF-01 a MF-06 de [`modos-de-fallo.md`](../evidencia/modos-de-fallo.md).
- **Riesgos:** abre R-22 y R-23 ([arc42 §11](../arc42/arc42-template-ES.md#11-risks-and-technical-debts)).
- **Código:** [`infraestructura/cola.py`](../../backend/infraestructura/cola.py)
  (`cliente_redis`, `primera_entrega`), [`api/main.py`](../../backend/api/main.py)
  (`obtener_cliente_cola`) y [`worker/main.py`](../../backend/worker/main.py).
- **Pruebas:** [`test_modos_de_fallo.py`](../../backend/tests/test_modos_de_fallo.py), validadas
  provocando la falla con mutaciones que su docstring enumera, y
  [`test_durabilidad_recepcion.py`](../../backend/tests/test_durabilidad_recepcion.py) para el
  caso de la cola caída.
- **C4:** relaciones 4 y 5 del Nivel 2 y 5 y 6 del Nivel 3 ([`c4/doc-c4.md`](../c4/doc-c4.md)).
