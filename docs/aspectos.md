# Aspectos del sistema

Este documento registra los aspectos identificados para el proyecto **Sistema de calificación automática de exámenes de cálculo diferencial mediante OCR y modelos de lenguaje**, siguiendo la metodología de Aspect Driven Development (ADD) del curso.

Un aspecto es un corte vertical del sistema, con valor propio, que se puede recorrer completo:

aspecto → requisito → elementos C4 → ADR → código → pruebas → evidencia de calidad

Cada aspecto se trabaja en siete pasos: declarar, especificar, ubicar, decidir, construir, verificar y evidenciar.

## Aspecto A-01: Carga de examen para calificación

### Declarar

- **Nombre:** Carga de examen para calificación.
- **Para quién es:** el profesor universitario o el asistente de cátedra (TA) que dicta el curso; de forma indirecta, también el estudiante cuyo examen se carga.
- **Qué problema resuelve:** hace que un examen escaneado o fotografiado quede disponible en el sistema para su procesamiento posterior. Sin este paso no hay información sobre la cual aplicar OCR ni evaluación mediante modelos de lenguaje, así que el resto del flujo depende de que este aspecto exista primero.

### Especificar

**Requisito (RF-01, Requisito Funcional 1):** el sistema debe permitir a un profesor cargar un examen escaneado o fotografiado de un estudiante (imagen o PDF) para que quede disponible para su procesamiento posterior.

**Escenario de calidad** (borrador):

| Parte | Contenido |
|---|---|
| Fuente del estímulo | Un profesor autenticado en el sistema |
| Estímulo | Sube el examen escaneado o fotografiado (imagen o PDF) de un estudiante |
| Artefacto | El módulo de carga de exámenes |
| Ambiente | Operación normal, profesor conectado a internet, en el contexto de un curso con alto número de estudiantes |
| Respuesta | El sistema valida el formato del archivo, lo almacena y confirma la recepción al profesor |
| Medida de respuesta | *Por definir* — tiempo máximo aceptable de confirmación y porcentaje de archivos válidos almacenados sin pérdida de datos |

### Ubicar

Pendiente. Todavía no se han definido los elementos de C4 (contenedores o componentes) que van a realizar este aspecto.

### Decidir

Pendiente. Por ahora no existe ninguna decisión estructural (por ejemplo, dónde y cómo se almacenan los exámenes cargados) que amerite un ADR. Se documentará cuando el equipo la tome.

### Construir / Verificar / Evidenciar

Pendiente. No existen código, pruebas ni evidencia de calidad para este aspecto en esta entrega.

### Por qué se eligió este aspecto primero

- Es el punto de entrada del flujo completo del sistema: sin un examen cargado no hay nada sobre lo cual aplicar OCR ni evaluación.
- Es funcional, no tecnológico. Se puede declarar y especificar sin depender todavía de qué motor de OCR, qué modelo de lenguaje o qué estrategia de comparación en SymPy se elija.
- Permite un primer incremento verificable (un examen queda recibido y registrado) que no depende de que las partes más complejas del sistema estén resueltas.

### Tabla de trazabilidad

| ID | Aspecto | Requisito | C4 | ADR | Código | Pruebas | Evidencia |
|----|---------|-----------|----|----|--------|---------|-----------|
| A-01 | Carga de examen para calificación | RF-01 | Pendiente | Pendiente | Pendiente | Pendiente | Pendiente |

## Tensiones de calidad identificadas (contexto para aspectos futuros)

El Informe Inicial del grupo identifica dos tensiones de calidad que todavía no aplican al aspecto A-01, pero que van a condicionar los aspectos que vienen después:

1. **Precisión de la extracción OCR vs. tolerancia a la variabilidad caligráfica.** La notación matemática manuscrita es ambigua (por ejemplo, la confusión entre la variable *x* y el operador ·, o entre exponentes y constantes). Un pipeline demasiado estricto rechaza o traduce mal expresiones válidas; uno demasiado permisivo "adivina" la intención del estudiante y genera un árbol de expresión en SymPy distinto al escrito, alterando la evaluación. Esta tensión le corresponde al futuro aspecto de extracción del contenido del examen.
2. **Determinismo sintáctico vs. equivalencia matemática en SymPy.** Una respuesta correcta puede escribirse de varias formas algebraicas no idénticas (por ejemplo, 1 − cos²(x) frente a sin²(x)). Comparar cadenas de texto genera falsos negativos; verificar la equivalencia real exige simplificación simbólica o evaluación numérica, con mayor costo de cómputo y casos límite que manejar. Esta tensión le corresponde al futuro aspecto de evaluación de una respuesta.

Estas tensiones no generan ADR ni decisiones todavía; se dejan anotadas aquí para que, cuando se declaren esos aspectos, el escenario de calidad correspondiente parta de ellas en vez de definirse desde cero.
