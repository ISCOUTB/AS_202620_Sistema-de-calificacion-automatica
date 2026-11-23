# La base de datos (ADR-0027)

Esta es la evidencia de [ADR-0027](../adr/0027-guardar-los-registros-en-postgres-detras-de-los-mismos-puertos.md):
la bitácora de recepción, los resultados de lectura y las revisiones del profesor se guardan en
Postgres cuando existe `DATABASE_URL`, detrás de los mismos puertos que antes escribían archivos.
Lo que había que mostrar es que **el sistema hace lo mismo con la base que con los archivos**, que
lo que ya estaba en archivos pasa a la base sin perder nada, y que el compose del servidor funciona
con sus límites de memoria y CPU.

---

## Resultado

| Qué | Cómo | Resultado |
|---|---|---|
| Los adaptadores de Postgres devuelven lo mismo que los de disco | `tests/test_base_de_datos.py`, contra Postgres 16: la misma secuencia de hechos en los dos | **9 de 9** |
| La migración deja en la base lo mismo que había en los archivos | `tests/test_migrar_a_postgres.py`, con una línea truncada a propósito | **1 de 1** |
| La suite completa del backend | `pytest` con Postgres y Redis, y `mypy` | **587 pasan**, 2 se saltan (las fotos de R-05, que no están en el repositorio); `mypy` sin errores en 111 archivos |
| La migración en el compose del servidor | 8 hojas y una revisión con archivos; después la base y `migrar_a_postgres` | La API devuelve **exactamente lo mismo** antes y después; una segunda corrida se niega y no duplica |
| La migración al arrancar, sin pasos a mano | Otro proyecto con volúmenes nuevos: 6 hojas y una revisión con archivos, y después la base | La API migró sola al arrancar y devuelve **lo mismo**; al reiniciarla no hizo nada, y las hojas nuevas fueron solo a la base |
| Un lote de 200 hojas en el compose del servidor, dos corridas | `medir_procesamiento`, con los límites de CPU y memoria de `compose.lab.yaml` | Confirmado en **1,2 y 2,8 s**, con **0 hojas pendientes de encolar**; procesado en **4,9 y 5,0 min** |
| La memoria de la base durante el lote | La memoria anónima del cgroup de `db`, cada 0,1 s | **12,1 MiB** de sus 192 MB |

---

## 1. Dónde se probó

En un computador con Docker, con `deploy/compose.lab.yaml`, el mismo archivo que despliega Dokploy,
y `deploy/compose.local-override.yaml`, que publica la API en `127.0.0.1`. Así corren los cinco
contenedores con los límites del servidor: la API con 0,5 CPU y 384 MB, el worker con 0,25 CPU y
96 MB, y `db` con 0,5 CPU y 192 MB. Las variables del panel (`SESION_SECRETO`, `DOCENTES` y
`POSTGRES_PASSWORD`) se pusieron con valores de prueba. Todas las hojas son sintéticas.

## 2. La migración: el servidor de hoy y el de mañana

1. **Sin base, como corre hoy el servidor.** Con `DATABASE_URL` vacía, se entró con una cuenta de
   prueba, se registró y habilitó la clave del examen por la API, se subieron 8 hojas sintéticas y
   se guardó la revisión de una pregunta. Quedaron en los tres `.jsonl` del volumen: 16 hechos en
   la bitácora, 8 resultados y 1 revisión.
2. **Con la base, como quedará después del despliegue.** Al poner `DATABASE_URL`, la API dejó de
   ver las 8 hojas: las tablas estaban vacías. Es lo que pasará en el servidor si nadie migra.
3. **`python -m herramientas.migrar_a_postgres`** dentro del contenedor de la API copió los 16, 8 y
   1 hechos, sin líneas saltadas. Los resultados y la revisión que devuelve la API quedaron
   **idénticos** a los del paso 1, comparados como JSON.
4. Una segunda corrida se negó: «las tablas ya tienen datos: no se migra para no duplicar».

**En el servidor no hay que correrla a mano.** `deploy/compose.lab.yaml` arranca la API con
`migrar_a_postgres --si-hace-falta`, que migra solo si la bitácora de la base está vacía. Se
probó en un proyecto aparte, con volúmenes nuevos: 6 hojas y una revisión con archivos; al poner
la base, la API copió 12, 6 y 1 hechos antes de atender, y devolvió lo mismo que antes. Al
reiniciarla respondió «la bitácora de la base ya tiene datos» y no copió nada. Cuatro hojas
nuevas quedaron en las tablas, y los `.jsonl` no crecieron.

## 3. Lo que encontró el lote de 200 hojas

La primera versión abría una conexión nueva a Postgres por cada operación. Con la API en media
CPU, un lote de 200 hojas tardó **8,8 s** en confirmarse y pasó el plazo de 8 s que la
recepción da al lote: **55 de las 200 hojas quedaron pendientes de encolar**, y esas no
se reintentan solas. Con archivos, el mismo lote no deja ninguna.

Ahora cada proceso guarda hasta cuatro conexiones libres y las reusa, comprobando que responden
antes de prestarlas. `test_cien_operaciones_no_abren_cien_conexiones` falló con la versión anterior
(100 conexiones para 100 operaciones) y pasa con esta; `test_si_la_base_corta_una_conexion_la_siguiente_operacion_abre_otra`
cubre el reinicio de la base. Con ese cambio, el mismo lote se confirmó en **1,2 y 2,8 s**, sin hojas
pendientes, y el worker lo terminó en **4,9 y 5,0 min** (dos corridas).

Ese tiempo es casi todo lectura: cada hoja tardó 1,4 s en el worker (p50), y 200 lecturas suman
unos 280 s; la base y la cola agregan segundos en todo el lote. La S14 midió 3,6 min con
archivos. La lectura salió más lenta en esta corrida, y la lectura no pasa por la base.

## 4. Para repetirla

Con Docker, desde la raíz del repositorio, el compose del servidor con un `deploy/.env` de prueba
(que git ignora) con `SESION_SECRETO`, `DOCENTES` y `POSTGRES_PASSWORD`:

    docker compose -p calificacion-lab --env-file deploy/.env \
      -f deploy/compose.lab.yaml -f deploy/compose.local-override.yaml up -d --build

La carga de un lote, con el token de una sesión en `QUANTIA_TOKEN` y la clave del examen ya
registrada y habilitada en la aplicación:

    docker compose -p calificacion-lab exec -e QUANTIA_TOKEN api \
      python -m herramientas.medir_procesamiento cargar --url http://localhost:8000 \
      --examen PARCIAL-1 --hojas 200

Las pruebas, desde `backend/`, con un Postgres que se pueda vaciar:

    DATABASE_URL_PRUEBAS=postgresql://postgres:postgres@localhost:5432/pruebas \
        python -m pytest tests/test_base_de_datos.py tests/test_migrar_a_postgres.py

## 5. Lo que queda abierto

- **El lote se midió dos veces, no tres,** y en un computador, no en el servidor. Las cifras de
  EC-01 a EC-04 y EC-07 del arc42 siguen siendo las medidas con archivos.
- **`/health` no consulta la base**: si se cae, la carga falla y el worker reintenta, pero la URL
  sigue respondiendo.
- **La migración automática supone que la cola está vacía al desplegar.** Si el worker procesara
  una hoja vieja antes de que la API migre, su resultado nuevo quedaría antes que los copiados.
- **Sin migraciones versionadas ni política de retención** (RNF-14).
