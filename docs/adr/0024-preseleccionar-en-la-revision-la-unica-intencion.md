# 0024 · Preseleccionar en la revisión la única intención

- **Estado:** aceptado
- **Fecha:** 2026-11-19
- **Decide:** Josué Ortega De Arco, María Restrepo Licona, Sebastián Cañas Plata, Susana Rosales Castellar
- **Escenarios de calidad relacionados:** [EC-01](../arc42/arc42-template-ES.md#ec-01) (exactitud), [EC-02](../arc42/arc42-template-ES.md#ec-02) (marcas ambiguas)
- **Riesgos:** R-04 (el umbral y ahora el corte son supuestos medidos con hojas sintéticas y tres fotos), la tensión [T-1](../aspectos.md#t-1) (exactitud frente a trabajo de revisión)
- **Restricciones que lo acotan:** RF-03 (lo que no supera el umbral va a revisión, sin una respuesta arbitraria), RF-08 (el docente resuelve y la nota se recalcula), QG-3 (ninguna marca dudosa se convierte en una nota equivocada en silencio), RNF-15 (la nota automática no se borra)
- **Relación con otros ADR:** complementa a [ADR-0023](0023-leer-las-hojas-en-posiciones-fijas-y-mandar-a-revision-lo-que-no-se-ve-bien.md) sin reemplazarlo. Las mismas preguntas siguen yendo a revisión, el umbral sigue en 70 y la nota se calcula igual; cambia cómo llegan esas preguntas al docente y cuándo se acepta un dígito del código del estudiante.

**La decisión, en una frase:** una burbuja con 40 o más de confianza cuenta como intención del
estudiante; si una pregunta en revisión tiene exactamente una, llega al docente con esa opción ya
elegida, sin que cuente en la nota hasta que él guarde, y si una columna del código tiene
exactamente una, el dígito se acepta.

---

## Contexto

Con ADR-0023, una pregunta dudosa o con doble marca va a revisión con las cuatro opciones vacías, y
el docente elige qué marcó el estudiante mirando el recorte de la fila. En las tres fotos del
prototipo (R-05) fueron a revisión 28 preguntas, y en 25 de ellas había una sola marca a la vista:
un chulo, una X, una burbuja a medio llenar o una marca completa con brillo. El docente tenía que
elegir la opción que ya se veía en la imagen, una por una. Es el costo que describe la tensión
T-1: si revisar toma tanto como calificar a mano, el sistema deja de ahorrar tiempo.

Las mismas fotos mostraron dónde está la línea entre una marca y lo que no lo es. **Todo lo borrado
quedó entre 2 y 35 de confianza, y toda marca real, en 50 o más.** El 50 incluye las burbujas que la
lectura no ve bien por brillo o porque su contorno quedó tapado: ADR-0023 las deja en 50 para que
vayan a revisión, y en la foto inclinada eran marcas completas.

El código del estudiante tenía el mismo problema, con una consecuencia peor. Una columna con un
dígito marcado tenue quedaba con `?`, el código incompleto dejaba la nota provisional, y la pantalla
de revisión no tiene cómo corregir el código. Pero en el código no hay docente que confirme: un
dígito aceptado mal le asigna la nota a otro estudiante sin que nadie lo vea.

## Alternativas consideradas

### 1. Qué hacer con la pregunta que tiene una sola marca

| Alternativa | A favor | En contra | Resultado |
|---|---|---|---|
| **Dejarla como está** (ADR-0023) | Nada que cambiar | 25 de 28 preguntas de las fotos llegan vacías aunque la marca se ve | Descartada |
| **Aceptarla sola**: una marca, aunque sea tenue, es la respuesta, y solo van a revisión las filas con más de una candidata | Menos revisión | El sistema decide lo dudoso sin el docente (RF-03, QG-3), y una sugerencia equivocada sería un error silencioso | Descartada |
| **Mandarla a revisión con la opción ya elegida**, y que cuente solo cuando el docente guarde | El docente mira y guarda; la nota no cambia hasta entonces | El docente puede guardar sin mirar | **Elegida** |

### 2. Cómo se ve una preselección

| Alternativa | A favor | En contra | Resultado |
|---|---|---|---|
| **Distinta de una elección**, con un botón de confirmar por pregunta | Se nota qué propuso el sistema | Un toque más por pregunta, que es justo lo que se quería ahorrar | Descartada |
| **Igual que una elección del docente**, con las confusas primero | El docente revisa la imagen y guarda todo junto | No se distingue a simple vista qué eligió el sistema | **Elegida** |

### 3. Dónde se calcula la sugerencia

| Alternativa | A favor | En contra | Resultado |
|---|---|---|---|
| **En `dashboard`, al armar la revisión** | No toca la lectura | `dashboard` no puede importar `omr` (`tests/test_fronteras.py`), y repetiría la regla fuera de donde se decide la pregunta | Descartada |
| **En `omr`, al decidir la pregunta**, guardada en la lectura | La regla vive junto al umbral, y la lectura se puede reproducir | Las hojas leídas antes no la traen | **Elegida** |

### 4. El valor del corte

| Alternativa | A favor | En contra | Resultado |
|---|---|---|---|
| **50** | El más prudente | Igual al 50 que pone la lectura cuando no ve bien una burbuja: deja sin margen el caso de la foto inclinada | Descartada |
| **35 o menos** | Preselecciona más | El borrón real más fuerte de las fotos llegó a 35: lo contaría como intención | Descartada |
| **40** | 5 puntos sobre el borrón más fuerte y 10 bajo la marca real más débil | Margen corto del lado de los borrones | **Elegido**, configurable de 31 a 50 |

## Decisión

1. **El corte de intención** (`omr/decision.py`): una burbuja cuenta como intención si su confianza
   es 40 o más. Es configuración del worker, como el umbral: `OMR_CORTE_DE_INTENCION`, 40 si no se
   fija, comprobado al arrancar entre 31 y 50. Por debajo de 31 contaría como intención una
   burbuja que la lectura considera vacía (30 o menos). Por encima de 50 dejaría de contar la
   burbuja que la lectura dejó en 50 por no verla bien, que en las fotos era siempre una marca. Con
   el umbral en 51 o más, una fila con doble marca tiene dos burbujas sobre el corte, así que nunca
   recibe una sugerencia.
2. **Las preguntas.** Van a revisión las mismas que antes: las dudosas y las de doble marca. Si
   exactamente una de sus burbujas llega al corte, la pregunta lleva esa opción como
   `opcion_sugerida`. Con dos o más, o con ninguna, va sin sugerencia: es una **confusa**. El
   sistema sigue sin elegir entre candidatas.
3. **La sugerencia viaja con la lectura.** `LecturaDePregunta.opcion_sugerida` se guarda en el
   registro de resultados, y `GET /examenes/{examen_id}/revision` la publica en cada pregunta. La
   lectura guarda también el corte con que se decidió (`LecturaDeHoja.corte_de_intencion`), junto
   al umbral. Una hoja leída antes de esta decisión no la trae y llega sin preselección. El
   contrato suma un campo opcional y no cambia de versión.
4. **La nota no cambia hasta que el docente guarda.** La nota provisional sigue sin contar las
   preguntas en revisión, preseleccionadas o no. La preselección entra a la nota como cualquier
   resolución: cuando el docente la guarda, con su nombre y la hora (RF-10, RNF-15).
5. **La pantalla de revisión** muestra primero las confusas, después las preseleccionadas y al
   final las ya resueltas. Una preseleccionada se ve igual que una opción elegida por el docente.
   «Guardar» la envía con las demás, y antes el docente puede cambiarla o elegir «Ninguna». La
   lista de hojas pone primero las que faltan por revisar y después las revisadas, cada grupo de la
   más nueva a la más vieja, con dos filtros que se marcan por separado y la hora de la última
   edición.
6. **El código del estudiante.** Una columna se acepta con su dígito si la lectura lo ve con
   certeza, como antes, **o si exactamente una de sus burbujas llega al corte**. Una marca clara
   con un borrón débil al lado se acepta con la marca clara. Con dos o más intenciones, o con
   ninguna, la columna queda con `?` y la nota sigue provisional. Aquí la tolerancia es cero: por
   eso se midió aparte.

## Consecuencias

### Positivas

- **En las tres fotos del prototipo**, de las 28 preguntas que van a revisión, 25 llegan
  preseleccionadas con lo que se marcó, 3 confusas (la pregunta 32 de cada foto, con dos marcas) y
  **ninguna con una sugerencia equivocada**. El código se lee completo y correcto en las tres.
- **En las hojas sintéticas** (300 hojas, semilla 2026, la misma de EC-01 y EC-02), las 1 163
  preguntas que van a revisión dan **0 sugerencias equivocadas**: las 247 dobles marcas llegan
  confusas, y las marcas tenues, a medias, chulos, X y con brillo llegan preseleccionadas con lo que
  se marcó, salvo 3 tenues que llegan confusas. EC-01 y EC-02 dan las mismas cifras que con
  ADR-0023.
- **En el código** (900 hojas sintéticas en tres semillas, 7 200 columnas con los casos difíciles
  como mayoría), **0 dígitos aceptados mal**. Las 590 columnas con solo un borrón fuerte, calibrado
  para llegar hasta donde llegaron los de las fotos, quedaron con `?`. Las 625 con un borrón fuerte
  al lado de una marca dieron el dígito marcado.
- La evidencia está en [`docs/evidencia/preseleccion-omr.md`](../evidencia/preseleccion-omr.md).

### Negativas y consecuencias asumidas

- **El docente puede guardar sin mirar.** Se acepta porque la nota no cambia hasta que guarda,
  porque las confusas van primero y porque cada pregunta muestra el recorte de su fila al lado de
  la opción elegida.
- **Una preselección no se puede dejar sin decidir**: para guardar el resto hay que confirmarla,
  cambiarla o elegir «Ninguna».
- **El margen del lado de los borrones es corto.** El borrón real más fuerte llegó a 35 y el corte
  está en 40. Los borrones sintéticos calibrados para imitarlos llegaron a 38.
- **10 de las 25 preseleccionadas de las fotos estaban en 50 exacto**, el valor que pone la lectura
  cuando no ve bien una burbuja. En las tres fotos eran marcas, pero es la parte que más depende de
  la luz.
- **El corte y el umbral se calibran juntos.** Una pregunta con una marca se acepta si la segunda
  burbuja más llena tiene a lo sumo 100 menos el umbral. Con el umbral en 70, eso es 30, por debajo
  del corte. Con un umbral de 60 o menos, una segunda burbuja con intención podría quedar dentro de
  una marca aceptada, en una pregunta y en el código.
- **La medición de las preguntas no incluye filas con solo un borrón fuerte**: agregarlas cambiaría
  las cifras publicadas de EC-01 y EC-02. Ese caso se midió en el código, que usa la misma lectura.
- **Las hojas leídas antes no traen la sugerencia.** Para verla hay que volver a subirlas.
- **Todo lo medido es una hoja del prototipo y hojas generadas**, no hojas de estudiantes reales.

## Reversión

- El corte es configuración: `OMR_CORTE_DE_INTENCION` entre 31 y 50, sin cambiar código.
- Quitar la preselección es dejar `opcion_sugerida` en nulo al decidir la pregunta. El campo es
  opcional en el contrato y el sitio muestra la pregunta sin nada elegido.
- Volver al código estricto es aceptar solo la columna que la lectura ve con certeza. La medición
  del código (`herramientas/medir_codigo.py`) dice qué cuesta en columnas por revisar.

## Qué dato haría revisar esta decisión

- **Un dígito del código aceptado mal**, en cualquier medición o en una hoja real. Basta uno.
- **Una sugerencia equivocada** en hojas reales.
- **Un borrón real con 40 o más de confianza**, o una marca real con menos de 40.
- **Docentes que guardan sin mirar**: notas corregidas después por reclamos sobre preguntas que
  llegaron preseleccionadas.

## Trazabilidad

- **Código:** `backend/omr/decision.py` (`sugerir_opcion`, `comprobar_corte_de_intencion`,
  `decidir_pregunta`, `decidir_codigo`), `backend/omr/lectura.py`,
  `backend/infraestructura/modelo.py` (`opcion_sugerida`, `corte_de_intencion`),
  `backend/worker/main.py` (`OMR_CORTE_DE_INTENCION`), `backend/dashboard/revision.py` y
  `backend/api/esquemas.py`; en el frontend, `features/revision/data/servicio_revision.dart`
  (`preguntasEnOrden`, `hojasVisibles`) y `features/revision/views/pantalla_revision.dart`.
- **Pruebas:** `test_decision.py`, `test_lectura.py`, `test_leer_y_calificar.py`,
  `test_ruta_revision.py`, `test_medir_lectura.py`, `test_medir_codigo.py` y
  `test_lectura_fotos_r05.py` (corre con `OMR_FOTOS_R05`); en el frontend,
  `servicio_revision_test.dart` y `revision_test.dart`.
- **Medición:** `herramientas/medir_lectura.py` (la preselección en las hojas de EC-01 y EC-02),
  `herramientas/medir_codigo.py` (el código) y
  `docs/evidencia/preseleccion-omr/contar_fotos_r05.py` (las fotos).
- **Evidencia:** [`docs/evidencia/preseleccion-omr.md`](../evidencia/preseleccion-omr.md) y sus
  informes JSON.
