# 0005 — Acotar el LLM a la generación de distractores diagnósticos

- **Estado:** aceptado
- **Fecha:** 2026-08-29
- **Decide:** Josué Ortega De Arco, María Restrepo Licona, Sebastián Cañas Plata, Susana Rosales Castellar
- **Escenario de calidad relacionado:** [EC-05](../arc42/arc42-template-ES.md#ec-05) (habilitación del examen, precisado en esta decisión)
- **Restricción que modifica:** RNF-01

---

## Contexto

Al revisar el paquete de correcciones que originó [ADR-0004](0004-quitar-validacion-simbolica-obligatoria-de-la-clave.md), el equipo detectó que la documentación seguía describiendo un modo de operación distinto del que realmente se va a construir.

El flujo real del sistema es este:

```
SEMANA DE PREPARACIÓN            EXAMEN                DESPUÉS DEL EXAMEN
El profesor carga en la          Se aplica en          El profesor sube fotos o
plataforma sus preguntas         papel. El sistema     escaneos. El sistema lee las
y su clave de respuestas.        no interviene.        marcas, califica y publica.
                                                       Lo dudoso va a revisión.
```

El profesor **llega con las preguntas ya escritas**. No las construye dentro del sistema con ayuda de un modelo de lenguaje: las trae, y lo que necesita de la plataforma es que reciba los exámenes resueltos y los califique.

La documentación, en cambio, describía la generación con LLM como el camino principal de la fase de autoría (RF-06), y RNF-01 declaraba «OMR + LLM» como stack obligatorio después de que ADR-0004 retirara SymPy.

### Por qué esto es una decisión y no una corrección de redacción

RNF-01 es una restricción, no una preferencia: su origen declarado es el enunciado del problema. Decir que el LLM es obligatorio cuando ningún paso del flujo real lo requiere no es un descuido de escritura, es documentar un sistema que no existe. Un evaluador que lea RNF-01 y después el flujo va a encontrar la contradicción, y con razón.

Es además el segundo ajuste consecutivo sobre la misma restricción. ADR-0004 le quitó SymPy tras la retroalimentación del profesor; esta decisión precisa qué papel le queda al LLM. Registrar los dos por separado mantiene legible por qué el stack impuesto se fue acotando y quién pidió cada recorte.

### Qué toca esta decisión

- **RNF-01** (arc42 §2.1): el LLM deja de ser un componente obligatorio del sistema.
- **RF-06** (arc42 §1.1): mezclaba dos cosas de distinta obligatoriedad —registrar el banco y generarlo con LLM— en un solo requisito.
- **RF-07** (arc42 §1.1): la aprobación de la clave pierde peso cuando el profesor aprueba preguntas que él mismo escribió.
- **RF-05** (arc42 §1.1): las estadísticas por pregunta ganan una dimensión opcional.
- **EC-05** (arc42 §10.2): su estímulo asumía una clave «generada por LLM o ingresada manualmente» como dos caminos equivalentes.
- **Módulo `autoria`** (aspectos.md A-04): su responsabilidad declarada pone la generación con LLM antes que el registro del banco.

### Restricciones conocidas

- Los ADR aceptados no se editan ni se borran. Esta decisión **no modifica** ADR-0002, ADR-0003 ni ADR-0004; los deja precisados donde corresponde y lo declara en su trazabilidad.
- RNF-13 sigue vigente: ningún dato personal sale hacia el proveedor de LLM. Esta decisión lo refuerza, porque acota todavía más la ventana en la que el modelo participa.
- RNF-02 y RNF-03 no cambian: la entrada sigue siendo hoja estructurada y opción múltiple.

---

## Alternativas consideradas

### A. Dejar RNF-01 como está y mantener la generación con LLM como camino principal

**A favor:**

- No exige reescribir nada.
- Conserva la lectura más literal del enunciado original del curso, donde el LLM aparecía como parte del stack.

**En contra:**

- Describe un sistema que el equipo no va a construir y que el usuario no va a usar así. El profesor trae sus preguntas.
- Deja al proyecto expuesto a la pregunta más incómoda posible en una sustentación: «¿dónde se usa el LLM, exactamente?», sin una respuesta que resista.

**Por qué no se eligió:** documentar una restricción que el flujo real no cumple es peor que ajustar la restricción con una razón escrita.

### B. Retirar el LLM por completo del proyecto

El sistema se reduce a lectura de marcas, calificación contra la clave, revisión de casos dudosos y dashboard.

**A favor:**

- Es la opción más simple y la más honesta con el flujo descrito: el sistema califica perfectamente sin ningún modelo de lenguaje.
- Elimina una dependencia externa, con su cuota, su latencia y sus modos de fallo (R-03), y cierra R-02 sin necesidad de decidir proveedor.

**En contra:**

- El enunciado del curso incluía el LLM. El profesor pidió retirar la obligatoriedad de SymPy, no la del LLM; retirarlo entero es ir más lejos de lo que ninguna fuente pidió.
- Se pierde la única pieza que le da al sistema valor pedagógico por encima de contar marcas. Sin ella, el proyecto es un lector de marcas con dashboard, que es exactamente lo que la ficha del problema dice que no basta.

**Por qué no se eligió:** resuelve la incoherencia amputando en vez de precisando, y sacrifica la parte del sistema que más lo diferencia.

### C. Acotar el LLM a la generación de distractores diagnósticos, a solicitud del profesor (ELEGIDA)

El LLM deja de ser un paso del flujo y pasa a ser una **capacidad de apoyo** que el profesor invoca cuando quiere, durante la semana de preparación del examen. Su trabajo concreto: proponer **distractores diagnósticos**, opciones incorrectas que corresponden a un error de procedimiento identificable.

Para una pregunta cuya respuesta correcta es `sin(x) + x·cos(x)`, la derivada de `x·sin(x)`:

| Opción propuesta | Error que representa |
|---|---|
| `cos(x)` | Se omitió la regla del producto |
| `x·cos(x)` | La regla se aplicó a medias |
| `sin(x) − x·cos(x)` | Error de signo |

**A favor:**

- Coincide con cómo el equipo describe el uso real: una opción de la plataforma que se usa en la semana de preparación, no un paso obligatorio.
- Le da al LLM un trabajo específico y verificable, en vez de una presencia nominal en el stack.
- Alimenta RF-05: cuando una opción trae asociado el error que representa, el dashboard puede informar no solo cuántos fallaron una pregunta, sino con qué equivocación. Eso convierte el examen en un instrumento de diagnóstico y no solo de medición.
- Mantiene al LLM **fuera de la ruta de calificación**, que es lo que hace alcanzables EC-03 y EC-04. Una llamada a un modelo externo dentro del procesamiento de cada hoja rompería el techo de cinco segundos.
- El costo de uso queda acotado a la fase de autoría: unas pocas llamadas por examen, una vez por corte. Calificar doscientas hojas no consume ninguna.

**En contra:**

- RNF-01 queda con un solo componente verdaderamente obligatorio (OMR). Hay que sostener por qué eso sigue respetando el enunciado.
- La calidad de los distractores propuestos depende del modelo y no es verificable automáticamente: el profesor tiene que revisarlos. Es el mismo modo de fallo que R-11 ya describe.

**Por qué se eligió:** es la única alternativa que describe el sistema real sin renunciar a la pieza que lo diferencia, y deja el LLM donde no compromete ningún escenario de rendimiento.

---

## Decisión

**1. RNF-01 se redefine.** El stack obligatorio queda como **OMR**. El LLM pasa a ser una capacidad de apoyo de la fase de autoría, disponible a solicitud del profesor, y no participa en ningún paso del flujo de calificación. La restricción sigue siendo de origen externo —el enunciado fija que el sistema se apoya en OMR y en un modelo de lenguaje—, pero se precisa dónde actúa cada uno.

**2. RF-06 se parte en dos requisitos de distinta obligatoriedad:**

- **RF-06 (obligatorio):** el sistema debe permitir al profesor registrar su banco de preguntas de cálculo diferencial y su clave de respuestas.
- **RF-11 (opcional):** el sistema debe permitir al profesor solicitar, para una pregunta dada, la generación de distractores diagnósticos con apoyo de un modelo de lenguaje, indicando para cada uno el error de procedimiento que representa. El profesor decide cuáles acepta.

**3. RF-07 se precisa como habilitación explícita.** El sistema no habilita un examen para calificación hasta que el profesor lo habilite de forma explícita, y registra quién lo hizo y cuándo. Cuando el contenido lo propuso el modelo, esa habilitación es además una revisión; cuando el profesor escribió sus propias preguntas, es una confirmación con valor de auditoría. En ambos casos alimenta RNF-15.

**4. RF-05 gana una dimensión opcional.** El dashboard informa siempre la distribución de respuestas por opción. Cuando una opción tiene asociada la etiqueta del error que representa —porque vino de RF-11 o porque el profesor la escribió—, la muestra junto a la distribución. La etiqueta se guarda una sola vez, al crear la pregunta; no genera ninguna llamada al modelo durante la calificación.

**5. La responsabilidad del módulo `autoria` se redefine** como «bancos de preguntas y clave de respuestas, generación opcional de distractores diagnósticos con apoyo de LLM, y habilitación del examen». La línea `Importa:` de su docstring no cambia, así que la prueba de fronteras no se ve afectada.

**6. No se editan los ADR anteriores.** ADR-0002 conserva su descripción de `autoria`, ya superada por la Decisión 5 de ADR-0004 y precisada por esta. ADR-0003 conserva su argumento de OpenCV, que sigue siendo el que sostiene la elección de FastAPI. ADR-0004 no cambia: retiró SymPy, y esta decisión no lo reintroduce.

---

## Consecuencias

### Positivas

- La documentación describe el sistema que el equipo va a construir. La pregunta «¿dónde se usa el LLM?» tiene una respuesta concreta y acotada.
- El LLM queda fuera de la ruta crítica de calificación, lo que protege EC-03 y EC-04 por diseño y no por suerte.
- El costo de operación del modelo se vuelve predecible y pequeño: unas llamadas por examen en la semana de preparación, ninguna al calificar.
- Los distractores diagnósticos dan contenido real a las estadísticas por pregunta que RF-05 ya exigía, sin añadir cómputo en la calificación.
- La separación de fases que sostiene RNF-13 se refuerza: el modelo participa en una ventana todavía más estrecha.

### Negativas / costos asumidos

- **RNF-01 queda con un solo componente obligatorio.** Hay que poder explicar en la sustentación por qué eso no es vaciar la restricción, sino precisarla. El argumento es que el LLM tiene una función especificada y verificable (RF-11), no una casilla marcada.
- **La calidad de los distractores propuestos no es verificable automáticamente.** Desde ADR-0004 no hay validación simbólica, así que el filtro es la revisión del profesor, con el riesgo que R-11 ya describe.
- **El sistema deja de prometer que valida la clave.** La ficha del problema debe reescribirse para no seguir sosteniendo un argumento que el sistema ya no cumple. Es trabajo de documentación, no de arquitectura, pero hay que hacerlo antes de la sustentación.

### Riesgos y qué los dispararía

| Riesgo | Disparador | Mitigación |
|---|---|---|
| Un evaluador concluye que el proyecto abandonó el LLM para evitar el trabajo. | Que RF-11 quede declarado pero sin especificar, sin escenario que lo mida y sin implementación prevista. | Especificar RF-11 con el mismo detalle que los demás requisitos y darle una fila propia en la tabla de trazabilidad, con su semana de construcción. |
| Nadie usa nunca la función de distractores diagnósticos, y el LLM queda como código muerto. | Que el equipo priorice OMR y calificación hasta la semana 16 y RF-11 nunca se construya. | Asignar RF-11 a un integrante desde el reparto por aspectos, con fecha, en lugar de dejarlo como «opcional» sin dueño. |
| El profesor confía en la etiqueta del error sin verificarla. | Aceptar en bloque los distractores propuestos sin revisar cuál error representa cada uno. | La pantalla de habilitación (RF-07) muestra cada opción con su etiqueta, para que la revisión sea explícita y no un clic de aceptar todo. |

### Qué habría que revisar si cambia

- **Si el curso exigiera que el LLM vuelva a ser obligatorio**, se escribe un ADR nuevo que revierta la Decisión 1; RF-06 y RF-11 se fusionarían de nuevo.
- **Si se decide medir RF-11 con un escenario propio**, se agrega a la sección 10 del arc42; no hace falta un ADR para eso.

---

## Trazabilidad

- **Restricción que modifica:** RNF-01 (arc42 §2.1).
- **Requisitos afectados:** RF-06 (acotado), RF-07 (precisado), RF-05 (ampliado con la dimensión opcional). **RF-11 es nuevo.**
- **Escenario afectado:** EC-05 (su estímulo se precisa: la clave la trae el profesor y puede haber sido apoyada por el modelo).
- **Aspecto afectado:** [A-04](../aspectos.md#a-04), redefinido de nuevo. Su nombre pasa a reflejar el registro del banco y la habilitación del examen, no la generación.
- **ADR relacionados, no modificados:**
  [0002](0002-procesar-calificacion-de-forma-asincrona.md) — la tabla de módulos conserva su descripción de `autoria`;
  [0003](0003-usar-fastapi-y-flutter.md) — su decisión se sostiene sobre OpenCV;
  [0004](0004-quitar-validacion-simbolica-obligatoria-de-la-clave.md) — retiró SymPy y esta decisión no lo reintroduce.
- **Elementos C4 afectados:** la fila y la etiqueta de «Proveedor de LLM» en el Nivel 1 pasan a describir la generación de distractores diagnósticos a solicitud. El nodo **sigue punteado**, ahora por dos razones: el proveedor no está decidido (R-02) y su uso es opcional.
- **Implementación:** pendiente. El módulo `autoria` sigue siendo un paquete vacío; el cambio es de docstring.
- **Pruebas que lo cubren:** pendiente. Cuando se construya A-04, la prueba relevante es que un examen no puede habilitarse sin una habilitación registrada con autor y fecha. RF-11, al ser opcional, se prueba por separado: que el sistema funcione completo sin invocarlo nunca.
- **Evidencia:** la conversación de equipo que precisa el flujo real se registra en `docs/ia.md`, Entrada 5.
