# 0021 · Desplegar en el servidor del laboratorio, con el sitio compilado en el CI

- **Estado:** aceptado
- **Fecha:** 2026-10-29
- **Decide:** Josué Ortega De Arco, María Restrepo Licona, Sebastián Cañas Plata, Susana Rosales Castellar
- **Escenario de calidad relacionado:** [EC-07](../arc42/arc42-template-ES.md#ec-07) (confirmación del lote en ≤ 10 s, 0 % de pérdida silenciosa)
- **Origen:** el requisito del docente en los seguimientos diarios de despliegue, «README con URL pública exacta bajo un subdominio de iscoutb.dev, diferenciando frontend y API», que marcaba a QuantIA como «Externo» mientras siguiera en Render; y el seguimiento del 26-oct, que pide validar el consumidor de [ADR-0020](0020-entregar-los-trabajos-al-menos-una-vez-con-reintentos-y-lista-de-fallidos.md) en el entorno desplegado y resolver la persistencia de Redis y del almacén
- **Restricciones que lo acotan:** RNF-16 (US$0 y sin tarjeta), RNF-11 (ningún secreto en el repositorio), RNF-12 (solo hojas sintéticas en un entorno desplegado) y las reglas del servidor (`docs/politicas-uso.md` del repositorio [ISCOUTB/iscoutb.dev](https://github.com/ISCOUTB/iscoutb.dev))
- **Relación con otros ADR:** reemplaza a [ADR-0009](0009-desplegar-la-api-en-el-servicio-web-gratuito-de-render-y-mantenerla-despierta.md), [ADR-0010](0010-servir-el-sitio-como-archivos-estaticos-en-render.md), [ADR-0011](0011-consumir-la-cola-desde-la-instancia-de-la-api-con-el-key-value-gratuito.md) y [ADR-0012](0012-mantener-el-almacen-en-el-disco-efimero-de-la-instancia-hasta-cerrar-r-06.md), las cuatro decisiones del entorno de Render. No toca [ADR-0002](0002-procesar-calificacion-de-forma-asincrona.md), [ADR-0006](0006-registrar-la-recepcion-en-una-bitacora-antes-de-encolar.md), [ADR-0016](0016-acotar-la-espera-de-la-cola-y-hacer-idempotente-al-worker.md), [ADR-0018](0018-dar-a-la-hoja-una-identidad-propia-y-derivar-su-estado-de-la-bitacora.md) ni ADR-0020: corre la misma imagen con el mismo código

**La decisión, en una frase:** el sistema corre en el servidor del laboratorio del curso, el panel
Dokploy de iscoutb.dev, con [`deploy/compose.lab.yaml`](../../deploy/compose.lab.yaml): la API, el
worker, Redis con persistencia y el sitio en nginx, en cuatro contenedores. El sitio lo compila el
CI y lo publica en la rama `despliegue`, que es la que lee el panel, así que solo se despliega lo que
pasó las pruebas.

---

## Contexto

**Render cumplió desde la S8, con cinco límites que ya estaban escritos:**

- **Quedaba fuera de iscoutb.dev**, que es lo que pide el docente.
- **El Key Value gratuito no persiste** (R-28). Desde ADR-0020 ahí viven la cola, los trabajos en
  curso, los reintentos, los fallidos y las marcas de idempotencia.
- **El disco era efímero** (ADR-0012): las hojas y la bitácora se perdían en cada despliegue.
- **La API se dormía a los 15 minutos** y tardaba 12,5 s en despertar (R-13). La mantenía despierta
  un monitor externo que gastaba 720 a 744 de las 750 h del workspace (R-15).
- **Solo una persona podía operar el workspace** (R-16).

**El servidor del laboratorio.** Cuando se escribieron ADR-0009 y ADR-0011, sus datos estaban «POR
CONFIRMAR». El docente publicó el manual el 13-oct (repositorio
[ISCOUTB/iscoutb.dev](https://github.com/ISCOUTB/iscoutb.dev)):

- Es una VM de Oracle Cloud compartida entre 23 equipos, con Traefik delante y un certificado para
  `*.iscoutb.dev`.
- Cada equipo tiene un proyecto en el panel. El nuestro es `calificacion`, con un servicio Compose
  llamado `sistema`.
- La cuota del equipo era de 4 contenedores y 512 MB sumando los límites. El panel anunció el
  29-oct que sube a 6 contenedores y 1 GB, aunque `docs/politicas-uso.md` todavía dice 4 y 512 MB.
- Cada contenedor tiene como máximo 0,5 CPU.
- Prohíbe `ports:`, `container_name`, `privileged`, los bind mounts y las redes externas. Los datos
  van en volúmenes con nombre y los secretos como `${VARIABLE}`, con el valor en el panel.
- Hay 2 compilaciones simultáneas para todo el servidor. Por eso el manual pide no compilar
  Flutter ahí: su imagen ocupa unos 3 GB.
- No hay copias de seguridad, y los volúmenes se borran después del 30-nov-2026.

**El sitio es Flutter web compilado.** La URL de la API se hornea al compilar (`BACKEND_URL`), así
que el sitio necesita un paso de compilación en alguna parte.

## Alternativas consideradas

### 1. Dónde corre el sistema

| Opción | A favor | En contra | |
|---|---|---|---|
| Seguir en Render | No hay que hacer nada; está medido desde la S8 | «Externo» en el seguimiento; la cola y las hojas se pierden (R-28, ADR-0012); arranque en frío y monitor; un solo operador | Descartada |
| **Servidor del laboratorio** | Bajo iscoutb.dev; volúmenes con nombre que sobreviven a los despliegues; un Redis propio que puede persistir; contenedores que no se duermen; según el manual, cada integrante entra al panel con su correo institucional | Compartido entre 23 equipos, con cuota y 0,5 CPU por contenedor; sin copias de seguridad; se borra después del 30-nov; la red de la UTB no resuelve `*.iscoutb.dev` | **Elegida** |

### 2. Dónde se compila el sitio

| Opción | A favor | En contra | |
|---|---|---|---|
| GitHub Pages (el plan del 9-oct) | Gratis, sin contenedor | Deja el sitio fuera de iscoutb.dev: al equipo que lo hizo así, el seguimiento lo marca «cumplimiento parcial». Además dependía de que el docente activara Pages, y seguía sin activarse | Descartada |
| Compilar Flutter en el servidor, con un Dockerfile de dos etapas | Una sola rama, sin publicar nada desde el CI | El manual pide no hacerlo: cada despliegue bajaría una imagen de unos 3 GB y ocuparía minutos uno de los 2 turnos de compilación de los 23 equipos | Descartada; es el plan B si el CI no pudiera publicar |
| Guardar el sitio compilado en `master` | Simple | Unas 200 000 líneas generadas en el historial y en el análisis de SonarCloud con cada cambio del frontend | Descartada |
| **El CI compila y publica la rama `despliegue`; el servidor solo copia el sitio a nginx** | Sin Flutter en el servidor; solo se despliega lo que pasó las pruebas, que es la sección 3.6 del manual; `master` queda solo con código | Una rama generada que nadie edita, reescrita en cada publicación; el CI necesita permiso de escritura (`contents: write`) | **Elegida** |

### 3. Un nombre con `/api` o dos nombres

El manual acepta las dos formas y pide justificarla en un ADR (CORS, cookies, versionado).

| Opción | A favor | En contra | |
|---|---|---|---|
| Un nombre, con la API bajo `/api` y *Strip Path* | Sin CORS | La API tendría que arrancar con `--root-path /api` para que `/docs` funcione, y el sitio llamaría a rutas con un prefijo que el contrato no tiene | Descartada |
| **Dos nombres: `calificacion` y `api-calificacion`** | La API conserva sus rutas y su contrato tal cual. Es la misma forma que en Render: el sitio llama a una URL horneada y la API acepta un solo origen (`ALLOWED_ORIGIN`) | CORS obligatorio, que ya estaba | **Elegida** |

No hay cookies, porque todavía no hay identidad (A-05). Y el contrato no cambia de versión.

## Decisión

1. **[`deploy/compose.lab.yaml`](../../deploy/compose.lab.yaml)** describe el entorno, con límites
   que salen de medirlo:

   | Servicio | Qué es | Memoria | CPU |
   |---|---|---|---|
   | `api` | La imagen de `backend/` | 384 MB | 0,50 |
   | `worker` | La misma imagen, con otro comando | 96 MB | 0,25 |
   | `redis` | `redis:7-alpine` | 64 MB | 0,25 |
   | `web` | El sitio, en nginx sin privilegios | 32 MB | 0,25 |

   Suman 576 MB de 1 GB y 4 de los 6 contenedores. Sin `ports:`, sin bind mounts y sin
   `container_name`.
2. **Redis persiste** con AOF (`appendfsync everysec`, sin instantáneas RDB) en el volumen
   `datos_cola`, con `maxmemory 32mb` y `noeviction`. La cola y las cuatro listas de ADR-0020
   sobreviven a los despliegues.
3. **Las hojas y la bitácora** van en el volumen `almacen_imagenes`, montado en `api` y en
   `worker`, que desde ADR-0020 abre cada imagen.
4. **El sitio lo compila el job `publicar-despliegue`** de [`ci.yml`](../../.github/workflows/ci.yml):
   - corre después de los dos jobs de pruebas, y solo en un push a `master`;
   - compila con `BACKEND_URL=https://api-calificacion.iscoutb.dev` y comprueba que la URL quedó en
     `main.dart.js`;
   - reescribe la rama `despliegue` como `master` más un commit con `deploy/sitio/web/`,
     `revision.txt` y un `.sonarcloud.properties` que deja lo generado fuera del análisis;
   - no publica si `master` ya avanzó.

   En `master`, [`deploy/sitio/Dockerfile`](../../deploy/sitio/Dockerfile) sirve una página
   provisional, para que el compose levante en limpio, como pide la lista de comprobación del manual.
   Copia las dos carpetas por su nombre, sin comodines, y su `.dockerignore` no deja entrar nada más
   a la imagen.
5. **En el panel:**
   - el servicio `sistema` lee la rama `despliegue`, con *Compose Path* `./deploy/compose.lab.yaml`
     y despliegue automático;
   - dos dominios con HTTPS de Let's Encrypt: `calificacion.iscoutb.dev` va a `web:8080` y
     `api-calificacion.iscoutb.dev` a `api:8000`;
   - en *Environment*, `ALLOWED_ORIGIN` y `LLM_API_KEY`, que solo existe ahí (RNF-11).
6. **`/health` sigue sin consultar Redis** (ADR-0006). Traefik solo envía tráfico a un contenedor
   sano, y con la cola caída la API tiene que seguir recibiendo hojas como pendientes.
7. **Render sigue arriba, sin cambios,** hasta que el docente confirme que revisó las filas de
   despliegue de la S8 y el taller. Entonces se suspenden sus servicios y se borra el monitor de
   UptimeRobot. En un solo commit se quitan `render.yaml`, `backend/arrancar-api-y-worker.sh` y la
   línea que lo copia en `backend/Dockerfile`.

## Consecuencias

### Positivas

- **El sitio y la API quedan bajo iscoutb.dev, por separado.**
- **Un despliegue no pierde nada.** La cola, con lo que está en curso, los reintentos, los fallidos
  y las marcas, persiste: R-28 se cierra en este entorno. Las hojas y la bitácora también: lo que
  ADR-0012 aceptaba perder ya no se pierde.
- **No hay arranque en frío** ni monitor ni cupo de horas: se cierran R-13 y R-15.
- **El worker tiene su contenedor y sus límites**, como en el entorno local. Ya no comparte 0,1 CPU
  con la API (R-25). No es extraer un módulo: es la misma imagen, así que
  [ADR-0017](0017-no-extraer-ningun-modulo-del-monolito-todavia.md) no cambia.
- **Solo se despliega lo que pasó las pruebas**, y `revision.txt` dice qué commit corre.
- **El equipo entero puede operar el panel** (R-16).

### Negativas y consecuencias asumidas

- **Servidor compartido, con 0,5 CPU por contenedor.** Con tres lotes de EC-07 a la vez no pasa
  nada. Con cinco, entre el 8 y el 30 % de las hojas quedan `pendiente_de_encolar`, porque vence el
  plazo de 8 s del lote (R-32).
- **Sin copias de seguridad, y borrado después del 30-nov-2026** (R-31). R-06 sigue abierto: falta
  la retención y la base de datos, que ahora cabe como quinto contenedor.
- **La red de la UTB no resuelve `*.iscoutb.dev`** (R-30): desde el campus, el sitio no abre.
- **La cuota escrita y la anunciada no coinciden**: los 576 MB pasan de los 512 que todavía dice el
  manual (R-31).
- **Cada push a `master` que pasa el CI vuelve a desplegar**, aunque solo cambie documentación. El
  contenedor del sitio se recrea porque cambia `revision.txt`.
- **El CI compila Flutter dos veces por push** (en las pruebas y al publicar), y necesita permiso de
  escritura sobre el repositorio.

## Reversión

1. **Un despliegue sale mal:** `git revert` del commit en `master`. El CI vuelve a publicar
   `despliegue` y el panel redespliega. Criterio de éxito: `/health` responde 200 y `revision.txt`
   dice el commit nuevo.
2. **El CI no puede publicar la rama:** el panel vuelve a leer `master`, y `deploy/sitio/Dockerfile`
   pasa a compilar Flutter en una primera etapa (el plan B de la alternativa 2).
3. **El servidor deja de servir:** mientras el docente no confirme la S8, Render sigue arriba. Después,
   el entorno de Render se recrea desde el `render.yaml` que queda en el historial de git.

## Qué dato haría revisar esta decisión

- **Que EC-07, medido en este entorno con 200 hojas, no se cumpla:** se revisan la CPU de `api` y el
  plazo del lote.
- **Que R-06 elija la base de datos:** sería el quinto contenedor, y `/health` tendría que
  comprobarla.
- **Que A-02 lea las marcas en el worker:** se vuelven a medir su memoria y su CPU.
- **Que la publicación de la rama falle** por permisos de la organización: el plan B.
- **Que el curso cierre el servidor** el 30-nov.

## Trazabilidad

- **Infraestructura como código:** [`deploy/compose.lab.yaml`](../../deploy/compose.lab.yaml),
  [`deploy/sitio/Dockerfile`](../../deploy/sitio/Dockerfile),
  [`deploy/compose.local-override.yaml`](../../deploy/compose.local-override.yaml),
  [`deploy/.env.example`](../../deploy/.env.example) y el job `publicar-despliegue` de
  [`ci.yml`](../../.github/workflows/ci.yml).
- **Commits:** `8ad703a` (el compose y el sitio), `6839cfd` (el job del CI), `6509cf3` y su
  corrección (`seguir_trabajo.py` lee el registro del panel) y `e42f894` (el sitio sin comodín,
  por el aviso `docker:S6470` de SonarCloud).
- **Evidencia:** [`despliegue-iscoutb.md`](../evidencia/despliegue-iscoutb.md): la revisión
  desplegada, la comprobación desde fuera de la universidad, el recorrido de una hoja y los límites
  de memoria medidos.
- **Costo:** [`costo-mensual.md`](../despliegue/costo-mensual.md).
- **Vista de despliegue:** [arc42 §7](../arc42/arc42-template-ES.md#7-deployment-view).
- **Riesgos:** cierra R-13, R-15 y R-16, y R-28 en este entorno; abre R-30, R-31 y R-32
  ([arc42 §11](../arc42/arc42-template-ES.md#11-risks-and-technical-debts)).
