# QuantIA

QuantIA es el sistema que automatiza la calificación de exámenes de opción múltiple de cálculo diferencial ([ADR-0008](docs/adr/0008-renombrar-el-sistema-a-quantia.md) explica el nombre). El profesor carga su banco de preguntas y su clave de respuestas, aplica el examen en papel y sube los escaneos; el sistema los lee mediante reconocimiento óptico de marcas (OMR), califica contra esa clave y publica los resultados en un dashboard, devolviendo a revisión manual toda marca que no supere el umbral de confianza. Como apoyo opcional durante la preparación, puede proponer **distractores diagnósticos** con ayuda de un modelo de lenguaje. El sistema es una herramienta de apoyo al criterio del profesor, no un reemplazo de su decisión final.

## Equipo

| Integrante | Cuenta de GitHub |
|---|---|
| Sebastián Cañas Plata | `scp1109` |
| Josué David Ortega De Arco | `josueacademico17-source` |
| María Del Mar Restrepo Licona | `Mariadelmar-restrepo` |
| Susana Marcela Rosales Castellar | `SusanaRosales` |

## Evidencia S9

La porción construida con apoyo de IA es **RF-11, la propuesta de distractores diagnósticos**
(aspecto [A-06](docs/aspectos.md#a-06)): el módulo [`backend/autoria/`](backend/autoria/) y la ruta
`POST /distractores` de la API, con el contrato en la versión 1.1.0.

| Fila de la ficha | Dónde está |
|---|---|
| Porción real y su cadena completa | [A-06 en `aspectos.md`](docs/aspectos.md#a-06): RF-11 → [EC-08](docs/arc42/arc42-template-ES.md#ec-08) → C4 → ADR → código → pruebas → evidencia |
| ADR con la decisión del equipo | [ADR-0013](docs/adr/0013-consumir-groq-detras-de-un-puerto-y-degradar-sin-bloquear-la-autoria.md): Groq detrás de un puerto de `autoria`, `httpx` sin dependencias nuevas, 20 s de espera sin reintentos y 503 ante cualquier falla |
| Prueba que falla ante el defecto | [El PR del defecto](https://github.com/ISCOUTB/AS_202620_Sistema-de-calificacion-automatica/pull/1), cerrado sin fusionar, y su [procedimiento con los runs](docs/evidencia/prueba-distractores-falla.md): sin el filtro de la respuesta correcta fallan 4 pruebas |
| Medición de EC-08 | [Evaluación](docs/evidencia/evaluacion-distractores.md): M1, ninguna de las 120 propuestas entregadas repite la respuesta correcta (0 %) · M2, p95 de la latencia de 2,91 s contra un techo de 15 s, en 40 solicitudes · M3, con el proveedor caído o lento la ruta responde 503 en 20,25 s como máximo, contra 21 s |
| Componente generativo evaluado | Conjunto de 20 preguntas ([`conjunto-evaluacion-distractores.json`](docs/evidencia/conjunto-evaluacion-distractores.json)), resultados ([`evaluacion-distractores.json`](docs/evidencia/evaluacion-distractores.json)), calidad: 44 de 60 propuestas diagnósticas válidas (73 %), ninguna equivalente a la respuesta correcta, y el error más común es la etiqueta (8 incorrectas y 4 a medias); costo: US$0 en la capa gratuita (al precio de pago serían US$0,0004 por solicitud y US$0,008 por examen de 20 preguntas); el proveedor en el [C4 Nivel 2, relación 8](docs/c4/doc-c4.md#relaciones-1) |
| `ia.md` con lo aceptado, lo corregido y lo rechazado | [Entrada 12](docs/ia.md#entrada-12) |
| Auditoría de erosión, dependencias y credenciales | [`auditoria-s9.md`](docs/evidencia/auditoria-s9.md): sin cruces de contexto ni de propiedad; un flanco de la prueba de fronteras, corregido; sin dependencias nuevas; sin credenciales |
| ADR aceptados no reescritos | [ADR-0014](docs/adr/0014-dejar-constancia-del-ajuste-de-enlaces-en-adr-0007.md) deja constancia del ajuste de enlaces de ADR-0007 |

## Dónde está la evidencia de cada entrega

La documentación larga vive en pocos archivos. Esta tabla dice, para lo que pide cada ficha, en
qué archivo y en qué sección está.

| Entrega | Qué | Dónde |
|---|---|---|
| Corte 1 | Medición de EC-07 antes y después del cambio, con su herramienta | [`docs/evidencia/medicion-ec07.md`](docs/evidencia/medicion-ec07.md) |
| S6 | Mapa de contextos y lenguaje ubicuo | [arc42 §8.1 y §8.2](docs/arc42/arc42-template-ES.md#81-mapa-de-contextos) |
| S6 | Tabla módulo → dato, recorrido de la auditoría y violaciones V-1 a V-5 con su plan | [arc42 §8.3](docs/arc42/arc42-template-ES.md#83-propiedad-de-datos) |
| S6 | Contexto del mapa que realiza cada aspecto | [`docs/aspectos.md`](docs/aspectos.md#tabla-de-trazabilidad) · [ADR-0007](docs/adr/0007-declarar-los-contextos-delimitados-y-la-regla-de-dueno-unico.md) |
| S6 | Hallazgos de SonarQube Cloud y sus correcciones | [`docs/evidencia/hallazgos-y-correcciones.md`](docs/evidencia/hallazgos-y-correcciones.md) |
| S7 | Contrato OpenAPI versionado (1.0.0) | [`docs/contrato/openapi.json`](docs/contrato/openapi.json) |
| S7 | Prueba de contrato y su paso propio en el pipeline | [`backend/tests/test_contrato.py`](backend/tests/test_contrato.py) · paso «Prueba de contrato (OpenAPI)» de [`ci.yml`](.github/workflows/ci.yml) |
| S7 | La prueba falla ante un cambio incompatible, con los tres runs | [`docs/evidencia/prueba-de-contrato-falla.md`](docs/evidencia/prueba-de-contrato-falla.md) |
| S7 | Flujos de interacción | [arc42 §6](docs/arc42/arc42-template-ES.md#6-runtime-view) |
| S7 | C4 Nivel 2 con protocolo y formato en cada relación | [`docs/c4/doc-c4.md`](docs/c4/doc-c4.md#nivel-2--diagrama-de-contenedores) |
| S9 | Porción construida con IA, prueba que falla, EC-08, auditoría y componente generativo | [Evidencia S9](#evidencia-s9) |
| Todas | Pipeline de integración continua | [Runs de GitHub Actions](https://github.com/ISCOUTB/AS_202620_Sistema-de-calificacion-automatica/actions) |
| Todas | Análisis estático y su *Quality Gate* | [SonarQube Cloud](https://sonarcloud.io/summary/new_code?id=ISCOUTB_AS_202620_Sistema-de-calificacion-automatica) |
| Todas | Respuesta a la retroalimentación automática | [`correcciones.md`](correcciones.md) |

## Entorno desplegado (S8)

Entorno de demostración: solo se cargan hojas sintéticas, nunca hojas de estudiantes (RNF-12), y
lo cargado se pierde en cada despliegue ([ADR-0012](docs/adr/0012-mantener-el-almacen-en-el-disco-efimero-de-la-instancia-hasta-cerrar-r-06.md)).

| | |
|---|---|
| Sistema | https://quantia-utb.onrender.com |
| API y *health check* | https://quantia-utb-api.onrender.com/health → `200 {"status":"ok"}`. La raíz de la API responde 404 porque no existe `GET /` |
| Comprobación desde fuera de la universidad | 2026-09-27, 18:59 (−05:00), internet residencial en Cartagena: sitio `http=200 tiempo=0,37 s` · API `health=200 tiempo=0,20 s` |
| Infraestructura como código | [`render.yaml`](render.yaml) (producción, Blueprint de Render) · [`docker-compose.yml`](docker-compose.yml) (local) · [`backend/Dockerfile`](backend/Dockerfile) · [`frontend/Dockerfile`](frontend/Dockerfile) · [`ci.yml`](.github/workflows/ci.yml) |
| Cómo recrearlo | [Cómo se despliega](#cómo-se-despliega) |
| Pipeline | [Runs de `master`](https://github.com/ISCOUTB/AS_202620_Sistema-de-calificacion-automatica/actions/workflows/ci.yml?query=branch%3Amaster). Render solo despliega un commit cuyo CI terminó en verde |
| Logs estructurados | Una línea JSON por evento, con `logging.config.dictConfig`, en [`backend/infraestructura/registro.py`](backend/infraestructura/registro.py). Líneas reales abajo |
| Métrica y escenario | `duracion_confirmacion_ms` del evento `lote_confirmado` ↔ [EC-07](docs/arc42/arc42-template-ES.md#ec-07) (confirmación ≤ 10 s, 0 % de pérdida). En una carga real desde el sitio: 14,1 ms |
| Secretos | Ninguno en el código: [`.env.example`](.env.example) para lo local; en Render, `REDIS_URL` la inyecta la plataforma desde la cola (`fromService`) |
| Costo mensual | US$0 al volumen supuesto. Primer punto de ruptura: las 750 h de instancia al mes del workspace, de las que la API despierta gasta 720 a 744; un segundo servicio web despierto lo rompe ([estimación](docs/despliegue/costo-mensual.md)) |
| arc42 | [§7 Deployment View](docs/arc42/arc42-template-ES.md#7-deployment-view) · [§2.2, RNF-16](docs/arc42/arc42-template-ES.md#22-restricciones-organizativas) |
| ADR de plataforma | [0009](docs/adr/0009-desplegar-la-api-en-el-servicio-web-gratuito-de-render-y-mantenerla-despierta.md) API · [0010](docs/adr/0010-servir-el-sitio-como-archivos-estaticos-en-render.md) sitio · [0011](docs/adr/0011-consumir-la-cola-desde-la-instancia-de-la-api-con-el-key-value-gratuito.md) cola y worker · [0012](docs/adr/0012-mantener-el-almacen-en-el-disco-efimero-de-la-instancia-hasta-cerrar-r-06.md) ficheros |
| Taller de despliegue | Condición: **patrón de carga**, definida por el equipo por indicación del docente. Pieza: **la API**. Arranque en frío medido: **12,5 s** frente a los 10 s de EC-07; con el monitor que la mantiene despierta, 0,2 a 0,4 s ([comparación](docs/despliegue/taller-despliegue-api.md) · [medición](docs/evidencia/medicion-arranque-en-frio.json) · [ADR-0009](docs/adr/0009-desplegar-la-api-en-el-servicio-web-gratuito-de-render-y-mantenerla-despierta.md)) |

Líneas reales del log en el entorno desplegado (worker y API):

    {"momento": "2026-09-27T21:58:41.572+00:00", "nivel": "INFO", "registro": "worker", "mensaje": "Hoja recibida", "evento": "hoja_recibida", "trabajo": "a3691012-4b72-45f4-a1a7-9446b2ff5cc6", "examen": "prueba-s8", "archivo": "mapa-del-codigo-omr.png", "referencia": "prueba-s8/f372843d-f673-47ab-8edf-005317e54ffd-mapa-del-codigo-omr.png"}
    {"momento": "2026-09-27T21:58:41.573+00:00", "nivel": "INFO", "registro": "api", "mensaje": "Lote confirmado", "evento": "lote_confirmado", "examen": "prueba-s8", "hojas_aceptadas": 1, "hojas_pendientes_de_encolar": 0, "hojas_rechazadas": 0, "duracion_confirmacion_ms": 14.1}

## Cómo se arranca

Requiere Docker (con el plugin Compose). Antes de la primera vez, copiar `.env.example` a `.env`.
Solo hace falta editarlo para probar la ruta de distractores: ahí va `LLM_API_KEY`, la clave del
proveedor de LLM, que nunca se versiona (RNF-11). Sin ella, esa ruta responde 503 y lo demás
funciona igual.

Desde la raíz del repositorio:

```
docker compose up
```

Levanta, con un solo comando, la aplicación web (FastAPI, puerto 8000), un worker que comparte
el mismo código de dominio que la API, la cola de trabajos (Redis), la base de datos (Postgres,
todavía sin esquema) y el frontend (Flutter compilado a estáticos, servido en el puerto 8080).
La primera construcción es lenta por el SDK de Flutter de la etapa de build del frontend; no
está colgado. Para reconstruir tras cambiar código: `docker compose up --build`.

- API: http://localhost:8000 (documentación interactiva en `/docs`, salud en `/health`).
- Frontend: http://localhost:8080.

Alternativas para desarrollo, que no reemplazan el comando oficial de arriba:
- Backend sin Docker: `docker compose up -d redis postgres` y luego, dentro de `backend/` con un
  entorno virtual, `pip install -r requirements.txt` y `uvicorn api.main:app --reload`.
- Frontend con recarga en caliente: dentro de `frontend/`,
  `flutter run -d chrome --dart-define=BACKEND_URL=http://localhost:8000`, sin reconstruir la
  imagen en cada cambio.

## Cómo se despliega

El entorno de demostración se recrea desde [`render.yaml`](render.yaml) en cualquier cuenta de
Render, sin depender de la de un integrante ([ADR-0009](docs/adr/0009-desplegar-la-api-en-el-servicio-web-gratuito-de-render-y-mantenerla-despierta.md)).

1. Crear una cuenta en Render iniciando sesión con GitHub; la capa gratuita no pide tarjeta.
2. En Render: *New → Blueprint*, conectar GitHub y elegir este repositorio, rama `master`. Render lee
   `render.yaml` y propone tres servicios: `quantia-utb-api` (servicio web, Docker), `quantia-utb-cola`
   (Key Value) y `quantia-utb` (sitio estático). Aplicar.
3. Esperar a que terminen las construcciones: la API construye `backend/Dockerfile`; el sitio descarga
   Flutter 3.44.3 y compila `frontend/`.
4. Si Render asignó URL distintas (cuando un nombre ya está tomado le agrega un sufijo), poner las
   reales en `ALLOWED_ORIGIN` (servicio de la API) y `BACKEND_URL` (sitio) de `render.yaml`, y volver a
   desplegar el sitio: la URL de la API queda horneada al compilar.
5. Crear en UptimeRobot, en su plan gratuito, un monitor HTTP(s) a `https://quantia-utb-api.onrender.com/health` (o a la URL que Render le haya asignado a la API) cada
   5 minutos. Mantiene despierta la API, que en frío tarda 12,5 s en responder.
6. Comprobar desde fuera de la universidad que el sitio y el `/health` de la API responden 200,
   cargar una hoja sintética desde el sitio y buscar en los logs de `quantia-utb-api` los eventos
   `lote_confirmado` y `hoja_recibida`.

Desde ahí, cada commit a `master` cuyo CI termina en verde redespliega solo el servicio cuya
carpeta cambió (`backend/` o `frontend/`).

## Corte vertical: carga de examen (aspecto A-01)

Del sistema hay **un aspecto construido de punta a punta** y los demás solo declarados. Ese es
[A-01, la carga de examen para calificación](docs/aspectos.md#a-01), que realiza RF-01: el
docente sube las hojas escaneadas de un examen y el sistema le confirma cuáles recibió y cuáles
no, con el motivo de cada rechazo.

Se eligió construir este primero porque es el punto de entrada del flujo —sin una hoja cargada
no hay nada que calificar— y porque no depende de las partes de mayor riesgo técnico: no hace
falta haber elegido el algoritmo de OMR ni el umbral de confianza para que funcione.

El recorrido atraviesa todas las capas, que es lo que lo hace un corte vertical y no una capa
horizontal:

```
navegador (Flutter)  ->  POST /examenes/{id}/hojas  ->  ingesta         (valida formato)
                                                    ->  infraestructura (almacena y encola)
                                                    ->  worker          (desencola y registra)
```

### Cómo recorrerlo

Con el sistema levantado (`docker compose up --build`), crea dos archivos de prueba: uno válido
y otro que finja serlo.

```bash
# una imagen PNG valida de 8x8 pixeles (o usa cualquier foto, escaneo o PDF propio)
base64 -d > /tmp/hoja-real.png <<'FIN'
iVBORw0KGgoAAAANSUhEUgAAAAgAAAAICAIAAABLbSncAAAAEUlEQVR4nGOQqziBFTEMLQkABkZXgRDDjAEAAAAASUVORK5CYII=
FIN

# un archivo de texto al que solo se le puso extension .jpg
echo "esto no es una imagen" > /tmp/hoja-falsa.jpg
```

En `http://localhost:8080`, escribe un identificador de examen (por ejemplo `CALC-2026-01`),
selecciona los dos archivos y súbelos. La respuesta separa lo recibido de lo rechazado:

```
Se procesaron 2 archivo(s)
Recibidas: 1
  hoja-real.png    En cola · trabajo 2eede6b8-dd9f-4db6-a3ab-6205644ea416
Rechazadas: 1
  hoja-falsa.jpg   El contenido no corresponde a un JPG; puede que el archivo
                   esté dañado o que se le haya cambiado la extensión.
```

Ese rechazo es el que muestra que la validación **lee los primeros bytes y no la extensión**: el
archivo se llama `.jpg` y aun así no pasa. Comprobarlo importa porque un archivo que se cuela
por tener el nombre correcto reaparece como error dentro del worker, cuando ya no hay a quién
avisarle.

Para ver el otro extremo del recorrido:

```
docker compose logs worker
```

```
Hoja recibida | trabajo=2eede6b8-dd9f-4db6-a3ab-6205644ea416 examen=CALC-2026-01
               archivo=hoja-real.png referencia=CALC-2026-01/e6c7e4cc-...-hoja-real.png
```

El identificador de trabajo es el mismo que muestra la pantalla. Esa coincidencia es la prueba
de que el recorrido se completó: la hoja pasó del navegador a la API, de ahí al volumen de
imágenes y a la cola de Redis, y de ahí a un proceso distinto en otro contenedor.

### Qué falta de este aspecto

El worker registra la hoja y ahí termina, porque el paso siguiente es el aspecto A-02 (detección
de marcas), que todavía no existe. La política de retención de imágenes que exige RNF-14 tampoco
está implementada: hoy nada borra lo que se guarda.

El almacenamiento y la bitácora de recepción están **detrás de sendos puertos** en
`infraestructura`, con adaptadores en disco declarados provisionales. Es deliberado: el corte
necesitaba guardar archivos sin cerrar de paso la decisión de persistencia, que sigue abierta
como riesgo R-06 del arc42. Cuando se escriba ese ADR, lo que cambia son los adaptadores;
`ingesta`, el modelo de datos y las pruebas del aspecto no se tocan.

El reintento de las hojas que quedaron `pendiente_de_encolar` **no está automatizado**:
`bitacora.pendientes()` deja el dato listo y consumirlo es trabajo del aspecto A-02.

## Cómo se prueba

Backend (dentro de `backend/`, con Redis disponible vía `docker compose up -d redis` o local):

```
pytest
```

Son 106. Verifican: que la aplicación FastAPI arranca y su endpoint de salud responde
200; que los siete módulos del dominio se importan sin error ni ciclos; que ningún módulo
importa por fuera de lo declarado en el docstring de su `__init__.py` (la prueba de fronteras
entre módulos); que un trabajo encolado en Redis se recupera igual al desencolarlo; y, para el
aspecto A-01, que se aceptan los formatos declarados, que cada rechazo lleva motivo legible, que
ningún archivo del lote desaparece del reporte, que se encola un trabajo por hoja aceptada y
ninguno por rechazada, y que un nombre de archivo con rutas no escapa del directorio del examen.

Trece de ellas llegaron con [ADR-0006](docs/adr/0006-registrar-la-recepcion-en-una-bitacora-antes-de-encolar.md)
y cubren el caso que rompía EC-07: la cola que se cae con el lote a medio procesar. Verifican que
ninguna hoja queda sin reportar, que la que no se encoló queda pendiente en la bitácora con su
imagen recuperable, que el estado se relee desde el archivo y no de la memoria, que una línea
truncada no inutiliza el registro, y que el lote deja de insistir contra una cola caída en vez de
pagar el tiempo de espera de conexión doscientas veces.

Cuarenta y cuatro llegaron con la porción de la S9 (aspecto A-06). Verifican que ninguna
propuesta que repita la respuesta correcta llega al profesor, aunque esté escrita distinto; que
al proveedor de LLM solo le llega la pregunta (RNF-13); que el tiempo agotado, la cuota agotada,
la clave rechazada y una respuesta ilegible terminan en un 503 con su motivo; y que ningún
módulo del dominio importa `api` ni `worker`. Ninguna sale a la red.

Seis son la **prueba de contrato** ([`backend/tests/test_contrato.py`](backend/tests/test_contrato.py)),
y verifican que el documento de `docs/contrato/openapi.json` y la API que corre no se puedan
separar: que el archivo versionado sea exactamente el que genera la aplicación de hoy, que su
número de versión sea el declarado en el código, que sigan estando las dos rutas, que la
respuesta de carga exija sus cuatro campos, que los estados publicados sean los dos del dominio,
y que una respuesta real traiga exactamente los campos que el contrato anuncia, ni uno más ni
uno menos.

Un cambio incompatible las pone en rojo diciendo qué se rompió. Renombrar `nombre_archivo`
produce:

```
El contrato versionado ya no describe a esta aplicacion:
  esquema cambiado: HojaAceptadaEnRespuesta (campos quitados: ['nombre_archivo']; nuevos: ['archivo'])
```

Que falla de verdad no es una afirmación: se comprobó rompiendo el contrato en `master` y
mirando el pipeline. El experimento, con los tres runs y la salida completa, está en
[`docs/evidencia/prueba-de-contrato-falla.md`](docs/evidencia/prueba-de-contrato-falla.md).

Tres más verifican que la herramienta que mide EC-07 siga corriendo contra el código de hoy
([`backend/tests/test_medir_ec07.py`](backend/tests/test_medir_ec07.py)). La herramienta es la
evidencia reproducible del escenario, y ya dejó de correr una vez sin que nada lo detectara.

Sin Redis levantado, la prueba de encolado se salta con un mensaje que dice qué levantar, en vez
de fallar con un error de conexión confuso. Las demás corren igual.

La prueba de contrato lee `docs/contrato/openapi.json` desde la raíz del repositorio, así que se
corre fuera de la imagen, como la corre el pipeline. Dentro de un contenedor construido desde
`backend/` (por ejemplo, con `docker compose run api pytest`) ese archivo no existe y sus seis
pruebas terminan en error.

Frontend (dentro de `frontend/`):

```
flutter test
```

Son 6 pruebas de widget. Verifican que la pantalla de inicio refleja el estado de conexión con
el backend y que no ofrece cargar hojas si el backend no responde; y, sobre la pantalla de
carga, que el botón de subir sigue deshabilitado hasta que haya examen y archivos, que el
reporte lista las aceptadas y las rechazadas con su motivo, y que una falla de red se muestra
como aviso y no como rechazo.

Ninguna toca la red ni el diálogo de archivos del navegador: la pantalla recibe esas dos
operaciones inyectadas y las pruebas les pasan sustitutos.

Estas mismas pruebas corren en cada push y pull request vía `.github/workflows/ci.yml`.

### Cómo se mide el escenario EC-07

Las dos cifras del escenario (confirmación del lote en ≤10 s y 0 % de pérdida silenciosa) se
miden con una herramienta versionada, sin Docker ni Redis:

```
cd backend
python -m herramientas.medir_ec07 --hojas 200 --kb 200 --repeticiones 3 --fallar-en 100
```

El resultado, el procedimiento y sus límites están en
[`docs/evidencia/medicion-ec07.md`](docs/evidencia/medicion-ec07.md).

## El contrato de la API

Lo que la API promete devolver está escrito en un documento OpenAPI versionado en el
repositorio: [`docs/contrato/openapi.json`](docs/contrato/openapi.json), en la versión 1.1.0.
Describe las tres rutas con el esquema de cada respuesta campo por campo, no solo el listado de
endpoints.

Está versionado y no se consulta en caliente por dos razones. `/openapi.json` solo existe
mientras la API está levantada y describe la versión que esté corriendo en ese momento, así que
ni un consumidor que quiera generar su cliente ni un revisor que quiera ver qué prometía la API
en un commit dado pueden usarlo. Y con el documento dentro del repositorio, un cambio
incompatible deja de ser invisible: aparece como un diff en ese archivo.

**No se edita a mano.** Se genera desde la aplicación con una herramienta versionada, igual que
las cifras de EC-07:

```
cd backend
python -m herramientas.exportar_contrato
```

La salida es determinista (claves ordenadas, indentación fija), de modo que dos exportaciones
del mismo código producen el mismo archivo. Si tras regenerar el diff sale vacío, el contrato no
cambió; si sale con cambios, hay que revisarlos uno por uno antes de commitear, porque un campo
que desaparece o un tipo que se estrecha rompen a quien ya consume la API.

`docs/contrato/` guarda documentos de contrato generados, uno por interfaz. Hoy solo está la
interfaz HTTP; la del sistema con la cola de trabajos todavía no está descrita.

## Restricciones y decisiones clave

Las restricciones completas, clasificadas en técnicas, organizativas y legales, están en la [sección 2 del arc42](docs/arc42/arc42-template-ES.md). Las principales:

- Solo evalúa exámenes de opción múltiple con hoja de respuestas de formato fijo; no procesa desarrollo libre.
- Dominio acotado a cálculo diferencial: límites, derivadas y simplificaciones algebraicas.
- Usuarios: profesores y TAs autenticados. El estudiante no interactúa con el sistema, solo es la fuente de las marcas en la hoja.
- Los resultados se presentan en un dashboard interactivo, no como archivo aislado ni salida de consola.
- Las calificaciones y los escaneos son datos personales de estudiantes: su tratamiento se rige por el régimen colombiano de protección de datos, y ningún dato personal se envía al proveedor de LLM.
- El stack está limitado a las opciones del curso. Se eligió FastAPI en el backend, porque el ecosistema de OpenCV solo existe con madurez en Python, y Flutter en el frontend, por la experiencia previa del equipo.
- El modelo de lenguaje no participa en la calificación: es una capacidad de apoyo de la fase de autoría, y el sistema funciona completo sin invocarla ([ADR-0005](docs/adr/0005-acotar-el-llm-a-la-generacion-de-distractores-diagnosticos.md)).

## Objetivos de calidad

- **Precisión:** ≥98% de exactitud en la detección de marcas OMR; 100% de los exámenes habilitados con aprobación manual registrada de la clave de respuestas.
- **Rendimiento:** ≤5 segundos por examen individual (percentil 95); requiere procesamiento en paralelo, no secuencial, para que un lote de 200 hojas quepa en ≤10 minutos.
- **Degradación controlada:** toda marca con confianza <70% se envía a revisión manual; el sistema detecta correctamente ≥99% de esos casos ambiguos.
- **Seguridad:** un profesor solo accede a los datos de los cursos que tiene autorizados.

## Metodología

El desarrollo sigue Aspect Driven Development (ADD): cada funcionalidad se declara como un aspecto que se puede trazar de principio a fin, desde el requisito hasta la evidencia de que funciona (ver [`docs/aspectos.md`](docs/aspectos.md)).

## Decisiones de arquitectura

| ADR | Título | Estado |
|---|---|---|
| [0001](docs/adr/0001-usar-monolito-modular.md) | Arquitectura de Monolito Modular | reemplazado por 0002 |
| [0002](docs/adr/0002-procesar-calificacion-de-forma-asincrona.md) | Procesar la calificación de forma asíncrona sobre el monolito modular | aceptado |
| [0003](docs/adr/0003-usar-fastapi-y-flutter.md) | Usar FastAPI en el backend y Flutter en el frontend | aceptado |
| [0004](docs/adr/0004-quitar-validacion-simbolica-obligatoria-de-la-clave.md) | Quitar la validación simbólica obligatoria de la clave de respuestas | aceptado |
| [0005](docs/adr/0005-acotar-el-llm-a-la-generacion-de-distractores-diagnosticos.md) | Acotar el LLM a la generación de distractores diagnósticos | aceptado |
| [0006](docs/adr/0006-registrar-la-recepcion-en-una-bitacora-antes-de-encolar.md) | Registrar la recepción en una bitácora antes de encolar | aceptado |
| [0007](docs/adr/0007-declarar-los-contextos-delimitados-y-la-regla-de-dueno-unico.md) | Declarar los contextos delimitados y la regla de dueño único de los datos | aceptado |
| [0008](docs/adr/0008-renombrar-el-sistema-a-quantia.md) | Renombrar el sistema a QuantIA | aceptado |
| [0009](docs/adr/0009-desplegar-la-api-en-el-servicio-web-gratuito-de-render-y-mantenerla-despierta.md) | Desplegar la API en el servicio web gratuito de Render y mantenerla despierta | aceptado |
| [0010](docs/adr/0010-servir-el-sitio-como-archivos-estaticos-en-render.md) | Servir el sitio como archivos estáticos en Render | aceptado |
| [0011](docs/adr/0011-consumir-la-cola-desde-la-instancia-de-la-api-con-el-key-value-gratuito.md) | Consumir la cola desde la instancia de la API con el Key Value gratuito | aceptado |
| [0012](docs/adr/0012-mantener-el-almacen-en-el-disco-efimero-de-la-instancia-hasta-cerrar-r-06.md) | Mantener el almacén en el disco efímero de la instancia hasta cerrar R-06 | aceptado |
| [0013](docs/adr/0013-consumir-groq-detras-de-un-puerto-y-degradar-sin-bloquear-la-autoria.md) | Consumir Groq detrás de un puerto y degradar sin bloquear la autoría | aceptado |
| [0014](docs/adr/0014-dejar-constancia-del-ajuste-de-enlaces-en-adr-0007.md) | Dejar constancia del ajuste de enlaces en ADR-0007 | aceptado |

Las decisiones de un ADR aceptado no se editan ni se borran: si una decisión cambia, se escribe uno nuevo y el anterior pasa a estado *reemplazado por*. Los ajustes menores que no son de arquitectura, como un enlace roto, se permiten dejando constancia ([ADR-0014](docs/adr/0014-dejar-constancia-del-ajuste-de-enlaces-en-adr-0007.md)).

## Estado actual

- [x] Aspectos A-01 (carga de examen) y A-06 (distractores diagnósticos) construidos de punta a punta;
  A-02 a A-05 declarados
- [x] arc42: objetivos de calidad, restricciones clasificadas y contexto
- [x] arc42: estrategia de solución, decisiones de arquitectura y riesgos
- [x] arc42: Building Block View, Runtime View y Cross-cutting Concepts (secciones 5, 6 y 8)
- [x] arc42: Deployment View (sección 7)
- [x] Escenarios de calidad: 5 priorizados y 3 complementarios; EC-07 y EC-08 medidos
- [x] C4 Niveles 1, 2 y 3
- [x] ADR 0001 a 0014
- [x] Elección de stack: FastAPI en el backend, Flutter en el frontend
- [x] Esqueleto ejecutable
- [x] Corte vertical de A-01: `ingesta`, almacén, bitácora, encolado y pantalla de carga
- [x] Contrato de la API (OpenAPI) versionado y su prueba en el pipeline
- [x] Despliegue en Render con URL pública, logs estructurados y métrica de EC-07
- [ ] ADR de persistencia y almacenamiento (riesgo R-06); el adaptador actual es provisional
- [ ] Modelo de datos compartido más allá de lo que A-01 necesitó
- [x] Proveedor de LLM: Groq, detrás de un puerto de `autoria` (ADR-0013)
- [ ] Aspectos A-02 a A-05

## Documentación

```
docs/
├── arc42/
│   └── arc42-template-ES.md                            # documento de arquitectura (arc42)
├── adr/                                                # 0001 a 0012; el 0001, reemplazado por el 0002
├── c4/
│   └── doc-c4.md                                       # modelo C4 (Niveles 1, 2 y 3)
├── contrato/
│   └── openapi.json                                    # contrato HTTP (OpenAPI 3.1), generado
├── despliegue/                                        # estimación de costo y taller de despliegue
├── evidencia/                                          # EC-07, arranque en frío, prueba de contrato, SonarQube
├── ficha-problema.md                                   # el problema, usuarios y alcance
├── aspectos.md                                         # aspectos y tabla de trazabilidad
└── ia.md                                               # registro de uso de IA
```

En la raíz, [`correcciones.md`](correcciones.md) responde a la retroalimentación automática del
curso. El registro de uso de IA está en [`docs/ia.md`](docs/ia.md) y la ficha del problema en
[`docs/ficha-problema.md`](docs/ficha-problema.md).
