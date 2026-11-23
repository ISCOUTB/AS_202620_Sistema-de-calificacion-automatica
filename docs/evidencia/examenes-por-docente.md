# Exámenes por docente y el panel (ADR-0028)

Esta es la evidencia de [ADR-0028](../adr/0028-dar-a-cada-examen-un-dueno-y-un-identificador-distinto-de-su-nombre.md):
cada examen tiene un dueño y un identificador que acuña el sistema, y el panel muestra las cifras
del examen elegido. Lo que había que mostrar es que **un docente no ve ni cambia lo de otro**, que
los exámenes que ya existían pasan a su dueño sin perder nada, y que las cifras del panel son las de
las hojas leídas.

---

## Resultado

| Qué | Cómo | Resultado |
|---|---|---|
| Cada ruta de un examen, con el dueño y con otro docente | `tests/test_aislamiento_entre_docentes.py` | **21 de 21**; sin la comprobación del dueño en `examen_del_docente`, fallan 10 |
| Las reglas del examen: identificador, nombre repetido, dueño, adopción y concurrencia | `tests/test_examenes_del_docente.py`, contra memoria, disco y Postgres 16 | **36 de 36** |
| Las cifras del panel con hojas leídas por el OMR | `tests/test_panel.py`, con hojas sintéticas: notas de 5,0 y 2,5, una marca tenue, una doble y una en blanco, una hoja ilegible y una sin clave | **7 de 7** |
| La suite completa del servidor | `pytest` con Postgres y Redis, y `mypy` | **658 pasan**, 2 se saltan (las fotos de R-05); `mypy` sin errores en 116 archivos |
| La suite del sitio | `flutter test` y `flutter analyze` | **226 pasan**; el análisis, sin avisos |
| De punta a punta, en el compose del servidor | El código anterior con dos docentes; después este cambio sobre la misma base | **39 de 39** comprobaciones |

---

## 1. Dónde se probó

En un computador con Docker, con `deploy/compose.lab.yaml` y `deploy/compose.local-override.yaml`,
como en la [evidencia de la base de datos](base-de-datos.md): los cinco contenedores con los
límites del servidor. Dos cuentas de prueba en `DOCENTES`, Ana y Beto, y
`DOCENTE_DE_LOS_EXAMENES_ANTERIORES` vacía. Todas las hojas son sintéticas
(`herramientas.medir_procesamiento`).

## 2. El recorrido

1. **Con el código anterior** (`master` en `9c4e278`): Ana registró y habilitó la clave de
   `PARCIAL-1` y subió 6 hojas; Beto, la de `QUIZ-B`, con 4. Beto veía `PARCIAL-1` en su lista y
   leía sus resultados: el error que motivó el ADR.
2. **Con este cambio, sobre la misma base y los mismos volúmenes.** Con el primer pedido, la API
   dejó en su registro el evento `examenes_adoptados` con 2 exámenes:
   - Ana ve solo `PARCIAL-1`, y Beto solo `QUIZ-B`: cada examen fue a quien habilitó su clave.
   - Los resultados de `PARCIAL-1` son idénticos a los de antes.
   - Beto recibe 404 en los resultados, la revisión, el panel y la clave de `PARCIAL-1`, con el
     mismo cuerpo que para un examen que no existe.
3. **Exámenes nuevos.** Ana y Beto crearon «Parcial 1» y recibieron `000001` y `000002`, con 201.
   Ana volvió a pedir «  parcial   1 » y recibió 200 con `000001`. Un nombre vacío o de 81
   caracteres, 422; la clave de un examen que no se creó, 404.
4. **Lo de otro docente.** Beto intentó registrar la clave de `000001`, habilitarla y subirle una
   hoja: 404 las tres veces.
5. **El panel.** Ana registró la clave de `000001` y subió 5 hojas. En sus dos exámenes, las notas
   del panel son las mismas de `GET /examenes/{examen_id}/resultados`, el promedio y los aprobados
   cuadran, y la respuesta no lleva identificadores de hoja ni códigos de estudiante. Beto pidió el
   panel de `000001`: 404.

La tabla `examenes` quedó así:

| `examen_id` | `nombre` | `docente` |
|---|---|---|
| `000001` | Parcial 1 | ana@utb.edu.co |
| `000002` | Parcial 1 | beto@utb.edu.co |
| `PARCIAL-1` | PARCIAL-1 | ana@utb.edu.co |
| `QUIZ-B` | QUIZ-B | beto@utb.edu.co |

## 3. Lo que corrigió la revisión antes de subirlo

El sitio se escribió sin poder correr Flutter. Al correrlo:

- **Dos pruebas nuevas del sitio fallaban.** Una comparaba registros de Dart que llevan una lista
  adentro, y esa igualdad compara la lista por identidad. La otra encontró un defecto real: las
  leyendas del panel se desbordaban a 390 px. Las tres (marcas, histograma y aciertos por pregunta)
  ahora parten el texto.
- **`mypy` daba 12 errores** de tipos, que no cambiaban lo que hace el código.

## 4. Lo que no cubre

- **Los cursos (EC-06).** Un docente ve solo lo suyo, pero no hay roles ni cursos que agrupen a
  varios docentes.
- **Un examen anterior sin rastro de quién habilitó su clave** va a
  `DOCENTE_DE_LOS_EXAMENES_ANTERIORES`, o al primer docente de la lista. Si es el equivocado, se
  corrige cambiando su fila en la tabla `examenes`.
- **El panel no tiene asignatura, grupo ni número de estudiantes:** el sistema no guarda esos
  datos.
