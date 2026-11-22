# 0025 · Identificar al docente con una sesión firmada y una lista de cuentas

- **Estado:** aceptado
- **Fecha:** 2026-11-21
- **Decide:** Josué Ortega De Arco, María Restrepo Licona, Sebastián Cañas Plata, Susana Rosales Castellar
- **Escenarios de calidad relacionados:** [EC-06](../arc42/arc42-template-ES.md#ec-06) (aislamiento por curso y por rol), en su primera mitad: que solo entre quien tiene cuenta
- **Riesgos y amenazas:** AM-02 y AM-08 del [modelo de amenazas](../evidencia/modelo-de-amenazas.md), R-14 y R-17; abre R-38 a R-40
- **Restricciones que lo acotan:** RF-09 (solo usuarios registrados), RF-10 (quién modificó una nota y cuándo), RNF-05 (el usuario es el docente, no el estudiante), RNF-11 (ningún secreto en el repositorio), RNF-12 (datos personales), RNF-15 (trazabilidad de la nota)
- **Relación con otros ADR:** no reemplaza a ninguno. Completa lo que [ADR-0023](0023-leer-las-hojas-en-posiciones-fijas-y-mandar-a-revision-lo-que-no-se-ve-bien.md) dejó para A-05, quién resuelve cada revisión, y guarda sus secretos en el panel de [ADR-0021](0021-desplegar-en-el-servidor-del-laboratorio-con-el-sitio-compilado-en-el-ci.md), como ya se hacía con `LLM_API_KEY`.

**La decisión, en una frase:** la API solo atiende a un docente que entró con su correo y su
contraseña; las cuentas viven cifradas en una variable del servidor, la entrada devuelve un token
firmado que vence a las 12 horas, y todas las rutas lo piden salvo la sonda de vida y las métricas.

---

## Contexto

Hasta ahora todas las rutas de la API eran públicas. Con la URL, cualquiera cargaba hojas, veía las
notas de un examen y resolvía una revisión con el nombre que quisiera, sin que nadie lo verificara
(RF-10). La amenaza AM-02 se aceptó con una condición: ninguna hoja real entra mientras sea así.

Dos cosas del final la volvieron urgente. La revisión muestra, en esta misma rama, el código del
estudiante junto al nombre de la hoja, porque es como el docente sabe de quién es. Y la presentación
es ante jurados que van a abrir el sistema como un cliente nuevo. El equipo trajo un diseño de la
pantalla de entrada hecho en Stitch.

Lo que había: el módulo `identidad`, declarado en ADR-0002 y vacío; un sitio en Flutter compilado a
web, servido en `calificacion.iscoutb.dev`, que llama a la API en otro nombre,
`api-calificacion.iscoutb.dev`; y un panel de Dokploy donde ya vivía el único secreto del sistema.

## Alternativas consideradas

### 1. Dónde viven las cuentas

| Alternativa | A favor | En contra |
|---|---|---|
| **Una lista cifrada en una variable del servidor (`DOCENTES`)** | Sin tabla, migraciones ni pantalla de registro; el secreto queda junto al otro | Agregar o quitar un docente es cambiar la variable y desplegar |
| Una tabla en Postgres | Altas y bajas sin desplegar | Postgres está declarado y sin uso (R-06): estrenarlo con las cuentas sería decidir la persistencia de paso |
| Entrar con la cuenta de la UTB (Microsoft 365 o SAVIO) | El docente no necesita otra contraseña | La aplicación la tiene que registrar TI de la universidad, y eso no está a nuestro alcance antes de la entrega |

### 2. Cómo viaja la sesión

| Alternativa | A favor | En contra |
|---|---|---|
| **Un token en `Authorization: Bearer`** | Lo mandan todos los servicios por un mismo cliente HTTP, y también los recortes | El sitio lo guarda en el almacenamiento del navegador (R-40) |
| Una cookie `HttpOnly` | Ningún script de la página la lee | En web, Flutter baja las imágenes por XHR sin credenciales: la cookie no llegaría a la ruta del recorte y la revisión se quedaría sin imágenes. Lo comprobamos en el SDK (`_network_image_web.dart`) |
| Una sesión guardada en el servidor | Se puede cerrar al instante | Un estado más que guardar; la lista ya permite cerrarle la puerta a alguien (punto 3 de la decisión) |

### 3. El token y las contraseñas

| Alternativa | A favor | En contra |
|---|---|---|
| **Token firmado con HMAC-SHA256 y contraseñas con scrypt, de la biblioteca estándar** | Ninguna dependencia nueva en un backend que se instala con `--require-hashes` y pasa por OSV-Scanner | Un formato propio, que solo lee nuestra API |
| JWT con PyJWT, y bcrypt o Argon2 | Formatos conocidos | Dependencias nuevas para un token que nadie fuera del sistema lee |

### 4. Qué rutas quedan abiertas

`GET` y `HEAD /health`, que consultan el monitor y Traefik; `POST /sesion`, para entrar; y
`GET /metricas`, que solo publica cuentas de los presupuestos y la caché (AM-09). Todo lo demás pide
sesión.

## Decisión

1. **Las cuentas.** `DOCENTES` lleva una entrada `correo=cifrada` por docente, separadas por comas.
   La cifrada es scrypt (n = 2^14, r = 8) con sal propia, en un formato sin `$` ni comas, porque
   compose interpreta `$` en el `.env` que escribe Dokploy. La imprime
   `python -m herramientas.crear_docente correo`, que pide la contraseña dos veces y no la guarda.
2. **La entrada.** `POST /sesion` recibe el correo y la contraseña. Un correo sin cuenta y una
   contraseña equivocada responden igual, «Correo o contraseña incorrectos», y cuestan lo mismo: en
   los dos casos se verifica una contraseña con scrypt. El registro anota `sesion_iniciada` o
   `entrada_rechazada`, sin el correo.
3. **El token.** Lleva el correo y el vencimiento, firmados con `SESION_SECRETO`, y vence a las
   `SESION_HORAS` (12). En cada petición la API comprueba la firma, el vencimiento y que el correo
   **siga** en la lista: quitar a alguien de `DOCENTES` y desplegar le cierra la puerta sin esperar a
   que el token venza, y cambiar el secreto cierra todas las sesiones.
4. **Las rutas.** Todas, salvo las cuatro de arriba, responden 401 sin un token válido. La prueba no
   las enumera a mano: recorre las de la aplicación, así que una ruta nueva sin sesión la pone en rojo.
5. **Quién resuelve.** El autor de cada resolución de RF-08 es el correo de la sesión. La solicitud ya
   no lleva `por`, y si llega uno se ignora.
6. **El código del estudiante, solo con sesión.** La revisión publica el código leído de cada hoja,
   para que el docente sepa de quién es. Las notas, los recortes y el registro siguen sin él.
7. **Falla cerrado.** Sin secreto o sin lista, nadie entra (`POST /sesion` responde 503) y `/health`
   sigue igual. Con una lista mal escrita tampoco entra nadie, y el registro dice qué entrada falla
   por su posición, sin el correo.
8. **El sitio.** Empieza en la pantalla de entrada, con el diseño del equipo sin lo que el sistema no
   hace: entrar con SAVIO o Microsoft 365 y recuperar la contraseña. Los servicios mandan el token
   por un mismo cliente, y los recortes, como encabezado de la imagen. Un 401 vuelve a la entrada con
   «Su sesión terminó». «Recordar sesión en este dispositivo» guarda el token en `localStorage`, y
   sin marcarla, en `sessionStorage`. Cerrar sesión pide confirmación.
9. **El contrato sube a 2.0.0**: un cliente de 1.8.0 recibe 401 donde antes recibía 200.

## Consecuencias

### Positivas

- **AM-02 se cierra en lo que dependía de no tener cuentas:** sin una, nadie carga, ve notas o
  códigos, ni resuelve revisiones.
- **RF-10 se cumple en la revisión:** cada resolución queda con el correo de quien entró (AM-08, en
  esa parte).
- **R-14 y R-17 se cierran:** la carga y los distractores dejan de ser rutas públicas.
- **Ninguna dependencia nueva.**

### Negativas y consecuencias asumidas

- **Sin aislamiento por curso (EC-06).** Todo docente con cuenta ve todos los exámenes, porque el
  sistema todavía no tiene cursos (A-04). Por eso la condición de AM-02 sigue: solo hojas sintéticas.
- **Sin límite de intentos (R-38).** Probar contraseñas solo lo frenan scrypt, unos 50 ms por
  intento, y el mínimo de 10 caracteres.
- **El token no se revoca antes de vencer (R-39)** salvo quitando la cuenta o cambiando el secreto, y
  las dos cosas piden un despliegue.
- **El token está al alcance de los scripts de la página (R-40).** Se acepta porque el sitio no
  muestra HTML de terceros ni de usuarios y el token vence a las 12 horas.
- **La carga no registra quién subió cada lote**, lo que queda de AM-08: la ruta pide sesión, pero la
  bitácora no guarda el correo.
- **Las herramientas de medición** que van por URL necesitan un token en `QUANTIA_TOKEN`; las que
  hablan con la aplicación en el mismo proceso sustituyen la sesión.
- **Antes de desplegar**, `SESION_SECRETO` y `DOCENTES` tienen que estar en el panel. Sin ellas, el
  sitio se queda en la pantalla de entrada.

## Reversión

El token y la cifrada solo los leen la API y `herramientas/crear_docente.py`. Pasar a JWT, a una
cookie o a una tabla de cuentas toca `identidad`, `api/main.py` y el cliente del sitio, sin migrar
datos: lo único guardado es la lista. Volver a rutas públicas es quitarles la dependencia, y reabre
AM-02 completa.

## Qué dato haría revisar esta decisión

- **Más de cinco docentes**, o altas y bajas más de una vez por semana: la lista pasa a una tabla.
- **Intentos rechazados seguidos** en el registro (`entrada_rechazada`): un límite de intentos.
- **Un segundo curso:** roles y aislamiento por curso (EC-06).
- **Que TI de la UTB registre la aplicación:** entrar con la cuenta institucional.

## Cómo se comprobó

- **Backend:** `test_identidad.py` (cifrar, firmar y leer la lista; tokens vencidos, alterados, con
  otro secreto o con caracteres que no son ASCII), `test_crear_docente.py`, `test_sesion.py` (la
  entrada, la configuración que falta, que toda ruta no pública responda 401, el preflight de CORS
  con `authorization` y el registro sin correo ni contraseña), `test_ruta_revision.py` (quien
  resuelve es el docente de la sesión) y `test_contrato.py` (cada ruta declara su seguridad y su
  401).
- **Sitio:** `sesion_test.dart`, `pantalla_entrada_test.dart`, `servicios_con_sesion_test.dart` (cada
  servicio manda el token, y un 401 cierra la sesión), `app_test.dart` y `revision_test.dart`.
- **Con uvicorn de verdad**, en un contenedor: sin token, 401; con la contraseña equivocada, 401 sin
  decir si el correo existe; con token, 200; con el token alterado, 401; el preflight admite
  `authorization`; `/health` y `/metricas`, 200; y el registro no tiene el correo ni la contraseña.
- **En local, con el sistema completo** levantado con compose y una cuenta generada con
  `crear_docente`: la API lee la lista y el secreto del `.env`, el sitio servido es el de la entrada,
  y un token firmado con ese secreto abre las rutas.

## Trazabilidad

- **Código:** `backend/identidad/` (`contrasenas.py`, `sesiones.py` y `docentes.py`),
  `backend/api/main.py` (`POST /sesion` y `docente_de_la_sesion`), `backend/api/settings.py`,
  `backend/api/esquemas.py`, `backend/herramientas/crear_docente.py` y
  `backend/herramientas/sesion.py`; en el sitio, `lib/common/api/sesion.dart`,
  `lib/common/api/cliente_con_sesion.dart`, `lib/app/sesion_actual.dart`,
  `lib/app/almacen_de_sesion*.dart`, `lib/features/sesion/views/pantalla_entrada.dart`,
  `lib/app/app.dart` y `lib/app/barra_superior.dart`.
- **Despliegue:** `deploy/compose.lab.yaml`, `docker-compose.yml` y los dos `.env.example`.
- **Contrato:** `docs/contrato/openapi.json`, versión 2.0.0.
