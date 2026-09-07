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
sección 6.

**Este documento no corrige nada.** Reporta el hallazgo y dice si corresponde corregir, dónde y
por qué. Las correcciones que ya se hicieron por otras razones se indican como tales.

| Revisión | Commit que declara haber mirado | Fecha del commit | Cierre de la actividad |
|---|---|---|---|
| Evidencia S1 | `4f6f5687` | 2026-08-09T13:16:43-05:00 | 2026-08-10T05:00:00Z |
| Evidencia S2 | `d4302f4b` | 2026-08-16T23:17:26-05:00 | 2026-08-17T05:00:00Z |
| Evidencia S3 | `dd422fb2` | 2026-08-23T23:52:23-05:00 | 2026-08-24T05:00:00Z |
| Evidencia S4 | `cede35e4` | 2026-08-30T23:51:34-05:00 | 2026-08-31T05:00:00Z |
| Primer corte | `cede35e4` (sin etiqueta) | 2026-08-30T23:51:34-05:00 | 2026-09-07T05:00:00Z |

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
conclusión, no la lectura: el diagrama estaba ahí y era comprobable en el mismo archivo. Las dos
frases ya fueron corregidas.

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
| S3 | No hay arranque, ni prueba, ni estructura de paquetes al cierre | `git ls-tree -r dd422fb` contiene únicamente `README.md` y nueve archivos bajo `docs/`. No hay código |
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

---

*Documento elaborado por el equipo a solicitud del docente. Fecha: 2026-09-06. Estado del
repositorio en el momento de escribirlo: posterior a `cede35e`, con las correcciones de las notas
A y B ya aplicadas.*
