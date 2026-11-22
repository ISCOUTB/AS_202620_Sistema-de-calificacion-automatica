# 0026 · Registrar y habilitar la clave desde la aplicación

- **Estado:** aceptado
- **Fecha:** 2026-11-22
- **Decide:** Josué Ortega De Arco, María Restrepo Licona, Sebastián Cañas Plata, Susana Rosales Castellar
- **Escenarios de calidad relacionados:** [EC-05](../arc42/arc42-template-ES.md#ec-05) (habilitación registrada de cada examen)
- **Riesgos y amenazas:** R-35 y AM-17 del [modelo de amenazas](../evidencia/modelo-de-amenazas.md)
- **Restricciones que lo acotan:** RF-07 (habilitación explícita, con autor y fecha, antes de calificar), RNF-15 (una nota no cambia en silencio), el formato de hoja v1 (40 preguntas de A a D)
- **Relación con otros ADR:** no reemplaza a ninguno. Escribe la clave que [ADR-0023](0023-leer-las-hojas-en-posiciones-fijas-y-mandar-a-revision-lo-que-no-se-ve-bien.md) dejó como dato escrito a mano, y usa la sesión de [ADR-0025](0025-identificar-al-docente-con-una-sesion-firmada-y-una-lista-de-cuentas.md) para saber quién la habilita.

**La decisión, en una frase:** el docente registra la clave de un examen en la pantalla de pauta y la
habilita a su nombre; la clave se puede cambiar mientras ninguna hoja del examen tenga nota, y
cambiarla la deja sin habilitar.

---

## Contexto

Desde A-03 el worker califica con la clave de cada examen, pero esa clave se escribía a mano en un
JSON y se copiaba al volumen por consola (R-35). La pantalla de pauta mostraba una clave de ejemplo.
Ante un jurado, el paso con que empieza la historia del producto, «el profesor registra su clave y la
habilita», no se podía hacer desde la aplicación.

Con ADR-0025 la API sabe quién es el docente, así que la habilitación puede quedar con su correo y
la hora, que es lo que pide RF-07 y mide EC-05.

## Alternativas consideradas

### 1. Cuándo se puede cambiar una clave

| Alternativa | A favor | En contra |
|---|---|---|
| **Mientras ninguna hoja del examen tenga nota** | Corrige un error de tipeo hasta el último momento útil | Después de la primera nota, un error se arregla fuera de la aplicación |
| Nunca, una vez habilitada | Lo más simple | Un error de tipeo después de habilitar solo se arregla por consola, aunque no se haya leído nada |
| Siempre, recalculando las notas | Lo más cómodo | Toca el registro de resultados y las revisiones ya resueltas; mucho trabajo y riesgo para la entrega |

Las notas se calculan al leer cada hoja y no se recalculan solas. Cambiar la clave después dejaría
hojas calificadas con dos claves distintas, y esa es la nota equivocada en silencio que QG-3 prohíbe.

### 2. Cómo se escriben las respuestas

Una cuadrícula de 40 filas con A, B, C y D, como la de la revisión, y además un campo para pegar las
respuestas, que muestra en un cuadro «1. A, 2. B, …» para confirmarlas antes de llenar la cuadrícula.
Lo decidió Sebastián: la cuadrícula no deja escribir una letra que la hoja no tiene, y pegar ahorra
cuarenta toques a quien ya tiene la clave escrita.

### 3. Qué queda fuera

El banco de preguntas (RF-06): sus enunciados y opciones no los usa la calificación. Las preguntas de
la pantalla de pauta siguen de ejemplo, porque son las que alimentan el generador de distractores.
Los pesos distintos de 1 también quedan fuera: la hoja no los muestra, y el formato los sigue
admitiendo en un archivo escrito a mano.

## Decisión

1. **Tres rutas, con sesión:** `GET /examenes/{examen_id}/clave` devuelve las respuestas, quién la
   habilitó y si todavía se puede cambiar; `PUT` la registra; y `POST .../clave/habilitacion` la
   habilita a nombre del docente de la sesión y con la hora. Es la única ruta que publica las
   respuestas correctas, y solo a quien entró; la revisión y la lista de exámenes siguen sin ellas.
2. **Lo que es una clave válida lo decide `autoria`** (`registro_de_claves.py`): de 1 a 40 respuestas,
   cada una entre A y D, con peso 1, y un identificador de examen con letras sin acento, dígitos,
   guiones y guiones bajos. Lo que no cumple responde 422 con un motivo para el docente.
3. **Se cambia mientras ninguna hoja tenga nota.** Una hoja leída sin clave habilitada no cuenta,
   porque no tiene nota. Después responde 409.
4. **Cambiarla la deja sin habilitar.** La habilitación certifica unas respuestas concretas.
5. **Habilitar dos veces no cambia nada:** quién y cuándo quedan como la primera vez.
6. **El adaptador escribe completo o nada:** `ClavesEnDisco.guardar` escribe un temporal y lo pone en
   su lugar con `os.replace`, en la misma forma que el worker ya lee. El worker no cambia.
7. **En el sitio,** la tarjeta «Clave del examen» de Pauta & IA, y la carga y la revisión vuelven a
   pedir la lista de exámenes cuando se guarda o se habilita una clave.

## Consecuencias

### Positivas

- **R-35 se cierra:** la clave ya no se copia a mano al volumen.
- **EC-05 se cumple por construcción:** cada examen habilitado desde la aplicación tiene el correo de
  quien lo habilitó y la hora.
- **AM-17 se reduce:** cambiar una clave desde la aplicación pide sesión y deja de valer después de la
  primera nota.

### Negativas y consecuencias asumidas

- **Un error en la clave después de la primera nota no se corrige desde la aplicación.** Hay que
  hacerlo a mano, y volver a subir las hojas.
- **Las hojas leídas antes de habilitar no reciben nota:** hay que volver a subirlas. El cuadro de
  habilitar lo dice.
- **El banco de preguntas sigue sin construir** (RF-06), y A-04 queda construido en parte.
- **Quien llega al volumen todavía puede cambiar el archivo de la clave** (lo que queda de AM-17).

## Reversión

Volver a escribir la clave a mano sigue funcionando: el archivo tiene la misma forma. Quitar las rutas
y la tarjeta no toca ningún dato guardado.

## Qué dato haría revisar esta decisión

- **Un docente que necesite corregir una clave con hojas ya calificadas:** recalcular las notas con la
  clave nueva, con su propio ADR.
- **Exámenes con preguntas de distinto peso:** pesos en la cuadrícula.

## Cómo se comprobó

- **Backend:** `test_registro_de_claves.py` (la clave válida, el identificador, habilitar a nombre del
  docente, cambiarla con y sin hojas calificadas, y la escritura completa o nada) y
  `test_ruta_clave.py` (las tres rutas, el 404, el 422 con su motivo, el 409 y el registro sin el
  correo); `test_sesion.py` exige 401 sin sesión también en estas rutas.
- **Sitio:** `servicio_clave_test.dart`, `clave_test.dart` (la cuadrícula, pegar y confirmar,
  guardar, habilitar con confirmación y la clave fija) y `app_test.dart` (una clave registrada en
  Pauta aparece en la carga sin recargar la página).
- **Con uvicorn de verdad,** en un contenedor: sin sesión, 401; registrar, 200 sin habilitar; una «E»,
  422 con su motivo; habilitar, 200 a nombre del docente; la lista de la carga la muestra habilitada;
  y el archivo guardado es el que lee el worker.

## Trazabilidad

- **Código:** `backend/autoria/registro_de_claves.py`, `backend/infraestructura/claves.py`
  (`RegistroDeClaves`, `ClavesEnDisco.guardar`) y `backend/api/main.py`; en el sitio,
  `lib/features/pauta/data/servicio_clave.dart`,
  `lib/features/pauta/views/widgets/tarjeta_clave.dart` y `lib/app/marco_app.dart`.
- **Contrato:** `docs/contrato/openapi.json`, versión 2.1.0.
