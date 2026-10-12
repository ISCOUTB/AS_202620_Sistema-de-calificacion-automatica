# 0015 · Limitar el gasto del proveedor de LLM con un presupuesto en la API

- **Estado:** aceptado
- **Fecha:** 2026-10-11
- **Decide:** Josué Ortega De Arco, María Restrepo Licona, Sebastián Cañas Plata, Susana Rosales Castellar
- **Escenario de calidad relacionado:** [EC-09](../arc42/arc42-template-ES.md#ec-09) (ráfaga contra la ruta de distractores), del segundo corte
- **Condición operativa del segundo corte:** límite de costo
- **Restricciones que lo acotan:** RNF-16 (US$0 y sin tarjeta), RNF-11 (ninguna credencial versionada)
- **Relación con otros ADR:** precisa [ADR-0013](0013-consumir-groq-detras-de-un-puerto-y-degradar-sin-bloquear-la-autoria.md) sin reemplazarlo, y mitiga el riesgo R-17

**La decisión, en una frase:** antes de salir a la red, cada solicitud de `POST /distractores` tiene
que caber en un presupuesto de 6 solicitudes por minuto y 150 por día, que vive en la memoria de la
API; la que no cabe se responde con 429 y `Retry-After`, sin gastar cuota del proveedor, y el
estado del presupuesto se publica en `GET /metricas`.

---

## Contexto

**La condición operativa.** El segundo corte pide demostrar cómo responde el MVP desplegado a un
escenario operativo nuevo. El del equipo es de **límite de costo**: `POST /distractores` es
pública, sin autenticación (R-17), y cada solicitud gasta cuota de la capa gratuita de Groq.
[ADR-0013](0013-consumir-groq-detras-de-un-puerto-y-degradar-sin-bloquear-la-autoria.md) dejó esa
consecuencia escrita y la daba por cerrada con dos argumentos: sin tarjeta el peor caso es agotar la
cuota y nunca una factura, y la ruta responde 503 cuando eso pasa.

**La línea base medida.** El 11-oct-2026 se lanzó contra el entorno desplegado una ráfaga de 20
solicitudes seguidas con
[`medir_presupuesto.py`](../../backend/herramientas/medir_presupuesto.py)
([`presupuesto-antes.json`](../evidencia/presupuesto-antes.json)):

| | Solicitudes |
|---|---|
| Llegaron al proveedor | 20 de 20 |
| Recibieron propuestas | 12 |
| Las cortó el proveedor por cuota (503) | 8, en 0,18 s cada una |
| Las cortó la API | 0: no había ningún freno propio |
| `/health` | 200 durante toda la ráfaga |

La ráfaga duró 22 s. **Una sola persona agotó en 18 segundos el límite por minuto de todo el
sistema**, y durante ese minuto ningún profesor pudo pedir distractores. El argumento de ADR-0013
sigue siendo cierto (no hubo factura, y el 503 llegó con su motivo), pero no alcanza: el costo no es
dinero, es la cuota compartida, y la cuota diaria (200 000 tokens) se agota igual de rápido con 233
solicitudes.

**Lo que acota la decisión:**
- **RNF-16:** la solución no puede costar dinero ni pedir tarjeta.
- **R-06 sigue abierto:** no hay persistencia estructurada donde guardar contadores.
- **Una sola instancia de la API con un solo proceso de uvicorn** (ADR-0009, ADR-0011).
- **`identidad` (A-05) no existe**, así que no se puede repartir el cupo por profesor.
- **Los límites de Groq**, consultados el 4-oct-2026 en https://console.groq.com/docs/rate-limits:
  8 000 tokens por minuto, 200 000 por día, 30 solicitudes por minuto y 1 000 por día.

## Alternativas consideradas

### 1. Dónde poner el freno

| Opción | A favor | En contra | |
|---|---|---|---|
| **No hacer nada** (statu quo de ADR-0013) | Cero código | La línea base muestra que una ráfaga corta a todos durante un minuto, y que 233 solicitudes agotan el día | Descartada |
| **Límite por IP**, con una biblioteca como `slowapi` | Reparte el cupo entre clientes | Agrega una dependencia y regenera el lock. Detrás del proxy de Render la IP del cliente llega en una cabecera que el cliente puede falsificar. Y no protege la cuota: veinte IP distintas la agotan igual | Descartada |
| **Presupuesto global en la memoria de la API** | Sin dependencias, sin red, sin tocar el dominio. Protege la cuota diaria aunque lleguen veinte clientes | Se vacía con cada reinicio; no sirve con más de una instancia; un cliente puede gastar el cupo de los demás | **Elegida** |
| **Presupuesto global en Redis** (el Key Value) | Sobrevive a reinicios de la API y sirve con varias instancias | El Key Value gratuito tampoco persiste (ADR-0011), así que no gana durabilidad real; agrega una ida y vuelta de red a cada solicitud; con una sola instancia no hay nada que coordinar | Descartada por ahora |
| **Autenticación** (A-05) | Es lo que cierra R-17 de verdad, con un cupo por profesor | `identidad` está vacío: no cabe en el corte | Prevista |

### 2. Qué contar

| Opción | | Por qué |
|---|---|---|
| Tokens | Descartada | Los tokens solo se conocen cuando el proveedor ya respondió, y para entonces ya se gastaron: el freno llegaría tarde |
| **Solicitudes enviadas, con un límite derivado del peor caso de tokens** | **Elegida** | Se sabe antes de salir a la red. El peor caso medido en la evaluación de EC-08 es de 1 323 tokens por solicitud: 6 por minuto son como mucho 7 938 tokens (debajo de 8 000) y 150 por día, como mucho 198 450 (debajo de 200 000) |

### 3. Qué responder cuando no hay cupo

| Opción | | Por qué |
|---|---|---|
| 503, como cuando el proveedor falla | Descartada | Diría «el proveedor no está disponible», que es falso: el proveedor está bien, lo que se agotó es el presupuesto propio. Un cliente no podría distinguir los dos casos |
| Esperar hasta que haya cupo | Descartada | Retiene un hilo hasta 60 s por solicitud; con una ráfaga, deja sin hilos a las demás rutas, incluida `/health` |
| **429 con `Retry-After`** | **Elegida** | Es el código del protocolo para «demasiadas solicitudes», y la cabecera dice cuándo volver. Es aditivo en el contrato: un cliente que ya consume la ruta no pierde nada |

## Decisión

1. **El presupuesto es un adaptador del puerto de `autoria`.** `GeneradorConPresupuesto`, en
   [`autoria/presupuesto.py`](../../backend/autoria/presupuesto.py), implementa
   `GeneradorDeDistractores` reservando un cupo antes de delegar en el adaptador real. La regla de
   `distractores.py` y el adaptador de `proveedor_llm.py` no cambian.
2. **Dos ventanas deslizantes:** 6 solicitudes por minuto y 150 por 24 horas, configurables con
   `LLM_SOLICITUDES_POR_MINUTO` y `LLM_SOLICITUDES_POR_DIA`. Los valores por omisión se declaran una
   sola vez, en `autoria`, y `api/settings.py` los lee de ahí.
3. **Cuenta lo que sale a la red.** Una solicitud cuenta en cuanto se envía, aunque el proveedor
   falle después. La que se responde con 503 por falta de clave no cuenta, porque nunca sale.
4. **Sin cupo, 429 con `Retry-After`** y el motivo en `detail`, sin llamar al proveedor.
5. **La reserva es atómica** (`threading.Lock`), porque la ruta corre en el grupo de hilos de
   FastAPI.
6. **Observabilidad:** cada corte deja un evento `presupuesto_agotado` en el registro JSON, con la
   ventana que lo cortó y lo usado; y `GET /metricas` publica el estado del presupuesto sin tocar
   la red ni el disco.
7. **El contrato pasa a 1.2.0**: agrega `GET /metricas` y el 429 de `/distractores`. Es un cambio
   menor porque solo agrega.
8. **Vive en la memoria del proceso de la API.** Es correcto con la única instancia y el único
   proceso de uvicorn que corren hoy, y es la deuda R-18 de la sección 11 del arc42.

**Por qué no reemplaza a ADR-0013.** Sus nueve puntos siguen vigentes: el proveedor sigue siendo
Groq, detrás del mismo puerto y adaptador, con 20 s de espera, sin reintentos y 503 ante cualquier
falla del proveedor. Lo que cambia es una consecuencia que ADR-0013 aceptaba («la ruta queda pública
sin autenticación, y cada solicitud gasta cuota»), que ahora tiene un freno medido. Esta decisión
precisa a ADR-0013 con el mismo criterio con el que 0006 precisa a 0002.

## Consecuencias

### Positivas

- **Ninguna ráfaga agota la cuota del proveedor.** Medido en local con un proveedor que aplica el
  límite publicado de Groq ([experimento](../evidencia/experimento-presupuesto.md)): de 20
  solicitudes, 6 llegan al proveedor y las 6 reciben propuestas; las 14 restantes reciben 429 en
  2 ms de mediana, sin salir a la red; ninguna termina en 503 por cuota. Sin el presupuesto, en el
  mismo montaje, llegaban las 20 y 11 terminaban en 503.
- **La cuota diaria queda protegida.** Ni con veinte clientes se pasa de 150 solicitudes al día.
- **El costo sigue en US$0** y no se agrega ninguna dependencia.
- **El cliente sabe qué pasó y cuándo volver**: el 429 se distingue del 503 y trae `Retry-After`.
- **El escenario se puede observar en vivo**, en `GET /metricas` y en el registro.

### Negativas

- **El cupo es global, no por profesor.** Una persona puede gastar el de los demás durante un
  minuto, o durante un día si insiste 150 veces. Lo cierra A-05 con un cupo por profesor (R-19).
- **Se vacía con cada reinicio y cada despliegue**, porque vive en memoria (R-18). Un reinicio en
  mitad del día devuelve el cupo diario completo: en 24 horas podrían salir hasta 300 solicitudes,
  más de las que caben en la cuota diaria de Groq. En ese caso el último freno vuelve a ser el 503
  del proveedor, como antes de esta decisión. Con el patrón de despliegue del proyecto (solo cuando
  cambia `backend/` y el CI queda en verde) es poco probable, pero no imposible.
- **Con más de una instancia o más de un proceso de uvicorn, cada uno tendría su propio
  presupuesto** y el total se multiplicaría. El día que eso pase, el presupuesto se mueve a Redis
  (la alternativa descartada por ahora) detrás del mismo adaptador.
- **6 por minuto es conservador**: en la línea base Groq dejó pasar 12 en el mismo minuto. Se
  prefiere un límite que no dependa de lo que el proveedor tolere un día dado.
- **La herramienta de EC-08 tiene que saltarse el presupuesto** para seguir siendo comparable con
  la de la S9 (manda 7,5 por minuto). Lo hace con `dependency_overrides`, y lo dice en su docstring.

## Reversión

1. **Ajustar los límites** es cambiar dos variables de entorno en `render.yaml` y redesplegar.
2. **Quitar el presupuesto** es volver a pasar el generador sin envolver en `api/main.py`: el
   contrato conservaría el 429 declarado sin usarlo, que no rompe a ningún cliente.
3. **Si el proveedor cambia**, los límites se recalculan con sus límites publicados y el peor caso
   de tokens medido con `evaluar_distractores.py`.

## Qué dato haría revisar esta decisión

- **Que la API corra en más de una instancia o con más de un proceso:** el presupuesto pasa a Redis.
- **Que se construya `identidad` (A-05):** el cupo pasa a ser por profesor.
- **Que la evaluación de EC-08 mida un peor caso de tokens por encima de 1 333** (8 000 / 6): el
  límite por minuto ya no cabría en el del proveedor y hay que bajarlo.

## Trazabilidad

- **Escenario:** [EC-09](../arc42/arc42-template-ES.md#ec-09), medido en el
  [experimento del segundo corte](../evidencia/experimento-presupuesto.md).
- **Riesgos:** mitiga R-17; abre R-18 y R-19 ([arc42 §11](../arc42/arc42-template-ES.md#11-risks-and-technical-debts)).
- **Código:** [`autoria/presupuesto.py`](../../backend/autoria/presupuesto.py),
  [`api/main.py`](../../backend/api/main.py) (`obtener_presupuesto`, el 429 y `GET /metricas`),
  [`api/esquemas.py`](../../backend/api/esquemas.py) (contrato 1.2.0) y
  [`api/settings.py`](../../backend/api/settings.py).
- **Configuración:** [`.env.example`](../../.env.example),
  [`docker-compose.yml`](../../docker-compose.yml) y [`render.yaml`](../../render.yaml).
- **Pruebas:** [`test_presupuesto.py`](../../backend/tests/test_presupuesto.py),
  [`test_ruta_distractores.py`](../../backend/tests/test_ruta_distractores.py) y
  [`test_contrato.py`](../../backend/tests/test_contrato.py), y el paso «Escenario del segundo corte»
  de [`ci.yml`](../../.github/workflows/ci.yml).
- **Herramientas:** [`medir_presupuesto.py`](../../backend/herramientas/medir_presupuesto.py) y
  [`proveedor_simulado.py`](../../backend/herramientas/proveedor_simulado.py).
- **C4:** relación 8 del Nivel 2 y relaciones 11 y 12 del Nivel 3 ([`c4/doc-c4.md`](../c4/doc-c4.md)).
