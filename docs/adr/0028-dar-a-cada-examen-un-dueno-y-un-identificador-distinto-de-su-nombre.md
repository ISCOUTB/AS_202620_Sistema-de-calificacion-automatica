# 0028 · Dar a cada examen un dueño y un identificador distinto de su nombre

- **Estado:** aceptado
- **Fecha:** 2026-11-23
- **Decide:** Sebastián Cañas Plata, Susana Rosales Castellar
- **Riesgos:** reduce AM-02 y la parte de EC-06 que ADR-0025 dejó abierta (cualquier docente con cuenta veía y cambiaba lo de los demás); el aislamiento por curso sigue pendiente
- **Relación con otros ADR:** completa [ADR-0025](0025-identificar-al-docente-con-una-sesion-firmada-y-una-lista-de-cuentas.md) (la sesión dice quién es el docente; ahora también decide qué ve) y [ADR-0026](0026-registrar-y-habilitar-la-clave-desde-la-aplicacion.md) (la clave se registra en un examen creado antes). Usa el medio de [ADR-0027](0027-guardar-los-registros-en-postgres-detras-de-los-mismos-puertos.md) para el registro nuevo. El panel deja los datos de ejemplo con los que nació.

**La decisión, en una frase:** cada examen se crea con un nombre que pone el docente y recibe un
identificador que acuña el sistema (`000001`); queda a nombre del docente de la sesión, y toda ruta
de un examen responde 404 a cualquier otro docente.

---

## Contexto

Con la base de datos ya en el servidor apareció el problema: al entrar con la cuenta de un profesor
se veían los exámenes, las claves y los resultados que había cargado otro. No era un fallo de la
base: ningún dato tenía dueño. Las rutas pedían sesión (`dependencies=[Depends(docente_de_la_sesion)]`)
pero no recibían el correo, y las tablas solo guardaban `examen_id`. El código lo decía: «sin cursos
todavía cualquier docente con cuenta ve todas las hojas (EC-06)».

Había un segundo problema escondido: el `examen_id` era el texto que escribía el docente. Dos
docentes que escribieran `parcial-1` compartían clave, hojas y resultados.

Y el panel del curso mostraba siempre los mismos datos de ejemplo, porque nunca se conectó a la API.

## Alternativas consideradas

| Alternativa | A favor | En contra | Resultado |
|---|---|---|---|
| **Agregar una columna `docente` a las tres tablas** | Consulta directa | Hay que migrar filas con datos, tocar al worker y a la cola, y el nombre seguiría chocando entre docentes | Descartada |
| **Prefijar el identificador con el correo** (`ana@…/parcial-1`) | Nada nuevo que guardar | El correo viaja en las rutas, en la cola y en las carpetas del almacén; cambiar de correo rompe todo | Descartada |
| **Un registro de exámenes aparte, con dueño, nombre e identificador propio** | El worker, la cola y las tablas existentes no cambian: el dueño se deduce del examen; el nombre deja de chocar | Una tabla más | **Elegida** |

## Decisión

1. **El registro de exámenes** (`infraestructura/examenes.py`): `ExamenesEnDisco` sin base de datos
   y `ExamenesEnPostgres` (tabla `examenes`) con ella. Guarda `examen_id`, `nombre`, la clave
   normalizada del nombre, `docente` y `creado_en`. Un docente no repite nombre (sin distinguir
   mayúsculas ni espacios de más); dos docentes sí.
2. **El identificador lo acuña el sistema**: seis dígitos con ceros a la izquierda, el siguiente al
   mayor. En Postgres, con una secuencia.
3. **`POST /examenes {nombre}`** crea el examen (201) o devuelve el que el docente ya tenía con ese
   nombre (200). La pantalla de la clave lo llama al guardar, y si la respuesta es 200 muestra la
   clave existente en vez de pisarla.
4. **`examen_de_la_sesion`**, una dependencia en todas las rutas de un examen: si no existe o es de
   otro docente, 404 con el mismo mensaje en los dos casos, para no revelar qué exámenes existen.
   `GET /examenes` lista solo los del docente.
5. **Los exámenes anteriores** no tenían dueño. La primera vez que cada proceso de la API usa el
   registro, adopta los identificadores que aparecen en las claves o en la bitácora y no tienen
   dueño: van a nombre de quien habilitó su clave (ADR-0026 lo guardó con el correo de la sesión)
   si sigue en `DOCENTES`, y si no, a `DOCENTE_DE_LOS_EXAMENES_ANTERIORES` o al primer docente de
   la lista. Su nombre es su identificador viejo.
6. **`GET /examenes/{examen_id}/panel`** (`dashboard/panel.py`): promedio, desviación, aprobación,
   hojas, preguntas por revisar, cómo se marcaron las respuestas, las notas y los aciertos por
   pregunta. El panel del frontend deja los datos de ejemplo y muestra esto, con la campana de
   Gauss de las notas.
7. **El contrato sube a 3.0.0**: registrar la clave de un examen que no se creó antes responde 404.

## Consecuencias

- Un docente solo ve, sube, califica y revisa lo suyo. Lo prueban `test_aislamiento_entre_docentes.py`
  (cada ruta con el dueño y con otro docente) y `test_examenes_del_docente.py` (las reglas, contra
  los tres adaptadores).
- Las pruebas escritas antes de este ADR usan un registro donde todo examen es del docente de prueba
  (`tests/sesion_de_prueba.py`): siguen probando lo suyo con `PARCIAL-1` y compañía.
- El panel ya no tiene datos de asignatura, grupo ni competencias: el sistema no los guarda. Si se
  quieren, hace falta registrar cursos (A-04, EC-06), que sigue pendiente.
- Un examen adoptado sin rastro de quién habilitó su clave puede quedar a nombre del docente
  equivocado. Se corrige cambiando su fila en la tabla `examenes`.

## Cómo se comprobó

- **Pruebas:** `test_aislamiento_entre_docentes.py` (21), `test_examenes_del_docente.py` (36, también
  contra Postgres 16) y `test_panel.py` (7). Sin la comprobación del dueño en `examen_del_docente`
  fallan 10 de las 21 de aislamiento. La suite completa del servidor: 658 pasan y 2 se saltan; la
  del sitio, 226.
- **De punta a punta, con el compose del servidor:** con el código anterior, dos docentes cargaron
  hojas y uno leía los resultados del otro. Con este cambio, sobre la misma base, cada examen pasó a
  quien había habilitado su clave, el otro docente recibió 404 en todas las rutas del examen y las
  cifras del panel coincidieron con los resultados: 39 de 39 comprobaciones
  ([evidencia](../evidencia/examenes-por-docente.md)).

## Reversión

- Revertir el cambio: la API vuelve a responder por `examen_id` sin mirar el dueño, y la tabla
  `examenes` queda sin uso. Los exámenes creados mientras tanto conservan su identificador numérico,
  que es el que llevan su clave, sus hojas y sus resultados: no se pierde nada, solo deja de verse
  su nombre.

## Trazabilidad

- **Código:** `backend/infraestructura/examenes.py`, `backend/infraestructura/base_de_datos.py`
  (`ExamenesEnPostgres`), `backend/autoria/examenes.py`, `backend/dashboard/panel.py` y
  `backend/api/main.py` (`examen_de_la_sesion`, `obtener_registro_de_examenes`, `POST /examenes` y
  `GET /examenes/{examen_id}/panel`); en el sitio, `tarjeta_clave.dart`, `servicio_examenes.dart` y
  `frontend/lib/features/panel/`.
- **Pruebas:** las tres de arriba y `test_contrato.py`; en el sitio, `panel_test.dart`,
  `servicio_panel_test.dart` y `clave_por_nombre_test.dart`.
- **Evidencia:** [`docs/evidencia/examenes-por-docente.md`](../evidencia/examenes-por-docente.md).
- **Configuración:** `DOCENTE_DE_LOS_EXAMENES_ANTERIORES` en `deploy/compose.lab.yaml` y
  `deploy/.env.example`.
