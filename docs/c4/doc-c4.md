# C4 - Sistema de Calificación OMR

## Nivel 1: Contexto del Sistema

El diagrama de contexto representa el **Sistema de Calificación OMR como una caja negra**, mostrando sus usuarios y los sistemas externos con los que interactúa.

### Diagrama de Contexto

```mermaid
%% Diagrama de Contexto - Sistema de Calificación OMR
%% El color del texto de las etiquetas de las flechas se fija con un
%% <span style="color:..."> para que se lea bien sin importar si el
%% visor usa tema claro u oscuro.

%%{init: {'theme': 'default', 'flowchart': {'htmlLabels': true}, 'themeVariables': {'edgeLabelBackground': '#f4f4f4'}}}%%
flowchart TB
    profesor["<b>Profesor / TA</b><br/>«person»<br/><br/>Docente autorizado que crea exámenes,<br/>sube escaneos y revisa el dashboard<br/>de resultados."]
    sistema["<b>Sistema de Calificación OMR</b><br/>«system»<br/><br/>Procesa imágenes de exámenes,<br/>valida las respuestas y calcula<br/>las calificaciones."]
    storage["<b>Base de Datos / Almacenamiento</b><br/>«external_system»<br/><br/>Almacena exámenes, claves de<br/>respuestas, calificaciones y<br/>registros de auditoría."]

    profesor -->|"<span style='color:#1a1a1a'>Carga exámenes, gestiona cursos<br/>y consulta resultados<br/>[HTTPS / Web UI]</span>"| sistema
    sistema -->|"<span style='color:#1a1a1a'>Lee y escribe exámenes, claves,<br/>calificaciones y auditoría<br/>[SQL / Filesystem]</span>"| storage

    classDef person fill:#08427B,stroke:#073B6F,color:#ffffff
    classDef system fill:#1168BD,stroke:#3379B7,color:#ffffff
    classDef external fill:#686868,stroke:#8C8C8C,color:#ffffff

    class profesor person
    class sistema system
    class storage external

```

### Elementos del contexto

| Elemento | Descripción |
|---|---|
| **Profesor / TA** | Docente autorizado que crea exámenes, sube los escaneos y revisa los resultados generados por el sistema. |
| **Sistema de Calificación OMR** | Sistema encargado de procesar los exámenes, validar las respuestas y generar las calificaciones. |
| **Sistema Académico de la Universidad** | Sistema externo encargado de recibir y centralizar las calificaciones definitivas. |

### Relaciones principales

- **Profesor / TA → Sistema de Calificación OMR:** carga los exámenes, gestiona los cursos y consulta los resultados mediante la interfaz web.
- **Sistema de Calificación OMR → Sistema Académico de la Universidad:** envía las calificaciones definitivas para su registro.


---

## Nivel 2: Contenedores

> Pendiente de desarrollar.

## Nivel 3: Componentes

> Pendiente de desarrollar.

## Nivel 4: Código

> Opcional
