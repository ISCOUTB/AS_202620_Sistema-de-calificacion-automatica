# 0017 · No extraer ningún módulo del monolito todavía

- **Estado:** aceptado
- **Fecha:** 2026-10-18
- **Decide:** Josué Ortega De Arco, María Restrepo Licona, Sebastián Cañas Plata, Susana Rosales Castellar
- **Escenarios de calidad relacionados:** [EC-04](../arc42/arc42-template-ES.md#ec-04) (escalabilidad ante carga masiva), [EC-07](../arc42/arc42-template-ES.md#ec-07) y [EC-08](../arc42/arc42-template-ES.md#ec-08)
- **Origen:** la S11 pide decidir si se extrae o no un módulo, con criterios; y [ADR-0011](0011-consumir-la-cola-desde-la-instancia-de-la-api-con-el-key-value-gratuito.md) dejó escrito que llevar el consumidor a otra parte se reconsideraba cuando el worker fuera idempotente, que lo es desde [ADR-0016](0016-acotar-la-espera-de-la-cola-y-hacer-idempotente-al-worker.md)
- **Restricciones que lo acotan:** RNF-16 (US$0 y sin tarjeta), R-06 abierto ([ADR-0012](0012-mantener-el-almacen-en-el-disco-efimero-de-la-instancia-hasta-cerrar-r-06.md)), R-15 (horas compartidas de Render) y R-16 (una sola persona opera Render)
- **Relación con otros ADR:** confirma la forma de [ADR-0002](0002-procesar-calificacion-de-forma-asincrona.md) (monolito modular con un worker asíncrono) sin cambiarla, y cierra la reconsideración que ADR-0011 dejó pendiente; no reemplaza ni precisa a ninguno

**La decisión, en una frase:** ningún módulo sale del monolito en este momento, ni el worker ni
`autoria`; se mantienen las fronteras que harían barata la extracción, y quedan escritos los datos
medibles que la volverían necesaria.

---

## Contexto

**Qué se podría extraer.** El monolito tiene siete módulos de dominio y dos puntos de entrada. Tres
de los módulos tienen código (`ingesta`, `autoria`, `infraestructura`); los demás están vacíos. Las
dos piezas que tienen un motivo plausible para salir son las dos que ya hablan con algo fuera del
proceso de la API:

- **El worker**, que consume la cola. Ya corre como **proceso aparte** dentro de la misma
  instancia (`arrancar-api-y-worker.sh`), con su propio punto de entrada, y solo se comunica con la
  API a través de Redis y del almacén: no comparte memoria con ella. Es el que tendría que escalar
  cuando exista el OMR (EC-04).
- **`autoria` con su adaptador al proveedor de LLM**, que depende de un sistema externo que el
  equipo no controla. Es la única integración que sale a internet.

**Lo que ya se midió.** Que la falla del proveedor no arrastre a la API está medido: con Groq caído
o lento, la ruta respondió 503 en 2,23 s y 20,25 s y `/health` siguió en 200 en los cuatro casos
(EC-08, M3); y una ráfaga contra la ruta queda en 429 sin salir a la red, con `/health` en 200
(EC-09). Que una cola caída o lenta no rompa la recepción, también: el lote de 200 confirma en
2,017 s con Redis lento ([`modos-de-fallo.md`](../evidencia/modos-de-fallo.md), MF-02).

**Lo que no se puede medir todavía.** EC-04 (200 hojas procesadas en 10 minutos con la CPU por
debajo del 85 %) depende del OMR, que no existe: hoy el worker solo escribe una línea de log por
hoja. No hay un dato de carga que diga que el worker necesita recursos propios.

**El entorno.** La API y el worker comparten un servicio web gratuito de Render: 0,1 CPU y 512 MB.
Las hojas y la bitácora viven en el disco efímero de esa instancia (ADR-0012), al que solo pueden
llegar los procesos de esa misma instancia. Las 750 horas gratuitas de servicio web son compartidas
por todo el workspace, y el monitor que mantiene despierta la API ya gasta entre 720 y 744 (R-15).
Render no tiene plan gratuito para *background workers*: el más barato cuesta US$7 al mes
(ADR-0011).

## Alternativas consideradas

### Opciones

1. **No extraer ninguno.** El worker sigue como segundo proceso de la instancia de la API, y
   `autoria` como módulo de la API.
2. **Extraer el worker a un servicio propio** en Render, como *background worker* o como un
   segundo servicio web que consuma la cola.
3. **Llevar el consumidor a una función** fuera de Render. Es la opción que ADR-0011 dejó para
   cuando el worker fuera idempotente, y es la que la guía de despliegue del curso acepta para un
   consumidor de cola «con idempotencia».
4. **Extraer `autoria` y el adaptador del proveedor a un servicio de distractores** propio, para
   aislar la única dependencia externa.

### Criterios

| Criterio | Qué pregunta |
|---|---|
| **C1 · Aislamiento de fallos** | ¿Hoy la falla de esa pieza arrastra al resto? Si no, extraerla no compra aislamiento |
| **C2 · Escalado independiente** | ¿Hay una carga medida que pida recursos propios para esa pieza? |
| **C3 · Datos** | ¿La pieza puede llevarse sus datos, o depende de algo que solo existe dentro de la instancia? |
| **C4 · Costo** | ¿Cabe en US$0 sin tarjeta (RNF-16) y en las horas compartidas (R-15)? |
| **C5 · Operación** | ¿Cuántas piezas más tiene que desplegar y vigilar una sola persona (R-16)? |
| **C6 · Modos de fallo nuevos** | ¿Cuántas integraciones nuevas, cada una con sus tres casos de la S11, agrega? |
| **C7 · Reversibilidad** | ¿Se puede extraer después sin reescribir, si los datos lo piden? |

### Evaluación

| | 1 · No extraer | 2 · Worker en servicio propio | 3 · Consumidor como función | 4 · Servicio de distractores |
|---|---|---|---|---|
| **C1** | Ya aislado: el worker es otro proceso y se reinicia solo; el proveedor caído deja `/health` en 200 (medido) | No gana: ya es otro proceso | No gana | No gana: EC-08 y EC-09 ya miden el aislamiento |
| **C2** | Suficiente mientras el worker solo registra | **Sin dato que lo pida**: EC-04 no se puede medir sin OMR | Sin dato que lo pida | La ruta está acotada a 6 solicitudes por minuto: no hay carga que escalar |
| **C3** | Sin cambios | **Bloqueado**: las hojas están en el disco efímero de la instancia de la API (ADR-0012); otro servicio no las ve | **Bloqueado**, por lo mismo; además la función no puede hacer `BLPOP` y necesitaría otro disparador | Posible: `autoria` no tiene datos propios; el presupuesto en memoria (R-18) se iría con él |
| **C4** | US$0 | **Rompe RNF-16**: *background worker* a US$7; un segundo servicio web siempre despierto duplicaría las horas (1 440 a 1 488 de 750) | Un proveedor nuevo, con su cuenta y su capa gratuita por verificar (si pide tarjeta, rompe RNF-16) | **Rompe R-15**: un segundo servicio web despierto no cabe en las 750 horas; dormido, cada primera solicitud pagaría 12,5 s de arranque en frío (R-13) |
| **C5** | Igual que hoy | Un servicio más en `render.yaml`, con su log y sus variables | Una plataforma más, fuera del Blueprint | Un servicio más, y el sitio con dos URL o la API como intermediaria |
| **C6** | Ninguno | Ninguno nuevo: la cola ya está | La conexión de la función con Redis, desde fuera de la red privada del Key Value (`ipAllowList: []`) | **Uno nuevo**: API → servicio de distractores, con no responde, responde tarde y responde dos veces, delante del que ya existe con Groq |
| **C7** | Alta: ver la decisión | — | — | — |

## Decisión

1. **No se extrae ningún módulo.** El worker sigue como segundo proceso de la instancia de la API
   (ADR-0011) y `autoria` como módulo de la API (ADR-0013).
2. **No es por falta de tiempo.** Extraer el worker es, en código, cambiar el comando de arranque y
   agregar un servicio a `render.yaml`: ya tiene su punto de entrada y ya habla con la API solo por
   Redis. Lo que lo impide son los datos (C3) y el costo (C4), y lo que lo haría innecesario hoy es
   que el aislamiento ya está medido (C1) y no hay carga que escalar (C2).
3. **Se mantienen las fronteras que hacen barata la extracción** (C7):
   - `test_fronteras.py` sigue en cada push, y ningún módulo importa por fuera de su `Importa:`.
   - El worker y la API solo se comunican por la cola y por el puerto `AlmacenDeImagenes`, nunca en
     memoria. Un cambio que los acople es un cambio de este ADR.
   - `autoria` solo sale a la red por el puerto `GeneradorDeDistractores`: moverla a otro servicio
     es escribir un adaptador nuevo de ese puerto que llame por HTTP, sin tocar la regla.
   - El worker es idempotente (ADR-0016), que es la condición que ADR-0011 pedía para moverlo.

## Consecuencias

### Positivas

- **Ninguna integración nueva**, y por tanto ningún modo de fallo nuevo que cubrir.
- **El costo sigue en US$0** y las horas de Render alcanzan.
- **Una sola pieza que desplegar**, desde el Blueprint, que cualquier integrante puede recrear (R-16).

### Negativas

- **El worker comparte 0,1 CPU con la API.** Cuando exista el OMR, un lote grande puede hacer más
  lenta la API mientras se procesa. Es el primer dato que hay que medir con A-02 (ver abajo).
- **Una caída de la instancia se lleva las dos cosas** a la vez, la API y el worker. Hoy Render la
  reinicia y la bitácora conserva lo pendiente mientras el disco viva (ADR-0012).
- **La decisión depende de datos que todavía no existen** (EC-04). Por eso es «todavía» y tiene
  disparadores concretos, no un «no» permanente.

## Reversión

Extraer el worker, el día que los datos lo pidan: cerrar antes R-06 con un almacén de objetos (sin
eso, otro servicio no ve las hojas), agregar el servicio en `render.yaml` con
`python -m worker.main` como comando, y quitar el ciclo del worker de `arrancar-api-y-worker.sh`. La
cola, el código del worker y su idempotencia no cambian.

## Qué dato haría revisar esta decisión

- **Que EC-04 se mida con el OMR de A-02 y no se cumpla** con el worker en la instancia compartida
  (más de 10 minutos para 200 hojas, o la CPU por encima del 85 %): se extrae el worker (opción 2).
- **Que R-06 se cierre con un almacén de objetos:** desaparece el bloqueo de C3 para las opciones 2
  y 3, y se vuelve a evaluar con el costo de ese día.
- **Que el equipo tenga presupuesto** o que RNF-16 cambie: desaparece el bloqueo de C4.
- **Que `/health` deje de responder en menos de 1 s mientras el proveedor de LLM falla o mientras
  se procesa un lote**, medido con las herramientas de EC-08 y EC-07: se evalúa la opción 4.
- **Que la API corra en más de una instancia:** el presupuesto pasa a Redis (ADR-0015) y se
  revisa si `autoria` sigue en la API.

## Trazabilidad

- **Escenarios:** [EC-04](../arc42/arc42-template-ES.md#ec-04), [EC-07](../arc42/arc42-template-ES.md#ec-07)
  y [EC-08](../arc42/arc42-template-ES.md#ec-08).
- **Datos que la sostienen:** la [evaluación de EC-08](../evidencia/evaluacion-distractores.md) (M3),
  el [experimento de EC-09](../evidencia/experimento-presupuesto.md) (M4) y la
  [tabla de modos de fallo](../evidencia/modos-de-fallo.md).
- **Riesgos:** R-06, R-15, R-16 y R-25 ([arc42 §11](../arc42/arc42-template-ES.md#11-risks-and-technical-debts)).
- **Código que mantiene barata la extracción:** [`worker/main.py`](../../backend/worker/main.py),
  [`arrancar-api-y-worker.sh`](../../backend/arrancar-api-y-worker.sh),
  [`autoria/distractores.py`](../../backend/autoria/distractores.py) (el puerto) y
  [`test_fronteras.py`](../../backend/tests/test_fronteras.py).
- **Despliegue:** [`render.yaml`](../../render.yaml) y
  [`docs/despliegue/costo-mensual.md`](../despliegue/costo-mensual.md).
