# QuantIA

QuantIA califica exámenes de opción múltiple de cálculo diferencial: el profesor registra su
banco y su clave, aplica el examen en papel y sube los escaneos; el sistema lee las marcas (OMR),
califica contra esa clave y devuelve a revisión manual toda marca dudosa. Como apoyo opcional,
propone **distractores diagnósticos** con un modelo de lenguaje. Apoya el criterio del profesor,
no lo reemplaza.

## Equipo

Sebastián Cañas Plata (`scp1109`) · Josué David Ortega De Arco (`josueacademico17-source`) ·
María Del Mar Restrepo Licona (`Mariadelmar-restrepo`) · Susana Marcela Rosales Castellar
(`SusanaRosales`).

## Entorno desplegado

| Pieza | URL |
|---|---|
| Sitio (frontend) | https://calificacion.iscoutb.dev |
| API | https://api-calificacion.iscoutb.dev · salud en `/health` · métricas en `/metricas` |
| Revisión desplegada | https://calificacion.iscoutb.dev/revision.txt |

En el servidor del laboratorio del curso, desde `deploy/compose.lab.yaml`. El panel lee la rama
`despliegue`, que el CI publica solo si las pruebas pasan ([ADR-0021](docs/adr/0021-desplegar-en-el-servidor-del-laboratorio-con-el-sitio-compilado-en-el-ci.md)).
Detalle en [Entorno desplegado, en detalle](#entorno-desplegado-en-detalle).

## Evidencia del final

- **Base de datos (ADR-0027):** la bitácora, los resultados y las revisiones en Postgres, detrás de
  los mismos puertos; lo que había en archivos pasa a la base sin cambios
  (`docs/evidencia/base-de-datos.md`).
- **Inicio de sesión (ADR-0025):** correo y contraseña de una lista cifrada en el servidor; sin
  sesión, las rutas de datos responden 401.
- **Clave desde la aplicación (ADR-0026):** se registra y se habilita en Pauta a nombre del
  docente, y no cambia después de la primera nota.
- **Revisión con la opción ya elegida (ADR-0024):** la única marca con 40 o más de confianza llega
  elegida; en las fotos, 25 de 28 bien y 0 equivocadas, y 0 en 1 163 preguntas sintéticas.

## Lectura y calificación de las hojas (A-02, A-03)

- **Construidas**, con la revisión manual de las preguntas dudosas (RF-08), en
  `docs/adr/0023-…`. Sobre 300 hojas sintéticas: EC-01, 100 % de marcas claras bien
  leídas (pide ≥98 %); EC-02, 100 % de las ambiguas a revisión (pide ≥99 %); 0 errores silenciosos.
  EC-03, p95 de 1,7 s por hoja (pide ≤5 s); EC-04, 200 hojas en 3,6 min (pide ≤10 min).
- **Salvedades:** hojas sintéticas, no las escaneadas de R-01; umbral sin calibrar con hojas reales
  (R-04); solo hojas sintéticas hasta que existan los cursos (AM-02).

| Qué | Dónde |
|---|---|
| Decisión, con sus alternativas | [ADR-0023](docs/adr/0023-leer-las-hojas-en-posiciones-fijas-y-mandar-a-revision-lo-que-no-se-ve-bien.md) |
| Medición de EC-01 a EC-04, el prototipo, RF-08 con las fotos y la memoria del worker | [`medicion-lectura-omr.md`](docs/evidencia/medicion-lectura-omr.md) |
| Los siete pasos de A-02 y A-03 | [`docs/aspectos.md`](docs/aspectos.md#a-02) |
| Los recorridos | [arc42 §6.8 y §6.9](docs/arc42/arc42-template-ES.md#68-lectura-y-calificación-de-una-hoja-rf-02-a-rf-05--a-02-y-a-03--adr-0023) |
| Código | `backend/omr/`, `backend/calificacion/`, `backend/dashboard/`, `backend/worker/main.py` |
| Cómo probarlo en un computador | [Cómo se recorre la lectura](#cómo-se-recorre-la-lectura) |

## Dónde está la evidencia

La documentación vive en `docs/`. Esta tabla dice dónde está cada cosa.

| Qué | Dónde |
|---|---|
| La arquitectura completa | [arc42](docs/arc42/arc42-template-ES.md) · [C4, Niveles 1 a 3](docs/c4/doc-c4.md) · [27 ADR](docs/adr/) |
| Los aspectos y su trazabilidad | [`docs/aspectos.md`](docs/aspectos.md#tabla-de-trazabilidad) |
| La lectura y la calificación: EC-01 a EC-04 | [`medicion-lectura-omr.md`](docs/evidencia/medicion-lectura-omr.md) · [`medicion-s14.md`](docs/evidencia/medicion-s14.md), tres repeticiones |
| La preselección en la revisión | [`preseleccion-omr.md`](docs/evidencia/preseleccion-omr.md) |
| La recepción sin pérdida: EC-07 | [`medicion-ec07.md`](docs/evidencia/medicion-ec07.md) |
| Los distractores con IA: EC-08 | [`evaluacion-distractores.md`](docs/evidencia/evaluacion-distractores.md) · [`auditoria-s9.md`](docs/evidencia/auditoria-s9.md) |
| El límite de costo del proveedor: EC-09 | [`experimento-presupuesto.md`](docs/evidencia/experimento-presupuesto.md) |
| Los modos de fallo y la cola | [`modos-de-fallo.md`](docs/evidencia/modos-de-fallo.md) · [`taller-mensajeria.md`](docs/evidencia/taller-mensajeria.md) |
| La consistencia de los datos y la caché | [`consistencia-y-cache.md`](docs/evidencia/consistencia-y-cache.md) |
| La base de datos | [`base-de-datos.md`](docs/evidencia/base-de-datos.md) |
| Las amenazas, las dependencias y la privacidad | [`modelo-de-amenazas.md`](docs/evidencia/modelo-de-amenazas.md) |
| El despliegue y su costo | [`despliegue-iscoutb.md`](docs/evidencia/despliegue-iscoutb.md) · [`costo-mensual.md`](docs/despliegue/costo-mensual.md) |
| El contrato de la API y su prueba | [`openapi.json`](docs/contrato/openapi.json) · [`test_contrato.py`](backend/tests/test_contrato.py) · [la prueba que falla](docs/evidencia/prueba-de-contrato-falla.md) |
| El análisis estático | [SonarQube Cloud](https://sonarcloud.io/summary/new_code?id=ISCOUTB_AS_202620_Sistema-de-calificacion-automatica) · [`hallazgos-y-correcciones.md`](docs/evidencia/hallazgos-y-correcciones.md) |
| El pipeline | [GitHub Actions](https://github.com/ISCOUTB/AS_202620_Sistema-de-calificacion-automatica/actions) |
| El uso de IA en la construcción | [`docs/ia.md`](docs/ia.md) |

## Entorno desplegado, en detalle

El servidor del laboratorio del curso, en iscoutb.dev, desde el 29-oct-2026
([ADR-0021](docs/adr/0021-desplegar-en-el-servidor-del-laboratorio-con-el-sitio-compilado-en-el-ci.md)).
Solo se cargan hojas sintéticas, nunca hojas de estudiantes (RNF-12): el servidor no hace copias de
seguridad y borra los volúmenes después del 30-nov-2026.

| | |
|---|---|
| Sitio | https://calificacion.iscoutb.dev |
| API y *health check* | https://api-calificacion.iscoutb.dev/health → `200 {"status":"ok"}`. La raíz de la API responde 404 porque no existe `GET /` |
| Revisión desplegada | https://calificacion.iscoutb.dev/revision.txt: el commit de `master` que está corriendo, escrito por el CI al compilar el sitio |
| Comprobación desde fuera de la universidad | 2026-10-29, de 23:30 a 00:05 (−05:00), internet residencial: `/health` con mediana de 0,28 s y p95 de 0,53 s en 30 peticiones; el sitio, CORS y los certificados, bien ([evidencia](docs/evidencia/despliegue-iscoutb.md)) |
| Infraestructura como código | [`deploy/compose.lab.yaml`](deploy/compose.lab.yaml) (servidor) · [`deploy/sitio/Dockerfile`](deploy/sitio/Dockerfile) · [`docker-compose.yml`](docker-compose.yml) (local) · [`backend/Dockerfile`](backend/Dockerfile) · [`ci.yml`](.github/workflows/ci.yml) |
| Cómo recrearlo | [Cómo se despliega](#cómo-se-despliega) |
| Pipeline | [Runs de `master`](https://github.com/ISCOUTB/AS_202620_Sistema-de-calificacion-automatica/actions/workflows/ci.yml?query=branch%3Amaster). Si las pruebas pasan, el job `publicar-despliegue` compila el sitio y publica la rama `despliegue`, que es la que despliega el panel |
| Recursos | 4 de los 6 contenedores de la cuota (`api`, `worker`, `redis` con AOF y `web`) y 576 MB de 1 GB, con límites medidos |
| Logs estructurados | Una línea JSON por evento, con `logging.config.dictConfig`, en [`backend/infraestructura/registro.py`](backend/infraestructura/registro.py). Líneas reales abajo |
| Métrica y escenario | `duracion_confirmacion_ms` del evento `lote_confirmado` ↔ [EC-07](docs/arc42/arc42-template-ES.md#ec-07) (confirmación ≤ 10 s, 0 % de pérdida). En la primera carga en este servidor: 7,9 ms. El presupuesto del proveedor de LLM, en https://api-calificacion.iscoutb.dev/metricas (EC-09) |
| Seguimiento de un mensaje | `trabajo_publicado` en la API, `trabajo_tomado` y `hoja_recibida` en el worker, con el mismo `trabajo` y la misma `hoja`, juntados por `herramientas/seguir_trabajo.py` ([evidencia](docs/evidencia/despliegue-iscoutb.md)) |
| Secretos | Ninguno en el código: [`.env.example`](.env.example) para lo local y [`deploy/.env.example`](deploy/.env.example) para el servidor. En el panel, *Environment* guarda `ALLOWED_ORIGIN` y `LLM_API_KEY`, y el compose las lee como `${VARIABLE}` |
| Costo mensual | US$0 para el equipo: el servidor lo paga el curso. La parte que nos corresponde, con la lista de precios de Oracle, es de unos US$2 al mes; lo primero que se rompe es la CPU de la API con cinco lotes a la vez ([estimación](docs/despliegue/costo-mensual.md)) |
| arc42 | [§7 Deployment View](docs/arc42/arc42-template-ES.md#7-deployment-view) · [§2.2, RNF-16](docs/arc42/arc42-template-ES.md#22-restricciones-organizativas) |
| ADR de plataforma | [0021](docs/adr/0021-desplegar-en-el-servidor-del-laboratorio-con-el-sitio-compilado-en-el-ci.md), que reemplaza a 0009 a 0012 |

Líneas reales del log en el entorno desplegado (API y worker; el panel muestra el de cada
contenedor por separado):

    {"momento": "2026-10-30T04:38:08.792+00:00", "nivel": "INFO", "registro": "ingesta", "mensaje": "Trabajo publicado", "evento": "trabajo_publicado", "trabajo": "b4f7061e-4444-4f6e-a132-f8e929c38047", "hoja": "ff64200e-7ffc-4b60-ae67-28fe3b1b0c68", "examen": "Calculo 2", "cola": "procesamiento"}
    {"momento": "2026-10-30T04:38:08.793+00:00", "nivel": "INFO", "registro": "worker", "mensaje": "Hoja recibida", "evento": "hoja_recibida", "trabajo": "b4f7061e-4444-4f6e-a132-f8e929c38047", "hoja": "ff64200e-7ffc-4b60-ae67-28fe3b1b0c68", "intento": 1, "examen": "Calculo 2", "archivo": "hoja-real.png", "referencia": "Calculo_2-20b4f352/35158635-8806-469c-8522-416de15e71e2-hoja-real.png", "bytes": 74}
    {"momento": "2026-10-30T04:38:08.793+00:00", "nivel": "INFO", "registro": "api", "mensaje": "Lote confirmado", "evento": "lote_confirmado", "examen": "Calculo 2", "hojas_aceptadas": 1, "hojas_pendientes_de_encolar": 0, "hojas_rechazadas": 1, "duracion_confirmacion_ms": 7.9}

## Cómo se arranca

Requiere Docker (con el plugin Compose). Antes de la primera vez, copiar `.env.example` a `.env` y
llenar `SESION_SECRETO` (un texto largo al azar) y `DOCENTES`, con la línea de cada cuenta que
imprime `python -m herramientas.crear_docente correo` desde `backend/` (ADR-0025): sin ellas nadie
puede entrar. `LLM_API_KEY`, la clave del proveedor de LLM, solo hace falta para la ruta de
distractores y nunca se versiona (RNF-11); sin ella, esa ruta responde 503 y lo demás funciona
igual. `LLM_SOLICITUDES_POR_MINUTO` y `LLM_SOLICITUDES_POR_DIA` son el presupuesto del proveedor
(ADR-0015) y no hace falta tocarlas.

Desde la raíz del repositorio:

```
docker compose up
```

Levanta, con un solo comando, la aplicación web (FastAPI, puerto 8000), un worker que comparte
el mismo código de dominio que la API, la cola de trabajos (Redis), la base de datos (Postgres,
con la bitácora, los resultados y las revisiones; ADR-0027) y el frontend (Flutter compilado a estáticos, servido en el puerto 8080).
La primera construcción es lenta por el SDK de Flutter de la etapa de build del frontend; no
está colgado. Para reconstruir tras cambiar código: `docker compose up --build`.

- API: http://localhost:8000 (documentación interactiva en `/docs`, salud en `/health`).
- Frontend: http://localhost:8080.

### Cómo se recorre la lectura

Para que una hoja salga con nota, su examen necesita una clave habilitada. Se registra y se
habilita en la pantalla Pauta & IA, después de entrar con una cuenta de `DOCENTES` (ADR-0025 y
ADR-0026): la cuadrícula de respuestas, o las letras pegadas de una vez, y el botón «Habilitar».

En Git Bash, estos comandos llevan `MSYS_NO_PATHCONV=1` delante, porque Git Bash cambia las rutas
que empiezan con `/` antes de pasárselas a Docker. En PowerShell, cmd, Linux o macOS van tal cual.

La hoja para imprimir sale de la misma definición con que se lee. Este semestre es la única: la
v1, en carta y al 100 %, con hasta 40 preguntas de A a D (ADR-0023, punto 1):

```
docker compose exec api python -c "from omr.plantilla import plantilla_pdf; open('/tmp/plantilla-v1.pdf','wb').write(plantilla_pdf())"
docker compose cp api:/tmp/plantilla-v1.pdf plantilla-v1.pdf
```

Después: se marca, se le toma una foto con la hoja ocupando casi toda la imagen y sin luz directa, y
en http://localhost:8080 se elige el examen de la lista y se sube la foto. La nota aparece junto al
archivo en unos segundos; si quedó «En revisión», el botón «Revisar» lleva a la pantalla de
revisión. Lo que hace cada paso está en el [arc42 §6.8 y §6.9](docs/arc42/arc42-template-ES.md#68-lectura-y-calificación-de-una-hoja-rf-02-a-rf-05--a-02-y-a-03--adr-0023).

Alternativas para desarrollo, que no reemplazan el comando oficial de arriba:
- Backend sin Docker: `docker compose up -d redis postgres` y luego, dentro de `backend/` con un
  entorno virtual, `pip install -r requirements.txt` y `uvicorn api.main:app --reload`.
- Frontend con recarga en caliente: dentro de `frontend/`,
  `flutter run -d chrome --dart-define=BACKEND_URL=http://localhost:8000`, sin reconstruir la
  imagen en cada cambio.

## Cómo se despliega

El entorno desplegado es el servicio `sistema` del proyecto `calificacion` en el panel del servidor
del laboratorio (https://panel.iscoutb.dev), al que entra cualquier integrante con su correo
institucional ([ADR-0021](docs/adr/0021-desplegar-en-el-servidor-del-laboratorio-con-el-sitio-compilado-en-el-ci.md)).
Desde la red de la UTB no abre, porque ahí `*.iscoutb.dev` no resuelve. Para dejarlo configurado
desde cero:

1. En el panel, proyecto `calificacion` → `production` → `sistema`, pestaña **General → Provider**:
   este repositorio, rama `despliegue` y *Compose Path* `./deploy/compose.lab.yaml`. **Save**.
2. **Environment**: `ALLOWED_ORIGIN=https://calificacion.iscoutb.dev` y `LLM_API_KEY` con la clave de
   Groq, que no se versiona. *Create Environment File* encendido. **Save**.
3. **Domains**, dos dominios con HTTPS y Let's Encrypt: `calificacion.iscoutb.dev` al servicio `web`,
   puerto 8080, y `api-calificacion.iscoutb.dev` al servicio `api`, puerto 8000.
4. **General**: *Autodeploy* encendido y **Deploy**. En **Deployments**, esperar *Done*.
5. Comprobar desde fuera de la universidad el `/health` de la API, el sitio y `revision.txt`;
   cargar una hoja sintética desde el sitio y seguirla con `herramientas/seguir_trabajo.py` en los
   **Logs** de `api` y `worker`.

La rama `despliegue` no se edita a mano: el job `publicar-despliegue` de `ci.yml` la vuelve a crear
en cada push a `master` cuyas pruebas pasan, como `master` más el sitio compilado. Desde ahí, cada
push así se despliega solo. Los pasos para levantar el compose del servidor en un computador están
en el encabezado de [`deploy/compose.local-override.yaml`](deploy/compose.local-override.yaml).

## Corte vertical: carga de examen (aspecto A-01)

Del sistema hay **cinco aspectos construidos de punta a punta**, y A-05 en parte. Los otros son
A-06, los [distractores diagnósticos](docs/aspectos.md#a-06); A-02 y A-03, la
[lectura y la calificación](#lectura-y-calificación-de-las-hojas-a-02-a-03); y A-04, la clave desde
la aplicación. Este es
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

### Lo que queda de este aspecto

Desde A-02, el worker no termina al registrar la hoja: la lee y la califica, y la nota aparece en
la misma pantalla de carga ([cómo se recorre](#cómo-se-recorre-la-lectura)). La política de
retención de imágenes que exige RNF-14 no está implementada: hoy nada borra lo que se guarda.

El almacenamiento y la bitácora de recepción están **detrás de sendos puertos** en
`infraestructura`. Por eso, cuando la bitácora pasó a Postgres (ADR-0027), lo que cambió fue el
adaptador: `ingesta`, el modelo de datos y las pruebas del aspecto no se tocaron.

El reintento de las hojas que quedaron `pendiente_de_encolar` **no está automatizado**:
`bitacora.pendientes()` deja el dato listo, y A-02 no lo consumió (R-32).

## Cómo se prueba

Backend (dentro de `backend/`, con Redis disponible vía `docker compose up -d redis` o local):

```
pytest
```

Son 424. Verifican: que la aplicación FastAPI arranca y su endpoint de salud responde
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

Cuarenta y cuatro son de los distractores (aspecto A-06). Verifican que ninguna
propuesta que repita la respuesta correcta llega al profesor, aunque esté escrita distinto; que
al proveedor de LLM solo le llega la pregunta (RNF-13); que el tiempo agotado, la cuota agotada,
la clave rechazada y una respuesta ilegible terminan en un 503 con su motivo; y que ningún
módulo del dominio importa `api` ni `worker`. Ninguna sale a la red.

Doce llegaron con el segundo corte (EC-09, ADR-0015). Verifican que el presupuesto admite hasta su
límite por minuto y corta la siguiente, que la ventana se libera de a una solicitud, que el límite
por día corta aunque el minuto tenga cupo, que una solicitud cortada no llama al proveedor, que el
429 trae `Retry-After`, que sin proveedor configurado no se gasta cupo, y que `GET /metricas` publica
lo mismo que vio el cliente. Usan un reloj falso, así que no esperan un minuto, y tampoco salen a la
red.

Una llegó con el frontend nuevo: que el navegador puede leer `Retry-After` en el 429. CORS solo
deja leer las cabeceras que la API declara, y sin esa el sitio no sabría cuánto esperar.

Diez son de los modos de fallo (ADR-0016), casi todas en
[`backend/tests/test_modos_de_fallo.py`](backend/tests/test_modos_de_fallo.py). Contra un servidor
que acepta la conexión y no contesta, verifican que publicar se rinde en menos de 3 s, que un lote
de 100 hojas confirma dentro de los 10 s con todas pendientes en la bitácora, que el cliente de
Redis no reintenta por su cuenta, que `desencolar` no se cuelga y que el adaptador del proveedor de
LLM se corta en su espera. Contra un Redis real, que el mismo trabajo publicado dos veces se procesa
una sola vez. Y que el worker sobrevive a un fallo de Redis, que procesa igual si no puede comprobar
la marca, y que la misma solicitud de distractores repetida no deja estado y gasta su propio cupo.
Se validaron provocando la falla con siete mutaciones, que el docstring del archivo enumera.

Veintisiete llegaron con los arreglos del 19-oct. Verifican que un error
del almacén o de la bitácora rechaza esa hoja y no tumba el lote; que una cola que contesta lento
no saca el lote del techo de EC-07, porque el lote tiene un plazo además de la espera por llamada;
que el lote se confirma fuera del bucle de eventos (R-21) y se lee de a una hoja, con un tope de
20 MB; que un nombre largo se acorta y dos exámenes no comparten carpeta; que una espera vencida al
consumir llega al worker como fallo de la cola; que la API reusa un solo cliente de Redis y busca a
Redis en el mismo lugar que el worker; que el filtro de distractores iguala `2x` con `2·x` y `sen`
con `sin`, y no pierde un distractor que vale 0; y que las herramientas de medición solo cuentan lo
que dicen contar. Cada una falla si se quita su arreglo.

Diecinueve llegaron con la entrega de consistencia y caché. Seis, en
[`backend/tests/test_identidad_de_la_hoja.py`](backend/tests/test_identidad_de_la_hoja.py),
verifican que cada hoja tiene un `hoja_id` propio, distinto de su `trabajo_id`; que el reporte, la
bitácora y el trabajo de la cola dicen el mismo; que la bitácora lo conserva al releerse, también en
las líneas escritas antes (ADR-0018); y que la API lo publica. Trece, en
[`backend/tests/test_cache_de_propuestas.py`](backend/tests/test_cache_de_propuestas.py), verifican
que la pregunta repetida sale de la caché sin llamar al proveedor ni gastar cupo, y cada regla de
invalidación de ADR-0019: el cambio de modelo o de instrucciones, las 24 horas que leer no renueva,
la capacidad, «Pedir otras propuestas», que no se guardan fallas ni respuestas vacías y que la regla
corre en cada lectura. Se validaron provocando la falla con diez mutaciones, que los dos docstrings
enumeran.

Diecisiete son del presupuesto de carga (ADR-0022), en
[`backend/tests/test_presupuesto_de_carga.py`](backend/tests/test_presupuesto_de_carga.py).
Verifican que un lote con más hojas que el tope, o que no cabe en el cupo de bytes de las últimas
24 horas, no entra entero y no deja nada en el almacén, la bitácora ni la cola; que el 429 dice
cuándo cabrá contando solo los lotes que hace falta que salgan; que la ventana libera el cupo al
cumplir un día; que `GET /metricas` publica lo cargado y lo cortado; y que ningún cuerpo de más
del tope llega a la ruta, lo declare o no. Se validaron provocando la falla con seis mutaciones,
que el docstring enumera; una no pone ninguna en rojo, y el docstring dice por qué.

Doscientas once llegaron con la lectura y la calificación (A-02, A-03 y RF-08,
[ADR-0023](docs/adr/0023-leer-las-hojas-en-posiciones-fijas-y-mandar-a-revision-lo-que-no-se-ve-bien.md)).
Verifican que la plantilla y la lectura salen de la misma definición; que cada burbuja se mide
contra su papel y una sombra no inventa marcas; que una marca con brillo o una burbuja tapada no se
leen como vacías; que la hoja se lee igual girada o en perspectiva; que una dudosa o una doble marca
van a revisión y nunca a una respuesta elegida; que una imagen enorme en píxeles queda ilegible sin
decodificarse, y que una hoja que mata al worker termina en fallidos después de cuatro intentos
en vez de detener la cola; las reglas de la nota y de cada resolución del docente; que sin una clave habilitada
no hay nota; los registros de resultados y de revisiones; y que ninguna ruta publica el código del
estudiante ni la respuesta correcta, y el log tampoco. Casi todas usan hojas sintéticas generadas
en la prueba; la de las tres fotos del prototipo corre si `OMR_FOTOS_R05` apunta a ellas, y si no,
se omite.

Diez son la **prueba de contrato** ([`backend/tests/test_contrato.py`](backend/tests/test_contrato.py)),
y verifican que el documento de `docs/contrato/openapi.json` y la API que corre no se puedan
separar: que el archivo versionado sea exactamente el que genera la aplicación de hoy, que su
número de versión sea el declarado en el código, que sigan estando las doce rutas (y que la de
distractores publique su 503 y su 429), que la
respuesta de carga exija sus cuatro campos, que los estados publicados sean los dos del dominio,
que la revisión no publique la respuesta correcta,
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
`backend/` (por ejemplo, con `docker compose run api pytest`) ese archivo no existe y sus diez
pruebas terminan en error.

Frontend (dentro de `frontend/`):

```
flutter test
```

Son 105, una carpeta por pantalla en `test/features/` más `test/app_test.dart`. Las cifras por
pantalla de esta lista son de antes de A-02 y A-03, que sumaron 32: la preparación de las fotos,
la lista de exámenes, las notas junto a cada archivo y la pantalla de revisión con datos reales.

- **Marco de la aplicación (6):** la barra superior refleja el estado de conexión con el backend
  y ofrece volver a comprobar; la navegación es un riel en escritorio y una barra en teléfono; y
  cambiar de sección no pierde lo escrito en otra.
- **Carga (18):** el botón de subir sigue deshabilitado hasta que haya examen y archivos, y sin
  conexión; el reporte lista las aceptadas y las rechazadas con su motivo; una hoja
  `pendiente_de_encolar` se muestra como pendiente; una falla de red o una respuesta ilegible
  se avisan sin dar el lote por perdido ni por recibido; y un 5xx dice que algunas hojas pudieron
  entrar, sin invitar a reintentar. Cuatro de ellas prueban el servicio contra un `MockClient`,
  incluido que el examen viaje codificado en la ruta.
- **Pauta y distractores (27):** el 503 y el 429 se muestran como advertencias con el mensaje de
  la API; con el límite por minuto hay cuenta regresiva, y con el diario no se ofrece repetir y el
  botón de pedir vuelve cuando pasa la espera. Diez de ellas prueban el servicio contra un
  `MockClient`, código por código, y una, que «Pedir otras propuestas» manda `otras: true`.
- **Panel (11):** avisa que usa datos de ejemplo y no se desborda a 390 px; no ofrece acciones de
  IA fuera del alcance, y su porcentaje de aprobación no divide por cero.
- **Revisión:** tenía 11 pruebas con datos de ejemplo. Desde RF-08 usa datos reales, y sus
  pruebas verifican que abre primero la hoja con preguntas por revisar, que guarda lo que elige el
  docente con su nombre y recalcula, que una pregunta ya resuelta se puede cambiar, que avisa si el
  examen no tiene dudas o si la revisión no llega, y que no se desborda a 390 px; las del servicio,
  que cada respuesta de la API se traduce a lo que ve el docente.

Ninguna toca la red ni el diálogo de archivos del navegador: las pantallas reciben esas
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
repositorio: [`docs/contrato/openapi.json`](docs/contrato/openapi.json), en la versión 1.8.0.
Describe las nueve rutas con el esquema de cada respuesta campo por campo, no solo el listado de
endpoints. La 1.2.0 agregó `GET /metricas` y el 429 de `/distractores` (segundo corte, ADR-0015).
La 1.3.0 agregó el `hoja_id` de cada hoja aceptada (ADR-0018), y la 1.4.0, la caché de propuestas:
`otras` en la solicitud de distractores, `desde_la_cache` en su respuesta y su estado en
`/metricas` (ADR-0019). La 1.5.0 agregó el presupuesto de carga: el 413 y el 429 de la ruta de
carga y su estado en `/metricas` (ADR-0022). Con A-02 y A-03
([ADR-0023](docs/adr/0023-leer-las-hojas-en-posiciones-fijas-y-mandar-a-revision-lo-que-no-se-ve-bien.md)),
la 1.6.0 agregó `GET /examenes/{examen_id}/resultados`, la nota de cada hoja sin el código del
estudiante; la 1.7.0, `GET /examenes`, los exámenes que tienen clave, sin las respuestas; y la
1.8.0, la revisión manual (RF-08): `GET /examenes/{examen_id}/revision`, el recorte de cada
pregunta y `POST /examenes/{examen_id}/hojas/{hoja_id}/revision`, más `revisada` en los
resultados. Todas solo agregan.

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
| [0009](docs/adr/0009-desplegar-la-api-en-el-servicio-web-gratuito-de-render-y-mantenerla-despierta.md) | Desplegar la API en el servicio web gratuito de Render y mantenerla despierta | reemplazado por 0021 |
| [0010](docs/adr/0010-servir-el-sitio-como-archivos-estaticos-en-render.md) | Servir el sitio como archivos estáticos en Render | reemplazado por 0021 |
| [0011](docs/adr/0011-consumir-la-cola-desde-la-instancia-de-la-api-con-el-key-value-gratuito.md) | Consumir la cola desde la instancia de la API con el Key Value gratuito | reemplazado por 0021 |
| [0012](docs/adr/0012-mantener-el-almacen-en-el-disco-efimero-de-la-instancia-hasta-cerrar-r-06.md) | Mantener el almacén en el disco efímero de la instancia hasta cerrar R-06 | reemplazado por 0021 |
| [0013](docs/adr/0013-consumir-groq-detras-de-un-puerto-y-degradar-sin-bloquear-la-autoria.md) | Consumir Groq detrás de un puerto y degradar sin bloquear la autoría | aceptado |
| [0014](docs/adr/0014-dejar-constancia-del-ajuste-de-enlaces-en-adr-0007.md) | Dejar constancia del ajuste de enlaces en ADR-0007 | aceptado |
| [0015](docs/adr/0015-limitar-el-gasto-del-proveedor-de-llm-con-un-presupuesto-en-la-api.md) | Limitar el gasto del proveedor de LLM con un presupuesto en la API | aceptado |
| [0016](docs/adr/0016-acotar-la-espera-de-la-cola-y-hacer-idempotente-al-worker.md) | Acotar la espera de la cola y hacer idempotente al worker | aceptado |
| [0017](docs/adr/0017-no-extraer-ningun-modulo-del-monolito-todavia.md) | No extraer ningún módulo del monolito todavía | aceptado |
| [0018](docs/adr/0018-dar-a-la-hoja-una-identidad-propia-y-derivar-su-estado-de-la-bitacora.md) | Dar a la hoja una identidad propia y derivar su estado de la bitácora | aceptado |
| [0019](docs/adr/0019-guardar-en-cache-las-propuestas-de-distractores.md) | Guardar en caché las propuestas de distractores | aceptado |
| [0020](docs/adr/0020-entregar-los-trabajos-al-menos-una-vez-con-reintentos-y-lista-de-fallidos.md) | Entregar los trabajos al menos una vez, con reintentos y lista de fallidos | aceptado |
| [0021](docs/adr/0021-desplegar-en-el-servidor-del-laboratorio-con-el-sitio-compilado-en-el-ci.md) | Desplegar en el servidor del laboratorio, con el sitio compilado en el CI | aceptado |
| [0022](docs/adr/0022-poner-un-presupuesto-de-carga-delante-del-almacen.md) | Poner un presupuesto de carga delante del almacén | aceptado |
| [0023](docs/adr/0023-leer-las-hojas-en-posiciones-fijas-y-mandar-a-revision-lo-que-no-se-ve-bien.md) | Leer las hojas en posiciones fijas y mandar a revisión lo que no se ve bien | aceptado |

Las decisiones de un ADR aceptado no se editan ni se borran: si una decisión cambia, se escribe uno nuevo y el anterior pasa a estado *reemplazado por*. Los ajustes menores que no son de arquitectura, como un enlace roto, se permiten dejando constancia ([ADR-0014](docs/adr/0014-dejar-constancia-del-ajuste-de-enlaces-en-adr-0007.md)).

## Estado al cierre

- [x] Aspectos A-01 (carga de examen), A-02 (lectura de las hojas), A-03 (calificación, salvo las
  estadísticas del Panel), A-04 (la clave desde la aplicación) y A-06 (distractores diagnósticos)
  construidos de punta a punta; A-05, en parte: la entrada con sesión, sin los cursos
- [x] Documentación completa: arc42 (las doce secciones), C4 Niveles 1, 2 y 3, y ADR 0001 a 0027
- [x] Escenarios de calidad: EC-01 a EC-04 medidos tres veces sobre hojas sintéticas, y EC-07 a
  EC-09 medidos
- [x] Monolito modular con cola y worker (ADR-0002): acuse, reintentos y lista de fallidos
  (ADR-0020), esperas acotadas y worker idempotente (ADR-0016)
- [x] Lectura OMR en posiciones fijas, revisión manual de lo dudoso (ADR-0023) y preselección de la
  única marca (ADR-0024)
- [x] Inicio de sesión (ADR-0025) y la clave registrada y habilitada en la aplicación (ADR-0026)
- [x] La bitácora, los resultados y las revisiones en Postgres (ADR-0027)
- [x] Distractores con un modelo de lenguaje, detrás de un puerto, con caché y presupuesto
  (ADR-0013, ADR-0015 y ADR-0019)
- [x] Contrato de la API versionado y su prueba en el pipeline; análisis estático y de dependencias
- [x] Despliegue en el servidor del laboratorio, con el sitio compilado en el CI (ADR-0021)
- [ ] Los cursos y su aislamiento (EC-06): hasta entonces, solo hojas sintéticas (AM-02)
- [ ] Las estadísticas del Panel con los resultados reales (RF-05) y el banco de preguntas (RF-06)
- [ ] Calibrar el umbral con hojas escaneadas (R-01, R-04) y medir EC-03 y EC-04 en el servidor (R-37)
- [ ] Detectar una hoja subida dos veces (R-24) y la retención de las imágenes (RNF-14)

## Documentación

```
docs/
├── arc42/
│   └── arc42-template-ES.md                            # documento de arquitectura (arc42)
├── adr/                                                # 0001 a 0027; el 0001, reemplazado por el 0002, y del 0009 al 0012, por el 0021
├── c4/
│   └── doc-c4.md                                       # modelo C4 (Niveles 1, 2 y 3)
├── contrato/
│   └── openapi.json                                    # contrato HTTP (OpenAPI 3.1), generado
├── despliegue/                                        # estimación de costo y taller de despliegue
├── evidencia/                                          # las mediciones, los experimentos y el modelo de amenazas
├── ficha-problema.md                                   # el problema, usuarios y alcance
├── aspectos.md                                         # aspectos y tabla de trazabilidad
└── ia.md                                               # registro de uso de IA
```

En la raíz, [`correcciones.md`](correcciones.md) responde a la retroalimentación automática del
curso. El registro de uso de IA está en [`docs/ia.md`](docs/ia.md) y la ficha del problema en
[`docs/ficha-problema.md`](docs/ficha-problema.md).
