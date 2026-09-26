# Correcciones a la retroalimentación automática

Este documento responde al encargo del docente de revisar la coherencia de la retroalimentación
publicada en `ISCOUTB/AS_202620_feedback` y reportar, sin corregirlos, los puntos en los que una
revisión da por ausente o incompleto algo que sí está en este repositorio.

**Alcance.** Solo se reportan hallazgos en una dirección: **la revisión respecto al repositorio**.
Lo que el repositorio deba corregir por su cuenta no es objeto de este documento, salvo la
sección 4, donde se reconoce explícitamente lo que la revisión señaló con razón.

**Método.** Cada afirmación se contrasta contra **el commit que la propia revisión declara haber
mirado**, no contra el estado actual. Si el equipo arregló algo después del cierre, no es un error
de la revisión y no aparece aquí. Los comandos para repetir cualquier comprobación están en la
sección 6, y los de S6 y S7, en la 7.5.

**Este documento no corrige nada.** Reporta el hallazgo y dice si corresponde corregir, dónde y
por qué. Las correcciones que ya se hicieron por otras razones se indican como tales.

| Revisión | Commit que declara haber mirado | Fecha del commit | Cierre de la actividad |
|---|---|---|---|
| Evidencia S1 | `4f6f5687` | 2026-08-09T13:16:43-05:00 | 2026-08-10T05:00:00Z |
| Evidencia S2 | `d4302f4b` | 2026-08-16T23:17:26-05:00 | 2026-08-17T05:00:00Z |
| Evidencia S3 | `dd422fb2` | 2026-08-23T23:52:23-05:00 | 2026-08-24T05:00:00Z |
| Evidencia S4 | `cede35e4` | 2026-08-30T23:51:34-05:00 | 2026-08-31T05:00:00Z |
| Primer corte | `cede35e4` (sin etiqueta) | 2026-08-30T23:51:34-05:00 | 2026-09-07T05:00:00Z |
| Evidencia S6 (pasada temprana) | `a47d5bd` | 2026-09-13T23:21:55-05:00 | 2026-09-14T05:00:00Z |
| Evidencia S7 (revisión corregida del 24 de septiembre) | `2269ca5` | 2026-09-20T21:48:00-05:00 | 2026-09-21T05:00:00Z |

---

## 1. Hallazgos que se solicita revisar

Ordenados por el efecto que tienen sobre el recuento de criterios.

| # | Dónde lo dice la revisión | Qué afirma | Qué hay en el commit revisado | Prueba verificable | ¿Corregir? |
|---|---|---|---|---|---|
| **1** | S4, matriz de la ficha, fila *Prueba automatizada del recorrido completo, en verde* → `No verificado`. S4, matriz transversal, fila *README y pipeline* → `No verificado`. `feedback.md` S4: «Suban evidencia del run de CI en verde (URL)». Planilla, *Lo que se arrastra*: «Verificación de CI sin runs». Planilla, contrato: *Pipeline en verde* → `No verificado`. Corte 1, fila *Prueba que cubre el cambio, en verde en el pipeline* → `No cumple` | «Sin `runs_ci` en la evidencia»; «Falta URL de run en verde anterior a la etiqueta» | El repositorio tiene **21 workflow runs y los 21 están en estado success**, públicos y legibles sin iniciar sesión. Uno de ellos corre sobre `cede35e`, que es el commit que la revisión califica. La URL de un run en verde ya estaba **dentro del repositorio** en el commit revisado | `docs/aspectos.md` línea 220 en `cede35e` enlaza el run `33347922678` sobre el commit `59e182e`, con `backend-tests` y `frontend-tests` en verde, disparado el 2026-08-31T01:33Z, tres horas y media antes del cierre de S4. La lista completa está en la pestaña Actions del repositorio, y el propio comando que la revisión sugiere (`curl -s .../actions/runs?per_page=20`) los devuelve | **Sí.** Afecta dos criterios de S4, uno del contrato y uno del corte 1 |
| **2** | S4, matriz de la ficha, fila *C4 nivel 1 y nivel 2 presentes y coherentes entre sí* → `No cumple`. `feedback.md` S4: «completen el C4 nivel 2 con su diagrama». Corte 1, fila *Límites declarados conservados tras el cambio* → `No cumple` («Nivel 2 del C4 no visible completo») | «La sección Nivel 2 lista contenedores "previstos" sin diagrama completo visible» | El diagrama del Nivel 2 **está completo** en el commit revisado: cinco contenedores, leyenda, tabla de elementos, ocho relaciones y once notas de modelado | `docs/c4/doc-c4.md` en `cede35e`: sección «Nivel 2 · Diagrama de Contenedores» en la línea 153 y bloque Mermaid completo entre las líneas 166 y 245, sobre un archivo de 338 líneas | **Sí, con una salvedad del equipo** (ver nota A) |
| **3** | S4, matriz transversal, fila *Registro de uso de IA* → `No verificado`. Corte 1, fila *Salida de IA aceptada, corregida o rechazada con motivo técnico* → `No cumple` | «`docs/ia.md` existe [...] contenido no visible en la evidencia» | El archivo tiene **79 líneas y seis entradas**, cada una con su sección «Qué se rechazó» y el motivo técnico | `docs/ia.md` en `cede35e`: entradas 1 a 6 en las líneas 15, 26, 37, 48, 59 y 70, con «Qué se rechazó» en las líneas 23, 34, 45, 56, 67 y 78 | **Sí.** Ver también el hallazgo 5, sobre el doble veredicto |
| **4** | Corte 1, filas *ADR del reto con alternativas, fuerzas, decisión y consecuencias* y *Límites declarados conservados tras el cambio*, ambas → `No cumple` | La observación de la primera dice, textualmente, «**Estructuralmente cumplen**; falta confirmar que sean los del reto sin la restricción asignada». La de la segunda dice «no se pudo verificar correspondencia total» | Son dos criterios marcados como incumplidos cuya propia observación declara que el artefacto cumple o que no se pudo verificar. En S1, S2 y S4 el mismo revisor reserva `No verificado` para ese caso | Comparar la fila *Ficha del problema* de S1 y la fila *Registro de uso de IA* de S4, marcadas `No verificado` por no poder comprobarse, con estas dos, marcadas `No cumple` por lo mismo | **Sí.** La diferencia entre `No cumple` y `No verificado` es lo que produce el recuento de 0 de 12 |
| **5** | S4, fila *Registro de uso de IA* → `No verificado`. Corte 1, fila equivalente → `No cumple` | El mismo archivo, en el mismo commit y con el mismo motivo declarado («contenido no visible»), recibe dos veredictos distintos | Es una incoherencia interna entre dos revisiones del kit, no una discrepancia con el repositorio | Ambas filas citan `docs/ia.md` en `cede35e` | **Sí.** Se solicita unificar el veredicto |
| **6** | Corte 1, rúbrica sugerida: cuatro criterios en 0,00 con la justificación «no se identifica una respuesta a la restricción nueva» | Se puntúa en cero la respuesta a una restricción que el propio revisor declara no haber tenido | La misma revisión escribe, en *Hallazgos para la planilla*: «la restricción asignada al equipo no fue proporcionada; el diagnóstico no se puede contrastar». El equipo tampoco la recibió por ningún canal | Sección *No verificado / pendientes* de `semana-05-corte1.md`, primer punto | **Sí.** Ver nota B sobre cómo respondió el equipo |
| **7** | `feedback.md` S4: «Revisen que la sección 9 del arc42 cite los ADRs y que el glosario tenga términos del dominio» | Pide corregir dos cosas que la matriz de esa misma semana marca como `Cumple` | La sección 9 tiene una tabla con hipervínculo a los cinco ADR, con estado, fecha y escenarios relacionados. El glosario tiene **16 términos de dominio** (OMR, OCR, distractor, distractor diagnóstico, umbral de confianza, clave de respuestas, cola de trabajos, worker, habeas data, p95, entre otros) | `docs/arc42/arc42-template-ES.md` en `cede35e`: sección 9 desde la línea 430, con la tabla de ADR hasta la línea 442; sección 12 desde la línea 698 | **Sí**, aunque no cambia el recuento: se solicita retirar la observación de la retroalimentación publicable, porque contradice la matriz de su propia semana |
| **8** | Planilla, tabla *Contribución por integrante*: 27 / 9 / 1 / 3, con «Última revisión 2026-09-03» | Las cifras no corresponden a ningún estado calificado | En `dd422fb` (S3) el historial da 25 / 9 / 3 / 1 y en `cede35e` (S4 y corte 1) da **34 / 16 / 7 / 3**. La propia matriz de S4 registra «4 autores con 34+16+7+3 commits», que contradice a la planilla | `git shortlog -sn cede35e` y `git shortlog -sn dd422fb` | **Sí.** Subestima a tres de los cuatro integrantes en una fila que la planilla usa para evaluar la participación |

---

## 2. Notas sobre dos de los hallazgos

**Nota A: qué indujo el error del Nivel 2, y de quién es.** El equipo no presenta el hallazgo 2
como un error solo del revisor. En el commit revisado, la línea 11 de `docs/c4/doc-c4.md` decía
`| **Niveles completos** | Nivel 1 (Contexto) |` aunque el propio archivo dibuja el Nivel 2
ciento cuarenta líneas más abajo, y la línea 164 anunciaba los contenedores como «previstos». La
revisión cita esas dos frases como su evidencia. Son exactamente las dos que un lector encontraría
primero, y la contradicción es responsabilidad del equipo. Lo que se solicita revisar es la
conclusión, no la lectura: el diagrama estaba ahí y era comprobable en el mismo archivo. De las dos
frases, la primera se corrigió en `201acac`. La segunda («Los contenedores previstos son», hoy en
la línea 165) no se corrigió entonces, aunque este documento lo daba por hecho: se corrigió junto
con la reescritura del Nivel 3 del C4, y se puede verificar con
`git log -S'Los contenedores previstos son' -- docs/c4/doc-c4.md`.

**Nota B: qué hizo el equipo ante la restricción que no llegó.** El equipo no dejó el reto sin
responder. Se tomó como restricción la deuda **R-06** (ausencia de decisión de persistencia y de
almacenamiento de imágenes), declarada en la sección 11 del arc42 desde antes del corte, y sobre
ella se hizo el ejercicio completo: diagnóstico con línea base medida, comparación de cuatro
alternativas, ADR-0006, implementación sobre el corte vertical de A-01, pruebas y medición
posterior. Si la restricción asignada era otra, el equipo está en condiciones de rehacer el
ejercicio sobre la correcta.

---

## 3. Efecto sobre el recuento de S4

La matriz de S4 tiene diez criterios y la revisión cuenta seis cumplidos, con la nota sugerida
`1 + 4 × (6/10) = 3,4`. Tres de los cuatro criterios restantes dependen de los hallazgos 1 y 2.

| Criterio de S4 | Estado publicado | Depende de | Estado si se acepta el hallazgo |
|---|---|---|---|
| C4 nivel 1 y nivel 2 presentes y coherentes entre sí | `No cumple` | Hallazgo 2 | Cumple |
| Límites del C4 nivel 2 correspondientes a la estructura del código | `No verificado` | Hallazgo 2 (la observación dice «depende del nivel 2, incompleto») | Verificable |
| Prueba automatizada del recorrido completo, en verde | `No verificado` | Hallazgo 1 | Cumple |
| Fila de `docs/aspectos.md` completa hasta la columna Pruebas | `No cumple` | Nada. **La observación es correcta** | No cumple |

Con los hallazgos 1 y 2 aceptados el recuento pasa de **6 a 9 de 10**, y la misma fórmula da
`1 + 4 × (9/10) = 4,6`. El equipo no solicita una nota: solicita que el recuento se calcule sobre
lo que el repositorio contenía en `cede35e`.

---

## 4. Lo que la revisión señala y es cierto

Esta sección existe porque un informe que solo reclama no merece crédito. Todo lo que sigue se
verificó contra el commit correspondiente y **la revisión tiene razón**.

| Revisión | Observación | Comprobación |
|---|---|---|
| S1 | Solo una cuenta contribuyendo al historial | `git shortlog -sn 4f6f5687` devuelve una sola cuenta |
| S1 | La ficha del problema no está en el repositorio | `git ls-tree -r 4f6f5687` no la contiene. Entró el 23 de agosto |
| S1 | `docs/adr` y `docs/c4` versionados como blobs vacíos y no como directorios | Correcto en `4f6f5687` |
| S2 | Restricciones sin categorías organizativas ni legales | En `d4302f4` la sección 2 tiene seis restricciones con categorías propias (tecnológica, de entrada, de diseño, de dominio, de usuarios, de salida). Ninguna organizativa ni legal |
| S2 | `docs/aspectos.md` no enlaza los escenarios desde la fila del aspecto | Correcto en `d4302f4` |
| S2 | Una sola cuenta hasta el cierre | `git shortlog -sn d4302f4` devuelve una sola cuenta |
| S3 | No hay arranque, ni prueba, ni estructura de paquetes al cierre | `git ls-tree -r dd422fb` contiene únicamente `README.md` y ocho archivos bajo `docs/`. No hay código |
| S3 | Dos commits posteriores al cierre; el esqueleto llegó cerca de dos horas tarde | Correcto. El equipo lo asume y no lo discute |
| S4 | La fila A-01 debe enlazar un contenedor C4 real y no «C2 pendiente» | Correcto. `docs/aspectos.md` línea 29 en `cede35e` dice `C1: Sistema de Calificación OMR · C2 pendiente (S4)` |
| S4 | Secciones 7 y 8 del arc42 pendientes | Correcto, y declarado como tal en el propio documento |
| Corte 1 | No existe la etiqueta `corte-1` | Correcto en el momento de la revisión preliminar |
| Corte 1 | No hay línea base medida con herramienta y procedimiento | Correcto en `cede35e` |

---

## 5. Una incoherencia que favorece al equipo y que no se solicita cambiar

La matriz de S3 califica la fila *Contribución de todos los integrantes* como `Cumple` citando
cuatro cuentas «en HEAD», mientras todas las demás filas de esa misma matriz se califican sobre
`dd422fb`. Es un criterio de verificación distinto para una sola fila. El resultado no cambia,
porque en `dd422fb` ya había cuatro cuentas, pero se deja constancia para que el criterio quede
parejo. El equipo no pide que se modifique.

Del mismo modo, en la matriz de S4 hay cuatro filas marcadas `Cumple` cuya observación dice «no
inspeccionado» o «no visibles» (secciones 2 a 4, sección 9, sección 10 y glosario), mientras otras
filas se marcan `No verificado` o `No cumple` por esa misma razón. Se señala únicamente porque es
el criterio que sostiene los hallazgos 1 y 3, no para pedir que las favorables se revisen.

---

## 6. Cómo repetir cada comprobación

```bash
git clone https://github.com/ISCOUTB/AS_202620_Sistema-de-calificacion-automatica.git
cd AS_202620_Sistema-de-calificacion-automatica

# Hallazgo 1 - runs de CI (los 21 en verde, sin autenticación)
curl -s "https://api.github.com/repos/ISCOUTB/AS_202620_Sistema-de-calificacion-automatica/actions/runs?per_page=30" \
  | python -c "import json,sys;[print(r['created_at'],r['head_sha'][:8],r['conclusion']) for r in json.load(sys.stdin)['workflow_runs']]"
git show cede35e:docs/aspectos.md | sed -n '220p'          # la URL ya estaba en el repositorio

# Hallazgo 2 - el Nivel 2 del C4 en el commit revisado
git show cede35e:docs/c4/doc-c4.md | sed -n '153,245p'

# Hallazgo 3 - contenido de docs/ia.md en el commit revisado
git show cede35e:docs/ia.md | grep -n "Qué se rechazó"

# Hallazgo 7 - seccion 9 y glosario
git show cede35e:docs/arc42/arc42-template-ES.md | sed -n '436,442p;698,716p'

# Hallazgo 8 - contribucion por integrante
git shortlog -sn cede35e
git shortlog -sn dd422fb

# Seccion 4 - lo que la revision senala con razon
git ls-tree -r --name-only dd422fb
git shortlog -sn d4302f4
```

## 7. Evidencias S6 y S7

Esta sección aplica el mismo método a las dos revisiones publicadas después del primer corte.
**La de S7 ya se corrigió**: el 24 de septiembre se publicó una revisión definitiva sobre
`2269ca5`, con 10 de 10, que reemplazó a la preliminar sobre `a47d5bd`. **La de S6 sigue siendo
una pasada temprana**: su encabezado lo dice, y `estado-s6.json` del repositorio de
retroalimentación registra `"modo": "early"`. Si se publica una pasada definitiva de S6, esta
sección se revisa contra ella.

### 7.1 S7: lo que se corrigió y lo que queda

| Hecho | Evidencia verificable |
|---|---|
| La revisión preliminar miró un commit anterior al cierre, pero no el último | Evaluó `a47d5bd` (13 de septiembre). El último commit de `master` anterior al cierre (`2026-09-21T05:00:00Z`) es `2269ca5`, y entre los dos hay 19 commits de los cuatro integrantes |
| La revisión corregida lo reconoce | Su encabezado: «El informe preliminar había omitido 19 commits elegibles; esta versión evalúa el último commit de `origin/master` anterior al cierre». Estado revisado: `2269ca5`, 10 de 10 |
| Nada que solicitar sobre la matriz de la ficha | Las diez filas quedaron en `Cumple` |

Quedan dos filas de la matriz transversal. Una es cierta y está en 7.4 (SonarCloud). La otra se
solicita revisar:

| # | Dónde lo dice la revisión | Qué afirma | Qué hay | ¿Corregir? |
|---|---|---|---|---|
| **9** | S7, transversal, «Contribución de todos los integrantes» → `No verificado`; `feedback.md` S7: «confirmar de forma explícita la asociación de las cuentas» | «`git shortlog -sne 2269ca5` produce cuatro grupos de identidad, pero `EQUIPOS.md` solo confirma dos cuentas» | La tabla de `EQUIPOS.md` que cita es la de «Usuarios de GitHub vistos en el historial», que el propio archivo presenta como cuentas **sin asignar a persona** y como punto de partida para la planilla. La **planilla de este equipo**, en su tabla «Contribución por integrante», ya asocia las cuatro: Sebastián Cañas Plata, `scp1109`; Josué David Ortega De Arco, `josueacademico17-source`; Susana Marcela Rosales Castellar, `SusanaRosales`; María Del Mar Restrepo Licona, `Mariadelmar-restrepo`. El equipo confirma esa asociación, y la deja escrita también en la sección «Equipo» del README | **Sí.** Se solicita tomar la asociación de la planilla y actualizar la tabla de `EQUIPOS.md`, que registra las cuentas de la primera consulta |

### 7.2 Lo que el revisor automático alcanza a leer de este repositorio

Varias filas de S6 quedaron en `No verificado` con el mismo motivo: «no se incluyó el contenido».
No es que el contenido falte. `scripts/cron/evaluar-semana.py`, que es lo que ejecuta el workflow
`revision-semanal.yml`, arma la evidencia con cuatro cortes:

- cada archivo de `docs/` y el README llegan con **sus primeras 300 líneas y, de ellas, los
  primeros 9 000 caracteres** (líneas 186 a 188 del script);
- `correcciones.md`, con el mismo corte (líneas 189 a 191);
- **`CONTRATO.md` llega con sus primeros 8 000 caracteres** (línea 421), y su apartado 11, la
  matriz transversal, empieza en el carácter 9 344;
- **toda la evidencia se trunca en 95 000 caracteres** al armar el mensaje para el modelo, y los
  documentos van antes que los runs de CI.

Los valores son los mismos en las versiones del script que corrieron las pasadas de S6
(`93594f6`) y de S7 (`e5609fc`). Reproducida esa lógica sobre `a47d5bd`, la evidencia mide
167 822 caracteres y se corta en 95 000. Contrastado con lo que las revisiones publicaron, lo que
el revisor cita está siempre dentro de lo que llega, y lo que declara no haber visto está siempre
fuera:

| Lo que dice la revisión | Dónde está | ¿Llega al revisor automático? |
|---|---|---|
| S6, «Tabla módulo → dato con seis entidades» (`Cumple`) | `08-propiedad-de-datos.md` en `a47d5bd`, carácter 1 330 | Sí |
| S6, «No se incluyó la sección de violaciones» (`No verificado`), **del mismo archivo** | carácter 9 205: el corte de 9 000 cae 205 caracteres antes | No |
| S6, «No se incluyó la sección 8 del arc42» | carácter 43 476 del arc42 en `a47d5bd` | No |
| S6, «no se incluyó el contenido» de `docs/aspectos.md` y `docs/ia.md` | los dos archivos quedan enteros después del corte de 95 000 | No |
| S6, «no se aportaron runs_ci» | `runs_ci` es el último campo de la evidencia | No |

Dos hechos posteriores lo confirman desde el lado del revisor.

- **Sobre el mismo commit, dos lectores distintos.** La revisión corregida de S7 y la pasada
  temprana de S8 miraron el mismo `2269ca5`. La primera, una «revisión académica local sobre
  evidencia Git», cita el contenido con número de línea: `docs/ia.md:126-138`, arc42 `356-440` y el
  run `35555368047` en verde. La segunda es la pasada automática, y dice de ese mismo commit que
  `docs/ia.md` «no se aporta el
  contenido», que la sección 2 del arc42 no está en la evidencia (empieza en el carácter 11 432,
  y del arc42 le llegan 8 272) y que «no hay runs_ci».
- **El propio revisor automático lo anota.** La pasada temprana de S8 termina con este hallazgo:
  «El contrato recibido no incluye el apartado 11; la matriz transversal se armó con los
  apartados 1 a 8». Es el corte de 8 000 caracteres sobre `CONTRATO.md`.

No se pide nada sobre S8, que todavía no cierra: se cita solo como evidencia del método.

**¿Corregir?** Sí: se solicita revisar el método. Un límite de 9 000 caracteres por archivo y de
95 000 en total deja fuera, en este repositorio, `aspectos.md`, el C4, `ia.md`, el contrato
OpenAPI, toda la carpeta `docs/evidencia/`, este mismo documento y los runs de CI; y el corte
sobre `CONTRATO.md` deja al revisor sin la matriz transversal que debe llenar. El comando para
repetir la reconstrucción está en 7.5.

### 7.3 Filas de S6 en `No verificado` cuyo contenido está en `a47d5bd`

| # | Fila y estado publicado | Qué afirma | Qué hay en `a47d5bd` | ¿Corregir? |
|---|---|---|---|---|
| **10** | «No conformidades de propiedad de datos detectadas»: `No verificado` | «No se incluyó la sección de violaciones» | `docs/arc42/08-propiedad-de-datos.md` línea 135, «Violaciones de propiedad de datos», con la tabla de V-1 a V-5 en las líneas 140 a 146: violación, dónde está, acción correctiva y de qué depende | **Sí** |
| **11** | «Plan de corrección por no conformidad»: `No verificado` | «No se incluyó la sección con planes de corrección» | La misma tabla, columnas «Acción correctiva» y «Depende de», y un apartado por violación a continuación | **Sí** |
| **12** | «arc42 sección 8 con lenguaje ubicuo y mapa de contextos»: `No verificado` | «No se incluyó la sección 8 del arc42» | `docs/arc42/arc42-template-ES.md`: sección 8 en la línea 421, mapa de contextos (8.1) en la 443 y lenguaje ubicuo (8.2) en la 604 | **Sí** |
| **13** | «Aspectos relacionables con los contextos del mapa»: `No verificado` | «No se incluyó el contenido de docs/aspectos.md» | `docs/aspectos.md` línea 42, que asigna a cada aspecto su contexto del mapa, y `08-propiedad-de-datos.md` línea 274, «Aspectos ↔ contextos», en las dos direcciones | **Sí** |
| **14** | «C4 nivel 3 y ADR si los límites cambiaron»: `No verificado` | «No se aportó [...] el contenido de docs/c4» | `docs/c4/doc-c4.md` línea 325, «Nivel 3 · Diagrama de Componentes», y ADR-0007 | **Sí, con la salvedad de 7.4** |
| **15** | Transversal, «La tabla de aspectos» y «Registro de uso de IA»: `No verificado` | «no se incluyó su contenido» | `docs/aspectos.md`, filas de A-01 a A-05 en las líneas 33 a 37; `docs/ia.md`, ocho entradas, con «Qué se rechazó» en las líneas 23, 34, 45, 56, 67, 78, 89 y 105 | **Sí** |
| **16** | Transversal, «Pipeline y análisis estático»: `No verificado` | «no se aportaron runs_ci, URL pública de SonarCloud ni línea del scanner» | El run `34805781748` corre sobre `a47d5bd` con conclusión *success*. Lo del scanner es cierto (ver 7.4) | **En parte**: los runs sí |

El equipo no solicita una nota: solicita que estas filas se evalúen sobre lo que contenía
`a47d5bd`.

### 7.4 Lo que las revisiones de S6 y S7 señalan y es cierto

| Revisión | Observación | Comprobación |
|---|---|---|
| S6 y S7 | No hay línea del workflow que invoque el analizador de SonarCloud ni archivo de configuración del análisis | Correcto en `a47d5bd` y en `2269ca5`: `.github/workflows/ci.yml` no menciona SonarCloud y no existe `sonar-project.properties`. El análisis corre desde SonarCloud y su *Quality Gate* es público, pero `CONTRATO.md` §8 pide las tres evidencias juntas |
| S6 | El Nivel 3 del C4 no se pudo verificar | La salvedad es del equipo: en `a47d5bd`, las líneas 336 a 342 de `doc-c4.md` decían que el repositorio «todavía no tiene código» y que el reparto salía de un resumen de la actividad y no del código. Era falso desde el 30 de agosto. El Nivel 3 se reescribió después contra el código real |

### 7.5 Cómo repetir las comprobaciones de esta sección

```bash
# 7.1 - el commit que correspondía a S7
git log -1 --format='%H %cI %s' --until=2026-09-21T05:00:00Z origin/master
git log --format='%h %cI %an' a47d5bd..2269ca5

# 7.2 - los cortes del revisor (en un clon de ISCOUTB/AS_202620_feedback)
grep -nE 'max_lines=300|\[:9000\]|\[:95000\]|contrato\[:8000\]' scripts/cron/evaluar-semana.py
python -c "t=open('CONTRATO.md',encoding='utf-8').read(); print(t.find('## 11.'))"

# 7.2 - dónde cae el corte (en este repositorio)
git show a47d5bd:docs/arc42/08-propiedad-de-datos.md | python -c "import sys; t=sys.stdin.buffer.read().decode('utf-8'); print(t.find('## Violaciones'))"
git show 2269ca5:docs/arc42/arc42-template-ES.md | python -c "import sys; t=sys.stdin.buffer.read().decode('utf-8'); print(t.find('# 2. Architecture Constraints'))"

# 7.3 - las secciones en el commit revisado
git show a47d5bd:docs/arc42/08-propiedad-de-datos.md | sed -n '135,146p'
git show a47d5bd:docs/arc42/arc42-template-ES.md | grep -nE '^# 8\.|^## 8\.[12]'
git show a47d5bd:docs/c4/doc-c4.md | grep -n '^## Nivel 3'
git show a47d5bd:docs/ia.md | grep -n 'Qué se rechazó'
```

---

*Documento elaborado por el equipo a solicitud del docente. Primera versión: 2026-09-06, sobre un
estado posterior a `cede35e`. El 2026-09-26 se agregó la sección 7, sobre S6 y S7, y se corrigió la nota A, que daba por corregida una frase
del C4 que no lo estaba, y un conteo de la sección 4.*
