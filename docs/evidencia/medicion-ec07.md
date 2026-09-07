# Medición de EC-07 sobre el aspecto A-01

Este documento es la evidencia de calidad del aspecto [A-01](../aspectos.md#a-01). Contiene la
línea base medida antes del cambio del primer corte, el resultado posterior y el procedimiento
para repetir ambos. La decisión que separa una medición de la otra es
[ADR-0006](../adr/0006-registrar-la-recepcion-en-una-bitacora-antes-de-encolar.md).

Lo que se mide es el escenario [EC-07](../arc42/arc42-template-ES.md#ec-07), que pide dos cosas
de la carga de un lote de hasta 200 hojas escaneadas:

1. **Confirmación de recepción del lote en ≤ 10 segundos.**
2. **0 % de pérdida silenciosa:** todo archivo cargado queda registrado como *aceptado* o como
   *rechazado con motivo*.

---

## Resultado

| Medida de EC-07 | Umbral | Antes (`cede35e`) | Después (`ADR-0006`) | |
|---|---|---|---|---|
| Confirmación del lote de 200 hojas, operación normal (peor de 3 corridas) | ≤ 10 s | 0,126 s | 1,744 s | cumple |
| Confirmación del lote de 200 hojas, con la cola caída | ≤ 10 s | no aplica (devolvía 500) | 7,842 s | cumple |
| Pérdida silenciosa con la cola cayendo en la hoja 101 | 0 % | **100 %** | **0 %** | corregido |

Desglose de la segunda fila, que es donde estaba el defecto:

| | Antes | Después |
|---|---|---|
| Código HTTP que recibe el docente | 500 | 200 |
| Hojas del lote reportadas | 0 de 200 | 200 de 200 |
| Trabajos encolados que el docente no puede conocer | 100 | 0 |
| Hojas recuperables sin volver a pedirle el archivo al docente | no existía el registro | 100 |
| Archivos escritos en el almacén | 101 | 201 (200 hojas + la bitácora) |

Informes en crudo: [`medicion-ec07-antes.json`](medicion-ec07-antes.json) ·
[`medicion-ec07-despues.json`](medicion-ec07-despues.json) ·
[`medicion-ec07-cola-caida.json`](medicion-ec07-cola-caida.json).

### El camino de fallo, y por qué tiene su propia cifra

La segunda fila de la tabla apareció después de probar el sistema completo con Docker, y no
estaba en la primera versión de esta medición. Al detener el contenedor de Redis y subir una
hoja, la bitácora la registró a las `03:43:20,135` y la respuesta salió a las `03:43:27,279`:
**7,1 segundos para una sola hoja**, contra los 20 ms que cuesta cuando la cola responde. Esa
diferencia es el tiempo que tarda el cliente de Redis en rendirse buscando un servidor que no
está.

La consecuencia era seria y la medición original no la vio, porque la cola sustituta fallaba de
inmediato: reintentar hoja por hoja habría costado 200 tiempos de espera, unos 1.420 segundos
por aritmética (200 × 7,1 s), casi veinticuatro minutos, para terminar en el mismo estado. La
corrección es el punto 3b de ADR-0006: tras el primer fallo el lote deja de tocar la cola.
Medido con la demora simulada, un lote de 200 hojas con la cola caída desde el principio
confirma en **7,842 s con un solo intento**.

El margen ahí es de 22 %, no del 83 % del camino normal, y no lo controla el equipo: lo fija el
tiempo de espera del cliente de Redis. Está declarado como tal en las consecuencias de
ADR-0006.

---

## Cómo repetir la medición

```bash
cd backend
pip install -r requirements.txt
python -m herramientas.medir_ec07 --hojas 200 --kb 200 --repeticiones 3 --fallar-en 100
python -m herramientas.medir_ec07 --fallar-en 0 --repeticiones 1   # peor caso: cola caida
```

No hace falta Docker ni Redis. La herramienta es
[`backend/herramientas/medir_ec07.py`](../../backend/herramientas/medir_ec07.py) y admite
`--json ruta.json` para guardar el informe.

**La misma herramienta corre sobre el estado anterior**, y es a propósito: si la cifra de antes
saliera de un procedimiento distinto que la de después, la comparación no valdría nada. La
herramienta detecta si la bitácora existe y se adapta, así que la línea base se obtiene
clonando el repositorio en el commit anterior y copiándole el directorio `herramientas`:

```bash
git clone <este repositorio> base && cd base && git checkout cede35e
cp -r ../backend/herramientas backend/herramientas
cd backend && python -m herramientas.medir_ec07
```

### Carga

- **200 hojas** por lote, que es el tope que declara EC-07.
- **200 KB por hoja**, JPEG con cabecera válida. El tamaño está en el orden de un escaneo real
  a 200 ppp en escala de grises, y la cabecera tiene que ser válida porque `ingesta` verifica
  los primeros bytes: con relleno arbitrario se estaría midiendo el camino de rechazo.
- **39,1 MB** por lote.
- **3 repeticiones**, y se reporta la peor, no la media. Un escenario de calidad se incumple en
  el peor caso, no en el promedio.

### Entorno de la corrida registrada

| | |
|---|---|
| Fecha | 2026-09-07 (UTC) |
| Python | 3.10.12 |
| Sistema | Linux 6.8.0-136-generic, x86_64 |
| Sistema de archivos del almacén | ext4 sobre disco, **no** `tmpfs` |

---

## Qué recorre la medición y qué no

**Lo que sí.** Se ejerce el endpoint real `POST /examenes/{id}/hojas` a través de `TestClient`,
de modo que el recorrido pasa por `api` → `ingesta` → `infraestructura.almacen` →
`infraestructura.bitacora`. El almacén es el adaptador real `AlmacenEnDisco` y la bitácora es
`BitacoraEnDisco`: las escrituras a disco son reales y cuentan en el tiempo. Se cronometra la
petición HTTP completa, que es lo que el docente espera frente a la pantalla.

**Lo que no, y conviene declararlo en vez de esconderlo:**

- **La cola es una sustituta en memoria, no un Redis real.** La cifra de latencia no incluye la
  ida y vuelta de red hacia Redis, así que es una **cota inferior** del tiempo real. Se hizo así
  por dos razones: la medición tiene que poder repetirse sin levantar contenedores, y la segunda
  medición necesita provocar el fallo en una hoja exacta del lote.
- **No se mide la durabilidad ante la caída del sistema operativo.** `BitacoraEnDisco` llama a
  `fsync` en cada línea, que es la defensa correcta, pero comprobarla exigiría cortarle la
  corriente a la máquina. Lo que sí se prueba es que el estado vive en el archivo y no en el
  objeto que lo escribió, que es la condición necesaria.
- **No se mide el recorrido hasta el worker.** El corte vertical de A-01 termina en el encolado;
  el procesamiento es el aspecto A-02.
- **La cifra de 0,126 s de la línea base incluía margen prestado.** Sin bitácora, el sistema
  confirmaba antes de que el sistema operativo hubiera llevado nada al disco. Comparar 0,126 con
  1,744 compara una promesa débil con una fuerte.

---

## Pruebas que cubren el cambio

[`backend/tests/test_durabilidad_recepcion.py`](../../backend/tests/test_durabilidad_recepcion.py),
13 pruebas. Se validaron **provocando la falla**, según la convención del equipo: una prueba que
nunca falló no prueba nada.

| Mutación aplicada a una copia del código | Pruebas que se ponen en rojo |
|---|---|
| Se quita el `try/except` de `recibir_lote`, de modo que la cola vuelva a tumbar el lote | 8 de 13 |
| Se quita la llamada a `bitacora.registrar` antes de publicar | 4 de 13 |
| `pendientes()` devuelve siempre la lista vacía | 2 de 13 |
| La bitácora abre el archivo en modo `w` en vez de `a`, sobrescribiendo | 3 de 13 |
| Se quita el corte del lote, de modo que se reintente contra una cola caída | 2 de 13 |
| `worker/main.py` vuelve al literal `"procesamiento"` en vez de leer el entorno | **ninguna** |

La última fila es un hueco declarado, no un descuido: ninguna prueba vigila que la API y el
worker usen el mismo nombre de cola, porque comprobarlo exige los dos procesos levantados. Está
anotado como tal en ADR-0006, en la sección de costos asumidos.

**Suite completa:** 46 pruebas de backend pasan y 1 se salta (`test_encolado.py`, que necesita
un Redis real). Con Redis disponible corren las 47, que es lo que hace el CI y lo que se
verificó con `docker compose run --rm --build api pytest -q`. Antes del cambio eran 33 y 1.
