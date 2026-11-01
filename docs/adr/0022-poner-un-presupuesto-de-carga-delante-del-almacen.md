# 0022 · Poner un presupuesto de carga delante del almacén

- **Estado:** aceptado
- **Fecha:** 2026-10-31
- **Decide:** Josué Ortega De Arco, María Restrepo Licona, Sebastián Cañas Plata, Susana Rosales Castellar
- **Amenaza relacionada:** AM-01 del modelo de amenazas de la S13 (`docs/evidencia/modelo-de-amenazas.md`), la primera en prioridad
- **Restricciones que lo acotan:** RNF-16 (US$0 y sin tarjeta); `identidad` (A-05) sin construir
- **Relación con otros ADR:** sigue el patrón de [ADR-0015](0015-limitar-el-gasto-del-proveedor-de-llm-con-un-presupuesto-en-la-api.md) sin reemplazar a ninguno; mitiga R-14 y R-31 en el entorno de [ADR-0021](0021-desplegar-en-el-servidor-del-laboratorio-con-el-sitio-compilado-en-el-ci.md)

**La decisión, en una frase:** antes de leer la primera hoja, cada lote de
`POST /examenes/{examen_id}/hojas` tiene que caber en un presupuesto de 250 hojas por lote y 256 MB
por 24 horas, que vive en la memoria de la API, y ningún cuerpo de petición pasa de 100 MB; lo que
no cabe se responde con 413 o con 429 y `Retry-After`, sin que ninguna hoja llegue al almacén.

---

## Contexto

**La amenaza.** La ruta de carga es pública y no tiene autenticación (R-14), y desde ADR-0021 lo que
acepta queda en el volumen `almacen_imagenes`, sobre el disco de 200 GB que comparten los 23 equipos
del servidor del laboratorio hasta el 30-nov (R-31). El modelo de amenazas de la S13 la puso primera
(AM-01, denegación de servicio sobre la relación 3 del Nivel 2 del C4): probabilidad media, porque la
URL de la API está en el README público, e impacto alto, porque llenar el disco no nos tumba solo a
nosotros, sino a los otros 22 equipos.

**Lo que había.** Un solo tope: 20 MB por hoja (`ingesta/recepcion.py`). Nada limitaba cuántas hojas
traía un lote (Starlette admite hasta 1 000 archivos por formulario) ni cuántos lotes llegaban en un
día. La firma de los primeros bytes no frena a nadie que quiera llenar el disco: basta con empezar
cada archivo con `%PDF-`. Cloudflare corta cada petición en 100 MB, así que unas 2 000 peticiones
llenaban el disco. Y Cloudflare solo ve lo que pasa por él: la IP del servidor es pública y Traefik
atiende sin tope a quien llegue directo, que es como lo probamos desde la UTB (R-30). Por ese camino,
una sola petición sin límite se guardaba entera en los temporales de Starlette, en el mismo disco,
antes de que la ruta la viera.

**Fuerzas:**

- **RNF-16:** la solución no puede costar dinero.
- **`identidad` (A-05) no existe**, así que no hay un cupo por docente que asignar.
- **Una sola instancia de la API con un solo proceso de uvicorn** (ADR-0021).
- **Traefik y Cloudflare son del curso:** no podemos configurarlos.
- **EC-07 no puede empeorar:** un lote de un corte (200 hojas) tiene que seguir entrando igual.

## Alternativas consideradas

### 1. Dónde poner el freno

| Alternativa | A favor | En contra | Resultado |
|---|---|---|---|
| **No hacer nada** | Cero código | El disco de 23 equipos queda a merced de una ruta pública | Descartada |
| **Límite en Traefik o en Cloudflare** | Corta antes de llegar a la API | Son del curso. Cloudflare ya corta en 100 MB por petición, pero no cuenta peticiones ni cubre el camino directo a la IP | No disponible |
| **Límite por IP** | Reparte el cupo entre clientes | Detrás de Cloudflare y del Traefik del curso, la IP que ve la API es la de un proxy o la que dice `X-Forwarded-For`, que la API acepta de cualquier origen (`deploy/compose.lab.yaml`); cuál de las dos depende de una configuración de Traefik que no es nuestra. Y veinte IP lo saltan | Descartada |
| **Cuota total del volumen** | Ataca el disco directamente | Medir el volumen es recorrerlo en cada lote; el espacio libre del disco es el de todos los equipos; y sin retención (R-06) solo crece | Descartada por ahora |
| **Presupuesto en la memoria de la API: hojas por lote, bytes por día y tope del cuerpo** | Sin dependencias ni red; mismo patrón que ADR-0015; acota el peor caso | Global, no por docente; se vacía con cada despliegue | **Elegida** |
| **El mismo presupuesto en Redis** | En el servidor Redis persiste con AOF (ADR-0021): sobreviviría a los despliegues | Si Redis cae, la carga tiene que seguir (ADR-0006), y el presupuesto necesitaría su propio plan de degradación | Descartada por ahora |
| **Autenticación** (A-05) | Es lo que cierra R-14 de verdad, con un cupo por docente | `identidad` está vacío: no cabe en la semana | Prevista |

### 2. Qué contar

| Alternativa | Resultado | Por qué |
|---|---|---|
| **Lo que se guarda, hoja por hoja** | Descartada | Cortaría a mitad de lote: el docente recibiría un lote a medias y tendría que averiguar qué faltó, que es lo que EC-07 evita |
| **Los bytes del lote al subir, antes de procesarlo** | **Elegida** | Se sabe antes de leer la primera hoja, y el lote cabe entero o no entra. Cuenta también lo que la validación rechace después, porque igual viajó |

### 3. Qué responder

| Alternativa | Resultado | Por qué |
|---|---|---|
| **200 con cada hoja rechazada por presupuesto** | Descartada | Es la respuesta a medias de arriba |
| **413 para lo que no se arregla esperando, 429 con `Retry-After` para lo que sí** | **Elegida** | Un lote de 300 hojas no va a caber nunca: hay que dividirlo. Uno que no cabe hoy cabe cuando salgan de la ventana los lotes de ayer, y la cabecera dice cuándo. Es aditivo en el contrato |

## Decisión

1. **El presupuesto vive en `ingesta`**, en [`ingesta/presupuesto.py`](../../backend/ingesta/presupuesto.py),
   con la biblioteca estándar. La ruta lo consulta en `cargar_hojas` antes de leer la primera hoja;
   `recibir_lote` no cambia.
2. **Dos topes:** 250 hojas por lote y 256 MB en una ventana deslizante de 24 horas. Se configuran
   con `CARGA_HOJAS_POR_LOTE` y `CARGA_MB_POR_DIA` (en el servidor, en `deploy/compose.lab.yaml`).
   Los valores por omisión se declaran una sola vez, en `ingesta`, y `api/settings.py` los lee de
   ahí.
3. **Se reserva el lote entero**, con lo que pesó al subir, antes de procesarlo.
4. **413** si el lote trae más de 250 hojas o pesa más que el cupo de un día; **429 con
   `Retry-After`** si no cabe en lo que queda del cupo. En los dos casos el motivo va en `detail` y
   ninguna hoja llega al almacén, a la bitácora ni a la cola.
5. **Ningún cuerpo de petición pasa de 100 MB**, el mismo tope que pone Cloudflare: un middleware
   ([`api/limite_del_cuerpo.py`](../../backend/api/limite_del_cuerpo.py)) responde 413 si el
   `Content-Length` declarado lo pasa, y si no se declara, cuenta los bytes mientras llegan y corta
   al pasarlo. Va por dentro de CORS, para que el sitio pueda leer el 413.
6. **La reserva es atómica** (`threading.Lock`), porque cada lote se confirma en un hilo aparte.
7. **Observabilidad:** cada lote cortado deja un evento `lote_demasiado_grande` o
   `carga_diaria_agotada` en el registro JSON, y `GET /metricas` publica `presupuesto_de_carga`: los
   bytes de las últimas 24 horas y los lotes admitidos y cortados.
8. **El contrato pasa a 1.5.0**: agrega el 413 y el 429 de la ruta de carga y el estado en
   `GET /metricas`. Es un cambio menor porque solo agrega.
9. **Vive en la memoria del proceso de la API**, como el presupuesto del proveedor (ADR-0015).

**De dónde salen los números.** 250 hojas dejan un cuarto de margen sobre las 200 de un corte
(EC-07). 256 MB son entre tres y seis lotes de un corte con escaneos de 200 a 400 KB (40 a 80 MB
cada uno). Con el cupo lleno todos los días hasta el 30-nov, son unos 7,5 GB, menos de lo que le toca
a cada equipo del disco compartido (200 GB entre 23, unos 8,7 GB). Y 100 MB es lo que ya deja pasar
Cloudflare: por el camino de siempre no cambia nada, y un lote de un corte cabe holgado.

## Consecuencias

### Positivas

- **El disco compartido deja de estar a merced de la ruta pública.** Por la ruta de carga entran
  como mucho 256 MB al día, contra un disco entero en unas 2 000 peticiones antes.
- **Los temporales también tienen tope**: 100 MB por petición, también por el camino directo a la
  IP del servidor.
- **Un lote de un corte entra igual que antes**: el de EC-07 (200 hojas de 200 KB) son 40 MB.
- **US$0 y ninguna dependencia nueva.**
- **El docente sabe qué pasó**: 413 si tiene que dividir el lote, 429 con `Retry-After` si tiene que
  esperar, y en los dos casos «No entró ninguna hoja».
- **Se puede observar en vivo**, en `GET /metricas` y en el registro.
- **Cada tope tiene una prueba que falla sin él**
  ([`test_presupuesto_de_carga.py`](../../backend/tests/test_presupuesto_de_carga.py)), con la regla
  de la sección 8.4 del arc42.

### Negativas

- **El cupo es global, no por docente.** Quien quiera puede gastar el del día y dejarnos sin carga
  hasta 24 horas: la amenaza pasa de «llenar el disco de 23 equipos» a «negarle la carga a nuestro
  equipo», que es peor para nosotros y mucho mejor para el servidor. Lo cierra A-05, con un cupo
  por docente, como R-19 en el proveedor.
- **Se vacía con cada reinicio y cada despliegue**, porque vive en memoria. Cada push a `master` que
  pasa el CI devuelve el cupo entero: con diez despliegues más hasta el 30-nov, el peor caso sube de
  7,5 a unos 10 GB. Lo resuelve el presupuesto en Redis, que en el servidor sí persiste (la
  alternativa descartada por ahora).
- **El sitio muestra el código y no el motivo.** `servicio_carga.dart` trata todo 4xx igual («La API
  rechazó la petición (413). No entró ninguna hoja.»), que es cierto pero no dice si hay que dividir
  o esperar.
- **No limita la CPU** que cuesta recibir y validar lo que se rechaza. Con 0,5 CPU (R-32), una
  ráfaga de lotes cortados todavía puede volver lenta la API mientras dura.

## Reversión

1. **Ajustar los topes** es cambiar `CARGA_HOJAS_POR_LOTE` o `CARGA_MB_POR_DIA` en el panel o en
   `deploy/compose.lab.yaml` y redesplegar.
2. **Quitar el presupuesto** es quitar la llamada a `reservar` en `cargar_hojas`, y quitar el tope
   del cuerpo es quitar su `add_middleware`. El contrato conservaría el 413 y el 429 declarados sin
   usarlos, que no rompe a ningún cliente.

## Qué dato haría revisar esta decisión

- **Que se construya `identidad` (A-05):** el cupo pasa a ser por docente.
- **Que un docente real no quepa en 256 MB al día**, porque escanea a más resolución o carga varios
  cursos el mismo día: se sube el cupo y se recalcula el peor caso hasta el 30-nov.
- **Que `lotes_rechazados_desde_el_arranque` crezca sin que nadie del equipo haya cargado:** alguien
  está usando la ruta, y el presupuesto pasa a Redis para que no se reinicie con los despliegues.
- **Que la API corra en más de una instancia o con más de un proceso:** cada uno tendría su cupo, y
  el presupuesto pasa a Redis.

## Trazabilidad

- **Amenaza:** AM-01 del modelo de amenazas de la S13 (`docs/evidencia/modelo-de-amenazas.md`).
- **Riesgos:** mitiga R-14 y R-31 ([arc42 §11](../arc42/arc42-template-ES.md#11-risks-and-technical-debts)).
- **Código:** [`ingesta/presupuesto.py`](../../backend/ingesta/presupuesto.py),
  [`api/limite_del_cuerpo.py`](../../backend/api/limite_del_cuerpo.py),
  [`api/main.py`](../../backend/api/main.py) (`obtener_presupuesto_de_carga`, el 413 y el 429, y
  `GET /metricas`), [`api/esquemas.py`](../../backend/api/esquemas.py) (contrato 1.5.0) y
  [`api/settings.py`](../../backend/api/settings.py).
- **Configuración:** [`deploy/compose.lab.yaml`](../../deploy/compose.lab.yaml).
- **Pruebas:** [`test_presupuesto_de_carga.py`](../../backend/tests/test_presupuesto_de_carga.py) y
  [`test_contrato.py`](../../backend/tests/test_contrato.py).
- **C4:** relaciones 1 y 3 del Nivel 2 ([`c4/doc-c4.md`](../c4/doc-c4.md)).
