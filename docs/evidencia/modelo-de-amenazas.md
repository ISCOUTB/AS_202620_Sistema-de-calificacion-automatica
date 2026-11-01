# Modelo de amenazas y plan de mitigación (S13)

| | |
|---|---|
| **Fecha** | 2026-10-31, sobre `master` después de la migración a iscoutb.dev ([ADR-0021](../adr/0021-desplegar-en-el-servidor-del-laboratorio-con-el-sitio-compilado-en-el-ci.md)) |
| **Método** | STRIDE sobre los elementos y las relaciones del [Nivel 2 del C4](../c4/doc-c4.md#nivel-2--diagrama-de-contenedores), más las piezas de despliegue de la [sección 7.1 del arc42](../arc42/arc42-template-ES.md#71-las-seis-piezas-del-despliegue) |
| **Escala** | Probabilidad (P) e impacto (I): Alta o Alto = 3, Media o Medio = 2, Baja o Bajo = 1. **Prioridad = P × I**, de 1 a 9. A igual prioridad, va primero la que alcanza a más gente |
| **Estado** | **Hecha** (en el código, con su prueba o su comprobación), **Pendiente** (con dueño y plazo) o **Aceptada** (con el motivo y lo que la reabre) |
| **Lo que decidió una mitigación estructural** | [ADR-0022](../adr/0022-poner-un-presupuesto-de-carga-delante-del-almacen.md): el presupuesto de carga, para AM-01 |
| **Dónde sigue** | La arquitectura de seguridad, la privacidad y las amenazas aceptadas, en las secciones 8 y 11 del [arc42](../arc42/arc42-template-ES.md) |

---

## 1. Qué se modeló

Los seis elementos del Nivel 2 (aplicación web, worker, cola, base de datos, almacén de imágenes y
proveedor de LLM) y sus ocho relaciones. La base de datos y las relaciones 2 y 6 están previstas y
no existen en el código, así que hoy no tienen amenazas propias: se modelan cuando R-06 las decida.

Al Nivel 2 se suman tres piezas del despliegue que el C4 no dibuja y que cambian lo que puede pasar:
el **borde** (Cloudflare y el Traefik del servidor), el **panel** (Dokploy, con las variables de
entorno) y la **rama `despliegue`** que publica el CI y el panel despliega sola.

Los límites de confianza que cruzan esos elementos:

1. **Internet → borde → aplicación web.** Todo lo que llega a la API es de cualquiera: no hay
   autenticación (`identidad`, A-05, está vacío). Además, la IP del servidor es pública y Traefik
   atiende a quien llegue directo, sin pasar por Cloudflare.
2. **Aplicación web → proveedor de LLM.** Lo único que sale de nuestra red, por HTTPS, con la clave
   de Groq.
3. **GitHub → servidor.** Lo que entra a `master` y pasa el CI se despliega sin que nadie lo apruebe.
4. **Almacén → disco compartido.** El volumen está en el disco de 200 GB que comparten los 23
   equipos del servidor, que no hace copias y borra los volúmenes después del 30-nov (R-31).

## 2. Amenazas priorizadas

Ordenadas por prioridad. «Relación N» es la relación N del Nivel 2 del C4.

| ID | STRIDE | Elemento del C4 | Amenaza | P | I | Prioridad | Mitigación | Dueño | Estado |
|---|---|---|---|---|---|---|---|---|---|
| **AM-01** | Denegación de servicio | Almacén de imágenes, por las relaciones 1 y 3 | La ruta pública de carga llena el disco compartido: no había tope de hojas por lote ni de lotes por día, y por la IP directa tampoco del tamaño de la petición, que Starlette guarda en temporales antes de llamar a la ruta | Media | Alto | **6** | Presupuesto de carga: 250 hojas por lote, 256 MB por 24 horas, 100 MB por petición; 413 o 429 sin que ninguna hoja entre ([ADR-0022](../adr/0022-poner-un-presupuesto-de-carga-delante-del-almacen.md), [`test_presupuesto_de_carga.py`](../../backend/tests/test_presupuesto_de_carga.py)) | María | **Hecha** (S13) |
| **AM-02** | Suplantación | Relación 1 (Profesor / TA → aplicación web) | Cualquiera, sin cuenta, carga hojas a cualquier examen y pide distractores como si fuera el docente (R-14, R-17, R-19) | Alta | Medio | **6** | Construir `identidad` (A-05). Mientras tanto, solo hojas sintéticas en el servidor, y los dos presupuestos ([ADR-0015](../adr/0015-limitar-el-gasto-del-proveedor-de-llm-con-un-presupuesto-en-la-api.md), ADR-0022) acotan el daño | Sebastián, con A-05 | **Aceptada** hasta la primera hoja real |
| **AM-03** | Manipulación | Relación 3 (aplicación web → almacén) | Un nombre de archivo con `../` escribe fuera del directorio del examen | Media | Alto | **6** | `nombre_seguro` y un UUID delante de cada nombre ([`almacen.py:48`](../../backend/infraestructura/almacen.py) y 126); `test_un_nombre_con_rutas_no_escapa_del_directorio_del_examen` | Sebastián | **Hecha** (A-01) |
| **AM-04** | Manipulación, elevación | Contenedores del Nivel 2 (sus imágenes base) | Una vulnerabilidad conocida en `python:3.12-slim`, `nginx-unprivileged:alpine` o `redis:7-alpine`: el análisis de dependencias mira los paquetes de Python y de Dart, no el sistema de las imágenes | Media | Medio | **4** | Escanear las imágenes en el pipeline, con la misma regla: un hallazgo sin decidir no se despliega | Josué | **Pendiente**, antes del proyecto final |
| **AM-05** | Elevación de privilegios | Contenedores del Nivel 2 | Un proceso que escapa de su contenedor llega al servidor que comparten 23 equipos | Baja | Alto | **3** | `api` y `worker` corren como `appuser` ([`backend/Dockerfile:21`](../../backend/Dockerfile)), `web` con `nginx-unprivileged`; sin modo privilegiado, montajes del servidor ni puertos publicados, como pide el manual del servidor; límites de memoria y CPU por contenedor | Sebastián | **Hecha** (ADR-0021) |
| **AM-06** | Manipulación, elevación | Rama `despliegue` → servidor (arc42 §7.1) | Una cuenta del equipo o una dependencia comprometida llega sola al servidor, porque cada push a `master` que pasa el CI se despliega | Baja | Alto | **3** | Acciones fijadas por hash; dependencias instaladas con `--require-hashes`; el análisis de dependencias bloquea `publicar-despliegue`; el binario del análisis se comprueba por SHA-256. Falta la verificación en dos pasos en las cuatro cuentas | Susana (el análisis); cada integrante, su cuenta | **Hecha** en parte; la verificación en dos pasos, **pendiente** |
| **AM-07** | Divulgación | Relación 8 (aplicación web → proveedor de LLM) | Datos personales de estudiantes llegan a Groq | Baja | Alto | **3** | Por diseño (RNF-13): lo único que viaja es `PreguntaParaDistractores`, enunciado y respuesta correcta ([`distractores.py:42`](../../backend/autoria/distractores.py)); el worker nunca llama al proveedor. Ver la [sección 4](#4-riesgos-del-componente-generativo) | Equipo | **Hecha** (S9) |
| **AM-08** | Repudio | Almacén de imágenes (bitácora), por la relación 1 | Nadie puede probar quién cargó un lote, ni negar haberlo cargado | Alta | Bajo | **3** | La bitácora de solo agregado ([ADR-0006](../adr/0006-registrar-la-recepcion-en-una-bitacora-antes-de-encolar.md)) y la identidad de cada hoja ([ADR-0018](../adr/0018-dar-a-la-hoja-una-identidad-propia-y-derivar-su-estado-de-la-bitacora.md)) dicen qué entró y cuándo; el quién llega con A-05 | Sebastián, con A-05 | **Aceptada** hasta A-05: con notas reales el impacto sube a Alto (RNF-15) |
| **AM-09** | Divulgación | Aplicación web: `/docs`, `/openapi.json` y `/metricas`, públicos | Exponen la forma de la API y cuentas de uso | Alta | Bajo | **3** | Solo publican cuentas y esquemas, ningún dato de un docente, una pregunta o una hoja; el contrato es público por decisión, versionado en el repositorio | Equipo | **Aceptada** |
| **AM-10** | Divulgación, manipulación | Relación 8 | Alguien en la ruta de red se hace pasar por Groq con un certificado de una autoridad comprometida, lee la `LLM_API_KEY` o devuelve distractores falsos: `certifi` 2026.7.22 confiaba en la raíz de emSign con intermedios comprometidos | Baja | Medio | **2** | `certifi` 2026.10.18 y el análisis de dependencias en el pipeline ([sección 5](#5-análisis-de-dependencias)) | Susana | **Hecha** (S13) |
| **AM-11** | Manipulación | Relación 8, componente generativo | Inyección de prompt: el enunciado trae instrucciones para el modelo | Media | Bajo | **2** | Ver la [sección 4](#4-riesgos-del-componente-generativo) | Equipo | **Hecha** (S9); lo que queda, **aceptado** |
| **AM-12** | Manipulación | Aplicación web: caché de propuestas ([ADR-0019](../adr/0019-guardar-en-cache-las-propuestas-de-distractores.md)) | Envenenamiento del contexto: alguien deja en la caché propuestas que después recibe el docente | Baja | Medio | **2** | Ver la [sección 4](#4-riesgos-del-componente-generativo) | Equipo | **Aceptada** |
| **AM-13** | Divulgación | Aplicación web: variables de entorno en el panel | La `LLM_API_KEY` la ve quien entra al panel, y se filtraría si alguien la versiona | Baja | Medio | **2** | No se versiona (RNF-11); barrido sin hallazgos en `HEAD` y en el historial el 31-oct; Dokploy escribe `deploy/.env` al desplegar. Si hay duda, se rota en console.groq.com. Sin tarjeta, el peor caso es la cuota, no una factura (RNF-16) | Sebastián | **Hecha** (el barrido); el acceso del panel, **aceptado** |
| **AM-14** | Divulgación, denegación | Cola de trabajos (relaciones 4 y 5) | Otro contenedor del servidor alcanza Redis, que no tiene contraseña, y lee o vacía la cola | Baja | Medio | **2** | Sin puertos publicados ([`compose.lab.yaml`](../../deploy/compose.lab.yaml)); falta comprobar en el panel que `redis` está solo en la red del proyecto y no en la de Traefik, que comparten los equipos | Sebastián | **Pendiente**: la comprobación en el panel |
| **AM-15** | Suplantación | Aplicación web (sitio) y relación 1 | Otra página usa el navegador del docente para llamar a la API | Baja | Bajo | **1** | CORS con un solo origen (`ALLOWED_ORIGIN`); no hay cookies ni sesiones que aprovechar | Equipo | **Hecha** |

## 3. El plan: qué se atacó primero

| Prioridad | Amenazas | Qué se hizo | Dónde |
|---|---|---|---|
| 6 | AM-01, AM-02, AM-03 | **AM-01 se cerró esta semana**, con la única mitigación estructural de la S13. AM-03 estaba cerrada desde A-01. AM-02 se acepta con fecha de vencimiento: ninguna hoja real entra antes de A-05 | ADR-0022 (S13); `almacen.py` (A-01); [arc42 §11](../arc42/arc42-template-ES.md#11-risks-and-technical-debts) |
| 4 | AM-04 | Pendiente, con dueño y plazo | Antes del proyecto final |
| 3 | AM-05 a AM-09 | Cerradas por el despliegue (AM-05) y por diseño (AM-07); el análisis de dependencias cubre parte de AM-06; AM-08 y AM-09 se aceptan | ADR-0021, RNF-13, el job `dependencias` |
| 2 y 1 | AM-10 a AM-15 | AM-10 se cerró esta semana; AM-14 queda por comprobar | `certifi` 2026.10.18 |

**Por qué AM-01 antes que AM-02, con la misma prioridad.** AM-01 alcanza a los 23 equipos del
servidor, no solo al nuestro, y se podía cerrar en la semana. AM-02 solo se cierra de verdad con
`identidad`, que es un aspecto entero (A-05); mientras tanto, su impacto es Medio porque en el
servidor solo hay hojas sintéticas, y la condición de aceptarla es justo esa: el día que entre una
hoja real, el impacto sube a Alto y A-05 tiene que existir antes.

**Por qué AM-10 se cerró antes que AM-04, con menos prioridad.** Salió del análisis de dependencias,
que es parte de la entrega, y corregirlo eran tres líneas de `requirements.txt`. No desplazó nada
de más prioridad: AM-04 necesita construir las imágenes en el pipeline y decidir qué hacer con sus
hallazgos, que no cabía en la semana.

## 4. Riesgos del componente generativo

El único componente generativo es la ruta de distractores (RF-11, A-06): la aplicación web le pide a
Groq propuestas para una pregunta, y el docente decide cuáles usa. La calificación no usa el modelo
([ADR-0005](../adr/0005-acotar-el-llm-a-la-generacion-de-distractores-diagnosticos.md)).

### Inyección de prompt (AM-11)

**Qué podría pasar.** El enunciado lo escribe quien llama a la ruta, y sin autenticación puede ser
cualquiera (AM-02). Un enunciado con «ignora las instrucciones anteriores y…» puede hacer que el
modelo devuelva otra cosa.

**Qué lo frena:**

- Las instrucciones van en el mensaje del sistema y el enunciado en el del usuario, por separado
  ([`proveedor_llm.py:134`](../../backend/autoria/proveedor_llm.py)).
- El enunciado tiene un tope de 1 000 caracteres y la respuesta correcta, de 300
  ([`esquemas.py`](../../backend/api/esquemas.py), `SolicitudDeDistractores`).
- La respuesta se pide como JSON (`response_format`, línea 144) y se lee con una forma fija: una
  lista de distractores con su etiqueta (línea 194). Lo que no tenga esa forma es un 503, no un
  texto libre.
- La regla de `distractores.py` descarta lo que repite la respuesta correcta.
- El sitio muestra cada propuesta como texto de Flutter, nunca como HTML: una salida manipulada no
  puede ejecutar nada en el navegador.
- Ninguna propuesta entra a un examen sin la habilitación del docente (RF-07).

**Qué queda, aceptado.** El modelo puede devolver propuestas malas o fuera de tema. Las recibe solo
quien las pidió, con la forma fija de arriba, y el docente las revisa una por una.

### Fuga de datos (AM-07)

**Qué podría pasar.** Que una hoja, un nombre o una nota lleguen al proveedor, que es un tercero
con su propia política de datos, fuera de nuestro control.

**Qué lo frena.** RNF-13, por construcción: `PreguntaParaDistractores` es lo único que viaja, y solo
tiene el enunciado, la respuesta correcta y la cantidad
([`distractores.py:42`](../../backend/autoria/distractores.py)). El worker, que es quien abre las
hojas, no conoce al proveedor. La fase de autoría, donde vive la ruta, va antes del examen: todavía
no existe ninguna hoja.

**Hacia el otro lado:** la clave de Groq no sale en ninguna respuesta ni en el registro, y
`/metricas` solo publica cuentas.

### Envenenamiento del contexto (AM-12)

**Qué podría pasar.** No hay recuperación de documentos ni memoria entre solicitudes: el único
«contexto» que sobrevive de una solicitud a otra es la caché de propuestas (ADR-0019), que guarda 24
horas lo que respondió el modelo. Si alguien pudiera dejar ahí propuestas manipuladas, el docente
las recibiría después.

**Qué lo frena:**

- La clave de la caché es el texto completo de la pregunta, normalizado, más el modelo y la huella
  de las instrucciones ([`cache.py:67`](../../backend/autoria/cache.py)). Para que el docente reciba
  lo que dejó otro, ese otro tendría que mandar exactamente la misma pregunta, y entonces el modelo
  respondió a la misma pregunta. Un enunciado con instrucciones inyectadas es otro enunciado, con
  otra clave.
- La regla se vuelve a aplicar a lo que sale de la caché.
- Con `otras: true`, el docente pide propuestas nuevas sin leer la caché.

**Qué queda, aceptado.** La caché es de todos y no de cada docente: quien conozca de antemano una
pregunta puede hacer que la respuesta del modelo quede guardada antes. Esa respuesta es la misma que
habría recibido el docente. Lo cierra A-05, con una caché por docente si hiciera falta.

## 5. Análisis de dependencias

| | |
|---|---|
| **Herramienta** | OSV-Scanner v2.7.0, sobre la base pública de vulnerabilidades de OSV |
| **En el pipeline** | Job `dependencias` de [`ci.yml`](../../.github/workflows/ci.yml), el primero del workflow. `publicar-despliegue` lo espera: con una vulnerabilidad sin decidir, el servidor no recibe el commit |
| **Qué analiza** | Las 29 versiones fijadas de [`backend/requirements.txt`](../../backend/requirements.txt) y los 47 paquetes de [`frontend/pubspec.lock`](../../frontend/pubspec.lock) (43 de pub.dev y 4 del SDK) |
| **Run** | https://github.com/ISCOUTB/AS_202620_Sistema-de-calificacion-automatica/actions/runs/41328819502, el primero con el job (commit `553fff3`). El resultado está en el resumen del run, que se lee sin iniciar sesión |
| **Comprobación aparte** | `pip-audit` 2.10.1 sobre el mismo `requirements.txt`, el 31-oct, con el mismo hallazgo |

**Los hallazgos y qué se hizo con cada uno:**

| Paquete | Versión | Vulnerabilidad | Nos afecta | Decisión |
|---|---|---|---|---|
| `certifi` | 2026.7.22 | PYSEC-2026-4320 (GHSA-6q48-6c7w-9gw2): trae la raíz «emSign ECC Root CA - G3», con ocho certificados intermedios de claves comprometidas | Sí: `httpx` valida con ese almacén el certificado de Groq (relación 8, AM-10) | **Corregida**: 2026.10.18, que quita la raíz (commit `9d6b221`) |
| Los 43 paquetes de pub.dev | | Ninguna conocida | | Nada que decidir |

Después de la corrección, el job da cero vulnerabilidades en los dos archivos.

**Cómo se decide un hallazgo nuevo.** Si sale uno, el job falla y no se despliega. Se decide de una
de dos formas: subir la versión, o, si no nos afecta, aceptarlo con su motivo y su fecha de
vencimiento en un `osv-scanner.toml` junto al archivo afectado, y agregarlo a la tabla de arriba.

**Lo que no cubre:** el sistema de las imágenes base (AM-04, pendiente) y las acciones de GitHub,
que van fijadas por hash.

No es el análisis estático del código: ese es el de SonarCloud, que corre desde el segundo corte.
Al entrar el job, SonarCloud marcó su descarga como vulnerabilidad (`githubactions:S6506`): el
`curl -L` no fijaba el protocolo, y una redirección podía bajar a HTTP. El SHA-256 ya rechazaba un
binario cambiado, pero se corrigió en el código con `--proto "=https" --tlsv1.2` (commit `d5f9c2e`)
en vez de aceptarlo en SonarCloud, y el *Quality Gate* volvió a verde.

## 6. Privacidad: qué datos personales se tratan y con qué base

### 6.1 Los datos que trata el sistema hoy

Contrastado con el código: el modelo de datos (`infraestructura/modelo.py`) no tiene ningún campo
de estudiante, y la búsqueda de la ficha (`email`, `correo`, `cedula`, `documento`, `nombre_completo`
y demás) no encuentra nada fuera de `docs/`. Pero hay datos personales en lo que se guarda:

| Dato | De quién | Dónde queda | Para qué | Cuánto tiempo |
|---|---|---|---|---|
| **La imagen de la hoja escaneada**, con lo que el estudiante escribió en ella (su nombre o su código) y sus marcas | Estudiante | El almacén de imágenes, en el volumen del servidor; la abre el worker | Calificar el examen (RF-01) y responder una revisión de nota (RNF-15) | Hoy, hasta que el servidor borre los volúmenes, después del 30-nov. Nada la borra antes (RNF-14, R-06) |
| **El nombre del archivo**, tal como lo subió el docente. Si los nombra por estudiante, es el nombre del estudiante | Estudiante, según cómo nombre el docente | La bitácora (`nombre_archivo`), la ruta en el almacén y la respuesta de la carga | Que el reporte le diga al docente qué hoja entró y cuál no (EC-07) | El mismo de la imagen |
| **La IP de quien llama a la API** | Docente | El registro de acceso de uvicorn, en los logs del contenedor que muestra el panel; también la ven Cloudflare y Traefik | Operar y depurar | Hasta el siguiente despliegue, que recrea el contenedor |
| **Las calificaciones** | Estudiante | Todavía no existen: llegan con A-03 y la base de datos de R-06 | Lo que justifica el sistema | Por decidir, con RNF-14 y RNF-15 |

**Lo que no trata:** no hay cuentas, así que no hay correo ni contraseña de ningún docente; no hay
base de datos; y a Groq solo van el enunciado y la respuesta correcta de una pregunta (RNF-13).

### 6.2 La base

- **El marco:** la Ley Estatutaria 1581 de 2012 y su reglamento, el Decreto 1377 de 2013, hoy
  compilado en el Decreto 1074 de 2015 (RNF-12).
- **El responsable del tratamiento es la universidad**, no el equipo: QuantIA es una herramienta
  con la que el docente califica en nombre de ella. La UTB tiene su política de tratamiento de
  datos personales y recoge la autorización de cada estudiante
  ([políticas institucionales](https://www.utb.edu.co/la-utb/politicas-y-otros/)); las consultas y
  los reclamos de los titulares se dirigen a su Secretaría General.
- **La base es la autorización del titular** (artículo 9 de la ley), que el estudiante da a la
  universidad, con la finalidad académica de evaluarlo. Ninguno de estos datos es sensible en el
  sentido del artículo 5.
- **Los principios que el diseño ya aplica:** finalidad (las hojas solo sirven para calificar);
  acceso y circulación restringida (nada sale a Groq, RNF-13); seguridad (AM-01, AM-03, AM-05).

**Lo que el equipo no ha confirmado.** No leímos las finalidades exactas de la autorización de la
UTB: su página no se deja descargar de forma automática, y no se consultó a la Secretaría General.
Por eso es una de las condiciones de abajo.

### 6.3 Hoy, y lo que falta antes de la primera hoja real

**Hoy no hay titulares reales.** En el servidor solo se cargan hojas sintéticas, generadas por el
equipo, sin datos de ninguna persona; el entorno se borra el 30-nov (R-31).

**Antes de cargar la primera hoja de un estudiante real tienen que existir cuatro cosas:**

1. `identidad` (A-05), para que solo el docente del curso cargue y consulte (AM-02, AM-08).
2. La confirmación, con la universidad, de que su autorización cubre calificar con esta herramienta,
   y de en calidad de qué la usa el docente.
3. La retención de RNF-14: las imágenes se borran o se anonimizan al cerrar el periodo de revisión
   de nota (RNF-15). Es parte del ADR de persistencia que cierra R-06.
4. Una indicación en la pantalla de carga: nombrar los archivos sin datos del estudiante, porque el
   nombre queda en la bitácora.

## 7. Lo que este modelo no cubre

- **Pruebas de penetración o auditoría externa:** no se hicieron, y la ficha no las pide.
- **El borde y el panel por dentro** (Cloudflare, Traefik y Dokploy): son del curso y no los
  configuramos. Se aceptan como están.
- **La base de datos y el OMR:** no existen todavía (R-06, A-02). Este modelo se repite cuando
  existan.
