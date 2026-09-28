# Taller de despliegue: la API frente al patrón de carga

Comparación de dos alternativas de despliegue para **una pieza** de QuantIA, **la API**, a partir
de la condición operativa **patrón de carga**. Corresponde a la actividad «Taller aplicado de
despliegue» de la semana 8. La decisión quedó en
[ADR-0009](../adr/0009-desplegar-la-api-en-el-servicio-web-gratuito-de-render-y-mantenerla-despierta.md).

| Criterio del taller | Dónde está |
|---|---|
| La comparación responde a la condición operativa | [1. La condición operativa](#1-la-condición-operativa) |
| Pieza concreta y nombrada | [2. La pieza](#2-la-pieza) |
| Dos alternativas con el mismo detalle | [4. Alternativa A](#4-alternativa-a-servicio-web-gratuito-que-se-apaga-por-inactividad) y [5. Alternativa B](#5-alternativa-b-instancia-siempre-encendida) |
| Al menos una sin tarjeta, verificada | [4. Alternativa A](#4-alternativa-a-servicio-web-gratuito-que-se-apaga-por-inactividad), «Tarjeta» |
| Arranque en frío medido frente al p95 | [6. Arranque en frío medido](#6-arranque-en-frío-medido) |
| Supuestos: volumen, concurrencia, datos, frecuencia | [3. Supuestos](#3-supuestos) |
| Prototipo o plan reproducible | A: [`render.yaml`](../../render.yaml), desplegado. B: el plan de la sección 5 |
| Costo con el punto en que se rompe la capa gratuita | [7. Comparación](#7-comparación-frente-a-la-condición) y [estimación de costo mensual](costo-mensual.md) |
| Procedimiento de reversión | [9. Reversión](#9-reversión) |
| ADR ligado a la condición | [ADR-0009](../adr/0009-desplegar-la-api-en-el-servicio-web-gratuito-de-render-y-mantenerla-despierta.md) |
| Evidencia del proyecto, no de un tutorial | [10. Evidencia](#10-evidencia-del-proyecto) |

## 1. La condición operativa

La consigna pide partir de la condición operativa asignada: límite de costo, necesidad de
reversión, patrón de carga o tiempo de recuperación. Al equipo no se le asignó ninguna. A la
consulta, el docente respondió: **«la que definan ustedes según la prioridad en el proyecto»**.

**Elegimos el patrón de carga, porque la prioridad de QuantIA es el volumen.**
- La [ficha del problema](../ficha-problema.md) lo pone como el primer problema: «del orden de
  doscientos estudiantes por corte».
- Los escenarios EC-04 (lote de 200 hojas en ≤ 10 min) y EC-07 (confirmación del lote en ≤ 10 s)
  lo miden.
- [ADR-0002](../adr/0002-procesar-calificacion-de-forma-asincrona.md), la decisión central de la
  arquitectura, existe por la forma de esa carga: 200 hojas × 5 s son 16,6 minutos contra un
  techo de 10.

La carga no es continua. Llega **en ráfagas**: un lote justo después de cada examen, y días sin
uso entre uno y otro.

**Por qué no las otras tres:**
- **Límite de costo:** casi toda alternativa cabe en US$0, así que diferenciaría poco. Además, el
  proyecto ya lo tiene como restricción (RNF-16, arc42 §2.2), que se cumple igual.
- **Necesidad de reversión:** el proyecto no la ha declarado como prioridad.
- **Tiempo de recuperación:** llevaría a los ficheros, cuya decisión de fondo sigue abierta
  (R-06).

**La condición, medible.** La API tiene que confirmar un lote en **≤ 10 s (EC-07) también en la
primera petición después de un periodo sin uso**. Y la pantalla de inicio, que espera 5 s a
`/health` antes de declarar que no hay conexión (`frontend/lib/servicio_salud.dart`), tiene que
encontrarla despierta.

## 2. La pieza

**La pieza es la API:** el servicio `api` del `docker-compose.yml`, la parte HTTP del contenedor
«Aplicación web» del C4 Nivel 2. Recibe los lotes en `POST /examenes/{examen_id}/hojas` y
responde la sonda `GET /health`. No es el sistema entero:
- el sitio tiene su propia decisión (ADR-0010);
- la cola, la suya (ADR-0011);
- los ficheros, la suya (ADR-0012).

El worker corre dentro de la misma instancia que la API (ADR-0011), así que hereda lo que se
decide aquí.

## 3. Supuestos

| Supuesto | Valor | De dónde sale |
|---|---|---|
| Volumen | 200 hojas por corte, de 200 KB cada una: unos 40 MB por lote | Ficha del problema; medición de EC-07 (`--kb 200`) |
| Frecuencia | Hasta 4 lotes al mes, en fechas de corte; días sin uso entre ellos | Tres cortes por semestre (semanas 5, 10 y 16), con margen |
| Concurrencia | Un docente cargando a la vez | Cada docente carga el lote de su curso |
| Tamaño de los datos | Hasta 160 MB de hojas al mes en el disco efímero; la cola, casi vacía | [Estimación de costo](costo-mensual.md), sección 2 |
| Forma de una sesión | Abrir el sitio (la pantalla de inicio consulta `/health`), elegir los archivos y enviar el lote | `frontend/lib/pantalla_inicio.dart` y `pantalla_carga.dart` |

Con esa forma, **sin nada que la mantenga despierta, toda sesión empieza en frío**: los lotes
llegan separados por días, y el servicio gratuito se apaga a los 15 minutos. Dentro de una sesión,
una de cada dos peticiones (la primera) cae en frío.

## 4. Alternativa A: servicio web gratuito que se apaga por inactividad

- **Qué es:** un servicio web Free de Render: 0,1 CPU, 512 MB y 750 h de instancia al mes por
  workspace, compartidas entre los servicios web gratuitos. Se apaga tras 15 minutos sin tráfico
  (https://render.com/pricing y https://render.com/docs/free, consultadas el 27-sep-2026).
- **Cómo corre:** en Docker con `backend/Dockerfile`, región `virginia`, declarado en
  [`render.yaml`](../../render.yaml) y aplicado como Blueprint. La API y el worker arrancan con
  [`backend/arrancar-api-y-worker.sh`](../../backend/arrancar-api-y-worker.sh).
- **Tarjeta:** no hace falta. **Verificado:** la cuenta de Render se creó el 27-sep-2026 iniciando
  sesión con GitHub, y no pidió tarjeta ni método de pago en ningún momento.
- **Qué pasa con la ráfaga:** la primera petición de cada sesión despierta la instancia. Medido
  (sección 6): 12,5 s para `/health` y 13,5 a 24,0 s para un lote. Supera los 10 s de EC-07 y los
  5 s de la pantalla de inicio, que se rinde y dice que no hay conexión. Una vez despierta, el p95
  del lote es de 1,3 s.
- **Costo y punto de ruptura:** US$0 al mes. Se rompe con las 750 h del workspace, con 5 GB de
  salida o con 500 minutos de build al mes (detalle en la [estimación](costo-mensual.md)).
- **Variante con monitor:** un monitor gratuito de UptimeRobot (sin tarjeta, intervalo mínimo de 5
  minutos: https://uptimerobot.com/pricing/, consultada el 27-sep-2026) consulta `/health` cada 5
  minutos, por debajo de los 15 del apagado. Quita el arranque en frío sin dinero. Verificado a las
  18:17 del 27-sep, veinte minutos después de activarlo: `/health` respondió en 0,21 a 0,43 s. El
  costo pasa a horas: la API despierta gasta 720 h (mes de 30 días) o 744 h (mes de 31) de las 750.
- **Prototipo:** desplegado y en uso. API en https://quantia-utb-api.onrender.com, sitio en
  https://quantia-utb.onrender.com.

## 5. Alternativa B: instancia siempre encendida

- **Qué es:** la instancia Starter de Render, «Less than 1 CPU» en la página de precios: 0,5 CPU y
  512 MB por US$7 al mes, que nunca se apaga (https://render.com/pricing, consultada el
  27-sep-2026).
- **Cómo corre:** igual que A. Mismo `backend/Dockerfile`, misma región, mismo script de arranque y
  mismo `render.yaml`; solo cambia el plan. Se eligió el mismo proveedor a propósito: así la única
  variable de la comparación es el modelo de ejecución (apagarse o no), que es lo que pregunta la
  condición.
- **Tarjeta:** sí la exige. Es un plan de pago, y la cuenta tiene que tener un método de pago.
- **Qué pasa con la ráfaga:** la instancia siempre está despierta, así que la primera petición de
  cada sesión se comporta como las demás: el p95 en caliente es de 0,13 s para `/health` y de 1,3 s
  para un lote. Cumple EC-07 y la espera de la pantalla sin ningún monitor.
- **Costo y punto de ruptura:** US$7 al mes desde el primer día, se use o no. No hay capa gratuita
  que romper: con el patrón del proyecto se pagan 720 horas al mes para atender una carga que ocupa
  minutos.
- **Plan reproducible:**
  1. Registrar un método de pago en el workspace de Render.
  2. En `render.yaml`, en el servicio `quantia-utb-api`, cambiar `plan: free` por `plan: starter`.
  3. Hacer commit y push a `master`. Cuando el CI termina en verde, Render aplica el cambio.
  4. Pausar el monitor de UptimeRobot, que deja de hacer falta.
  5. Comprobar con `curl` que `/health` responde en décimas de segundo tras más de 15 minutos sin
     tráfico.

## 6. Arranque en frío medido

Ninguna de las dos alternativas es una función, así que la ficha no exige este contraste. **Se
midió de todos modos**, porque la alternativa A escala a cero igual que una función, y su arranque
en frío es justamente lo que la condición pone a prueba.

**Procedimiento.**
- Herramienta versionada:
  [`backend/herramientas/medir_arranque_en_frio.py`](../../backend/herramientas/medir_arranque_en_frio.py).
- Desde internet residencial en Cartagena, fuera de la red de la universidad, con el monitor
  apagado y sin nadie usando el sistema.
- Antes de cada muestra en frío, 16 minutos sin tráfico (uno más que el apagado). Después, una
  serie en caliente.
- Lotes de 20 hojas sintéticas de 200 KB (3,9 MB).
- Resultado completo:
  [`medicion-arranque-en-frio.json`](../evidencia/medicion-arranque-en-frio.json).

```
cd backend
python -m herramientas.medir_arranque_en_frio --frio-salud 3 --frio-lote 2 --espera-min 16 \
    --caliente 30 --caliente-lotes 5 --lote-hojas 20 --kb 200 --json medicion-arranque-en-frio.json
```

| Hora (27-sep, −05:00) | Petición | Estado previo | Tiempo |
|---|---|---|---|
| 15:14 | `GET /health` | 16 min sin tráfico | 12,50 s |
| 15:30 | Lote de 20 hojas | 16 min sin tráfico | 13,47 s |
| 15:46 | `GET /health` | 16 min sin tráfico | 12,51 s |
| 16:02 | Lote de 20 hojas | 16 min sin tráfico | 23,98 s |
| 16:19 | `GET /health` | 16 min sin tráfico | 12,51 s |
| 16:19 | 30 × `GET /health` | despierta | mediana 0,12 s · p95 0,13 s |
| 16:19 | 5 lotes de 20 hojas | despierta | mediana 0,88 s · p95 1,32 s |

**Contraste con el escenario de la pieza.**
- EC-07 fija el techo de la confirmación del lote en 10 s. En caliente, el p95 del lote es de
  1,3 s y cumple con margen.
- En frío, las dos muestras (13,5 y 24,0 s) lo superan: el arranque le suma entre 12,6 y 23,1 s al
  lote.
- `/health` en frío tarda 12,5 s, más del doble de los 5 s que espera la pantalla de inicio.
- En el servidor, la confirmación de un lote real tomó 14,1 ms (evento `lote_confirmado` en el log
  del entorno desplegado). El tiempo en frío es el arranque de la plataforma, no el código.

## 7. Comparación frente a la condición

| | A sin monitor | A con monitor (elegida) | B: Starter siempre encendida |
|---|---|---|---|
| Primera petición tras días sin uso | 12,5 s (`/health`), 13,5 a 24,0 s (lote) | como en caliente: 0,2 a 0,4 s | como en caliente |
| EC-07 en la primera petición | **No cumple** | Cumple | Cumple |
| Pantalla de inicio (espera de 5 s) | Se rinde | Encuentra la API | Encuentra la API |
| Costo mensual | US$0 | US$0 | US$7 |
| Tarjeta | No | No | Sí |
| Punto de ruptura | 750 h, 5 GB, 500 min de build | 750 h: la API ya usa 720 a 744, así que no cabe otro servicio web despierto | No hay capa gratuita: costo fijo |
| Cambio en el código | Ninguno | Ninguno (`HEAD /health` responde 200 para el monitor) | Ninguno: una línea de `render.yaml` |
| Quién puede operarlo | El workspace gratuito tiene un puesto (R-16); cualquiera lo recrea desde `render.yaml` | Igual | Igual, más quien tenga la tarjeta |

## 8. Decisión

**A con monitor**, registrada en
[ADR-0009](../adr/0009-desplegar-la-api-en-el-servicio-web-gratuito-de-render-y-mantenerla-despierta.md).
- Responde a la condición: la primera petición de una ráfaga ya no paga el arranque.
- Cumple RNF-16 sin tarjeta.
- Deja a B como salida inmediata si la capa gratuita cambia.
- **B se descarta** porque exige tarjeta, fuera de la restricción de costo, y porque con este
  patrón paga 720 horas al mes para atender minutos de carga.

## 9. Reversión

1. **Un despliegue sale mal.** En Render, en el servicio `quantia-utb-api`, se hace *Rollback* a
   uno de los 5 despliegues que conserva el plan gratuito. Otra vía es `git revert` del commit: el
   CI corre y Render redespliega cuando queda en verde. Criterio de éxito: `/health` responde 200 y
   una carga deja `lote_confirmado` en el log.
2. **Se agotan las 750 h o Render cambia su capa gratuita.** Se pausa el monitor en UptimeRobot:
   la API vuelve a dormirse y deja de gastar horas, a cambio del arranque en frío. Si hace falta
   mantenerla despierta, se pasa a B con el plan de la sección 5.
3. **Falla el monitor.** La API vuelve al comportamiento de A sin monitor. Es una degradación
   (12,5 s en la primera petición), no una caída.
4. **Render deja de servir.** El mismo `backend/Dockerfile` se levanta con `docker-compose.yml` en
   otra máquina (el servidor del laboratorio, cuando se confirme que es accesible desde fuera). Se
   recompila el sitio con la nueva `BACKEND_URL` y se actualiza `ALLOWED_ORIGIN`.

**Quién la ejecuta.** El workspace gratuito de Render tiene un solo puesto (R-16). Si esa persona
no está, cualquier integrante recrea el entorno en su cuenta desde `render.yaml`, siguiendo la
sección «Cómo se despliega» del [README](../../README.md).

## 10. Evidencia del proyecto

Todo sale del repositorio y del entorno desplegado. Ninguna captura de un tutorial.

- Configuración: [`render.yaml`](../../render.yaml), [`backend/Dockerfile`](../../backend/Dockerfile) y [`backend/arrancar-api-y-worker.sh`](../../backend/arrancar-api-y-worker.sh).
- Medición: [`medir_arranque_en_frio.py`](../../backend/herramientas/medir_arranque_en_frio.py) y [`medicion-arranque-en-frio.json`](../evidencia/medicion-arranque-en-frio.json).
- Commits:
  - `3832a16`: el entorno como Blueprint.
  - `1ead6a8`: el primer despliegue falló porque Render no interpreta las comillas de `dockerCommand`, y el arranque pasó a un script.
  - `fed572e` y `a53d5f9`: la herramienta de medición y su resultado.
  - `05375c6`: `HEAD /health`, porque el monitor gratuito consulta con `HEAD` y la API respondía 405.
- En el entorno desplegado: el sitio y la API responden desde fuera de la universidad, y el log registra `hoja_recibida` y `lote_confirmado` en JSON (líneas reales en el README).

## 11. Otras opciones consideradas

- **El servidor del laboratorio.** La guía del curso deja todos sus datos en «POR_CONFIRMAR»,
  incluido si es accesible desde fuera de la universidad, y pide no basar el taller solo en él.
  Queda como destino de la reversión 4.
- **La API como función** (las que nombra la guía: Cloudflare Workers, Vercel Functions, AWS
  Lambda). Tendría el mismo problema de arranque en frío. Además, la API escribe en disco y mantiene
  la conexión con la cola, que son los criterios 3 y 4 de la guía, y habría que reescribirla en vez
  de desplegar el mismo Dockerfile (criterio 6).
- **Otras plataformas de contenedores que piden tarjeta**, verificado el 26-sep-2026: Fly.io
  («All organizations […] require a credit card on file»: https://docs.fly.io/about/pricing/),
  Google Cloud Run (exige una cuenta de facturación:
  https://docs.cloud.google.com/free/docs/free-cloud-features) y Koyeb (preautorización con
  tarjeta: https://www.koyeb.com/docs/faqs/pricing). No cumplen la condición de «sin tarjeta» ni
  RNF-16.
