# Registro de uso de Inteligencia Artificial

Este documento registra el uso de herramientas de IA durante el desarrollo del proyecto **Sistema de calificación automática de exámenes de cálculo diferencial mediante OCR y modelos de lenguaje**, conforme a la guía del curso.

**La IA propone; el equipo decide y verifica.** Ninguna salida generada por una herramienta de IA entra al proyecto sin revisión, validación y, si hace falta, corrección por parte del equipo.

Este registro documenta IA como herramienta de construcción (apoyo para redactar, diseñar y documentar). El modelo de lenguaje que el sistema use en producción para evaluar exámenes es IA como componente del sistema, y se documentará dentro del aspecto correspondiente, no aquí.

## Campos de cada entrada

Fecha, actividad realizada, herramienta utilizada, respuesta obtenida (resumen), qué se aceptó, qué se rechazó, justificación de la decisión.

## Registro

### Entrada 1

- **Fecha:** 2026-08-07
- **Actividad realizada:** Elaboración y ajuste iterativo de los documentos de la primera entrega (ficha del problema, docs/aspectos.md, docs/ia.md, README.md) hasta la versión que se lleva al primer commit del repositorio.
- **Herramienta utilizada:** Claude (Anthropic).
- **Prompt utilizado (resumen):** Se pidió, en sucesivas iteraciones, un borrador de la ficha del problema y del aspecto A-01 con su tabla de trazabilidad, luego ajustarlos a las etapas de ADD (declarar/especificar/ubicar/decidir/construir/verificar/evidenciar) y a un escenario de calidad, y finalmente alinearlos con el Informe Inicial oficial del grupo (problema, usuarios y tensiones de calidad ya definidos por el equipo).
- **Respuesta obtenida (resumen):** En cada paso la IA entregó una versión de los documentos ajustada a lo pedido, hasta llegar a la versión final: ficha del problema alineada con el Informe Inicial (incluyendo integrantes del grupo), aspecto A-01 "Carga de examen para calificación" con sus siete etapas, y las dos tensiones de calidad del informe incorporadas como contexto para los aspectos que vienen después.
- **Qué se aceptó:** la estructura de los documentos por etapas de ADD, el aspecto A-01 como primer corte vertical, y el uso de las dos tensiones de calidad del informe para anticipar el contexto de los aspectos de OCR y de evaluación con SymPy.
- **Qué se rechazó:** cualquier afirmación sobre resultados o ventajas del sistema sin evidencia que las respalde; valores numéricos concretos en el escenario de calidad de A-01, porque el equipo todavía no los ha discutido; y que el aspecto principal de esta entrega se definiera alrededor de una tecnología (OCR, LLM, SymPy) en vez de una función.
- **Justificación:** el mismo criterio se aplicó en los tres momentos: la IA propone la forma y organiza la información, pero el contenido que compromete al equipo (alcance, umbrales, decisiones técnicas) solo se acepta cuando corresponde a algo que el equipo ya definió (en este caso, el Informe Inicial firmado por los cuatro integrantes) y se deja explícitamente pendiente cuando no.

### Entrada 2

- **Fecha:** 2026-08-16
- **Actividad realizada:** Refactorización de los escenarios de calidad y el árbol de utilidad para la transición tecnológica de OCR a OMR, y generación de la arquitectura documentada en modelo C4 (Contexto y Contenedores) mediante código Mermaid.
- **Herramienta utilizada:** Gemini (Google), Claude (Anthropic).
- **Prompt utilizado (resumen):** Se solicitó adaptar los escenarios de calidad y mejorar modelo de árbol de utilidad escrito previamente, asumiendo el cambio del motor OCR a un motor OMR, estableciendo el documento de escenarios como la fuente de la verdad para unificar métricas. Luego, se solicitó la creación de modelos C4, exigiendo iterativamente adaptar el Nivel 1 (Contexto) a las reglas estrictas de la rúbrica del curso (diagramas como código versionable, etiquetas de propósito/tecnología en flechas, y leyenda explicativa autónoma), basandose también en la documentación oficial de C4 model. Finalmente, se solicitó asistencia para renderizar el código de Mermaid en un visor Markdown web.
- **Respuesta obtenida (resumen):** La IA reescribió los escenarios descartando la evaluación matemática en el reconocimiento de imagen (inviable en OMR) y enfocándolos en el manejo de marcas ambiguas (degradación controlada). Unificó las métricas del árbol de utilidad (tiempos, volúmenes de 200 hojas) basándose en el documento de escenarios. Entregó el código Mermaid para el Nivel 1 de C4 cumpliendo las exigencias de la rúbrica y diagnosticó errores de sintaxis en el visor web.
- **Qué se aceptó:** La redefinición arquitectónica para OMR (priorizar la identificación de ambigüedades por umbrales de confianza), la unificación del árbol de utilidad con el documento de escenarios, y el código Mermaid del diagrama de Contexto, ya que cumplía estrictamente con los criterios de evaluación de la asignatura para el nivel 1.
- **Qué se rechazó:** Cualquier uso de plantillas documentales gráficas o manuales (Word/PDF) para los diagramas, forzando la generación de "diagramas como código" compatibles con repositorios (en la ruta `/docs/c4/`). Además, se rechazó la inclusión de funcionalidades de equivalencia simbólica dentro del procesamiento de imagen, delegando SymPy y LLMs exclusivamente a la validación previa de la clave de respuestas.
- **Justificación:** Se validaron los cambios técnicos a OMR y la unificación del árbol de utilidad porque reflejan las restricciones tecnológicas reales y eliminan las inconsistencias previas del proyecto. El código Mermaid se aprobó porque asegura que la arquitectura pueda someterse a control de versiones en Pull Requests sin desincronizarse, cumpliendo la rúbrica obligatoria.
