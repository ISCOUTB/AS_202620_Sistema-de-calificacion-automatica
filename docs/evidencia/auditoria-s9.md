# Auditoría de la S9: erosión, dependencias y credenciales

Revisión del código de la porción de la S9 (RF-11, aspecto A-06), hecha el 4 de octubre de 2026
sobre el código tal como se sube a `master`. Cubre las filas 7, 8 y 9 de la evidencia S9: si la
generación con IA cruzó un límite de contexto o una regla de propiedad de datos de la S6, si las
dependencias que trajo existen y son las legítimas, y si quedó alguna credencial. Los comandos se
repiten sobre `master` en la verificación final, antes del cierre.

**Resultado:** el código generado no cruzó ningún límite ni ninguna regla de propiedad. La
auditoría sí encontró un flanco en la prueba que debía detectarlo (E-1), y se corrigió. No hay
dependencias nuevas ni credenciales.

## 1. Qué se auditó

| Archivo | Qué es |
|---|---|
| [`backend/autoria/distractores.py`](../../backend/autoria/distractores.py) | Tipos, puerto y regla de qué propuestas llegan al profesor |
| [`backend/autoria/proveedor_llm.py`](../../backend/autoria/proveedor_llm.py) | Adaptador al proveedor de LLM |
| [`backend/autoria/__init__.py`](../../backend/autoria/__init__.py) | Interfaz pública del módulo y su línea `Posee:` |
| [`backend/api/main.py`](../../backend/api/main.py), [`esquemas.py`](../../backend/api/esquemas.py) y [`settings.py`](../../backend/api/settings.py) | La ruta `POST /distractores`, sus esquemas y su configuración |
| [`backend/herramientas/evaluar_distractores.py`](../../backend/herramientas/evaluar_distractores.py) | La herramienta de evaluación |

Contra qué se contrastó:
- el mapa de contextos ([arc42 §8.1](../arc42/arc42-template-ES.md#81-mapa-de-contextos)), cuya relación 5 dice que Autoría llega al proveedor de LLM por una **capa anticorrupción**;
- la regla de dueño único ([arc42 §8.3](../arc42/arc42-template-ES.md#83-propiedad-de-datos), [ADR-0007](../adr/0007-declarar-los-contextos-delimitados-y-la-regla-de-dueno-unico.md));
- la línea `Importa:` del docstring de cada módulo, que es la fuente de verdad de `test_fronteras.py`.

## 2. Límites de contexto

**Imports reales del código nuevo:**

| Archivo | Importa | ¿Dentro de lo declarado? |
|---|---|---|
| `autoria/distractores.py:24-26` | Solo la biblioteca estándar (`re`, `dataclasses`, `typing`) | Sí: no toca ningún otro módulo |
| `autoria/proveedor_llm.py:27-38` | Biblioteca estándar, `httpx` y `autoria.distractores` | Sí: `httpx` es una biblioteca externa, y lo demás es del mismo módulo |
| `autoria/__init__.py:8-17` | `autoria.distractores` y `autoria.proveedor_llm` | Sí |
| `api/main.py:34` | `autoria` | Sí: `api` es un punto de entrada y su trabajo es llamar al dominio |

`autoria` declara `Importa: infraestructura, identidad` (`autoria/__init__.py:4`) y hoy no usa
ninguno de los dos: el código nuevo no amplía la frontera.

**La capa anticorrupción se sostiene.** El formato del proveedor (`choices`, `usage`,
`prompt_tokens`) aparece solo en `autoria/proveedor_llm.py` (líneas 102, 112 y 181): fuera del
adaptador, el resto del sistema solo ve `DistractorPropuesto`. Se comprobó con
`git grep -n '"choices"\|"usage"\|prompt_tokens' -- backend ':!backend/tests'`.

**RNF-13 se sostiene.** Lo único que viaja al proveedor son los tres campos de
`PreguntaParaDistractores` (`autoria/distractores.py:42`), con la plantilla
`MENSAJE_PARA_EL_MODELO` (`autoria/proveedor_llm.py:54`). La prueba
`test_la_solicitud_solo_lleva_la_pregunta_y_las_instrucciones_fijas`
(`tests/test_proveedor_llm.py:55`) compara el cuerpo entero de la solicitud, así que un campo de más
la pone en rojo.

**El grep de la ficha** (paso 7 de la evidencia S9), sin coincidencias:

```
git grep -nIE '(INSERT INTO|UPDATE |\.save\(|\.create\(|repository\.)' HEAD -- . ':!docs'
```

El código nuevo no persiste nada: las propuestas se devuelven al profesor y no se guardan.

### E-1 · La prueba de fronteras no miraba los puntos de entrada

- **Dónde:** `backend/tests/test_fronteras.py`. La función `_imports_reales` solo buscaba imports
  hacia los siete módulos del dominio.
- **Cómo se detectó:** al recorrer los imports del adaptador. Si el adaptador hubiera leído su
  configuración con `from api.settings import LLM_MODELO`, el dominio habría quedado atado a la
  puerta HTTP, y ninguna prueba lo habría notado. Se comprobó agregando ese import: las siete
  pruebas de fronteras siguieron en verde.
- **Corrección:** `PUNTOS_DE_ENTRADA = ["api", "worker"]` (`test_fronteras.py:32`) y la prueba
  `test_ningun_modulo_del_dominio_importa_un_punto_de_entrada` (`test_fronteras.py:109`), que falla
  si un módulo del dominio importa `api` o `worker`. Se validó provocando la falla: con el mismo
  import, la prueba nueva sale roja y las siete anteriores siguen en verde.
- **Relación con V-1:** es la otra cara de V-1 (§8.3). La mitad de V-1 que sigue abierta no cambia:
  `api` y `worker` todavía no declaran su propia línea `Importa:`.

## 3. Propiedad de datos

| Entidad | Dónde | Quién decide su contenido | Dueño |
|---|---|---|---|
| `PreguntaParaDistractores` | `autoria/distractores.py:42` | El profesor la escribe; la API solo traduce la petición, igual que con `ArchivoCargado` en A-01 | `autoria` |
| `DistractorPropuesto` | `autoria/distractores.py:54` | La regla de `autoria` decide cuáles llegan al profesor | `autoria` |
| `PropuestaDescartada` | `autoria/distractores.py:63` | La regla de `autoria`, que fija el motivo | `autoria` |
| `ResultadoDePropuesta` | `autoria/distractores.py:71` | `filtrar_propuestas` | `autoria` |

- **Ninguna entidad nueva entró a `infraestructura/modelo.py`**, cuyas cinco entidades son de
  `ingesta` (§8.3). El archivo no se tocó.
- **Los esquemas de la API** (`SolicitudDeDistractores`, `RespuestaDeDistractores` y los demás de
  `api/esquemas.py`) son la forma del contrato HTTP, no entidades del dominio. Es la misma regla que
  ya declara el docstring de ese archivo.
- **`autoria` es el primer módulo que declara `Posee:`** (`autoria/__init__.py:5`). Es la mitad de la
  corrección prevista para V-5. La otra mitad, una prueba que falle si una entidad no tiene
  exactamente un dueño declarado, sigue pendiente.

Con la regla de ADR-0007 (el dueño es quien decide el contenido de los campos de negocio, no quien
los persiste), las cuatro son de `autoria` sin ambigüedad.

## 4. Dependencias

**Los manifiestos no cambiaron.** Contra el estado de la S8, el diff sale vacío:

```
git diff 1f8f76d -- backend/requirements.in backend/requirements.txt frontend/pubspec.yaml frontend/pubspec.lock
```

**Lo que la IA propuso esta semana** (según el registro de `docs/ia.md`, entrada 12):

| Propuesta | Qué se hizo | Por qué |
|---|---|---|
| `openai`, el SDK oficial | Rechazada | Obliga a regenerar el lock en Linux, y su método `chat.completions.create(` aparece en el grep de erosión del paso 7 |
| `urllib.request`, de la biblioteca estándar | Corregida: se usó `httpx` | `httpx` ya es dependencia directa del backend (`requirements.in`), así que no agrega nada y permite probar sin red con `httpx.MockTransport` |

**Cada dependencia directa del backend y la propuesta rechazada, verificadas en PyPI** el 4-oct-2026 a
las 15:17, con su API pública (`https://pypi.org/pypi/<paquete>/json`). Se comprobó el nombre exacto,
el repositorio oficial y que la versión fijada en el lock exista:

| Paquete | Versión en el lock | ¿Existe esa versión en PyPI? | Primera versión publicada | Repositorio oficial |
|---|---|---|---|---|
| `fastapi` | 0.141.1 | Sí | 2018-12-08 | github.com/fastapi/fastapi |
| `uvicorn` | 0.52.4 | Sí | 2017-06-05 | github.com/Kludex/uvicorn |
| `httpx` | 0.28.1 | Sí | 2019-07-19 | github.com/encode/httpx |
| `redis` | 8.1.0 | Sí | 2012-10-08 | github.com/redis/redis-py |
| `pytest` | 9.1.1 | Sí | 2010-11-25 | github.com/pytest-dev/pytest |
| `python-multipart` | 0.0.32 | Sí | 2013-03-26 | github.com/Kludex/python-multipart |
| `openai` (rechazada) | No está | No aplica | 2020-02-18 | github.com/openai/openai-python |

Ningún nombre es una variante parecida a la de un paquete conocido: los seis del lock son los
mismos de `requirements.in`, escritos igual que en PyPI. El frontend no cambió en la semana.

## 5. Credenciales

Los tres comandos del CONTRATO §9, sobre el código de la porción y su documentación:

| Comando | Resultado |
|---|---|
| `git grep -nIE '(AKIA[0-9A-Z]{16}\|-----BEGIN [A-Z ]*PRIVATE KEY\|ghp_[A-Za-z0-9]{36}\|xox[baprs]-\|sk-[A-Za-z0-9]{20,}\|(password\|passwd\|secret\|token\|api_?key)\s*[:=]\s*.{6,})'` | Sin coincidencias (código de salida 1, que aquí es el resultado bueno) |
| `git ls-files \| grep -E '(^\|/)\.env$'` | Sin coincidencias: no hay `.env` versionado |
| `git log --oneline -S'BEGIN PRIVATE KEY'` | Sin coincidencias en el historial |

**Dónde vive la clave del proveedor:**
- en el entorno, nunca en el código: `api/settings.py:28` la lee de `LLM_API_KEY`;
- en `.env.example:37` la variable está vacía;
- en `docker-compose.yml:42` se toma del `.env` local, que git ignora;
- en `render.yaml:55` va con `sync: false`, así que Render la pide en su panel y no pasa por el repositorio;
- las pruebas no la necesitan: ninguna sale a la red;
- la herramienta de evaluación la lee del entorno y no la escribe en su informe.

## 6. Resumen

| Hallazgo | Ubicación | Cómo se detectó | Corrección | Estado |
|---|---|---|---|---|
| E-1 · La prueba de fronteras no miraba `api` ni `worker` | `backend/tests/test_fronteras.py` | Recorrido de los imports del adaptador, y confirmado agregando un import prohibido | `test_fronteras.py:32` y `:109`, validada provocando la falla | Cerrado |
| V-5 · La regla de dueño único no la verifica ninguna prueba | `autoria/__init__.py:5` | Ya registrada en §8.3 | Primera línea `Posee:` | Abierta a medias: falta la prueba |
| Cruces de contexto del código generado | Archivos de la sección 1 | Recorrido de imports, `test_fronteras.py`, grep del paso 7 | Ninguna necesaria | Sin hallazgos |
| Dependencias nuevas | Manifiestos del backend y del frontend | `git diff` contra `1f8f76d` y PyPI | Ninguna necesaria | Sin dependencias nuevas |
| Credenciales | Todo el repositorio | Comandos del CONTRATO §9 | Ninguna necesaria | Sin credenciales |
