---
date: August 2026
title: "![arc42](images/arc42-logo.png) Arquitectura del Sistema de Calificación Automática de Exámenes"
---

# **About arc42**

arc42, the template for documentation of software and system
architecture.

Template Version 9.0-EN. (based upon AsciiDoc version), July 2025

Created, maintained and © by Dr. Peter Hruschka, Dr. Gernot Starke and
contributors. See [https://arc42.org](https://arc42.org).

# Introduction and Goals
## Requirements Overview
El sistema tiene como objetivo automatizar el proceso de evaluación y calificación de exámenes de opción múltiple para la asignatura de **Cálculo Diferencial** en facultades de ingeniería, ciencias exactas y economía. La solución integra **Reconocimiento Óptico de Marcas (OMR)**, **Modelos de Lenguaje (LLM)** y **Computación Simbólica (SymPy)** para ofrecer un flujo extremo a extremo seguro, preciso e interactivo.

### Funcionalidades Principales:
1. **Generación y Validación Matemática de Exámenes:**
   - Creación de bancos de preguntas enfocadas en el dominio de cálculo diferencial (límites, derivadas y simplificaciones algebraicas).
   - Verificación simbólica mediante **SymPy** para asegurar la unicidad matemática de la respuesta correcta (comprobando equivalencias) y descartar distractores ambiguos o equivalentes entre sí.

2. **Procesamiento OMR e Ingesta de Exámenes Escaneados:**
   - Lectura digitalizada de hojas de respuestas físicas con formato estandarizado.
   - Algoritmo de detección de llenado con umbrales de confianza para identificar y gestionar marcas ambiguas, tenues o borrados parciales.

3. **Calificación Automática y Dashboard Interactivo:**
   - Comparación instantánea de respuestas OMR contra la clave de respuestas validada.
   - Presentación de resultados consolidados en un **Dashboard** interactivo para la visualización de notas por curso, estadísticas por examen y alertas de revisión manual.

---

## Quality Goals
Los objetivos de calidad primarios que guían la arquitectura del sistema se alinean con las necesidades operativas del equipo docente:

1. **Precisión y Validez Matemática (Exactitud OMR + SymPy):** Garantizar una lectura OMR altamente confiable (≥98% de exactitud) y una validación de clave al 100% libre de ambigüedades algebraicas antes de la aplicación.
2. **Rendimiento y Eficiencia de Procesamiento:** Procesar exámenes individuales en ≤ 5 segundos y lotes masivos (200 hojas) en ≤ 10 minutos para soportar periodos de evaluación crítica sin degradación.
3. **Manejabilidad de Casos Borde (Degradación Controlada):** Detectar y marcar automáticamente en el dashboard las respuestas con confianza de llenado <70% para revisión manual docente, evitando calificaciones erróneas silenciosas.
4. **Seguridad y Aislamiento por Rol:** Restringir el acceso exclusivamente a usuarios registrados (Profesores y TAs), garantizando que cada docente acceda únicamente a los datos y calificaciones de sus cursos autorizados.

---

## Stakeholders

| Stakeholder | Contact | Expectations |
|---|---|---|
| **Profesores de Cálculo / Cátedra** | docentes.calculo@utb.edu | Reducir drásticamente el tiempo de calificación de exámenes masivos de Cálculo Diferencial. Garantizar que las claves de respuesta no contengan ambigüedades matemáticas. Disponer de un dashboard intuitivo con métricas de rendimiento por curso y por pregunta. |
| **Asistentes de Cátedra (TAs)** | tas.ingenieria@utb.edu | Herramienta ágil para la ingesta en lote de imágenes escaneadas. Interfaz clara para resolver manualmente preguntas clasificadas como ambiguas por el OMR. |
| **Comité Académico / Dirección de Programa** | direccion.sistemas@utb.edu | Alta precisión y confiabilidad en las calificaciones automatizadas. Seguridad, confidencialidad y auditabilidad en el almacenamiento de notas y datos académicos. |
| **Administradores de TI / Sistema** | admin.sys@utb.edu | Sistema modular, mantenible y desacoplado con bajo consumo de CPU/memoria en servidor. Alta disponibilidad (≥95%) durante periodos críticos de exámenes parciales y finales. |

# Architecture Constraints
Las siguientes restricciones fijan los límites del diseño arquitectónico. Cada una está justificada técnicamente según el contexto del proyecto:

1. **Restricción Tecnológica (Stack Obligatorio: OMR + LLM + SymPy):**
   - *Justificación:* El planteamiento del problema fija la solución técnica desde el enunciado: la calificación debe realizarse mediante OMR (detección de marcas), LLM y SymPy (generación y validación simbólica del banco de preguntas). No es una decisión libre del equipo, cualquier arquitectura alternativa queda fuera del alcance definido. Es la restricción más determinante porque condiciona todos los componentes del sistema.

2. **Restricción de Entrada (Hoja de respuestas estructurada de opción múltiple):**
   - *Justificación:* El examen debe resolverse en una hoja física con formato estandarizado (casillas en posiciones fijas), no en papel de escritura libre. Esto obliga a que el layout de la hoja sea fijo y conocido de antemano para que el OMR pueda leer las marcas correctamente, y descarta cualquier formato de examen irregular.

3. **Restricción de Diseño de Examen (Solo preguntas evaluables como opción múltiple):**
   - *Justificación:* Al procesar marcas y no expresiones abiertas, el sistema solo puede evaluar preguntas con una única respuesta final identificable entre varias opciones. Preguntas que requieran desarrollo o demostración quedan fuera de alcance. Esta restricción define directamente cómo se construye el banco de preguntas de cálculo diferencial.

4. **Restricción de Dominio (Cálculo Diferencial):**
   - *Justificación:* El alcance temático se limita a derivadas, límites y simplificaciones algebraicas. Esto acota el motor de validación simbólica (SymPy) y evita sobredimensionar el sistema para casos fuera de alcance (integrales, ecuaciones diferenciales, álgebra lineal, etc.).

5. **Restricción de Usuarios Objetivo (Profesores y TAs, no estudiantes):**
   - *Justificación:* El informe define explícitamente en la sección "Usuarios a los que sirve" que el sistema está dirigido a profesores universitarios y asistentes de cátedra (TAs) de facultades de ingeniería, ciencias exactas y economía. El estudiante es únicamente la fuente de las marcas en la hoja de respuestas, pero no es usuario del sistema ni interactúa con él directamente. Esta restricción es importante porque condiciona el diseño de roles, autenticación y permisos: no se necesita una interfaz ni cuenta para el estudiante, y todo el flujo de interacción (carga de exámenes, revisión de casos ambiguos, consulta del dashboard) se diseña exclusivamente para el rol docente.

6. **Restricción de Salida (Presentación en Dashboard):**
   - *Justificación:* El planteamiento del problema especifica explícitamente que los resultados deben presentarse "en un dashboard", no como archivo aislado, reporte por correo o salida de solo consola. Esto fija que la arquitectura debe incluir necesariamente una capa de visualización de datos con la que el profesor interactúe directamente, lo cual condiciona decisiones de diseño como la necesidad de una interfaz web, actualización de resultados en tiempo (casi) real, y estructura de datos pensada para agregación y despliegue visual (por curso, por examen, por pregunta), no solo para almacenamiento.


# Context and Scope
## Business Context
El sistema interactúa con los usuarios docentes (Profesores y TAs) y procesa los insumos físicos (hojas de respuestas escaneadas) para generar las calificaciones y métricas analíticas.

Diagrama de Contexto de Negocio:

- Profesor / TA (Usuario) --(Carga de Exámenes Escaneados / Creación de Preguntas)--> Sistema de Calificación (CalcCheck / SymGrading)
- Profesor / TA (Usuario) <-- (Consultar Dashboard / Reportes / Revisión de Casos Ambiguos) -- Sistema de Calificación
- Examen Físico (Hoja de Respuestas) -- (Digitalización PNG/JPG/PDF) --> Sistema de Calificación

### Descripción de Interfaces del Dominio Extranjero:

* **Profesor / TA:**
  * *Entradas:* Carga de claves de respuesta, parámetros de evaluación, archivos escaneados de exámenes (imágenes/PDF) y confirmación de revisión manual para casos ambiguos.
  * *Salidas:* Vistas del dashboard interactivo, reportes consolidados por curso, analítica de ítems por pregunta y notificaciones de casos dudosos.
* **Hoja de Respuestas (Formato Físico Escaneado):**
  * *Entrada:* Archivos digitalizados en formato JPG, PNG o PDF con diseño de plantilla estructurada.

---

## Technical Context
### Diagrama C4 - Nivel 1: Contexto del Sistema

Diagrama C4 (Texto Estructurado):
1. Usuario: Profesor / TA (Docente autorizado que crea exámenes, sube escaneos y revisa el dashboard de resultados).
2. Sistema: Sistema de Calificación (Procesador OMR, Validador SymPy/LLM y Dashboard).

Flujos Principales:
- Profesor / TA -> Sistema: Sube exámenes escaneados, gestiona cursos y revisa calificaciones (vía HTTPS / Web UI).
- Sistema -> Profesor / TA: Muestra dashboard de resultados, alertas y marcas ambiguas (vía HTTPS / Web UI).

### Explicación de Interfaces Técnicas e Insumos/Salidas por Canal

| Canal / Interfaz | Entrada | Salida | Protocolo / Formato |
|---|---|---|---|
| **Interfaz Web Dashboard** | Autenticación, gestión de cursos, resolución de marcas ambiguas | Despliegue de notas, gráficos y alertas de ambigüedad | HTTPS / JSON, HTML5, CSS |
| **Canal Ingesta OMR** | Lote de imágenes/PDF de hojas escaneadas | Matriz de respuestas detectadas con nivel de confianza (%) | Filesystem / OpenCV, PNG, JPG, PDF (300 DPI) |
| **Motor SymPy / LLM** | Expresiones matemáticas de la clave de respuestas | Validación de unicidad y equivalencia entre opciones | In-Process Python API |

# Solution Strategy
# Building Block View
## Whitebox Overall System
[Diagrama general pendiente]

Motivation

:   [Explicación pendiente]

Contained Building Blocks

:   [Descripción de los bloques contenidos pendiente]

Important Interfaces

:   [Descripción de las interfaces importantes pendiente]

### [Nombre del bloque 1]
[Propósito / responsabilidad pendiente]

[Interfaces pendientes]

[Características de calidad/rendimiento opcionales]

[Ubicación opcional de directorio/archivo]

[Requisitos cumplidos opcionales]

[Problemas, riesgos o asuntos abiertos opcionales]

### [Nombre del bloque 2]
[black box template]

### [Nombre del bloque n]
[black box template]

### [Nombre de la interfaz 1]
...

### [Nombre de la interfaz m]
## Level 2
### White Box [building block 1]
[Plantilla de caja blanca pendiente]

### White Box [building block 2]
[Plantilla de caja blanca pendiente]

...

### White Box [building block m]
## Level 3
### White Box [Bloque x.1]
[Plantilla de caja blanca pendiente]

### White Box [Bloque x.2]
[Plantilla de caja blanca pendiente]

### White Box [Bloque y.1]
[Plantilla de caja blanca pendiente]

# Runtime View
## [Escenario de ejecución 1]
-   [Diagrama de ejecución o descripción textual pendiente]

-   [Descripción de los aspectos relevantes de las interacciones pendiente]
    between the building block instances depicted in this diagram.>

## [Escenario de ejecución 2]
## ...

## [Runtime Scenario n]
# Deployment View
## Infrastructure Level 1
[Diagrama general pendiente]

Motivation

:   [Explicación pendiente]

Quality and/or Performance Features

:   [Explicación pendiente]

Mapping of Building Blocks to Infrastructure

:   [Descripción del mapeo pendiente]

## Infrastructure Level 2
### [Elemento de infraestructura 1]
[Diagrama y explicación pendientes]

### [Elemento de infraestructura 2]
[Diagrama y explicación pendientes]

...

### [Infrastructure Element n]
[Diagrama y explicación pendientes]

# Cross-cutting Concepts
## [Concept 1]
[explanation]

## [Concept 2]
[explanation]

...

## [Concept n]
[explanation]

# Architecture Decisions
# Quality Requirements
## Quality Requirements Overview
El árbol de utilidad organiza los atributos de calidad priorizados por Impacto de negocio y Riesgo técnico:

### Árbol de Utilidad

- Rendimiento:
  * Tiempo de respuesta en calificación individual: El procesamiento end-to-end de una hoja y su despliegue en el dashboard debe realizarse en ≤ 5 segundos por examen (percentil 95). (Impacto: Medio | Riesgo técnico: Medio)
  * Escalabilidad ante carga masiva: El sistema encola y procesa 100% de un lote de 200 hojas simultáneas en ≤ 10 minutos totales, con uso de CPU/memoria del servidor por debajo del 85%. (Impacto: Alto | Riesgo técnico: Alto)

- Escalabilidad:
  * Crecimiento de datos: El crecimiento del almacenamiento de imágenes no debe provocar una degradación significativa del tiempo de respuesta del sistema. (Impacto: Medio | Riesgo técnico: Alto)
  * Usuarios concurrentes: El sistema debe soportar al menos 10 usuarios concurrentes sin producir errores ni una degradación significativa del tiempo de respuesta. (Impacto: Medio | Riesgo técnico: Bajo)

- Disponibilidad:
  * Recuperación ante fallos: En caso de una falla durante el procesamiento, los exámenes previamente cargados deben conservarse y reanudar su procesamiento sin volver a cargarlos. (Impacto: Alto | Riesgo técnico: Alto)
  * Disponibilidad del servicio: El sistema debe estar disponible durante los periodos de evaluación, con una disponibilidad mínima del 95%. (Impacto: Alto | Riesgo técnico: Medio)

- Mantenibilidad:
  * Modificación: Un cambio o corrección en un módulo del sistema no debe requerir modificaciones en los demás módulos. (Impacto: Medio | Riesgo técnico: Alto)
  * Corrección de errores: Una corrección de errores debe poder implementarse sin interrumpir el funcionamiento del resto del sistema. (Impacto: Medio | Riesgo técnico: Alto)

- Seguridad:
  * Protección de datos: 
      * Solo los usuarios con permisos correspondientes pueden modificar las calificaciones. (Impacto: Alto | Riesgo técnico: Alto)
      * Un profesor solo debe poder acceder a los datos de los cursos que tenga autorizado. (Impacto: Alto | Riesgo técnico: Medio)
  * Autenticación: Solo podrán acceder los usuarios registrados. (Impacto: Alto | Riesgo técnico: Medio)
  * Autorización: Un usuario autenticado solo podrá acceder a las funciones y datos correspondientes a su rol. (Impacto: Alto | Riesgo técnico: Medio)

- Precisión:
  * Reconocimiento OMR: El sistema identifica correctamente la opción con ≥98% de exactitud sobre un dataset de prueba de 300 hojas escaneadas. (Impacto: Alto | Riesgo técnico: Alto)
  * Manejo de marcas ambiguas (Degradación controlada): El sistema identifica como ambigua ≥99% de las marcas que no superan un umbral de confianza (<70%) y las envía a revisión manual, evitando calificaciones erróneas. (Impacto: Alto | Riesgo técnico: Alto)
  * Validez de la clave de respuestas: El motor LLM + SymPy verifica simbólicamente que solo una opción es equivalente a la esperada en el 100% de exámenes generados (≤ 5 segundos por pregunta) antes de habilitarlos. (Impacto: Alto | Riesgo técnico: Alto)

---

## Quality Scenarios
A continuación se formalizan los 5 escenarios de calidad requeridos con sus correspondientes métricas cuantitativas:

### Escenario 1: Exactitud de detección de marcas OMR

| Atributo | Detalle |
|---|---|
| **Fuente** | Profesor |
| **Estímulo** | Sube una hoja de respuestas escaneada con casillas marcadas por el estudiante. |
| **Artefacto** | Módulo de OMR (detección de marcas). |
| **Entorno** | Operación normal, carga individual. |
| **Respuesta** | El sistema identifica correctamente la opción marcada en cada pregunta. |
| **Medida de Respuesta** | **≥98% de exactitud** en la detección de la marca correcta, sobre un dataset de prueba de 300 hojas escaneadas. |
---

### Escenario 2: Manejo de marcas ambiguas (degradación controlada)

| Atributo | Detalle |
|---|---|
| **Fuente** | Sistema OMR (ambigüedad en la hoja). |
| **Estímulo** | El estudiante dejó doble marca, marca tenue o marca borrada parcialmente en una pregunta. |
| **Artefacto** | Módulo de OMR. |
| **Entorno** | Operación normal. |
| **Respuesta** | El sistema no asigna una respuesta arbitraria; marca la pregunta como **requiere revisión manual** en el dashboard. |
| **Medida de Respuesta** | El sistema identifica correctamente como ambigua **≥99% de las marcas** que no superan un umbral de confianza definido (ej. contraste de llenado <70%), evitando calificaciones erróneas silenciosas. |
---

### Escenario 3: Tiempo de respuesta en calificación individual

| Atributo | Detalle |
|---|---|
| **Fuente** | Profesor |
| **Estímulo** | Solicita la calificación de una hoja ya escaneada. |
| **Artefacto** | Pipeline completo (OMR → comparación con clave → dashboard). |
| **Entorno** | Operación normal, carga típica del servidor. |
| **Respuesta** | El sistema procesa la hoja y despliega el resultado en el dashboard. |
| **Medida de Respuesta** | **Tiempo de procesamiento end-to-end ≤ 5 segundos** por examen (percentil 95). |
---

### Escenario 4: Escalabilidad ante carga masiva

| Atributo | Detalle |
|---|---|
| **Fuente** | Profesor o TA de un curso masivo |
| **Estímulo** | Sube en lote 200 hojas de respuestas escaneadas simultáneamente. |
| **Artefacto** | Servidor de procesamiento / cola de trabajos. |
| **Entorno** | Pico de carga (fin de periodo de examen). |
| **Respuesta** | El sistema encola y procesa todas las hojas sin caídas ni pérdida de datos. |
| **Medida de Respuesta** | **100% de las hojas procesadas correctamente en ≤ 10 minutos** totales, con uso de CPU/memoria del servidor por debajo del 85% durante todo el proceso. |
---

### Escenario 5: Validez de la clave de respuestas (unicidad matemática)

| Atributo | Detalle |
|---|---|
| **Fuente** | Profesor (al generar o cargar el examen). |
| **Estímulo** | Se define un banco de preguntas con una opción correcta y varios distractores generados o ingresados. |
| **Artefacto** | Motor LLM + SymPy de validación de clave. |
| **Entorno** | Fase de creación del examen, antes de aplicarlo. |
| **Respuesta** | El sistema verifica simbólicamente que solo una opción es matemáticamente equivalente a la respuesta correcta esperada, y alerta si dos opciones son equivalentes entre sí. |
| **Medida de Respuesta** | **100% de los exámenes generados pasan la validación de unicidad** antes de habilitarse para aplicación; **tiempo de validación ≤ 5 segundos** por pregunta. |
# Risks and Technical Debts
# Glossary

| Término | Definición |
|---|---|
| **OMR** | Optical Mark Recognition (Reconocimiento de marcas en papel). |
| **SymPy** | Librería de Python para cálculo y matemáticas simbólicas. |
