# Ficha del problema

**Proyecto:** Sistema de Calificación OMR — calificación automática de exámenes de opción
múltiple de cálculo diferencial
**Equipo:** Josué Ortega De Arco, María Restrepo Licona, Sebastián Cañas Plata, Susana Rosales Castellar
**Última actualización:** 2026-08-24

> **Nota sobre el alcance.** La primera versión de esta ficha, escrita en la semana 1, planteaba
> un sistema de OCR sobre exámenes manuscritos con evaluación de procedimientos. Ese enfoque se
> descartó en la semana 2 al confirmarse que el enunciado del problema fija hoja de respuestas
> estructurada y preguntas de opción múltiple. La transición está registrada en
> [`ia.md`](ia.md), Entrada 2, y las restricciones que la fijan son RNF-02 y RNF-03 del
> [arc42](arc42/arc42-template-ES.md). Esta ficha describe el sistema que efectivamente se está
> construyendo.

---

## Contexto

En los cursos de cálculo diferencial de pregrado, la evaluación se realiza con frecuencia
mediante exámenes de opción múltiple sobre hojas de respuesta de formato fijo, que el
estudiante rellena marcando casillas. Este formato se elige porque permite evaluar cursos
numerosos —del orden de doscientos estudiantes por corte— en un plazo razonable.

La calificación recae sobre el docente del curso y sobre los asistentes de cátedra, que deben
procesar las hojas y consolidar los resultados. Antes de eso, alguien tuvo que construir el
examen: redactar cada pregunta con una respuesta correcta y tres o cuatro distractores
plausibles.

## Descripción del problema

Hay dos problemas distintos, y el segundo es el que suele pasar inadvertido.

**El primero es de volumen.** Procesar doscientas hojas a mano consume horas de tiempo docente
en una tarea mecánica, y ese costo se repite en cada corte. Además retrasa la
retroalimentación: el estudiante recibe su nota cuando el evaluador tuvo tiempo, no cuando el
examen terminó.

**El segundo es de validez de la clave de respuestas.** En matemáticas, una misma expresión
admite muchas formas equivalentes. Al redactar distractores para una pregunta de derivadas o de
límites, es fácil escribir uno que resulte **algebraicamente equivalente a la respuesta
correcta** sin advertirlo: por ejemplo, ofrecer `1 − cos²(x)` y `sin²(x)` como opciones
distintas. Cuando eso ocurre, la pregunta tiene dos respuestas correctas y el sistema de
calificación —manual o automático— penaliza a estudiantes que respondieron bien.

Este segundo problema no se resuelve leyendo las marcas más rápido. Requiere verificar la
equivalencia matemática entre las opciones **antes** de aplicar el examen, que es un trabajo
que ningún lector de marcas comercial hace.

## Usuarios del sistema

| Usuario | Rol | Qué hace con el sistema |
|---|---|---|
| **Profesor de cálculo diferencial** | Usuario principal | Construye el banco de preguntas, habilita el examen una vez validado, carga las hojas escaneadas, resuelve las marcas ambiguas y consulta los resultados. |
| **Asistente de cátedra (TA)** | Usuario operativo | Carga los escaneos en lote y resuelve las marcas que el sistema marcó como dudosas. |

El estudiante **no es usuario del sistema**: no tiene cuenta ni interfaz, y su única
interacción es rellenar la hoja de respuestas en papel. Sí es un afectado directo, porque las
consecuencias de un error de lectura o de una clave inválida recaen sobre su calificación.

## Otros afectados

- **Comité académico y dirección de programa.** Responden por la confiabilidad de las
  calificaciones y por la confidencialidad de los datos académicos.
- **Administradores de TI.** Operan el sistema y responden por su disponibilidad durante los
  periodos de evaluación.

## Consecuencias de no resolverlo

Mientras el proceso dependa por completo del trabajo manual se mantienen tres limitaciones: el
tiempo de entrega de resultados queda sujeto a la disponibilidad del evaluador; los errores en
la clave de respuestas se descubren tarde, cuando ya afectaron calificaciones reales; y el
tamaño de curso que puede atenderse queda limitado por la capacidad de procesamiento manual.

## Objetivo del proyecto

Construir un sistema que automatice la calificación de exámenes de opción múltiple de cálculo
diferencial en dos frentes:

1. **Leer las hojas de respuesta escaneadas** mediante reconocimiento óptico de marcas (OMR),
   calculando un nivel de confianza por cada detección y enviando a revisión manual todo lo que
   no supere el umbral, en lugar de asignar una respuesta arbitraria.
2. **Validar la clave de respuestas antes de aplicar el examen**, verificando con computación
   simbólica (SymPy) que exactamente una opción es equivalente a la respuesta esperada y que
   ningún par de distractores es equivalente entre sí. La generación de enunciados y
   distractores se apoya en un modelo de lenguaje, cuya salida siempre pasa por esa validación.

Los resultados se presentan en un dashboard con notas por curso, estadísticas por examen y por
pregunta, y alertas de los casos que requieren revisión.

El sistema es una **herramienta de apoyo al criterio del docente**, no un reemplazo de su
decisión final: toda marca dudosa se le devuelve para que decida.

## Alcance

**Dentro del alcance**

- Exámenes de opción múltiple sobre hoja de respuestas de formato fijo, con casillas en
  posiciones conocidas.
- Dominio de cálculo diferencial: límites, derivadas y simplificaciones algebraicas.
- Usuarios docentes autenticados, con acceso limitado a los cursos que tienen asignados.
- Ingesta de escaneos en formato JPG, PNG o PDF, individualmente o en lote.

**Fuera del alcance**

- Preguntas de desarrollo o demostración, y cualquier evaluación de procedimientos escritos a
  mano.
- Otras áreas del cálculo: integral, multivariable, ecuaciones diferenciales.
- Interfaz o cuenta para estudiantes.
- Integración con el sistema académico institucional para publicar notas.
- Impresión y distribución física de los exámenes.

## Tensiones de calidad

El proyecto tiene dos tensiones que condicionan su diseño y que se desarrollan en
[`aspectos.md`](aspectos.md):

- **T-1 · Sensibilidad de la detección frente a carga de revisión manual.** Un umbral de
  confianza permisivo produce errores silenciosos; uno estricto manda tantas preguntas a
  revisión que el sistema deja de ahorrar tiempo.
- **T-2 · Determinismo sintáctico frente a equivalencia matemática.** Comparar expresiones como
  texto genera falsos negativos; verificar equivalencia real cuesta cómputo y tiene casos
  límite.

## Estado y documentación relacionada

La arquitectura está documentada y en construcción. Esta ficha describe el problema; el diseño
y su justificación viven en:

- [`arc42/arc42-template-ES.md`](arc42/arc42-template-ES.md) — requisitos, restricciones,
  objetivos de calidad y escenarios medibles.
- [`adr/`](adr/) — las decisiones de arquitectura con sus alternativas y consecuencias.
- [`c4/doc-c4.md`](c4/doc-c4.md) — los diagramas del sistema.
- [`aspectos.md`](aspectos.md) — la trazabilidad de cada aspecto, desde el requisito hasta la
  evidencia.
