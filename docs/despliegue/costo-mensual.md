# Estimación de costo mensual del entorno desplegado

Estima cuánto cuesta al mes el entorno de QuantIA en el servidor del laboratorio del curso, en
iscoutb.dev. Sigue lo que pide el manual del servidor:

- los precios de la lista pública de Oracle Cloud, por OCPU-hora, por GB de RAM-hora y por GB de
  disco al mes;
- los supuestos declarados: la parte del servidor que nos corresponde y las horas al mes;
- el punto en que dejaríamos de caber.

Conserva la forma del apartado «Cómo estimar el costo mensual» de la «Guía de despliegue y costos»
del curso: supuestos, cuatro números, un resultado, el punto de ruptura y los costos que no son
dinero.

Los precios se consultaron el 29-oct-2026 en la API pública del estimador de costos de Oracle, cuya
lista se actualizó el 8-oct-2026 (fuentes al final). El despliegue está en
[`deploy/compose.lab.yaml`](../../deploy/compose.lab.yaml), en la
[sección 7 del arc42](../arc42/arc42-template-ES.md#7-deployment-view) y en
[ADR-0021](../adr/0021-desplegar-en-el-servidor-del-laboratorio-con-el-sitio-compilado-en-el-ci.md).
La restricción que fija el objetivo de US$0 es RNF-16 (costo mensual de US$0 y ninguna cuenta con
tarjeta).

## 1. Supuestos

| Supuesto | Valor | De dónde sale |
|---|---|---|
| El servidor | VM de Oracle Cloud `VM.Standard.E5.Flex` con 1 OCPU (2 vCPU) y 12 GB de RAM, en la región Phoenix, compartida entre 23 equipos | Manual del servidor, sección 5 |
| Disco del servidor | 200 GB | Aviso del panel del 29-oct (el manual decía 45 GB) |
| Nivel de rendimiento del disco | *Balanced*, 10 unidades de rendimiento (VPU) por GB | Es el nivel por omisión de los volúmenes de Oracle |
| Horas al mes | 720 (mes de 30 días) y 744 (mes de 31) | El servidor está encendido todo el mes |
| Nuestra parte, forma A | 1/23 del servidor, por partes iguales | 23 equipos |
| Nuestra parte, forma B | 1/23 de la CPU, más lo que suman nuestros límites de memoria (576 MB) y lo que ocupamos en disco (1 GB, una cota) | La CPU es compartida: los límites de 0,5 CPU son topes, no reservas. La memoria es como el docente reparte la cuota («sumando los límites») |
| Hojas por corte | 200 de 200 KB, así que un lote pesa unos 40 MB | [Ficha del problema](../ficha-problema.md) y la [medición de EC-07](../evidencia/medicion-ec07.md) |
| Lotes al mes | 4 | Tres cortes por semestre; se calcula con 4 para dejar margen |
| Visitas al sitio | 50 primeras visitas al mes | Supuesto: docentes y evaluadores |

## 2. Los cuatro números

**Operaciones al mes**
- Cargas: 4 peticiones de lote, con 800 hojas en total.
- Cola: 800 publicaciones y la espera del worker. Redis corre en nuestro contenedor y no se cobra
  por comando.
- Comprobaciones de salud: las hace Docker dentro del servidor (la API y el sitio cada 30 s, Redis
  cada 10 s) y no salen a la red. No hace falta un monitor externo, porque nada se duerme.

**Tamaño de los datos almacenados**
- Hojas y bitácora, en el volumen `almacen_imagenes`: hasta 160 MB al mes. Persisten hasta el
  30-nov-2026, cuando el servidor borra los volúmenes, así que no pasan de unos 200 MB.
- Cola, en el AOF de Redis (`datos_cola`): unos 290 bytes por trabajo, del orden de KB.
- Imágenes: la del backend (que comparten `api` y `worker`), la del sitio y la de Redis. Con los
  volúmenes, se toma 1 GB como cota de lo que ocupamos en disco.
- Base de datos: 0, porque no se despliega.

**Tráfico de salida**
- Sitio: 50 primeras visitas × 1,60 MB son unos 80 MB. Los 1,60 MB se midieron el 30-oct sobre el
  sitio desplegado ([evidencia](../evidencia/despliegue-iscoutb.md)). Cloudflare, que está delante,
  guarda en caché los archivos del sitio, así que del servidor sale menos.
- API: 4 respuestas de lote de unos 50 KB, más las de `/health` y `/metricas`: menos de 1 MB.
- Total: **unos 81 MB.** Oracle no cobra los primeros 10 TB de salida al mes.

**Horas de ejecución**
- Los cuatro contenedores, 720 o 744 h: están encendidos todo el mes.
- Compilación en el servidor: segundos por despliegue, porque Flutter no se compila ahí. El primer
  despliegue instaló las dependencias de Python en 6,9 s.
- Integración continua: 3 min 9 s el run que publicó el despliegue (Flutter se compila dos veces:
  en las pruebas y al publicar). El repositorio es público, así que no consume cuota de minutos.

## 3. Resultado: US$0 al mes para el equipo

El servidor lo paga el curso, y nadie del equipo tiene una cuenta con tarjeta: RNF-16 se cumple.
Lo que sigue es cuánto del servidor nos corresponde.

**El servidor completo:**

| Recurso | Precio | Mes de 30 días | Mes de 31 días |
|---|---|---|---|
| CPU: 1 OCPU | US$0,03 por OCPU-hora | US$21,60 | US$22,32 |
| Memoria: 12 GB | US$0,002 por GB-hora | US$17,28 | US$17,86 |
| Disco: 200 GB | US$0,0255 por GB al mes, más 10 VPU × US$0,0017 | US$8,50 | US$8,50 |
| Salida | Gratis hasta 10 TB al mes | US$0 | US$0 |
| **Total** | | **US$47,38** | **US$48,68** |

**Nuestra parte:**

| Forma | Cálculo, mes de 31 días | Mes de 30 días | Mes de 31 días |
|---|---|---|---|
| A, partes iguales | US$48,68 / 23 | US$2,06 | US$2,12 |
| B, por recursos | CPU: US$0,03 / 23 × 744 = US$0,97. Memoria: 0,5625 GB × US$0,002 × 744 = US$0,84. Disco: 1 GB × US$0,0425 = US$0,04 | US$1,79 | US$1,85 |

**Unos US$2 al mes**, por cualquiera de las dos formas. Oracle cobra la VM entera, se use o no: esta
parte es una forma de repartir el costo, no lo que pagaría el curso de menos si no estuviéramos.

| Pieza | Dónde corre | Límite | Costo para el equipo |
|---|---|---|---|
| Sitio | Contenedor `web` (nginx) | 32 MB, 0,25 CPU | US$0 |
| API | Contenedor `api` | 384 MB, 0,50 CPU | US$0 |
| Worker | Contenedor `worker` | 96 MB, 0,25 CPU | US$0 |
| Cola | Contenedor `redis`, con AOF | 64 MB, 0,25 CPU | US$0 |
| Ficheros | Volumen `almacen_imagenes` | hasta unos 200 MB | US$0 |
| Base de datos | No se despliega | | US$0 |
| Pipeline | GitHub Actions, repositorio público | unos 3 min por run | US$0 |

## 4. Dónde dejaríamos de caber

**Con la cuota del equipo, el entorno de hoy cabe con margen: usa 4 de 6 contenedores y 576 MB de
1 GB.** Lo primero que se rompe no es la memoria sino la CPU de un contenedor, con varios lotes a la
vez:

| Recurso | Cuota | Uso | Se rompe cuando | Qué pasa |
|---|---|---|---|---|
| **CPU de la API** (lo primero que se rompe) | 0,5 CPU por contenedor | Un lote de EC-07 la ocupa unos segundos | Cinco lotes de 200 hojas a la vez: tardan 11 s y vence el plazo de 8 s del lote | Entre el 8 y el 30 % de las hojas quedan `pendiente_de_encolar`, guardadas y en la bitácora (R-32). Con tres lotes a la vez no pasa |
| Memoria (suma de los límites) | 1 GB (el manual todavía dice 512 MB) | 576 MB | La base de datos de R-06 y el worker leyendo marcas con A-02 piden más de los 448 MB que quedan | Hay que bajar límites o sacar una pieza. Si un contenedor pasa su propio límite, el kernel lo mata y Docker lo reinicia |
| Contenedores | 6 (el manual todavía dice 4) | 4 | La base de datos y un segundo worker ocupan los dos que quedan; un séptimo no cabe | |
| Disco | 200 GB para 23 equipos, sin cuota publicada por equipo (unos 8,7 GB en promedio) | menos de 1 GB | Unos 200 lotes de 40 MB | No se alcanza antes del 30-nov |
| Tiempo | Los volúmenes se borran después del 30-nov-2026 | | El 30-nov | El entorno termina con el curso (R-31) |

**Si se aplica la cuota escrita en el manual** (512 MB), la API vuelve a 256 MB y el total queda en
448 MB. Aguanta tres lotes de EC-07 a la vez con margen y queda justa con cinco (251 MiB de 256).

## 5. Lo que no es dinero

- **Integración continua:** unos 3 minutos por push a `master`, sin cuota de minutos, porque el
  repositorio es público.
- **Despliegue:** no hay despliegue manual. El panel despliega solo lo que pasó el CI, y lo hace en
  cada push a `master`, también en uno de documentación. Si otros equipos están compilando, espera
  turno: hay 2 compilaciones simultáneas para todo el servidor.
- **Cuánta gente sabe rehacerlo:** los cuatro integrantes entran al panel con su correo
  institucional, y los pasos están en «Cómo se despliega» del [README](../../README.md).
- **Latencia:** no hay arranque en frío. Desde Colombia, `/health` responde con p95 de 0,53 s,
  pasando por Cloudflare hasta Phoenix.
- **Dependencias:** el servidor del curso no hace copias de seguridad y se borra el 30-nov (R-31), y
  la red de la UTB no resuelve `*.iscoutb.dev` (R-30).

## 6. Cómo recalcular

- **Servidor al mes (US$)** = (OCPU × 0,03 + GB de RAM × 0,002) × horas + GB de disco × 0,0425.
- **Nuestra parte, forma A** = servidor al mes / número de equipos.
- **Nuestra parte, forma B** = 0,03 / número de equipos × horas + GB de nuestros límites × 0,002 ×
  horas + GB que ocupamos × 0,0425.
- **Memoria** = suma de los `deploy.resources.limits.memory` de `compose.lab.yaml`. Tiene que quedar
  dentro de la cuota.

## 7. El entorno anterior, en Render

Del 27-sep al 29-oct el entorno corrió en la capa gratuita de Render, también por US$0. Su primer
punto de ruptura eran las 750 h de instancia del workspace, de las que la API, despierta con un
monitor, gastaba 720 a 744. La estimación completa está en el historial de este archivo (commit
`58147b8`). Render sigue arriba, sin cambios, hasta que el docente confirme las filas de despliegue
de la S8; mientras tanto, sigue en US$0.

## Fuentes

- Manual del servidor del laboratorio (la VM, la cuota y las reglas): https://github.com/ISCOUTB/iscoutb.dev, README, sección 5, y `docs/politicas-uso.md`
- Oracle Cloud, API pública del estimador de costos, consultada el 29-oct-2026 (lista actualizada el 8-oct-2026):
  - CPU E5, US$0,03 por OCPU-hora: https://apexapps.oracle.com/pls/apex/cetools/api/v1/products/?currencyCode=USD&partNumber=B97384
  - Memoria E5, US$0,002 por GB-hora: https://apexapps.oracle.com/pls/apex/cetools/api/v1/products/?currencyCode=USD&partNumber=B97385
  - Disco, US$0,0255 por GB al mes: https://apexapps.oracle.com/pls/apex/cetools/api/v1/products/?currencyCode=USD&partNumber=B91961
  - Rendimiento del disco, US$0,0017 por VPU y GB al mes: https://apexapps.oracle.com/pls/apex/cetools/api/v1/products/?currencyCode=USD&partNumber=B91962
  - Salida, gratis hasta 10 240 GB al mes y US$0,0085 por GB después: https://apexapps.oracle.com/pls/apex/cetools/api/v1/products/?currencyCode=USD&partNumber=B88327
- Oracle Cloud, niveles de rendimiento de los volúmenes (*Balanced*, 10 VPU por GB, por omisión): https://docs.oracle.com/en-us/iaas/Content/Block/Concepts/blockvolumeperformance.htm
- Peso del sitio, latencia de `/health` y límites de memoria medidos: [`despliegue-iscoutb.md`](../evidencia/despliegue-iscoutb.md)
