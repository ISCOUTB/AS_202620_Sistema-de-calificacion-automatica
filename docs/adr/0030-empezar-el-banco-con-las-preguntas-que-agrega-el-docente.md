# 0030 · Empezar el banco con las preguntas que agrega el docente

- **Estado:** aceptado
- **Fecha:** 2026-11-23
- **Decide:** Sebastián Cañas Plata, Susana Rosales Castellar
- **Riesgos:** ninguno nuevo; se guarda el correo del docente con el texto de sus preguntas, sin datos de estudiantes
- **Relación con otros ADR:** empieza RF-06, que [ADR-0026](0026-registrar-y-habilitar-la-clave-desde-la-aplicacion.md) dejó pendiente al registrar solo la clave. Reconoce la pregunta como [ADR-0029](0029-guardar-los-distractores-que-el-docente-aprueba.md), guarda a nombre del docente de [ADR-0025](0025-identificar-al-docente-con-una-sesion-firmada-y-una-lista-de-cuentas.md) y usa el medio de [ADR-0027](0027-guardar-los-registros-en-postgres-detras-de-los-mismos-puertos.md).

**La decisión, en una frase:** las preguntas que el docente agrega en Pauta con «+» se guardan a
su nombre en el servidor y van arriba en la lista; las que tienen distractores guardados pasan al
final, con ellos a la vista.

---

## Contexto

Al probar ADR-0029 en local aparecieron dos faltas. La lista de Pauta tenía solo las diez
preguntas de ejemplo, sin forma de agregar otra; una pregunta escrita en el generador se perdía al
salir. Y al guardar distractores la lista no cambiaba, así que no se veía dónde habían quedado.

RF-06 pide el banco de preguntas, y hasta aquí no tenía código (A-04).

## Alternativas consideradas

| Alternativa | A favor | En contra | Resultado |
|---|---|---|---|
| **Solo en la pantalla:** la agregada vive mientras la página está abierta, y en el servidor solo si se le guardan distractores | Sin tabla nueva | Una pregunta sin distractores se pierde al recargar | Descartada |
| **«+» vacía el formulario del generador** en vez de abrir una fila en la lista | No repite los campos del generador | No deja cargar varias preguntas antes de generar | Descartada |
| **El banco completo de RF-06:** tema, examen y pesos | Es lo que pide el requisito | Mucho más que lo pedido, y la clave ya se registra aparte (ADR-0026) | Descartada por ahora |
| **Un registro de las preguntas de cada docente** | Persiste, es de cada docente y se reconoce igual que lo guardado | Sin tema y sin examen | **Elegida** |

## Decisión

1. **El registro** (`infraestructura/preguntas_del_docente.py`): `PreguntasEnDisco` sin base de
   datos y `PreguntasEnPostgres` (tabla `preguntas_del_docente`, llave primaria
   `(docente, llave)`) con ella. Agregar una que el docente ya tiene no cambia nada.
2. **La pregunta** es el enunciado y la respuesta correcta con los espacios normalizados, y se
   reconoce con `llave_de_la_pregunta`, la de ADR-0029 (`autoria/preguntas_del_docente.py`). Sin
   texto, 422; repetida, 409.
3. **Tres rutas, con la sesión:** `GET /preguntas`, de la más reciente a la más antigua;
   `POST /preguntas`; y `DELETE /preguntas/{llave}`. La de otro docente responde 404. Entran en el
   contrato 3.1.0, con las de ADR-0029.
4. **En Pauta:** «+» abre arriba en la lista una fila con el enunciado, la respuesta correcta y
   «Agregar», que queda abierta para seguir con otra. Las agregadas van arriba, con «Eliminar», y
   después las de ejemplo por su número. Las que tienen distractores guardados pasan al final, en
   «Con distractores guardados», con «Quitar» (ADR-0029). Al quitarlos, la pregunta vuelve a su
   lugar: la de ejemplo a su número y la agregada arriba.
5. **Una pregunta escrita en el generador** entra a la lista al guardarle distractores, para que
   al quitárselos no desaparezca.

## Consecuencias

- Las preguntas del docente sobreviven a recargar la página y a cambiar de computador.
- El banco empieza sin tema y sin examen: la lista no sabe a qué examen va cada pregunta, y la
  clave todavía no las usa.
- Eliminar una pregunta no toca sus distractores guardados: para borrar las dos cosas, primero se
  quitan los distractores.
- No hay tope de preguntas por docente; solo escriben los de la lista de cuentas (ADR-0025).

## Cómo se comprobó

- **Servidor:** `test_preguntas_del_docente.py` (29, con los adaptadores contra memoria, disco y
  Postgres 16), la prueba de contrato con las diecisiete rutas y la de sesión, que recorre las
  nuevas. La suite completa: 732 pasan y 2 se saltan; `mypy` sin errores.
- **Sitio:** en `pauta_test.dart`, «+» abre la fila y la pregunta nueva queda arriba y se puede
  elegir; no se agrega una vacía ni una que ya está; «Eliminar» la quita de la lista; una pregunta
  escrita en el generador entra a la lista al guardarle distractores y vuelve arriba al quitárselos;
  y a 390 px nada desborda. También `servicio_preguntas_test.dart` y
  `servicios_con_sesion_test.dart`. La suite del sitio: 263 pasan.

## Reversión

- Revertir el cambio: la lista vuelve a las diez de ejemplo y la tabla queda sin uso. Las preguntas
  guardadas no entran a ningún examen ni a ninguna nota.

## Trazabilidad

- **Código:** `backend/infraestructura/preguntas_del_docente.py`,
  `backend/infraestructura/base_de_datos.py` (`PreguntasEnPostgres`),
  `backend/autoria/preguntas_del_docente.py` y `backend/api/main.py`
  (`obtener_registro_de_preguntas` y las tres rutas); en el sitio, `servicio_preguntas.dart`,
  `pantalla_pauta.dart`, `lista_preguntas.dart` y `fila_nueva_pregunta.dart`.
- **Pruebas:** las de arriba.
- **Configuración:** `RUTA_PREGUNTAS_DEL_DOCENTE` en `backend/api/settings.py`, solo sin
  `DATABASE_URL`.
