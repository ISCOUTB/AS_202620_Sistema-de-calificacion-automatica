# Modos de fallo de las integraciones (S11)

La S11 pide, para la integración principal del sistema, qué pasa cuando el otro lado **no
responde**, **responde tarde** o **responde dos veces**, con una mitigación asignada a cada caso, y
que las mitigaciones declaradas en los ADR estén implementadas o pendientes con un plan. Este
documento lo hace para las tres integraciones que tiene QuantIA, no solo para la principal, y
separa lo que tiene prueba automática de lo que solo está descrito.

- **Decisiones:** [ADR-0016](../adr/0016-acotar-la-espera-de-la-cola-y-hacer-idempotente-al-worker.md)
  (esperas de la cola y worker idempotente) y
  [ADR-0017](../adr/0017-no-extraer-ningun-modulo-del-monolito-todavia.md) (no extraer ningún
  módulo todavía).
- **Riesgos:** R-22 a R-24 en la [sección 11 del arc42](../arc42/arc42-template-ES.md#11-risks-and-technical-debts).
- **Pruebas:** [`test_modos_de_fallo.py`](../../backend/tests/test_modos_de_fallo.py) y las que la
  tabla cita, que el pipeline corre en el paso «Modos de fallo de las integraciones (S11)» de
  [`ci.yml`](../../.github/workflows/ci.yml).
- **Fecha:** 2026-10-18, sobre el código de `master` después de los commits de la S11. Actualizado
  con los arreglos del 19-oct (sección 9): cambiaron MF-02, MF-05 y
  MF-13.

## 1. Las integraciones

QuantIA es un monolito modular ([ADR-0002](../adr/0002-procesar-calificacion-de-forma-asincrona.md)):
los siete módulos del dominio se llaman en proceso, y entre ellos no hay red que pueda fallar. Las
integraciones son las tres fronteras donde sí hay un proceso o un sistema del otro lado.

| ID | De → a | Protocolo | Dónde está la llamada | Por qué importa |
|---|---|---|---|---|
| **I-1** · principal | API → cola (Redis) → worker | Redis: `RPUSH` y `BLPOP` sobre una lista, con `redis-py` | [`infraestructura/cola.py`](../../backend/infraestructura/cola.py) (`publicar`, `desencolar`), llamada desde [`ingesta/recepcion.py`](../../backend/ingesta/recepcion.py) y [`worker/main.py`](../../backend/worker/main.py) | Es la columna de ADR-0002: **toda hoja aceptada pasa por ella**, y EC-07 promete 0 % de pérdida silenciosa y confirmación en 10 s |
| **I-2** | API → proveedor de LLM (Groq) | HTTPS, `POST /chat/completions`, con `httpx` | [`autoria/proveedor_llm.py:135`](../../backend/autoria/proveedor_llm.py) | Es el único sistema externo que el equipo no controla. RF-11 es opcional: su falla no puede arrastrar al resto |
| **I-3** | Navegador (sitio Flutter) → API | HTTPS, con `package:http` | [`servicio_salud.dart`](../../frontend/lib/common/api/servicio_salud.dart), [`servicio_carga.dart`](../../frontend/lib/features/carga/data/servicio_carga.dart) y [`servicio_distractores.dart`](../../frontend/lib/features/pauta/data/servicio_distractores.dart) | Es lo que ve el docente: un fallo mal explicado aquí parece una pérdida aunque no lo sea |

**Por qué la principal es I-1 y no I-2.** I-2 es la que encuentra primero una búsqueda de llamadas
HTTP (ver la sección 7), pero RF-11 es opcional y ninguna nota depende de ella. Por I-1 pasan todas
las hojas, y es la que sostiene el escenario de calidad del aspecto construido más importante
(EC-07). Por eso I-1 tiene un ADR propio en esta entrega, y las otras dos se cubren con lo que ya
decidieron ADR-0013 y ADR-0015 más las pruebas que faltaban.

## 2. Tabla de modos de fallo

**Estado:** *Probada* = la mitigación está en el código y una prueba automática se pone en rojo si
se quita (las de la S11 se validaron provocando la falla, con las mutaciones que lista el docstring
de `test_modos_de_fallo.py`). *Implementada* = está en el código, sin prueba automática del caso.
*Declarada* = no está en el código; tiene riesgo en la sección 11 y un plan.

| ID | Int. | Modo | Qué pasaría sin mitigación | Mitigación asignada | Dónde está | Prueba | Estado |
|---|---|---|---|---|---|---|---|
| **MF-01** | I-1 | **No responde** al publicar: Redis caído o rechaza la conexión | Medido en el corte 1: el endpoint devolvía 500 y **100 % de pérdida silenciosa** | Bitácora antes de encolar: la hoja queda `pendiente_de_encolar`, el lote se confirma completo y deja de insistir tras el primer fallo ([ADR-0006](../adr/0006-registrar-la-recepcion-en-una-bitacora-antes-de-encolar.md)) | [`ingesta/recepcion.py:233`](../../backend/ingesta/recepcion.py) · [`cola.py:115`](../../backend/infraestructura/cola.py) | 18 en [`test_durabilidad_recepcion.py`](../../backend/tests/test_durabilidad_recepcion.py), entre ellas `test_ninguna_hoja_del_lote_queda_sin_reportar_si_la_cola_se_cae` y `test_el_lote_no_insiste_contra_una_cola_caida` | Probada |
| **MF-02** | I-1 | **Responde tarde** al publicar: Redis acepta la conexión y no contesta | Medido en la S11 con `58147b8`: **10,012 s** por publicación y **10,017 s** un lote de 200, fuera del techo de 10 s de EC-07 | Espera de 2 s para publicar y para conectar, separada de la del worker, y el cliente sin reintentos propios ([ADR-0016](../adr/0016-acotar-la-espera-de-la-cola-y-hacer-idempotente-al-worker.md)). Después: 2,004 s y 2,017 s. **Desde los arreglos del 19-oct, además, un plazo de 8 s para todo el lote:** la espera de 2 s es por llamada, y una cola que contesta cada publicación en 1,9 s nunca fallaba y llevaba 200 hojas a unos 380 s; vencido el plazo, lo que falta queda pendiente | [`cola.py:48-50`](../../backend/infraestructura/cola.py) y `cliente_redis` (línea 79) · [`api/main.py:107`](../../backend/api/main.py) · [`ingesta/recepcion.py:221`](../../backend/ingesta/recepcion.py) (`PLAZO_PARA_ENCOLAR_SEGUNDOS`, línea 63) | 4 en [`test_modos_de_fallo.py`](../../backend/tests/test_modos_de_fallo.py): la publicación se rinde en menos de 3 s; un lote de 100 confirma en menos de 10 s, todo pendiente, con una conexión; el cliente no reintenta; la conexión lleva su espera. Y `test_una_cola_lenta_no_lleva_el_lote_fuera_del_techo_de_ec07`, en `test_durabilidad_recepcion.py` | Probada (S11; el plazo, el 19-oct) |
| **MF-03** | I-1 | **Responde dos veces**: el mismo trabajo llega dos veces al worker. Pasa si un `RPUSH` vence en el cliente pero entró en Redis y la hoja se republica desde la bitácora, con el mismo `trabajo_id` | Dos procesamientos de la misma hoja; con A-02, dos calificaciones | Worker idempotente: `SET trabajo-visto:<id> NX EX` de 7 días antes de procesar; la repetida se registra `trabajo_repetido` y se salta. Si no se puede comprobar, se procesa y se registra `idempotencia_sin_comprobar` ([ADR-0016](../adr/0016-acotar-la-espera-de-la-cola-y-hacer-idempotente-al-worker.md)) | [`cola.py:126`](../../backend/infraestructura/cola.py) (`primera_entrega`) · [`worker/main.py:54`](../../backend/worker/main.py) y `_es_primera_entrega` (línea 80) | `test_el_trabajo_que_llega_dos_veces_se_procesa_una_sola_vez` (Redis real) y `test_si_no_se_puede_comprobar_la_marca_el_trabajo_se_procesa_igual` | Probada (S11) |
| **MF-04** | I-1 | **No responde** al consumir: Redis caído mientras el worker espera | El worker terminaría con una excepción y dejaría de consumir | El worker captura `RedisError`, espera 5 s y vuelve a pedir; si aun así termina, `arrancar-api-y-worker.sh` lo reinicia ([ADR-0011](../adr/0011-consumir-la-cola-desde-la-instancia-de-la-api-con-el-key-value-gratuito.md)) | [`worker/main.py:43`](../../backend/worker/main.py) · [`arrancar-api-y-worker.sh`](../../backend/arrancar-api-y-worker.sh) | `test_el_worker_sigue_vivo_si_la_cola_no_responde` | Probada (S11) |
| **MF-05** | I-1 | **Responde tarde** al consumir | Sin espera en el socket, el `BLPOP` se quedaría colgado para siempre | Espera de 10 s en el socket (más que los 5 s del `BLPOP`). Si vence igual, el `TimeoutError` llega al worker, que lo registra como `fallo_de_la_cola`, espera 5 s y vuelve a pedir, como en MF-04. Hasta los arreglos del 19-oct se traducía en «no hay trabajo»: una cola caída se veía como un worker sin trabajo, sin aviso ni pausa | [`cola.py:158`](../../backend/infraestructura/cola.py) (`desencolar`) · [`worker/main.py:43`](../../backend/worker/main.py) | `test_desencolar_de_una_cola_que_no_contesta_avisa_en_vez_de_colgarse` · `test_el_worker_sigue_vivo_si_la_cola_no_responde[responde-tarde]` | Probada (S11; el aviso, el 19-oct) |
| **MF-06** | I-1 | El worker **muere después del `BLPOP`** y antes de terminar: la cola entregó, pero nadie confirma | El trabajo sale de la lista y no vuelve: la hoja queda almacenada, pero no se procesa | **Acuse de recibo**: `BLMOVE` a una lista de trabajos en curso y `LREM` al terminar, o Redis Streams con `XACK`. Se construye con A-02, que es cuando procesar deja de ser escribir una línea de log. **Construida en el taller de mensajería ([ADR-0020](../adr/0020-entregar-los-trabajos-al-menos-una-vez-con-reintentos-y-lista-de-fallidos.md))**: `BLMOVE` a `procesamiento:en-curso`, `LREM` al terminar, y lo que quedó en curso vuelve a la cola al arrancar | — · desde ADR-0020, [`consumo.py`](../../backend/infraestructura/consumo.py) (`tomar`, `confirmar`, `recuperar_en_curso`) | — · desde ADR-0020, `test_un_trabajo_que_quedo_en_curso_vuelve_a_la_cola_al_arrancar_y_se_procesa` ([`test_mensajeria.py`](../../backend/tests/test_mensajeria.py)) | **Declarada** (R-22). **Probada desde ADR-0020** |
| **MF-07** | I-2 | **No responde**: Groq caído, sin red o sin clave | La ruta devolvería 500, o se colgaría | 503 con un motivo para el profesor, sin reintentos; sin clave, 503 antes de reservar cupo ([ADR-0013](../adr/0013-consumir-groq-detras-de-un-puerto-y-degradar-sin-bloquear-la-autoria.md)). Medido en EC-08: 503 en 2,23 s, `/health` en 200 | [`proveedor_llm.py:148`](../../backend/autoria/proveedor_llm.py) · [`api/main.py:347`](../../backend/api/main.py) | `test_sin_conexion_con_el_proveedor` · `test_sin_proveedor_configurado_responde_503_y_la_api_sigue_viva` · `test_si_el_proveedor_falla_responde_503_con_el_motivo` | Probada |
| **MF-08** | I-2 | **Responde tarde** | Cada solicitud retendría un hilo de la API sin límite | Espera de 20 s y 503 con el motivo (ADR-0013); el presupuesto de 6 por minuto acota cuántas pueden estar esperando a la vez (ADR-0015). Medido en EC-08: 503 en 20,25 s | [`proveedor_llm.py:44`](../../backend/autoria/proveedor_llm.py) y línea 143 | `test_el_tiempo_agotado_no_tumba_la_solicitud` (transporte simulado) y `test_un_proveedor_que_no_contesta_se_corta_en_su_espera_y_sin_reintentar` (un servidor que no contesta, una sola conexión) | Probada (S11) |
| **MF-09** | I-2 | **Responde dos veces** / la solicitud se repite: doble clic o reenvío | Doble gasto de cuota. No hay estado que duplicar | La ruta no guarda nada: cada solicitud es independiente, y el presupuesto cuenta cada una (ADR-0015). En el sitio, el botón se deshabilita mientras espera. **Desde [ADR-0019](../adr/0019-guardar-en-cache-las-propuestas-de-distractores.md)**, la repetida dentro de 24 horas sale de la caché de propuestas, sin llegar al proveedor ni gastar cupo; «Pedir otras propuestas» manda `otras: true` y sí sale | [`api/main.py:287`](../../backend/api/main.py) · [`pantalla_pauta.dart:306`](../../frontend/lib/features/pauta/views/pantalla_pauta.dart) | `test_la_misma_solicitud_dos_veces_no_deja_estado_y_gasta_su_propio_cupo` · en el frontend, «Mientras espera muestra la forma de las tarjetas y el límite de 20 s» ([`pauta_test.dart:151`](../../frontend/test/features/pauta_test.dart)) · con la caché, `test_la_misma_pregunta_sale_de_la_cache_sin_llamar_al_proveedor_ni_gastar_cupo` ([`test_cache_de_propuestas.py`](../../backend/tests/test_cache_de_propuestas.py)) | Probada (S11) |
| **MF-10** | I-2 | Responde **con error** o **ilegible**: 429 de cuota, 401, 5xx o un JSON sin la forma pedida | 500, o una propuesta vacía presentada como válida | 503 con un motivo distinto para cada caso (ADR-0013) | [`proveedor_llm.py`](../../backend/autoria/proveedor_llm.py), desde la línea 154 | `test_un_codigo_de_error_del_proveedor_se_explica_al_profesor` (5 casos) · `test_una_respuesta_sin_la_forma_esperada_se_reporta_como_ilegible` | Probada |
| **MF-11** | I-3 | **No responde**: la API dormida, caída o sin red | El docente llenaría el formulario y fallaría al final | `/health` con 5 s de espera; sin respuesta, la barra lo dice y los botones de subir y de proponer se deshabilitan. El monitor externo mantiene la instancia despierta (R-13) | [`servicio_salud.dart:19`](../../frontend/lib/common/api/servicio_salud.dart) | «Sin conexión con la API el botón se deshabilita y lo dice» ([`carga_test.dart:203`](../../frontend/test/features/carga_test.dart)) · «El botón queda deshabilitado sin enunciado, sin respuesta o sin conexión» ([`pauta_test.dart:118`](../../frontend/test/features/pauta_test.dart)) | Probada |
| **MF-12** | I-3 | **Responde tarde** | La pantalla esperaría sin decir nada | Distractores: 25 s de espera en el navegador, por encima de los 20 s de la API, y un aviso que ofrece volver a pedir. Carga: **sin espera en el navegador, a propósito** (ver nota 1); si la conexión se corta mientras llega la respuesta, el aviso dice que algunas hojas pudieron entrar | [`servicio_distractores.dart:123`](../../frontend/lib/features/pauta/data/servicio_distractores.dart) · [`servicio_carga.dart:141`](../../frontend/lib/features/carga/data/servicio_carga.dart) | Carga: «Una falla de red se muestra como aviso, no como rechazo» y «Una respuesta ilegible se avisa sin dar el lote por perdido ni por recibido» ([`carga_test.dart`](../../frontend/test/features/carga_test.dart)). **Los 25 s de distractores no tienen prueba propia** (ver la sección 6) | Implementada |
| **MF-13** | I-3 | **Responde dos veces** / el docente sube dos veces | Hojas duplicadas en el almacén y, con A-02, dos calificaciones | Doble clic: el botón se deshabilita mientras sube. Lo recibido sale de la selección para no subirlo otra vez. Desde los arreglos del 19-oct, un 5xx, una respuesta cortada o un reporte ilegible dicen que algunas hojas pudieron entrar y no invitan a reintentar; antes, un 5xx decía «No se recibió ninguna hoja». **Falta**: detectar en la API una hoja ya recibida (ver la sección 4) | [`pantalla_carga.dart:140`](../../frontend/lib/features/carga/views/pantalla_carga.dart) y el comentario de la línea 153 · [`servicio_carga.dart:152`](../../frontend/lib/features/carga/data/servicio_carga.dart) | «Mientras sube muestra el progreso y no deja subir otra vez» ([`carga_test.dart:224`](../../frontend/test/features/carga_test.dart)) · «Las hojas recibidas salen de la selección para no volver a subirlas» (línea 175) · «Si algunas hojas pudieron entrar, el aviso no invita a reintentar sin más» · [`servicio_carga_test.dart`](../../frontend/test/features/servicio_carga_test.dart) | Probada en el sitio; **declarada** en la API (R-24) |

**Nota 1: por qué la carga no tiene tiempo de espera en el navegador.** Lo que tarda una carga
depende del tamaño del lote y de la red del docente, no de la API: 200 escaneos de 1 MB por una red
doméstica pueden tardar más de un minuto en subir, y cualquier límite fijo cortaría cargas que
avanzan bien. Peor, un corte del lado del navegador deja la duda de qué entró, que es justo lo que
EC-07 quiere evitar. La parte que sí depende del servidor ya está acotada: la API confirma el lote en
10 s aunque la cola no responda (MF-01) o responda tarde (MF-02). Si la red se corta, el navegador
lo informa y el aviso no invita a reenviar sin más.

**Nota 2: por qué no hay *circuit breaker* para Groq.** Se evaluó para MF-08. Un *circuit breaker*
corta las solicitudes durante un rato después de varios fallos seguidos, para no retener hilos
esperando a un proveedor que no va a contestar. Aquí el presupuesto ya hace ese trabajo: como mucho
6 solicitudes por minuto llegan al proveedor, así que en el peor caso hay 6 hilos esperando 20 s
cada minuto, de los 40 del grupo de hilos de FastAPI, y `/health` siguió en 200 en las cuatro
corridas de EC-08 con el proveedor caído o lento. El *circuit breaker* agregaría estado y un modo de
fallo propio (quedarse abierto con el proveedor ya sano) para ahorrar casi nada. **Se revisa si** el
presupuesto sube por encima de 20 por minuto, o si una medición muestra `/health` lento mientras el
proveedor falla.

## 3. Correspondencia entre lo declarado y lo implementado

Cada mitigación que algún ADR o documento del repositorio declaró, con dónde quedó.

| Mitigación declarada | Dónde se declaró | Dónde quedó | Prueba | Estado |
|---|---|---|---|---|
| Registrar la recepción antes de encolar y cortar el lote ante la cola caída | [ADR-0006](../adr/0006-registrar-la-recepcion-en-una-bitacora-antes-de-encolar.md) | `ingesta/recepcion.py`, `infraestructura/bitacora.py` | `test_durabilidad_recepcion.py` | Implementada (MF-01) |
| Una espera de conexión explícita para Redis, si la espera del cliente subía de 9 s | ADR-0006, «Qué dato haría revisar esta decisión» | `infraestructura/cola.py`, `api/main.py` | `test_modos_de_fallo.py` | Implementada en la S11 (MF-02) |
| El worker sobrevive a un fallo transitorio de Redis | arc42 §6.2, paso 6 | `worker/main.py` | `test_el_worker_sigue_vivo_si_la_cola_no_responde` | Implementada; la prueba llegó en la S11 (MF-04) |
| Un consumidor idempotente, condición para llevarlo a otra parte | [ADR-0011](../adr/0011-consumir-la-cola-desde-la-instancia-de-la-api-con-el-key-value-gratuito.md), «el worker de hoy no es idempotente» | `infraestructura/cola.py`, `worker/main.py` | `test_modos_de_fallo.py` | Implementada en la S11 (MF-03); la reconsideración está en [ADR-0017](../adr/0017-no-extraer-ningun-modulo-del-monolito-todavia.md) |
| 20 s de espera, sin reintentos y 503 ante cualquier falla del proveedor | [ADR-0013](../adr/0013-consumir-groq-detras-de-un-puerto-y-degradar-sin-bloquear-la-autoria.md) | `autoria/proveedor_llm.py`, `api/main.py` | `test_proveedor_llm.py`, `test_ruta_distractores.py`, `test_modos_de_fallo.py` | Implementada (MF-07, MF-08, MF-10) |
| Presupuesto de 6 por minuto y 150 por día, 429 sin salir a la red | [ADR-0015](../adr/0015-limitar-el-gasto-del-proveedor-de-llm-con-un-presupuesto-en-la-api.md) | `autoria/presupuesto.py`, `api/main.py` | `test_presupuesto.py`, `test_ruta_distractores.py` | Implementada (acota MF-08 y MF-09) |
| Mantener la API despierta para que `/health` responda | [ADR-0009](../adr/0009-desplegar-la-api-en-el-servicio-web-gratuito-de-render-y-mantenerla-despierta.md) y R-13 | Un monitor externo (UptimeRobot), fuera del código | No aplica: es operación | Implementada (MF-11) |
| **Acuse de recibo** en la cola | ADR-0006, alternativa B; [`aspectos.md`](../aspectos.md#a-01), A-01 paso 5: «la cola no tiene acuse de recibo» | — | — | **Pendiente, con plan** (MF-06, R-22): `BLMOVE` + `LREM` o Streams con `XACK`, al construir A-02. **Implementada en el taller de mensajería** con `BLMOVE` + `LREM` ([ADR-0020](../adr/0020-entregar-los-trabajos-al-menos-una-vez-con-reintentos-y-lista-de-fallidos.md)) |
| **Reintento automático** de las hojas `pendiente_de_encolar` | ADR-0006 y arc42 §6.2: «trabajo del aspecto A-02» | — | — | **Pendiente, con plan**: un ciclo que lea la bitácora y republique con el mismo `trabajo_id`; MF-03 ya lo hace seguro |
| **Mover la marca de idempotencia a después de procesar** | [ADR-0016](../adr/0016-acotar-la-espera-de-la-cola-y-hacer-idempotente-al-worker.md), punto 5, y el docstring del worker | — | — | **Pendiente, con plan** (R-23): al construir A-02. **Implementada en el taller de mensajería**: `ya_procesado` y `marcar_procesado` en `cola.py` ([ADR-0020](../adr/0020-entregar-los-trabajos-al-menos-una-vez-con-reintentos-y-lista-de-fallidos.md)) |
| **Detectar una hoja ya recibida** en la API | El comentario de `pantalla_carga.dart`: «el sistema no tiene forma de detectar un duplicado» | — | — | **Pendiente, con plan** (MF-13, R-24): ver la sección 4 |

Ninguna mitigación declarada quedó sin destino: o está en el código con su prueba, o tiene riesgo en
la sección 11 del arc42 y el momento en que se construye.

## 4. Idempotencia

**En la cola (construida).** La clave es el `trabajo_id`. Se acuña una sola vez, en
`preparar_trabajo`, **antes** de registrar la hoja en la bitácora (ADR-0006); por eso cualquier
republicación de esa hoja lleva el mismo identificador, y es él, y no el contenido, lo que hay que
recordar. El worker hace `SET trabajo-visto:<id> 1 NX EX 604800` antes de procesar:

- **Atómico.** `NX` hace que, entre dos workers que reciban el mismo trabajo, solo uno vea «primera
  vez». No hace falta un candado aparte.
- **Con vencimiento.** 7 días cubren de sobra la ventana en que una hoja pendiente se reintenta, y
  evitan que las marcas llenen el Key Value (del orden de cien bytes cada una).
- **Si no se puede comprobar, se procesa.** El trabajo ya salió de la cola; descartarlo sería perder
  la hoja, que es peor que procesarla dos veces. Queda el evento `idempotencia_sin_comprobar`.
- **Antes de procesar, por ahora.** Procesar hoy es escribir una línea de log, así que una caída a
  mitad no deja nada a medias. Con A-02 la marca pasa a después de terminar (R-23).
- **Después de procesar, desde el taller de mensajería** ([ADR-0020](../adr/0020-entregar-los-trabajos-al-menos-una-vez-con-reintentos-y-lista-de-fallidos.md)). Con
  acuse de recibo, un trabajo no terminado vuelve a la cola, y con la marca antes se habría
  descartado como repetido. Ya no se procesa «sin comprobar»: si Redis falla, el trabajo sigue en
  curso y vuelve a la cola cuando Redis contesta.

**En la carga (diseñada, sin construir).** Cuando la respuesta de una carga no llega, el docente no
sabe qué entró y puede volver a subir el lote. La API no lo detecta. El diseño previsto:

1. La clave de idempotencia es `(examen_id, SHA-256 del contenido)`, calculada en `ingesta` al
   validar la hoja. No hace falta que el cliente mande nada nuevo, y funciona igual si el docente
   vuelve a subir el archivo desde otra pestaña.
2. La bitácora guarda la huella junto al `trabajo_id`. Una hoja cuya huella ya está en el mismo
   examen se reporta como `ya_recibida`, con el `trabajo_id` original, y no se almacena ni se encola
   otra vez.
3. Es un cambio menor del contrato (un estado nuevo en la respuesta de la carga), y lo verifica una
   prueba que sube el mismo lote dos veces.

No se construye en la S11 porque hoy el duplicado no tiene consecuencias (el worker solo registra)
y el estado nuevo toca el contrato y la pantalla. Se construye antes de que A-02 califique.

**En la propuesta de distractores (no aplica).** La ruta no guarda estado: dos solicitudes
iguales son dos propuestas independientes, y lo único que cuesta la repetida es su cupo, que el
presupuesto cuenta (MF-09).

**Desde [ADR-0019](../adr/0019-guardar-en-cache-las-propuestas-de-distractores.md) la ruta sí guarda algo:** las propuestas que devolvió el proveedor, por
pregunta, durante 24 horas, en una caché de la memoria de la API. No es estado de ninguna hoja ni
de ningún profesor, y no cambia lo anterior: una solicitud repetida sigue sin dejar nada a medias,
y ahora además no gasta cupo. Su política de invalidación está en
[`consistencia-y-cache.md`](consistencia-y-cache.md).

<a id="saga"></a>

## 5. Por qué no hay saga

Una saga coordina una transacción que cruza varios servicios, cada uno con su propia base, como una
secuencia de pasos locales con una **compensación** para deshacer los anteriores si uno falla.
QuantIA no tiene ninguna transacción así:

- **La recepción es local y se recupera hacia adelante.** Guardar la imagen y registrarla en la
  bitácora ocurren en el mismo proceso y el mismo disco. La publicación en la cola viene después, y
  si falla no hay nada que deshacer: la hoja ya está guardada y registrada como pendiente, y lo que
  falta es terminar el paso, no compensar los anteriores. Es recuperación hacia adelante, la que
  construye ADR-0006.
- **El worker no escribe en otro servicio.** Hoy registra; con A-02 y A-03 escribirá en la base del
  mismo sistema, que es una transacción local.
- **La propuesta de distractores no deja estado** (sección 4).

**Cuándo empezaría a aplicar.** Si A-03 publicara las notas en un sistema académico externo (hoy
fuera de alcance, arc42 §3.3), o si una extracción separara la recepción y el procesamiento con
bases propias. [ADR-0017](../adr/0017-no-extraer-ningun-modulo-del-monolito-todavia.md) decide no
extraer, y uno de sus motivos es no crear ese problema antes de necesitarlo.

## 6. Qué tiene prueba y qué solo está descrito

**Con prueba automática que se pone en rojo si se quita la mitigación:** MF-01 a MF-05, MF-07 a
MF-11, y la parte del sitio de MF-13. Las nueve pruebas de `test_modos_de_fallo.py` se validaron
provocando la falla con siete mutaciones, que su docstring enumera (la espera vuelta a 10 s, la API
sin la espera corta, el cliente con 3 reintentos, sin espera de conexión, el worker sin la
comprobación, la marca sin comprobar descartando el trabajo y el adaptador del proveedor esperando
ocho veces su tiempo). La de MF-09 en `test_ruta_distractores.py` no se validó con una mutación: el
código no tiene hoy ninguna caché que quitar, y la prueba queda para que nadie agregue una sin verlo.
La caché llegó después, con ADR-0019, y esa prueba se ajustó a sabiendas: corre con una caché de
capacidad 0, y la conducta con caché la sostiene `test_cache_de_propuestas.py`, validada con sus
propias mutaciones.
Las que llegaron con los arreglos del 19-oct (sección 9) se validaron igual: cada una falla si se quita su arreglo.

**Solo descritos, sin prueba:**

- **MF-06**, el worker que muere a mitad: no hay mitigación que probar (R-22). **Ya no**: desde el
  taller de mensajería tiene mitigación y prueba (ADR-0020); la ejecución está en
  [`taller-mensajeria.md`](taller-mensajeria.md).
- **MF-12**, los 25 s del sitio para los distractores: el código los tiene, pero ninguna prueba del
  frontend hace vencer ese tiempo. Se escribe con un cliente que nunca responde y los temporizadores
  falsos de `testWidgets`, con una espera de 26 s.
- **MF-13** en la API: no está construido (R-24).
- La caída del sistema operativo durante la escritura de la bitácora, que defiende el `fsync` y solo
  se comprobaría cortándole la corriente a la máquina (lo dice ya `aspectos.md`, A-01).

## 7. Lo que encuentra una búsqueda de llamadas y de mecanismos de resiliencia

La búsqueda de llamadas a otros sistemas
`(httpx|requests\.|fetch\(|axios|HttpClient|RestTemplate|WebClient)`, fuera de `docs/`, devuelve
`httpx` en [`autoria/proveedor_llm.py`](../../backend/autoria/proveedor_llm.py) (I-2) y en tres
herramientas de medición de `backend/herramientas/`, que no son parte del sistema en operación. **No
encuentra las otras dos integraciones**, porque usan otras bibliotecas: I-1 usa `redis-py`
(`redis.Redis.from_url` en `cola.py`) e I-3 usa `package:http` de Dart (`http.get`, `http.post` y
`http.MultipartRequest`). Por eso la sección 1 las nombra con su archivo.

La búsqueda de mecanismos `(retry|backoff|circuit|timeout|deadline|idempoten)`, fuera de `docs/`,
encuentra los de la tabla: `cola.py` (las esperas, `Retry(NoBackoff(), 0)` y `primera_entrega`),
`worker/main.py` (la idempotencia), `proveedor_llm.py` (los 20 s), `autoria/presupuesto.py` y
`api/main.py` (`Retry-After`), `ingesta/recepcion.py` (el corte del lote y, desde los arreglos del 19-oct, su
plazo), `servicio_salud.dart` (5 s), `servicio_distractores.dart` (25 s y `Retry-After`) y sus
pruebas.
Lo que dice `retry` en este código es casi siempre lo contrario de un reintento: `Retry(NoBackoff(),
0)` y `Retry-After` existen para **no** reintentar a ciegas.

## 8. Cómo se reproduce

Desde `backend/`, con Redis disponible (`docker compose up -d redis`):

```
pytest -v tests/test_modos_de_fallo.py tests/test_durabilidad_recepcion.py tests/test_proveedor_llm.py tests/test_ruta_distractores.py
```

Sin Redis corren todas menos la de «responde dos veces», que se salta con un mensaje. Las cifras de
MF-02 (10,012 s y 10,017 s antes; 2,004 s y 2,017 s después) se tomaron en la máquina de desarrollo
con el mismo servidor que no contesta de `test_modos_de_fallo.py`, llamando a `publicar` y a
`recibir_lote` con 200 hojas a través de `obtener_cliente_cola()`, primero sobre `58147b8` y después
sobre el código de la S11. Son tiempos de la biblioteca, sin la red ni la lectura de los archivos de
una carga real, así que son una cota inferior de lo que vería el docente; lo que importa es que
antes la espera sola ya pasaba el techo, y ahora deja 8 s de margen.

## 9. Lo que cambió con los arreglos del 19-oct

Al revisar el código de `98a9dcc`, el commit de la S11, se vio que tres mitigaciones de esta
tabla cubrían menos de lo que decían. Se corrigieron con su prueba, cada una validada provocando la
falla, y la tabla de la sección 2 ya está al día.

| Modo | Lo que faltaba | Arreglo |
|---|---|---|
| **MF-02** | La espera de 2 s es por llamada: una cola que contesta cada `RPUSH` en 1,9 s nunca falla, y el lote de 200 tardaba unos 380 s, todo encolado | Un plazo de 8 s para todo el lote (`PLAZO_PARA_ENCOLAR_SEGUNDOS`: los 10 s de EC-07 menos la espera de una publicación); vencido, lo que falta queda pendiente |
| **MF-05** | Un `TimeoutError` al consumir pasaba por cola vacía, sin aviso ni pausa. En Windows, un Redis ausente en `localhost` da `TimeoutError` y no `ConnectionError` | El error sube al worker, que lo registra como `fallo_de_la_cola` y espera 5 s |
| **MF-13** | Un 5xx decía «No se recibió ninguna hoja» e invitaba a reintentar, aunque el proxy de Render puede devolver 502 o 504 con el lote en curso | Un 4xx dice que no entró ninguna hoja; un 5xx, que algunas pudieron entrar, y el aviso no invita a reintentar |

Los mismos arreglos corrigieron tres fallos cercanos que no son de una integración, porque del otro lado
está el disco o la propia API:

- **Un error del almacén o de la bitácora tumbaba el lote entero** con un 500, aunque las hojas
  anteriores ya estaban en la cola: es MF-01 con otro colaborador. Ahora esa hoja se rechaza con un
  motivo que dice que no entró, y el lote sigue.
- **`cargar_hojas` confirmaba el lote dentro del event loop** y congelaba la API mientras tanto,
  `/health` incluido (R-21). Ahora corre en un hilo aparte.
- **El lote se leía entero a memoria**, sin tope, en una ruta pública. Ahora se lee de a una hoja,
  con un tope de 20 MB por hoja.

Cada arreglo es un commit propio, con lo que corrige y su prueba en la descripción.
