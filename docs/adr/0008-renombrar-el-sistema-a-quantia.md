# 0008 · Renombrar el sistema a QuantIA

- **Estado:** aceptado
- **Fecha:** 2026-09-22
- **Decide:** Josué Ortega De Arco, María Restrepo Licona, Sebastián Cañas Plata, Susana Rosales Castellar
- **Escenario de calidad relacionado:** ninguno. Es una decisión de identidad del producto: no mueve fronteras, contratos ni escenarios
- **Relación con otros ADR:** no reemplaza ni precisa a ninguno

**La decisión, en una frase:** el sistema se llama **QuantIA**; «sistema de calificación de
exámenes de opción múltiple mediante OMR» pasa a ser su descripción, y el nombre del repositorio
no cambia.

---

## Contexto

Hasta esta decisión el sistema no tenía nombre propio: se lo llamaba por su descripción,
«Sistema de Calificación OMR» en la documentación y «Sistema de calificación automática de
exámenes de cálculo diferencial mediante OMR» en el README. Eso traía dos problemas:

1. **Es largo.** Se repite en títulos, diagramas, la interfaz web y el contrato de la API, y una
   descripción usada como nombre obliga a elegir cada vez entre la versión larga y una abreviada.
   Por eso terminaron conviviendo tres variantes de la misma frase.
2. **Era el único proyecto del curso sin nombre de producto.** Los demás equipos se identifican
   por un nombre propio en el listado del curso; este, por una descripción.

El equipo acordó el cambio antes de la evidencia de la semana 7 y lo dejó registrado como
decisión prevista en la sección 9 del arc42 (commit `a47d5bd`), con una condición: aplicarlo
completo y de una vez. El antecedente muestra por qué: el 30 de agosto el C4 adoptó «QuantIA» por
su cuenta (`5501189`) mientras el resto de la documentación seguía con el nombre anterior, y
durante un tiempo el mismo sistema tuvo dos nombres según el documento.

### Qué significa el nombre

**Quant** viene de *quantification* y *quantitative*: cuantificar, medir y asignar valores, que
es lo que el sistema hace con cada hoja (convierte marcas en respuestas y respuestas en una
nota). **IA** es la inteligencia artificial como tecnología que puede apoyar el análisis.

La segunda mitad necesita una precisión, porque el nombre no puede contradecir lo que el sistema
hace. **La calificación no usa un modelo de lenguaje**: es reconocimiento óptico de marcas
seguido de una comparación contra la clave que el profesor habilitó
([ADR-0005](0005-acotar-el-llm-a-la-generacion-de-distractores-diagnosticos.md)). La IA como
componente del sistema está donde ese ADR la ubica: apoyo opcional en la autoría, proponiendo
distractores diagnósticos cuando el profesor los pide (RF-11). El sistema califica completo sin
invocarla nunca.

---

## Alternativas consideradas

### A. Mantener la descripción como nombre

No cuesta nada cambiar lo que no se cambia. Se descarta por las dos razones del contexto: la
longitud, que ya había producido tres variantes, y la falta de un nombre propio.

### B. Adoptar «QuantIA» (ELEGIDA)

Corto, propio, y ya lo usaba parte del equipo. Su costo es el riesgo que se describe en las
consecuencias: la «IA» del nombre puede leerse como que la calificación la hace un modelo.

---

## Decisión

1. El sistema se llama **QuantIA**. Donde un documento lo presenta por primera vez, lo hace como
   «QuantIA, sistema de calificación de exámenes de opción múltiple mediante OMR»; después basta
   el nombre.
2. El cambio se aplica completo en una sola entrega: la documentación viva (arc42, C4, aspectos,
   ficha del problema, README, registro de uso de IA), el título de la API y de su contrato
   OpenAPI, y la interfaz web.
3. **No se reescribe lo que registra el pasado.** Los ADR 0001 a 0007 están aceptados y no se
   editan, y las entradas anteriores de `docs/ia.md` y de `correcciones.md` citan el nombre que
   se usaba en su momento. Por eso el nombre anterior sigue apareciendo ahí, y es correcto.
4. **El repositorio conserva su nombre**, `AS_202620_Sistema-de-calificacion-automatica`. Lo fija
   la convención del curso (`CONTRATO.md` §1), y cambiarlo rompería los enlaces absolutos y la
   identificación del equipo en las revisiones.
5. **La versión del contrato HTTP no cambia** (1.0.0). El título del documento OpenAPI es un
   metadato: no cambia ninguna ruta, campo ni tipo de lo que la API promete a quien la consume.

---

## Consecuencias

### Positivas

- Un nombre corto y único en títulos, diagramas, interfaz y contrato.
- Termina la convivencia de variantes de la descripción.

### Negativas y costos asumidos

- **El nombre menciona una tecnología que la calificación no usa.** Es la pregunta previsible en
  la sustentación («¿dónde está la IA?»), y la respuesta es la del apartado *Qué significa el
  nombre*: la IA es apoyo opcional en la autoría, no parte del camino de calificación. El equipo
  evaluó este riesgo y lo acepta.
- El nombre anterior sigue en los ADR aceptados y en el historial, por la regla de no reescribir.
- El documento OpenAPI cambia de título, así que se regenera con la herramienta
  (`backend/herramientas/exportar_contrato.py`) y no a mano. La prueba de contrato lo exige.

### Qué dato haría revisar esta decisión

- Que RF-11 no se construya nunca (riesgo R-12): el nombre quedaría aludiendo a una capacidad que
  el sistema no tiene, y habría que decidir si se conserva.
- Que el nombre se confunda con el de otro producto o proyecto.

---

## Trazabilidad

- **Registro previo:** arc42, sección 9, «Decisiones previstas», de donde sale al aplicarse.
- **Documentos afectados:** arc42 (título, §1.1, mapa de contextos y §9), C4 (los tres niveles),
  `aspectos.md`, `ficha-problema.md`, `README.md` y el encabezado de `ia.md`.
- **Código afectado:** `backend/api/main.py` (título y descripción de la aplicación),
  `docs/contrato/openapi.json` (regenerado), `frontend/lib/pantalla_inicio.dart`,
  `frontend/web/index.html`, `frontend/web/manifest.json` y la descripción de
  `frontend/pubspec.yaml`.
- **Pruebas que lo cubren:** `backend/tests/test_contrato.py`, que exige que el contrato
  versionado sea el que genera la aplicación, y la prueba de widget que comprueba que la pantalla
  de inicio muestra el nombre del sistema (`frontend/test/widget_test.dart`).
