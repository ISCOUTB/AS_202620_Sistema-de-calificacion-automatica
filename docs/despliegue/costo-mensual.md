# Estimación de costo mensual del entorno desplegado

Estima cuánto cuesta al mes el entorno de demostración de QuantIA en Render, con el método del
apartado «Cómo estimar el costo mensual» de la «Guía de despliegue y costos» del curso:

- cuatro números salidos del escenario del proyecto (operaciones al mes, tamaño de los datos
  almacenados, tráfico de salida y horas de ejecución);
- un resultado que se espera en cero;
- **el punto en que la capa gratuita se rompe**;
- los costos que no son dinero.

Las cifras de los proveedores se consultaron el 27-sep-2026 en sus páginas oficiales (fuentes al
final). El despliegue está descrito en [`render.yaml`](../../render.yaml) y en la
[sección 7 del arc42](../arc42/arc42-template-ES.md#7-deployment-view). La restricción que
fija el objetivo de US$0 es RNF-16 (costo mensual de US$0 y ninguna cuenta con tarjeta).

## 1. Supuestos

Salen del proyecto, no del catálogo del proveedor.

| Supuesto | Valor | De dónde sale |
|---|---|---|
| Hojas por corte | 200 | [Ficha del problema](../ficha-problema.md): «del orden de doscientos estudiantes por corte»; es el lote de EC-04 y EC-07 |
| Tamaño de una hoja | 200 KB, así que un lote de 200 hojas pesa unos 40 MB | Parámetro de la [medición de EC-07](../evidencia/medicion-ec07.md) (`--kb 200`) |
| Lotes al mes | 4 | El curso tiene tres cortes por semestre (semanas 5, 10 y 16), así que un mes de corte trae a lo sumo un lote por curso. Se calcula con 4 para dejar margen |
| Concurrencia | Un docente cargando a la vez | Un docente carga el lote de su curso; no hay cargas simultáneas en este entorno |
| Visitas al sitio | 50 primeras visitas al mes | Supuesto: docentes y evaluadores. Cada primera visita descarga el sitio completo |
| Monitor | Una consulta `HEAD /health` cada 5 minutos | [ADR-0009](../adr/0009-desplegar-la-api-en-el-servicio-web-gratuito-de-render-y-mantenerla-despierta.md) |
| Espera del worker | Una `BLPOP` cada 5 s, aunque no haya trabajo | `backend/worker/main.py` |
| Días del mes | 30 y 31 | Los dos casos, porque el cupo de horas cambia con el mes |

## 2. Los cuatro números

**Operaciones al mes**
- Cargas: 4 peticiones de lote, con 800 hojas en total.
- Monitor: 288 consultas al día, es decir 8 640 al mes (30 días) o 8 928 (31 días).
- Cola: 800 escrituras (`RPUSH`, una por hoja) y 518 400 o 535 680 `BLPOP` de la espera del
  worker. La espera es casi todo el tráfico de la cola, y el Key Value de Render no cobra por
  comando.
- Las comprobaciones de salud internas de Render no se facturan.

**Tamaño de los datos almacenados**
- Disco de la instancia de la API: hasta 160 MB al mes (4 lotes de 40 MB), más la bitácora,
  que suma unos KB. Es efímero y se borra en cada despliegue
  ([ADR-0012](../adr/0012-mantener-el-almacen-en-el-disco-efimero-de-la-instancia-hasta-cerrar-r-06.md)).
- Cola: casi vacía, porque el worker toma cada trabajo al llegar. En el peor caso, un lote
  completo con el worker detenido son 200 trabajos de unos 300 bytes: unos 60 KB de los 25 MB.
- Base de datos: 0, porque no se despliega.

**Tráfico de salida**
- Sitio: 50 primeras visitas × 0,75 MB son unos 38 MB. Los 0,75 MB se midieron sobre el sitio
  desplegado: `main.dart.js` comprimido. CanvasKit lo baja el navegador del CDN de Google, no de
  Render.
- API: 4 respuestas de lote de unos 50 KB, más las de `/health`: menos de 1 MB.
- Monitor: respuestas sin cuerpo, del orden de 2 MB al mes.
- La subida de las hojas (160 MB) es tráfico de entrada.
- Total: **unos 40 MB de salida, menos del 1 % de los 5 GB incluidos.**

**Horas de ejecución**
- API con el worker adentro: 720 h (mes de 30 días) o 744 h (mes de 31), porque el monitor la
  mantiene despierta todo el mes.
- Sitio estático: no consume horas de instancia.
- Cola: es una instancia gratuita propia (Key Value Free).
- Construcciones: la imagen de la API tarda unos 20 s (en el log del primer despliegue fue de
  19:35:06 a 19:35:24). Para el sitio, que compila Flutter, se supone una cota de 10 minutos. Cada
  servicio se reconstruye solo cuando cambia su carpeta, así que con 10 despliegues de cada uno al
  mes son unos 100 minutos de los 500.
- Integración continua: unos 84 s por run (mediana de los últimos 12 en GitHub Actions). El
  repositorio es público, así que no consume cuota de minutos.

## 3. Resultado: US$0 al mes

| Pieza | Plataforma y plan | Consumo al volumen supuesto | Costo |
|---|---|---|---|
| Sitio | Sitio estático de Render | unos 38 MB de salida | US$0 |
| API y worker | Servicio web Free de Render | 720 a 744 h de las 750 | US$0 |
| Cola | Key Value Free de Render | unos 60 KB en el peor caso; 50 conexiones | US$0 |
| Ficheros | Disco efímero de la instancia de la API | hasta 160 MB, que se borran al desplegar | US$0 |
| Base de datos | No se despliega | nada | US$0 |
| Pipeline | GitHub Actions, repositorio público | unos 84 s por run | US$0 |
| Monitor | UptimeRobot, plan gratuito | 1 de 50 monitores | US$0 |

## 4. Dónde se rompe la capa gratuita

**Con un solo servicio web despierto, hasta unas 6 600 primeras visitas al sitio y hasta unos 50
despliegues del sitio al mes, el costo sigue en cero.** A partir de ahí:

| Recurso | Cupo gratuito | Consumo supuesto | Se rompe cuando | Qué pasa y cuánto cuesta después |
|---|---|---|---|---|
| **Horas de instancia** (el primero que se rompe) | 750 h al mes por workspace, compartidas por todos los servicios web gratuitos | 720 a 744 h | Un segundo servicio web queda despierto todo el mes: el cupo se agota hacia la mitad del mes | Render suspende los servicios gratuitos hasta el mes siguiente. Para evitarlo, una instancia Starter: US$7 al mes por servicio, con tarjeta |
| Ancho de banda | 5 GB al mes | unos 40 MB | Unas 6 600 primeras visitas al sitio al mes (a 0,75 MB cada una) | US$0,15 por GB. Por ejemplo, 10 000 primeras visitas son unos 7,5 GB: 2,5 GB de más, unos US$0,38 |
| Minutos de build | 500 al mes | unos 100 | Unos 50 despliegues del sitio al mes, a 10 minutos cada uno | US$5 por cada 1000 minutos |
| Key Value | 25 MB y 50 conexiones | unos 60 KB en el peor caso | Del orden de 80 000 trabajos pendientes, que solo se acumulan con el worker detenido | Las escrituras fallan (`noeviction`) y las hojas quedan `pendiente_de_encolar`. El plan siguiente cuesta US$10 al mes (256 MB, con persistencia en disco) |
| Disco persistente | No existe en el plan gratuito | | Cuando haga falta conservar hojas entre despliegues (R-06) | US$0,25 por GB al mes, más la instancia de pago de US$7 |

**Las dos alternativas del taller frente al volumen.**
- **A, el servicio gratuito:** cuesta US$0 hasta los puntos de ruptura de arriba.
- **B, la instancia siempre encendida:** cuesta US$7 al mes desde el primer día, cualquiera sea el
  volumen.

A deja de ser la más barata solo cuando hace falta un segundo servicio siempre encendido. Con el
patrón de carga del proyecto, que son ráfagas en fechas de corte, eso no ocurre
([comparación completa](taller-despliegue-api.md)).

**La cola en Upstash, alternativa descartada en
[ADR-0011](../adr/0011-consumir-la-cola-desde-la-instancia-de-la-api-con-el-key-value-gratuito.md):**
su plan gratuito da 500 000 comandos al mes, y la espera del worker sola hace 518 400 o 535 680.
Se rompería sin ninguna carga.

## 5. Lo que no es dinero

- **Integración continua:** unos 84 s por run y sin cuota de minutos, porque el repositorio es
  público.
- **Despliegue:** no hay despliegue manual. Render despliega solo los commits cuyo CI termina en
  verde (`autoDeployTrigger: checksPass`) y solo el servicio cuya carpeta cambió.
- **Cuánta gente sabe rehacerlo:** el workspace gratuito de Render tiene un solo puesto, así que
  hoy lo opera una sola persona (riesgo R-16). Cualquier integrante puede recrear el entorno en su
  propia cuenta desde `render.yaml`, siguiendo la sección «Cómo se despliega» del
  [README](../../README.md).
- **Latencia:** si se apaga el monitor, el costo pasa a ser de tiempo. La primera petición después
  de 15 minutos sin tráfico tarda 12,5 s
  ([medición](../evidencia/medicion-arranque-en-frio.json)).
- **Dependencia de terceros:** el monitor depende del plan gratuito de UptimeRobot, y todo el
  entorno depende de que Render mantenga su capa gratuita (R-15).

## 6. Cómo recalcular

- **Horas al mes** = horas del mes × servicios web despiertos todo el mes. Tiene que quedar en 750
  o menos.
- **Salida al mes (MB)** ≈ primeras visitas × 0,75 + lotes × 0,05 + 2 (monitor). Tiene que
  quedar en 5 000 o menos.
- **Minutos de build al mes** ≈ despliegues del sitio × 10 + despliegues de la API × 0,3. Tiene
  que quedar en 500 o menos.
- **Comandos de la cola al mes** = 12 × 60 × 24 × días (espera) + hojas del mes.

## Fuentes

- Render, precios (planes, ancho de banda, minutos de build, disco, Key Value): https://render.com/pricing, consultada el 27-sep-2026
- Render, capa gratuita (750 h por workspace, apagado a los 15 minutos, sin disco persistente): https://render.com/docs/free
- Render, planes de Key Value (25 MB y 50 conexiones en el gratuito): https://render.com/docs/compute-plans
- UptimeRobot, plan gratuito (50 monitores, cada 5 minutos, sin tarjeta): https://uptimerobot.com/pricing/
- Upstash, plan gratuito (500 000 comandos al mes): https://upstash.com/docs/redis/overall/pricing
- Medición del arranque en frío: [`medicion-arranque-en-frio.json`](../evidencia/medicion-arranque-en-frio.json)
- Peso del sitio: medido el 27-sep-2026 descargando `main.dart.js` de https://quantia-utb.onrender.com con compresión (724 523 bytes)
