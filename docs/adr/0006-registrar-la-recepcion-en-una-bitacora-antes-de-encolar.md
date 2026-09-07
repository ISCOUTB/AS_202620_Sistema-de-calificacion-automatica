# 0006 — Registrar la recepción en una bitácora antes de encolar

- **Estado:** aceptado
- **Fecha:** 2026-09-06
- **Decide:** Josué Ortega De Arco, María Restrepo Licona, Sebastián Cañas Plata, Susana Rosales Castellar
- **Escenario de calidad relacionado:** [EC-07](../arc42/arc42-template-ES.md#ec-07) (confirmación fiable de recepción del lote)
- **Restricción que acota:** R-06 (deuda: no hay decisión de persistencia ni de almacenamiento de imágenes)
- **Precisa, sin reemplazar:** [ADR-0002](0002-procesar-calificacion-de-forma-asincrona.md)

---

## Contexto

El aspecto A-01 quedó construido de punta a punta en la semana 4, y su código dejó anotado un hueco que nadie había medido:

> Queda un hueco conocido, y es necesario nombrarlo: entre el guardado y el encolado no hay transacción. Si el proceso muere justo en medio, el archivo queda huérfano en el almacén.
>
> — `ingesta/recepcion.py`, en el estado `cede35e`

Este ADR existe porque ese hueco dejó de ser una nota al margen y pasó a ser un número.

### El diagnóstico, con la línea base medida

Se construyó una herramienta reproducible, [`backend/herramientas/medir_ec07.py`](../../backend/herramientas/medir_ec07.py), y se ejerció el endpoint real `POST /examenes/{id}/hojas` con la carga que EC-07 declara: un lote de 200 hojas escaneadas. La medición se corrió sobre el commit `cede35e`, que es el estado anterior a esta decisión. El procedimiento completo y sus limitaciones están en [`docs/evidencia/medicion-ec07.md`](../evidencia/medicion-ec07.md).

| Medida de EC-07 | Umbral del escenario | Estado inicial (`cede35e`) | ¿Cumple? |
|---|---|---|---|
| Confirmación de recepción del lote | ≤ 10 s | **0,126 s** (peor de 3) | Sí, con dos órdenes de magnitud de margen |
| Pérdida silenciosa | 0 % | **100 %** | **No** |

La primera cifra dice que la latencia no es el problema de este escenario y que hay presupuesto de sobra para gastar. La segunda dice dónde está el problema de verdad.

**Qué significa ese 100 %.** Con la cola cayéndose en la hoja 101 de un lote de 200, el sistema respondía **500** y el docente no recibía reporte de **ninguna** de las 200 hojas, mientras 100 trabajos ya estaban encolados y 101 archivos escritos en el almacén. Las consecuencias son tres y todas malas:

1. El docente no sabe qué entró, así que su única salida razonable es volver a subir el lote completo.
2. Al hacerlo, las 100 hojas ya encoladas se procesan **dos veces**.
3. Las hojas almacenadas y no encoladas quedan invisibles: nadie las va a procesar y nadie sabe que están ahí.

EC-07 promete exactamente lo contrario: «todo archivo cargado queda registrado como *aceptado* o *rechazado con motivo*». La promesa no se rompía por descuido de una línea, sino porque el módulo no tenía **dónde** anotar que una hoja ya estaba adentro.

### Dónde se localiza el impacto

- **Requisitos:** RF-01 (carga de exámenes escaneados). El escenario que lo mide es EC-07.
- **C4:** la relación 3 del Nivel 2 (Aplicación web → Almacén de imágenes) y la 4 (Aplicación web → Cola de trabajos). El defecto vive **entre** las dos, que es justamente el lugar que un diagrama de contenedores no puede mostrar: dos flechas dibujadas una al lado de la otra no dicen que no hay nada que las una.
- **Código:** `backend/ingesta/recepcion.py`, el bucle de `recibir_lote`; `backend/infraestructura/cola.py`, que no distinguía acuñar un trabajo de publicarlo.
- **Aspecto:** [A-01](../aspectos.md#a-01), fila «Evidencia».

### Restricciones que enmarcan la decisión

- **R-06 sigue abierto y esta decisión no lo cierra.** No se elige medio de persistencia definitivo ni política de retención (RNF-14). Se cubre el hueco de recepción, que es la parte de R-06 que impedía medir EC-07.
- **RNF-12 y RNF-13:** la bitácora guarda identificadores de trabajo, referencias del almacén y nombres de archivo. Ningún dato personal del estudiante, y nada de esto sale del sistema.
- **Los ADR aceptados no se editan.** Esta decisión no modifica ADR-0002: lo precisa. ADR-0002 estableció el procesamiento asíncrono y la cola; no dijo qué pasa cuando la cola no está, y esa omisión es lo que se resuelve aquí. Por eso conviven en vez de reemplazarse.
- **El aislamiento hexagonal es selectivo** (arc42 §4.1): se aplica en dos puntos, no en los siete módulos. El almacenamiento es uno de ellos, y la bitácora es parte del mismo punto.

---

## Alternativas consideradas

### A. Dejar el hueco documentado y no tocar el código

Se conserva la anotación en el docstring y se declara EC-07 como no medible hasta que exista el ADR de persistencia definitiva.

**A favor:**

- No cuesta nada y no introduce ningún mecanismo nuevo que después haya que mantener o desmontar.
- Es defendible mientras el sistema no esté en manos de nadie: hoy no hay usuarios reales que puedan perder un lote.

**En contra:**

- La cifra ya está medida y es 100 %. Un defecto medido que se deja abierto deja de ser deuda declarada y pasa a ser un defecto conocido sin plan.
- Bloquea la construcción de A-02: el aspecto siguiente consume la cola, y no puede razonar sobre qué hacer con un trabajo que se perdió si no hay dónde consultarlo.

**Por qué no se eligió:** el costo de la alternativa elegida resultó ser una clase (`bitacora.py`) y un `try/except`. No hay proporción entre ese costo y el de dejar el escenario incumplido.

### B. Cola con acuse de recibo y persistencia (Redis Streams con `XACK`, o AOF con `appendfsync always`)

Se cambia la lista FIFO por un flujo con grupos de consumidores y confirmación explícita, o se configura Redis para descargar cada escritura a disco.

**A favor:**

- Resuelve además un problema que la bitácora no toca: el trabajo que se pierde **después** de encolarse, cuando el worker lo saca y muere antes de terminarlo. Es la garantía que A-02 va a necesitar.
- Es el camino estándar y no habría que inventar nada.

**En contra:**

- **No resuelve el defecto medido.** Los dos fallos de la línea base ocurren cuando la cola **no responde**: ninguna garantía que dependa de que la cola esté disponible puede cubrirlos. Con Streams y `XACK`, la caída en la hoja 101 sigue devolviendo 500 y sigue perdiendo el reporte de las 200.
- Ata la solución a Redis justo cuando R-06 está abierto, que es lo que el puerto `AlmacenDeImagenes` se cuidó de no hacer.
- `appendfsync always` degrada el rendimiento de la cola para todo el sistema, no solo para la recepción.

**Por qué no se eligió:** ataca el problema equivocado. Es la respuesta correcta a una pregunta distinta —la durabilidad del trabajo ya encolado— y queda anotada como trabajo de A-02, no descartada.

### C. Registrar la recepción en PostgreSQL

La base de datos ya está declarada en el `docker-compose.yml` y en el Nivel 2 del C4. Se crea una tabla `recepcion` y se escribe ahí antes de encolar, con el patrón *outbox*.

**A favor:**

- Es el destino natural a largo plazo: cuando exista el esquema, la recepción va a vivir ahí de todos modos.
- Da consultas, índices y concurrencia entre procesos sin escribir una línea. La bitácora en archivo no da ninguna de las tres.
- Permite una transacción real entre el registro de la recepción y cualquier otro dato estructurado del examen.

**En contra:**

- **Postgres hoy no tiene esquema ni migraciones**, y ningún módulo lo usa (arc42 §5.1). Crear la primera tabla del sistema para tapar este hueco fija el modelo de datos, la herramienta de migraciones y el estilo de acceso **sin ADR**, que es exactamente lo que R-06 pide no hacer por omisión.
- Convierte la recepción en dependiente de que la base de datos esté arriba. Se cambiaría una dependencia frágil (la cola) por otra.

**Por qué no se eligió:** es la alternativa correcta *después* del ADR de persistencia, no *en lugar* de él. Elegirla ahora tomaría por la puerta de atrás la decisión que ese ADR tiene que tomar de frente.

### D. Bitácora de recepción de solo agregado, detrás de un puerto (ELEGIDA)

Un registro propio del módulo `infraestructura`, escrito **antes** de publicar en la cola y confirmado **después**. Puerto `BitacoraDeRecepcion` y adaptador `BitacoraEnDisco`, que agrega una línea JSON por hecho y la descarga a disco con `fsync`. Ninguna línea se reescribe: confirmar una entrada es agregar otra que la referencia.

**A favor:**

- **Cubre el defecto medido**, que es lo que ninguna de las otras hace: el registro no depende de que la cola responda, así que la hoja queda anotada incluso cuando el encolado falla.
- Es del mismo tamaño que el problema. Una clase, un `try/except` y un campo nuevo en el modelo.
- **Deja R-06 abierto de verdad.** El puerto es el mismo mecanismo con el que A-01 evitó cerrar la decisión de almacenamiento: cuando el ADR de persistencia elija medio, se escribe otro adaptador y ni `ingesta` ni el modelo se enteran.
- Solo agregado es la forma correcta para lo que tiene que sobrevivir a una caída: una escritura que sobrescribe puede dejar el archivo a medias justo en el momento del que hay que sobrevivir. Una línea truncada solo puede ser la última, y se descarta al releer.
- El `fsync` hace la promesa comprobable en vez de declarada.

**En contra:**

- **Cuesta latencia, y se midió cuánto:** de 0,126 s a 1,744 s en el peor de tres corridas sobre el mismo lote de 200 hojas, catorce veces más lento. Son 400 `fsync`, dos por hoja.
- Es de un solo proceso. Dos instancias de la API escribiendo el mismo archivo no está soportado, y el sistema todavía corre con una.
- **El reintento no está automatizado.** `pendientes()` deja el dato listo; consumirlo es trabajo de A-02.
- Agrega un mecanismo que el ADR de persistencia definitiva probablemente reemplace. Es deuda deliberada, con fecha de revisión.

**Por qué se eligió:** es la única alternativa que cubre el defecto medido sin tomar por omisión la decisión que R-06 tiene pendiente, y su costo cabe con holgura en el presupuesto que la primera medición dejó libre.

---

## Decisión

**1. Se introduce una bitácora de recepción en `infraestructura`,** con el puerto `BitacoraDeRecepcion` y el adaptador `BitacoraEnDisco`, de solo agregado y con `fsync` por línea. `BitacoraEnMemoria` acompaña para las pruebas que no miden durabilidad.

**2. `recibir_lote` registra antes de publicar.** El orden por hoja pasa a ser: almacenar, acuñar el trabajo, registrar en la bitácora, publicar en la cola, confirmar en la bitácora. Ningún paso se puede adelantar sin reabrir el hueco.

**3. Un fallo de la cola deja de abortar el lote.** La hoja se reporta como **aceptada** con estado `pendiente_de_encolar`. No se reporta como rechazada, porque no lo fue: está almacenada y registrada, y pedirle al docente que la vuelva a subir es lo que produce las duplicaciones.

**3b. El lote deja de insistir después del primer fallo.** Marcada la cola como no disponible, las hojas restantes se almacenan, se registran y se reportan como pendientes **sin volver a intentar publicarlas**. Esto no es una optimización, es lo que mantiene alcanzable el techo de 10 segundos de EC-07: un cliente de Redis que no encuentra servidor no falla al instante, agota el tiempo de conexión primero. Se midieron **7,1 s para una sola hoja** contra un contenedor de Redis detenido, comparados con 20 ms cuando la cola responde. Reintentar hoja por hoja llevaría un lote de 200 a más de veinte minutos para terminar exactamente en el mismo estado: las mismas 200 hojas almacenadas, registradas y pendientes. El primer fallo ya contestó la pregunta.

**4. El identificador del trabajo se acuña antes de tocar la cola.** `infraestructura.cola` separa `preparar_trabajo` de `publicar` para que la entrada de bitácora y el trabajo que llegue después se refieran al mismo identificador. `encolar` se conserva como composición de las dos.

**5. Los fallos de la cola se traducen en `ColaNoDisponible`.** `ingesta` declara en su docstring que no conoce Redis, y esa frase tiene que seguir siendo cierta: `publicar` es el único punto donde una excepción de redis-py se convierte en una del dominio.

**6. La respuesta del endpoint gana el campo `estado` por hoja aceptada.** Es aditivo: el cliente Flutter no cambia, porque `trabajo_id` sigue existiendo y sigue siendo una cadena en los dos estados.

**7. `worker/main.py` lee `NOMBRE_COLA` del entorno.** Lo tenía como literal mientras la API ya lo leía de la variable, de modo que cambiarla dejaba a la API encolando en una lista y al worker escuchando otra: el mismo modo de fallo que esta decisión ataca, entrando por la otra puerta.

**8. R-06 sigue abierto.** Esta decisión no elige medio de persistencia definitivo ni política de retención. Su alcance es la recepción.

---

## Consecuencias

### Positivas

- **EC-07 pasa a estar medido y cumplido en sus dos cifras:** 0 % de pérdida silenciosa y 1,744 s contra un umbral de 10 s. Deja de ser un objetivo declarado.
- El aspecto A-01 completa su cadena de trazabilidad hasta la columna de evidencia con un resultado contrastado contra el umbral, no con una captura de pantalla.
- La medición es repetible con un comando y compara contra el estado anterior con la misma herramienta, porque `medir_ec07.py` corre igual en un repositorio que no tenga bitácora.
- A-02 hereda un dato que antes no existía: qué hojas están almacenadas sin procesar.
- El defecto del `NOMBRE_COLA` desaparece.

### Negativas y costos asumidos

- **La confirmación es catorce veces más lenta.** Se acepta explícitamente: gasta 1,744 s de un presupuesto de 10 y deja 83 % de margen. Si el margen bajara del 50 %, la decisión se revisa (ver abajo).
- **En el camino de fallo el margen es mucho más estrecho, y es lo más frágil de esta decisión.** Con la cola caída desde el principio, el lote de 200 hojas confirma en **7,842 s con un solo intento** contra la cola, dentro del umbral pero con apenas 22 % de margen. Ese margen no lo controla el equipo: lo fija el tiempo que tarda el cliente de Redis en rendirse. Si esa demora subiera por encima de unos 9 s, el escenario se incumpliría en el camino de fallo aunque el código no cambie. La mitigación evidente, fijar un `socket_connect_timeout` corto en `cliente_redis`, **no se tomó en esta decisión**: es una elección de configuración que merece su propio análisis y no cabía en el alcance del reto.
- **Parte del margen anterior era prestado.** Los 0,126 s de la línea base incluían escrituras que el sistema operativo aún no había llevado al disco: el sistema confirmaba rápido porque no estaba prometiendo nada. Comparar 0,126 con 1,744 compara una promesa débil con una fuerte, y conviene decirlo así.
- **La bitácora es de un solo proceso.** El día que la API corra en dos instancias sobre el mismo volumen, este adaptador deja de servir. Está escrito en su docstring.
- **El reintento sigue siendo manual.** Hoy `pendientes()` se consulta; nadie la drena sola. Una hoja pendiente que nadie reintente sigue sin calificarse, aunque ahora al menos se sabe cuál es.
- **Ningún automatismo vigila el punto 7.** Que el worker lea la variable correcta no lo comprueba ninguna prueba; se verificó a mano devolviendo el literal y confirmando que las 44 pruebas siguen pasando. Es un hueco declarado, no cerrado.

### Riesgos y qué los dispararía

| Riesgo | Disparador | Mitigación |
|---|---|---|
| La bitácora crece sin límite y nadie la rota. | Un semestre de uso sin política de retención (RNF-14, abierta en R-06). | El ADR de persistencia definitiva tiene que cubrir el ciclo de vida de la bitácora junto al de las imágenes, no solo el guardado. |
| El equipo lee «0 % de pérdida silenciosa» como «el sistema no pierde hojas». | Citar la cifra sin su procedimiento en la sustentación o en el informe. | Lo que se midió es que ninguna hoja queda **sin reportar** ante un fallo de la cola. La durabilidad ante la caída del sistema operativo no se midió y no se puede medir sin cortarle la corriente a la máquina. |
| Se toma la bitácora por la solución de persistencia y R-06 se da por cerrado. | Que el ADR de persistencia no se escriba porque «ya hay algo que guarda». | El adaptador se llama y se documenta como lo que es. El punto 8 de la decisión lo dice, y R-06 sigue listado como abierto en arc42 §11. |
| Dos instancias de la API corrompen el archivo. | Escalar horizontalmente antes de reemplazar el adaptador. | El puerto ya existe: el reemplazo es una clase, no una migración. |

### Qué dato haría revisar esta decisión

- **Que la latencia de confirmación supere 5 s** (la mitad del presupuesto de EC-07) al medir con Redis real y almacenamiento definitivo. Entonces el `fsync` por línea deja de caber y hay que agrupar las escrituras por lote.
- **Que el tiempo de espera de conexión del cliente de Redis suba por encima de 9 s**, por configuración o por un entorno de red distinto. Eso solo deja 1 s para las 200 escrituras y rompe EC-07 en el camino de fallo. Es el dato que obligaría a fijar un `socket_connect_timeout` explícito.
- **Que el sistema necesite más de una instancia de la API.** El adaptador en archivo deja de ser correcto ese mismo día.
- **Que el ADR de persistencia elija un medio transaccional** que abarque el almacén y el registro. Entonces la bitácora sobra y su reemplazo se escribe como ADR nuevo.

**Costo de reversión: bajo, y por diseño.** Todo lo que esta decisión agrega está detrás de un puerto o dentro de un `try/except`. Volver atrás es un adaptador distinto; no toca `ingesta`, ni el modelo, ni el frontend.

---

## Trazabilidad

- **Restricción que acota:** R-06 (arc42 §11). Sigue abierta; se cubre solo la parte que impedía medir EC-07.
- **Requisito afectado:** RF-01 (arc42 §1.1). No cambia su enunciado.
- **Escenario afectado:** [EC-07](../arc42/arc42-template-ES.md#ec-07). Su medida no cambia; pasa de objetivo a resultado medido.
- **Aspecto afectado:** [A-01](../aspectos.md#a-01), columnas Código, Pruebas y Evidencia.
- **Elementos C4 afectados:** Nivel 2, relaciones 3 y 4. El almacén de imágenes pasa a conservar también la bitácora de recepción; no aparece un contenedor nuevo, porque no lo es.
- **ADR relacionados, no modificados:** [0002](0002-procesar-calificacion-de-forma-asincrona.md) — establece la cola y el procesamiento asíncrono; esta decisión precisa qué ocurre cuando la cola no responde, y por eso conviven en lugar de reemplazarse.
- **Implementación:** `backend/infraestructura/bitacora.py` (nuevo), `backend/infraestructura/modelo.py`, `backend/infraestructura/cola.py`, `backend/ingesta/recepcion.py`, `backend/api/main.py`, `backend/api/settings.py`, `backend/worker/main.py`.
- **Pruebas que lo cubren:** [`backend/tests/test_durabilidad_recepcion.py`](../../backend/tests/test_durabilidad_recepcion.py), 13 pruebas. Se validaron provocando la falla con seis mutaciones; la tabla está en el documento de evidencia.
- **Evidencia:** [`docs/evidencia/medicion-ec07.md`](../evidencia/medicion-ec07.md), con los dos informes en crudo (`medicion-ec07-antes.json`, `medicion-ec07-despues.json`) y el procedimiento para repetirlos.
