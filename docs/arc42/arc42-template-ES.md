---
date: 2026-08-23
title: "Arquitectura del Sistema de Calificación OMR"
---

# **About arc42**

arc42, la plantilla para documentar arquitecturas de software y de sistemas.

Versión de plantilla 9.0. Creada y mantenida por Dr. Peter Hruschka, Dr. Gernot Starke
y colaboradores. Ver [https://arc42.org](https://arc42.org).

**Estado de este documento:** semana 2 del curso. Las secciones 1 a 3 y la 10 están
escritas; las secciones 5 a 9 y 11 se completan en las semanas 4 y 6, y cada una indica
explícitamente cuándo se llena y por qué todavía no se puede.

**Convenciones de identificadores usadas en todo el repositorio:**

| Prefijo | Significado | Dónde se define |
|---|---|---|
| `RF-nn` | Requisito funcional | Sección 1.1 de este documento |
| `RNF-nn` | Requisito no funcional / de proyecto | Sección 2 (Restricciones) |
| `EC-nn` | Escenario de calidad | Sección 10.2 de este documento |
| `A-nn` | Aspecto (corte vertical) | `docs/aspectos.md` |
| `ADR-nnnn` | Decisión de arquitectura | `docs/adr/` |

---

# 1. Introduction and Goals

## 1.1 Requirements Overview

El **Sistema de Calificación OMR** automatiza la evaluación y calificación de exámenes de
opción múltiple para la asignatura de **Cálculo Diferencial** en facultades de ingeniería,
ciencias exactas y economía. La solución integra **Reconocimiento Óptico de Marcas (OMR)**,
**Modelos de Lenguaje (LLM)** y **Computación Simbólica (SymPy)** para ofrecer un flujo
extremo a extremo seguro, preciso e interactivo.

El sistema opera en **dos fases temporalmente separadas**, distinción que condiciona toda la
arquitectura:

- **Fase de autoría (antes del examen):** el profesor construye el banco de preguntas con
  apoyo de LLM y el sistema valida simbólicamente la clave con SymPy. Es una fase sin
  presión de tiempo real.
- **Fase de calificación (después del examen):** el sistema ingesta escaneos, detecta marcas
  y produce notas. Es la fase con exigencias de latencia y de volumen (EC-03, EC-04).

### Funcionalidades principales

| ID | Requisito funcional | Fase |
|---|---|---|
| **RF-01** | El sistema debe permitir a un docente autenticado cargar exámenes escaneados (JPG, PNG o PDF), individualmente o en lote, y confirmar su recepción. | Calificación |
| **RF-02** | El sistema debe detectar, para cada pregunta de una hoja escaneada, la casilla marcada, junto con un nivel de confianza asociado a esa detección. | Calificación |
| **RF-03** | El sistema debe marcar como *requiere revisión manual* toda detección cuya confianza no supere el umbral configurado, en lugar de asignar una respuesta arbitraria. | Calificación |
| **RF-04** | El sistema debe comparar las respuestas detectadas contra la clave validada del examen y calcular la calificación resultante. | Calificación |
| **RF-05** | El sistema debe presentar los resultados en un dashboard interactivo con notas por curso, estadísticas por examen y por pregunta, y alertas de revisión manual. | Calificación |
| **RF-06** | El sistema debe permitir crear bancos de preguntas de cálculo diferencial (límites, derivadas y simplificaciones algebraicas), con apoyo de un LLM para la generación de enunciados y distractores. | Autoría |
| **RF-07** | El sistema debe verificar simbólicamente con SymPy que exactamente una opción es equivalente a la respuesta esperada, y alertar cuando dos distractores sean matemáticamente equivalentes entre sí, antes de habilitar el examen. | Autoría |
| **RF-08** | El sistema debe permitir a un docente resolver manualmente las preguntas marcadas como ambiguas y recalcular la nota afectada. | Calificación |
| **RF-09** | El sistema debe restringir el acceso a usuarios registrados y limitar cada docente a los cursos que tiene autorizados. | Transversal |

## 1.2 Quality Goals

Los cuatro objetivos de calidad primarios que guían la arquitectura. Cada uno se hace
verificable a través de los escenarios de calidad de la sección 10.

| # | Objetivo de calidad | Por qué es prioritario | Escenarios que lo verifican |
|---|---|---|---|
| **QG-1** | **Precisión y validez matemática.** Lectura OMR altamente confiable y clave de respuestas libre de ambigüedades algebraicas antes de la aplicación. | Una nota mal calculada tiene consecuencias académicas directas y erosiona la confianza en el sistema de forma irreversible. | EC-01, EC-05 |
| **QG-2** | **Rendimiento y eficiencia de procesamiento.** Calificar exámenes individuales en segundos y lotes masivos en minutos. | Si calificar con el sistema no es más rápido que calificar a mano, el sistema no tiene razón de existir. | EC-03, EC-04 |
| **QG-3** | **Manejabilidad de casos borde (degradación controlada).** Ninguna marca dudosa se convierte en una calificación silenciosamente errónea. | Es la contraparte necesaria de QG-1: la precisión perfecta no existe, así que el sistema debe *saber* cuándo no sabe. | EC-02 |
| **QG-4** | **Seguridad y aislamiento por rol.** Cada docente accede únicamente a los datos y calificaciones de sus cursos autorizados. | Las calificaciones son datos académicos sensibles y su manipulación indebida es un riesgo institucional, no solo técnico. | EC-06 |

> **Nota sobre disponibilidad.** El árbol de utilidad (sección 10.1) incluye disponibilidad
> y mantenibilidad como atributos relevantes, pero no se elevan a objetivo de calidad
> primario: en el contexto de un sistema de uso interno y por lotes, una indisponibilidad
> breve se absorbe reintentando la carga, mientras que un error de precisión no se absorbe.
> Se documentan y se miden, pero no dominan las decisiones de diseño.

## 1.3 Stakeholders

| Stakeholder | Rol frente al sistema | Contacto | Expectativas |
|---|---|---|---|
| **Profesores de Cálculo / Cátedra** | Usuario principal | docentes.calculo@utb.edu | Reducir drásticamente el tiempo de calificación de exámenes masivos. Garantizar que las claves no contengan ambigüedades matemáticas. Disponer de un dashboard con métricas por curso y por pregunta. |
| **Asistentes de Cátedra (TAs)** | Usuario operativo | tas.ingenieria@utb.edu | Ingesta ágil en lote de imágenes escaneadas. Interfaz clara para resolver manualmente las preguntas clasificadas como ambiguas. |
| **Comité Académico / Dirección de Programa** | Patrocinador y auditor | direccion.sistemas@utb.edu | Alta precisión y confiabilidad de las calificaciones. Seguridad, confidencialidad y auditabilidad del almacenamiento de notas. |
| **Administradores de TI / Sistema** | Operador | admin.sys@utb.edu | Sistema modular, mantenible y desacoplado, con bajo consumo de CPU/memoria. Disponibilidad ≥95% en periodos críticos. |
| **Estudiantes** | Afectado, **no usuario** | — | Que su respuesta sea leída como la marcó y que una marca dudosa no se convierta en un error en su contra. No interactúan con el sistema (ver Restricción 5); se listan porque son quienes soportan las consecuencias de un fallo de QG-1 y QG-3. |
| **Equipo de desarrollo** | Constructor | Josué Ortega, María Restrepo, Sebastián Cañas, Susana Rosales | Un repositorio que arranque de forma reproducible y una estructura que permita trabajar en la lógica de negocio sin pelear con el montaje. |

---

# 2. Architecture Constraints

Las siguientes restricciones fijan los límites del diseño. Cada una está justificada según el
contexto del proyecto. Las restricciones 1 a 6 provienen del enunciado del problema; la 7
proviene de las condiciones de entrega del curso.

| ID | Restricción | Justificación |
|---|---|---|
| **RNF-01** | **Stack obligatorio: OMR + LLM + SymPy.** | El planteamiento del problema fija la solución técnica desde el enunciado: la calificación se realiza mediante OMR, y la generación y validación del banco de preguntas mediante LLM y SymPy. No es una decisión libre del equipo; cualquier arquitectura alternativa queda fuera del alcance. Es la restricción más determinante porque condiciona todos los componentes. |
| **RNF-02** | **Entrada: hoja de respuestas estructurada de opción múltiple.** | El examen se resuelve en una hoja física con formato estandarizado (casillas en posiciones fijas), no en papel de escritura libre. Obliga a que el layout sea fijo y conocido de antemano para que el OMR pueda localizar las marcas, y descarta formatos de examen irregulares. |
| **RNF-03** | **Diseño de examen: solo preguntas evaluables como opción múltiple.** | Al procesar marcas y no expresiones escritas, el sistema solo puede evaluar preguntas con una única respuesta final identificable entre varias opciones. Las preguntas de desarrollo o demostración quedan fuera de alcance. Define directamente cómo se construye el banco de preguntas. |
| **RNF-04** | **Dominio: cálculo diferencial.** | El alcance temático se limita a límites, derivadas y simplificaciones algebraicas. Acota el motor de validación simbólica y evita sobredimensionar el sistema para integrales, ecuaciones diferenciales o álgebra lineal. |
| **RNF-05** | **Usuarios objetivo: profesores y TAs, no estudiantes.** | El sistema está dirigido a docentes y asistentes de cátedra. El estudiante es únicamente la fuente de las marcas en la hoja, pero no es usuario ni interactúa con el sistema. Condiciona el diseño de roles, autenticación y permisos: no existe interfaz ni cuenta de estudiante, y todo el flujo de interacción se diseña para el rol docente. |
| **RNF-06** | **Salida: presentación en dashboard.** | El planteamiento especifica que los resultados se presentan en un dashboard, no como archivo aislado ni reporte por correo. Fija que la arquitectura debe incluir una capa de visualización con la que el docente interactúe, y una estructura de datos pensada para agregación (por curso, examen y pregunta), no solo para almacenamiento. |
| **RNF-07** | **Arranque reproducible con un solo comando.** | Condición de entrega del curso: el repositorio debe levantarse con un único comando y presentar un esqueleto ejecutable con una prueba automatizada en verde. Esta restricción es la que más peso tiene en la decisión registrada en [ADR-0001](adr/0001-usar-monolito-modular.md), porque penaliza cualquier topología que exija orquestar varios despliegues. |

---

# 3. Context and Scope

## 3.1 Business Context

El sistema recibe insumos físicos digitalizados (hojas de respuestas escaneadas) y los
convierte en calificaciones y métricas analíticas para los usuarios docentes.

| Socio de comunicación | Entradas al sistema | Salidas desde el sistema |
|---|---|---|
| **Profesor / TA** | Creación y edición de bancos de preguntas; claves de respuesta; parámetros de evaluación; archivos escaneados de exámenes (imágenes o PDF); resolución manual de casos ambiguos. | Vistas del dashboard interactivo; reportes consolidados por curso; analítica de ítems por pregunta; alertas de casos dudosos y de claves inválidas. |
| **Proveedor de LLM** *(pendiente de decisión, ver sección 11)* | Enunciados y parámetros para generación de preguntas y distractores. | Preguntas y distractores candidatos, que **siempre** pasan después por la validación simbólica de SymPy antes de aceptarse. |

> **Nota de modelado.** La *hoja de respuestas física* no se representa como socio de
> comunicación. Un documento en papel no es un actor ni un sistema: es el **artefacto de
> entrada** que el docente digitaliza y carga. Quien se comunica con el sistema es el
> docente; la hoja es el contenido de esa comunicación. El escáner tampoco aparece porque
> es una herramienta ofimática ajena al sistema, cuya salida (un archivo) el docente sube
> manualmente.

## 3.2 Technical Context

El diagrama de Nivel 1 y su leyenda se mantienen en [`docs/doc-c4.md`](doc-c4.md), que es la
fuente única de los diagramas C4. Aquí se documentan las interfaces técnicas y su
correspondencia con los canales de negocio.

| Canal / Interfaz | Entrada | Salida | Protocolo / Formato | Mapeo con 3.1 |
|---|---|---|---|---|
| **Interfaz Web (Dashboard)** | Autenticación, gestión de cursos y bancos de preguntas, carga de escaneos, resolución de marcas ambiguas | Notas, gráficos, alertas de ambigüedad y de clave inválida | HTTPS · HTML5 / CSS / JSON | Profesor / TA |
| **Canal de ingesta OMR** | Lote de imágenes o PDF de hojas escaneadas | Matriz de respuestas detectadas con nivel de confianza (%) por pregunta | Carga HTTP multipart; procesamiento con OpenCV sobre PNG, JPG o PDF a 300 DPI | Profesor / TA |
| **Motor de validación simbólica (SymPy)** | Expresiones matemáticas de la opción correcta y de los distractores | Veredicto de unicidad y de equivalencia entre opciones | API Python in-process (SymPy es una librería, no un servicio) | — (interno) |
| **Proveedor de LLM** *(pendiente)* | Especificación del tipo de pregunta a generar | Enunciados y distractores candidatos | **Pendiente de decidir.** Si se usa una API alojada, es HTTPS/JSON contra un sistema externo; si se usa un modelo local, es in-process. Ver sección 11. | Proveedor de LLM |

> **Corrección respecto a la versión anterior de este documento:** SymPy y el LLM se
> describían como un único "Motor SymPy / LLM · In-Process Python API". Son dos cosas
> distintas: SymPy es una librería que corre dentro del proceso, mientras que el LLM puede
> ser un servicio externo con latencia de red, costo por uso y modo de fallo propio. Se
> separan porque tienen implicaciones arquitectónicas opuestas.

## 3.3 Fuera de alcance

Se declara explícitamente para evitar que el diagrama de contexto crezca sin control:

- Integración con el sistema académico institucional (publicación automática de notas).
- Interfaz o cuenta para estudiantes (RNF-05).
- Evaluación de preguntas abiertas o de desarrollo (RNF-03).
- Impresión o distribución física de los exámenes generados.

---

# 4. Solution Strategy

Resumen de las decisiones fundamentales tomadas hasta ahora y su relación con los objetivos
de calidad. Cada decisión estructural tiene su registro detallado en `docs/adr/`.

| Decisión | Motivación | Objetivo de calidad al que sirve | Registro |
|---|---|---|---|
| **Monolito modular** con módulos de límites explícitos (`autoria`, `ingesta`, `omr`, `calificacion`, `dashboard`, `identidad`, `infraestructura`). | Un único despliegue satisface RNF-07 (arranque con un solo comando) sin renunciar a fronteras internas claras que permitan trabajar y probar cada módulo por separado. | QG-2 (indirectamente), mantenibilidad | [ADR-0001](adr/0001-usar-monolito-modular.md) |
| **Procesamiento asíncrono con cola de trabajos y workers** para la calificación de lotes; la respuesta HTTP confirma la recepción, no la calificación. | Es la única forma de cumplir EC-04 (200 hojas en ≤10 min) sin romper EC-03 (≤5 s por hoja): procesando en paralelo. Además da la persistencia del trabajo pendiente que exige la recuperación ante fallos. | QG-2 | [ADR-0001](adr/0001-usar-monolito-modular.md) |
| **Umbral de confianza explícito** en la detección OMR, con desvío a revisión manual en vez de decisión automática. | El OMR es intrínsecamente probabilístico. Convertir la incertidumbre en un estado visible del sistema (*requiere revisión*) es preferible a ocultarla tras una respuesta inventada. | QG-1, QG-3 | Pendiente (ADR previsto en semana 4) |
| **Validación simbólica obligatoria antes de habilitar un examen**: ninguna pregunta generada por LLM se acepta sin pasar por SymPy. | El LLM genera texto plausible, no matemáticas correctas. SymPy actúa como verificador determinista sobre una salida no determinista. | QG-1 | Pendiente (ADR previsto en semana 4) |
| **Separación temporal entre fase de autoría y fase de calificación.** | Aísla la dependencia del LLM (lenta, externa, potencialmente costosa) de la ruta crítica de calificación, que es donde están las exigencias de latencia. | QG-2 | Implícita en ADR-0001 |

---

### Estrategias técnicas

- **Frontend:** Se utilizará **Flutter** para construir la interfaz principal, ya que permite desarrollar una aplicación con una base de código común y una interfaz consistente. Esto facilita el mantenimiento y reduce el esfuerzo de desarrollo.
- **Panel de administración:** Se utilizarán **HTML, CSS y JavaScript** para el panel administrativo, por ser tecnologías ligeras y adecuadas para interfaces web con formularios, tablas, filtros y visualización de resultados.
- **Backend:** Se utilizará **Python** para implementar la lógica del sistema y los servicios del backend. Su ecosistema facilita la integración con OMR, SymPy, procesamiento de imágenes y modelos de IA, evitando añadir complejidad innecesaria.
- **Arquitectura:** Las tecnologías se mantienen separadas por responsabilidades: Flutter y el panel web se encargan de la interacción con el usuario, mientras Python concentra la lógica de negocio y el procesamiento. Esto permite modificar una parte sin afectar directamente a las demás.

### Criterios de calidad

- **Seguridad:** La separación entre frontend, panel administrativo y backend permite centralizar la autenticación, autorización y validación de datos en el backend. Así, los permisos por rol y por curso no dependen únicamente de la interfaz.
- **Rendimiento:** Python permite ejecutar el procesamiento OMR y las operaciones de cálculo en el backend, mientras que el procesamiento asíncrono con workers evita bloquear las peticiones del usuario. Esto ayuda a cumplir los tiempos establecidos para la calificación individual y por lotes.
- **Escalabilidad:** La separación de responsabilidades permite aumentar los recursos del backend y de los workers cuando crezca la cantidad de exámenes, sin tener que modificar las interfaces de usuario. Además, el diseño modular facilita incorporar nuevos componentes posteriormente.
- **Mantenibilidad:** El uso de tecnologías específicas para cada capa reduce el acoplamiento y facilita que cada parte pueda desarrollarse, probarse y actualizarse de forma independiente.

---

# 5. Building Block View

> **Pendiente — se completa en la semana 4.** Esta sección requiere que el diagrama C4 de
> Nivel 2 esté cerrado y que los contenedores correspondan a unidades desplegables reales,
> lo cual todavía no ocurre: en la semana 2 solo existe el Nivel 1. Documentar aquí una
> descomposición ahora sería documentar lo que se quisiera tener, no lo que hay.
>
> La descomposición prevista, ya anticipada en ADR-0001, es de siete módulos:
> `autoria`, `ingesta`, `omr`, `calificacion`, `dashboard`, `identidad` e `infraestructura`.

## 5.1 Whitebox Overall System

> Pendiente — semana 4, junto con el C4 Nivel 2.

## 5.2 Level 2

> Pendiente — semana 4.

## 5.3 Level 3

> Pendiente — semanas 4 y 6, junto con el C4 Nivel 3.

---

# 6. Runtime View

> **Pendiente — se completa en la semana 4.** Los escenarios de ejecución previstos, en
> orden de prioridad, son:
>
> 1. **Calificación de un lote de exámenes** (recorre RF-01 → RF-02 → RF-03 → RF-04 → RF-05
>    y es el escenario donde se manifiestan EC-03 y EC-04).
> 2. **Resolución manual de una marca ambigua** (RF-08, verifica EC-02).
> 3. **Generación y validación de un examen** (RF-06 → RF-07, verifica EC-05).
>
> No se describen todavía porque la interacción entre bloques depende de la descomposición
> de la sección 5, que aún no está cerrada.

---

# 7. Deployment View

> **Pendiente — se completa en la semana 4.** No se documenta todavía porque el equipo no ha
> decidido el entorno de despliegue (servidor institucional, contenedor local o PaaS), y esa
> decisión depende a su vez de si el LLM se consume como API externa o se aloja localmente
> (ver sección 11). Documentar una topología ahora sería especulación.

---

# 8. Cross-cutting Concepts

> **Pendiente — se completa en la semana 4.** Los conceptos transversales ya identificados,
> a la espera de desarrollo:
>
> - **Manejo de la incertidumbre del OMR:** el nivel de confianza como dato de primera clase
>   que acompaña a toda respuesta detectada a lo largo del pipeline.
> - **Seguridad y autorización por curso:** cómo se aplica el aislamiento de RNF-05 y QG-4 de
>   forma uniforme en todos los módulos.
> - **Trazabilidad y auditoría de calificaciones:** registro de quién modificó una nota y
>   cuándo, exigido por el Comité Académico.
> - **Manejo de errores del proveedor de LLM:** política de reintento y degradación cuando la
>   generación falla, sin bloquear la fase de calificación.

---

# 9. Architecture Decisions

Las decisiones se registran una por archivo en `docs/adr/`, siguiendo la convención del
curso. Un ADR aceptado no se edita ni se borra: si la decisión cambia, se escribe uno nuevo
y el anterior pasa a estado *reemplazado por*.

| ADR | Título | Estado | Fecha | Escenarios relacionados |
|---|---|---|---|---|
| [0001](adr/0001-usar-monolito-modular.md) | Usar monolito modular con procesamiento asíncrono | aceptado | 2026-08-22 | EC-03, EC-04 |

**Decisiones previstas (aún no tomadas):**

- Elección del proveedor de LLM y de su modo de consumo (externo vs. local) — ver sección 11.
- Mecanismo de persistencia y de almacenamiento de las imágenes escaneadas.
- Estrategia de calibración del umbral de confianza del OMR.

---

# 10. Quality Requirements

## 10.1 Quality Requirements Overview

El árbol de utilidad organiza los atributos de calidad priorizados por impacto de negocio y
riesgo técnico. Las hojas del árbol marcadas con `EC-nn` están formalizadas como escenarios
en la sección 10.2.

**Precisión** *(→ QG-1, QG-3)*

- **EC-01 · Reconocimiento OMR:** el sistema identifica correctamente la opción marcada con
  ≥98% de exactitud sobre un dataset de prueba de 300 hojas escaneadas.
  *(Impacto: Alto | Riesgo técnico: Alto)*
- **EC-02 · Manejo de marcas ambiguas (degradación controlada):** el sistema identifica como
  ambigua ≥99% de las marcas que no superan el umbral de confianza y las envía a revisión
  manual. *(Impacto: Alto | Riesgo técnico: Alto)*
- **EC-05 · Validez de la clave de respuestas:** el motor LLM + SymPy verifica simbólicamente
  que solo una opción es equivalente a la esperada, en el 100% de los exámenes generados.
  *(Impacto: Alto | Riesgo técnico: Alto)*

**Rendimiento** *(→ QG-2)*

- **EC-03 · Tiempo de respuesta en calificación individual:** procesamiento end-to-end de una
  hoja en ≤5 segundos (percentil 95). *(Impacto: Medio | Riesgo técnico: Medio)*
- **EC-04 · Escalabilidad ante carga masiva:** un lote de 200 hojas se procesa completo en
  ≤10 minutos, con uso de CPU y memoria por debajo del 85%.
  *(Impacto: Alto | Riesgo técnico: Alto)*
- **EC-07 · Confirmación fiable de recepción del lote:** la carga confirma en ≤10 segundos y
  ningún archivo cargado se pierde sin dejar traza. *(Impacto: Alto | Riesgo técnico: Bajo)*

**Seguridad** *(→ QG-4)*

- **EC-06 · Aislamiento por curso y por rol:** un docente autenticado no puede leer ni
  modificar datos de un curso que no tiene autorizado, y solo los roles con permiso pueden
  modificar calificaciones. *(Impacto: Alto | Riesgo técnico: Medio)*
- Autenticación: solo acceden usuarios registrados. *(Impacto: Alto | Riesgo técnico: Medio)*

**Escalabilidad** *(atributo secundario, no formalizado como escenario)*

- Crecimiento de datos: el crecimiento del almacenamiento de imágenes no debe degradar
  significativamente el tiempo de respuesta. *(Impacto: Medio | Riesgo técnico: Alto)*
- Usuarios concurrentes: al menos 10 usuarios concurrentes sin errores ni degradación
  significativa. *(Impacto: Medio | Riesgo técnico: Bajo)*

**Disponibilidad** *(atributo secundario)*

- Recuperación ante fallos: ante una falla durante el procesamiento, los exámenes ya cargados
  se conservan y reanudan su procesamiento sin volver a cargarlos.
  *(Impacto: Alto | Riesgo técnico: Alto)*
- Disponibilidad del servicio: ≥95% durante los periodos de evaluación.
  *(Impacto: Alto | Riesgo técnico: Medio)*

**Mantenibilidad** *(atributo secundario, dirige ADR-0001)*

- Modificación: un cambio en un módulo no debe requerir modificaciones en los demás.
  *(Impacto: Medio | Riesgo técnico: Alto)*
- Corrección de errores: una corrección debe poder implementarse sin interrumpir el resto del
  sistema. *(Impacto: Medio | Riesgo técnico: Alto)*

## 10.2 Quality Scenarios

### EC-01 · Exactitud de detección de marcas OMR

| Atributo | Detalle |
|---|---|
| **Fuente** | Profesor |
| **Estímulo** | Sube una hoja de respuestas escaneada con casillas marcadas por el estudiante. |
| **Artefacto** | Módulo `omr` (detección de marcas). |
| **Entorno** | Operación normal, carga individual. |
| **Respuesta** | El sistema identifica correctamente la opción marcada en cada pregunta. |
| **Medida de respuesta** | **≥98% de exactitud** en la detección de la marca correcta, sobre un dataset de prueba de 300 hojas escaneadas con etiquetado manual de referencia. |
| **Relacionado** | QG-1 · RF-02 |

### EC-02 · Manejo de marcas ambiguas (degradación controlada)

| Atributo | Detalle |
|---|---|
| **Fuente** | El propio módulo OMR, al detectar ambigüedad en la hoja. |
| **Estímulo** | El estudiante dejó doble marca, marca tenue o marca borrada parcialmente en una pregunta. |
| **Artefacto** | Módulo `omr`. |
| **Entorno** | Operación normal. |
| **Respuesta** | El sistema no asigna una respuesta arbitraria: marca la pregunta como **requiere revisión manual** en el dashboard. |
| **Medida de respuesta** | El sistema clasifica correctamente como ambigua **≥99% de las marcas** cuyo contraste de llenado no supera el umbral de confianza definido (valor inicial: 70%, sujeto a calibración), evitando calificaciones erróneas silenciosas. |
| **Relacionado** | QG-3 · RF-03 |

### EC-03 · Tiempo de respuesta en calificación individual

| Atributo | Detalle |
|---|---|
| **Fuente** | Profesor |
| **Estímulo** | Solicita la calificación de una hoja ya escaneada. |
| **Artefacto** | Pipeline de calificación completo (`ingesta` → `omr` → `calificacion` → `dashboard`). |
| **Entorno** | Operación normal, carga típica del servidor, sin lote masivo en curso. |
| **Respuesta** | El sistema procesa la hoja y el resultado queda visible en el dashboard. |
| **Medida de respuesta** | **Tiempo end-to-end ≤5 segundos** por examen (percentil 95), medido desde la confirmación de carga hasta la disponibilidad del resultado. |
| **Relacionado** | QG-2 · RF-01, RF-04, RF-05 |

### EC-04 · Escalabilidad ante carga masiva

| Atributo | Detalle |
|---|---|
| **Fuente** | Profesor o TA de un curso masivo. |
| **Estímulo** | Sube en lote 200 hojas de respuestas escaneadas. |
| **Artefacto** | Cola de trabajos y pool de workers de procesamiento. |
| **Entorno** | Pico de carga (fin de periodo de examen). |
| **Respuesta** | El sistema confirma la recepción del lote de inmediato, lo encola y lo procesa completo sin caídas ni pérdida de datos, mostrando el avance en el dashboard. |
| **Medida de respuesta** | **100% de las hojas procesadas correctamente en ≤10 minutos** desde la confirmación de recepción, con uso de CPU y memoria del servidor por debajo del 85% durante todo el proceso. |
| **Relacionado** | QG-2 · RF-01 · ADR-0001 |

> **Nota de coherencia entre EC-03 y EC-04.** 200 hojas × 5 s = 16,6 min de trabajo
> secuencial, por encima del límite de 10 minutos. Los dos escenarios solo son satisfacibles
> simultáneamente si el procesamiento del lote es paralelo: con 4 workers concurrentes el
> lote baja a ~4,2 min. Por eso el procesamiento asíncrono no es una optimización futura sino
> parte de la decisión estructural registrada en ADR-0001. El número de workers es el
> parámetro que se ajusta si la medición real se desvía.

### EC-05 · Validez de la clave de respuestas (unicidad matemática)

| Atributo | Detalle |
|---|---|
| **Fuente** | Profesor, al generar o cargar un examen. |
| **Estímulo** | Se define un banco de preguntas con una opción correcta y varios distractores, generados por LLM o ingresados manualmente. |
| **Artefacto** | Módulo `autoria` (validador SymPy sobre la salida del LLM). |
| **Entorno** | **Fase de autoría**, antes de aplicar el examen. Fuera de la ruta crítica de calificación. |
| **Respuesta** | El sistema verifica simbólicamente que solo una opción es equivalente a la respuesta esperada, y alerta si dos opciones resultan equivalentes entre sí. |
| **Medida de respuesta** | **100% de los exámenes habilitados han pasado la validación de unicidad**; **tiempo de validación ≤5 segundos por pregunta**. |
| **Relacionado** | QG-1 · RF-06, RF-07 |

> **Nota.** El límite de 5 segundos de EC-05 es *por pregunta y en fase de autoría*; no entra
> en conflicto con los 5 segundos *por hoja completa* de EC-03, que corresponden a la fase de
> calificación. Son dos fases distintas del ciclo de vida del examen (ver sección 1.1).

### EC-06 · Aislamiento de datos por curso y por rol

| Atributo | Detalle |
|---|---|
| **Fuente** | Docente autenticado. |
| **Estímulo** | Intenta acceder a las calificaciones o al banco de preguntas de un curso que no tiene asignado, o intenta modificar una nota sin el permiso correspondiente. |
| **Artefacto** | Módulo `identidad` (autenticación y autorización). |
| **Entorno** | Operación normal. |
| **Respuesta** | El sistema deniega la operación, no revela la existencia ni el contenido del recurso, y registra el intento. |
| **Medida de respuesta** | **100% de los intentos de acceso cruzado son denegados** en la batería de pruebas de autorización, que cubre todas las rutas que exponen datos de curso. |
| **Relacionado** | QG-4 · RF-09 · RNF-05 |

### EC-07 · Confirmación fiable de recepción del lote

| Atributo | Detalle |
|---|---|
| **Fuente** | Docente autenticado (profesor o TA). |
| **Estímulo** | Sube un lote de hasta 200 hojas de respuesta escaneadas. |
| **Artefacto** | Módulo `ingesta` (recepción, validación de formato y encolado). |
| **Entorno** | Operación normal, curso masivo al cierre de un periodo de evaluación. |
| **Respuesta** | El sistema valida el formato de cada archivo, almacena los válidos, encola su procesamiento, rechaza los inválidos indicando el motivo y confirma al docente qué se recibió y qué no. |
| **Medida de respuesta** | **Confirmación de recepción del lote en ≤10 segundos**, con **0% de pérdida silenciosa**: todo archivo cargado queda registrado como *aceptado* o *rechazado con motivo*. |
| **Relacionado** | QG-2, QG-3 · RF-01 · Aspecto A-01 |

> **Nota.** EC-07 mide la *recepción*, no la calificación. La separación es consecuencia
> directa de ADR-0001: al procesar de forma asíncrona, la carga promete que nada se pierde,
> mientras que la promesa de calificar en tiempo la sostienen EC-03 y EC-04. Es el escenario
> que verifica el aspecto A-01 (`docs/aspectos.md`).

---

# 11. Risks and Technical Debts

| ID | Riesgo / deuda | Impacto | Qué lo dispara | Mitigación prevista |
|---|---|---|---|---|
| **R-01** | **No existe todavía el dataset de 300 hojas escaneadas** que EC-01 usa como medida. Sin él, el objetivo de calidad más importante del sistema no es verificable. | Alto | Llegar a la semana de medición sin hojas etiquetadas. | Producir el dataset temprano: imprimir plantillas, llenarlas con marcas variadas (incluyendo casos borde deliberados) y etiquetarlas manualmente. Es trabajo de laboratorio, no de programación, y se puede empezar ya. |
| **R-02** | **Decisión pendiente sobre el proveedor de LLM.** Sin resolverla, el C4 de Nivel 1 no puede cerrarse (cambia si hay o no sistema externo) y la vista de despliegue tampoco. | Medio | Que la decisión siga abierta al llegar a la semana 4. | Decidir antes del Nivel 2. La opción de referencia es una API alojada con nivel gratuito (ver nota más abajo), porque un modelo local añade requisitos de hardware que el proyecto no puede asumir. |
| **R-03** | **Dependencia de un servicio externo no controlado** si el LLM es una API alojada: límites de cuota, latencia variable, cambios de modelo y posible indisponibilidad. | Medio | Superar la cuota gratuita durante una sesión de generación intensiva. | La separación de fases ya mitiga lo esencial: el LLM solo participa en la autoría, nunca en la calificación, así que una caída del proveedor no impide calificar. Añadir además reintentos y la posibilidad de ingresar preguntas manualmente. |
| **R-04** | **El umbral de confianza del 70% es un valor supuesto, no medido.** Un umbral mal calibrado dispara falsos positivos (todo va a revisión manual, el sistema deja de ahorrar tiempo) o falsos negativos (errores silenciosos, se rompe QG-3). | Alto | Fijar el umbral sin evidencia y descubrirlo en producción. | Calibrar sobre el dataset de R-01 y documentar la curva de precisión frente al umbral en un ADR. |
| **R-05** | **El equipo no tiene experiencia previa medible con OpenCV / OMR**, que es justamente la parte de mayor riesgo técnico del sistema. | Alto | Dejar el módulo `omr` para el final del cronograma. | Construir un prototipo desechable de detección de marcas antes de la semana 4, aunque sea sobre una sola hoja, para convertir la incertidumbre en información. |
| **R-06** | **Deuda: no hay decisión de persistencia ni de almacenamiento de imágenes.** El módulo `infraestructura` está nombrado pero vacío. | Medio | Necesitar guardar el primer lote real. | ADR previsto para la semana 4. |
| **R-07** | **Deuda: EC-04 supone paralelismo pero no está fijado el número de workers** ni medido el consumo de CPU por hoja. | Medio | Que el límite de 85% de CPU se incumpla con la concurrencia elegida. | Medir el costo de una hoja en el prototipo de R-05 y derivar el número de workers de ese dato. |
| **R-08** | **Riesgo de erosión de los límites entre módulos** ("big ball of mud"), heredado de ADR-0001. | Medio | Importaciones directas entre módulos sin pasar por sus interfaces. | Revisión de código y análisis automático de dependencias en CI. |

### Nota de apoyo a R-02: opciones de LLM con nivel gratuito

El sistema usa el LLM únicamente para **generar enunciados y distractores en la fase de
autoría**, no en la ruta crítica de calificación. Esto significa que el volumen de llamadas es
bajo (decenas de preguntas por examen, no miles por minuto) y que la latencia no es crítica,
así que un nivel gratuito con límites de cuota es funcionalmente suficiente para el proyecto.

Alternativas con nivel gratuito y sin tarjeta de crédito, a revisar al tomar la decisión:

- **Google AI Studio (API de Gemini)** — nivel gratuito con clave de API inmediata; los
  límites concretos por modelo se consultan en la propia consola de AI Studio, ya que Google
  no publica una tabla fija y varían por cuenta y modelo.
- **Groq** — nivel gratuito con modelos abiertos alojados; límites del orden de decenas de
  peticiones por minuto y cientos a algunos miles por día según el modelo.
- **GitHub Models** — acceso gratuito a varios modelos con la cuenta de GitHub del equipo,
  cómodo por integrarse con el repositorio del curso.

En los tres casos el consumo se aísla detrás de una interfaz propia del módulo `autoria`, de
modo que cambiar de proveedor sea una sustitución local y no un cambio arquitectónico. Esa es
la mitigación real de R-03.

---

# 12. Glossary

| Término | Definición |
|---|---|
| **ADR** | *Architecture Decision Record.* Registro de una decisión arquitectónica: su contexto, alternativas evaluadas, lo decidido y sus consecuencias. |
| **Aspecto** | Corte vertical del sistema con valor propio, recorrible completo desde la necesidad hasta la evidencia. No es una capa ni un módulo. Ver `docs/aspectos.md`. |
| **Clave de respuestas** | Conjunto de opciones correctas de un examen, contra el cual se comparan las marcas detectadas. |
| **Distractor** | Opción incorrecta de una pregunta de opción múltiple, diseñada para ser plausible. Un distractor equivalente a la respuesta correcta invalida la pregunta. |
| **Escenario de calidad (EC)** | Especificación medible de un atributo de calidad en seis partes: fuente, estímulo, artefacto, entorno, respuesta y medida de respuesta. |
| **LLM** | *Large Language Model.* Modelo de lenguaje usado aquí para generar enunciados y distractores, cuya salida siempre se verifica con SymPy. |
| **OCR** | *Optical Character Recognition.* Reconocimiento de caracteres escritos. **No se usa en este sistema**; se aclara porque versiones anteriores de la documentación lo mencionaban por error. |
| **OMR** | *Optical Mark Recognition.* Reconocimiento de marcas en posiciones conocidas de una hoja estructurada. Es lo que este sistema usa: detecta *si una casilla está rellenada*, no *qué está escrito*. |
| **Percentil 95 (p95)** | Valor por debajo del cual queda el 95% de las mediciones. Se usa en EC-03 para que un caso lento aislado no invalide el escenario. |
| **SymPy** | Librería de Python para matemática simbólica. Aquí verifica equivalencia algebraica entre expresiones. |
| **TA** | *Teaching Assistant.* Asistente de cátedra; usuario operativo del sistema. |
| **Umbral de confianza** | Valor mínimo de certeza de la detección OMR por debajo del cual una respuesta se envía a revisión manual en lugar de calificarse. |
| **Worker** | Proceso que consume trabajos de la cola y los ejecuta en segundo plano, independiente del proceso que atiende las peticiones web. |
