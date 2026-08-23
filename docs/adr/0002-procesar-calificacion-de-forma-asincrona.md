# 0002 — Procesar la calificación de forma asíncrona sobre el monolito modular

- **Estado:** aceptado
- **Fecha:** 2026-08-23
- **Decide:** Josué Ortega De Arco, María Restrepo Licona, Sebastián Cañas Plata, Susana Rosales Castellar
- **Escenario de calidad relacionado:** EC-03 (tiempo de respuesta individual), EC-04 (escalabilidad ante carga masiva)
- **Reemplaza a:** [0001 — Arquitectura de Monolito Modular](0001-usar-monolito-modular.md)

---

## Contexto

La revisión de coherencia previa al corte 1 —cruzar el [ADR-0001](0001-usar-monolito-modular.md)
contra el [arc42](../arc42/arc42-template-ES.md), los escenarios
de calidad y el diagrama C4— encontró dos cosas que obligan a volver a decidir. No es una
corrección de estilo: la primera es un requisito que la decisión anterior no puede cumplir, y
la segunda deja parte del sistema sin ubicación.

**1. Los escenarios EC-03 y EC-04 son incompatibles bajo procesamiento síncrono.**

EC-03 exige calificar una hoja individual en ≤5 s (percentil 95). EC-04 exige procesar un lote
de 200 hojas en ≤10 min, que son 3 s por hoja de caudal sostenido. Procesando de forma
secuencial dentro de la petición web, 200 × 5 s = 16,6 min: por encima del techo. Los dos
escenarios son razonables por separado, y por eso el conflicto pasó inadvertido al escribirlos;
solo aparece al multiplicar.

Hay además un problema que la aritmética no muestra: ninguna petición HTTP sobrevive 16
minutos de espera. El navegador expira, el docente ve un error y no tiene forma de saber
cuántas hojas se procesaron. El ADR-0001 mencionaba las colas de mensajes únicamente como algo
a evaluar «si el volumen de exámenes crece exponencialmente», es decir, las trataba como una
optimización futura. La revisión muestra que no lo son: son condición para cumplir un escenario
ya comprometido hoy.

**2. El ADR-0001 razonó sobre premisas que el proyecto contradice.**

Al contrastarlo con las restricciones del arc42 aparecieron tres afirmaciones falsas en su
contexto, que además sostenían parte de su razonamiento:

- Declaraba el sistema **«monousuario en su primera versión»**. RNF-05 define dos roles
  (profesores y TAs), el árbol de utilidad exige ≥10 usuarios concurrentes y QG-4 es un
  objetivo de calidad completo sobre autenticación y aislamiento por curso.
- Afirmaba que **«no hay algoritmos complejos de equivalencia matemática ni procesamiento de
  lenguaje natural»**, y usaba eso como argumento para descartar la arquitectura hexagonal.
  RNF-01 obliga a usar LLM y SymPy, y EC-05 mide precisamente la validación de equivalencia
  algebraica. El descarte de esa alternativa quedó apoyado en algo que el proyecto niega.
- Describía la lógica de negocio como **«simple: comparación de marcas»**, cierto solo para el
  módulo de calificación y falso para la validación simbólica de la clave.

**3. Como consecuencia de lo anterior, la descomposición de 0001 dejaba requisitos sin
ubicación.** Sus cuatro módulos (`captura`, `calificacion`, `dashboard`, `infraestructura`) no
dan sitio a la generación con LLM ni a la validación con SymPy —la mitad del stack obligatorio
de RNF-01, requisitos RF-06 y RF-07— ni a la autenticación y autorización (RF-09, objetivo
QG-4). No es que los módulos estuvieran mal nombrados: faltaban.

**Lo que sigue vigente de 0001.** La elección de fondo —un único despliegue organizado en
módulos, frente a capas o microservicios— resiste la revisión y se confirma. Lo que se decide
aquí es cómo se ejecuta el trabajo dentro de ese despliegue y cuál es su descomposición real.

### Fuerzas en tensión

1. **Latencia individual frente a caudal del lote.** Optimizar para responder rápido a una
   hoja suelta y optimizar para tragar 200 hojas seguidas empujan en direcciones distintas. La
   primera pide hacer el trabajo ya; la segunda pide repartirlo.
2. **Simplicidad de despliegue frente a paralelismo.** RNF-07 exige arrancar con un solo
   comando, lo que penaliza cualquier topología que haya que orquestar. Pero cumplir EC-04
   exige ejecutar varias hojas a la vez.
3. **Inmediatez percibida frente a honestidad de la respuesta.** Responder «calificado» al
   instante es mejor experiencia que responder «recibido», pero solo se puede prometer lo
   primero si de verdad ya ocurrió.
4. **Complejidad asumida hoy frente a reescritura mañana.** Los estados intermedios de un
   trabajo asíncrono cuestan trabajo desde el primer día, aunque al principio se procesen
   pocas hojas.

### Restricciones conocidas

- RNF-07: arranque reproducible con un solo comando.
- El sistema es **multiusuario desde la primera versión**: profesores y TAs, con
  autenticación, roles y aislamiento de datos por curso (RNF-05, EC-06), y al menos 10
  usuarios concurrentes.
- El stack está fijado por RNF-01: OMR para calificar, LLM y SymPy para construir y validar el
  banco de preguntas.
- El sistema opera en **dos fases temporalmente separadas**: autoría (generación y validación,
  sin presión de tiempo) y calificación (ingesta y OMR, con exigencias de latencia y volumen).
  La parte más lenta e impredecible —la llamada al LLM— no está en la ruta crítica de la parte
  más exigente.
- El equipo tiene experiencia en Python y frameworks web monolíticos; no tiene experiencia
  operando sistemas distribuidos.
- RNF-08: el stack de implementación está limitado a las opciones del curso (NestJS o FastAPI
  en el backend; Flutter o Next.js en el frontend). La elección concreta se registrará en un
  ADR propio, pero cualquiera de ellas es compatible con esta decisión.
- RNF-09: cuatro personas con dedicación parcial y un cronograma fijado por el curso. No hay
  capacidad para operar infraestructura distribuida.
- RNF-10: los cuatro integrantes deben contribuir al historial del repositorio, lo que
  favorece una descomposición con fronteras que puedan asignarse por separado.
- Todavía no existe medición del costo real de CPU por hoja: el número de workers no se puede
  fijar con evidencia en este momento.

---

## Alternativas consideradas

La pregunta abierta es cómo satisfacer EC-03, EC-04 y RNF-07 a la vez. Las alternativas se
formulan sobre esa pregunta, no sobre la topología general, que 0001 ya resolvió.

### A. Mantener el procesamiento síncrono y relajar EC-04

Dejar la calificación dentro de la petición web y subir el techo del lote a un valor coherente
con el procesamiento secuencial (~20 min para 200 hojas).

**A favor:**

- Es la opción más simple de construir: no hay cola, ni workers, ni estados intermedios.
- No añade ninguna dependencia de infraestructura.
- Honesta: documenta lo que el sistema realmente hará.

**En contra:**

- Renuncia a un escenario de calidad que sí es alcanzable con esfuerzo moderado; se rebaja el
  objetivo para ajustarlo a la solución, en vez de al revés.
- **No resuelve el problema de fondo**, que no es el número sino la espera: ninguna petición
  HTTP sobrevive 20 minutos. El docente seguiría viendo un error de expiración.
- Un fallo a mitad del lote obliga a volver a subirlo todo, incumpliendo el requisito de
  recuperación ante fallos del árbol de utilidad.

**Por qué no se eligió:** relajar el número no arregla el modo de fallo. Aunque se aceptaran
los 20 minutos, el diseño síncrono seguiría siendo inviable en la práctica.

### B. Paralelismo dentro de la petición HTTP, sin cola

Mantener el procesamiento dentro de la petición pero repartir las hojas entre varios hilos o
procesos, esperando a que todas terminen antes de responder.

**A favor:**

- Cumple la aritmética de EC-04: con 4 vías de ejecución, el lote baja a ~4,2 min.
- Más simple que una cola: no hay que persistir el estado del trabajo.

**En contra:**

- Sigue atado a la vida de la petición: 4 minutos de espera con el navegador bloqueado es una
  experiencia mala, y cualquier corte de red pierde el lote entero.
- **No da recuperación ante fallos:** si el proceso muere a mitad, el trabajo en curso se
  evapora porque solo existía en memoria.
- El docente no puede hacer nada más mientras espera, y no hay forma de mostrar avance parcial.

**Por qué no se eligió:** resuelve el número pero no la durabilidad ni el bloqueo. Es el
paralelismo sin las dos propiedades por las que vale la pena.

### C. Extraer el OMR a un servicio independiente

Sacar el módulo de procesamiento a un servicio desplegable aparte, que escale por su cuenta.

**A favor:**

- Aislamiento garantizado por el límite de proceso, sin depender de la disciplina del equipo.
- Permite escalar solo la parte que consume CPU.

**En contra:**

- **Contradice RNF-07:** deja de ser un solo comando de arranque.
- Reintroduce toda la complejidad operacional que 0001 descartó con buenos argumentos, y que
  esta revisión no invalida.
- El beneficio —escalar el OMR de forma independiente— no lo pide ningún escenario actual:
  EC-04 se satisface con paralelismo dentro de un mismo despliegue.

**Por qué no se eligió:** paga el costo de un sistema distribuido para obtener algo que la
alternativa D ya consigue sin salir del monolito.

### D. Cola de trabajos persistente y pool de workers en el mismo despliegue (ELEGIDA)

La carga de exámenes guarda los archivos, anota los trabajos pendientes en una cola persistente
y responde de inmediato confirmando la **recepción**. Un conjunto de workers —procesos que no
atienden peticiones web— consume la cola y ejecuta el pipeline `omr → calificacion`. El
dashboard refleja el avance.

**A favor:**

- **Cumple EC-04 sin romper EC-03:** las hojas se procesan en paralelo; con 4 workers el lote
  de 200 baja a ~4,2 min, mientras que una hoja suelta sigue tardando sus ≤5 s.
- **Da la recuperación ante fallos casi gratis:** como la cola vive en disco y no en memoria,
  una caída a mitad del lote no pierde nada. Al reiniciar, los trabajos pendientes siguen ahí.
  Esto satisface el requisito del árbol de utilidad —«los exámenes previamente cargados deben
  conservarse sin volver a cargarlos»— que hasta ahora no tenía ningún mecanismo detrás.
- **No rompe RNF-07:** la aplicación web, la cola y los workers se levantan con el mismo
  comando; siguen siendo un único despliegue.
- **Desbloquea la interfaz:** el docente puede navegar el dashboard mientras el lote se
  procesa, y ver el avance.
- Deja abierta la ruta a la alternativa C: si algún día hace falta, la cola es exactamente la
  frontera por la que se corta el servicio de OMR.

**En contra:**

- Introduce estados intermedios del trabajo (encolado, en proceso, terminado, fallido) que hay
  que modelar, mostrar y probar.
- **Cambia lo que el sistema le promete al usuario:** la confirmación pasa de «su examen está
  calificado» a «su examen está recibido». Es un cambio de diseño de interfaz, no solo de
  backend.
- Añade una dependencia de infraestructura desde el primer día.
- El número de workers es un parámetro que no se puede fijar con evidencia todavía.

**Por qué se eligió:** es la única alternativa que satisface EC-03, EC-04 y RNF-07 a la vez, y
la única que además resuelve la recuperación ante fallos. Su costo —modelar estados y ajustar
la interfaz— es trabajo de diseño que se paga una vez, no complejidad operacional recurrente.

---

## Decisión

Se decide lo siguiente:

**1. Se confirma el monolito modular de ADR-0001.** Un único despliegue frente a capas o
microservicios. Esta parte no cambia y sus argumentos originales siguen siendo válidos.

**2. La calificación se ejecuta de forma asíncrona** (alternativa D). La carga confirma la
recepción y encola; un pool de workers consume la cola y ejecuta `omr → calificacion`. El
número de workers es un parámetro de configuración, no una constante del código, y se
calibrará con la medición de EC-04 una vez exista el prototipo de OMR.

**3. Se corrige la descomposición en módulos**, de cuatro a siete, para que todo requisito
tenga dónde vivir:

| Módulo | Responsabilidad | Requisitos que realiza |
|---|---|---|
| `autoria` | Bancos de preguntas, generación con LLM y validación simbólica con SymPy. | RF-06, RF-07 |
| `ingesta` | Recepción y validación de archivos escaneados, individuales o en lote; encolado. | RF-01 |
| `omr` | Detección de marcas y cálculo del nivel de confianza; clasificación de ambigüedad. | RF-02, RF-03 |
| `calificacion` | Comparación contra la clave validada y cálculo de notas; recálculo tras revisión manual. | RF-04, RF-08 |
| `dashboard` | Presentación, agregaciones por curso/examen/pregunta y alertas. | RF-05 |
| `identidad` | Autenticación, roles y aislamiento de datos por curso. | RF-09 |
| `infraestructura` | Persistencia, almacenamiento de imágenes y adaptador de cola. | transversal |

`autoria` e `identidad` son nuevos: cubren RF-06, RF-07 y RF-09, que antes no tenían módulo.
El antiguo `captura` se separa en `ingesta` y `omr`, porque recibir un archivo y detectar
marcas en él son responsabilidades distintas con perfiles de riesgo muy distintos —la primera
es rutinaria, la segunda concentra el mayor riesgo técnico del proyecto— y porque el aspecto
A-01 cubre la primera pero no la segunda.

**4. Aislamiento selectivo mediante interfaz propia** en dos puntos, y solo en esos dos: el
**proveedor de LLM** y el **almacenamiento de imágenes**. El ADR-0001 descartó la arquitectura
hexagonal apoyándose en una premisa falsa; corregida la premisa, la conclusión sigue siendo
razonable como política global —aplicar puertos y adaptadores a los siete módulos por igual
produciría indirección vacía en los más delgados, como `dashboard`— pero no en estos dos
puntos concretos, donde el sistema toca infraestructura volátil o no determinista y el
beneficio es real. Aislar el proveedor de LLM es, además, la mitigación concreta del riesgo
R-03 del arc42: cambiar de proveedor, o quedarse sin cuota a mitad de un parcial, debe ser una
sustitución local y no un rediseño.

---

## Consecuencias

### Positivas

- **EC-03 y EC-04 pasan a ser satisfacibles a la vez**, que era imposible con la decisión
  anterior.
- **Recuperación ante fallos** sin mecanismo adicional: la cola persistente conserva los
  trabajos pendientes.
- **La interfaz deja de bloquearse** durante los lotes largos, y puede mostrar avance parcial.
- **Todo requisito funcional tiene módulo asignado**, lo que hace que la trazabilidad
  `aspecto → requisito → C4 → código` del método ADD se pueda recorrer sin huecos.
- **La dependencia del LLM queda aislada** detrás de una interfaz propia y fuera de la ruta
  crítica de calificación, así que una caída del proveedor no impide calificar.
- **Se conserva la ruta de evolución** hacia servicios independientes: la cola ya es la
  frontera natural de corte.

### Negativas / costos asumidos

- **Complejidad de la asincronía desde el día 1:** estados del trabajo, fallos parciales de un
  lote y comunicación del avance. Se paga aunque al principio el volumen sea bajo.
- **Cambio en el contrato con el usuario:** el docente recibe confirmación de recepción, no de
  calificación. Hay que rediseñar esa pantalla y comunicar el estado intermedio.
- **Dependencia de infraestructura de cola** desde el inicio.
- **Siete paquetes que arrancan casi vacíos**, con más estructura inicial que la propuesta
  anterior de cuatro.
- **La disciplina sigue sustituyendo a la garantía:** nada impide técnicamente que un módulo
  importe las entrañas de otro. Este costo se hereda de 0001 sin cambios.

### Riesgos y qué los dispararía

| Riesgo | Disparador | Mitigación |
|---|---|---|
| El paralelismo no alcanza para EC-04, o dispara el uso de CPU por encima del 85%. | Que el costo real de procesar una hoja sea muy superior al estimado. | Medir el costo por hoja en el prototipo temprano de OMR (riesgo R-05 del arc42) y derivar el número de workers de ese dato antes de comprometer la cifra. |
| La complejidad de la asincronía retrasa la entrega inicial. | Que el equipo construya un sistema de colas elaborado en vez del más simple que funcione. | Empezar con el mecanismo de cola más simple disponible y tratarlo como detalle de infraestructura sustituible, detrás del adaptador de `infraestructura`. |
| El sistema degenera en un monolito desordenado. | Importaciones directas entre módulos sin pasar por sus interfaces públicas. | Revisión de código y análisis automático de dependencias en CI, que falle el build ante una importación prohibida. |
| La modularidad resulta excesiva para los módulos más delgados. | Que `dashboard` o `identidad` no lleguen a tener contenido propio. | Fusionar módulos es barato y reversible; se revisa en la semana 6 con el código real a la vista. |
| El dashboard no comunica bien el estado intermedio y el docente cree que se perdieron hojas. | Diseñar la pantalla de carga como si la calificación fuera inmediata. | Tratar los estados del trabajo como parte del diseño de la interfaz desde el Nivel 2, no como un detalle posterior. |

### Qué habría que revisar si cambia

- **Si desaparece RNF-07** (arranque con un solo comando), la alternativa C vuelve a estar
  sobre la mesa para el módulo `omr`.
- **Si el volumen crece un orden de magnitud**, se evalúa escalar los workers en máquinas
  separadas, lo que ya no sería un monolito estricto.
- **Si el LLM pasara a usarse en la ruta de calificación** y no solo en autoría, se rompería la
  separación de fases sobre la que se apoya esta decisión y habría que reevaluarla entera.
- **Si se admitieran preguntas de desarrollo** (hoy excluidas por RNF-03), entraría lógica de
  interpretación de expresiones escritas mucho más compleja, y habría que reconsiderar el
  aislamiento hexagonal completo para `autoria` y para el nuevo módulo de extracción.
- **Si la medición mostrara que un lote de 200 hojas nunca ocurre en la práctica**, convendría
  revisar si EC-04 sigue justificando el costo de la asincronía.

---

## Trazabilidad

- **Requisitos / aspectos:** RNF-07 es la restricción que impide las alternativas B y C; EC-03
  y EC-04 son los escenarios que fuerzan la asincronía. Los siete módulos realizan RF-01 a
  RF-09 según la tabla de la sección *Decisión*. El aspecto A-01 ([`../aspectos.md`](../aspectos.md)) se ubica
  en `ingesta` e `infraestructura`, y su escenario EC-07 mide la recepción precisamente porque
  esta decisión separa recibir de calificar.
- **Elementos C4 afectados:** esta decisión fija la forma del **Nivel 2**, que deberá mostrar
  como contenedores separados al menos: la **aplicación web**, el **worker de procesamiento**,
  la **cola de trabajos**, la **base de datos** y el **almacén de imágenes**. Los siete módulos
  aparecerán como componentes en el Nivel 3 de la aplicación web y del worker. El Nivel 1 no
  cambia con esta decisión.
- **Implementación:** pendiente. El esqueleto de paquetes se crea en la semana 4; este campo se
  completará con el hash del commit correspondiente.
- **Pruebas que lo cubren:** pendiente. Las previstas son (a) una prueba de humo que verifique
  el arranque con el comando único de RNF-07, (b) una prueba de importación que verifique que
  no hay ciclos ni dependencias prohibidas entre módulos, y (c) una prueba de integración del
  encolado que verifique que un trabajo sobrevive al reinicio del proceso —que es la que
  realmente cubre la recuperación ante fallos—.
- **Evidencia:** pendiente hasta la semana 4.
