# Hallazgos de código y sus correcciones

Los hallazgos que SonarQube Cloud reportó sobre la rama `master`, repartidos en tres instantáneas
(seguridad, fiabilidad y mantenibilidad). Encontró **trece hallazgos**, todos con archivo y línea,
y **los trece quedaron corregidos** en esta misma entrega: ninguno se aceptó sin arreglar. Una de
esas correcciones, la de AE-12, rompió la herramienta que mide EC-07 y se revirtió después; está
explicado al final de este documento. El equipo se los repartió, la instantánea de seguridad la trabajó Sebastián y las de fiabilidad y
mantenibilidad, Susana.

Esta revisión es **automática**: encuentra patrones de código que una herramienta reconoce sin
conocer el dominio. Es distinta del recorrido **manual** de propiedad de datos, que pregunta qué
módulo decide el contenido de cada campo de negocio y vive en
la [sección 8.3 del arc42](../arc42/arc42-template-ES.md#83-propiedad-de-datos). Las dos recorren el
mismo código y no se sustituyen: ninguna herramienta conoce la regla de dueño único, y la
herramienta encuentra cosas que un recorrido a mano no busca.

Cada fila dice dónde estaba el hallazgo, cuál era el error y cómo se corrigió, con el commit que lo
implementa. El pipeline quedó en verde después de cada uno.

---

Las trece, con dónde estaba cada una, qué era el error y cómo se corrigió. Todas verificables en el
historial: el commit que las arregla está en la última columna y el pipeline quedó en verde después
de cada uno.

### Instantánea de seguridad (diez hallazgos)

| ID | Dónde estaba | Cuál era el error | Cómo se arregló | Commit |
|---|---|---|---|---|
| AE-1 | `.github/workflows/ci.yml`, paso de `pip install` | `pip install -r` sin `--only-binary :all:` permite instalar distribuciones de código fuente, y un `setup.py` de cualquier dependencia se ejecuta durante la instalación, dentro del pipeline | Se agregó `--only-binary :all:` al comando: solo se instalan ruedas ya compiladas, que no ejecutan código al instalarse | [`523e05a`](https://github.com/ISCOUTB/AS_202620_Sistema-de-calificacion-automatica/commit/523e05a), corregido el YAML en [`c150707`](https://github.com/ISCOUTB/AS_202620_Sistema-de-calificacion-automatica/commit/c150707) |
| AE-2 | `.github/workflows/ci.yml`, los cuatro `uses:` | Las acciones se referenciaban por etiqueta (`actions/checkout@v4`, `setup-python@v5`, `flutter-action@v2`). Una etiqueta se puede mover a otro commit sin avisar, así que el pipeline ejecutaba código que podía cambiar bajo los pies del equipo | Cada acción quedó fijada a su SHA completo, con la etiqueta como comentario para saber qué versión es | [`8d671cd`](https://github.com/ISCOUTB/AS_202620_Sistema-de-calificacion-automatica/commit/8d671cd) |
| AE-3 | `.github/workflows/ci.yml`, paso de `pip install` | Se instalaban las dependencias sin fijar las versiones resueltas ni verificar su contenido: dos ejecuciones del mismo commit podían traer paquetes distintos | Se agregó `--require-hashes`, y `requirements.txt` pasó a ser un lock con hashes generado con `pip-compile --generate-hashes`, quedando `requirements.in` con la intención | [`58600e5`](https://github.com/ISCOUTB/AS_202620_Sistema-de-calificacion-automatica/commit/58600e5) |
| AE-4 | `.github/workflows/ci.yml`, paso de `flutter pub get` | Mismo problema del lado de Dart: `flutter pub get` a secas resuelve versiones nuevas aunque exista `pubspec.lock` | Se agregó `--enforce-lockfile` | [`601a92d`](https://github.com/ISCOUTB/AS_202620_Sistema-de-calificacion-automatica/commit/601a92d) |
| AE-5 | `backend/Dockerfile`, línea del `COPY` | `COPY . .` copiaba el contexto completo a la imagen, incluido lo que no hace falta para ejecutar y lo que pudiera contener datos sensibles | Se sustituyó por un `COPY` explícito por paquete: los nueve módulos del backend más `worker`, `tests` y `pytest.ini` | [`a9a4b4f`](https://github.com/ISCOUTB/AS_202620_Sistema-de-calificacion-automatica/commit/a9a4b4f) |
| AE-6 | `backend/Dockerfile`, línea 4 | El mismo `pip install` sin `--only-binary :all:` que AE-1, esta vez dentro de la imagen | Se agregó `--only-binary :all:` | [`523e05a`](https://github.com/ISCOUTB/AS_202620_Sistema-de-calificacion-automatica/commit/523e05a) |
| AE-7 | `backend/Dockerfile`, línea 4 | El mismo problema de versiones sin fijar que AE-3, dentro de la imagen | Se agregó `--require-hashes` sobre el mismo lock | [`58600e5`](https://github.com/ISCOUTB/AS_202620_Sistema-de-calificacion-automatica/commit/58600e5) |
| AE-8 | `backend/Dockerfile`, ausencia de `USER` | La imagen `python` corre como `root` por omisión, así que el proceso de la API tenía privilegios que no necesita | Se crea `appuser` (uid 10001), se le da la propiedad de `/app` y del directorio del almacén, y se declara `USER appuser` antes del `CMD` | [`c8230dd`](https://github.com/ISCOUTB/AS_202620_Sistema-de-calificacion-automatica/commit/c8230dd) |
| AE-9 | `frontend/Dockerfile`, línea del `flutter pub get` | El mismo problema de AE-4, dentro de la imagen | Se agregó `--enforce-lockfile` | [`601a92d`](https://github.com/ISCOUTB/AS_202620_Sistema-de-calificacion-automatica/commit/601a92d), restablecido tras fijar el SDK en [`7d80188`](https://github.com/ISCOUTB/AS_202620_Sistema-de-calificacion-automatica/commit/7d80188) |
| AE-10 | `frontend/Dockerfile`, etapa final | La imagen `nginx` corre como `root` por omisión | Se cambió la imagen final a `nginxinc/nginx-unprivileged:alpine`, con `USER nginx` y `EXPOSE 8080`, y se ajustó el mapeo de puertos del `docker-compose.yml`, porque un nginx sin privilegios no puede escuchar en el 80 | [`1f7c22e`](https://github.com/ISCOUTB/AS_202620_Sistema-de-calificacion-automatica/commit/1f7c22e) |

### Instantáneas de fiabilidad y mantenibilidad (tres hallazgos)

| ID | Dónde estaba | Cuál era el error | Cómo se arregló | Commit |
|---|---|---|---|---|
| AE-11 | `frontend/web/index.html`, línea 2 | El elemento `<html>` no declaraba idioma. Sin `lang`, un lector de pantalla no sabe en qué idioma pronunciar el contenido, y se incumple el criterio 3.1.1 de WCAG 2.1 | Se reemplazó `<html>` por `<html lang="es">`, porque todo el contenido visible de la aplicación está en español | [`99101dd`](https://github.com/ISCOUTB/AS_202620_Sistema-de-calificacion-automatica/commit/99101dd) |
| AE-12 | `backend/herramientas/medir_ec07.py`, línea 84 (`ColaEnMemoria.rpush`) | El parámetro `cola` estaba en la firma y no se usaba en el cuerpo (`python:S1172`). Un parámetro muerto sugiere una dependencia que no existe y confunde sobre la intención de la función | Se quitó el parámetro de la firma y se actualizaron las llamadas para que dejen de pasarlo. La función no cambia de comportamiento, solo de interfaz | [`20b25ec`](https://github.com/ISCOUTB/AS_202620_Sistema-de-calificacion-automatica/commit/20b25ec), revertida después ([ver el final](#una-corrección-que-rompió-la-herramienta-de-medición-ae-12)) |
| AE-13 | `frontend/Dockerfile`, línea 7 | `${BACKEND_URL}` sin comillas en el `RUN` del build (`docker:S6570`): el shell puede partir el valor o expandir rutas | Se envolvió la variable entre comillas dobles | [`2c77bff`](https://github.com/ISCOUTB/AS_202620_Sistema-de-calificacion-automatica/commit/2c77bff) |

**Una observación que la herramienta no hizo y conviene dejar escrita.** El patrón que AE-5 corrigió
en `backend/Dockerfile` sigue presente en `frontend/Dockerfile` línea 30, donde el `COPY . .` de la
etapa de build no se marcó. Ahí está acotado por `frontend/.dockerignore` y por tratarse de una
etapa intermedia cuyo resultado no llega a la imagen final, que solo recibe
`/app/build/web`. Queda anotado porque la ausencia de alerta no es lo mismo que la ausencia del
patrón.

---

## Una corrección que rompió la herramienta de medición (AE-12)

**Qué pasó.** AE-12 quitó el parámetro `cola` de `ColaEnMemoria.rpush` porque el cuerpo del
método no lo usaba. Pero `medir_ec07.py` no llama a ese método: le entrega `ColaEnMemoria` al
endpoint real como si fuera el cliente de Redis, y quien lo invoca es `publicar`, en
`backend/infraestructura/cola.py` (línea 55), con la firma de redis-py: `rpush(cola, valor)`. El
parámetro no se usaba adentro, pero era parte de lo que se espera desde afuera. Desde
[`20b25ec`](https://github.com/ISCOUTB/AS_202620_Sistema-de-calificacion-automatica/commit/20b25ec)
la herramienta terminaba en `TypeError: ColaEnMemoria.rpush() takes 2 positional arguments but 3
were given` antes de producir ninguna cifra, y nada lo detectaba: ninguna prueba la ejecutaba, y
la fila de AE-12 decía que la función no cambiaba de comportamiento.

**Cómo se encontró.** Ejecutando la herramienta, no leyéndola. Una auditoría de coherencia del
repositorio (22 de septiembre) corrió `python -m herramientas.medir_ec07` para comprobar que la
evidencia de EC-07 seguía siendo reproducible, y no lo era.

**Cómo se corrigió.**

- Se devolvió el parámetro, con un comentario que explica por qué está ahí y un `# NOSONAR` en esa
  línea, para que el aviso `python:S1172` no vuelva a proponer quitarlo. Queda como un aviso
  aceptado con su motivo, no como uno ignorado.
- Se agregó [`backend/tests/test_medir_ec07.py`](../../backend/tests/test_medir_ec07.py): tres
  pruebas que corren las dos mediciones con lotes de pocas hojas. Con la firma rota, las tres
  fallan con el mismo `TypeError`. El pipeline las corre en cada push, dentro de la suite del
  backend.
- La herramienta volvió a medir. Con su configuración por omisión (200 hojas de 200 KB) confirmó
  el lote en menos de un segundo con 0 % de pérdida silenciosa, y en 7,9 s con la cola caída a
  mitad del lote, dentro del techo de 10 s de EC-07.

**Lo que enseña.** Un parámetro que el cuerpo de una función no usa puede ser obligatorio desde
afuera, cuando la función cumple una interfaz que otro código invoca; aquí, la del cliente de
Redis. Una herramienta que solo mira el cuerpo no ve esa relación, y una corrección que la sigue
al pie de la letra la rompe. Por eso lo que se corrige se ejecuta, y si una prueba debía
detectarlo, se provoca la falla.
