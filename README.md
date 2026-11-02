# QuantIA

QuantIA califica exámenes de opción múltiple de cálculo diferencial: el profesor registra su
banco y su clave, aplica el examen en papel y sube los escaneos; el sistema lee las marcas (OMR),
califica contra esa clave y devuelve a revisión manual toda marca dudosa. Como apoyo opcional,
propone **distractores diagnósticos** con un modelo de lenguaje. Apoya el criterio del profesor,
no lo reemplaza.

## Equipo

Sebastián Cañas Plata (`scp1109`) · Josué David Ortega De Arco (`josueacademico17-source`) ·
María Del Mar Restrepo Licona (`Mariadelmar-restrepo`) · Susana Marcela Rosales Castellar
(`SusanaRosales`).

## Entorno desplegado

| Pieza | URL |
|---|---|
| Sitio (frontend) | https://calificacion.iscoutb.dev |
| API | https://api-calificacion.iscoutb.dev · salud en `/health` · métricas en `/metricas` |
| Revisión desplegada | https://calificacion.iscoutb.dev/revision.txt |

En el servidor del laboratorio del curso, desde `deploy/compose.lab.yaml`. El panel lee la rama
`despliegue`, que el CI publica solo si las pruebas pasan ([ADR-0021](docs/adr/0021-desplegar-en-el-servidor-del-laboratorio-con-el-sitio-compilado-en-el-ci.md)).
Detalle en [Entorno desplegado, en detalle](#entorno-desplegado-en-detalle).

## Evidencia S13: modelado de amenazas

- **Amenazas:** 15, con STRIDE sobre el Nivel 2 del C4, cada una con probabilidad, impacto,
  mitigación, dueño y estado (`docs/evidencia/modelo-de-amenazas.md`). La primera, AM-01, la carga
  pública que llenaba el disco compartido, se cerró: 250 hojas por lote, 256 MB por día y 100 MB por
  petición (ADR-0022).
- **Dependencias:** OSV-Scanner en el CI, antes de publicar el despliegue. `certifi` vulnerable,
  corregido; 0 en el frontend.
- **Privacidad:** la hoja, el nombre del archivo y la IP del docente, con base en la Ley 1581 y la
  autorización que recoge la UTB (arc42 §8.7). Aceptadas, con su motivo: arc42 §11.1.

| Qué | Dónde |
|---|---|
| Tabla de amenazas, plan, componente generativo, dependencias y privacidad | [`modelo-de-amenazas.md`](docs/evidencia/modelo-de-amenazas.md) |
| La mitigación estructural | [ADR-0022](docs/adr/0022-poner-un-presupuesto-de-carga-delante-del-almacen.md) · [`test_presupuesto_de_carga.py`](backend/tests/test_presupuesto_de_carga.py) |
| Análisis de dependencias en el pipeline | job `dependencias` de [`ci.yml`](.github/workflows/ci.yml) · [run](https://github.com/ISCOUTB/AS_202620_Sistema-de-calificacion-automatica/actions/runs/41328819502) |
| Arquitectura de seguridad, privacidad y amenazas aceptadas | [arc42 §8.6](docs/arc42/arc42-template-ES.md#86-seguridad), [§8.7](docs/arc42/arc42-template-ES.md#87-privacidad-y-datos-personales) y [§11.1](docs/arc42/arc42-template-ES.md#111-amenazas-aceptadas-s13) |

## Evidencia: consistencia de los datos y caché

Lo que se entrega: la tabla operación → garantía de consistencia, el diseño de una caché con su
política de invalidación y el ADR de la decisión de datos más costosa de revertir. Las tres cosas
están en el código, con pruebas, y no solo en los documentos.

- **Tabla operación → consistencia** ([`consistencia-y-cache.md`](docs/evidencia/consistencia-y-cache.md), sección 2): diez
  operaciones, C-01 a C-10, cada una con la garantía que da, la que **no** da, el archivo y la
  línea, y la prueba. Por ejemplo: lo confirmado al docente ya está escrito con `fsync`; la carga es
  atómica por hoja y no por lote; la cola va detrás de la bitácora y nunca al revés; el worker
  procesa como mucho una vez por trabajo; el presupuesto es linealizable dentro del proceso.
- **La decisión de datos más costosa de revertir** ([ADR-0018](docs/adr/0018-dar-a-la-hoja-una-identidad-propia-y-derivar-su-estado-de-la-bitacora.md)): la **identidad de la hoja**.
  El ADR recorre las demás decisiones de datos con lo que costaría revertir cada una, y esta es la
  única que no está detrás de un puerto y cuyo costo crece con cada registro. Hasta ahora era
  implícita (el `trabajo_id`) y no dejaba recalificar una hoja sin chocar con la idempotencia de
  ADR-0016. Se separa un `hoja_id` propio y la bitácora pasa a ser la fuente de verdad del estado.
- **Caché con su invalidación** ([ADR-0019](docs/adr/0019-guardar-en-cache-las-propuestas-de-distractores.md)): las propuestas del proveedor de LLM se guardan
  24 horas, y la misma pregunta repetida no llama al proveedor ni gasta cupo. Se invalida por
  versión (el modelo y la huella de las instrucciones van en la clave), por tiempo, por capacidad y
  a pedido del profesor («Pedir otras propuestas» manda `otras: true`). Se guarda sin filtrar, así
  que la regla corre en cada lectura. Nunca guarda el estado de una hoja.
- **Probado:** 19 pruebas nuevas, validadas provocando la falla con diez mutaciones; el contrato
  pasa a 1.4.0, solo agregando.

| Lo que se pide | Dónde está |
|---|---|
| Tabla operación → garantía de consistencia | [`consistencia-y-cache.md`](docs/evidencia/consistencia-y-cache.md), sección 2, filas C-01 a C-10, cada una con su prueba |
| Diseño de caché con su política de invalidación | [`consistencia-y-cache.md`](docs/evidencia/consistencia-y-cache.md), sección 3 · [ADR-0019](docs/adr/0019-guardar-en-cache-las-propuestas-de-distractores.md) · [`autoria/cache.py`](backend/autoria/cache.py) · [`test_cache_de_propuestas.py`](backend/tests/test_cache_de_propuestas.py) (13 pruebas, una mutación por regla) |
| ADR de la decisión de datos más costosa de revertir | [ADR-0018](docs/adr/0018-dar-a-la-hoja-una-identidad-propia-y-derivar-su-estado-de-la-bitacora.md), con la tabla que compara lo que costaría revertir cada decisión de datos · [`test_identidad_de_la_hoja.py`](backend/tests/test_identidad_de_la_hoja.py) (6 pruebas) |
| Correspondencia con el repositorio | Cada fila de la tabla cita archivo, línea y prueba; el código está en `ingesta/recepcion.py`, `infraestructura/bitacora.py`, `autoria/cache.py` y `api/main.py`, y el contrato en [`openapi.json`](docs/contrato/openapi.json) 1.4.0 |
| Documentación sincronizada | arc42 §5.1, §6.2, §6.4, §8.3, §8.5 (nueva), §9 y §11 (R-26 y R-27) · [C4](docs/c4/doc-c4.md) Nivel 2, relación 8, y Nivel 3, relaciones 3, 11 y 12 · [`aspectos.md`](docs/aspectos.md), filas A-01 y A-06 |
| Uso de IA | [`docs/ia.md`, entrada 17](docs/ia.md#entrada-17) |

## Evidencia S11: fallos parciales y decisión de extracción

La integración principal es la **cola de trabajos** (API → Redis → worker): toda hoja aceptada pasa
por ella. La S11 la recorrió con los tres casos que pide, y también las otras dos integraciones, el
proveedor de LLM y el sitio frente a la API.

- **Tabla de modos de fallo** ([`modos-de-fallo.md`](docs/evidencia/modos-de-fallo.md)): 13 modos, MF-01 a MF-13, cada uno con
  su mitigación, el archivo y la línea, la prueba y su estado. 10 tienen prueba automática; MF-12
  está implementado sin prueba de su espera, MF-13 está probado solo en el sitio, y MF-06 (el
  worker que muere a mitad) y la detección de duplicados en la API quedan declarados, con riesgo y
  plan.
- **Encontrado al medir:** con Redis lento, un lote de 200 hojas tardaba **10,017 s** en
  confirmarse, fuera del techo de 10 s de EC-07. Con [ADR-0016](docs/adr/0016-acotar-la-espera-de-la-cola-y-hacer-idempotente-al-worker.md), **2,017 s**.
- **Idempotencia:** el worker procesa una sola vez el trabajo que la cola entrega dos veces, con
  `SET trabajo-visto:<id> NX EX`. No hay saga: ninguna transacción cruza servicios, y la recepción
  se recupera hacia adelante desde la bitácora.
- **Decisión de extracción:** [ADR-0017](docs/adr/0017-no-extraer-ningun-modulo-del-monolito-todavia.md), **no extraer ningún módulo todavía**, evaluado
  contra tres opciones de extracción con siete criterios, y con los datos que lo harían revisar.
- **CI:** el paso «Modos de fallo de las integraciones (S11)» de [`ci.yml`](.github/workflows/ci.yml).

| Lo que pide la S11 | Dónde está |
|---|---|
| Tabla de modos de fallo de la integración principal: no responde, responde tarde, responde dos veces | [`modos-de-fallo.md`](docs/evidencia/modos-de-fallo.md), sección 2: MF-01 a MF-06 para la cola, y MF-07 a MF-13 para el proveedor de LLM y el sitio |
| Una mitigación asignada a cada modo | La misma tabla, columnas «Mitigación asignada», «Dónde está» y «Prueba» |
| Correspondencia entre lo declarado y lo implementado, o lo pendiente con plan | [`modos-de-fallo.md`](docs/evidencia/modos-de-fallo.md), sección 3 · riesgos R-22 a R-25 en el [arc42 §11](docs/arc42/arc42-template-ES.md#11-risks-and-technical-debts) |
| Diseño de idempotencia o saga, o por qué no aplica | [`modos-de-fallo.md`](docs/evidencia/modos-de-fallo.md), secciones 4 y 5 · [ADR-0016](docs/adr/0016-acotar-la-espera-de-la-cola-y-hacer-idempotente-al-worker.md) |
| ADR de extraer o no extraer, con criterios | [ADR-0017](docs/adr/0017-no-extraer-ningun-modulo-del-monolito-todavia.md): cuatro opciones, siete criterios, «no extraer» con sus motivos y sus disparadores |
| arc42 §11 con los modos de fallo | R-22 a R-25 en el [arc42 §11](docs/arc42/arc42-template-ES.md#11-risks-and-technical-debts), y el recorrido en [§6.6](docs/arc42/arc42-template-ES.md#66-fallos-parciales-de-las-integraciones-s11--adr-0016) |
| `aspectos.md` al día | Filas [A-01](docs/aspectos.md#a-01) y [A-06](docs/aspectos.md#a-06), con sus subsecciones de la S11 |
| Los modos de fallo probados, no solo listados | [`test_modos_de_fallo.py`](backend/tests/test_modos_de_fallo.py) (9 pruebas en la S11, validadas provocando la falla con 7 mutaciones; 12 desde los arreglos del 19-oct) y la columna «Prueba» de la tabla |
| Documentación sincronizada | arc42 §5.1, §6.2, §6.6, §8.4, §9 y §11 · [C4](docs/c4/doc-c4.md) Nivel 2, relaciones 4 y 5, y Nivel 3, relaciones 5 y 6 · [`aspectos.md`](docs/aspectos.md) |
| Uso de IA | [`docs/ia.md`, entrada 15](docs/ia.md#entrada-15) |

## Segundo corte: límite de costo

Escenario operativo del segundo corte: **límite de costo**. `POST /distractores` es pública y cada
solicitud gasta cuota de la capa gratuita de Groq (R-17). La pregunta es qué hace el MVP desplegado
cuando alguien la golpea con una ráfaga.

- **Línea base, en el entorno desplegado:** de 20 solicitudes seguidas, las 20 llegaron a Groq y 8
  terminaron en 503 porque el proveedor cortó por cuota. Durante ese minuto la ruta quedó inutilizable
  para cualquier otro profesor.
- **Decisión, [ADR-0015](docs/adr/0015-limitar-el-gasto-del-proveedor-de-llm-con-un-presupuesto-en-la-api.md):**
  un presupuesto de 6 solicitudes por minuto y 150 por día en la memoria de la API, delante del
  adaptador de Groq. Lo que no cabe se responde con 429 y `Retry-After`, sin salir a la red. Precisa
  a ADR-0013 sin reemplazarlo.
- **Observabilidad:** el evento `presupuesto_agotado` en el registro JSON y `GET /metricas`, con el
  contrato en 1.2.0.
- **Resultado desplegado** ([experimento](docs/evidencia/experimento-presupuesto.md), con
  hipótesis, montaje, umbrales y límites): de 20 solicitudes, 6 llegaron a Groq, 0 cortadas por
  cuota (antes 8) y 14 con 429 de la API (p95 0,121 s); `/health` en 200. Cumple los cuatro
  umbrales. Una corrida local con proveedor simulado aísla la variación de Groq.
- **CI:** el paso «Escenario del segundo corte (presupuesto del proveedor de LLM)» de
  [`ci.yml`](.github/workflows/ci.yml).

| Fila del reto | Dónde está |
|---|---|
| Escenario y su medida | [EC-09 en el arc42](docs/arc42/arc42-template-ES.md#ec-09) · recorrido en [§6.5](docs/arc42/arc42-template-ES.md#65-ráfaga-contra-la-ruta-de-distractores-ec-09--adr-0015) |
| Decisión | [ADR-0015](docs/adr/0015-limitar-el-gasto-del-proveedor-de-llm-con-un-presupuesto-en-la-api.md), que precisa a [ADR-0013](docs/adr/0013-consumir-groq-detras-de-un-puerto-y-degradar-sin-bloquear-la-autoria.md) |
| Código | [`autoria/presupuesto.py`](backend/autoria/presupuesto.py) · [`api/main.py`](backend/api/main.py) (429 y `GET /metricas`) · [`api/esquemas.py`](backend/api/esquemas.py) (contrato 1.2.0) |
| Pruebas y pipeline | [`test_presupuesto.py`](backend/tests/test_presupuesto.py) · [`test_ruta_distractores.py`](backend/tests/test_ruta_distractores.py) · paso propio en [`ci.yml`](.github/workflows/ci.yml) |
| Experimento | [`experimento-presupuesto.md`](docs/evidencia/experimento-presupuesto.md), con los informes [`presupuesto-antes.json`](docs/evidencia/presupuesto-antes.json), [`presupuesto-despues.json`](docs/evidencia/presupuesto-despues.json), [`presupuesto-local-antes.json`](docs/evidencia/presupuesto-local-antes.json) y [`presupuesto-local-despues.json`](docs/evidencia/presupuesto-local-despues.json) |
| Observabilidad | https://quantia-utb-api.onrender.com/metricas y el evento `presupuesto_agotado` en los logs de `quantia-utb-api` |
| Documentación sincronizada | arc42 §3, §5, §6.5, §7, §8, §9, §10 ([EC-09](docs/arc42/arc42-template-ES.md#ec-09)) y §11 (R-17 mitigado; R-18 a R-21, con las divergencias conocidas en R-20) · [C4](docs/c4/doc-c4.md) Nivel 2, relación 8, y Nivel 3, relación 12 · [`aspectos.md`](docs/aspectos.md#a-06) |
| Uso de IA | [`docs/ia.md`, entrada 13](docs/ia.md#entrada-13) |

## Evidencia S9

Porción construida con IA: **RF-11, distractores diagnósticos** (aspecto A-06), en
`backend/autoria/` y la ruta `POST /distractores` (contrato 1.1.0).

- **Código:** `autoria/distractores.py` (la regla), `autoria/proveedor_llm.py` (el adaptador) y
  `api/main.py`, en los commits `e81dbce` a `12ba9d6`.
- **Cadena:** fila A-06 de `docs/aspectos.md`, de RF-11 a EC-08, C4, ADR, código, pruebas y evidencia.
- **ADR-0013:** Groq detrás de un puerto de `autoria`, sin dependencias nuevas, 20 s sin
  reintentos y 503 si falla.
- **Prueba que falla:** PR #1, cerrado sin fusionar; runs 37243370215 y 37244214146 en rojo, con
  4 pruebas.
- **EC-08 medido:** M1, 0 de 120 propuestas repiten la correcta; M2, p95 de 2,91 s (≤ 15 s); M3,
  503 en 20,25 s (≤ 21 s).
- **`docs/ia.md`, entrada 12:** rechazados el SDK `openai`, `urllib` y los reintentos, con su motivo.
- **`docs/evidencia/auditoria-s9.md`:** sin cruces de contexto ni de propiedad (un flanco de
  `test_fronteras.py`, corregido); sin dependencias nuevas, las directas verificadas en PyPI; sin
  credenciales.
- **Componente generativo:** 20 preguntas; 44 de 60 propuestas válidas y 0 equivalentes; US$0 en
  la capa gratuita y US$0,0004 por solicitud; C4 Nivel 2, relación 8.

Los enlaces, fila por fila:

| Fila de la ficha | Dónde está |
|---|---|
| Porción real y su cadena completa | [A-06 en `aspectos.md`](docs/aspectos.md#a-06): RF-11 → [EC-08](docs/arc42/arc42-template-ES.md#ec-08) → C4 → ADR → código → pruebas → evidencia |
| ADR con la decisión del equipo | [ADR-0013](docs/adr/0013-consumir-groq-detras-de-un-puerto-y-degradar-sin-bloquear-la-autoria.md): Groq detrás de un puerto de `autoria`, `httpx` sin dependencias nuevas, 20 s de espera sin reintentos y 503 ante cualquier falla |
| Prueba que falla ante el defecto | [El PR del defecto](https://github.com/ISCOUTB/AS_202620_Sistema-de-calificacion-automatica/pull/1), cerrado sin fusionar, y su [procedimiento con los runs](docs/evidencia/prueba-distractores-falla.md): sin el filtro de la respuesta correcta fallan 4 pruebas |
| Medición de EC-08 | [Evaluación](docs/evidencia/evaluacion-distractores.md): M1, ninguna de las 120 propuestas entregadas repite la respuesta correcta (0 %) · M2, p95 de la latencia de 2,91 s contra un techo de 15 s, en 40 solicitudes · M3, con el proveedor caído o lento la ruta responde 503 en 20,25 s como máximo, contra 21 s |
| Componente generativo evaluado | Conjunto de 20 preguntas ([`conjunto-evaluacion-distractores.json`](docs/evidencia/conjunto-evaluacion-distractores.json)), resultados ([`evaluacion-distractores.json`](docs/evidencia/evaluacion-distractores.json)), calidad: 44 de 60 propuestas diagnósticas válidas (73 %), ninguna equivalente a la respuesta correcta, y el error más común es la etiqueta (8 incorrectas y 4 a medias); costo: US$0 en la capa gratuita (al precio de pago serían US$0,0004 por solicitud y US$0,008 por examen de 20 preguntas); el proveedor en el [C4 Nivel 2, relación 8](docs/c4/doc-c4.md#relaciones-1) |
| `ia.md` con lo aceptado, lo corregido y lo rechazado | [Entrada 12](docs/ia.md#entrada-12) |
| Auditoría de erosión, dependencias y credenciales | [`auditoria-s9.md`](docs/evidencia/auditoria-s9.md): sin cruces de contexto ni de propiedad; un flanco de la prueba de fronteras, corregido; sin dependencias nuevas; sin credenciales. Los dos `git log -S` del CONTRATO §9 devuelven un solo commit, `49ae0c0`: es esa auditoría, que cita los comandos textualmente, no una clave |
| ADR aceptados no reescritos | [ADR-0014](docs/adr/0014-dejar-constancia-del-ajuste-de-enlaces-en-adr-0007.md) deja constancia del ajuste de enlaces de ADR-0007 |

## Dónde está la evidencia de cada entrega

La documentación larga vive en pocos archivos. Esta tabla dice, para lo que pide cada ficha, en
qué archivo y en qué sección está.

| Entrega | Qué | Dónde |
|---|---|---|
| Corte 1 | Medición de EC-07 antes y después del cambio, con su herramienta | [`docs/evidencia/medicion-ec07.md`](docs/evidencia/medicion-ec07.md) |
| S6 | Mapa de contextos y lenguaje ubicuo | [arc42 §8.1 y §8.2](docs/arc42/arc42-template-ES.md#81-mapa-de-contextos) |
| S6 | Tabla módulo → dato, recorrido de la auditoría y violaciones V-1 a V-5 con su plan | [arc42 §8.3](docs/arc42/arc42-template-ES.md#83-propiedad-de-datos) |
| S6 | Contexto del mapa que realiza cada aspecto | [`docs/aspectos.md`](docs/aspectos.md#tabla-de-trazabilidad) · [ADR-0007](docs/adr/0007-declarar-los-contextos-delimitados-y-la-regla-de-dueno-unico.md) |
| S6 | Hallazgos de SonarQube Cloud y sus correcciones | [`docs/evidencia/hallazgos-y-correcciones.md`](docs/evidencia/hallazgos-y-correcciones.md) |
| S7 | Contrato OpenAPI versionado (1.0.0) | [`docs/contrato/openapi.json`](docs/contrato/openapi.json) |
| S7 | Prueba de contrato y su paso propio en el pipeline | [`backend/tests/test_contrato.py`](backend/tests/test_contrato.py) · paso «Prueba de contrato (OpenAPI)» de [`ci.yml`](.github/workflows/ci.yml) |
| S7 | La prueba falla ante un cambio incompatible, con los tres runs | [`docs/evidencia/prueba-de-contrato-falla.md`](docs/evidencia/prueba-de-contrato-falla.md) |
| S7 | Flujos de interacción | [arc42 §6](docs/arc42/arc42-template-ES.md#6-runtime-view) |
| S7 | C4 Nivel 2 con protocolo y formato en cada relación | [`docs/c4/doc-c4.md`](docs/c4/doc-c4.md#nivel-2--diagrama-de-contenedores) |
| S9 | Porción construida con IA, prueba que falla, EC-08, auditoría y componente generativo | [Evidencia S9](#evidencia-s9) |
| Corte 2 | Escenario operativo de límite de costo: decisión, experimento, CI, observabilidad y documentación sincronizada | [Segundo corte](#segundo-corte-límite-de-costo) |
| S11 | Modos de fallo de las integraciones, idempotencia, saga y decisión de no extraer | [Evidencia S11](#evidencia-s11-fallos-parciales-y-decisión-de-extracción) |
| Consistencia y caché | Tabla operación → consistencia, caché con su invalidación y ADR de la decisión de datos más costosa de revertir | [Evidencia: consistencia de los datos y caché](#evidencia-consistencia-de-los-datos-y-caché) |
| Taller de mensajería | Contrato del mensaje, entrega al menos una vez, duplicados, reintentos, seguimiento y ADR frente a la alternativa síncrona | [`docs/evidencia/taller-mensajeria.md`](docs/evidencia/taller-mensajeria.md) · [ADR-0020](docs/adr/0020-entregar-los-trabajos-al-menos-una-vez-con-reintentos-y-lista-de-fallidos.md) |
| Despliegue en iscoutb.dev | Revisión desplegada, comprobación desde fuera de la universidad, recorrido de una hoja de la API al worker y límites de memoria medidos | [`docs/evidencia/despliegue-iscoutb.md`](docs/evidencia/despliegue-iscoutb.md) · [ADR-0021](docs/adr/0021-desplegar-en-el-servidor-del-laboratorio-con-el-sitio-compilado-en-el-ci.md) |
| S13 | Amenazas priorizadas con su mitigación, análisis de dependencias y privacidad | [Evidencia S13](#evidencia-s13-modelado-de-amenazas) |
| Todas | Pipeline de integración continua | [Runs de GitHub Actions](https://github.com/ISCOUTB/AS_202620_Sistema-de-calificacion-automatica/actions) |
| Todas | Análisis estático y su *Quality Gate* | [SonarQube Cloud](https://sonarcloud.io/summary/new_code?id=ISCOUTB_AS_202620_Sistema-de-calificacion-automatica) |
| Todas | Respuesta a la retroalimentación automática | [`correcciones.md`](correcciones.md) |

## Entorno desplegado, en detalle

El servidor del laboratorio del curso, en iscoutb.dev, desde el 29-oct-2026
([ADR-0021](docs/adr/0021-desplegar-en-el-servidor-del-laboratorio-con-el-sitio-compilado-en-el-ci.md)).
Solo se cargan hojas sintéticas, nunca hojas de estudiantes (RNF-12): el servidor no hace copias de
seguridad y borra los volúmenes después del 30-nov-2026.

| | |
|---|---|
| Sitio | https://calificacion.iscoutb.dev |
| API y *health check* | https://api-calificacion.iscoutb.dev/health → `200 {"status":"ok"}`. La raíz de la API responde 404 porque no existe `GET /` |
| Revisión desplegada | https://calificacion.iscoutb.dev/revision.txt: el commit de `master` que está corriendo, escrito por el CI al compilar el sitio |
| Comprobación desde fuera de la universidad | 2026-10-29, de 23:30 a 00:05 (−05:00), internet residencial: `/health` con mediana de 0,28 s y p95 de 0,53 s en 30 peticiones; el sitio, CORS y los certificados, bien ([evidencia](docs/evidencia/despliegue-iscoutb.md)) |
| Infraestructura como código | [`deploy/compose.lab.yaml`](deploy/compose.lab.yaml) (servidor) · [`deploy/sitio/Dockerfile`](deploy/sitio/Dockerfile) · [`docker-compose.yml`](docker-compose.yml) (local) · [`backend/Dockerfile`](backend/Dockerfile) · [`ci.yml`](.github/workflows/ci.yml) |
| Cómo recrearlo | [Cómo se despliega](#cómo-se-despliega) |
| Pipeline | [Runs de `master`](https://github.com/ISCOUTB/AS_202620_Sistema-de-calificacion-automatica/actions/workflows/ci.yml?query=branch%3Amaster). Si las pruebas pasan, el job `publicar-despliegue` compila el sitio y publica la rama `despliegue`, que es la que despliega el panel |
| Recursos | 4 de los 6 contenedores de la cuota (`api`, `worker`, `redis` con AOF y `web`) y 576 MB de 1 GB, con límites medidos |
| Logs estructurados | Una línea JSON por evento, con `logging.config.dictConfig`, en [`backend/infraestructura/registro.py`](backend/infraestructura/registro.py). Líneas reales abajo |
| Métrica y escenario | `duracion_confirmacion_ms` del evento `lote_confirmado` ↔ [EC-07](docs/arc42/arc42-template-ES.md#ec-07) (confirmación ≤ 10 s, 0 % de pérdida). En la primera carga en este servidor: 7,9 ms. El presupuesto del proveedor de LLM, en https://api-calificacion.iscoutb.dev/metricas (EC-09) |
| Seguimiento de un mensaje | `trabajo_publicado` en la API, `trabajo_tomado` y `hoja_recibida` en el worker, con el mismo `trabajo` y la misma `hoja`, juntados por `herramientas/seguir_trabajo.py` ([evidencia](docs/evidencia/despliegue-iscoutb.md)) |
| Secretos | Ninguno en el código: [`.env.example`](.env.example) para lo local y [`deploy/.env.example`](deploy/.env.example) para el servidor. En el panel, *Environment* guarda `ALLOWED_ORIGIN` y `LLM_API_KEY`, y el compose las lee como `${VARIABLE}` |
| Costo mensual | US$0 para el equipo: el servidor lo paga el curso. La parte que nos corresponde, con la lista de precios de Oracle, es de unos US$2 al mes; lo primero que se rompe es la CPU de la API con cinco lotes a la vez ([estimación](docs/despliegue/costo-mensual.md)) |
| arc42 | [§7 Deployment View](docs/arc42/arc42-template-ES.md#7-deployment-view) · [§2.2, RNF-16](docs/arc42/arc42-template-ES.md#22-restricciones-organizativas) |
| ADR de plataforma | [0021](docs/adr/0021-desplegar-en-el-servidor-del-laboratorio-con-el-sitio-compilado-en-el-ci.md), que reemplaza a 0009 a 0012 |

Líneas reales del log en el entorno desplegado (API y worker; el panel muestra el de cada
contenedor por separado):

    {"momento": "2026-10-30T04:38:08.792+00:00", "nivel": "INFO", "registro": "ingesta", "mensaje": "Trabajo publicado", "evento": "trabajo_publicado", "trabajo": "b4f7061e-4444-4f6e-a132-f8e929c38047", "hoja": "ff64200e-7ffc-4b60-ae67-28fe3b1b0c68", "examen": "Calculo 2", "cola": "procesamiento"}
    {"momento": "2026-10-30T04:38:08.793+00:00", "nivel": "INFO", "registro": "worker", "mensaje": "Hoja recibida", "evento": "hoja_recibida", "trabajo": "b4f7061e-4444-4f6e-a132-f8e929c38047", "hoja": "ff64200e-7ffc-4b60-ae67-28fe3b1b0c68", "intento": 1, "examen": "Calculo 2", "archivo": "hoja-real.png", "referencia": "Calculo_2-20b4f352/35158635-8806-469c-8522-416de15e71e2-hoja-real.png", "bytes": 74}
    {"momento": "2026-10-30T04:38:08.793+00:00", "nivel": "INFO", "registro": "api", "mensaje": "Lote confirmado", "evento": "lote_confirmado", "examen": "Calculo 2", "hojas_aceptadas": 1, "hojas_pendientes_de_encolar": 0, "hojas_rechazadas": 1, "duracion_confirmacion_ms": 7.9}

### El entorno anterior: Render (S8)

Del 27-sep al 29-oct el sistema corrió en la capa gratuita de Render, desde [`render.yaml`](render.yaml)
(ADR-0009 a ADR-0012, reemplazados por ADR-0021). Sigue arriba, sin cambios, hasta que el docente
confirme las filas de despliegue de la S8 y el taller.

| | |
|---|---|
| Sistema y API | https://quantia-utb.onrender.com · https://quantia-utb-api.onrender.com/health |
| Comprobación de la S8 | 2026-09-27, 18:59 (−05:00), internet residencial en Cartagena: sitio `http=200 tiempo=0,37 s` · API `health=200 tiempo=0,20 s` |
| Escenario del segundo corte | Límite de costo sobre `POST /distractores`: presupuesto de 6 por minuto y 150 por día, 429 si no cabe, y su estado en https://quantia-utb-api.onrender.com/metricas ([ADR-0015](docs/adr/0015-limitar-el-gasto-del-proveedor-de-llm-con-un-presupuesto-en-la-api.md)) |
| Taller de despliegue | Condición: **patrón de carga**, definida por el equipo por indicación del docente. Pieza: **la API**. Arranque en frío medido: **12,5 s** frente a los 10 s de EC-07; con el monitor que la mantiene despierta, 0,2 a 0,4 s ([comparación](docs/despliegue/taller-despliegue-api.md) · [medición](docs/evidencia/medicion-arranque-en-frio.json) · [ADR-0009](docs/adr/0009-desplegar-la-api-en-el-servicio-web-gratuito-de-render-y-mantenerla-despierta.md)) |

## Cómo se arranca

Requiere Docker (con el plugin Compose). Antes de la primera vez, copiar `.env.example` a `.env`.
Solo hace falta editarlo para probar la ruta de distractores: ahí va `LLM_API_KEY`, la clave del
proveedor de LLM, que nunca se versiona (RNF-11). Sin ella, esa ruta responde 503 y lo demás
funciona igual. Ahí están también `LLM_SOLICITUDES_POR_MINUTO` y `LLM_SOLICITUDES_POR_DIA`, el
presupuesto del proveedor (ADR-0015), que no hace falta tocar.

Desde la raíz del repositorio:

```
docker compose up
```

Levanta, con un solo comando, la aplicación web (FastAPI, puerto 8000), un worker que comparte
el mismo código de dominio que la API, la cola de trabajos (Redis), la base de datos (Postgres,
todavía sin esquema) y el frontend (Flutter compilado a estáticos, servido en el puerto 8080).
La primera construcción es lenta por el SDK de Flutter de la etapa de build del frontend; no
está colgado. Para reconstruir tras cambiar código: `docker compose up --build`.

- API: http://localhost:8000 (documentación interactiva en `/docs`, salud en `/health`).
- Frontend: http://localhost:8080.

Alternativas para desarrollo, que no reemplazan el comando oficial de arriba:
- Backend sin Docker: `docker compose up -d redis postgres` y luego, dentro de `backend/` con un
  entorno virtual, `pip install -r requirements.txt` y `uvicorn api.main:app --reload`.
- Frontend con recarga en caliente: dentro de `frontend/`,
  `flutter run -d chrome --dart-define=BACKEND_URL=http://localhost:8000`, sin reconstruir la
  imagen en cada cambio.

## Cómo se despliega

El entorno desplegado es el servicio `sistema` del proyecto `calificacion` en el panel del servidor
del laboratorio (https://panel.iscoutb.dev), al que entra cualquier integrante con su correo
institucional ([ADR-0021](docs/adr/0021-desplegar-en-el-servidor-del-laboratorio-con-el-sitio-compilado-en-el-ci.md)).
Desde la red de la UTB no abre, porque ahí `*.iscoutb.dev` no resuelve. Para dejarlo configurado
desde cero:

1. En el panel, proyecto `calificacion` → `production` → `sistema`, pestaña **General → Provider**:
   este repositorio, rama `despliegue` y *Compose Path* `./deploy/compose.lab.yaml`. **Save**.
2. **Environment**: `ALLOWED_ORIGIN=https://calificacion.iscoutb.dev` y `LLM_API_KEY` con la clave de
   Groq, que no se versiona. *Create Environment File* encendido. **Save**.
3. **Domains**, dos dominios con HTTPS y Let's Encrypt: `calificacion.iscoutb.dev` al servicio `web`,
   puerto 8080, y `api-calificacion.iscoutb.dev` al servicio `api`, puerto 8000.
4. **General**: *Autodeploy* encendido y **Deploy**. En **Deployments**, esperar *Done*.
5. Comprobar desde fuera de la universidad el `/health` de la API, el sitio y `revision.txt`;
   cargar una hoja sintética desde el sitio y seguirla con `herramientas/seguir_trabajo.py` en los
   **Logs** de `api` y `worker`.

La rama `despliegue` no se edita a mano: el job `publicar-despliegue` de `ci.yml` la vuelve a crear
en cada push a `master` cuyas pruebas pasan, como `master` más el sitio compilado. Desde ahí, cada
push así se despliega solo. Los pasos para levantar el compose del servidor en un computador están
en el encabezado de [`deploy/compose.local-override.yaml`](deploy/compose.local-override.yaml).

## Corte vertical: carga de examen (aspecto A-01)

Del sistema hay **dos aspectos construidos de punta a punta**, y los demás solo declarados. El
otro es A-06, la porción de la [Evidencia S9](#evidencia-s9). Este es
[A-01, la carga de examen para calificación](docs/aspectos.md#a-01), que realiza RF-01: el
docente sube las hojas escaneadas de un examen y el sistema le confirma cuáles recibió y cuáles
no, con el motivo de cada rechazo.

Se eligió construir este primero porque es el punto de entrada del flujo —sin una hoja cargada
no hay nada que calificar— y porque no depende de las partes de mayor riesgo técnico: no hace
falta haber elegido el algoritmo de OMR ni el umbral de confianza para que funcione.

El recorrido atraviesa todas las capas, que es lo que lo hace un corte vertical y no una capa
horizontal:

```
navegador (Flutter)  ->  POST /examenes/{id}/hojas  ->  ingesta         (valida formato)
                                                    ->  infraestructura (almacena y encola)
                                                    ->  worker          (desencola y registra)
```

### Cómo recorrerlo

Con el sistema levantado (`docker compose up --build`), crea dos archivos de prueba: uno válido
y otro que finja serlo.

```bash
# una imagen PNG valida de 8x8 pixeles (o usa cualquier foto, escaneo o PDF propio)
base64 -d > /tmp/hoja-real.png <<'FIN'
iVBORw0KGgoAAAANSUhEUgAAAAgAAAAICAIAAABLbSncAAAAEUlEQVR4nGOQqziBFTEMLQkABkZXgRDDjAEAAAAASUVORK5CYII=
FIN

# un archivo de texto al que solo se le puso extension .jpg
echo "esto no es una imagen" > /tmp/hoja-falsa.jpg
```

En `http://localhost:8080`, escribe un identificador de examen (por ejemplo `CALC-2026-01`),
selecciona los dos archivos y súbelos. La respuesta separa lo recibido de lo rechazado:

```
Se procesaron 2 archivo(s)
Recibidas: 1
  hoja-real.png    En cola · trabajo 2eede6b8-dd9f-4db6-a3ab-6205644ea416
Rechazadas: 1
  hoja-falsa.jpg   El contenido no corresponde a un JPG; puede que el archivo
                   esté dañado o que se le haya cambiado la extensión.
```

Ese rechazo es el que muestra que la validación **lee los primeros bytes y no la extensión**: el
archivo se llama `.jpg` y aun así no pasa. Comprobarlo importa porque un archivo que se cuela
por tener el nombre correcto reaparece como error dentro del worker, cuando ya no hay a quién
avisarle.

Para ver el otro extremo del recorrido:

```
docker compose logs worker
```

```
Hoja recibida | trabajo=2eede6b8-dd9f-4db6-a3ab-6205644ea416 examen=CALC-2026-01
               archivo=hoja-real.png referencia=CALC-2026-01/e6c7e4cc-...-hoja-real.png
```

El identificador de trabajo es el mismo que muestra la pantalla. Esa coincidencia es la prueba
de que el recorrido se completó: la hoja pasó del navegador a la API, de ahí al volumen de
imágenes y a la cola de Redis, y de ahí a un proceso distinto en otro contenedor.

### Qué falta de este aspecto

El worker registra la hoja y ahí termina, porque el paso siguiente es el aspecto A-02 (detección
de marcas), que todavía no existe. La política de retención de imágenes que exige RNF-14 tampoco
está implementada: hoy nada borra lo que se guarda.

El almacenamiento y la bitácora de recepción están **detrás de sendos puertos** en
`infraestructura`, con adaptadores en disco declarados provisionales. Es deliberado: el corte
necesitaba guardar archivos sin cerrar de paso la decisión de persistencia, que sigue abierta
como riesgo R-06 del arc42. Cuando se escriba ese ADR, lo que cambia son los adaptadores;
`ingesta`, el modelo de datos y las pruebas del aspecto no se tocan.

El reintento de las hojas que quedaron `pendiente_de_encolar` **no está automatizado**:
`bitacora.pendientes()` deja el dato listo y consumirlo es trabajo del aspecto A-02.

## Cómo se prueba

Backend (dentro de `backend/`, con Redis disponible vía `docker compose up -d redis` o local):

```
pytest
```

Son 213. Verifican: que la aplicación FastAPI arranca y su endpoint de salud responde
200; que los siete módulos del dominio se importan sin error ni ciclos; que ningún módulo
importa por fuera de lo declarado en el docstring de su `__init__.py` (la prueba de fronteras
entre módulos); que un trabajo encolado en Redis se recupera igual al desencolarlo; y, para el
aspecto A-01, que se aceptan los formatos declarados, que cada rechazo lleva motivo legible, que
ningún archivo del lote desaparece del reporte, que se encola un trabajo por hoja aceptada y
ninguno por rechazada, y que un nombre de archivo con rutas no escapa del directorio del examen.

Trece de ellas llegaron con [ADR-0006](docs/adr/0006-registrar-la-recepcion-en-una-bitacora-antes-de-encolar.md)
y cubren el caso que rompía EC-07: la cola que se cae con el lote a medio procesar. Verifican que
ninguna hoja queda sin reportar, que la que no se encoló queda pendiente en la bitácora con su
imagen recuperable, que el estado se relee desde el archivo y no de la memoria, que una línea
truncada no inutiliza el registro, y que el lote deja de insistir contra una cola caída en vez de
pagar el tiempo de espera de conexión doscientas veces.

Cuarenta y cuatro llegaron con la porción de la S9 (aspecto A-06). Verifican que ninguna
propuesta que repita la respuesta correcta llega al profesor, aunque esté escrita distinto; que
al proveedor de LLM solo le llega la pregunta (RNF-13); que el tiempo agotado, la cuota agotada,
la clave rechazada y una respuesta ilegible terminan en un 503 con su motivo; y que ningún
módulo del dominio importa `api` ni `worker`. Ninguna sale a la red.

Doce llegaron con el segundo corte (EC-09, ADR-0015). Verifican que el presupuesto admite hasta su
límite por minuto y corta la siguiente, que la ventana se libera de a una solicitud, que el límite
por día corta aunque el minuto tenga cupo, que una solicitud cortada no llama al proveedor, que el
429 trae `Retry-After`, que sin proveedor configurado no se gasta cupo, y que `GET /metricas` publica
lo mismo que vio el cliente. Usan un reloj falso, así que no esperan un minuto, y tampoco salen a la
red.

Una llegó con el frontend nuevo: que el navegador puede leer `Retry-After` en el 429. CORS solo
deja leer las cabeceras que la API declara, y sin esa el sitio no sabría cuánto esperar.

Diez llegaron con la S11 (modos de fallo, ADR-0016), casi todas en
[`backend/tests/test_modos_de_fallo.py`](backend/tests/test_modos_de_fallo.py). Contra un servidor
que acepta la conexión y no contesta, verifican que publicar se rinde en menos de 3 s, que un lote
de 100 hojas confirma dentro de los 10 s con todas pendientes en la bitácora, que el cliente de
Redis no reintenta por su cuenta, que `desencolar` no se cuelga y que el adaptador del proveedor de
LLM se corta en su espera. Contra un Redis real, que el mismo trabajo publicado dos veces se procesa
una sola vez. Y que el worker sobrevive a un fallo de Redis, que procesa igual si no puede comprobar
la marca, y que la misma solicitud de distractores repetida no deja estado y gasta su propio cupo.
Se validaron provocando la falla con siete mutaciones, que el docstring del archivo enumera.

Veintisiete llegaron con los arreglos del 19-oct. Verifican que un error
del almacén o de la bitácora rechaza esa hoja y no tumba el lote; que una cola que contesta lento
no saca el lote del techo de EC-07, porque el lote tiene un plazo además de la espera por llamada;
que el lote se confirma fuera del bucle de eventos (R-21) y se lee de a una hoja, con un tope de
20 MB; que un nombre largo se acorta y dos exámenes no comparten carpeta; que una espera vencida al
consumir llega al worker como fallo de la cola; que la API reusa un solo cliente de Redis y busca a
Redis en el mismo lugar que el worker; que el filtro de distractores iguala `2x` con `2·x` y `sen`
con `sin`, y no pierde un distractor que vale 0; y que las herramientas de medición solo cuentan lo
que dicen contar. Cada una falla si se quita su arreglo.

Diecinueve llegaron con la entrega de consistencia y caché. Seis, en
[`backend/tests/test_identidad_de_la_hoja.py`](backend/tests/test_identidad_de_la_hoja.py),
verifican que cada hoja tiene un `hoja_id` propio, distinto de su `trabajo_id`; que el reporte, la
bitácora y el trabajo de la cola dicen el mismo; que la bitácora lo conserva al releerse, también en
las líneas escritas antes (ADR-0018); y que la API lo publica. Trece, en
[`backend/tests/test_cache_de_propuestas.py`](backend/tests/test_cache_de_propuestas.py), verifican
que la pregunta repetida sale de la caché sin llamar al proveedor ni gastar cupo, y cada regla de
invalidación de ADR-0019: el cambio de modelo o de instrucciones, las 24 horas que leer no renueva,
la capacidad, «Pedir otras propuestas», que no se guardan fallas ni respuestas vacías y que la regla
corre en cada lectura. Se validaron provocando la falla con diez mutaciones, que los dos docstrings
enumeran.

Diecisiete llegaron con la S13 (ADR-0022), en
[`backend/tests/test_presupuesto_de_carga.py`](backend/tests/test_presupuesto_de_carga.py).
Verifican que un lote con más hojas que el tope, o que no cabe en el cupo de bytes de las últimas
24 horas, no entra entero y no deja nada en el almacén, la bitácora ni la cola; que el 429 dice
cuándo cabrá contando solo los lotes que hace falta que salgan; que la ventana libera el cupo al
cumplir un día; que `GET /metricas` publica lo cargado y lo cortado; y que ningún cuerpo de más
del tope llega a la ruta, lo declare o no. Se validaron provocando la falla con seis mutaciones,
que el docstring enumera; una no pone ninguna en rojo, y el docstring dice por qué.

Seis son la **prueba de contrato** ([`backend/tests/test_contrato.py`](backend/tests/test_contrato.py)),
y verifican que el documento de `docs/contrato/openapi.json` y la API que corre no se puedan
separar: que el archivo versionado sea exactamente el que genera la aplicación de hoy, que su
número de versión sea el declarado en el código, que sigan estando las cuatro rutas (y que la de
distractores publique su 503 y su 429), que la
respuesta de carga exija sus cuatro campos, que los estados publicados sean los dos del dominio,
y que una respuesta real traiga exactamente los campos que el contrato anuncia, ni uno más ni
uno menos.

Un cambio incompatible las pone en rojo diciendo qué se rompió. Renombrar `nombre_archivo`
produce:

```
El contrato versionado ya no describe a esta aplicacion:
  esquema cambiado: HojaAceptadaEnRespuesta (campos quitados: ['nombre_archivo']; nuevos: ['archivo'])
```

Que falla de verdad no es una afirmación: se comprobó rompiendo el contrato en `master` y
mirando el pipeline. El experimento, con los tres runs y la salida completa, está en
[`docs/evidencia/prueba-de-contrato-falla.md`](docs/evidencia/prueba-de-contrato-falla.md).

Tres más verifican que la herramienta que mide EC-07 siga corriendo contra el código de hoy
([`backend/tests/test_medir_ec07.py`](backend/tests/test_medir_ec07.py)). La herramienta es la
evidencia reproducible del escenario, y ya dejó de correr una vez sin que nada lo detectara.

Sin Redis levantado, la prueba de encolado se salta con un mensaje que dice qué levantar, en vez
de fallar con un error de conexión confuso. Las demás corren igual.

La prueba de contrato lee `docs/contrato/openapi.json` desde la raíz del repositorio, así que se
corre fuera de la imagen, como la corre el pipeline. Dentro de un contenedor construido desde
`backend/` (por ejemplo, con `docker compose run api pytest`) ese archivo no existe y sus seis
pruebas terminan en error.

Frontend (dentro de `frontend/`):

```
flutter test
```

Son 73, una carpeta por pantalla en `test/features/` más `test/app_test.dart`:

- **Marco de la aplicación (6):** la barra superior refleja el estado de conexión con el backend
  y ofrece volver a comprobar; la navegación es un riel en escritorio y una barra en teléfono; y
  cambiar de sección no pierde lo escrito en otra.
- **Carga (18):** el botón de subir sigue deshabilitado hasta que haya examen y archivos, y sin
  conexión; el reporte lista las aceptadas y las rechazadas con su motivo; una hoja
  `pendiente_de_encolar` se muestra como pendiente; una falla de red o una respuesta ilegible
  se avisan sin dar el lote por perdido ni por recibido; y un 5xx dice que algunas hojas pudieron
  entrar, sin invitar a reintentar. Cuatro de ellas prueban el servicio contra un `MockClient`,
  incluido que el examen viaje codificado en la ruta.
- **Pauta y distractores (27):** el 503 y el 429 se muestran como advertencias con el mensaje de
  la API; con el límite por minuto hay cuenta regresiva, y con el diario no se ofrece repetir y el
  botón de pedir vuelve cuando pasa la espera. Diez de ellas prueban el servicio contra un
  `MockClient`, código por código, y una, que «Pedir otras propuestas» manda `otras: true`.
- **Panel (11) y Revisión (11):** avisan que usan datos de ejemplo (en Revisión, también que un
  veredicto no se guarda) y no se desbordan a 390 px; el Panel tampoco ofrece acciones de IA
  fuera del alcance, y su porcentaje de aprobación no divide por cero.

Ninguna toca la red ni el diálogo de archivos del navegador: las pantallas reciben esas
operaciones inyectadas y las pruebas les pasan sustitutos.

Estas mismas pruebas corren en cada push y pull request vía `.github/workflows/ci.yml`.

### Cómo se mide el escenario EC-07

Las dos cifras del escenario (confirmación del lote en ≤10 s y 0 % de pérdida silenciosa) se
miden con una herramienta versionada, sin Docker ni Redis:

```
cd backend
python -m herramientas.medir_ec07 --hojas 200 --kb 200 --repeticiones 3 --fallar-en 100
```

El resultado, el procedimiento y sus límites están en
[`docs/evidencia/medicion-ec07.md`](docs/evidencia/medicion-ec07.md).

## El contrato de la API

Lo que la API promete devolver está escrito en un documento OpenAPI versionado en el
repositorio: [`docs/contrato/openapi.json`](docs/contrato/openapi.json), en la versión 1.5.0.
Describe las cuatro rutas con el esquema de cada respuesta campo por campo, no solo el listado de
endpoints. La 1.2.0 agregó `GET /metricas` y el 429 de `/distractores` (segundo corte, ADR-0015).
La 1.3.0 agregó el `hoja_id` de cada hoja aceptada (ADR-0018), y la 1.4.0, la caché de propuestas:
`otras` en la solicitud de distractores, `desde_la_cache` en su respuesta y su estado en
`/metricas` (ADR-0019). La 1.5.0 agregó el presupuesto de carga: el 413 y el 429 de la ruta de
carga y su estado en `/metricas` (ADR-0022). Las tres solo agregan.

Está versionado y no se consulta en caliente por dos razones. `/openapi.json` solo existe
mientras la API está levantada y describe la versión que esté corriendo en ese momento, así que
ni un consumidor que quiera generar su cliente ni un revisor que quiera ver qué prometía la API
en un commit dado pueden usarlo. Y con el documento dentro del repositorio, un cambio
incompatible deja de ser invisible: aparece como un diff en ese archivo.

**No se edita a mano.** Se genera desde la aplicación con una herramienta versionada, igual que
las cifras de EC-07:

```
cd backend
python -m herramientas.exportar_contrato
```

La salida es determinista (claves ordenadas, indentación fija), de modo que dos exportaciones
del mismo código producen el mismo archivo. Si tras regenerar el diff sale vacío, el contrato no
cambió; si sale con cambios, hay que revisarlos uno por uno antes de commitear, porque un campo
que desaparece o un tipo que se estrecha rompen a quien ya consume la API.

`docs/contrato/` guarda documentos de contrato generados, uno por interfaz. Hoy solo está la
interfaz HTTP; la del sistema con la cola de trabajos todavía no está descrita.

## Restricciones y decisiones clave

Las restricciones completas, clasificadas en técnicas, organizativas y legales, están en la [sección 2 del arc42](docs/arc42/arc42-template-ES.md). Las principales:

- Solo evalúa exámenes de opción múltiple con hoja de respuestas de formato fijo; no procesa desarrollo libre.
- Dominio acotado a cálculo diferencial: límites, derivadas y simplificaciones algebraicas.
- Usuarios: profesores y TAs autenticados. El estudiante no interactúa con el sistema, solo es la fuente de las marcas en la hoja.
- Los resultados se presentan en un dashboard interactivo, no como archivo aislado ni salida de consola.
- Las calificaciones y los escaneos son datos personales de estudiantes: su tratamiento se rige por el régimen colombiano de protección de datos, y ningún dato personal se envía al proveedor de LLM.
- El stack está limitado a las opciones del curso. Se eligió FastAPI en el backend, porque el ecosistema de OpenCV solo existe con madurez en Python, y Flutter en el frontend, por la experiencia previa del equipo.
- El modelo de lenguaje no participa en la calificación: es una capacidad de apoyo de la fase de autoría, y el sistema funciona completo sin invocarla ([ADR-0005](docs/adr/0005-acotar-el-llm-a-la-generacion-de-distractores-diagnosticos.md)).

## Objetivos de calidad

- **Precisión:** ≥98% de exactitud en la detección de marcas OMR; 100% de los exámenes habilitados con aprobación manual registrada de la clave de respuestas.
- **Rendimiento:** ≤5 segundos por examen individual (percentil 95); requiere procesamiento en paralelo, no secuencial, para que un lote de 200 hojas quepa en ≤10 minutos.
- **Degradación controlada:** toda marca con confianza <70% se envía a revisión manual; el sistema detecta correctamente ≥99% de esos casos ambiguos.
- **Seguridad:** un profesor solo accede a los datos de los cursos que tiene autorizados.

## Metodología

El desarrollo sigue Aspect Driven Development (ADD): cada funcionalidad se declara como un aspecto que se puede trazar de principio a fin, desde el requisito hasta la evidencia de que funciona (ver [`docs/aspectos.md`](docs/aspectos.md)).

## Decisiones de arquitectura

| ADR | Título | Estado |
|---|---|---|
| [0001](docs/adr/0001-usar-monolito-modular.md) | Arquitectura de Monolito Modular | reemplazado por 0002 |
| [0002](docs/adr/0002-procesar-calificacion-de-forma-asincrona.md) | Procesar la calificación de forma asíncrona sobre el monolito modular | aceptado |
| [0003](docs/adr/0003-usar-fastapi-y-flutter.md) | Usar FastAPI en el backend y Flutter en el frontend | aceptado |
| [0004](docs/adr/0004-quitar-validacion-simbolica-obligatoria-de-la-clave.md) | Quitar la validación simbólica obligatoria de la clave de respuestas | aceptado |
| [0005](docs/adr/0005-acotar-el-llm-a-la-generacion-de-distractores-diagnosticos.md) | Acotar el LLM a la generación de distractores diagnósticos | aceptado |
| [0006](docs/adr/0006-registrar-la-recepcion-en-una-bitacora-antes-de-encolar.md) | Registrar la recepción en una bitácora antes de encolar | aceptado |
| [0007](docs/adr/0007-declarar-los-contextos-delimitados-y-la-regla-de-dueno-unico.md) | Declarar los contextos delimitados y la regla de dueño único de los datos | aceptado |
| [0008](docs/adr/0008-renombrar-el-sistema-a-quantia.md) | Renombrar el sistema a QuantIA | aceptado |
| [0009](docs/adr/0009-desplegar-la-api-en-el-servicio-web-gratuito-de-render-y-mantenerla-despierta.md) | Desplegar la API en el servicio web gratuito de Render y mantenerla despierta | reemplazado por 0021 |
| [0010](docs/adr/0010-servir-el-sitio-como-archivos-estaticos-en-render.md) | Servir el sitio como archivos estáticos en Render | reemplazado por 0021 |
| [0011](docs/adr/0011-consumir-la-cola-desde-la-instancia-de-la-api-con-el-key-value-gratuito.md) | Consumir la cola desde la instancia de la API con el Key Value gratuito | reemplazado por 0021 |
| [0012](docs/adr/0012-mantener-el-almacen-en-el-disco-efimero-de-la-instancia-hasta-cerrar-r-06.md) | Mantener el almacén en el disco efímero de la instancia hasta cerrar R-06 | reemplazado por 0021 |
| [0013](docs/adr/0013-consumir-groq-detras-de-un-puerto-y-degradar-sin-bloquear-la-autoria.md) | Consumir Groq detrás de un puerto y degradar sin bloquear la autoría | aceptado |
| [0014](docs/adr/0014-dejar-constancia-del-ajuste-de-enlaces-en-adr-0007.md) | Dejar constancia del ajuste de enlaces en ADR-0007 | aceptado |
| [0015](docs/adr/0015-limitar-el-gasto-del-proveedor-de-llm-con-un-presupuesto-en-la-api.md) | Limitar el gasto del proveedor de LLM con un presupuesto en la API | aceptado |
| [0016](docs/adr/0016-acotar-la-espera-de-la-cola-y-hacer-idempotente-al-worker.md) | Acotar la espera de la cola y hacer idempotente al worker | aceptado |
| [0017](docs/adr/0017-no-extraer-ningun-modulo-del-monolito-todavia.md) | No extraer ningún módulo del monolito todavía | aceptado |
| [0018](docs/adr/0018-dar-a-la-hoja-una-identidad-propia-y-derivar-su-estado-de-la-bitacora.md) | Dar a la hoja una identidad propia y derivar su estado de la bitácora | aceptado |
| [0019](docs/adr/0019-guardar-en-cache-las-propuestas-de-distractores.md) | Guardar en caché las propuestas de distractores | aceptado |
| [0020](docs/adr/0020-entregar-los-trabajos-al-menos-una-vez-con-reintentos-y-lista-de-fallidos.md) | Entregar los trabajos al menos una vez, con reintentos y lista de fallidos | aceptado |
| [0021](docs/adr/0021-desplegar-en-el-servidor-del-laboratorio-con-el-sitio-compilado-en-el-ci.md) | Desplegar en el servidor del laboratorio, con el sitio compilado en el CI | aceptado |
| [0022](docs/adr/0022-poner-un-presupuesto-de-carga-delante-del-almacen.md) | Poner un presupuesto de carga delante del almacén | aceptado |

Las decisiones de un ADR aceptado no se editan ni se borran: si una decisión cambia, se escribe uno nuevo y el anterior pasa a estado *reemplazado por*. Los ajustes menores que no son de arquitectura, como un enlace roto, se permiten dejando constancia ([ADR-0014](docs/adr/0014-dejar-constancia-del-ajuste-de-enlaces-en-adr-0007.md)).

## Estado actual

- [x] Aspectos A-01 (carga de examen) y A-06 (distractores diagnósticos) construidos de punta a punta;
  A-02 a A-05 declarados
- [x] arc42: objetivos de calidad, restricciones clasificadas y contexto
- [x] arc42: estrategia de solución, decisiones de arquitectura y riesgos
- [x] arc42: Building Block View, Runtime View y Cross-cutting Concepts (secciones 5, 6 y 8)
- [x] arc42: Deployment View (sección 7)
- [x] Escenarios de calidad: 5 priorizados y 4 complementarios; EC-07, EC-08 y EC-09 medidos
- [x] C4 Niveles 1, 2 y 3
- [x] ADR 0001 a 0022
- [x] Elección de stack: FastAPI en el backend, Flutter en el frontend
- [x] Esqueleto ejecutable
- [x] Corte vertical de A-01: `ingesta`, almacén, bitácora, encolado y pantalla de carga
- [x] Contrato de la API (OpenAPI) versionado y su prueba en el pipeline
- [x] Despliegue con URL pública, logs estructurados y métrica de EC-07: en Render desde la S8 y en
  el servidor del laboratorio (iscoutb.dev) desde el 29-oct, con la cola y las hojas persistentes
  (ADR-0021)
- [ ] ADR de persistencia y almacenamiento (riesgo R-06); el adaptador actual es provisional
- [ ] Modelo de datos compartido más allá de lo que A-01 necesitó
- [x] Proveedor de LLM: Groq, detrás de un puerto de `autoria` (ADR-0013)
- [x] Segundo corte: presupuesto del proveedor de LLM, `GET /metricas` y experimento de EC-09 (ADR-0015)
- [x] S11: modos de fallo de las tres integraciones, esperas acotadas de la cola y worker idempotente (ADR-0016); decisión de no extraer (ADR-0017)
- [x] Arreglos del 19-oct: el lote ya no se cae por un error del disco,
  tiene un plazo para la cola, no congela la API (R-21 cerrado) y se lee de a una hoja con tope
- [x] Acuse de recibo, reintentos y lista de fallidos en la cola (ADR-0020, R-22 cerrado)
- [ ] Detección de hojas subidas dos veces (R-24, con A-02)
- [x] Consistencia y caché: tabla operación → consistencia, `hoja_id` propio con la bitácora como
  fuente de verdad (ADR-0018) y caché de propuestas con su invalidación (ADR-0019)
- [ ] Consulta del estado vigente de una hoja (R-26, con A-02)
- [x] S13: modelo de amenazas con STRIDE sobre el C4, análisis de dependencias en el pipeline,
  presupuesto de carga (ADR-0022) y privacidad
- [ ] Autenticación (A-05), antes de la primera hoja real (AM-02); análisis de las imágenes base
  (R-34)
- [ ] Aspectos A-02 a A-05

## Documentación

```
docs/
├── arc42/
│   └── arc42-template-ES.md                            # documento de arquitectura (arc42)
├── adr/                                                # 0001 a 0022; el 0001, reemplazado por el 0002, y del 0009 al 0012, por el 0021
├── c4/
│   └── doc-c4.md                                       # modelo C4 (Niveles 1, 2 y 3)
├── contrato/
│   └── openapi.json                                    # contrato HTTP (OpenAPI 3.1), generado
├── despliegue/                                        # estimación de costo y taller de despliegue
├── evidencia/                                          # EC-07, arranque en frío, prueba de contrato, SonarQube; de la S9: EC-08, prueba del defecto y auditoría; del corte 2: experimento de EC-09; de la S11: modos de fallo; de consistencia y caché: la tabla de garantías y el diseño de la caché; del taller de mensajería: su ejecución; del despliegue en iscoutb.dev: la verificación; de la S13: el modelo de amenazas
├── ficha-problema.md                                   # el problema, usuarios y alcance
├── aspectos.md                                         # aspectos y tabla de trazabilidad
└── ia.md                                               # registro de uso de IA
```

En la raíz, [`correcciones.md`](correcciones.md) responde a la retroalimentación automática del
curso. El registro de uso de IA está en [`docs/ia.md`](docs/ia.md) y la ficha del problema en
[`docs/ficha-problema.md`](docs/ficha-problema.md).
