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

**La porción de la S9 es [A-06](#a-06)** (RF-11, escenario [EC-08](arc42/arc42-template-ES.md#ec-08), [ADR-0013](adr/0013-consumir-groq-detras-de-un-puerto-y-degradar-sin-bloquear-la-autoria.md)). Medida: M1, 0 de 120 propuestas repiten la respuesta correcta; M2, p95 de 2,91 s contra 15 s; M3, 503 en 20,25 s contra 21 s ([evaluación](evidencia/evaluacion-distractores.md)). La prueba falla ante el defecto en el [PR #1](https://github.com/ISCOUTB/AS_202620_Sistema-de-calificacion-automatica/pull/1) ([procedimiento](evidencia/prueba-distractores-falla.md)), y la [auditoría](evidencia/auditoria-s9.md) recorre contextos, propiedad, dependencias y credenciales.

Cada fila enlaza a su escenario de calidad en el arc42. Los ocho escenarios documentados son
alcanzables desde la fila del aspecto que los realiza.

| ID | Aspecto | Estado | Requisito | Escenario de calidad | Contexto C4 (Nivel 1) | C4 | ADR | Código | Pruebas | Evidencia |
|---|---|---|---|---|---|---|---|---|---|---|
| **[A-01](#a-01)** | Carga de examen para calificación | **Construido** | RF-01 | [EC-07](arc42/arc42-template-ES.md#ec-07) | [Rel. 1](c4/doc-c4.md#relaciones): Profesor/TA → Sistema | C1: [QuantIA](c4/doc-c4.md#nivel-1--diagrama-de-contexto-del-sistema) · C2: [Aplicación web](c4/doc-c4.md#nivel-2--diagrama-de-contenedores), [Almacén de imágenes](c4/doc-c4.md#nivel-2--diagrama-de-contenedores), [Cola de trabajos](c4/doc-c4.md#nivel-2--diagrama-de-contenedores) | [0002](adr/0002-procesar-calificacion-de-forma-asincrona.md) · [0006](adr/0006-registrar-la-recepcion-en-una-bitacora-antes-de-encolar.md) | [`ingesta/recepcion.py`](../backend/ingesta/recepcion.py) · [`infraestructura/almacen.py`](../backend/infraestructura/almacen.py) · [`infraestructura/bitacora.py`](../backend/infraestructura/bitacora.py) · [`infraestructura/modelo.py`](../backend/infraestructura/modelo.py) · [`api/main.py`](../backend/api/main.py) · [`frontend/lib/pantalla_carga.dart`](../frontend/lib/pantalla_carga.dart) | [`test_recepcion.py`](../backend/tests/test_recepcion.py) · [`test_durabilidad_recepcion.py`](../backend/tests/test_durabilidad_recepcion.py) · [`test_carga_hojas.py`](../backend/tests/test_carga_hojas.py) · [`widget_test.dart`](../frontend/test/widget_test.dart) | [Medición de EC-07](evidencia/medicion-ec07.md): 1,744 s contra ≤10 s · 0 % de pérdida silenciosa · [captura](#a-01-evidencia) |
| **[A-02](#a-02)** | Detección de marcas y nivel de confianza | Declarado | RF-02, RF-03 | [EC-01](arc42/arc42-template-ES.md#ec-01) · [EC-02](arc42/arc42-template-ES.md#ec-02) | **Sin contexto propio** — proceso interno, no cruza la frontera del sistema (ver nota abajo) | Pendiente | ADR de umbral previsto (R-04) | Pendiente | Pendiente | Pendiente |
| **[A-03](#a-03)** | Calificación contra la clave y publicación | Declarado | RF-04, RF-05, RF-08 | [EC-03](arc42/arc42-template-ES.md#ec-03) · [EC-04](arc42/arc42-template-ES.md#ec-04) | [Rel. 2](c4/doc-c4.md#relaciones): Sistema → Profesor/TA | Pendiente | [0002](adr/0002-procesar-calificacion-de-forma-asincrona.md) | Pendiente | Pendiente | Pendiente |
| **[A-04](#a-04)** | Registro del banco y habilitación del examen | Declarado | RF-06, RF-07 | [EC-05](arc42/arc42-template-ES.md#ec-05) | [Rel. 1](c4/doc-c4.md#relaciones): Profesor/TA → Sistema | Pendiente | [0003](adr/0003-usar-fastapi-y-flutter.md) · [0004](adr/0004-quitar-validacion-simbolica-obligatoria-de-la-clave.md) · [0005](adr/0005-acotar-el-llm-a-la-generacion-de-distractores-diagnosticos.md) | Pendiente | Pendiente | Pendiente |
| **[A-05](#a-05)** | Identidad y aislamiento por curso | Declarado | RF-09, RF-10 | [EC-06](arc42/arc42-template-ES.md#ec-06) | [Rel. 1 y 2](c4/doc-c4.md#relaciones): transversal a ambas — condición de «docente autenticado» bajo la que operan | Pendiente | ADR de auditoría previsto (RF-10) | Pendiente | Pendiente | Pendiente |
| **[A-06](#a-06)** | Propuesta de distractores diagnósticos | **Construido** | RF-11 *(opcional)* | [EC-08](arc42/arc42-template-ES.md#ec-08) | [Rel. 3](c4/doc-c4.md#relaciones): Sistema → Proveedor de LLM (opcional) | C1: [Proveedor de LLM](c4/doc-c4.md#nivel-1--diagrama-de-contexto-del-sistema) · C2: [Aplicación web → Proveedor de LLM](c4/doc-c4.md#relaciones-1) (relación 8) · C3: [`autoria`](c4/doc-c4.md#nivel-3--diagrama-de-componentes) | [0005](adr/0005-acotar-el-llm-a-la-generacion-de-distractores-diagnosticos.md) · [0013](adr/0013-consumir-groq-detras-de-un-puerto-y-degradar-sin-bloquear-la-autoria.md) | [`autoria/distractores.py`](../backend/autoria/distractores.py) · [`autoria/proveedor_llm.py`](../backend/autoria/proveedor_llm.py) · [`api/main.py`](../backend/api/main.py) (`POST /distractores`) | [`test_distractores.py`](../backend/tests/test_distractores.py) · [`test_proveedor_llm.py`](../backend/tests/test_proveedor_llm.py) · [`test_ruta_distractores.py`](../backend/tests/test_ruta_distractores.py) | [Evaluación de EC-08](evidencia/evaluacion-distractores.md): M1: 0 de 120 propuestas repiten la respuesta correcta · M2: p95 de 2,91 s contra 15 s · M3: 503 en 20,25 s contra 21 s · [la prueba falla ante el defecto](evidencia/prueba-distractores-falla.md) · [auditoría](evidencia/auditoria-s9.md) |

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
[Nivel 3 del C4](c4/doc-c4.md#nivel-3--diagrama-de-componentes), donde `omr` es un componente previsto del worker. A-05, en cambio, sí se ancla a las relaciones
existentes aunque no dibuje una propia: es la condición de autenticación y aislamiento por curso
bajo la que ya operan las relaciones 1 y 2 con el Profesor/TA, no una comunicación adicional que
falte por trazar. **En el mapa de contextos de §8.1, en cambio, A-02 sí tiene
contexto y es OMR**: la palabra «contexto» significa cosas distintas en el Nivel 1 del C4 y en el
mapa de contextos, y esta es la fila donde más se nota. Ver también la [sección 8.3 del arc42](arc42/arc42-template-ES.md#83-propiedad-de-datos)
para la misma trazabilidad vista desde qué módulo y qué dato realiza cada aspecto.

A-01 y A-06 son los aspectos construidos. Los demás están declarados para fijar el orden de trabajo y
para que cada escenario de calidad tenga un aspecto responsable; cada uno se especifica cuando se
levanta lo que lo bloquea, que está escrito en su sección («Por qué no se trabaja todavía»).

**Por qué A-01 está en «Construido».** Los pasos 5 a 7 (construir, verificar y evidenciar) están
hechos y son comprobables: el código y las pruebas están en la fila de la tabla, y las dos cifras
de EC-07 están medidas con una herramienta versionada
([`evidencia/medicion-ec07.md`](evidencia/medicion-ec07.md)): confirmación del lote en 1,744 s
contra un techo de 10 s, y 0 % de pérdida silenciosa. Lo que sigue abierto (el medio definitivo
de almacenamiento y la retención de RNF-14) depende de R-06, no de A-01.

**Por qué A-06 está en «Construido».** Los pasos 5 a 7 están hechos en la S9: el código, las
pruebas y la evaluación de EC-08 están en la fila de la tabla, y las tres medidas del escenario
se midieron con una herramienta versionada: M1, ninguna de las 120 propuestas entregadas repite la respuesta correcta (0 %); M2, p95 de la latencia de 2,91 s contra un techo de 15 s, en 40 solicitudes; M3, con el proveedor caído o lento la ruta responde 503 en 20,25 s como máximo, contra 21 s. Lo que sigue
abierto es la pantalla del sitio: hoy RF-11 se usa por la API.

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
| Pantalla de carga y reporte | [`frontend/lib/pantalla_carga.dart`](../frontend/lib/pantalla_carga.dart) |
| Llamada al endpoint | [`frontend/lib/servicio_carga.dart`](../frontend/lib/servicio_carga.dart) |
| Diálogo de archivos del navegador | [`frontend/lib/selector_archivos.dart`](../frontend/lib/selector_archivos.dart) |

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
reintentar sin pedirle el archivo al docente. Siguen abiertos el reintento automático, que es
trabajo de A-02, y el caso de una hoja que llegó a la cola pero el worker no terminó de procesar:
la cola no tiene acuse de recibo.

El `examen_id` tampoco se verifica contra nada, porque el módulo `autoria` (aspecto A-04) es el
que registrará los exámenes y aún no existe. La ruta ya tiene su forma definitiva para que
cuando A-04 llegue solo haya que sumar la comprobación.

### 6. Verificar

**35 pruebas automatizadas de este aspecto**: 31 en el backend y 4 de widget en el frontend.
(La suite de widget tiene 6; las otras dos son las de conexión que ya traía el esqueleto.) Trece
de las del backend llegaron con [ADR-0006](adr/0006-registrar-la-recepcion-en-una-bitacora-antes-de-encolar.md)
y cubren el caso que antes rompía EC-07: la cola que se cae con el lote a medio procesar.

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
| La pantalla no ofrece cargar si el backend no responde | No llevar al docente a una pantalla que va a fallar | [`widget_test.dart`](../frontend/test/widget_test.dart) |
| El reporte lista aceptadas y rechazadas con su motivo | EC-07 visible para el usuario | [`widget_test.dart`](../frontend/test/widget_test.dart) |
| Una falla de red se muestra como aviso, no como rechazo | Son cosas distintas y el docente debe distinguirlas | [`widget_test.dart`](../frontend/test/widget_test.dart) |
| Ninguna hoja queda sin reportar si la cola se cae a mitad del lote | La cifra de EC-07 que antes daba 100 % de pérdida | [`test_durabilidad_recepcion.py`](../backend/tests/test_durabilidad_recepcion.py) |
| La hoja no encolada queda pendiente en la bitácora, con su imagen recuperable | Reportarla no basta: el reintento no puede depender del docente | [`test_durabilidad_recepcion.py`](../backend/tests/test_durabilidad_recepcion.py) |
| El estado pendiente se relee desde otro objeto sobre el mismo archivo | Que la bitácora viva en el disco y no en la memoria de quien la escribió | [`test_durabilidad_recepcion.py`](../backend/tests/test_durabilidad_recepcion.py) |
| Una línea truncada no inutiliza la bitácora | El proceso puede morir escribiendo, y las líneas anteriores siguen valiendo | [`test_durabilidad_recepcion.py`](../backend/tests/test_durabilidad_recepcion.py) |
| El endpoint confirma el lote en vez de devolver 500 | Lo que ve el docente, de punta a punta por HTTP | [`test_durabilidad_recepcion.py`](../backend/tests/test_durabilidad_recepcion.py) |
| El lote no insiste contra una cola caída | El techo de 10 s de EC-07 en el camino de fallo | [`test_durabilidad_recepcion.py`](../backend/tests/test_durabilidad_recepcion.py) |
| El corte no se adelanta mientras la cola responde | Que no se dejen de encolar hojas por prudencia mal entendida | [`test_durabilidad_recepcion.py`](../backend/tests/test_durabilidad_recepcion.py) |

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

**Declarado.**

- **Para quién es:** el profesor, que necesita que la lectura sea fiel a lo que el estudiante
  marcó; y el estudiante, que soporta las consecuencias de un error.
- **Qué problema resuelve:** convierte una imagen escaneada en respuestas legibles por el
  sistema, acompañadas de un nivel de confianza que hace explícita la incertidumbre.
- **Requisitos:** RF-02, RF-03.
- **Escenarios:** [EC-01](arc42/arc42-template-ES.md#ec-01) (exactitud ≥98%) ·
  [EC-02](arc42/arc42-template-ES.md#ec-02) (marcas ambiguas ≥99%).
- **Tensión que lo condiciona:** [T-1](#t-1).
- **Por qué no se trabaja todavía:** su escenario principal se mide contra un dataset de 300
  hojas etiquetadas que aún no existe (riesgo R-01), y el umbral de confianza no puede fijarse
  sin esa evidencia (R-04). Es además el aspecto de mayor riesgo técnico del proyecto (R-05).

---

<a id="a-03"></a>

## Aspecto A-03: Calificación contra la clave y publicación de resultados

**Declarado.**

- **Para quién es:** el profesor y el TA, que necesitan la nota y las estadísticas por
  pregunta.
- **Qué problema resuelve:** compara las respuestas detectadas contra la clave habilitada,
  calcula la nota y la publica en el dashboard, permitiendo resolver manualmente lo ambiguo y
  recalcular.
- **Requisitos:** RF-04, RF-05, RF-08.
- **Escenarios:** [EC-03](arc42/arc42-template-ES.md#ec-03) (≤5 s por hoja) ·
  [EC-04](arc42/arc42-template-ES.md#ec-04) (200 hojas en ≤10 min).
- **Decisión que ya lo condiciona:**
  [ADR-0002](adr/0002-procesar-calificacion-de-forma-asincrona.md) — la nota de una hoja con
  preguntas ambiguas queda *provisional* hasta que el docente la resuelva.
- **Por qué no se trabaja todavía:** depende de A-02, que produce su entrada.

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

### 6. Verificar

- [`test_distractores.py`](../backend/tests/test_distractores.py): la regla, y **la prueba del
  defecto**. Sin el descarte de la respuesta correcta fallan 4 pruebas, y se demostró con un PR
  que no se fusionó ([procedimiento y runs](evidencia/prueba-distractores-falla.md)).
- [`test_proveedor_llm.py`](../backend/tests/test_proveedor_llm.py): RNF-13 sobre el cuerpo
  entero de la solicitud, y la degradación.
- [`test_ruta_distractores.py`](../backend/tests/test_ruta_distractores.py): la ruta (200, 503 y
  422).
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

**Pendiente:** la pantalla del sitio. Hoy RF-11 se usa por la API.

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
- **Por qué no se trabaja todavía:** es transversal a los demás aspectos y conviene
  especificarlo cuando existan al menos dos flujos reales sobre los que aplicarlo.

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
