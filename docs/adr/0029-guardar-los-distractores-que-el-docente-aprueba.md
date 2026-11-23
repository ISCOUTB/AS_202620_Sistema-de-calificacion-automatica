# 0029 · Guardar los distractores que el docente aprueba

- **Estado:** aceptado
- **Fecha:** 2026-11-23
- **Decide:** Sebastián Cañas Plata, Susana Rosales Castellar
- **Riesgos:** ninguno nuevo; se guarda el correo del docente con el texto que él escribió, sin datos de estudiantes
- **Relación con otros ADR:** completa [ADR-0013](0013-consumir-groq-detras-de-un-puerto-y-degradar-sin-bloquear-la-autoria.md) (el modelo propone; ahora la decisión del docente también queda). Reconoce la pregunta como la caché de [ADR-0019](0019-guardar-en-cache-las-propuestas-de-distractores.md), guarda a nombre del docente de [ADR-0025](0025-identificar-al-docente-con-una-sesion-firmada-y-una-lista-de-cuentas.md) y usa el medio de [ADR-0027](0027-guardar-los-registros-en-postgres-detras-de-los-mismos-puertos.md). [ADR-0030](0030-empezar-el-banco-con-las-preguntas-que-agrega-el-docente.md) pone las preguntas con distractores guardados al final de la lista de Pauta.

**La decisión, en una frase:** los distractores que el docente elige se guardan a su nombre, por
pregunta, y la pregunta pasa al final de la lista de Pauta con ellos a la vista; una propuesta
descartada se puede regenerar sola, sin perder las demás.

---

## Contexto

El generador (RF-11) propone y el docente decide (RF-07), pero la decisión vivía solo en la
pantalla. La nota lo decía: «Las que elija no quedan guardadas aquí; cópielas a su examen». Al
salir de Pauta, o al pedir otras propuestas, lo elegido se perdía.

Y «Pedir otras propuestas» reemplaza todas: para cambiar una sola descartada había que perder las
que ya estaban elegidas.

No hay banco de preguntas (RF-06): la pregunta existe solo como el texto del formulario.

## Alternativas consideradas

| Alternativa | A favor | En contra | Resultado |
|---|---|---|---|
| **Guardar en el navegador** | Sin ruta nueva | Se pierde al cambiar de computador o al borrar los datos del navegador, y no queda a nombre del docente | Descartada |
| **Dentro de la caché de propuestas** (ADR-0019) | Ya reconoce la pregunta | Vive en la memoria del proceso, vence a las 24 horas y es de todos los docentes | Descartada |
| **Esperar al banco de preguntas** (RF-06) | Sería su lugar | RF-06 no está construido | Descartada por ahora |
| **Un registro aparte, por docente y pregunta** | Persiste, es de cada docente y no depende del banco | La pregunta se reconoce por su texto | **Elegida** |
| **Verlo solo al volver a pedir distractores para la pregunta** | Sin una ruta para listar | Al guardar no se ve dónde queda, y para verlo hay que consultar al modelo | Descartada al probarlo en local |

## Decisión

1. **El registro** (`infraestructura/distractores_guardados.py`): `DistractoresEnDisco` sin base de
   datos y `DistractoresEnPostgres` (tabla `distractores_guardados`, llave primaria
   `(docente, llave)`) con ella. Guardar otra vez la misma pregunta reemplaza lo anterior, y lo del
   docente se lista de lo más antiguo a lo más reciente.
2. **La pregunta** se reconoce por el enunciado y la respuesta correcta con los espacios
   normalizados, como en la caché (`llave_de_la_pregunta`).
3. **La regla al guardar** (`autoria/distractores_guardados.py`): de 1 a 3, porque la hoja tiene
   cuatro opciones; ninguno igual a la respuesta correcta ni a otro, con la misma `normalizar` que
   filtra las propuestas; y cada uno con el error que representa. Si no cumple, 422 con el motivo,
   y lo guardado no cambia.
4. **Tres rutas, con la sesión:** `PUT /distractores/guardados` guarda, `GET` lista lo del
   docente con la llave de cada pregunta, y `DELETE /distractores/guardados/{llave}` lo quita; lo
   de otro docente responde 404. El contrato sube a 3.1.0.
5. **En Pauta:** «Guardar distractores» guarda las elegidas y la pregunta pasa al final de la
   lista, en «Con distractores guardados», con los distractores a la vista y «Quitar» (ADR-0030).
   Elegirla ahí los muestra sin consultar al modelo; al pedir otras, lo guardado llega primero y ya
   elegido, y una propuesta que lo repite no aparece dos veces. Una tarjeta
   descartada ofrece «Regenerar», a la izquierda de «Deshacer»: pide una sola propuesta nueva
   (`cantidad: 1`, `otras: true`) y reemplaza solo esa. La caché guarda aparte cada cantidad, así
   que no pisa las propuestas de la pregunta.

## Consecuencias

- Lo elegido sobrevive a salir de Pauta, a otro computador y a «Pedir otras propuestas».
- Cada «Regenerar» es una solicitud al proveedor y gasta cupo del presupuesto (ADR-0015).
- Lo guardado se ve en la lista de preguntas, sin consultar al modelo ni gastar cupo, aunque el
  proveedor no responda.
- Un cambio mínimo en el texto de la pregunta la vuelve otra pregunta. ADR-0030 empieza el banco
  (RF-06), pero la pregunta se sigue reconociendo por su texto.

## Cómo se comprobó

- **Servidor:** `test_distractores_guardados.py` (39, con los adaptadores contra memoria, disco y
  Postgres 16), la prueba de contrato con las diecisiete rutas y la de sesión, que recorre las
  nuevas. La suite completa: 732 pasan y 2 se saltan; `mypy` sin errores.
- **Sitio:** en `pauta_test.dart`, «Regenerar» aparece solo en la descartada y a la izquierda de
  «Deshacer», pide una sola propuesta y cambia solo esa tarjeta, y avisa si la nueva repite otra o
  si falla; «Guardar distractores» manda las elegidas, las marca como guardadas y pasa la pregunta
  al final de la lista; elegirla ahí muestra lo guardado sin consultar al modelo, y elegir otra
  pregunta lo quita del generador; «Quitar» la devuelve a su número. También
  `servicio_distractores_test.dart` y `servicios_con_sesion_test.dart`. La suite del sitio: 263
  pasan.

## Reversión

- Revertir el cambio: Pauta deja de guardar y la tabla queda sin uso. Lo guardado no entra a ningún
  examen ni a ninguna nota.

## Trazabilidad

- **Código:** `backend/infraestructura/distractores_guardados.py`,
  `backend/infraestructura/base_de_datos.py` (`DistractoresEnPostgres`),
  `backend/autoria/distractores_guardados.py` y `backend/api/main.py`
  (`obtener_registro_de_distractores` y las tres rutas); en el sitio, `servicio_distractores.dart`,
  `pantalla_pauta.dart`, `lista_preguntas.dart`, `vista_propuestas.dart` y
  `tarjetas_propuesta.dart`.
- **Pruebas:** las de arriba.
- **Configuración:** `RUTA_DISTRACTORES_GUARDADOS` en `backend/api/settings.py`, solo sin
  `DATABASE_URL`.
