# 0009 · Desplegar la API en el servicio web gratuito de Render y mantenerla despierta

- **Estado:** aceptado
- **Fecha:** 2026-09-27
- **Decide:** Josué Ortega De Arco, María Restrepo Licona, Sebastián Cañas Plata, Susana Rosales Castellar
- **Escenario de calidad relacionado:** [EC-07](../arc42/arc42-template-ES.md#ec-07) (confirmación del lote en ≤ 10 s, 0 % de pérdida silenciosa)
- **Condición operativa del taller de despliegue:** patrón de carga
- **Relación con otros ADR:** precisa, sin reemplazar, a [ADR-0002](0002-procesar-calificacion-de-forma-asincrona.md): el procesamiento asíncrono no cambia; aquí se decide dónde corre la API. El worker corre en la misma instancia según [ADR-0011](0011-consumir-la-cola-desde-la-instancia-de-la-api-con-el-key-value-gratuito.md)

**La decisión, en una frase:** la API corre en un servicio web gratuito de Render
(`quantia-utb-api`, declarado en [`render.yaml`](../../render.yaml)), y un monitor externo la
consulta cada 5 minutos para que no se apague, porque su arranque en frío medido (12,5 s) no cabe
en los 10 s de EC-07.

## Contexto

**La condición operativa.** El taller pide comparar dos alternativas «a partir de la condición
operativa asignada». Al equipo no se le asignó ninguna, y a la consulta el docente respondió: «la
que definan ustedes según la prioridad en el proyecto». Elegimos **patrón de carga**, porque la
prioridad de QuantIA es el volumen. Los lotes de unas 200 hojas llegan justo después de cada
examen (EC-04, EC-07), con días sin uso entre uno y otro, y esa forma de la carga es la razón de
ADR-0002.

**La pieza** es la API: el servicio `api` del compose, que recibe
`POST /examenes/{examen_id}/hojas`. La restricción de costo del curso fija US$0 al mes y ninguna
cuenta con tarjeta.

**El problema.** El servicio web gratuito de Render se apaga tras 15 minutos sin tráfico. Con
lotes separados por días, prácticamente toda sesión de un docente empieza en frío. La guía del
curso lo convierte en criterio: si el umbral del escenario es menor que el arranque en frío
medido, la pieza no sirve así.

**La medición** se hizo el 27-sep-2026 desde internet residencial, fuera de la red de la
universidad, con [`medir_arranque_en_frio.py`](../../backend/herramientas/medir_arranque_en_frio.py).
El resultado está en [`medicion-arranque-en-frio.json`](../evidencia/medicion-arranque-en-frio.json).

| Petición | En frío (tras 16 min sin tráfico) | En caliente |
|---|---|---|
| `GET /health` | 12,5 s (3 de 3 muestras) | p95 de 0,13 s (30 muestras) |
| Lote de 20 hojas de 200 KB | 13,5 s y 24,0 s | p95 de 1,3 s (5 lotes) |

Una carga real desde el sitio registró `duracion_confirmacion_ms: 14.1` en el servidor. El tiempo
en frío es el arranque de la plataforma, no el código. **En frío no se cumple EC-07**, y la
pantalla de inicio, que espera 5 s a `/health`, se rinde antes de que la API despierte.

## Alternativas consideradas

**A. Servicio web gratuito, sin nada más.** Cuesta US$0 y no pide tarjeta: la cuenta se creó el
27-sep-2026 iniciando sesión con GitHub y no pidió método de pago. Da 0,1 CPU, 512 MB y 750 h de
instancia al mes por workspace (https://render.com/pricing, consultada el 27-sep-2026).
Descartada tal cual: la medición muestra que incumple EC-07 en la primera petición de cada
sesión.

**B. Instancia siempre encendida (Render Starter).** Da 0,5 CPU y 512 MB por US$7 al mes, con
tarjeta (misma fuente). No tiene arranque en frío. Descartada por la restricción de costo, y
porque con este patrón paga 720 horas al mes para atender una carga que ocupa minutos, en unas
pocas fechas de corte.

**C. La A más un monitor externo (elegida).** UptimeRobot, en su plan gratuito y sin tarjeta
(50 monitores, intervalo mínimo de 5 minutos: https://uptimerobot.com/pricing/, consultada el
27-sep-2026), consulta `/health` cada 5 minutos, por debajo de los 15 del apagado. Quita el
arranque en frío sin dinero. El costo se paga en horas: 720 (mes de 30 días) o 744 (mes de 31) de
las 750 del workspace.

**Otras opciones consideradas:**
- **El servidor del laboratorio:** sus datos siguen «POR_CONFIRMAR» en la guía, incluido si es
  accesible desde fuera de la universidad. La guía pide no basar el taller solo en él.
- **La API como función:** tendría el mismo problema de arranque en frío, y además la API escribe
  en disco y mantiene la conexión con la cola, que son los criterios 3 y 4 de la guía.

## Decisión

La API se declara en `render.yaml` como servicio web gratuito:
- región `virginia` y Docker con [`backend/Dockerfile`](../../backend/Dockerfile);
- arranque con [`backend/arrancar-api-y-worker.sh`](../../backend/arrancar-api-y-worker.sh);
- *health check* en `/health`;
- despliegue solo cuando el CI del commit termina en verde (`autoDeployTrigger: checksPass`) y
  cambió `backend/`.

Un monitor de UptimeRobot consulta `https://quantia-utb-api.onrender.com/health` cada 5 minutos.

## Consecuencias

**Lo que se gana:**
- En caliente, EC-07 se cumple con margen, y la pantalla de inicio encuentra la API despierta.
- El código no depende del proveedor (criterio 6 de la guía). La atadura vive en `render.yaml` y
  en el script de arranque, y el mismo Dockerfile corre con `docker-compose.yml`.

**Lo que se asume:**
- **Punto de ruptura: las 750 h del workspace.** Con el monitor, la API gasta 720 o 744 h, así
  que ningún otro servicio web gratuito puede quedar despierto todo el mes (por eso el sitio es
  estático, ADR-0010). Si se agotan, Render suspende los servicios hasta el mes siguiente.
- Depende de un tercero (UptimeRobot) y de que Render mantenga su capa gratuita. Render no
  documenta este uso como soportado ni lo prohíbe.
- El plan gratuito tiene un solo puesto: solo una persona opera el workspace. Se mitiga con
  `render.yaml`, que recrea el entorno en cualquier cuenta siguiendo el README.
- El disco de la instancia es efímero (ADR-0012).
- El primer despliegue falló porque Render no interpreta las comillas de `dockerCommand`, y se
  corrigió llevando el comando a un script (`1ead6a8`).

## Reversión

1. **Un despliegue sale mal.** En Render se hace *Rollback* a uno de los 5 últimos despliegues, o
   `git revert` del commit, que se redespliega solo cuando el CI queda en verde. Criterio de
   éxito: `/health` responde 200 y una carga deja `lote_confirmado` en el log.
2. **Se agota el cupo de horas o cambia la capa gratuita.** Se pausa el monitor: la API vuelve a
   dormirse y deja de gastar horas, a cambio del arranque en frío. Otra salida es cambiar
   `plan: free` por `plan: starter` en `render.yaml` (alternativa B, con tarjeta).
3. **Render deja de servir.** El mismo `backend/Dockerfile` se levanta con `docker-compose.yml`
   en otra máquina. Luego se recompila el sitio con la nueva `BACKEND_URL` y se actualiza
   `ALLOWED_ORIGIN`.

## Trazabilidad

- Configuración: [`render.yaml`](../../render.yaml), [`backend/arrancar-api-y-worker.sh`](../../backend/arrancar-api-y-worker.sh)
- Medición: [`medir_arranque_en_frio.py`](../../backend/herramientas/medir_arranque_en_frio.py), [`medicion-arranque-en-frio.json`](../evidencia/medicion-arranque-en-frio.json)
- Comparación completa del taller: [`taller-despliegue-api.md`](../despliegue/taller-despliegue-api.md)
- Vista de despliegue: [arc42 §7](../arc42/arc42-template-ES.md#7-deployment-view)
- Commits: `3832a16` (`render.yaml`), `1ead6a8` (script de arranque), `fed572e` y `a53d5f9` (medición)
