# Diagramas C4 — Sistema de Calificación OMR

Este documento es la **fuente única de los diagramas C4** del proyecto. Los diagramas se
escriben como código (Mermaid) para que se revisen en el pull request junto al resto de los
cambios y no se desincronicen en silencio.

| | |
|---|---|
| **Sistema** | QuantIA |
| **Última actualización** | 2026-08-30 |
| **Niveles completos** | Nivel 1 (Contexto) |
| **Notación** | C4 model — [c4model.com](https://c4model.com) · Renderizado con Mermaid `flowchart` |
| **Documentos relacionados** | [`../arc42/arc42-template-ES.md`](../arc42/arc42-template-ES.md) · [`../adr/`](../adr/) · [`../aspectos.md`](../aspectos.md) |

---

## Nivel 1 · Diagrama de Contexto del Sistema

**Tipo de diagrama:** C4 Nivel 1 — Contexto del Sistema
**Ámbito:** Sistema de Calificación OMR
**Fecha:** 2026-08-29
**Audiencia:** cualquier persona, técnica o no

El diagrama representa el Sistema de Calificación OMR **como una caja negra**, junto a sus
usuarios y a los sistemas externos con los que interactúa. No muestra nada de su estructura
interna: eso corresponde al Nivel 2.

```mermaid
---
title: "C4 Nivel 1 · Contexto — Sistema de Calificación OMR (2026-08-29)"
---
flowchart TB
    profesor["<b>Profesor / TA</b>
    [Persona]

    Gestión."]

    sistema["<b>QuantIA</b>
    [Sistema de software]

    Procesa las hojas escaneadas,
    califica contra la clave y presenta
    los resultados."]

    llm["<b>Proveedor de LLM</b>
    "]

    profesor -->|"Registra exámenes y sube escaneos
    <b>[HTTPS · Web UI]</b>"| sistema
    sistema -->|"Devuelve notas y alertas
    <b>[HTTPS · HTML/JSON]</b>"| profesor
    sistema -.->|"Pide distractores
    <b>[HTTPS/JSON]</b>"| llm

    classDef person fill:#08427B,stroke:#073B6F,color:#ffffff
    classDef system fill:#1168BD,stroke:#3379B7,color:#ffffff
    classDef external fill:#999999,stroke:#6B6B6B,color:#ffffff,stroke-dasharray: 5 5

    class profesor person
    class sistema system
    class llm external
```

### Leyenda

| Símbolo | Significado |
|---|---|
| Caja azul oscuro | **Persona.** Usuario humano del sistema. |
| Caja azul | **Sistema en alcance.** El sistema que estamos diseñando. |
| Caja gris con borde punteado | **Sistema externo.** Fuera de nuestro control; lo consumimos pero no lo construimos. |
| Flecha continua | Relación confirmada. La etiqueta indica **propósito** y, en negrita, **tecnología**. |
| Flecha punteada | Relación **prevista pero no confirmada**, sujeta a una decisión pendiente. |

### Elementos del contexto

| Elemento | Tipo | Descripción |
|---|---|---|
| **Profesor / TA** | Persona | Docente autorizado que registra los bancos de preguntas y la clave, sube los escaneos de las hojas de respuesta, resuelve las marcas ambiguas y consulta los resultados. Es el **único** usuario humano del sistema (restricción RNF-05). |
| **Sistema de Calificación OMR** | Sistema en alcance | Recibe el banco de preguntas y la clave que registra el profesor, procesa las hojas escaneadas mediante reconocimiento óptico de marcas, calcula las calificaciones y las presenta en un dashboard interactivo. |
| **Proveedor de LLM** | Sistema externo *(opcional y pendiente)* | Servicio de modelo de lenguaje que el profesor puede invocar en la **fase de autoría** para que le proponga distractores diagnósticos (RF-11). No participa en la calificación, y el sistema opera completo sin invocarlo nunca. Su salida nunca se acepta sola: el profesor decide qué acepta y habilita el examen (RF-07). |

### Relaciones

| # | Origen → Destino | Propósito | Tecnología |
|---|---|---|---|
| 1 | Profesor / TA → Sistema | Registra el banco de preguntas y la clave, habilita el examen, sube las hojas escaneadas, gestiona sus cursos y resuelve las marcas ambiguas. | HTTPS · Web UI |
| 2 | Sistema → Profesor / TA | Presenta notas, estadísticas por pregunta y alertas de revisión manual. | HTTPS · HTML/JSON |
| 3 | Sistema → Proveedor de LLM *(opcional, pendiente)* | Solicita distractores diagnósticos para una pregunta, a petición del profesor. | HTTPS/JSON, por confirmar |

---

### Notas de modelado

Estas notas explican **por qué** ciertos elementos aparecen o no aparecen, que es donde se
concentran los errores más comunes de un diagrama de Nivel 1.

**Por qué la base de datos no está aquí.** Es interna al sistema: la operamos y desplegamos
nosotros, no tiene vida propia fuera del proyecto y nadie más la consume. Aparecerá como
contenedor en el Nivel 2, no como sistema externo en el Nivel 1.

**Por qué la hoja de respuestas física no está aquí.** Un documento en papel no es ni una
persona ni un sistema de software: es el **artefacto de entrada** que el docente digitaliza y
carga. Quien se comunica con el sistema es el docente; la hoja escaneada es el *contenido* de
esa comunicación, y por eso viaja en la etiqueta de la flecha 1, no en un nodo propio. El
escáner tampoco aparece: es una herramienta ofimática ajena al sistema, cuya salida el docente
sube manualmente.

**Por qué el estudiante no está aquí.** El estudiante rellena la hoja, pero no interactúa con
el sistema ni tiene cuenta en él (RNF-05). Es un stakeholder afectado —está registrado como
tal en la sección 1.3 del [arc42](../arc42/arc42-template-ES.md)— pero no un actor del diagrama de contexto.

**Por qué el proveedor de LLM aparece punteado.** Por dos razones, no una. La primera: su uso
es **opcional** (RF-11), así que la relación existe pero no se recorre en todos los casos. La
segunda: el equipo aún no ha decidido cómo se consume el modelo (riesgo R-02 del arc42). Esa
segunda decisión cambia el diagrama:

- **Si se consume una API alojada** (Google AI Studio, Groq, GitHub Models u otra), el nodo se
  confirma como sistema externo, la flecha 3 pasa a continua y hay que documentar sus modos de
  fallo.
- **Si se aloja un modelo local**, el nodo **desaparece** de este nivel y el modelo pasa a ser
  un contenedor del Nivel 2.

El nodo no lleva esas dos condiciones escritas en su etiqueta. Un elemento de Nivel 1 se rotula
con su tipo —«Sistema externo»— y nada más; que el uso sea opcional y el proveedor esté sin
decidir lo comunican el trazo discontinuo, la leyenda y esta nota, y el Nivel 3 lo detallará
cuando se dibuje. Cargar la caja de calificativos la vuelve ilegible sin agregar información
que no esté ya en el documento.

Se dibuja en lugar de omitirlo porque el sistema sí ofrece esa capacidad, aunque no dependa de
ella: omitirlo daría a entender que la función no existe. Desde [ADR-0005](../adr/0005-acotar-el-llm-a-la-generacion-de-distractores-diagnosticos.md)
el LLM ya no es un componente obligatorio de RNF-01, sino una capacidad de apoyo, y el trazo
discontinuo es justamente lo que comunica esa diferencia.

**Por qué las etiquetas de las flechas son cortas.** Cada una nombra el propósito en unas pocas
palabras y la tecnología entre corchetes, que es lo que pide la notación. La descripción completa
de cada relación —incluida la revisión de marcas ambiguas, que la flecha 1 no alcanza a
nombrar— está en la tabla de relaciones de arriba. El diagrama se lee de un vistazo; la tabla se
lee cuando hace falta el detalle.

**Ausencia deliberada de otros sistemas externos.** No hay integración con el sistema académico
institucional ni con ningún servicio de autenticación externo: la autenticación es propia del
sistema (RF-09). Los actores y sistemas externos de este diagrama se corresponden uno a uno con
los socios de comunicación de la sección 3.1 del arc42.

**Qué no cruza la frontera hacia el LLM.** Por RNF-13, la flecha 3 transporta únicamente
especificaciones de preguntas matemáticas: ningún nombre, calificación ni hoja escaneada sale
hacia el proveedor externo. Es una restricción legal con forma de decisión de diseño, y este
diagrama es donde se hace visible. Si en el futuro se integrara la publicación automática de notas, ese sistema
académico entraría aquí como sistema externo con su propia flecha etiquetada.

---

## Nivel 2 · Diagrama de Contenedores

**Tipo de diagrama:** C4 Nivel 2 — Contenedores  
**Ámbito:** Sistema de Calificación OMR  
**Fecha:** 2026-08-29  
**Audiencia:** equipo de desarrollo y personas con conocimiento técnico

El diagrama representa la estructura interna de **QuantIA** mediante sus principales contenedores. A diferencia del Nivel 1, donde QuantIA se representa como una caja negra, este nivel muestra las unidades principales que componen el sistema y las relaciones entre ellas.

El diseño está condicionado por [ADR-0002](../adr/0002-procesar-calificacion-de-forma-asincrona.md), que establece un procesamiento asíncrono. La aplicación web recibe las operaciones del profesor y coordina el procesamiento mediante una cola de trabajos. El procesamiento de las hojas escaneadas, el reconocimiento óptico de marcas y el cálculo de las calificaciones se ejecutan en un worker independiente.

Los contenedores previstos son: **aplicación web**, **worker de procesamiento**, **cola de trabajos**, **base de datos** y **almacén de imágenes**.

```mermaid
---
title: "C4 Nivel 2 · Contenedores — QuantIA (2026-08-29)"
---
flowchart TB
    profesor["<b>Profesor / TA</b>
    [Persona]

    Gestión."]

    subgraph quantia["<b>QuantIA</b>"]

        web["<b>Aplicación web</b>
        [Contenedor]

        Gestiona la autenticación, cursos,
        preguntas, exámenes, carga de escaneos
        y consulta de resultados."]

        cola["<b>Cola de trabajos</b>
        [Contenedor]

        Gestiona los trabajos pendientes
        de procesamiento asíncrono."]

        worker["<b>Worker de procesamiento</b>
        [Contenedor]

        Procesa los escaneos, realiza el OMR,
        calcula las calificaciones y genera
        alertas de revisión."]

        db["<b>Base de datos</b>
        [Contenedor]

        Almacena usuarios, cursos, preguntas,
        claves, exámenes y resultados."]

        imagenes["<b>Almacén de imágenes</b>
        [Contenedor]

        Almacena las hojas de respuesta
        escaneadas y archivos asociados."]
    end

    llm["<b>Proveedor de LLM</b>
    [Sistema externo]"]

    profesor -->|"Gestiona y consulta
    <b>[HTTPS · Web UI]</b>"| web

    web -->|"Lee y escribe datos
    <b>[SQL]</b>"| db

    web -->|"Almacena escaneos
    <b>[Object Storage API]</b>"| imagenes

    web -->|"Crea trabajos de procesamiento
    <b>[Message Queue]</b>"| cola

    cola -->|"Entrega trabajos pendientes
    <b>[Message Queue]</b>"| worker

    worker -->|"Lee y escribe resultados
    <b>[SQL]</b>"| db

    worker -->|"Lee hojas escaneadas
    <b>[Object Storage API]</b>"| imagenes

    web -.->|"Solicita distractores
    <b>[HTTPS/JSON]</b>"| llm

    classDef person fill:#08427B,stroke:#073B6F,color:#ffffff
    classDef container fill:#1168BD,stroke:#3379B7,color:#ffffff
    classDef external fill:#999999,stroke:#6B6B6B,color:#ffffff,stroke-dasharray: 5 5

    class profesor person
    class web,cola,worker,db,imagenes container
    class llm external
```

### Leyenda

| Símbolo | Significado |
|---|---|
| Caja azul oscuro | **Persona.** Usuario humano del sistema. |
| Caja azul | **Contenedor.** Unidad principal de software o infraestructura que forma parte del sistema. |
| Caja gris con borde punteado | **Sistema externo.** Fuera de nuestro control; lo consumimos pero no lo construimos. |
| Flecha continua | Relación confirmada. La etiqueta indica **propósito** y, en negrita, **tecnología**. |
| Flecha punteada | Relación **prevista pero no confirmada**, sujeta a una decisión pendiente. |

### Elementos del Nivel 2

| Elemento | Tipo | Descripción |
|---|---|---|
| **Aplicación web** | Contenedor | Interfaz principal de QuantIA para el profesor. Gestiona la autenticación, los cursos, los bancos de preguntas, los exámenes, la carga de hojas escaneadas y la consulta de resultados. También inicia los trabajos de procesamiento y, opcionalmente, solicita distractores al proveedor de LLM. |
| **Worker de procesamiento** | Contenedor | Ejecuta de forma asíncrona el procesamiento de las hojas escaneadas. Realiza el reconocimiento óptico de marcas (OMR), calcula las calificaciones y genera alertas para los casos que requieren revisión manual. |
| **Cola de trabajos** | Contenedor | Mantiene los trabajos de procesamiento pendientes y permite desacoplar la aplicación web del procesamiento OMR. |
| **Base de datos** | Contenedor | Almacena la información estructurada de QuantIA, incluyendo usuarios, cursos, preguntas, claves de respuesta, exámenes y resultados de las calificaciones. |
| **Almacén de imágenes** | Contenedor | Conserva las hojas de respuesta escaneadas y los archivos necesarios para su procesamiento. |
| **Proveedor de LLM** | Sistema externo *(opcional y pendiente)* | Servicio externo utilizado durante la fase de autoría para proponer distractores diagnósticos. No participa en el procesamiento OMR ni en el cálculo de las calificaciones. |

### Relaciones

| # | Origen → Destino | Propósito | Tecnología |
|---|---|---|---|
| 1 | Profesor / TA → Aplicación web | Gestiona cursos, bancos de preguntas, exámenes, escaneos y consulta resultados. | HTTPS · Web UI |
| 2 | Aplicación web → Base de datos | Consulta y persiste la información estructurada de QuantIA. | SQL |
| 3 | Aplicación web → Almacén de imágenes | Almacena las hojas de respuesta escaneadas. | Object Storage API |
| 4 | Aplicación web → Cola de trabajos | Crea los trabajos que deben ser procesados de forma asíncrona. | Message Queue |
| 5 | Cola de trabajos → Worker de procesamiento | Entrega los trabajos pendientes para su procesamiento. | Message Queue |
| 6 | Worker de procesamiento → Base de datos | Consulta información necesaria y persiste las calificaciones y resultados del procesamiento. | SQL |
| 7 | Worker de procesamiento → Almacén de imágenes | Recupera las hojas escaneadas que debe procesar. | Object Storage API |
| 8 | Aplicación web → Proveedor de LLM *(opcional, pendiente)* | Solicita distractores diagnósticos para una pregunta durante la autoría. | HTTPS/JSON |

---

### Notas de modelado

Estas notas explican **por qué** se han separado los diferentes contenedores y cómo se relacionan con las decisiones arquitectónicas establecidas para QuantIA.

**Por qué la aplicación web y el worker están separados.** El procesamiento de las hojas de respuesta puede requerir operaciones de reconocimiento de imágenes y cálculo que no deben bloquear la interacción del profesor. Por esta razón, la aplicación web recibe la solicitud y delega el procesamiento al worker mediante la cola de trabajos, siguiendo la decisión establecida en [ADR-0002](../adr/0002-procesar-calificacion-de-forma-asincrona.md).

**Por qué existe una cola de trabajos.** La cola permite implementar el procesamiento asíncrono. Cuando el profesor carga las hojas escaneadas, la aplicación web crea un trabajo y lo coloca en la cola. El worker toma posteriormente ese trabajo y ejecuta el procesamiento. De esta manera, la aplicación web puede continuar atendiendo otras solicitudes mientras se procesa el examen.

**Por qué el almacén de imágenes está separado de la base de datos.** Las hojas de respuesta escaneadas son archivos binarios y no forman parte de la información estructurada de QuantIA. Por ello, se almacenan en un contenedor de almacenamiento independiente. La base de datos conserva la información estructurada y las referencias necesarias para relacionar cada archivo con su examen correspondiente.

**Por qué la base de datos aparece como contenedor.** La base de datos forma parte de la infraestructura necesaria para operar QuantIA y es utilizada directamente por los contenedores de la aplicación web y del worker. En el Nivel 1 permanece oculta porque es una parte interna del sistema; en este nivel se muestra para explicar cómo se persiste la información.

**Por qué el profesor interactúa únicamente con la aplicación web.** El profesor es el único usuario humano de QuantIA (RNF-05). No interactúa directamente con la base de datos, la cola, el worker ni el almacén de imágenes. La aplicación web actúa como punto de entrada para sus operaciones.

**Por qué el worker accede directamente al almacén de imágenes.** El worker necesita recuperar las hojas escaneadas para realizar el procesamiento OMR. La aplicación web se encarga de registrar la carga y almacenar el archivo, mientras que el worker lo recupera cuando consume el trabajo correspondiente.

**Por qué el worker escribe en la base de datos.** Una vez terminado el procesamiento, el worker debe persistir los resultados de la calificación y la información necesaria para que la aplicación web pueda presentarlos posteriormente al profesor.

**Por qué el proveedor de LLM se conecta con la aplicación web.** El LLM únicamente participa en la fase de autoría, cuando el profesor solicita propuestas de distractores diagnósticos (RF-11). No participa en el flujo de procesamiento de las hojas ni en el cálculo de las calificaciones. Por ello, la interacción se realiza desde la aplicación web.

**Por qué la relación con el proveedor de LLM aparece punteada.** Al igual que en el Nivel 1, el uso del LLM es opcional y la decisión sobre cómo consumir el modelo todavía está pendiente. Si se utiliza una API alojada, continuará representándose como un sistema externo. Si se decide alojar un modelo local, el proveedor externo desaparecerá del Nivel 1 y el modelo o servicio correspondiente deberá representarse como un contenedor de QuantIA.

**Qué información se envía al LLM.** De acuerdo con RNF-13, la interacción con el proveedor de LLM se limita a especificaciones de preguntas matemáticas necesarias para generar distractores. No deben enviarse nombres de estudiantes, calificaciones ni hojas escaneadas.

**Por qué no aparece el sistema académico institucional.** Actualmente no existe una integración con el sistema académico institucional. QuantIA presenta los resultados directamente al profesor, por lo que no se incorpora un contenedor o sistema externo adicional en este nivel.

**Por qué no aparece el estudiante.** El estudiante no interactúa directamente con QuantIA ni dispone de una cuenta (RNF-05). Su participación consiste en completar la hoja física de respuestas, que posteriormente es escaneada y cargada por el profesor.

**Por qué no aparece el escáner.** El escáner es una herramienta externa utilizada para digitalizar la hoja física. Su resultado es un archivo que el profesor carga en QuantIA, por lo que no constituye un contenedor ni un sistema con el que QuantIA mantenga una integración propia.

**Procesamiento asíncrono.** El flujo principal de procesamiento es:

1. El profesor carga las hojas escaneadas mediante la aplicación web.
2. La aplicación web almacena las hojas en el almacén de imágenes.
3. La aplicación web crea un trabajo de procesamiento.
4. La cola conserva el trabajo hasta que un worker pueda procesarlo.
5. El worker consume el trabajo y recupera las hojas escaneadas.
6. El worker realiza el reconocimiento óptico de marcas (OMR).
7. El worker calcula las calificaciones utilizando la clave registrada.
8. El worker almacena los resultados en la base de datos.
9. El profesor consulta las notas, estadísticas y alertas mediante la aplicación web.
10. Cuando corresponde, el profesor resuelve manualmente las marcas ambiguas desde la aplicación web.
## Nivel 3 · Diagrama de Componentes

> **Pendiente — semanas 4 y 6.**
>
> Se dibujará el interior de la **aplicación web** y del **worker de procesamiento**. Los
> componentes serán los siete módulos definidos en ADR-0002: `autoria`, `ingesta`, `omr`,
> `calificacion`, `dashboard`, `identidad` e `infraestructura`. Cada componente de este nivel
> debe existir ya como contenedor o dentro de un contenedor del Nivel 2: no se inventan piezas
> al bajar de nivel.

## Nivel 4 · Código

> **No se elaborará.** Es opcional según la guía del curso y, cuando se necesite, conviene
> generarlo desde el código en lugar de mantenerlo a mano, porque se desincroniza de inmediato.
