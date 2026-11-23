# 0027 · Guardar los registros en Postgres detrás de los mismos puertos

- **Estado:** aceptado
- **Fecha:** 2026-11-22
- **Decide:** Josué Ortega De Arco, María Restrepo Licona, Sebastián Cañas Plata, Susana Rosales Castellar
- **Riesgos:** cierra en parte R-06 (la decisión de persistencia) y V-4 (la bitácora en disco supone un solo proceso escritor)
- **Relación con otros ADR:** cambia el medio de los registros de [ADR-0006](0006-registrar-la-recepcion-en-una-bitacora-antes-de-encolar.md) (bitácora), [ADR-0018](0018-dar-a-la-hoja-una-identidad-propia-y-derivar-su-estado-de-la-bitacora.md) y [ADR-0023](0023-leer-las-hojas-en-posiciones-fijas-y-mandar-a-revision-lo-que-no-se-ve-bien.md) (resultados y revisiones) sin cambiar lo que deciden: los registros siguen siendo de solo agregado y con un único escritor cada uno.

**La decisión, en una frase:** la bitácora de recepción, el registro de resultados y el de
revisiones se guardan en Postgres cuando existe `DATABASE_URL`, con un adaptador nuevo para cada
puerto que ya existía; sin `DATABASE_URL`, siguen siendo archivos `.jsonl`.

---

## Contexto

Desde la S2, el Nivel 2 del C4 y el `docker-compose.yml` declaran una base de datos, pero ningún
módulo la usaba: los tres registros eran archivos `.jsonl` en el volumen de las hojas, con
adaptadores marcados como provisionales hasta resolver R-06. Esos archivos tienen tres límites:
cada consulta recorre el archivo entero, solo admiten un proceso escritor por archivo (V-4), y no
se pueden consultar fuera de la aplicación.

Los tres registros ya estaban detrás de puertos (`BitacoraDeRecepcion`, `LectorDeRecepciones`,
`RegistroDeResultados`, `LectorDeResultados`, `RegistroDeRevisiones`, `LectorDeRevisiones`), y la
API y el worker eligen el adaptador en un solo lugar cada uno. Cambiar el medio es escribir un
adaptador, no tocar a quien lo usa.

## Alternativas consideradas

| Alternativa | A favor | En contra | Resultado |
|---|---|---|---|
| **Seguir con archivos** | Nada que cambiar | Los tres límites de arriba; el C4 declara una base que no existe | Descartada |
| **Un esquema relacional completo** (una tabla por pregunta, por burbuja, por resolución) con un ORM | Consultas finas | Reescribe la serialización y obliga a migraciones; mucho cambio para el cierre del curso | Descartada por ahora |
| **Una tabla por registro, de solo agregado, con el hecho completo en `jsonb`** y las columnas que se consultan sueltas | Los adaptadores devuelven exactamente lo mismo que en disco, así que las pruebas de los puertos valen para los dos; consultas por examen con índice | El detalle de cada pregunta queda dentro del documento | **Elegida** |
| **Una base gestionada** (Supabase, Neon) en vez de un contenedor | Sin contenedor que cuidar | Los datos salen del servidor del laboratorio; depende de una cuenta externa | Posible sin cambiar código: basta con su `DATABASE_URL` |

## Decisión

1. **`infraestructura/base_de_datos.py`** con tres adaptadores, `BitacoraEnPostgres`,
   `ResultadosEnPostgres` y `RevisionesEnPostgres`, y el esquema (`ESQUEMA`): tres tablas de solo
   agregado, `bitacora_de_recepcion`, `resultados_de_lectura` y `revisiones_del_profesor`. Cada
   fila es un hecho. Los resultados guardan además `estado`, `nota_en_decimas` y `provisional` en
   columnas, para consultarlos sin abrir el documento.
2. **El mismo documento que en disco.** Los dos adaptadores arman cada hecho con las mismas
   funciones (`hecho_de_lectura`, `hecho_ilegible`, `hecho_de_resoluciones`), así que leen lo
   mismo. `tests/test_base_de_datos.py` lo comprueba con una base real: la misma secuencia de
   hechos, en disco y en Postgres, da el mismo resultado.
3. **La elección, por configuración.** `DATABASE_URL` en la API (`api/settings.py`) y en el
   worker. Sin ella, todo sigue en archivos, que es lo que usan las pruebas que no miden la base.
4. **El esquema lo crea la aplicación** la primera vez que se conecta, con `CREATE TABLE IF NOT
   EXISTS`. No hay migraciones que correr a mano.
5. **Conexiones reusadas:** cada proceso guarda hasta cuatro conexiones libres por base y presta
   una por operación, con su transacción, después de comprobar que responde. Abrir una conexión
   por operación hizo que un lote de 200 hojas tardara 8,8 s en confirmarse con la API en
   media CPU y pasara el plazo de 8 s de la recepción: 55 hojas quedaron pendientes de
   encolar. Sin sentencias preparadas, para que funcione también detrás de un pooler. Un fallo
   de conexión sube como `ConnectionError` (un `OSError`), que el worker ya trata como
   transitorio y reintenta (ADR-0020).
6. **Siguen siendo archivos** las imágenes de las hojas y sus recortes (el almacén) y las claves
   de respuestas, que registra la aplicación ([ADR-0026](0026-registrar-y-habilitar-la-clave-desde-la-aplicacion.md)).
7. **En los entornos:** en local, el `postgres` del `docker-compose.yml` ya existía y ahora la API
   y el worker esperan a que esté sano. En el servidor del laboratorio entra como quinto
   contenedor (`db`, 192 MB; el total queda en 768 MB de 1 GB), con la contraseña en Dokploy →
   Environment como `POSTGRES_PASSWORD`. El CI levanta un Postgres para las pruebas.
8. **Lo que ya estaba en archivos** se copia una vez con `herramientas/migrar_a_postgres.py`. En el
   servidor la corre la API al arrancar, con `--si-hace-falta`, que migra solo si la bitácora de
   la base está vacía. Corrida a mano, se niega si las tablas ya tienen datos.

## Consecuencias

### Positivas

- **Medido en Docker con el compose del servidor y sus límites** ([evidencia](../evidencia/base-de-datos.md)):
  un lote de 200 hojas se confirma en 1,2 y 2,8 s, sin hojas pendientes de encolar, y se procesa en
  4,9 y 5,0 min; la base llegó a 12,1 MiB de sus 192 MB. Lo que estaba en los `.jsonl` pasa a la base
  y la API devuelve exactamente lo mismo antes y después.
- Las consultas por examen usan un índice en vez de recorrer un archivo.
- La API y el worker pueden escribir desde contenedores distintos sin compartir un archivo (V-4).
- Los resultados se pueden consultar con SQL, por ejemplo
  `SELECT hoja_id, estado, nota_en_decimas FROM resultados_de_lectura WHERE examen_id = '…'`.
- Volver a los archivos es quitar `DATABASE_URL`.

### Negativas y consecuencias asumidas

- **Un contenedor más** en el servidor: 5 de los 6 de la cuota y 768 MB de 1 GB.
- **Las cifras de EC-01 a EC-04 y EC-07 del arc42 se midieron con archivos.** Con la base, el
  lote de 200 hojas se midió dos veces, no tres, y en un computador.
- **Si la base se cae**, la carga de hojas falla (la bitácora no se puede escribir) y el worker
  reintenta. `/health` no consulta la base todavía.
- **Sin migraciones versionadas:** un cambio de esquema futuro tendrá que agregarlas.
- **Sin política de retención** (RNF-14): sigue abierta, ahora sobre tablas.

## Reversión

- Quitar `DATABASE_URL` de la API y del worker: vuelven a los archivos del volumen, que siguen
  ahí. Lo escrito en Postgres mientras tanto no se copia de vuelta.

## Trazabilidad

- **Código:** `backend/infraestructura/base_de_datos.py`, `backend/api/main.py`
  (`obtener_bitacora`, `obtener_lector_de_recepciones`, `obtener_lector_de_resultados`,
  `obtener_revisiones`), `backend/api/settings.py`, `backend/worker/main.py` (`ejecutar`),
  `backend/herramientas/migrar_a_postgres.py`.
- **Pruebas:** `backend/tests/test_base_de_datos.py` y `backend/tests/test_migrar_a_postgres.py`
  (corren con `DATABASE_URL_PRUEBAS`).
- **Evidencia:** [`docs/evidencia/base-de-datos.md`](../evidencia/base-de-datos.md).
- **Configuración:** `docker-compose.yml`, `deploy/compose.lab.yaml`, `.github/workflows/ci.yml`,
  `backend/requirements.in` (`psycopg[binary]`).
