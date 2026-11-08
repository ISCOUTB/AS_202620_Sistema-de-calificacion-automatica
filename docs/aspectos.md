# Aspectos del sistema

Este documento registra los aspectos identificados para **QuantIA**
(calificación automática de exámenes de opción múltiple de cálculo diferencial mediante
reconocimiento óptico de marcas, contra la clave que el profesor registra y habilita de forma
explícita), siguiendo la metodología de Aspect Driven Development del curso.

Desde [ADR-0005](adr/0005-acotar-el-llm-a-la-generacion-de-distractores-diagnosticos.md) el
modelo de lenguaje **no participa en la calificación**: es una capacidad opcional de la fase de
autoría que propone distractores diagnósticos cuando el profesor se los pide (RF-11), y el
sistema opera completo sin invocarla nunca.

Un aspecto es un corte vertical del sistema, con valor propio, que se puede recorrer completo:

> aspecto → requisito → elementos C4 → ADR → código → pruebas → evidencia de calidad

Cada aspecto se trabaja en siete pasos: declarar, especificar, ubicar, decidir, construir,
verificar y evidenciar.

**Documentos relacionados:** [`arc42/arc42-template-ES.md`](arc42/arc42-template-ES.md)
(requisitos `RF-nn`, restricciones `RNF-nn`, escenarios `EC-nn`) ·
[`c4/doc-c4.md`](c4/doc-c4.md) (diagramas) · [`adr/`](adr/) (decisiones).

---

## Tabla de trazabilidad

**La lectura de las hojas ([A-02](#a-02)) y su calificación ([A-03](#a-03)) están construidas**, con la revisión manual de las preguntas dudosas desde la aplicación (RF-08) ([ADR-0023](adr/0023-leer-las-hojas-en-posiciones-fijas-y-mandar-a-revision-lo-que-no-se-ve-bien.md)). Sobre 300 hojas sintéticas: EC-01, 9 406 de 9 406 marcas claras bien leídas (100 %; pide ≥98 %); EC-02, 1 026 de 1 026 marcas ambiguas a revisión (100 %; pide ≥99 %); ninguna respuesta leída mal sin aviso, tampoco en las tres fotos del prototipo (R-05). Con el sistema completo y los límites del servidor: EC-03, p95 de 1,7 s por hoja (pide ≤5 s); EC-04, 200 hojas en 3,6 min (pide ≤10 min) ([medición](evidencia/medicion-lectura-omr.md)). Falta el conjunto escaneado de R-01, calibrar el umbral con él (R-04) y saber quién resuelve cada revisión (A-05).

**La porción de la S9 es [A-06](#a-06)** (RF-11, escenario [EC-08](arc42/arc42-template-ES.md#ec-08), [ADR-0013](adr/0013-consumir-groq-detras-de-un-puerto-y-degradar-sin-bloquear-la-autoria.md)). Medida: M1, 0 de 120 propuestas repiten la respuesta correcta; M2, p95 de 2,91 s contra 15 s; M3, 503 en 20,25 s contra 21 s ([evaluación](evidencia/evaluacion-distractores.md)). La prueba falla ante el defecto en el [PR #1](https://github.com/ISCOUTB/AS_202620_Sistema-de-calificacion-automatica/pull/1) ([procedimiento](evidencia/prueba-distractores-falla.md)), y la [auditoría](evidencia/auditoria-s9.md) recorre contextos, propiedad, dependencias y credenciales.

**El escenario operativo del segundo corte es de límite de costo, sobre la misma fila [A-06](#a-06)**
(escenario [EC-09](arc42/arc42-template-ES.md#ec-09), [ADR-0015](adr/0015-limitar-el-gasto-del-proveedor-de-llm-con-un-presupuesto-en-la-api.md)): una ráfaga contra `POST /distractores`. Medido en local con un proveedor que aplica el límite de Groq, pasa de 20 solicitudes en el proveedor y 11 cortes por cuota a 6 y 0, con los 14 rechazos de la API en 2 ms de mediana ([experimento](evidencia/experimento-presupuesto.md)).

**Los fallos parciales de la S11 caen sobre [A-01](#a-01) y [A-06](#a-06)**, las dos filas
construidas ([tabla de modos de fallo](evidencia/modos-de-fallo.md)). La integración principal es la cola de A-01: con
Redis lento, un lote de 200 hojas tardaba 10,017 s en confirmarse, fuera de EC-07, y con
[ADR-0016](adr/0016-acotar-la-espera-de-la-cola-y-hacer-idempotente-al-worker.md) tarda 2,017 s; el worker procesa una sola vez el trabajo que llega dos veces.
[ADR-0017](adr/0017-no-extraer-ningun-modulo-del-monolito-todavia.md) decide no extraer ningún módulo todavía, con sus criterios.

**La entrega de consistencia y caché cae sobre las mismas dos filas** ([tabla operación →
consistencia y diseño de la caché](evidencia/consistencia-y-cache.md)). En [A-01](#a-01), [ADR-0018](adr/0018-dar-a-la-hoja-una-identidad-propia-y-derivar-su-estado-de-la-bitacora.md) separa la
identidad de la hoja (`hoja_id`) de la de su trabajo y declara la bitácora fuente de verdad de su
estado: es la decisión de datos más costosa de revertir. En [A-06](#a-06), [ADR-0019](adr/0019-guardar-en-cache-las-propuestas-de-distractores.md)
guarda 24 horas las propuestas del proveedor, y la misma pregunta repetida no gasta cupo.

**El taller de mensajería cae sobre [A-01](#a-01)**, porque su operación es la cola de trabajos,
de la API al worker ([taller](evidencia/taller-mensajeria.md)). [ADR-0020](adr/0020-entregar-los-trabajos-al-menos-una-vez-con-reintentos-y-lista-de-fallidos.md) le da al mensaje un contrato versionado y
pasa la entrega a al menos una vez, con acuse, reintentos con espera creciente y lista de fallidos;
una ejecución real con la API, el worker y Redis muestra el duplicado, el fallo recuperable y el que
termina en fallidos.

Cada fila enlaza a su escenario de calidad en el arc42. Los nueve escenarios documentados son
alcanzables desde la fila del aspecto que los realiza.

| ID | Aspecto | Estado | Requisito | Escenario de calidad | Contexto C4 (Nivel 1) | C4 | ADR | Código | Pruebas | Evidencia |
|---|---|---|---|---|---|---|---|---|---|---|
| **[A-01](#a-01)** | Carga de examen para calificación | **Construido** | RF-01 | [EC-07](arc42/arc42-template-ES.md#ec-07) | [Rel. 1](c4/doc-c4.md#relaciones): Profesor/TA → Sistema | C1: [QuantIA](c4/doc-c4.md#nivel-1--diagrama-de-contexto-del-sistema) · C2: [Aplicación web](c4/doc-c4.md#nivel-2--diagrama-de-contenedores), [Almacén de imágenes](c4/doc-c4.md#nivel-2--diagrama-de-contenedores), [Cola de trabajos](c4/doc-c4.md#nivel-2--diagrama-de-contenedores) | [0002](adr/0002-procesar-calificacion-de-forma-asincrona.md) · [0006](adr/0006-registrar-la-recepcion-en-una-bitacora-antes-de-encolar.md) · [0016](adr/0016-acotar-la-espera-de-la-cola-y-hacer-idempotente-al-worker.md) · [0018](adr/0018-dar-a-la-hoja-una-identidad-propia-y-derivar-su-estado-de-la-bitacora.md) · [0020](adr/0020-entregar-los-trabajos-al-menos-una-vez-con-reintentos-y-lista-de-fallidos.md) | [`ingesta/recepcion.py`](../backend/ingesta/recepcion.py) · [`infraestructura/almacen.py`](../backend/infraestructura/almacen.py) · [`infraestructura/bitacora.py`](../backend/infraestructura/bitacora.py) · [`infraestructura/modelo.py`](../backend/infraestructura/modelo.py) · [`api/main.py`](../backend/api/main.py) · [`frontend/lib/features/carga/views/pantalla_carga.dart`](../frontend/lib/features/carga/views/pantalla_carga.dart) · [`infraestructura/cola.py`](../backend/infraestructura/cola.py) · [`worker/main.py`](../backend/worker/main.py) · [`infraestructura/consumo.py`](../backend/infraestructura/consumo.py) · contrato del mensaje: [`trabajo-v1.schema.json`](contrato/trabajo-v1.schema.json) | [`test_recepcion.py`](../backend/tests/test_recepcion.py) · [`test_durabilidad_recepcion.py`](../backend/tests/test_durabilidad_recepcion.py) · [`test_carga_hojas.py`](../backend/tests/test_carga_hojas.py) · [`carga_test.dart`](../frontend/test/features/carga_test.dart) · [`servicio_carga_test.dart`](../frontend/test/features/servicio_carga_test.dart) · [`test_modos_de_fallo.py`](../backend/tests/test_modos_de_fallo.py) · [`test_identidad_de_la_hoja.py`](../backend/tests/test_identidad_de_la_hoja.py) · [`test_mensajeria.py`](../backend/tests/test_mensajeria.py) | [Medición de EC-07](evidencia/medicion-ec07.md): 1,744 s contra ≤10 s · 0 % de pérdida silenciosa · [captura](#a-01-evidencia) · [Modos de fallo](evidencia/modos-de-fallo.md) (S11): con la cola lenta, el lote de 200 confirma en 2,017 s (antes 10,017 s) · [Consistencia](evidencia/consistencia-y-cache.md): filas C-01 a C-05 · [Taller de mensajería](evidencia/taller-mensajeria.md): ejecución con un duplicado, un fallo recuperable y uno que termina en fallidos |
| **[A-02](#a-02)** | Detección de marcas y nivel de confianza | **Construido** | RF-02, RF-03 | [EC-01](arc42/arc42-template-ES.md#ec-01) · [EC-02](arc42/arc42-template-ES.md#ec-02) | **Sin contexto propio** — proceso interno, no cruza la frontera del sistema (ver nota abajo) | C2: [Worker → Almacén de imágenes](c4/doc-c4.md#relaciones-1) (relación 7) · C3: [`omr`](c4/doc-c4.md#nivel-3--diagrama-de-componentes) | [0023](adr/0023-leer-las-hojas-en-posiciones-fijas-y-mandar-a-revision-lo-que-no-se-ve-bien.md) · [0020](adr/0020-entregar-los-trabajos-al-menos-una-vez-con-reintentos-y-lista-de-fallidos.md) | [`omr/formato.py`](../backend/omr/formato.py) · [`omr/plantilla.py`](../backend/omr/plantilla.py) · [`omr/vision.py`](../backend/omr/vision.py) · [`omr/decision.py`](../backend/omr/decision.py) · [`omr/lectura.py`](../backend/omr/lectura.py) · [`omr/errores.py`](../backend/omr/errores.py) · [`worker/main.py`](../backend/worker/main.py) (`leer_y_calificar`) · en el sitio, [`preparacion_de_hojas.dart`](../frontend/lib/features/carga/data/preparacion_de_hojas.dart) | [`test_plantilla.py`](../backend/tests/test_plantilla.py) · [`test_vision.py`](../backend/tests/test_vision.py) · [`test_decision.py`](../backend/tests/test_decision.py) · [`test_lectura.py`](../backend/tests/test_lectura.py) · [`test_lectura_fotos_r05.py`](../backend/tests/test_lectura_fotos_r05.py) · [`test_medir_lectura.py`](../backend/tests/test_medir_lectura.py) · [`preparacion_de_hojas_test.dart`](../frontend/test/features/preparacion_de_hojas_test.dart) | [Medición de la lectura](evidencia/medicion-lectura-omr.md): EC-01, 100 % contra ≥98 % · EC-02, 100 % contra ≥99 % · 0 respuestas mal leídas sin aviso, en 300 hojas sintéticas y en las 3 fotos del prototipo (R-05) · un PNG que mataba al worker por memoria, ahora ilegible |
| **[A-03](#a-03)** | Calificación contra la clave y publicación | **Construido**, salvo las estadísticas del Panel (RF-05) | RF-04, RF-05, RF-08 | [EC-03](arc42/arc42-template-ES.md#ec-03) · [EC-04](arc42/arc42-template-ES.md#ec-04) | [Rel. 2](c4/doc-c4.md#relaciones): Sistema → Profesor/TA | C2: [Worker y Aplicación web → Almacén de imágenes](c4/doc-c4.md#relaciones-1) (relaciones 7 y 3) · C3: [`calificacion` y `dashboard`](c4/doc-c4.md#nivel-3--diagrama-de-componentes) | [0002](adr/0002-procesar-calificacion-de-forma-asincrona.md) · [0018](adr/0018-dar-a-la-hoja-una-identidad-propia-y-derivar-su-estado-de-la-bitacora.md) · [0023](adr/0023-leer-las-hojas-en-posiciones-fijas-y-mandar-a-revision-lo-que-no-se-ve-bien.md) | [`calificacion/nota.py`](../backend/calificacion/nota.py) · [`calificacion/revision.py`](../backend/calificacion/revision.py) · [`infraestructura/claves.py`](../backend/infraestructura/claves.py) · [`infraestructura/resultados.py`](../backend/infraestructura/resultados.py) · [`infraestructura/revisiones.py`](../backend/infraestructura/revisiones.py) · [`autoria/examenes.py`](../backend/autoria/examenes.py) · [`dashboard/resultados.py`](../backend/dashboard/resultados.py) · [`dashboard/revision.py`](../backend/dashboard/revision.py) · [`api/main.py`](../backend/api/main.py) (cinco rutas, contrato 1.8.0) · pantallas: [`reporte_recepcion.dart`](../frontend/lib/features/carga/views/widgets/reporte_recepcion.dart) y [`pantalla_revision.dart`](../frontend/lib/features/revision/views/pantalla_revision.dart) | [`test_calificacion.py`](../backend/tests/test_calificacion.py) · [`test_claves.py`](../backend/tests/test_claves.py) · [`test_resultados.py`](../backend/tests/test_resultados.py) · [`test_leer_y_calificar.py`](../backend/tests/test_leer_y_calificar.py) · [`test_ruta_resultados.py`](../backend/tests/test_ruta_resultados.py) · [`test_ruta_examenes.py`](../backend/tests/test_ruta_examenes.py) · [`test_revisiones.py`](../backend/tests/test_revisiones.py) · [`test_ruta_revision.py`](../backend/tests/test_ruta_revision.py) · [`test_medir_procesamiento.py`](../backend/tests/test_medir_procesamiento.py) · [`revision_test.dart`](../frontend/test/features/revision_test.dart) · [`servicio_revision_test.dart`](../frontend/test/features/servicio_revision_test.dart) · [`servicio_resultados_test.dart`](../frontend/test/features/servicio_resultados_test.dart) · [`servicio_examenes_test.dart`](../frontend/test/features/servicio_examenes_test.dart) | [Medición de la lectura](evidencia/medicion-lectura-omr.md#3-ec-03-y-ec-04-el-sistema-completo): EC-03, p95 de 1,7 s contra ≤5 s · EC-04, 200 de 200 hojas en 3,6 min contra ≤10 min · [RF-08 con las fotos del prototipo](evidencia/medicion-lectura-omr.md#4-la-revisión-manual-con-las-fotos-del-prototipo-rf-08): de 3,9 a 4,0, sin que la respuesta correcta salga de la API |
| **[A-04](#a-04)** | Registro del banco y habilitación del examen | Declarado | RF-06, RF-07 | [EC-05](arc42/arc42-template-ES.md#ec-05) | [Rel. 1](c4/doc-c4.md#relaciones): Profesor/TA → Sistema | Pendiente | [0003](adr/0003-usar-fastapi-y-flutter.md) · [0004](adr/0004-quitar-validacion-simbolica-obligatoria-de-la-clave.md) · [0005](adr/0005-acotar-el-llm-a-la-generacion-de-distractores-diagnosticos.md) | Pendiente | Pendiente | Pendiente |
| **[A-05](#a-05)** | Identidad y aislamiento por curso | Declarado | RF-09, RF-10 | [EC-06](arc42/arc42-template-ES.md#ec-06) | [Rel. 1 y 2](c4/doc-c4.md#relaciones): transversal a ambas — condición de «docente autenticado» bajo la que operan | Pendiente | ADR de auditoría previsto (RF-10) | Pendiente | Pendiente | Pendiente |
| **[A-06](#a-06)** | Propuesta de distractores diagnósticos | **Construido** | RF-11 *(opcional)* | [EC-08](arc42/arc42-template-ES.md#ec-08) · [EC-09](arc42/arc42-template-ES.md#ec-09) | [Rel. 3](c4/doc-c4.md#relaciones): Sistema → Proveedor de LLM (opcional) | C1: [Proveedor de LLM](c4/doc-c4.md#nivel-1--diagrama-de-contexto-del-sistema) · C2: [Aplicación web → Proveedor de LLM](c4/doc-c4.md#relaciones-1) (relación 8) · C3: [`autoria`](c4/doc-c4.md#nivel-3--diagrama-de-componentes) | [0005](adr/0005-acotar-el-llm-a-la-generacion-de-distractores-diagnosticos.md) · [0013](adr/0013-consumir-groq-detras-de-un-puerto-y-degradar-sin-bloquear-la-autoria.md) · [0015](adr/0015-limitar-el-gasto-del-proveedor-de-llm-con-un-presupuesto-en-la-api.md) · [0017](adr/0017-no-extraer-ningun-modulo-del-monolito-todavia.md) · [0019](adr/0019-guardar-en-cache-las-propuestas-de-distractores.md) | [`autoria/distractores.py`](../backend/autoria/distractores.py) · [`autoria/proveedor_llm.py`](../backend/autoria/proveedor_llm.py) · [`autoria/presupuesto.py`](../backend/autoria/presupuesto.py) · [`autoria/cache.py`](../backend/autoria/cache.py) · [`api/main.py`](../backend/api/main.py) (`POST /distractores` y `GET /metricas`) · pantalla: [`pantalla_pauta.dart`](../frontend/lib/features/pauta/views/pantalla_pauta.dart) y [`servicio_distractores.dart`](../frontend/lib/features/pauta/data/servicio_distractores.dart) | [`test_distractores.py`](../backend/tests/test_distractores.py) · [`test_proveedor_llm.py`](../backend/tests/test_proveedor_llm.py) · [`test_ruta_distractores.py`](../backend/tests/test_ruta_distractores.py) · [`test_presupuesto.py`](../backend/tests/test_presupuesto.py) · [`pauta_test.dart`](../frontend/test/features/pauta_test.dart) · [`servicio_distractores_test.dart`](../frontend/test/features/servicio_distractores_test.dart) · [`test_modos_de_fallo.py`](../backend/tests/test_modos_de_fallo.py) · [`test_cache_de_propuestas.py`](../backend/tests/test_cache_de_propuestas.py) | [Evaluación de EC-08](evidencia/evaluacion-distractores.md): M1: 0 de 120 propuestas repiten la respuesta correcta · M2: p95 de 2,91 s contra 15 s · M3: 503 en 20,25 s contra 21 s · [la prueba falla ante el defecto](evidencia/prueba-distractores-falla.md) · [auditoría](evidencia/auditoria-s9.md) · [Experimento de EC-09](evidencia/experimento-presupuesto.md) (segundo corte): de 20 solicitudes en el proveedor y 11 cortes por cuota a 6 y 0 · [Modos de fallo MF-07 a MF-10](evidencia/modos-de-fallo.md) (S11) · [Caché de propuestas](evidencia/consistencia-y-cache.md): filas C-07 y C-08, y su política de invalidación |

**Estados:** *Declarado* = pasos 1 y 3 parciales (nombre, para quién, qué resuelve, requisitos
y escenario asignados). *Especificado* = pasos 1 a 4 completos. *Construido* = pasos 5 a 7.

**Contexto del mapa que realiza cada aspecto.** La columna de arriba cita las relaciones del
**Nivel 1 del C4**, que describen cómo el sistema se comunica con actores externos. Los
**contextos del [mapa de contextos](arc42/arc42-template-ES.md#81-mapa-de-contextos)** son otra
cosa: son la división interna del dominio, y cada aspecto realiza uno. A-01 realiza **Ingesta**,
A-02 realiza **OMR**, A-03 realiza **Calificación** y **Dashboard** (la comparación contra la clave
y la publicación de resultados, RF-05), A-04 y A-06 realizan **Autoría** y A-05 realiza **Identidad**. El
séptimo contexto, **Infraestructura**, es de soporte y no tiene aspecto propio: interviene en A-01
pero no decide ningún campo de negocio. La correspondencia completa, en las dos direcciones, está
en la [sección 8.3 del arc42](arc42/arc42-template-ES.md#83-propiedad-de-datos), apartado «Aspectos ↔ contextos».

**Por qué A-02 queda sin relación en el Nivel 1.** Las tres relaciones del diagrama de Nivel 1
([`c4/doc-c4.md`](c4/doc-c4.md#nivel-1--diagrama-de-contexto-del-sistema)) son comunicaciones que
cruzan la frontera del sistema: el profesor que sube hojas o registra un banco (relación 1), el
sistema que devuelve notas y alertas (relación 2), y el sistema que pide distractores al LLM
(relación 3). La detección de marcas de A-02 ocurre enteramente **dentro** de la caja negra —
entre el almacén de imágenes y la cola de trabajos, disparada por el worker, no por un actor
externo— así que no hay ninguna flecha del Nivel 1 que la represente: se hace visible en el
[Nivel 3 del C4](c4/doc-c4.md#nivel-3--diagrama-de-componentes), donde `omr` es un componente del worker. A-05, en cambio, sí se ancla a las relaciones
existentes aunque no dibuje una propia: es la condición de autenticación y aislamiento por curso
bajo la que ya operan las relaciones 1 y 2 con el Profesor/TA, no una comunicación adicional que
falte por trazar. **En el mapa de contextos de §8.1, en cambio, A-02 sí tiene
contexto y es OMR**: la palabra «contexto» significa cosas distintas en el Nivel 1 del C4 y en el
mapa de contextos, y esta es la fila donde más se nota. Ver también la [sección 8.3 del arc42](arc42/arc42-template-ES.md#83-propiedad-de-datos)
para la misma trazabilidad vista desde qué módulo y qué dato realiza cada aspecto.

A-01, A-02, A-03 y A-06 son los aspectos construidos. A-04 y A-05 están declarados para fijar el
orden de trabajo y para que cada escenario de calidad tenga un aspecto responsable; cada uno se
especifica cuando se levanta lo que lo bloquea, que está escrito en su sección («Por qué no se
trabaja todavía»).

**Por qué A-01 está en «Construido».** Los pasos 5 a 7 (construir, verificar y evidenciar) están
hechos y son comprobables: el código y las pruebas están en la fila de la tabla, y las dos cifras
de EC-07 están medidas con una herramienta versionada
([`evidencia/medicion-ec07.md`](evidencia/medicion-ec07.md)): confirmación del lote en 1,744 s
contra un techo de 10 s, y 0 % de pérdida silenciosa. Lo que sigue abierto (el medio definitivo
de almacenamiento y la retención de RNF-14) depende de R-06, no de A-01.

**Por qué A-06 está en «Construido».** Los pasos 5 a 7 están hechos en la S9: el código, las
pruebas y la evaluación de EC-08 están en la fila de la tabla, y las tres medidas del escenario
se midieron con una herramienta versionada: M1, ninguna de las 120 propuestas entregadas repite la respuesta correcta (0 %); M2, p95 de la latencia de 2,91 s contra un techo de 15 s, en 40 solicitudes; M3, con el proveedor caído o lento la ruta responde 503 en 20,25 s como máximo, contra 21 s. Desde el
frontend nuevo, RF-11 también se usa desde el sitio, en la pantalla Pauta y distractores, que
explica al docente el 503 del proveedor y el 429 del presupuesto.

**Por qué A-02 y A-03 están en «Construido», y con qué salvedades.** Los pasos 5 a 7 están hechos:
el código y las pruebas están en sus filas, y los cuatro escenarios se midieron con herramientas
versionadas ([`evidencia/medicion-lectura-omr.md`](evidencia/medicion-lectura-omr.md)). Las
salvedades, que la evidencia dice con cifras:

- **EC-01 se midió sobre hojas sintéticas**, no sobre las 300 hojas escaneadas y etiquetadas a mano
  que pide el escenario (R-01). Las sintéticas miden la lógica dentro de las condiciones que se
  generaron; las tres fotos del prototipo dicen cómo se porta con una hoja real, y el umbral de 70
  no se ha calibrado con hojas reales (R-04).
- **EC-03 y EC-04 se midieron en local**, con los límites del servidor del laboratorio. EC-04 pide
  además la CPU del servidor por debajo del 85 %, y eso se mide allá.
- **De RF-05 falta el Panel**: las notas se ven por hoja en la pantalla de carga y en la de
  revisión, pero las estadísticas por pregunta y por curso siguen con datos de ejemplo.
- **RF-08 se construyó antes de A-05.** Cada resolución queda con el nombre que escribe el docente
  y la hora, pero el nombre no se verifica y las rutas son públicas. Vale solo con hojas
  sintéticas, que es la condición de la amenaza AM-02.

**Lo que todavía es maqueta.** Carga (A-01, A-02 y A-03), Revisión (RF-08) y el generador de Pauta
(A-06) llaman a la API. El Panel y la clave y el banco de Pauta muestran datos de ejemplo bajo un
aviso visible, porque las estadísticas de RF-05 y el registro de la clave (A-04) no están
construidos. Muestran cómo se van a ver, no lo que el sistema hace hoy.

---

<a id="a-01"></a>

## Aspecto A-01: Carga de examen para calificación

### 1. Declarar

- **Nombre:** Carga de examen para calificación.
- **Para quién es:** el profesor universitario o el asistente de cátedra (TA) que dicta el
  curso. El estudiante es un afectado indirecto —es su examen el que se carga— pero no es
  usuario del sistema (RNF-05).
- **Qué problema resuelve:** hace que una hoja de respuestas escaneada quede recibida,
  validada y registrada en el sistema, disponible para su procesamiento posterior. Sin este
  paso no hay ninguna imagen sobre la cual ejecutar la detección de marcas, así que todo el
  flujo de calificación depende de que este aspecto exista primero.

### 2. Especificar

**Requisito (RF-01):** el sistema debe permitir a un docente autenticado cargar exámenes
escaneados (JPG, PNG o PDF), individualmente o en lote, validar su formato y confirmar su
recepción.

**Escenario de calidad: [EC-07 · Confirmación fiable de recepción del lote](arc42/arc42-template-ES.md#ec-07)**

| Parte | Contenido |
|---|---|
| **Fuente del estímulo** | Un docente autenticado (profesor o TA). |
| **Estímulo** | Sube un lote de hasta 200 hojas de respuesta escaneadas (JPG, PNG o PDF). |
| **Artefacto** | Módulo `ingesta` (recepción, validación de formato y encolado). |
| **Ambiente** | Operación normal, en el contexto de un curso masivo al cierre de un periodo de evaluación. |
| **Respuesta** | El sistema valida el formato de cada archivo, almacena los válidos, encola su procesamiento, rechaza explícitamente los inválidos indicando el motivo, y confirma al docente qué se recibió y qué no. |
| **Medida de respuesta** | **Confirmación de recepción del lote en ≤10 segundos**, con **0% de pérdida silenciosa**: todo archivo cargado queda registrado como *aceptado* o *rechazado con motivo*; ninguno desaparece sin dejar traza. |

> **Por qué esta medida y no otra.** La confirmación de recepción es lo único que este aspecto
> puede prometer: la calificación ocurre después, de forma asíncrona (ADR-0002), así que medir
> aquí el tiempo hasta la nota mediría un aspecto distinto —eso lo cubren EC-03 y EC-04—. Lo
> que sí es responsabilidad de la carga es que nada se pierda entre el clic del docente y la
> cola de trabajo, y que el docente sepa de inmediato qué entró. La pérdida silenciosa de una
> hoja es peor que un rechazo: es un examen sin calificar que nadie sabe que falta.

### 3. Ubicar

**Nivel 1 (contexto):** el aspecto se realiza dentro de la caja «QuantIA»,
en la relación *Profesor / TA → Sistema*. Está enteramente dentro del sistema; no involucra
ningún sistema externo. Ver [`c4/doc-c4.md`](c4/doc-c4.md).

**Nivel 2 (contenedores):** el aspecto atraviesa la **aplicación web** (recepción HTTP y
validación), el **almacén de imágenes** (persistencia del archivo y de la bitácora) y la **cola
de trabajos** (encolado del procesamiento): las relaciones 1, 3, 4 y 5 del
[Nivel 2](c4/doc-c4.md#nivel-2--diagrama-de-contenedores), todas construidas.

**Módulos afectados (ADR-0002):** `ingesta` como responsable principal, `identidad` para
verificar que el docente puede cargar en ese curso, e `infraestructura` para el almacenamiento
y la cola.

### 4. Decidir

**No hay un ADR propio de este aspecto, y es una decisión consciente, no un olvido.** La
topología en la que se apoya —procesamiento asíncrono con cola, de modo que la carga confirme
recepción y no calificación— ya quedó decidida en
[ADR-0002](adr/0002-procesar-calificacion-de-forma-asincrona.md), que es una decisión de
alcance mayor.

Queda **una decisión estructural pendiente** que sí ameritará su propio ADR: **dónde y cómo se
almacenan las imágenes cargadas**, incluyendo la política de retención que exige RNF-14 (los
escaneos no pueden conservarse indefinidamente). Sigue abierta porque depende de la
decisión de persistencia (riesgo R-06 del arc42);
[ADR-0006](adr/0006-registrar-la-recepcion-en-una-bitacora-antes-de-encolar.md) decidió solo la parte de la recepción que impedía medir EC-07.

**Cómo se construyó el aspecto sin cerrar esa decisión.** El corte necesitaba guardar archivos
hoy, y elegir un almacenamiento al paso habría cerrado R-06 sin ADR. La salida es la que el
arc42 §4 ya justifica: el aislamiento hexagonal no se aplica en los siete módulos sino
**selectivamente en los dos puntos donde la matriz de estilos muestra que compensa**, y el
almacén de imágenes es uno de esos dos. Así que `infraestructura` expone el puerto
`AlmacenDeImagenes` —lo único que `ingesta` conoce— y `AlmacenEnDisco` es un adaptador
**provisional** sobre el volumen del `docker-compose.yml`. Cuando llegue el ADR de persistencia,
lo que cambia es ese adaptador; el módulo, el modelo de datos y las pruebas del aspecto no se
tocan. La política de retención de RNF-14 aterrizará también ahí, y hoy no está implementada:
nada borra lo que se guarda.

### 5. Construir

| Pieza | Dónde |
|---|---|
| Modelo de datos compartido | [`backend/infraestructura/modelo.py`](../backend/infraestructura/modelo.py) |
| Puerto de almacenamiento y adaptador provisional | [`backend/infraestructura/almacen.py`](../backend/infraestructura/almacen.py) |
| Validación, almacenamiento y encolado | [`backend/ingesta/recepcion.py`](../backend/ingesta/recepcion.py) |
| Interfaz pública del módulo (`__all__`) | [`backend/ingesta/__init__.py`](../backend/ingesta/__init__.py) |
| Endpoint `POST /examenes/{examen_id}/hojas` | [`backend/api/main.py`](../backend/api/main.py) |
| Consumo del trabajo encolado | [`backend/worker/main.py`](../backend/worker/main.py) |
| Pantalla de carga y reporte | [`frontend/lib/features/carga/views/pantalla_carga.dart`](../frontend/lib/features/carga/views/pantalla_carga.dart) |
| Llamada al endpoint | [`frontend/lib/features/carga/data/servicio_carga.dart`](../frontend/lib/features/carga/data/servicio_carga.dart) |
| Diálogo de archivos del navegador | [`frontend/lib/features/carga/data/selector_archivos.dart`](../frontend/lib/features/carga/data/selector_archivos.dart) |

Tres decisiones de construcción que conviene poder defender:

1. **La validación revisa los primeros bytes, no solo la extensión.** Renombrar un archivo es
   trivial; si el engaño pasa aquí, el error reaparece dentro del worker, cuando ya no hay a
   quién avisarle.
2. **Un archivo inválido no aborta el lote.** Doscientas hojas y una corrupta no pueden costarle
   al docente volver a subir las otras ciento noventa y nueve, que es justo lo que EC-07 quiere
   evitar. Por eso la respuesta es 200 aunque haya rechazos: la petición se atendió completa y
   el cuerpo dice archivo por archivo qué pasó.
3. **Primero se almacena, después se encola.** Al revés, el worker podría recibir un trabajo que
   apunta a una imagen que todavía no existe.

El hueco entre el guardado y el encolado lo cerró
[ADR-0006](adr/0006-registrar-la-recepcion-en-una-bitacora-antes-de-encolar.md): una hoja almacenada
cuyo trabajo no llegó a la cola queda registrada en la bitácora como pendiente, y se puede
reintentar sin pedirle el archivo al docente. Siguen abiertos el reintento automático, que no
llegó con A-02 (R-32), y el caso de una hoja que llegó a la cola pero el worker no terminó de
procesar: la cola no tenía acuse de recibo, y lo cerró ADR-0020.

El `examen_id` tampoco se verifica contra nada, porque el módulo `autoria` (aspecto A-04) es el
que registrará los exámenes y aún no existe. La ruta ya tiene su forma definitiva para que
cuando A-04 llegue solo haya que sumar la comprobación.

### 6. Verificar

**60 pruebas automatizadas de este aspecto**: 42 en el backend y 18 en el frontend, en
[`carga_test.dart`](../frontend/test/features/carga_test.dart) y
[`servicio_carga_test.dart`](../frontend/test/features/servicio_carga_test.dart). (La suite del
frontend tiene 72; las demás son de las otras tres pantallas y del marco de la aplicación.) Trece
de las del backend llegaron con [ADR-0006](adr/0006-registrar-la-recepcion-en-una-bitacora-antes-de-encolar.md)
y cubren el caso que antes rompía EC-07: la cola que se cae con el lote a medio procesar. Once más
y cinco del frontend llegaron con los arreglos del 19-oct: las seis
últimas filas de la tabla.

| Prueba | Qué sostiene | Archivo |
|---|---|---|
| Acepta los formatos declarados | RF-01: JPG, PNG y PDF | [`test_recepcion.py`](../backend/tests/test_recepcion.py) |
| Rechaza con motivo legible | Un rechazo sin motivo es indistinguible de una pérdida | [`test_recepcion.py`](../backend/tests/test_recepcion.py) |
| Ningún archivo del lote desaparece | La medida verificable de EC-07 | [`test_recepcion.py`](../backend/tests/test_recepcion.py) |
| Un archivo inválido no tumba el lote | Degradación controlada de la carga | [`test_recepcion.py`](../backend/tests/test_recepcion.py) |
| Un trabajo por hoja aceptada, ninguno por rechazada | Que no se califique de más ni de menos | [`test_recepcion.py`](../backend/tests/test_recepcion.py) |
| La hoja queda almacenada con su contenido intacto | El orden almacenar → encolar | [`test_recepcion.py`](../backend/tests/test_recepcion.py) |
| Un nombre con rutas no escapa del directorio | El nombre lo controla quien sube | [`test_recepcion.py`](../backend/tests/test_recepcion.py) |
| El endpoint confirma la recepción, individual y en lote | El contrato con el frontend | [`test_carga_hojas.py`](../backend/tests/test_carga_hojas.py) |
| La pantalla no ofrece cargar si el backend no responde | No llevar al docente a una pantalla que va a fallar | [`carga_test.dart`](../frontend/test/features/carga_test.dart) |
| El reporte lista aceptadas y rechazadas con su motivo | EC-07 visible para el usuario | [`carga_test.dart`](../frontend/test/features/carga_test.dart) |
| Una falla de red se muestra como aviso, no como rechazo | Son cosas distintas y el docente debe distinguirlas | [`carga_test.dart`](../frontend/test/features/carga_test.dart) |
| Ninguna hoja queda sin reportar si la cola se cae a mitad del lote | La cifra de EC-07 que antes daba 100 % de pérdida | [`test_durabilidad_recepcion.py`](../backend/tests/test_durabilidad_recepcion.py) |
| La hoja no encolada queda pendiente en la bitácora, con su imagen recuperable | Reportarla no basta: el reintento no puede depender del docente | [`test_durabilidad_recepcion.py`](../backend/tests/test_durabilidad_recepcion.py) |
| El estado pendiente se relee desde otro objeto sobre el mismo archivo | Que la bitácora viva en el disco y no en la memoria de quien la escribió | [`test_durabilidad_recepcion.py`](../backend/tests/test_durabilidad_recepcion.py) |
| Una línea truncada no inutiliza la bitácora | El proceso puede morir escribiendo, y las líneas anteriores siguen valiendo | [`test_durabilidad_recepcion.py`](../backend/tests/test_durabilidad_recepcion.py) |
| El endpoint confirma el lote en vez de devolver 500 | Lo que ve el docente, de punta a punta por HTTP | [`test_durabilidad_recepcion.py`](../backend/tests/test_durabilidad_recepcion.py) |
| El lote no insiste contra una cola caída | El techo de 10 s de EC-07 en el camino de fallo | [`test_durabilidad_recepcion.py`](../backend/tests/test_durabilidad_recepcion.py) |
| El corte no se adelanta mientras la cola responde | Que no se dejen de encolar hojas por prudencia mal entendida | [`test_durabilidad_recepcion.py`](../backend/tests/test_durabilidad_recepcion.py) |
| Un error del almacén o de la bitácora rechaza esa hoja y no el lote | Un disco lleno en la hoja 101 devolvía 500 con las 100 primeras ya en la cola | [`test_durabilidad_recepcion.py`](../backend/tests/test_durabilidad_recepcion.py) |
| Una cola lenta no saca el lote del techo de EC-07 | La espera de 2 s es por llamada: hace falta un plazo para el lote entero | [`test_durabilidad_recepcion.py`](../backend/tests/test_durabilidad_recepcion.py) |
| El lote se confirma fuera del bucle de eventos y se lee de a una hoja | Que `/health` siga respondiendo y que el lote no llene la memoria (R-21) | [`test_carga_hojas.py`](../backend/tests/test_carga_hojas.py) |
| La hoja que pasa de 20 MB se rechaza y el lote sigue | La memoria de la API no depende de lo que alguien suba | [`test_recepcion.py`](../backend/tests/test_recepcion.py) · [`test_carga_hojas.py`](../backend/tests/test_carga_hojas.py) |
| Un nombre largo se acorta y dos exámenes no comparten carpeta | El nombre lo controla quien sube, y la retención será por examen (RNF-14) | [`test_recepcion.py`](../backend/tests/test_recepcion.py) |
| Un 5xx no afirma que no entró nada, y el examen viaja codificado | Que el docente no duplique hojas por un mensaje equivocado | [`servicio_carga_test.dart`](../frontend/test/features/servicio_carga_test.dart) · [`carga_test.dart`](../frontend/test/features/carga_test.dart) |

**Las pruebas nuevas se validaron provocando la falla**, según la convención del equipo: se
rompió a propósito la verificación de bytes, el reporte de rechazados, el conteo de encolados y
la frontera del módulo, y en cada caso se comprobó que la prueba correspondiente fallaba antes
de revertir. Una prueba que nunca falló no prueba nada.

De ahí salió un hallazgo que quedó anotado en el propio código: la prueba de rutas solo se pone
en rojo si se quitan **las dos** defensas de `nombre_seguro`, porque cada una basta por separado.
Verifica la propiedad y no el mecanismo, que es lo correcto, pero nadie debería borrar una de
las dos líneas creyendo que esta prueba lo detectaría.

**Verificación manual de extremo a extremo.** Las pruebas automatizadas no cruzan la frontera:
las del backend usan una cola sustituta y las del frontend un backend sustituto. El recorrido
completo se comprobó a mano sobre `docker compose up`, subiendo una imagen válida y un archivo
de texto con extensión `.jpg`. El sistema aceptó la primera, rechazó el segundo por contenido, y
**el identificador de trabajo que mostró la pantalla apareció idéntico en el log del worker**,
que corre en otro contenedor. El procedimiento está en el README para que sea reproducible.

**La medición del escenario de calidad ya está hecha, y encontró un incumplimiento.** EC-07
pide dos cifras. La primera —confirmación del lote en ≤10 segundos— se cumplía con margen. La
segunda —0 % de pérdida silenciosa— **daba 100 %**: con la cola cayéndose a mitad de un lote de
200 hojas, el sistema devolvía 500 y no reportaba ninguna de las 200, mientras 100 trabajos ya
estaban encolados. Eso motivó
[ADR-0006](adr/0006-registrar-la-recepcion-en-una-bitacora-antes-de-encolar.md) y el cambio que
lo corrige. El procedimiento, las dos corridas y sus límites están en
[`evidencia/medicion-ec07.md`](evidencia/medicion-ec07.md).

| Medida de EC-07 | Umbral | Antes (`cede35e`) | Después |
|---|---|---|---|
| Confirmación del lote de 200 hojas, operación normal | ≤ 10 s | 0,126 s | 1,744 s |
| Confirmación del lote de 200 hojas, con la cola caída | ≤ 10 s | devolvía 500 | 7,842 s |
| Pérdida silenciosa | 0 % | 100 % | 0 % |

Una prueba prevista que **no** se escribió, y no por olvido: **autorización**, es decir que un
docente no pueda cargar en un curso ajeno (RNF-05). Depende de `identidad`, el aspecto A-05, que
está vacío.

Y una que se escribió con un alcance menor del que su nombre sugiere: la durabilidad se verifica
releyendo la bitácora desde otro objeto sobre el mismo archivo, lo que demuestra que el estado
vive en el disco y no en memoria. Que el archivo esté en el plato y no en la caché del sistema
operativo lo sostiene el `fsync` de `BitacoraEnDisco`, y comprobarlo exigiría cortarle la
corriente a la máquina. Está dicho así en el docstring de esa prueba.

<a id="a-01-evidencia"></a>

### 7. Evidenciar

| Evidencia | Qué demuestra | Dónde |
|---|---|---|
| Ejecución de CI | Las 34 pruebas del backend y las 6 de widget pasando en una máquina limpia, con las dependencias instaladas desde cero y Redis levantado como servicio | [Run del commit `59e182e`](https://github.com/ISCOUTB/AS_202620_Sistema-de-calificacion-automatica/actions/runs/33347922678) — `backend-tests` y `frontend-tests` en verde |
| Reporte de recepción en pantalla | Un lote mixto procesado: la hoja válida recibida con su identificador de trabajo, la falsa rechazada con el motivo | [Captura del reporte](#a-01-evidencia) |
| Registro del worker | El mismo identificador de trabajo apareciendo en un proceso distinto, en otro contenedor: el recorrido se completó | Reproducible con `docker compose logs worker`; el procedimiento está en el [README](../README.md) |
| Reporte de medición de EC-07 | Las dos cifras del escenario, medidas antes y después del cambio de [ADR-0006](adr/0006-registrar-la-recepcion-en-una-bitacora-antes-de-encolar.md), con el procedimiento para repetirlas | [`evidencia/medicion-ec07.md`](evidencia/medicion-ec07.md) — 1,744 s contra un umbral de 10 s y 0 % de pérdida silenciosa contra un umbral de 0 % |

![Reporte de recepción de un lote mixto: una hoja recibida con su identificador de trabajo y un
archivo rechazado con el motivo](evidencia/a-01-reporte-de-recepcion.png)

El identificador de trabajo `2eede6b8-dd9f-4db6-a3ab-6205644ea416` que se ve en la captura es el
mismo que registró el worker en el contenedor aparte. Esa coincidencia es lo que convierte a la
captura en evidencia del recorrido completo y no solo de que la pantalla dibuja bien.

La distinción importa para no leer de más ni de menos esta fila: **que el aspecto funciona** lo
demuestran las pruebas del paso 6 y el recorrido de extremo a extremo; **cuán rápido y cuán a
prueba de caídas** lo responde la medición de EC-07 de la tabla anterior. Lo que ninguna de las
dos cubre es la caída del sistema operativo, que solo se comprobaría cortándole la corriente a la
máquina.

### S11: fallos parciales de la cola (EC-07)

La cola de trabajos es la integración principal del sistema: toda hoja aceptada pasa por ella. La
S11 la recorrió con los tres casos que pide (que Redis no responda, que responda tarde y que
responda dos veces), de los dos lados, en la [tabla de modos de fallo](evidencia/modos-de-fallo.md) (MF-01 a MF-06).

- **Encontrado al medir:** con Redis lento, una publicación tardaba 10,012 s y el lote de 200
  hojas 10,017 s, porque la API usaba la espera de 10 s del worker. Es el dato que ADR-0006 dejó
  escrito para revisarse.
- **Decidir:** [ADR-0016](adr/0016-acotar-la-espera-de-la-cola-y-hacer-idempotente-al-worker.md), que precisa a ADR-0006: la API espera 2 s, el worker 10 s, el
  cliente no reintenta solo, y el worker procesa cada `trabajo_id` una sola vez con
  `SET NX EX`.
- **Construir:** [`infraestructura/cola.py`](../backend/infraestructura/cola.py)
  (`cliente_redis` y `primera_entrega`), [`api/main.py`](../backend/api/main.py)
  (`obtener_cliente_cola`) y [`worker/main.py`](../backend/worker/main.py).
- **Verificar:** ocho pruebas del backend en
  [`test_modos_de_fallo.py`](../backend/tests/test_modos_de_fallo.py), que se suman a las del
  paso 6 y se validaron provocando la falla con seis mutaciones. Después del cambio, el lote de 200
  confirma en 2,017 s con la cola lenta.
- **Sigue abierto:** el worker que muere después de retirar el trabajo lo pierde, porque la lista
  no tiene acuse de recibo (MF-06, R-22); la marca de idempotencia pasa a después de procesar
  cuando exista A-02 (R-23); y la API no detecta una hoja subida dos veces (MF-13, R-24). Los tres
  tienen su plan en la tabla.

### Consistencia: la identidad de la hoja y la fuente de verdad de su estado

La entrega de consistencia pide el ADR de la decisión de datos más costosa de revertir, y es de este
aspecto: la identidad de la hoja, de la que va a colgar todo lo que A-02 y A-03 guarden.

- **Encontrado al revisar:** la hoja no tenía identidad propia. El `trabajo_id` hacía de identidad
  de la hoja y de la del encargo que viaja por la cola, y con un solo valor no se podía volver a
  procesar una hoja (para recalificarla) sin chocar con la idempotencia de ADR-0016.
- **Decidir:** [ADR-0018](adr/0018-dar-a-la-hoja-una-identidad-propia-y-derivar-su-estado-de-la-bitacora.md). Un `hoja_id` acuñado una vez por `ingesta`, distinto del
  `trabajo_id`, y la bitácora como única fuente de verdad del estado; la copia `estado` de la
  respuesta es una instantánea. Se toma ahora, cuando revertirla todavía es quitar un campo.
- **Construir:** [`ingesta/recepcion.py`](../backend/ingesta/recepcion.py) lo acuña,
  [`infraestructura/bitacora.py`](../backend/infraestructura/bitacora.py) lo escribe y lo relee (las
  líneas viejas, con su `trabajo_id`), [`worker/main.py`](../backend/worker/main.py) lo registra y el
  contrato pasa a 1.3.0.
- **Verificar:** seis pruebas en
  [`test_identidad_de_la_hoja.py`](../backend/tests/test_identidad_de_la_hoja.py), que se suman a
  las del paso 6 y se validaron provocando la falla con cuatro mutaciones.
- **Evidenciar:** las garantías de cada paso de la carga, en la
  [tabla operación → consistencia](evidencia/consistencia-y-cache.md), filas C-01 a C-05.
- **Sigue abierto:** ninguna ruta deja consultar el estado vigente de una hoja, y hoy obtenerlo es
  releer toda la bitácora (R-26).

### Taller de mensajería: la cola de trabajos

La operación del taller es la de este aspecto: cada hoja aceptada viaja como un mensaje de la API al
worker por la cola. Es desacoplamiento temporal real, así que no hubo prototipo aparte.

- **Encontrado al revisar:** el mensaje no tenía contrato; la entrega era como mucho una vez (el
  worker que moría a mitad perdía el trabajo, R-22); la marca de idempotencia iba antes de procesar
  (R-23); no había reintentos ni lista de fallidos, y el worker daba por recibida una hoja cuya
  imagen ya no estaba.
- **Decidir:** [ADR-0020](adr/0020-entregar-los-trabajos-al-menos-una-vez-con-reintentos-y-lista-de-fallidos.md), frente a la alternativa síncrona (procesar en la petición de
  carga: 16,6 minutos para un lote de 200 contra los 10 s de EC-07). Al menos una vez con
  idempotencia, con listas de Redis, sin agregar un broker.
- **Construir:** el contrato versión 1 en [`cola.py`](../backend/infraestructura/cola.py),
  publicado en [`trabajo-v1.schema.json`](contrato/trabajo-v1.schema.json); el acuse, los reintentos
  (5, 10 y 20 s, cuatro intentos) y la lista de fallidos en
  [`consumo.py`](../backend/infraestructura/consumo.py); el worker que abre la imagen; y el rastro de
  cada mensaje en el registro, con [`seguir_trabajo.py`](../backend/herramientas/seguir_trabajo.py) y
  [`cola_de_fallidos.py`](../backend/herramientas/cola_de_fallidos.py).
- **Verificar:** quince pruebas en [`test_mensajeria.py`](../backend/tests/test_mensajeria.py), entre
  ellas la del duplicado y la del fallo recuperable, validadas con una mutación por propiedad.
- **Evidenciar:** una [ejecución real](evidencia/taller-mensajeria.md) con la API, el worker y Redis: la hoja 1 se procesa una
  vez aunque llegó dos y un worker caído la dejó en curso; la 2, en el tercer intento; la 3 termina
  en la lista de fallidos con su motivo.
- **Sigue abierto:** todo vive en un Redis sin persistencia (R-28), y la recuperación supone un
  solo worker (R-29).

### Por qué se eligió este aspecto primero

- Es el punto de entrada del flujo completo: sin una hoja cargada no hay nada sobre lo cual
  ejecutar la detección de marcas ni la calificación.
- Es funcional, no tecnológico. Se puede declarar y especificar sin depender todavía de qué
  algoritmo de OMR, qué umbral de confianza o qué proveedor de LLM se elija.
- Permite un primer incremento verificable de extremo a extremo —un examen queda recibido y
  registrado— que no depende de que las partes de mayor riesgo técnico estén resueltas.

---

<a id="a-02"></a>

## Aspecto A-02: Detección de marcas y nivel de confianza

**Construido** entre el 2 y el 6 de noviembre, con apoyo de IA (registro en [`ia.md`](ia.md),
entrada 21). La decisión es [ADR-0023](adr/0023-leer-las-hojas-en-posiciones-fijas-y-mandar-a-revision-lo-que-no-se-ve-bien.md),
aceptado por el equipo el 6-nov.

### 1. Declarar

- **Para quién es:** el profesor, que necesita que la lectura sea fiel a lo que el estudiante
  marcó; y el estudiante, que soporta las consecuencias de un error.
- **Qué problema resuelve:** convierte una foto o un escaneo de la hoja en respuestas legibles por
  el sistema, acompañadas de un nivel de confianza que hace explícita la incertidumbre.

### 2. Especificar

- **Requisitos:** RF-02 (la marca de cada pregunta, con su confianza) y RF-03 (lo que no llega al
  umbral va a revisión, nunca a una respuesta elegida por el sistema).
- **Escenarios:** [EC-01](arc42/arc42-template-ES.md#ec-01) (≥98 % de marcas bien leídas sobre
  300 hojas etiquetadas) y [EC-02](arc42/arc42-template-ES.md#ec-02) (≥99 % de las marcas
  ambiguas a revisión).
- **Restricciones que lo obligan:** RNF-01 (la calificación es OMR, sin LLM), RNF-02 (hoja de
  formato fijo con marcas de registro) y RNF-12 (el código del estudiante no va al log).
- **Tensión que lo condiciona:** [T-1](#t-1), exactitud frente a trabajo de revisión.
- **Alcance de este semestre:** solo la hoja v1 (carta, 40 preguntas de A a D). Un examen puede tener menos de 40 preguntas; otro papel, más preguntas o una quinta opción quedan fuera, por las razones del punto 1 de ADR-0023.

### 3. Ubicar

- **Contexto:** OMR ([arc42 §8.1](arc42/arc42-template-ES.md#81-mapa-de-contextos)). Ninguna
  relación del Nivel 1 del C4: ocurre dentro del sistema (ver la nota de arriba).
- **C4:** relación 7 del Nivel 2 (el worker lee la hoja del almacén) y `omr` dentro del worker en
  el Nivel 3 ([`c4/doc-c4.md`](c4/doc-c4.md#nivel-3--diagrama-de-componentes)).
- **Módulo:** `omr`, dueño de `LecturaDeBurbuja`, `LecturaDePregunta`, `LecturaDelCodigo` y
  `LecturaDeHoja` ([§8.3](arc42/arc42-template-ES.md#83-propiedad-de-datos)). Lo invoca el worker,
  en `leer_y_calificar`.

### 4. Decidir

[ADR-0023](adr/0023-leer-las-hojas-en-posiciones-fijas-y-mandar-a-revision-lo-que-no-se-ve-bien.md),
con sus alternativas: las burbujas se leen en las posiciones que fija el formato, después de
enderezar la hoja con sus cuatro marcas; cada una se mide contra el papel que la rodea; una
pregunta tiene respuesta solo si la confianza de marcarla y la de descartar las demás llegan al
umbral (70, configurable de 51 a 100); y lo que no se ve bien (el brillo del grafito, un contorno
tapado) va a revisión. Una hoja que no se puede leer queda `ILEGIBLE` con su motivo, sin reintento.

Lo decidió el prototipo que pedía R-05: una hoja impresa, marcada a mano y fotografiada tres veces.
Lo que mostraron las fotos, y lo que cambió en el diseño, está en la
[sección 1 de la medición](evidencia/medicion-lectura-omr.md#1-la-hoja-del-prototipo-r-05).

### 5. Construir

| Pieza | Dónde |
|---|---|
| Formato v1 (carta, 40 preguntas A a D, código `T` + 8 dígitos, cuatro marcas) | [`backend/omr/formato.py`](../backend/omr/formato.py) |
| Plantilla imprimible, dibujada con la misma definición con que se lee | [`backend/omr/plantilla.py`](../backend/omr/plantilla.py) (`plantilla_pdf`) |
| Tamaño por encabezado, marcas, orientación, enderezado, ajuste, medida y recortes | [`backend/omr/vision.py`](../backend/omr/vision.py) |
| Confianza de cada burbuja y regla de cada pregunta y del código | [`backend/omr/decision.py`](../backend/omr/decision.py) |
| La lectura completa, una función pura: bytes dentro, lectura fuera | [`backend/omr/lectura.py`](../backend/omr/lectura.py) |
| Los motivos de una hoja ilegible | [`backend/omr/errores.py`](../backend/omr/errores.py) |
| El paso del worker: leer, calificar, guardar el resultado y los recortes | [`backend/worker/main.py`](../backend/worker/main.py) (`leer_y_calificar`) |
| En el sitio, las fotos pasadas a gris y a 3 200 px antes de subirlas | [`preparacion_de_hojas.dart`](../frontend/lib/features/carga/data/preparacion_de_hojas.dart) y `reducir_foto*.dart` |

Tres decisiones de construcción que conviene poder defender:

1. **Una burbuja que se ve vacía no se da por vacía si su interior está desparejo.** Una marca de
   lápiz con el reflejo del foco rellenó 0,06, como el papel. Una vacía cuenta como incorrecta sin
   pasar por el profesor, así que leerla vacía sería un error silencioso.
2. **La orientación sale del parecido de la hoja entera con la plantilla**, no de las burbujas:
   girada 180°, casi todas las burbujas de respuesta caen sobre otras burbujas.
3. **El tamaño de la imagen se lee del encabezado antes de decodificarla.** Un PNG de 120 KB y
   10 000 × 10 000 px mataba al worker por memoria y lo dejaba tomando la misma hoja en cada
   reinicio. Además, desde entonces la muerte del worker cuenta como un intento, para cualquier otra
   causa ([sección 5 de la medición](evidencia/medicion-lectura-omr.md#5-imágenes-que-piden-más-memoria-de-la-que-tiene-el-worker)).

### 6. Verificar

- [`test_plantilla.py`](../backend/tests/test_plantilla.py): el formato y la plantilla, incluido
  que no haya tinta en el cuarto de pulgada del borde que la impresora no imprime.
- [`test_vision.py`](../backend/tests/test_vision.py), [`test_decision.py`](../backend/tests/test_decision.py)
  y [`test_lectura.py`](../backend/tests/test_lectura.py): cada paso con números escritos a mano y
  la hoja completa con hojas sintéticas (giradas, con sombra, desenfocadas, con brillo), con los
  recortes y con las imágenes que no se pueden leer.
- [`test_lectura_fotos_r05.py`](../backend/tests/test_lectura_fotos_r05.py): las tres fotos del
  prototipo. Las fotos no están en el repositorio; la prueba corre si `OMR_FOTOS_R05` apunta a
  ellas.
- [`preparacion_de_hojas_test.dart`](../frontend/test/features/preparacion_de_hojas_test.dart): las
  tandas de la pantalla de carga.
- [`test_mensajeria.py`](../backend/tests/test_mensajeria.py), contra Redis: una hoja que mata al
  worker vuelve con un intento más cada vez y, después de cuatro, termina en fallidos mientras las
  demás se leen (R-36).
- **Validadas provocando la falla:** cada salvaguarda de la lectura se rompió a propósito y alguna
  prueba se puso en rojo; sin el tope por encabezado, por ejemplo, fallan las dos pruebas de las
  imágenes enormes.

### 7. Evidenciar

[Medición de la lectura](evidencia/medicion-lectura-omr.md), con su procedimiento y sus informes
JSON:

- EC-01: 9 406 de 9 406 marcas claras bien leídas (100 %, contra ≥98 %);
- EC-02: 1 026 de 1 026 marcas ambiguas a revisión (100 %, contra ≥99 %);
- ninguna respuesta leída mal sin aviso, en las 300 hojas y en las tres fotos del prototipo;
- 0,46 preguntas por hoja a revisión sin necesitarlo, todas por el brillo.

**Lo que no prueba:** las 300 hojas son sintéticas, y el umbral de 70 no se ha calibrado con hojas
reales (R-01 y R-04).

---

<a id="a-03"></a>

## Aspecto A-03: Calificación contra la clave y publicación de resultados

**Construido** junto con A-02, salvo las estadísticas del Panel (RF-05), con la revisión manual
(RF-08) antes de A-05. Registro de IA en [`ia.md`](ia.md), entrada 21.

### 1. Declarar

- **Para quién es:** el profesor y el TA, que necesitan la nota y las estadísticas por
  pregunta.
- **Qué problema resuelve:** compara las respuestas detectadas contra la clave habilitada,
  calcula la nota y la publica, y deja resolver a mano lo ambiguo y recalcular.

### 2. Especificar

- **Requisitos:** RF-04 (comparar y calificar), RF-05 (presentar los resultados) y RF-08 (resolver
  a mano y recalcular). Toca también RF-07 (sin una clave habilitada no hay nota) y RF-10 (quién
  modificó una nota y cuándo).
- **Escenarios:** [EC-03](arc42/arc42-template-ES.md#ec-03) (≤5 s por hoja, p95) y
  [EC-04](arc42/arc42-template-ES.md#ec-04) (200 hojas en ≤10 min).
- **Restricciones que lo obligan:** RNF-15 (una nota corregida a mano se distingue de la
  automática) y RNF-12 (el código del estudiante no sale por una ruta pública).

### 3. Ubicar

- **Contextos:** Calificación y Dashboard ([§8.3](arc42/arc42-template-ES.md#83-propiedad-de-datos),
  «Por qué A-03 abarca dos contextos»). Relación 2 del Nivel 1 del C4.
- **C4:** relaciones 7 (el worker lee la clave y guarda el resultado) y 3 (la aplicación web lee
  los resultados y guarda las revisiones) del Nivel 2; `calificacion` en los dos contenedores y
  `dashboard` en la aplicación web, en el Nivel 3.
- **Módulos:** `calificacion` decide la nota (`ResultadoDePregunta`, `CalificacionDeHoja`,
  `ResolucionDelProfesor`); `dashboard` la presenta (`ResultadoDeHoja`, `ResultadosDelExamen` y
  las cuatro de la revisión); `autoria` es la dueña de la clave y de la lista de exámenes.

### 4. Decidir

- [ADR-0002](adr/0002-procesar-calificacion-de-forma-asincrona.md): la nota de una hoja con
  preguntas ambiguas queda *provisional* hasta que el docente las resuelva.
- [ADR-0018](adr/0018-dar-a-la-hoja-una-identidad-propia-y-derivar-su-estado-de-la-bitacora.md):
  todo se refiere por `hoja_id` y se guarda como hechos de solo agregado.
- [ADR-0023](adr/0023-leer-las-hojas-en-posiciones-fijas-y-mandar-a-revision-lo-que-no-se-ve-bien.md),
  puntos 7 a 9 y sus consecuencias: la nota en décimas, la clave por un puerto, el registro de
  resultados aparte de la bitácora, las notas sin el código del estudiante y RF-08 antes de A-05.

### 5. Construir

| Pieza | Dónde |
|---|---|
| La nota, el veredicto de cada resolución y la nota vigente | [`backend/calificacion/nota.py`](../backend/calificacion/nota.py) |
| Resolver las preguntas de una hoja (RF-08) | [`backend/calificacion/revision.py`](../backend/calificacion/revision.py) |
| La clave por un puerto, y la lista de exámenes que tienen una | [`infraestructura/claves.py`](../backend/infraestructura/claves.py) · [`autoria/examenes.py`](../backend/autoria/examenes.py) |
| El registro de resultados (lo escribe el worker) y el de revisiones (la API) | [`infraestructura/resultados.py`](../backend/infraestructura/resultados.py) · [`infraestructura/revisiones.py`](../backend/infraestructura/revisiones.py) |
| Lo que ve el profesor: las notas por hoja y las preguntas en revisión | [`dashboard/resultados.py`](../backend/dashboard/resultados.py) · [`dashboard/revision.py`](../backend/dashboard/revision.py) |
| `GET /examenes`, `GET /examenes/{id}/resultados`, `GET /examenes/{id}/revision`, `POST /examenes/{id}/hojas/{hoja}/revision` y el recorte de cada pregunta | [`api/main.py`](../backend/api/main.py), contrato 1.8.0 ([`openapi.json`](contrato/openapi.json)) |
| En el sitio: la lista de exámenes, las notas junto a cada archivo y la pantalla de revisión | [`servicio_examenes.dart`](../frontend/lib/features/carga/data/servicio_examenes.dart) · [`servicio_resultados.dart`](../frontend/lib/features/carga/data/servicio_resultados.dart) · [`reporte_recepcion.dart`](../frontend/lib/features/carga/views/widgets/reporte_recepcion.dart) · [`pantalla_revision.dart`](../frontend/lib/features/revision/views/pantalla_revision.dart) · [`servicio_revision.dart`](../frontend/lib/features/revision/data/servicio_revision.dart) |

Tres decisiones de construcción que conviene poder defender:

1. **El profesor dice qué marcó el estudiante, no si está bien.** Elige A a D o «Ninguna» mirando
   el recorte de la fila, y `calificacion` decide el veredicto con la clave. La respuesta correcta
   nunca sale de la API: ni en la revisión ni en la lista de exámenes.
2. **La nota automática no se reescribe.** Cada resolución es un hecho nuevo, la última de cada
   pregunta manda, y la nota vigente se recalcula; la automática queda como historia y la corregida
   sale marcada `revisada` (RNF-15).
3. **Las notas se publican sin el código del estudiante**, porque las rutas son públicas hasta
   A-05: la pantalla dice si el código se leyó completo y nada más.

### 6. Verificar

- [`test_calificacion.py`](../backend/tests/test_calificacion.py): las reglas de la nota (décimas,
  redondeo a la mitad hacia arriba, una anulada no cambia el total) y las de la resolución.
- [`test_claves.py`](../backend/tests/test_claves.py), [`test_resultados.py`](../backend/tests/test_resultados.py)
  y [`test_revisiones.py`](../backend/tests/test_revisiones.py): los tres registros, incluida una
  línea truncada.
- [`test_leer_y_calificar.py`](../backend/tests/test_leer_y_calificar.py): el paso del worker, y
  que el código del estudiante no llega al log (una fuga inyectada pone la prueba en rojo).
- [`test_ruta_resultados.py`](../backend/tests/test_ruta_resultados.py),
  [`test_ruta_examenes.py`](../backend/tests/test_ruta_examenes.py) y
  [`test_ruta_revision.py`](../backend/tests/test_ruta_revision.py): las rutas, y que ninguna
  respuesta trae el código del estudiante ni la respuesta correcta.
- [`test_contrato.py`](../backend/tests/test_contrato.py): las nueve rutas del contrato 1.8.0.
- En el sitio, [`revision_test.dart`](../frontend/test/features/revision_test.dart),
  [`servicio_revision_test.dart`](../frontend/test/features/servicio_revision_test.dart),
  [`servicio_resultados_test.dart`](../frontend/test/features/servicio_resultados_test.dart),
  [`servicio_examenes_test.dart`](../frontend/test/features/servicio_examenes_test.dart) y las de
  la pantalla de carga.

### 7. Evidenciar

- **EC-03:** de la carga al resultado, p95 de 1,7 s por hoja suelta (contra ≤5 s).
- **EC-04:** un lote de 200 hojas procesado entero en 3,6 min (contra ≤10 min), con el worker al
  81 % de su memoria y al 100 % de su cuarto de CPU.
- **RF-08:** con las fotos del prototipo, la hoja de arriba pasó de 3,9 a 4,0 al resolver sus
  cuatro preguntas, sin que la respuesta correcta saliera de la API
  ([captura y detalle](evidencia/medicion-lectura-omr.md#4-la-revisión-manual-con-las-fotos-del-prototipo-rf-08)).

**Lo que falta:** las estadísticas por pregunta y por curso del Panel (RF-05); saber quién resuelve
cada revisión (A-05, AM-02); que una hoja subida dos veces no se califique dos veces (R-24); y que
la clave se registre desde la aplicación, que hoy se copia a mano al volumen (A-04).

---

<a id="a-04"></a>

## Aspecto A-04: Registro del banco y habilitación del examen

**Declarado.**

- **Para quién es:** el profesor que prepara el examen.
- **Qué problema resuelve:** recibe el banco de preguntas y la clave que el profesor trae
  escritos, y garantiza que ningún examen se califique sin que él lo haya habilitado
  explícitamente, dejando registro de quién lo hizo y cuándo. Los distractores diagnósticos
  opcionales (RF-11) se separaron en [A-06](#a-06), con su propio escenario.
- **Requisitos:** RF-06, RF-07.
- **Escenario:** [EC-05](arc42/arc42-template-ES.md#ec-05).
- **Tensión que lo condicionaba:** [T-2](#t-2) — retirada; ver la nota en esa sección.
- **Decisión que ya lo condiciona:**
  [ADR-0004](adr/0004-quitar-validacion-simbolica-obligatoria-de-la-clave.md) — retira la
  validación simbólica automática con SymPy que este aspecto tenía previsto y la reemplaza por
  la aprobación manual del profesor. [ADR-0005](adr/0005-acotar-el-llm-a-la-generacion-de-distractores-diagnosticos.md) precisa además que el
  profesor llega con sus preguntas escritas: la generación con LLM deja de ser el camino
  principal y queda como apoyo opcional (RF-11). [ADR-0003](adr/0003-usar-fastapi-y-flutter.md) sigue
  vigente sin cambios: la elección de FastAPI ya no depende de SymPy, pero se sostiene sobre
  OpenCV.
- **Por qué no se trabaja todavía:** no le falta nada técnico. El registro del banco, la clave y
  la habilitación funcionan sin LLM; la parte que sí lo necesita, los distractores, ya se
  construyó en [A-06](#a-06). Es una cuestión de orden de trabajo.
- **Lo que ya dejó A-03:** la clave existe como dato, `ClaveDeRespuestas` con su `Habilitacion`
  (quién y cuándo), de la que `autoria` es dueña, y se lee por un puerto
  (`infraestructura/claves.py`). Hoy se escribe a mano en un JSON por examen y se copia al volumen;
  sin habilitación, la hoja queda sin nota (RF-07). A-04 es lo que la registra y la habilita desde
  la aplicación.

---

<a id="a-06"></a>

## Aspecto A-06: Propuesta de distractores diagnósticos

**Construido** en la S9, con apoyo de IA (registro en [`ia.md`](ia.md), entrada 12).

### 1. Declarar

- **Para quién es:** el profesor que prepara el examen y quiere opciones incorrectas que digan con
  qué error se equivocó el estudiante.
- **Qué problema resuelve:** construir distractores diagnósticos toma tiempo. A pedido del
  profesor, el sistema propone opciones incorrectas, cada una con el error de procedimiento que
  representa, y **el profesor decide cuáles acepta**: nada entra a un examen sin su habilitación
  (RF-07).
- **Requisito:** RF-11, opcional. El sistema funciona completo sin invocarlo nunca
  ([ADR-0005](adr/0005-acotar-el-llm-a-la-generacion-de-distractores-diagnosticos.md)).
- **Por qué es un aspecto aparte de A-04:** A-04 realiza RF-06 y RF-07, y su escenario (EC-05) mide
  la habilitación. Los distractores tienen su propio escenario (EC-08), su propio sistema externo
  y su propio modo de fallar.

### 2. Especificar

- **Escenario:** [EC-08](arc42/arc42-template-ES.md#ec-08), con tres medidas:
  - **M1:** ninguna propuesta que repita textualmente la respuesta correcta llega al profesor;
  - **M2:** p95 de la latencia de 15 s o menos;
  - **M3:** con el proveedor caído o lento, 503 en 21 s o menos.
- **Restricciones que lo obligan:**
  - RNF-13: solo la pregunta sale hacia el proveedor;
  - RNF-16: costo US$0 y sin tarjeta;
  - RNF-11: la clave llega por el entorno, nunca por el repositorio.

### 3. Ubicar

- **Contexto:** Autoría ([arc42 §8.1](arc42/arc42-template-ES.md#81-mapa-de-contextos)). Llega al
  proveedor por la relación 5, que es una capa anticorrupción.
- **C4:** relación 3 del Nivel 1, relación 8 del Nivel 2, y `autoria` con sus relaciones 10 y 11 en
  el Nivel 3 ([`c4/doc-c4.md`](c4/doc-c4.md)).
- **Módulo:** `autoria`, que es dueño de sus cuatro entidades
  ([§8.3](arc42/arc42-template-ES.md#83-propiedad-de-datos)). La entrada es `api`, con
  `POST /distractores`.

### 4. Decidir

- [ADR-0005](adr/0005-acotar-el-llm-a-la-generacion-de-distractores-diagnosticos.md): el LLM es una capacidad opcional de la autoría, fuera de la calificación.
- [ADR-0013](adr/0013-consumir-groq-detras-de-un-puerto-y-degradar-sin-bloquear-la-autoria.md): Groq detrás de un puerto de `autoria`, llamado con `httpx`, 20 s de
  espera sin reintentos y 503 ante cualquier falla. Ahí están las alternativas descartadas.

### 5. Construir

- [`autoria/distractores.py`](../backend/autoria/distractores.py): la pregunta, la propuesta, el
  puerto `GeneradorDeDistractores` y la regla de qué llega al profesor.
- [`autoria/proveedor_llm.py`](../backend/autoria/proveedor_llm.py): el adaptador al proveedor y
  la métrica de EC-08 (evento `distractores_propuestos`).
- [`api/main.py`](../backend/api/main.py): `POST /distractores`. El contrato pasa a 1.1.0
  ([`contrato/openapi.json`](contrato/openapi.json)).
- [`herramientas/evaluar_distractores.py`](../backend/herramientas/evaluar_distractores.py): la
  medición de EC-08.
- [`pantalla_pauta.dart`](../frontend/lib/features/pauta/views/pantalla_pauta.dart) y
  [`servicio_distractores.dart`](../frontend/lib/features/pauta/data/servicio_distractores.dart):
  la pantalla del sitio. El botón se deshabilita mientras espera; el 503 se muestra como
  advertencia con «Volver a pedir»; y el 429 muestra el mensaje de la API con una cuenta regresiva
  que lee `Retry-After` (límite por minuto) o sin botón (límite diario). La API expone esa
  cabecera al navegador en CORS (`api/main.py`).

### 6. Verificar

- [`test_distractores.py`](../backend/tests/test_distractores.py): la regla, y **la prueba del
  defecto**. Sin el descarte de la respuesta correcta fallan 4 pruebas, y se demostró con un PR
  que no se fusionó ([procedimiento y runs](evidencia/prueba-distractores-falla.md)).
- [`test_proveedor_llm.py`](../backend/tests/test_proveedor_llm.py): RNF-13 sobre el cuerpo
  entero de la solicitud, y la degradación.
- [`test_ruta_distractores.py`](../backend/tests/test_ruta_distractores.py): la ruta (200, 503 y
  422), y desde el frontend nuevo, que el navegador puede leer `Retry-After` en el 429.
- [`servicio_distractores_test.dart`](../frontend/test/features/servicio_distractores_test.dart)
  y [`pauta_test.dart`](../frontend/test/features/pauta_test.dart): 26 pruebas de la pantalla. Cada
  código de respuesta se traduce a lo que ve el docente, contra un `MockClient`, y un 429 nunca se
  muestra como «La API respondió 429».
- [`test_fronteras.py`](../backend/tests/test_fronteras.py): la auditoría de la S9 le agregó la
  prueba de que el dominio no importa `api` ni `worker`
  ([auditoría](evidencia/auditoria-s9.md)).

### 7. Evidenciar

[Evaluación de EC-08](evidencia/evaluacion-distractores.md), con el conjunto de 20 preguntas
([`evidencia/conjunto-evaluacion-distractores.json`](evidencia/conjunto-evaluacion-distractores.json))
y el resultado completo
([`evidencia/evaluacion-distractores.json`](evidencia/evaluacion-distractores.json)):

- M1, ninguna de las 120 propuestas entregadas repite la respuesta correcta (0 %);
- M2, p95 de la latencia de 2,91 s contra un techo de 15 s, en 40 solicitudes;
- M3, con el proveedor caído o lento la ruta responde 503 en 20,25 s como máximo, contra 21 s;
- calidad, calificada por el equipo: 44 de 60 propuestas diagnósticas válidas (73 %), ninguna equivalente a la respuesta correcta, y el error más común es la etiqueta (8 incorrectas y 4 a medias);
- costo: US$0 en la capa gratuita (al precio de pago serían US$0,0004 por solicitud y US$0,008 por examen de 20 preguntas).

**La pantalla del sitio** llegó con el frontend nuevo (paso 5 de esta sección). Sus pruebas son de
widget; las cifras de M1 a M3 siguen siendo las de la API.

### Segundo corte: límite de costo (EC-09)

El escenario operativo del segundo corte cae sobre este aspecto: `POST /distractores` es pública y
cada solicitud gasta cuota de Groq (R-17). La línea base, medida en el entorno desplegado antes de
cambiar nada, mostró que una ráfaga de 20 solicitudes llegaba entera al proveedor y que 8 terminaban
en 503 por cuota ([`presupuesto-antes.json`](evidencia/presupuesto-antes.json)).

- **Especificar:** [EC-09](arc42/arc42-template-ES.md#ec-09), con cuatro medidas: ningún corte del
  proveedor por cuota, 6 o menos solicitudes en el proveedor, un 429 propio en 1 s o menos y
  `/health` en 200.
- **Decidir:** [ADR-0015](adr/0015-limitar-el-gasto-del-proveedor-de-llm-con-un-presupuesto-en-la-api.md),
  un presupuesto de 6 solicitudes por minuto y 150 por día en la memoria de la API, que precisa a
  ADR-0013 sin reemplazarlo.
- **Construir:** [`autoria/presupuesto.py`](../backend/autoria/presupuesto.py) (el presupuesto y
  `GeneradorConPresupuesto`, que envuelve al adaptador de Groq) y [`api/main.py`](../backend/api/main.py)
  (el 429 con `Retry-After`, el evento `presupuesto_agotado` y `GET /metricas`). El contrato pasa a
  1.2.0.
- **Verificar:** [`test_presupuesto.py`](../backend/tests/test_presupuesto.py), con un reloj falso,
  y cuatro pruebas nuevas en [`test_ruta_distractores.py`](../backend/tests/test_ruta_distractores.py),
  que el pipeline corre como paso propio.
- **Evidenciar:** el [experimento](evidencia/experimento-presupuesto.md), con hipótesis, dos montajes
  (local con un proveedor simulado y el entorno desplegado con Groq), resultado y conclusión.

### S11: fallos parciales del proveedor de LLM

La propuesta de distractores es la segunda integración de la [tabla de modos de fallo](evidencia/modos-de-fallo.md)
(MF-07 a MF-10). Las mitigaciones ya estaban decididas en ADR-0013 (20 s, sin reintentos, 503 con
motivo) y ADR-0015 (el presupuesto acota cuántas solicitudes esperan a la vez); la S11 agregó lo que
faltaba probar:

- **Responde tarde:** el adaptador apuntado a un servidor que acepta la conexión y no contesta se
  corta en su tiempo de espera, en una sola conexión
  ([`test_modos_de_fallo.py`](../backend/tests/test_modos_de_fallo.py)).
- **Responde dos veces:** la misma solicitud repetida no deja estado y gasta su propio cupo
  ([`test_ruta_distractores.py`](../backend/tests/test_ruta_distractores.py)).
- **Sin *circuit breaker*, con motivo:** con 6 solicitudes por minuto como máximo, el peor caso son
  6 hilos esperando 20 s; la tabla dice qué dato lo haría necesario.
- **No se extrae a un servicio propio:** [ADR-0017](adr/0017-no-extraer-ningun-modulo-del-monolito-todavia.md) lo evaluó como opción y lo descartó
  por ahora, con los datos que lo harían revisar.

### Consistencia: la caché de propuestas

El diseño de caché de la entrega de consistencia es de este aspecto: es la única lectura cara del
sistema (un cupo del presupuesto y unos 2 s por solicitud) y lo que se lee no envejece solo.

- **Decidir:** [ADR-0019](adr/0019-guardar-en-cache-las-propuestas-de-distractores.md). Las propuestas del proveedor se guardan 24 horas en la memoria de
  la API, por fuera del presupuesto, y la misma pregunta pedida otra vez se responde desde ahí, con
  la regla aplicada otra vez y `desde_la_cache: true`.
- **Invalidación:** el modelo y la huella de las instrucciones van en la clave; se guarda sin
  filtrar y la regla corre en cada lectura; 24 horas que leer no renueva; 256 entradas; y «Pedir
  otras propuestas» manda `otras: true`, que salta la caché y reemplaza lo guardado. Las fallas no
  se guardan.
- **Construir:** [`autoria/cache.py`](../backend/autoria/cache.py),
  [`api/main.py`](../backend/api/main.py) (la ruta y `GET /metricas`), el contrato en 1.4.0 y, en el
  sitio, [`servicio_distractores.dart`](../frontend/lib/features/pauta/data/servicio_distractores.dart)
  y [`pantalla_pauta.dart`](../frontend/lib/features/pauta/views/pantalla_pauta.dart).
- **Verificar:** trece pruebas en
  [`test_cache_de_propuestas.py`](../backend/tests/test_cache_de_propuestas.py), validadas con una
  mutación por regla de invalidación, y dos ajustes en las pruebas del sitio.
- **Evidenciar:** la política de invalidación completa y las filas C-07 y C-08 de la
  [tabla de consistencia](evidencia/consistencia-y-cache.md). En vivo, `cache_de_distractores` en `GET /metricas`.
- **Sigue abierto:** la caché vive en cada proceso (R-27), y su efecto con tráfico real no se ha
  medido todavía.

---

<a id="a-05"></a>

## Aspecto A-05: Identidad y aislamiento de datos por curso

**Declarado.**

- **Para quién es:** el Comité Académico y los administradores de TI, responsables de la
  confidencialidad de las calificaciones; y el estudiante, titular de los datos.
- **Qué problema resuelve:** garantiza que solo usuarios registrados accedan, que cada docente
  vea únicamente sus cursos, y que toda modificación de una nota quede registrada con su autor
  y su fecha.
- **Requisitos:** RF-09, RF-10.
- **Escenario:** [EC-06](arc42/arc42-template-ES.md#ec-06).
- **Restricciones que lo obligan:** RNF-05, RNF-12 (protección de datos personales) y RNF-15
  (trazabilidad para el derecho de revisión del estudiante).
- **Por qué no se trabaja todavía:** es transversal a los demás aspectos y convenía
  especificarlo cuando existieran al menos dos flujos reales sobre los que aplicarlo. **Ya
  existen**: la carga, las notas y la revisión manual. Y es la condición para la primera hoja real
  (AM-02): hoy cualquiera con la URL ve las notas de un examen, sin el código del estudiante, y
  puede resolver una revisión con cualquier nombre.

---

## Tensiones de calidad identificadas

Estas tensiones no aplican a A-01, pero condicionan los aspectos que vienen después. Se dejan
anotadas para que, cuando se especifiquen esos aspectos, su escenario de calidad parta de
ellas en vez de definirse desde cero.

<a id="t-1"></a>

### T-1 · Sensibilidad de la detección frente a tasa de revisión manual

*Corresponde al aspecto [A-02](#a-02) (RF-02, RF-03 · EC-01, EC-02).*

El OMR debe decidir si una casilla está rellenada a partir de una señal continua —el contraste
de llenado— que varía con la calidad del escaneo: iluminación desigual, inclinación de la
hoja, manchas, marcas tenues a lápiz, borrados parciales que dejan rastro. El umbral de
confianza que separa «marcada» de «ambigua» tiene dos formas de fallar en direcciones
opuestas. Un umbral **demasiado permisivo** califica marcas dudosas como si fueran ciertas y
produce errores silenciosos: se rompe QG-3 y el estudiante paga el error. Un umbral
**demasiado estricto** manda a revisión manual una fracción alta de las preguntas y el sistema
deja de ahorrar tiempo: se cumple la precisión, pero se pierde la razón de ser del sistema.

La tensión, entonces, no es entre precisión y velocidad de cómputo, sino entre **exactitud y
carga de trabajo humana residual**. Fijar el umbral es una decisión que necesita evidencia —el
dataset de 300 hojas del riesgo R-01— y debe registrarse en un ADR con la curva medida, no
elegirse por intuición.

**Lo que dijo la primera medición** ([ADR-0023](adr/0023-leer-las-hojas-en-posiciones-fijas-y-mandar-a-revision-lo-que-no-se-ve-bien.md)).
Con el umbral de 70, en las 300 hojas sintéticas fueron a revisión sin necesitarlo 0,46 preguntas
por hoja, todas por el brillo, y ninguna respuesta se leyó mal sin aviso. En las fotos del
prototipo el brillo pesó más: en la inclinada, las 12 marcas de lápiz de la 1 a la 12 fueron a
revisión, y en la de arriba, el código entero. Es el lado seguro de la tensión, y por eso la
pantalla de carga pide tomar la foto sin luz directa. El ADR deja escrito qué dato lo haría
revisar: más de tres preguntas por hoja a revisión en un examen real. La curva contra hojas reales
sigue pendiente (R-01, R-04).

<a id="t-2"></a>

### T-2 · [Retirada] Determinismo sintáctico frente a equivalencia matemática en SymPy

*Correspondía al aspecto [A-04](#a-04) (RF-06, RF-07 · EC-05). Retirada por
[ADR-0004](adr/0004-quitar-validacion-simbolica-obligatoria-de-la-clave.md), 2026-08-24.*

Una misma respuesta correcta puede escribirse de varias formas algebraicas no idénticas: por
ejemplo, `1 − cos²(x)` y `sin²(x)` son la misma cosa escrita distinto. Esto importaba en la
**fase de autoría**, al validar que un examen es correcto: si la comparación entre la opción
correcta y los distractores se hace por cadena de texto, dos distractores matemáticamente
equivalentes pasan la validación y se habilita un examen con dos respuestas correctas.

Esta tensión existía porque el diseño original resolvía el problema con software: verificar la
equivalencia real exige simplificación simbólica o evaluación numérica (SymPy), con mayor
costo de cómputo y casos límite que manejar (expresiones que SymPy no logra simplificar,
equivalencias que solo valen en un dominio restringido). El profesor confirmó que esa
automatización no es necesaria, así que la tensión entre «comparar por texto» y «comparar por
equivalencia matemática» deja de ser una decisión de software: la comparación pasa a hacerla
el profesor al aprobar la clave.

> **El riesgo que describía esta tensión no desaparece, se traslada.** Antes era «el software
> puede no detectar una equivalencia no evidente»; ahora es «el profesor puede no detectarla»
> bajo presión de tiempo. ADR-0004 documenta esa contrapartida explícitamente como una
> consecuencia negativa aceptada, no como un riesgo resuelto.
