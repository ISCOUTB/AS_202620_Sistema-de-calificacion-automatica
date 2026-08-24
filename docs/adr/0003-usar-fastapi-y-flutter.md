# 0003 — Usar FastAPI en el backend y Flutter en el frontend

- **Estado:** aceptado
- **Fecha:** 2026-08-23
- **Decide:** Josué Ortega De Arco, María Restrepo Licona, Sebastián Cañas Plata, Susana Rosales Castellar
- **Escenario de calidad relacionado:** [EC-05](../arc42/arc42-template-ES.md#ec-05) (validez de la clave de respuestas), [EC-01](../arc42/arc42-template-ES.md#ec-01) (exactitud OMR)
- **Restricción que resuelve:** RNF-08

---

## Contexto

La restricción RNF-08 limita el stack a cuatro opciones fijadas por el curso: **NestJS o
FastAPI** en el backend, **Flutter o Next.js** en el frontend. No es una elección libre entre
todo lo disponible, sino entre esas cuatro.

La decisión hay que tomarla ahora porque el esqueleto ejecutable de la semana 3 ya requiere un
lenguaje y un gestor de dependencias, y porque
[ADR-0002](0002-procesar-calificacion-de-forma-asincrona.md) fijó siete módulos y un pool de
workers que tienen que escribirse en algo.

### Lo que decide el backend

Dos hechos del proyecto pesan más que cualquier preferencia del equipo:

1. **RNF-01 obliga a usar SymPy.** SymPy es una librería de Python y no tiene equivalente
   maduro en el ecosistema de Node. El escenario EC-05 —verificar simbólicamente que solo una
   opción es equivalente a la esperada— depende directamente de ella.
2. **El OMR se construye sobre OpenCV.** Las *bindings* de Python (`cv2`) junto con NumPy y
   SciPy son el camino estándar y el que tiene documentación, ejemplos y respuestas
   disponibles. `opencv4nodejs` existe, pero está mucho menos mantenido. Dado que el OMR es el
   componente de mayor riesgo técnico del proyecto (riesgo R-05) y que nadie del equipo tiene
   experiencia previa con visión por computador, la disponibilidad de material de referencia no
   es un detalle menor.

### Lo que decide el frontend

Aquí ninguna librería fuerza la mano, así que deciden dos cosas: la naturaleza del uso y la
capacidad real del equipo.

**La naturaleza del uso.** El sistema se opera desde un escritorio: los escaneos salen de un
escáner conectado a un computador, la carga es de hasta 200 archivos a la vez (EC-04, EC-07),
el dashboard es denso en tablas y agregaciones por curso, examen y pregunta (RNF-04), y la
revisión manual de marcas ambiguas se hace sentado frente a una pantalla. **No hay ningún flujo
móvil en el sistema**, porque el estudiante ni siquiera es usuario (RNF-05). Esto descarta
construir una aplicación móvil, pero no decide entre las dos opciones: ambas compilan a web.

**La capacidad del equipo.** El equipo ha trabajado un semestre completo con Flutter y Dart. No
tiene experiencia comparable con React. Bajo RNF-09 —cuatro personas con dedicación parcial y
un cronograma con cortes en las semanas 5 y 10— este hecho no es un detalle de preferencia:
determina cuánto del tiempo disponible se gasta aprendiendo la herramienta en lugar de
construyendo el sistema, justo en el semestre en que el trabajo de mayor riesgo (el OMR) ya va
a consumir el margen.

### Fuerzas en tensión

1. **Idoneidad de la herramienta frente a competencia del equipo.** El ecosistema de React es
   más rico para dashboards densos en tablas, pero una herramienta mejor en manos de alguien
   que no la conoce rinde menos que una herramienta adecuada en manos de quien sí.
2. **Un solo lenguaje en todo el repositorio frente a la mejor herramienta para cada mitad.**
   NestJS con Next.js daría TypeScript de punta a punta, pero obligaría a sacar SymPy y OpenCV
   a otro proceso.
3. **Curva de aprendizaje frente a cronograma.** RNF-09 limita el tiempo, y el corte 1 llega en
   la semana 5.

### Restricciones conocidas

- RNF-08: solo NestJS o FastAPI; solo Flutter o Next.js.
- RNF-01: OMR, LLM y SymPy son obligatorios.
- RNF-07: el repositorio arranca con un solo comando.
- RNF-09: cuatro personas con dedicación parcial, sin experiencia en sistemas distribuidos, con
  un semestre de experiencia en Flutter.
- RNF-11: repositorio público; ninguna credencial puede versionarse.
- ADR-0002 fija un único despliegue con cola de trabajos y workers.

---

## Alternativas consideradas

### A. NestJS con un servicio auxiliar en Python

Backend principal en NestJS, con SymPy y el OMR extraídos a un servicio Python al que NestJS
llama por HTTP o por la cola.

**A favor:**

- TypeScript en el backend, con tipos compartibles si el frontend también fuera TypeScript.
- NestJS trae inyección de dependencias y una estructura modular explícita, que encajaría bien
  con los siete módulos del ADR-0002.
- BullMQ es una implementación de cola madura y bien documentada.

**En contra:**

- **Rompe RNF-07:** dos runtimes que arrancar y orquestar, no uno.
- **Contradice el espíritu del ADR-0002**, que descartó los microservicios por complejidad
  operacional. Esta alternativa los reintroduce por la puerta de atrás, y encima sin ninguno de
  sus beneficios: el servicio Python no se escala por separado, solo existe porque el lenguaje
  principal no puede hacer ese trabajo.
- Dos lenguajes de backend y dos suites de pruebas para cuatro personas con dedicación parcial.
- La frontera entre NestJS y el servicio Python quedaría trazada por una limitación de
  herramienta, no por una responsabilidad del dominio, que es justo lo que una arquitectura
  modular debe evitar.
- El equipo tampoco tiene experiencia con NestJS, así que el argumento de la competencia previa
  no lo respalda.

**Por qué no se eligió:** paga la complejidad de un sistema distribuido a cambio de nada que el
proyecto necesite.

### B. NestJS puro, reimplementando la validación simbólica

Todo el backend en NestJS, sustituyendo SymPy por alguna librería de álgebra simbólica de
JavaScript y OpenCV por `opencv4nodejs`.

**A favor:**

- Un solo lenguaje y un solo runtime en el backend; cumple RNF-07 sin esfuerzo.

**En contra:**

- **Incumple RNF-01**, que nombra SymPy explícitamente. El stack está fijado por el enunciado
  del problema, no es una preferencia negociable.
- Las alternativas de álgebra simbólica en JavaScript no ofrecen la comprobación de
  equivalencia que EC-05 necesita con la misma solidez.
- Concentraría el riesgo en el componente que ya es el más arriesgado del proyecto (R-05).

**Por qué no se eligió:** viola una restricción dura. Se documenta para dejar constancia de que
se consideró y de por qué queda fuera.

### C. FastAPI con Next.js

Backend en FastAPI; frontend en Next.js, como aplicación web.

**A favor:**

- **Ecosistema más rico para el dashboard.** Las librerías de React para tablas de datos densas
  y gráficos son más numerosas y maduras que las equivalentes de Flutter, y RNF-04 hace del
  dashboard el entregable central.
- **Carga de archivos nativa del navegador.** El arrastrar y soltar y el `input multiple` son
  primitivas HTML, con soporte y ejemplos abundantes; EC-07 requiere subir hasta 200 archivos.
- El resultado es HTML real, con texto seleccionable y accesibilidad por defecto.

**En contra:**

- **El equipo no tiene experiencia con React.** Aprender el modelo de componentes, el manejo de
  estado y las particularidades de Next.js —enrutamiento por App Router, componentes de
  servidor, hidratación— compite directamente con el tiempo de construir el sistema, bajo un
  cronograma que ya está apretado (RNF-09).
- Se usaría una fracción pequeña del framework: el renderizado en servidor y el SEO no aportan
  nada en una herramienta interna tras autenticación.

**Por qué no se eligió:** sus ventajas son reales pero marginales frente al costo de aprender
un ecosistema entero durante el mismo semestre en que hay que resolver el OMR. La versión
anterior de este ADR eligió esta alternativa y dejó anotado que la existencia de experiencia
previa con Dart la invertiría; el equipo confirmó esa experiencia y la decisión se tomó en
consecuencia.

### D. FastAPI con Flutter web (ELEGIDA)

Backend en FastAPI, workers en el mismo proyecto Python, frontend en Flutter compilado a web.

**A favor:**

- **El equipo ya sabe Flutter.** Un semestre de trabajo previo significa que el tiempo se gasta
  en resolver el problema y no en aprender la herramienta. Bajo RNF-09 este es el argumento de
  mayor peso, y es verificable, no una preferencia.
- **SymPy y OpenCV corren en el proceso que los necesita**, sin servicios auxiliares ni saltos
  de red. RNF-01 se cumple sin fricción.
- **Los workers comparten el código de dominio con la aplicación web**, porque están en el
  mismo proyecto Python. Esto es lo que hace que el monolito modular del ADR-0002 funcione de
  verdad: el módulo `omr` es el mismo objeto para la API y para el worker.
- **Cumple RNF-07:** el frontend compila a archivos estáticos, así que el despliegue no
  necesita un runtime de Node en producción. Un `docker compose up` levanta API, workers, cola,
  base de datos y los estáticos del frontend.
- **Ventaja concreta en la revisión manual (RF-08).** Flutter dibuja sobre un lienzo, lo que
  hace natural el zoom, el desplazamiento y el recorte de la región de la hoja que contiene la
  marca dudosa. Es la pantalla más exigente visualmente de todo el sistema.
- Un solo lenguaje en todo el frontend, con tipado estático, y una única forma de construir
  interfaz en lugar de la combinación de HTML, CSS y JavaScript.

**En contra:**

- **El dashboard denso es más trabajo.** Las tablas paginadas y ordenables, y los gráficos por
  pregunta que pide RNF-04, existen en Flutter pero con menos opciones y menos ejemplos que en
  React. Habrá que construir a mano lo que en React vendría resuelto.
- **La carga múltiple de archivos es menos directa.** Seleccionar y subir hasta 200 archivos
  desde Flutter web pasa por un plugin en lugar de por una primitiva del navegador.
- **Flutter web renderiza sobre lienzo, no sobre el DOM.** Desde que se retiró el renderizador
  HTML, la salida va por CanvasKit o WebAssembly. Eso implica un paquete inicial más pesado y
  un texto que no es HTML real, con las limitaciones de accesibilidad y de selección de texto
  que eso conlleva.
- **La imagen de construcción es pesada.** El SDK de Flutter en Docker ocupa bastante y la
  primera construcción es lenta.

**Por qué se eligió:** es la única alternativa que satisface RNF-01 y RNF-07 sin un segundo
runtime **y** se apoya en competencia que el equipo ya tiene. Sus desventajas son reales, pero
todas son trabajo adicional acotado y previsible; la desventaja de la alternativa C era un
riesgo de cronograma difuso, que es peor en un proyecto con cortes en fecha fija.

---

## Decisión

**1. Backend en FastAPI**, con los siete módulos del ADR-0002 como paquetes de un mismo
proyecto Python, y los workers ejecutándose desde ese mismo proyecto.

**2. Frontend en Flutter, compilado a web.** No se construye aplicación móvil ni de escritorio:
el flujo del sistema es de escritorio a través del navegador, y el estudiante no es usuario
(RNF-05). Se mantiene una sola plataforma de destino para no dispersar el esfuerzo.

**3. El frontend se empaqueta como archivos estáticos.** La imagen de Docker usa una etapa de
construcción con el SDK de Flutter y una etapa final con un servidor estático liviano, de modo
que la imagen que corre no arrastre el SDK. La primera construcción es lenta y se documenta en
el README para que nadie crea que el arranque está colgado.

**4. El arranque único de RNF-07 es `docker compose up`**, que levanta la aplicación web, los
workers, la cola, la base de datos y el frontend. El comando se documenta en el README.

**5. Contra el riesgo R-08 se añade una prueba automatizada de fronteras entre módulos**, que
falla si un módulo importa las entrañas de otro sin pasar por su interfaz pública. FastAPI no
impone modularidad, así que la modularidad se verifica en CI en lugar de confiarla a la
disciplina. Esta prueba es parte del esqueleto ejecutable, no una tarea futura.

**6. Se valida temprano la vista más densa del dashboard.** Antes de la semana 6, se construye
una pantalla de prueba con una tabla paginada y ordenable de tamaño realista, para confirmar
que el camino elegido sostiene RNF-04. Es la contrapartida honesta de haber elegido la opción
con menos ecosistema para esa parte concreta.

---

## Consecuencias

### Positivas

- El equipo empieza a producir desde el primer día en el frontend, sin curva de aprendizaje.
- SymPy y OpenCV se usan directamente, sin capa de integración entre lenguajes.
- Los workers y la API comparten el código de dominio: una mejora en `omr` beneficia a los dos
  sin duplicación ni sincronización.
- El frontend compila a estáticos, así que en producción no hace falta un runtime de Node.
- La pantalla de revisión manual de marcas ambiguas, que es la de mayor exigencia visual,
  queda en la herramienta que mejor la resuelve.
- La generación automática de OpenAPI en FastAPI adelanta trabajo del contrato de API que el
  curso pide en la semana 7.

### Negativas / costos asumidos

- **Dos lenguajes y dos gestores de dependencias** en el repositorio, Python y Dart, con dos
  suites de pruebas y dos trabajos de CI.
- **Sin tipos compartidos** entre backend y frontend: un cambio en el contrato de la API no
  rompe la compilación del frontend, hay que detectarlo con pruebas.
- **El dashboard cuesta más trabajo manual** que en React. Es un costo aceptado a cambio de no
  pagar la curva de aprendizaje, y por eso la Decisión incluye validarlo temprano.
- **Paquete inicial más pesado** y texto renderizado sobre lienzo, con las limitaciones de
  accesibilidad que eso implica. Es tolerable porque los usuarios son docentes en computadores
  institucionales tras autenticación, no visitantes anónimos con conexiones pobres.
- **La modularidad del backend no la impone el framework.** Sin la prueba de fronteras, el
  proyecto se degrada a un paquete plano sin que nadie lo note.
- **Docker pasa a ser requisito** para los cuatro integrantes, y la primera construcción es
  notablemente lenta por el SDK de Flutter.

### Riesgos y qué los dispararía

| Riesgo | Disparador | Mitigación |
|---|---|---|
| El dashboard denso resulta más costoso de lo previsto y compromete RNF-04. | Descubrir en la semana 10 que la tabla por pregunta no rinde o no se puede construir en el tiempo disponible. | La validación temprana del punto 6 de la Decisión: una tabla paginada y ordenable de tamaño realista antes de la semana 6. Si falla, hay tiempo de reaccionar. |
| La carga de 200 archivos desde Flutter web resulta incómoda o poco fiable. | Probar la carga en lote por primera vez ya con EC-07 encima. | Incluir la selección múltiple de archivos en el esqueleto o en el corte vertical de la semana 4, no más tarde. |
| El repositorio se degrada a un paquete plano sin fronteras reales. | Que la prueba de fronteras se desactive o se marque como omitida cuando estorbe. | La prueba corre en CI y bloquea el merge; si una frontera necesita cambiar, se cambia la regla explícitamente y queda en el historial. |
| Divergencia entre el contrato de la API y lo que el frontend espera. | Cambiar un modelo de FastAPI sin actualizar el cliente de Dart. | Generar el cliente desde el OpenAPI de FastAPI cuando exista lógica real, en la semana 7. |
| La construcción de Docker es tan lenta que el equipo deja de usar el comando único. | Reconstruir la imagen de Flutter en cada cambio del frontend. | Documentar en el README el flujo de desarrollo local del frontend con recarga en caliente, dejando `docker compose up` como el arranque oficial e íntegro. |
| Algún integrante no puede levantar el proyecto por Docker. | Equipos con restricciones de instalación o hardware limitado. | Documentar en el README la alternativa local sin Docker para desarrollo. |

### Qué habría que revisar si cambia

- **Si el curso ampliara RNF-08** y permitiera otros stacks, la parte del backend no cambiaría:
  se decidió por la dependencia de SymPy y OpenCV, no por descarte.
- **Si la validación temprana del dashboard mostrara que Flutter no sostiene RNF-04**, habría
  que reevaluar la alternativa C asumiendo el costo de aprendizaje, o reconsiderar el alcance
  de las vistas analíticas.
- **Si apareciera un requisito de uso móvil real**, esta decisión ya lo cubre sin cambios: es la
  única ventaja de Flutter que hoy no se está aprovechando.
- **Si el OMR resultara inviable en Python** por rendimiento, habría que reconsiderar todo el
  eje de la decisión, no solo el lenguaje del frontend.

---

## Trazabilidad

- **Restricción que resuelve:** RNF-08. La decisión también hace efectivos RNF-01 (SymPy y
  OpenCV disponibles) y RNF-07 (arranque único).
- **Escenarios relacionados:** EC-05 depende directamente de SymPy; EC-01 depende del
  ecosistema de OpenCV. EC-04 y EC-07 se apoyan en que los workers compartan proceso y código
  con la API, según ADR-0002. RF-08 (revisión manual) se beneficia del lienzo de Flutter.
- **Aspectos afectados:** todos. En particular [A-04](../aspectos.md#a-04), que es el que usa
  SymPy y el proveedor de LLM, y [A-03](../aspectos.md#a-03), que incluye la revisión manual.
- **Elementos C4 afectados:** fija la tecnología de los contenedores del Nivel 2 previsto en
  ADR-0002: aplicación web y worker en Python/FastAPI, frontend en Flutter servido como
  estáticos.
- **Implementación:** esqueleto ejecutable de la semana 3. Este campo se completa con el hash
  del commit correspondiente.
- **Pruebas que lo cubren:** la prueba de humo del arranque, la prueba de importación de los
  siete módulos y la prueba de fronteras entre módulos descrita en la Decisión.
