# Aspectos del sistema

Este documento registra los aspectos identificados para el **Sistema de Calificación OMR**
(calificación automática de exámenes de opción múltiple de cálculo diferencial mediante
reconocimiento óptico de marcas, con generación del banco de preguntas apoyada en LLM y
aprobación manual del profesor sobre la clave de respuestas), siguiendo la metodología de
Aspect Driven Development del curso.

Un aspecto es un corte vertical del sistema, con valor propio, que se puede recorrer completo:

> aspecto → requisito → elementos C4 → ADR → código → pruebas → evidencia de calidad

Cada aspecto se trabaja en siete pasos: declarar, especificar, ubicar, decidir, construir,
verificar y evidenciar.

**Documentos relacionados:** [`arc42/arc42-template-ES.md`](arc42/arc42-template-ES.md)
(requisitos `RF-nn`, restricciones `RNF-nn`, escenarios `EC-nn`) ·
[`c4/doc-c4.md`](c4/doc-c4.md) (diagramas) · [`adr/`](adr/) (decisiones).

---

## Tabla de trazabilidad

Cada fila enlaza a su escenario de calidad en el arc42. Los siete escenarios documentados son
alcanzables desde la fila del aspecto que los realiza.

| ID | Aspecto | Estado | Requisito | Escenario de calidad | C4 | ADR | Código | Pruebas | Evidencia |
|---|---|---|---|---|---|---|---|---|---|
| **[A-01](#a-01)** | Carga de examen para calificación | Especificado | RF-01 | [EC-07](arc42/arc42-template-ES.md#ec-07) | C1: Sistema de Calificación OMR · C2 pendiente (S4) | [0002](adr/0002-procesar-calificacion-de-forma-asincrona.md) | Pendiente (S4) | Pendiente (S4) | Pendiente (S4) |
| **[A-02](#a-02)** | Detección de marcas y nivel de confianza | Declarado | RF-02, RF-03 | [EC-01](arc42/arc42-template-ES.md#ec-01) · [EC-02](arc42/arc42-template-ES.md#ec-02) | Pendiente (S4) | ADR de umbral previsto (S4) | Pendiente | Pendiente | Pendiente |
| **[A-03](#a-03)** | Calificación contra la clave y publicación | Declarado | RF-04, RF-05, RF-08 | [EC-03](arc42/arc42-template-ES.md#ec-03) · [EC-04](arc42/arc42-template-ES.md#ec-04) | Pendiente (S4) | [0002](adr/0002-procesar-calificacion-de-forma-asincrona.md) | Pendiente | Pendiente | Pendiente |
| **[A-04](#a-04)** | Registro del banco y habilitación del examen | Declarado | RF-06, RF-07, RF-11 | [EC-05](arc42/arc42-template-ES.md#ec-05) | Pendiente (S4) | [0003](adr/0003-usar-fastapi-y-flutter.md) · [0004](adr/0004-quitar-validacion-simbolica-obligatoria-de-la-clave.md) · [0005](adr/0005-acotar-el-llm-a-la-generacion-de-distractores-diagnosticos.md) | Pendiente | Pendiente | Pendiente |
| **[A-05](#a-05)** | Identidad y aislamiento por curso | Declarado | RF-09, RF-10 | [EC-06](arc42/arc42-template-ES.md#ec-06) | Pendiente (S4) | ADR de auditoría previsto (S6) | Pendiente | Pendiente | Pendiente |

**Estados:** *Declarado* = pasos 1 y 3 parciales (nombre, para quién, qué resuelve, requisitos
y escenario asignados). *Especificado* = pasos 1 a 4 completos. *Construido* = pasos 5 a 7.

A-01 es el único aspecto que se trabaja completo en esta entrega. Los demás se declaran para
fijar el orden de trabajo y para que cada escenario de calidad tenga un aspecto responsable
desde ya; se especificarán en las semanas 4 y 6.

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

**Nivel 1 (contexto):** el aspecto se realiza dentro de la caja «Sistema de Calificación OMR»,
en la relación *Profesor / TA → Sistema*. Está enteramente dentro del sistema; no involucra
ningún sistema externo. Ver [`c4/doc-c4.md`](c4/doc-c4.md).

**Nivel 2 (contenedores):** pendiente hasta la semana 4. Según ADR-0002, el aspecto atravesará
la **aplicación web** (recepción HTTP y validación), el **almacén de imágenes** (persistencia
del archivo) y la **cola de trabajos** (encolado del procesamiento).

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
escaneos no pueden conservarse indefinidamente). Se pospone a la semana 4 porque depende de la
decisión de persistencia, todavía abierta (riesgo R-06 del arc42).

### 5. Construir

Pendiente. No existe código para este aspecto en esta entrega.

### 6. Verificar

Pendiente. Pruebas previstas:

- Validación de formato: acepta JPG, PNG y PDF; rechaza el resto indicando el motivo.
- Carga en lote: el número de trabajos encolados coincide con el de archivos aceptados.
- Durabilidad: un archivo aceptado y su trabajo sobreviven al reinicio del proceso. Es la que
  realmente cubre el «0% de pérdida silenciosa» de EC-07.
- Autorización: un docente no puede cargar hojas en un curso que no tiene asignado (RNF-05).

### 7. Evidenciar

Pendiente. No existe evidencia de calidad para este aspecto en esta entrega.

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

**Declarado.** Se especifica en la semana 4.

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

**Declarado.** Se especifica en la semana 4.

- **Para quién es:** el profesor y el TA, que necesitan la nota y las estadísticas por
  pregunta.
- **Qué problema resuelve:** compara las respuestas detectadas contra la clave validada,
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

**Declarado.** Se especifica en la semana 6.

- **Para quién es:** el profesor que prepara el examen.
- **Qué problema resuelve:** recibe el banco de preguntas y la clave que el profesor trae
  escritos, y garantiza que ningún examen se califique sin que él lo haya habilitado
  explícitamente, dejando registro de quién lo hizo y cuándo. Opcionalmente le propone
  distractores diagnósticos para ayudarlo a construir las preguntas (RF-11).
- **Requisitos:** RF-06, RF-07, RF-11 *(opcional)*.
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
- **Restricción legal relevante:** RNF-13 — ningún dato personal de estudiantes se envía al
  proveedor de LLM. Este aspecto es el único que se comunica con un servicio externo, así que
  es donde esa restricción se hace efectiva.
- **Por qué no se trabaja todavía:** requiere haber decidido el proveedor de LLM y su modo de
  consumo (riesgo R-02).

---

<a id="a-05"></a>

## Aspecto A-05: Identidad y aislamiento de datos por curso

**Declarado.** Se especifica en la semana 6.

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

> **Nota sobre una corrección de alcance.** Una versión anterior de este documento describía
> tensiones de **OCR de expresiones manuscritas** (ambigüedad caligráfica entre la variable
> *x* y el operador de producto, entre exponentes y constantes), heredadas del informe inicial
> del grupo. Ese alcance quedó descartado en la transición a OMR registrada en `ia.md`
> (Entrada 2): el sistema lee **marcas en casillas de posición fija**, no escritura a mano,
> tal como fijan RNF-02 y RNF-03. T-1 se reescribió para reflejar el sistema que efectivamente
> se está construyendo; T-2 se conservó entonces y se reubicó en la fase donde realmente
> ocurría. Ahora, con ADR-0004, T-2 se retira a su vez porque esa fase dejó de resolverse por
> software.
