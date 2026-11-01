# Despliegue en el servidor del laboratorio (iscoutb.dev)

El 29 de octubre de 2026 QuantIA pasó de Render al servidor del laboratorio del curso. Este
documento deja la verificación: qué revisión quedó desplegada, que el sitio y la API responden desde
fuera de la universidad, el recorrido de una hoja de la API al worker en el entorno desplegado y los
límites de memoria del compose, medidos. El recorrido responde a lo que pidió el seguimiento del
docente del 26-oct: «validar el consumidor actualizado en el entorno desplegado y documentar la
revisión exacta».

- **Decisión:** [ADR-0021](../adr/0021-desplegar-en-el-servidor-del-laboratorio-con-el-sitio-compilado-en-el-ci.md).
- **Infraestructura como código:** [`deploy/compose.lab.yaml`](../../deploy/compose.lab.yaml),
  [`deploy/sitio/Dockerfile`](../../deploy/sitio/Dockerfile) y el job `publicar-despliegue` de
  [`ci.yml`](../../.github/workflows/ci.yml).
- **Sitio:** https://calificacion.iscoutb.dev · **API:** https://api-calificacion.iscoutb.dev
- **Fecha:** 2026-10-29, hora de Colombia. Los registros están en UTC, así que dicen 2026-10-30.

## 1. La revisión desplegada

| | |
|---|---|
| `master` | `6839cfd` (`ci: publicar en la rama despliegue lo que pasa las pruebas`), sobre `8ad703a` (`chore(despliegue): describir el entorno del servidor del laboratorio`) |
| CI | [Run 41001351456](https://github.com/ISCOUTB/AS_202620_Sistema-de-calificacion-automatica/actions/runs/41001351456), de 04:09:55 a 04:13:04 UTC, los tres jobs en verde: `backend-tests` (39 s), `frontend-tests` (1 min 37 s) y `publicar-despliegue` (1 min 25 s) |
| Rama `despliegue` | `5c6ccb8`, «despliegue: master en 6839cfd», del bot del CI: `master` más un commit con el sitio compilado en `deploy/sitio/web/` (38 archivos y `revision.txt`) y `.sonarcloud.properties`, que deja lo generado fuera del análisis |
| Despliegue | Panel de Dokploy, proyecto `calificacion`, servicio `sistema`: `docker compose -p calificacion-sistema-am0klk --env-file deploy/.env -f ./deploy/compose.lab.yaml up -d --build --remove-orphans`, terminado con «Docker Compose Deployed». Crea los volúmenes `almacen_imagenes` y `datos_cola`, y el worker registra `worker_iniciado` a las 04:28:42 UTC |
| Lo que dice el servidor | https://calificacion.iscoutb.dev/revision.txt → `6839cfdeb0204690d5253bb385eb4b72ee7210e2` |

`revision.txt` lo escribe el CI al compilar el sitio, así que siempre dice qué commit de `master`
está sirviendo el servidor.

## 2. Comprobación desde fuera de la universidad

Hecha el 2026-10-30 entre las 04:30 y las 05:05 UTC (29-oct, de 23:30 a 00:05 en Colombia), desde
internet residencial.

| Comprobación | Resultado |
|---|---|
| `GET https://api-calificacion.iscoutb.dev/health` | `200 {"status":"ok"}`. En 30 peticiones seguidas: mediana 0,28 s, p95 0,53 s y máximo 0,80 s |
| `GET https://api-calificacion.iscoutb.dev/metricas` | `200`: presupuesto de 6 por minuto y 150 por día, sin uso, y la caché vacía; `arrancado_en` 2026-10-30T04:28:41Z |
| `https://calificacion.iscoutb.dev` | `200`, título «QuantIA»; `main.dart.js` contiene `https://api-calificacion.iscoutb.dev`, la URL horneada al compilar |
| CORS | `OPTIONS /health` con `Origin: https://calificacion.iscoutb.dev` → `200` y `access-control-allow-origin` con ese origen; con otro origen → `400` |
| Certificados | En los dos nombres: `CN=iscoutb.dev`, emitido por Let's Encrypt, vence el 27-dic-2026 |
| Primera visita al sitio | 1 601 585 bytes con `Accept-Encoding: br, gzip`: `main.dart.js` 793 268 (Cloudflare lo sirve en brotli), las seis fuentes 803 508 (sin comprimir) y el resto 4 809. CanvasKit lo baja el navegador del CDN de Google, como en Render |

**No hay arranque en frío.** Los contenedores no se duermen, así que no hace falta el monitor que
mantenía despierta la API en Render (12,5 s en frío, R-13).

## 3. Una hoja de la API al worker, en el entorno desplegado

Desde el sitio, en *Carga*, examen «Calculo 2», se subieron dos archivos: un PNG sintético de 74
bytes, `hoja-real.png`, y un archivo inválido. El nombre lo puso quien hizo la prueba: es una imagen
sintética, no una hoja de estudiante (RNF-12). El registro se copió de la pestaña *Logs* del panel,
que muestra el de cada contenedor por separado y le antepone su marca de tiempo a las líneas del
worker:

```
worker:
2026-10-30T04:38:08.792Z {"momento": "2026-10-30T04:38:08.792+00:00", "nivel": "INFO", "registro": "worker", "mensaje": "Trabajo tomado", "evento": "trabajo_tomado", "trabajo": "b4f7061e-4444-4f6e-a132-f8e929c38047", "hoja": "ff64200e-7ffc-4b60-ae67-28fe3b1b0c68", "intento": 1, "examen": "Calculo 2", "espera_en_cola_ms": 6.1}
2026-10-30T04:38:08.793Z {"momento": "2026-10-30T04:38:08.793+00:00", "nivel": "INFO", "registro": "worker", "mensaje": "Hoja recibida", "evento": "hoja_recibida", "trabajo": "b4f7061e-4444-4f6e-a132-f8e929c38047", "hoja": "ff64200e-7ffc-4b60-ae67-28fe3b1b0c68", "intento": 1, "examen": "Calculo 2", "archivo": "hoja-real.png", "referencia": "Calculo_2-20b4f352/35158635-8806-469c-8522-416de15e71e2-hoja-real.png", "bytes": 74}

api:
{"momento": "2026-10-30T04:38:08.792+00:00", "nivel": "INFO", "registro": "ingesta", "mensaje": "Trabajo publicado", "evento": "trabajo_publicado", "trabajo": "b4f7061e-4444-4f6e-a132-f8e929c38047", "hoja": "ff64200e-7ffc-4b60-ae67-28fe3b1b0c68", "examen": "Calculo 2", "cola": "procesamiento"}
{"momento": "2026-10-30T04:38:08.793+00:00", "nivel": "INFO", "registro": "api", "mensaje": "Lote confirmado", "evento": "lote_confirmado", "examen": "Calculo 2", "hojas_aceptadas": 1, "hojas_pendientes_de_encolar": 0, "hojas_rechazadas": 1, "duracion_confirmacion_ms": 7.9}
{"momento": "2026-10-30T04:38:08.794+00:00", "nivel": "INFO", "registro": "uvicorn.access", "mensaje": "108.162.210.191:0 - \"POST /examenes/Calculo%202/hojas HTTP/1.1\" 200"}
```

Con ese registro por la entrada estándar, desde `backend/`:
`python -m herramientas.seguir_trabajo - --trabajo b4f7061e-4444-4f6e-a132-f8e929c38047`

```
2026-10-30T04:38:08.792+00:00  trabajo_publicado      {}
2026-10-30T04:38:08.792+00:00  trabajo_tomado         {"intento": 1, "espera_en_cola_ms": 6.1}
2026-10-30T04:38:08.793+00:00  hoja_recibida          {"intento": 1, "bytes": 74}
{
  "trabajo": "b4f7061e-4444-4f6e-a132-f8e929c38047",
  "hoja": "ff64200e-7ffc-4b60-ae67-28fe3b1b0c68",
  "estado": "procesado",
  "intentos": 1,
  "de_punta_a_punta_ms": 1.0,
  "eventos": [
    "trabajo_publicado",
    "trabajo_tomado",
    "hoja_recibida"
  ]
}
```

**Lo que muestra:**

- **El consumidor de [ADR-0020](../adr/0020-entregar-los-trabajos-al-menos-una-vez-con-reintentos-y-lista-de-fallidos.md)
  funciona en el entorno desplegado**, sobre `6839cfd`: el mismo `trabajo` y la misma `hoja` en la
  API y en el worker, procesado al primer intento, sin reintentos ni fallidos.
- **El worker abrió la imagen** (`bytes: 74`) desde el volumen `almacen_imagenes`, que la API y el
  worker comparten aunque corren en contenedores distintos.
- **El lote se confirmó en 7,9 ms**, con una hoja aceptada, una rechazada y ninguna pendiente: el
  archivo inválido no tumbó el lote ([EC-07](../arc42/arc42-template-ES.md#ec-07)).
- **La IP del registro de acceso es de Cloudflare**, que está delante del servidor; la del cliente no
  queda registrada.

**La herramienta necesitó un arreglo para leer este registro**, hecho el mismo día: antes descartaba
las líneas con la marca del panel delante, y no ordenaba los eventos de dos registros pegados uno
detrás del otro. Daba el trabajo por «en camino» y 0 ms. Las dos pruebas nuevas de
[`test_mensajeria.py`](../../backend/tests/test_mensajeria.py) usan estas mismas líneas, abreviadas.

## 4. Lo que sobrevive a un despliegue

En Render, cada despliegue borraba las hojas y la bitácora (disco efímero) y un reinicio del Key
Value se llevaba la cola (R-28). Aquí las dos cosas están en volúmenes con nombre:

| Qué | Dónde | Comprobado |
|---|---|---|
| Hojas y bitácora de recepción | volumen `almacen_imagenes`, montado en `api` y `worker` | En local, con el mismo compose (26-oct): la bitácora (1 650 líneas) sobrevive a `down` y `up` |
| Cola, trabajos en curso, reintentos, fallidos y marcas de idempotencia | Redis con AOF (`appendfsync everysec`) en el volumen `datos_cola` | En local (26-oct): 5 trabajos encolados con el worker detenido sobreviven a `down` y `up`, y el worker los procesa al volver |

En el servidor, el registro del despliegue muestra que se crearon los dos volúmenes. El servidor no
hace copias de seguridad y borra los volúmenes después del 30-nov-2026, así que este entorno sigue
recibiendo solo hojas sintéticas.

## 5. Límites de memoria, medidos

Medidos en local con Docker 29.7.2 el 26 y el 29-oct, levantando `deploy/compose.lab.yaml` con
`deploy/compose.local-override.yaml`. Se lee la memoria **anónima** de cada contenedor
(`anon` en `/sys/fs/cgroup/memory.stat`) cada 0,1 s: es la que no se puede liberar, porque la caché de
archivos el kernel la suelta antes de matar el proceso. `docker stats` muestrea tan lento que se
salta los picos: el 26-oct dio 91 MiB para la API con tres lotes a la vez, y el pico real es 174. La
carga son lotes simultáneos de imágenes PNG sintéticas (la cabecera PNG y bytes al azar).

| Carga | `api` | `worker` |
|---|---|---|
| En reposo | 42 MiB | 23 MiB |
| 3 lotes de 200 hojas de 200 KB a la vez (EC-07) | 174 MiB | 26 MiB |
| 5 lotes de 200 hojas de 200 KB a la vez | 265 MiB (251 con el límite de 256 MB) | 25 MiB |
| 1, 3 y 5 lotes de 10 hojas de 19 MB a la vez | 78, 140 y 200 MiB | 41 MiB |

Las hojas pequeñas aprietan más que las grandes: al recibir un lote, Starlette guarda en memoria
cada archivo de menos de 1 MB, así que un lote de EC-07 ocupa unos 40 MB hasta que se responde; los
de 19 MB van a un archivo temporal. Redis no pasó de 7 MiB con 800 trabajos y el sitio usa 12 MiB.

| Servicio | Límite de memoria | CPU |
|---|---|---|
| `api` | 384 MB | 0,50 |
| `worker` | 96 MB | 0,25 |
| `redis` | 64 MB | 0,25 |
| `web` | 32 MB | 0,25 |
| **Total** | **576 MB de 1 GB, 4 de 6 contenedores** | |

Con 256 MB, cinco lotes de EC-07 a la vez dejaban la API a 5 MiB del límite, donde el kernel la
mata; por eso pasó a 384 MB cuando la cuota subió a 1 GB.

**Con cinco lotes a la vez, entre el 8 y el 30 % de las hojas quedan `pendiente_de_encolar`.** No es
la memoria: con 0,5 CPU los cinco lotes tardan 11 s y vence el plazo de 8 s que el lote tiene para
publicar en la cola (`PLAZO_PARA_ENCOLAR_SEGUNDOS`, en
[`ingesta/recepcion.py`](../../backend/ingesta/recepcion.py), que sale de los 10 s de EC-07). Las
hojas quedan guardadas y en la bitácora. Con tres lotes a la vez, todas quedan `encolada`.

## 6. Lo que no cubre

- **EC-07 con 200 hojas en este entorno.** Aquí se probó una hoja; el lote de 200 se midió en local
  con el mismo compose. Repetirlo en el servidor carga 40 MB de hojas sintéticas en un servidor que
  comparten 23 equipos.
- **La persistencia, probada en el servidor.** Se comprobó en local; en el servidor solo consta que
  se crearon los volúmenes.
- **Render sigue arriba**, sin cambios, hasta que el docente confirme las filas de despliegue de la
  S8 y el taller (ADR-0021).
