# 08 · Propiedad de datos

Este documento fija el primer **concepto transversal** de la sección 8 del
[arc42](arc42-template-ES.md#8-cross-cutting-concepts) que deja de ser una intención: la
**propiedad de datos**. Existe porque el sistema es un monolito modular
([ADR-0001](../adr/0001-usar-monolito-modular.md) ·
[ADR-0002](../adr/0002-procesar-calificacion-de-forma-asincrona.md)) con siete módulos que se
prueban por frontera (`test_fronteras.py`), y una frontera de *imports* sin una frontera
equivalente de *datos* solo previene un tipo de acoplamiento y deja pasar el otro: dos módulos
que no se importan entre sí pueden seguir escribiendo la misma entidad sin que ninguna prueba
actual lo detecte.

**La regla.** Cada entidad de datos del dominio tiene **exactamente un módulo dueño**: el único
módulo autorizado a decidir el contenido de sus campos de negocio, es decir, a construir una
instancia con valores nuevos o a mutar los que ya tiene. Los demás módulos pueden importar el
tipo, pasarlo como parámetro, o —en el caso de un adaptador de persistencia— reconstituirlo
fielmente a partir de lo que el dueño ya escribió, pero no pueden decidir por su cuenta qué
significa un campo ni qué valor le corresponde. Esta es la regla contra la que se
contrastan las violaciones de propiedad de datos de este documento.

---

## Tabla módulo → dato

Una fila por entidad existente en el código, con su dueño, la ruta del archivo donde está
**declarada** y la línea exacta. La tabla no incluye datos que todavía no tienen clase propia:
eso se trata aparte, en [«Entidades previstas»](#entidades-previstas-sin-construir).

| Entidad | Módulo dueño | Ruta | Línea |
|---|---|---|---|
| `ArchivoCargado` | `ingesta` | [`backend/infraestructura/modelo.py`](../../backend/infraestructura/modelo.py) | 37 |
| `HojaAceptada` | `ingesta` | [`backend/infraestructura/modelo.py`](../../backend/infraestructura/modelo.py) | 48 |
| `ArchivoRechazado` | `ingesta` | [`backend/infraestructura/modelo.py`](../../backend/infraestructura/modelo.py) | 69 |
| `ResultadoRecepcion` | `ingesta` | [`backend/infraestructura/modelo.py`](../../backend/infraestructura/modelo.py) | 80 |
| `EntradaDeBitacora` | `ingesta` | [`backend/infraestructura/modelo.py`](../../backend/infraestructura/modelo.py) | 96 |
| `Trabajo` | `infraestructura` | [`backend/infraestructura/cola.py`](../../backend/infraestructura/cola.py) | 26 |

**Por qué el dueño de las cinco es `ingesta` y no `infraestructura`, si las cinco clases están
declaradas en `infraestructura/modelo.py`.** La ruta y la línea son de dónde vive la
*declaración*, no de quién decide el *contenido*. `modelo.py` dice de sí mismo por qué está en
`infraestructura` y no en otro módulo: es el único que los siete `__init__.py` declaran poder
importar todos, así que ubicar ahí el modelo compartido no exige mover ninguna frontera. Pero
propiedad no es lo mismo que ubicación: quien decide qué significa cada campo y en qué momento
cambia de valor es `ingesta.recepcion.recibir_lote`, que es donde se construyen las cinco
instancias con datos reales —el motivo de un rechazo, el estado `encolada` o
`pendiente_de_encolar`, el `trabajo_id`— y no `infraestructura`, que no conoce esas reglas de
negocio. `api/main.py` construye un `ArchivoCargado` en la línea 85, pero solo como el adaptador
HTTP que traduce el `multipart/form-data` de la petición al tipo que `ingesta` ya definió; no
decide ningún campo de negocio, se limita a copiar nombre y bytes.

**Por qué `Trabajo` es la única entidad cuyo dueño no es `ingesta`.** `Trabajo`
([`cola.py:26`](../../backend/infraestructura/cola.py)) no es una entidad de negocio sino el
**sobre de transporte** con el que un encargo viaja a la cola, y su dueño es `infraestructura`
porque es quien decide lo único que el sobre declara por su cuenta: el identificador, acuñado en
`preparar_trabajo` (`cola.py:38`). El `payload` lo arma `ingesta` en
[`recepcion.py:130`](../../backend/ingesta/recepcion.py), y a primera vista eso parece dos manos
sobre la misma entidad. No lo es: `infraestructura` nunca interpreta ese diccionario, lo serializa
entero al publicar (`cola.py:55`), así que no decide ninguno de sus campos ni se convierte en
segundo autor del dato que transporta. El identificador que acuña sí viaja después a
`EntradaDeBitacora` y a `HojaAceptada`, pero como el mismo valor propagado y no redecidido, que es
exactamente lo que [ADR-0006](../adr/0006-registrar-la-recepcion-en-una-bitacora-antes-de-encolar.md)
exige al separar el acuñado de la publicación.

**La única aparente excepción, y por qué no rompe la regla.** `infraestructura/bitacora.py`
reconstruye un `EntradaDeBitacora` en su línea 117, dentro de `BitacoraEnDisco.pendientes()`.
No es una segunda autoría: es la lectura de vuelta de exactamente los mismos cuatro campos que
`ingesta` ya escribió en la línea 138 de `recepcion.py`, deserializados desde el JSON Lines que
la propia bitácora produjo. `BitacoraDeRecepcion` es un puerto (`Protocol`) que `ingesta`
declara y que `infraestructura` implementa; el adaptador puede rearmar el dato que le
confiaron, pero no le añade ni le cambia ningún campo. Si algún día `BitacoraEnDisco` empezara a
inferir o corregir un campo al releerlo —por ejemplo, a decidir un `estado` que `ingesta` no le
dio— ahí sí pasaría a tener dos dueños, y esta tabla es la que lo haría visible.

---

## Entidades previstas (sin construir)

Los aspectos A-02 a A-05 todavía no tienen código ([`docs/aspectos.md`](../aspectos.md)), así que
sus datos no pueden llevar ruta ni línea sin inventarlas. Se dejan aquí, con dueño previsto según
la responsabilidad que cada módulo ya declara en su `__init__.py`, para que la tabla de arriba se
complete por adición y no se reescriba cuando esos aspectos se especifiquen.

| Entidad prevista | Módulo dueño previsto | Aspecto | Estado |
|---|---|---|---|
| Marca detectada y su nivel de confianza | `omr` | A-02 | Pendiente (S4) |
| Nota / resultado de calificación | `calificacion` | A-03 | Pendiente (S4) |
| Banco de preguntas y clave de respuestas | `autoria` | A-04 | Pendiente (S6) |
| Distractor diagnóstico (RF-11, opcional) | `autoria` | A-04 | Pendiente (S6) |
| Usuario, rol y curso | `identidad` | A-05 | Pendiente (S6) |

Que el dueño previsto de la nota sea `calificacion` y no `omr` ni `dashboard` es deliberado:
`calificacion` es el único módulo cuyo `__init__.py` declara la responsabilidad de «cálculo de
notas»; `omr` entrega la detección y su confianza, `dashboard` solo agrega y presenta lo que
`calificacion` ya decidió. Si al construir A-03 una nota terminara mutándose desde `dashboard`
—por ejemplo, para redondear una cifra visible— esta tabla es la que declara que eso está fuera
de regla, sin esperar a que una prueba de fronteras lo detecte primero.

---

## Recorrido de la auditoría

Esta sección es lo contrario de la tabla de arriba: no qué módulo *debería* decidir cada dato, sino
qué se encontró al recorrer el código preguntando quién lo decide de verdad. Es un recorrido
**manual** del backend completo, no de una muestra, y lo hace una persona porque ninguna
herramienta conoce la regla de dueño único que este documento enuncia. Los hallazgos que SonarQube Cloud
reporta sobre el mismo código son de otra clase y están documentados aparte, en
[`docs/evidencia/hallazgos-y-correcciones.md`](../evidencia/hallazgos-y-correcciones.md).

**Qué se buscó, en este orden.** Primero, dónde se construye o se muta cada una de las entidades de
[`modelo.py`](../../backend/infraestructura/modelo.py) y el `Trabajo` de
[`cola.py`](../../backend/infraestructura/cola.py): un `grep` de cada nombre de clase sobre
`backend/`, descartando las pruebas, y la lectura de cada sitio para distinguir la autoría real de
la traducción o la deserialización. Segundo, qué mecanismo del repositorio hace cumplir hoy la
regla, que resultó ser la prueba de fronteras
([`test_fronteras.py`](../../backend/tests/test_fronteras.py)) y su lista `MODULOS`, y qué queda
fuera de su alcance. Tercero, qué datos viajan entre procesos sin ser entidades: el nombre de la
cola, la ruta de la bitácora y el estado de una hoja.

**Los dos comandos que la ficha propone devuelven vacío sobre este repositorio, y eso es parte del
hallazgo, no un fallo de la búsqueda.** El primero busca migraciones, esquemas o un directorio
`models/`: no hay base de datos en uso todavía (el ADR de persistencia sigue abierto como riesgo
R-06, y `postgres` está en el compose sin esquema ni módulo que lo consulte), y además el modelo
compartido se llama `modelo.py`, en español, y el patrón `models?/` no lo alcanza. El segundo busca
escrituras con `INSERT INTO`, `.save(` o `repository.`, y aquí las escrituras pasan por puertos con
nombres del dominio, `almacen.guardar` y `bitacora.registrar`. Por eso cada hallazgo de esta
sección se cita con ruta y línea explícitas.

**Alcance.** Cubre el backend en el estado en que está el aspecto A-01, que es el único construido.
Las entidades de A-02 a A-05 no tienen código, así que todavía no pueden tener violaciones: lo que
les corresponde es la tabla de dueños previstos de la sección anterior. La lista crece por adición
con cada aspecto que se construya.

---

## Violaciones de propiedad de datos

Las cinco que salieron del recorrido. **Todas están abiertas**, verificadas contra `8f662e3`, y
cada una lleva su acción correctiva y aquello de lo que depende para poder hacerse.

| ID | Violación | Dónde está | Acción correctiva | Depende de |
|---|---|---|---|---|
| V-1 | `api` y `worker` importan el dominio sin declarar frontera, y la prueba que la verifica no los recorre | `backend/api/__init__.py`, `backend/worker/__init__.py`, `backend/tests/test_fronteras.py:17` | Docstring con `Responsabilidad:` e `Importa:` en ambos y agregarlos a `MODULOS`, comprobando la prueba en rojo | Nada |
| V-2 | El nombre de la cola está declarado dos veces y ninguna declaración es la fuente de verdad | `backend/api/settings.py:13`, `backend/worker/main.py:25` | Una sola declaración en `infraestructura/cola.py` y la prueba que falla si los dos procesos resuelven nombres distintos | Nada |
| V-3 | El estado de una hoja existe en la bitácora y en la `HojaAceptada` que viajó al frontend, sin nada que los concilie | `backend/infraestructura/modelo.py:65`, `backend/ingesta/recepcion.py:165` | Que la bitácora sea la única fuente de verdad del estado al construir el reintento | Que exista A-02 |
| V-4 | `BitacoraEnDisco` supone un único proceso escritor, y nada lo declara ni lo impide | `backend/infraestructura/bitacora.py:70` | Declarar el supuesto en el adaptador y cerrarlo en el ADR de persistencia definitiva | El ADR que cierra R-06 |
| V-5 | La regla de dueño único vive solo en este documento: ninguna prueba la verifica | `backend/infraestructura/modelo.py`, `backend/tests/test_fronteras.py` | Línea `Posee:` en el docstring de cada módulo y extender la prueba de fronteras a la propiedad | Nada |

### V-1 · `api` y `worker` importan el dominio sin declarar frontera

`backend/api/__init__.py` y `backend/worker/__init__.py` **pesan cero bytes**: son los dos únicos
paquetes del backend sin docstring, frente a los siete del dominio, que declaran todos su
`Responsabilidad:` y su `Importa:`. Y los dos importan dominio:
[`api/main.py`](../../backend/api/main.py) trae `infraestructura.almacen`,
`infraestructura.bitacora`, `infraestructura.cola`, `infraestructura.modelo` e `ingesta` en sus
líneas 17 a 21, y [`worker/main.py`](../../backend/worker/main.py) trae `infraestructura.cola` en
su línea 15.

Por qué es una violación de propiedad de datos y no solo de estructura: el único mecanismo que hoy
hace cumplir algo parecido a la regla de dueño único es
[`test_fronteras.py`](../../backend/tests/test_fronteras.py), que lee la línea `Importa:` de cada
docstring y falla si un módulo importa algo que no declaró. Su lista `MODULOS` (líneas 17 a 25)
contiene exactamente los siete módulos del dominio, así que **los dos paquetes que tocan las
entidades desde fuera del dominio son precisamente los dos que la prueba no recorre**.
`api/main.py` construye un `ArchivoCargado` en su línea 85; hoy es traducción fiel del
`multipart/form-data` a un tipo que `ingesta` ya definió, y por eso no aparece como segundo dueño
en la tabla de arriba, pero nada en el repositorio verificaría que siga siéndolo.

Que la prueba sí sirve para lo que declara está comprobado: quitarle la línea `Importa:` a
cualquiera de los siete la pone en rojo, con el mensaje que `_importados_permitidos` levanta
(`test_fronteras.py:36`). El hueco no es la prueba, es su alcance.

**Acción correctiva.** Escribir el docstring de los dos paquetes con `Responsabilidad:` e
`Importa:`, declarando lo que cada uno ya importa, y agregar `api` y `worker` a `MODULOS`. La
corrección no se da por buena hasta ver la prueba en rojo quitándole la línea `Importa:` a uno de
los dos recién agregados, por el mismo criterio con el que se validaron las pruebas de A-01.

### V-2 · El nombre de la cola está declarado dos veces

`NOMBRE_COLA` aparece en [`api/settings.py`](../../backend/api/settings.py) línea 13 y en
[`worker/main.py`](../../backend/worker/main.py) línea 25. Las dos leen la misma variable de
entorno y las dos repiten el mismo literal por omisión, `"procesamiento"`. Hoy el sistema funciona
porque coinciden, pero **nada verifica que coincidan**, y el dato que relaciona a los dos procesos
no tiene un dueño: tiene dos declaraciones de igual rango.

Que esto no lo cubre ninguna prueba no es una suposición: ya está registrado. La sexta mutación de
las seis con las que se validaron las pruebas del corte 1 era devolver el nombre de la cola del
worker a un literal, y **no la detecta ninguna** de las 47 pruebas del backend; quedó declarada
como hueco en [ADR-0006](../adr/0006-registrar-la-recepcion-en-una-bitacora-antes-de-encolar.md) y
en el [documento de evidencia](../evidencia/medicion-ec07.md). Lo que agregó este recorrido es la
segunda mitad del problema: **ni `NOMBRE_COLA` ni `RUTA_BITACORA` aparecían en
`docker-compose.yml` ni en `.env.example`**, donde sí están `REDIS_URL`, `DATABASE_URL`,
`RUTA_ALMACEN` y `ALLOWED_ORIGIN`. Un despliegue que quisiera cambiar el nombre de la cola tenía
que fijarlo en dos servicios sin que ningún archivo del repositorio dijera que son dos: fijarlo
solo en `api` deja a la API encolando en una lista y al worker escuchando otra, con el lote
confirmado al docente y ninguna hoja procesada. Es el mismo modo de fallo que ADR-0006 ataca desde
el otro lado.

**Esa mitad ya está cerrada.** Las dos variables están declaradas en `.env.example` y en
`docker-compose.yml`: `NOMBRE_COLA` en los servicios `api` y `worker`, con el mismo valor por
omisión que ya tenía el código, y `RUTA_BITACORA` solo en `api`, que es el único proceso que la
lee. Lo que sigue abierto de V-2 es la declaración única y la prueba que la verifica.

**Acción correctiva.** Dejar una sola declaración del valor por omisión en
[`infraestructura/cola.py`](../../backend/infraestructura/cola.py), que es el módulo que los dos
procesos ya importan, y que `api/settings.py` y `worker/main.py` la lean de ahí en vez de
repetirla. Poner la declaración en `api/settings.py` y hacer que el worker la importe resolvería la
duplicación creando una dependencia nueva de `worker` hacia `api`, que es justamente la frontera
que V-1 deja sin declarar. Falta además la prueba que hoy no existe, que es la que falla si los
dos procesos resuelven nombres distintos. Esa prueba es también la que
cierra el hueco de mutación declarado en ADR-0006.

### V-3 · El estado de una hoja vive en dos sitios

La bitácora es de solo agregado y guarda **hechos, no estado**: `recibida` cuando la hoja quedó
almacenada (`bitacora.py:77`) y `encolada` cuando su trabajo llegó a la cola (`bitacora.py:89`). El
estado se deriva releyendo el archivo, que es lo que hace `pendientes()` (`bitacora.py:98`). Pero
`HojaAceptada` tiene además un campo `estado`
([`modelo.py:65`](../../backend/infraestructura/modelo.py)), que `recepcion.py` fija en su línea
165 con el valor que corresponda en ese instante y que viaja en la respuesta HTTP hasta el
frontend.

Las dos representaciones nacen del mismo dueño, `ingesta`, así que la regla no se rompe en el
momento de la escritura. Se rompe después: la copia que viajó al frontend **no se actualiza
nunca**. Cuando A-02 construya el reintento de las hojas `pendiente_de_encolar`, la bitácora dirá
`encolada` y la pantalla que el docente tiene abierta seguirá diciendo `pendiente_de_encolar`, sin
que nada concilie las dos. El dato tiene un dueño pero dos copias con vidas distintas, que es la
forma en que este tipo de violación aparece en un sistema que todavía no tiene base de datos.

**Acción correctiva.** Al construir el reintento en A-02, declarar la bitácora como única fuente de
verdad del estado de una hoja y que cualquier consulta posterior se resuelva contra ella. El campo
`estado` de `HojaAceptada` se mantiene, porque el frontend lo lee y quitarlo rompería el contrato
con la pantalla de carga, pero pasa a documentarse en el modelo como lo que es: una instantánea del
momento de la respuesta, no el estado vigente.

### V-4 · `BitacoraEnDisco` supone un único proceso escritor

`_agregar` ([`bitacora.py:70`](../../backend/infraestructura/bitacora.py)) abre el archivo en modo
`a`, escribe una línea completa, hace `flush` y `fsync`, y cierra. No hay bloqueo de archivo ni
coordinación de ningún tipo, y ni el docstring del adaptador ni ADR-0006 declaran el supuesto.

Con una sola réplica de `api` el diseño es correcto y es lo que EC-07 midió. Con dos, dos líneas
pueden entrelazarse en el mismo archivo, y `pendientes()` descarta la línea que no parsea
(`bitacora.py:110`, con el comentario que explica por qué una línea truncada solo puede ser la
última). Ese descarte es seguro cuando el único escritor murió a mitad de línea, pero con dos
escritores la línea corrupta puede describir una hoja que sí se almacenó: **perder su registro es
exactamente la pérdida silenciosa que ADR-0006 existe para evitar**, y el 0 % medido dejaría de
valer. La regla dice que `ingesta` es el dueño del dato; el adaptador no puede sostener esa
propiedad si el proceso que lo ejecuta se replica.

**Acción correctiva.** Declarar el supuesto de una sola réplica en el docstring de
`BitacoraEnDisco` y en el compose, que es lo inmediato, y cerrarlo en el ADR de persistencia
definitiva que resuelve R-06, que es donde se decide el medio. No se corrige poniéndole un bloqueo
de archivo a este adaptador: es provisional por diseño, y darle garantías de concurrencia lo
convertiría en la decisión de persistencia que ese ADR todavía no ha tomado.

### V-5 · La regla de dueño único no la verifica ninguna prueba

Las cinco entidades de `modelo.py` y el `Trabajo` de `cola.py` tienen dueño asignado en la tabla de
arriba, pero nada en el código lo sostiene. `modelo.py` es el único módulo que los siete
`__init__.py` declaran poder importar, decisión deliberada y justificada en el propio archivo, con
una consecuencia que hay que decir: **cualquier entidad que se declare ahí queda por omisión al
alcance de los siete módulos**, y esta tabla es lo único que dice cuál de ellos la posee.
`test_fronteras.py` verifica quién importa a quién, no quién decide qué.

El efecto práctico llega con el próximo aspecto. Cuando A-02 declare la marca detectada con su
nivel de confianza, o A-03 la nota, nada impedirá que nazcan sin dueño declarado, o que un segundo
módulo empiece a fijarles un campo, hasta que alguien vuelva a hacer a mano el recorrido de esta
sección. Una regla que solo vive en un documento se degrada exactamente igual que la frontera de
imports que el riesgo R-08 describe, y por la misma razón.

**Acción correctiva.** Llevar la declaración de propiedad al código, con una línea `Posee:` en el
docstring de cada `__init__.py`, del mismo modo en que `Importa:` ya declara la frontera de
importaciones, y extender `test_fronteras.py` para que falle si una entidad de `modelo.py` no
aparece declarada por exactamente un módulo. Es la corrección que convierte esta tabla en algo que
el CI mantiene, y la que hace que las cuatro anteriores no vuelvan a aparecer.

---

## Aspectos ↔ contextos

Esta sección conecta la propiedad de datos con la tabla de trazabilidad de
[`aspectos.md`](../aspectos.md#tabla-de-trazabilidad), y se lee en dos direcciones a propósito.
La primera tabla va del aspecto al contexto; la segunda va del contexto al aspecto, que es la que
deja ver si algún contexto del mapa se quedó sin nadie que lo realice.

Los nombres en versalita son los **contextos del [mapa de la sección 8.1](arc42-template-ES.md#81-mapa-de-contextos)**;
entre paréntesis va el módulo del backend que los implementa, que es el mismo nombre en minúscula.
La última columna es otra cosa y conviene no confundirla: son las relaciones del **Nivel 1 del
C4**, que describen cómo el sistema se comunica con actores externos, no cómo se divide por dentro.

### De cada aspecto a su contexto

| Aspecto | Contexto del mapa (§8.1) | Módulo dueño de los datos | Entidades que crea | Relación del C4 Nivel 1 |
|---|---|---|---|---|
| [A-01](../aspectos.md#a-01) | **Ingesta** | `ingesta` | `ArchivoCargado`, `HojaAceptada`, `ArchivoRechazado`, `ResultadoRecepcion`, `EntradaDeBitacora` | [Rel. 1](../c4/doc-c4.md#relaciones): Profesor/TA → Sistema |
| [A-02](../aspectos.md#a-02) | **OMR** | `omr` (previsto) | Marca detectada y confianza (previsto) | Ninguna: proceso interno |
| [A-03](../aspectos.md#a-03) | **Calificación** y **Dashboard** | `calificacion` (previsto) | Nota / resultado (previsto) | [Rel. 2](../c4/doc-c4.md#relaciones): Sistema → Profesor/TA |
| [A-04](../aspectos.md#a-04) | **Autoría** | `autoria` (previsto) | Banco, clave, distractor (previsto) | [Rel. 1 y 3](../c4/doc-c4.md#relaciones): Profesor/TA → Sistema · Sistema → Proveedor de LLM |
| [A-05](../aspectos.md#a-05) | **Identidad** | `identidad` (previsto) | Usuario, rol, curso (previsto) | [Rel. 1 y 2](../c4/doc-c4.md#relaciones): transversal a ambas |

**Por qué A-03 abarca dos contextos.** Su enunciado es «calificación contra la clave y
**publicación de resultados**», y sus requisitos incluyen RF-05, las estadísticas por pregunta. La
comparación contra la clave y el cálculo de la nota son de Calificación; presentar esa nota, las
estadísticas y las alertas de revisión es la responsabilidad que §8.1 le asigna a Dashboard. Es el
único aspecto que cruza dos contextos, y por eso el dueño de los datos sigue siendo uno solo:
`calificacion` decide la nota, `dashboard` solo la presenta.

### De cada contexto a su aspecto

| Contexto del mapa (§8.1) | Aspecto que lo realiza | Estado |
|---|---|---|
| **Ingesta** | [A-01](../aspectos.md#a-01) | Construido |
| **OMR** | [A-02](../aspectos.md#a-02) | Declarado |
| **Calificación** | [A-03](../aspectos.md#a-03) | Declarado |
| **Dashboard** | [A-03](../aspectos.md#a-03), en su mitad de publicación (RF-05) | Declarado |
| **Autoría** | [A-04](../aspectos.md#a-04) | Declarado |
| **Identidad** | [A-05](../aspectos.md#a-05) | Declarado |
| **Infraestructura** | Ninguno, y es correcto que así sea | Interviene en A-01 |

**Por qué Infraestructura no tiene aspecto propio, y no es un olvido.** Es el único contexto de
soporte del mapa: no modela un subdominio de negocio, provee persistencia y servicios técnicos a
los otros seis. Interviene en A-01 con el almacén, la bitácora y el modelo compartido, pero no
decide ningún campo de negocio, que es justo lo que la regla de dueño único separa. Un aspecto
describe una capacidad que le sirve a alguien; Infraestructura no le sirve a un usuario, le sirve a
los otros seis contextos. El día que eso cambie será porque el ADR de persistencia (R-06) le dé una
decisión propia que defender, y entonces habrá que revisar esta fila.

**Por qué A-02 aparece sin relación del C4 Nivel 1 y eso no es un hueco.** Las tres relaciones del
Nivel 1 ([`c4/doc-c4.md`](../c4/doc-c4.md#nivel-1--diagrama-de-contexto-del-sistema)) cruzan la
frontera del sistema: el profesor que sube hojas o registra un banco, el sistema que devuelve notas
y alertas, y el sistema que pide distractores al LLM. La detección de marcas ocurre enteramente
dentro de la caja negra, entre el almacén y la cola, disparada por el worker y no por un actor
externo. **En el mapa de contextos de §8.1, en cambio, A-02 sí tiene contexto y es OMR**: los dos
usos de la palabra «contexto» en esta documentación significan cosas distintas, y esta es la fila
donde más se nota.
