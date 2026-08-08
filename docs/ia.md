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
