# 0004 — Quitar la validación simbólica obligatoria de la clave de respuestas

- **Estado:** aceptado
- **Fecha:** 2026-08-24
- **Decide:** Josué Ortega De Arco, María Restrepo Licona, Sebastián Cañas Plata, Susana Rosales Castellar
- **Escenario de calidad relacionado:** [EC-05](../arc42/arc42-template-ES.md#ec-05) (validez de la clave de respuestas, redefinido en esta decisión)
- **Restricción que modifica:** RNF-01

---

## Contexto

El profesor del curso dio la siguiente retroalimentación sobre el alcance: no hace falta usar
SymPy, porque el OMR reconoce únicamente la marca seleccionada, no el texto de la respuesta.

Antes de decidir hubo que separar dos preguntas que esa frase mezcla, porque tienen respuestas
distintas:

1. **¿Hace falta capacidad de interpretación simbólica dentro del reconocimiento de marcas?**
   No, y nunca la tuvo: RNF-02 y RNF-03 ya fijan que el OMR solo detecta si una casilla está
   rellena, no qué expresión contiene. El glosario del arc42 lo dice explícitamente desde antes
   de esta retroalimentación. En esto el comentario del profesor confirma una decisión ya
   tomada, no la cambia.

2. **¿Hace falta verificar automáticamente, en la fase de autoría, que la clave de respuestas
   es matemáticamente única?** Aquí es donde SymPy vivía realmente (RF-07, EC-05, módulo
   `autoria`), en una fase completamente separada del OMR y sin presión de tiempo real. La
   frase del profesor, tomada literalmente, no es un argumento en contra de esto —el OMR nunca
   hizo este trabajo—, pero la intención real de la observación, confirmada con el equipo, es
   la segunda: no es necesario automatizar esa verificación. El equipo puede construir la clave
   y confiar en la revisión del propio profesor antes de habilitar el examen, sin exigir una
   comprobación simbólica por software.

Se documenta esta distinción porque, sin ella, alguien que lea la retroalimentación más
adelante podría concluir erróneamente que el proyecto alguna vez propuso usar SymPy dentro del
reconocimiento de imagen, lo cual nunca fue cierto y contradiría RNF-02/RNF-03.

**Por qué esto sí es una decisión que hay que registrar.** RNF-01 fijaba el stack obligatorio
como «OMR + LLM + SymPy» y su origen declarado era el enunciado del problema, «no una decisión
libre del equipo». Que el profesor —fuente de ese enunciado— confirme que SymPy deja de ser
obligatorio es exactamente el tipo de cambio que un ADR debe dejar trazado, no una corrección
de redacción para aplicar en silencio.

### Qué toca esta decisión

- **RNF-01** (arc42 §2.1): pierde su tercer componente obligatorio.
- **RF-07** (arc42 §1.1): su mecanismo de verificación deja de ser simbólico.
- **EC-05** (arc42 §10.2): su artefacto y su medida de respuesta estaban definidos alrededor
  del validador SymPy.
- **T-2** (aspectos.md): la tensión «determinismo sintáctico frente a equivalencia matemática
  en SymPy» pierde su objeto, porque ya no hay comparación automática que deba elegir entre
  las dos.
- **Módulo `autoria`** (ADR-0002, aspectos.md A-04): su responsabilidad declarada incluía
  «validación simbólica con SymPy».
- **ADR-0003**, que justificó elegir FastAPI/Python sobre NestJS/Node con dos argumentos
  independientes: (1) SymPy no tiene equivalente maduro en Node, y (2) OpenCV sí. Esta decisión
  retira el argumento (1). No se reemplaza ADR-0003 completo porque su decisión —FastAPI y
  Flutter— no cambia: el argumento (2) ya bastaba por sí mismo, y de hecho es el que la propia
  alternativa B rechazada de ADR-0003 usaba junto con el de SymPy. Se deja constancia aquí, sin
  editar el archivo 0003, porque los ADR aceptados no se tocan una vez escritos.

### Restricciones conocidas

- Los ADR aceptados no se editan ni se borran (convención del curso). Este documento no
  modifica 0003; lo hace explícito en su propia trazabilidad.
- RNF-13 sigue vigente sin cambios: ningún dato personal sale hacia el proveedor de LLM. Esta
  decisión no toca esa restricción.
- El dominio matemático (límites, derivadas, simplificaciones algebraicas de RNF-06) tampoco
  cambia; lo que cambia es quién verifica la unicidad de la clave, no qué se genera.

---

## Alternativas consideradas

### A. Mantener la validación simbólica con SymPy (statu quo)

**A favor:**

- Da una garantía determinista de unicidad matemática, superior a la que puede dar una
  revisión humana bajo presión de tiempo.
- Es lo que ya estaba diseñado y documentado en RF-07 y EC-05; no exige reescribir nada.

**En contra:**

- El profesor, que es quien fija el alcance del curso, indicó que no es necesaria.
- T-2 ya identificaba esta pieza como la de mayor costo de cómputo y mayor cantidad de casos
  límite del sistema (expresiones que SymPy no simplifica, equivalencias válidas solo en un
  dominio restringido), y el equipo no tiene experiencia previa con computación simbólica.
- Mantenerla como obligatoria cuando ya no lo es introduce trabajo y riesgo que ninguna parte
  interesada está pidiendo.

**Por qué no se eligió:** construir para un requisito que la fuente del requisito retiró no es
prudencia, es alcance no acordado.

### B. Retirar la validación simbólica y reemplazarla por aprobación manual del profesor (ELEGIDA)

El profesor revisa la clave propuesta —opción correcta y distractores, generados con apoyo de
LLM o escritos a mano— y debe aprobarla explícitamente antes de que el sistema habilite el
examen para calificación. El sistema no calcula equivalencia matemática; solo registra la
aprobación, con quién la dio y cuándo.

**A favor:**

- Coincide con la retroalimentación del profesor.
- Elimina de `autoria` la pieza de mayor riesgo técnico y de cómputo que tenía, sin que ningún
  escenario de calidad exija recuperarla.
- El «quién y cuándo aprobó» es, además, el mismo patrón de auditoría que RF-10 y RNF-15 ya
  exigen para las calificaciones; extenderlo a la clave es consistente con el resto del
  sistema, no una pieza nueva.
- Reduce el alcance de ADR-0003 a un único argumento duro (OpenCV), que ya es explícitamente
  suficiente en esa decisión.

**En contra:**

- Pierde la garantía determinista: un profesor puede pasar por alto una equivalencia
  algebraica no evidente, exactamente el error que T-2 describía. El riesgo no desaparece, se
  traslada de software a criterio humano.
- El «tiempo de validación ≤5 segundos por pregunta» de la antigua EC-05 dejaba de tener
  sentido para una revisión humana; hay que decidir si EC-05 necesita una medida de tiempo
  nueva o si se retira esa parte.

**Por qué se eligió:** es lo que pidió la fuente del alcance, y el costo que se deja de pagar
(cómputo simbólico, casos límite de SymPy, curva de aprendizaje del equipo con esa librería)
era real y no estaba compensado por ningún requisito que sobreviva a esta decisión.

### C. Validación simbólica como ayuda opcional, no bloqueante

SymPy se mantiene en el sistema como una sugerencia para el profesor («estas dos opciones
parecen equivalentes, ¿confirmas?»), pero no impide habilitar el examen.

**A favor:**

- Conserva parte del valor de la detección automática sin hacerla obligatoria.

**En contra:**

- Sigue exigiendo que el equipo construya e integre el validador simbólico —el mismo trabajo y
  el mismo riesgo técnico de la alternativa A— para un componente que, al no ser bloqueante, es
  más difícil de verificar con un escenario de calidad (¿qué se mide: que sugiere, o que evita
  errores?).
- El profesor no pidió una ayuda opcional; pidió que no fuera necesaria. Construir la mitad del
  alcance retirado no honra la retroalimentación, la reinterpreta.

**Por qué no se eligió:** paga buena parte del costo de la alternativa A sin la garantía que la
justificaba, y sin que nadie lo haya pedido.

---

## Decisión

**1. RNF-01 se redefine a «OMR + LLM».** El stack obligatorio pierde a SymPy. La validación de
que la clave de respuestas es matemáticamente única deja de ser una garantía computada por el
sistema y pasa a ser una aprobación manual del profesor, registrada por el sistema.

**2. RF-07 se redefine:** «El sistema debe presentar al profesor la clave propuesta —opción
correcta y distractores— para su revisión, y no debe habilitar el examen para calificación
hasta que el profesor la apruebe explícitamente.» Ya no menciona SymPy ni verificación
simbólica.

**3. EC-05 se redefine** alrededor de la aprobación manual en lugar del validador simbólico. La
parte de la medida de respuesta sobre tiempo de validación (antes «≤5 segundos por pregunta»,
pensada para una operación de cómputo) queda **pendiente de que el equipo decida** si tiene
sentido una medida de tiempo para una revisión humana, o si se retira sin reemplazo. No se
inventa una cifra en este ADR.

**4. T-2 se marca como resuelta/retirada** en `aspectos.md`, con una nota que explica que el
riesgo que describía —una comparación de texto deja pasar distractores equivalentes— no
desaparece, sino que pasa a mitigarse por revisión humana en vez de por software, con el
conocido riesgo de que un ser humano también puede pasarlo por alto.

**5. La responsabilidad del módulo `autoria`** se redefine como «bancos de preguntas,
generación de enunciados con LLM y aprobación manual de la clave de respuestas», sin mención de
SymPy. Esta redacción se aplica en los dos sitios que sí son editables: el docstring de
`backend/autoria/__init__.py` —que además es la fuente de verdad de la prueba de fronteras— y
el aspecto A-04 de `aspectos.md`. La línea `Importa:` del docstring no cambia, así que la
prueba de fronteras no se ve afectada.

**6. No se agrega `sympy` a `requirements.txt`.** El esqueleto actual nunca lo declaró como
dependencia, así que no hay código que revertir.

**7. No se editan ADR-0002 ni ADR-0003**, porque son ADR aceptados. Sus textos conservan las
menciones a SymPy como registro histórico de lo que se decidió en su momento, y es este ADR el
que los deja sin efecto en ese punto concreto:

- **ADR-0002** describe `autoria` en su tabla de módulos como «generación con LLM y validación
  simbólica con SymPy». Esa fila queda superada por la Decisión 5 de este ADR. Lo único que
  cambia de 0002 es esa descripción de responsabilidad: su decisión de fondo —siete módulos y
  procesamiento asíncrono— no se toca, y `autoria` sigue existiendo con los mismos requisitos
  (RF-06, RF-07) y las mismas fronteras de importación.
- **ADR-0003** apoyaba la elección de FastAPI en dos argumentos independientes; este ADR retira
  el primero (SymPy) y su decisión se sostiene sin cambios sobre el segundo (OpenCV), tal como
  la propia alternativa B rechazada de ese ADR ya argumentaba.

---

## Consecuencias

### Positivas

- El componente de mayor riesgo de cómputo dentro de `autoria` desaparece del alcance
  obligatorio, y con él la curva de aprendizaje de SymPy que ningún integrante del equipo
  tenía.
- El alcance del proyecto queda alineado con lo que la fuente del enunciado —el profesor—
  confirmó que es necesario, en lugar de con una lectura literal de una versión anterior del
  enunciado.
- El patrón «aprobación manual con autor y fecha» reutiliza el mismo mecanismo de auditoría que
  RF-10 exige para las calificaciones, en vez de introducir uno nuevo solo para la clave.
- `docs/ia.md` gana una entrada más que documenta por qué se rechazó la lectura literal de la
  retroalimentación del profesor (que el OMR no necesita SymPy, cosa que el proyecto ya sabía)
  y se aceptó su intención real (que la clave no necesita validación automática).

### Negativas / costos asumidos

- **Se pierde la garantía determinista de unicidad matemática.** Un profesor bajo presión de
  tiempo puede aprobar una clave con un distractor equivalente a la respuesta correcta, el
  mismo modo de fallo que T-2 documentaba para la comparación de texto. El sistema ya no tiene
  una segunda línea de defensa automática contra eso.
- **Queda una medida de EC-05 sin definir** (el equipo debe decidir si hay un tiempo objetivo
  de revisión, o si se retira esa parte del escenario).
- Si en una entrega posterior el profesor o el curso exigieran de nuevo una verificación
  automática, haría falta un ADR nuevo que revierta esta decisión; el trabajo de diseño (no de
  código, porque nunca se implementó) se repite.

### Riesgos y qué los dispararía

| Riesgo | Disparador | Mitigación |
|---|---|---|
| Un distractor equivalente a la respuesta correcta pasa la revisión manual y se habilita un examen con dos respuestas correctas. | El profesor revisa la clave bajo presión de tiempo (por ejemplo, la noche antes del examen) y no advierte una equivalencia algebraica no evidente. | Ninguna automática, por diseño de esta decisión. Mitigación de proceso: la pantalla de revisión debe mostrar las expresiones simplificadas o graficadas una junto a otra, para que el ojo humano tenga la mejor ayuda posible sin cómputo simbólico obligatorio. Queda como recomendación de diseño de interfaz, no como requisito. |
| El equipo reintroduce SymPy más adelante sin dejarlo trazado. | Presión de tiempo o de rúbrica en un corte posterior. | Cualquier reintroducción pasa por un ADR nuevo que revierta explícitamente este, no por un cambio silencioso de RF-07. |

### Qué habría que revisar si cambia

- **Si el profesor o el curso volvieran a exigir verificación automática de la clave**, se
  escribe un ADR-0005 que reintroduce SymPy (o una alternativa), y RF-07/EC-05 vuelven a
  redefinirse.
- **Si se decide una medida de tiempo para EC-05**, se actualiza el arc42 en esa sección; no
  hace falta un ADR nuevo para eso, porque no es un cambio de decisión arquitectónica, es
  completar una medida pendiente.

---

## Trazabilidad

- **Restricción que modifica:** RNF-01 (arc42 §2.1).
- **Requisitos afectados:** RF-07 (redefinido). RF-06 no cambia: el LLM sigue generando
  enunciados y distractores.
- **Escenario afectado:** EC-05 (redefinido; medida de tiempo pendiente de decidir).
- **Aspectos afectados:** [A-04](../aspectos.md#a-04) (redefinido) y la tensión
  [T-2](../aspectos.md#t-2) (marcada resuelta/retirada).
- **ADR relacionados, no modificados** (ver Decisión 7):
  [0002](0002-procesar-calificacion-de-forma-asincrona.md) — la descripción de `autoria` en su
  tabla de módulos queda superada, su decisión de fondo no cambia; y
  [0003](0003-usar-fastapi-y-flutter.md) — pierde uno de sus dos argumentos, su decisión no
  cambia.
- **Elementos C4 afectados:** la nota «por qué SymPy no está aquí» del Nivel 1 deja de aplicar
  porque SymPy deja de ser parte del stack; se retira del documento. La fila de «Proveedor de
  LLM» se actualiza para describir la aprobación manual en lugar de la validación simbólica.
- **Implementación:** pendiente. No existía código de SymPy en el esqueleto de la semana 3, así
  que no hay nada que eliminar del backend; solo se actualiza el docstring de `autoria`.
- **Pruebas que lo cubren:** pendiente. Cuando se construya el aspecto A-04, la prueba
  relevante deja de ser «verificar equivalencia simbólica entre expresiones» y pasa a ser «un
  examen no puede habilitarse sin una aprobación manual registrada, con su autor y su fecha».
- **Evidencia:** la retroalimentación del profesor que origina este ADR se registra en
  `docs/ia.md`, Entrada 4.
