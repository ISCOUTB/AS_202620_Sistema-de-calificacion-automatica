# Ficha del problema

**Proyecto:** Sistema de Calificación OMR — calificación automática de exámenes de opción
múltiple de cálculo diferencial
**Equipo:** Josué Ortega De Arco, María Restrepo Licona, Sebastián Cañas Plata, Susana Rosales Castellar
**Última actualización:** 2026-08-30

---

## Contexto

En los cursos de cálculo diferencial de pregrado, la evaluación se realiza con frecuencia
mediante exámenes de opción múltiple sobre hojas de respuesta de formato fijo, que el
estudiante rellena marcando casillas. Este formato se elige porque permite evaluar cursos
numerosos —del orden de doscientos estudiantes por corte— en un plazo razonable.

La calificación recae sobre el docente del curso y sobre los asistentes de cátedra, que deben
procesar las hojas y consolidar los resultados. Antes de eso, el profesor construyó el examen:
redactó cada pregunta con una respuesta correcta y tres o cuatro distractores plausibles, y
armó la **clave de respuestas**, que es la lista de cuál opción es la correcta en cada pregunta.

## Descripción del problema

Hay dos problemas, y el sistema los atiende de manera distinta. Vale la pena decirlo con
precisión, porque solo el primero se resuelve automatizando.

**El primero es de volumen, y sí se automatiza.** Procesar doscientas hojas a mano consume
horas de tiempo docente en una tarea mecánica, y ese costo se repite en cada corte. Además
retrasa la retroalimentación: el estudiante recibe su nota cuando el evaluador tuvo tiempo, no
cuando el examen terminó.

Pero leer marcas rápido no basta. Un lector de marcas que responde con una letra cuando la
casilla está a medio borrar convierte un error de lectura en una nota equivocada, y nadie se
entera. Por eso el sistema calcula un **nivel de confianza** por cada detección y devuelve a
revisión manual todo lo que no lo supere, en vez de inventar una respuesta.

**El segundo es de validez de la clave, y este no se resuelve solo.** En matemáticas una misma
expresión admite muchas formas equivalentes. Al redactar distractores para una pregunta de
derivadas o de límites es fácil escribir uno que resulte **algebraicamente equivalente a la
respuesta correcta** sin advertirlo: por ejemplo, ofrecer `1 − cos²(x)` y `sin²(x)` como
opciones distintas. Cuando eso ocurre, la pregunta tiene dos respuestas correctas y la
calificación —manual o automática— penaliza a estudiantes que respondieron bien.

Verificar esa equivalencia automáticamente exigía computación simbólica, y el profesor del
curso confirmó que esa automatización no es necesaria (ADR-0004). De modo que **el sistema no
garantiza que la clave sea válida**: eso sigue dependiendo del criterio del profesor.

Lo que sí aporta es de otro orden, y conviene no exagerarlo:

- **Antes del examen**, obliga a una habilitación explícita, registrada con autor y fecha.
  Nadie califica con una clave que nadie revisó.
- **Después del examen**, la estadística por pregunta puede levantar la bandera: si un
  distractor se lleva casi tantas marcas como la respuesta correcta, algo pasa con esa
  pregunta. No prueba que sean equivalentes, pero señala dónde mirar.

## Una oportunidad, además de los dos problemas

Los distractores no tienen por qué ser opciones incorrectas cualquiera. Si cada uno corresponde
a **un error de procedimiento identificable**, la estadística deja de decir cuántos fallaron y
pasa a decir en qué se equivocaron.

Para una pregunta cuya respuesta es la derivada de `x·sin(x)`:

| Opción | Error que representa |
|---|---|
| `cos(x)` | Se omitió la regla del producto |
| `x·cos(x)` | La regla se aplicó a medias |
| `sin(x) − x·cos(x)` | Error de signo |

Construir buenos distractores así toma tiempo, y es donde el sistema ofrece una ayuda
**opcional**: a solicitud del profesor, propone distractores diagnósticos con apoyo de un
modelo de lenguaje, indicando qué error representa cada uno (RF-11). El profesor decide cuáles
acepta, y el sistema funciona completo sin que nadie use nunca esa función.

## Usuarios del sistema

| Usuario | Rol | Qué hace con el sistema |
|---|---|---|
| **Profesor de cálculo diferencial** | Usuario principal | Registra su banco de preguntas y su clave, habilita el examen, carga las hojas escaneadas, resuelve las marcas ambiguas y consulta los resultados. Opcionalmente, pide distractores diagnósticos durante la preparación. |
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
tiempo de entrega de resultados queda sujeto a la disponibilidad del evaluador; los errores de
lectura se vuelven invisibles, porque nadie distingue una marca dudosa de una clara; y el
tamaño de curso que puede atenderse queda limitado por la capacidad de procesamiento manual.

## Objetivo del proyecto

Construir un sistema que reciba los exámenes resueltos y los califique, con tres frentes:

1. **Leer las hojas de respuesta escaneadas** mediante reconocimiento óptico de marcas (OMR),
   calculando un nivel de confianza por cada detección y enviando a revisión manual todo lo que
   no supere el umbral, en lugar de asignar una respuesta arbitraria.
2. **Calificar contra la clave que el profesor registró** y presentar los resultados en un
   dashboard con notas por curso, estadísticas por examen y por pregunta, y alertas de los
   casos que requieren revisión.
3. **Apoyar opcionalmente la construcción del examen**, proponiendo distractores diagnósticos
   con la etiqueta del error que representa cada uno.

El sistema es una **herramienta de apoyo al criterio del docente**, no un reemplazo de su
decisión final: toda marca dudosa se le devuelve para que decida, y ningún examen se califica
sin que él lo haya habilitado.

## Alcance

**Dentro del alcance**

- Exámenes de opción múltiple sobre hoja de respuestas de formato fijo, con casillas en
  posiciones conocidas.
- Dominio de cálculo diferencial: límites, derivadas y simplificaciones algebraicas.
- Registro del banco de preguntas y de la clave de respuestas por parte del profesor.
- Generación opcional de distractores diagnósticos con apoyo de un modelo de lenguaje.
- Usuarios docentes autenticados, con acceso limitado a los cursos que tienen asignados.
- Ingesta de escaneos en formato JPG, PNG o PDF, individualmente o en lote.

**Fuera del alcance**

- Preguntas de desarrollo o demostración, y cualquier evaluación de procedimientos escritos a
  mano.
- Otras áreas del cálculo: integral, multivariable, ecuaciones diferenciales.
- Interfaz o cuenta para estudiantes.
- Integración con el sistema académico institucional para publicar notas.
- Impresión y distribución física de los exámenes.
- Verificación automática por computación simbólica de la equivalencia entre opciones: la
  validez de la clave la responde el profesor al habilitar el examen, no el software
  (ADR-0004).

## Tensiones de calidad

- **T-1 · Sensibilidad de la detección frente a carga de revisión manual.** Un umbral de
  confianza permisivo produce errores silenciosos; uno estricto manda tantas preguntas a
  revisión que el sistema deja de ahorrar tiempo. Se desarrolla en [`aspectos.md`](aspectos.md).
- **T-2 · Determinismo sintáctico frente a equivalencia matemática** *(retirada, ver
  `aspectos.md`)*. Comparar expresiones como texto puede dejar pasar distractores equivalentes
  a la respuesta correcta; verificarlo automáticamente exige cómputo simbólico. El profesor
  confirmó que esa automatización no es necesaria, así que el riesgo no desaparece: se traslada
  del software al criterio del profesor, con la posibilidad de que un caso no evidente pase
  inadvertido también para una persona (riesgo R-11 del arc42).

## Estado y documentación relacionada

La arquitectura está documentada y en construcción. Esta ficha describe el problema; el diseño
y su justificación viven en:

- [`arc42/arc42-template-ES.md`](arc42/arc42-template-ES.md) — requisitos, restricciones,
  objetivos de calidad y escenarios medibles.
- [`adr/`](adr/) — las decisiones de arquitectura con sus alternativas y consecuencias.
- [`c4/doc-c4.md`](c4/doc-c4.md) — los diagramas del sistema.
- [`aspectos.md`](aspectos.md) — la trazabilidad de cada aspecto, desde el requisito hasta la
  evidencia.
