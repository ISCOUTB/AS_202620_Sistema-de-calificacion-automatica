# 08 · Propiedad de datos

Este documento fija el primer **concepto transversal** de la sección 8 del
[arc42](arc42-template-ES.md#8-cross-cutting-concepts) que deja de ser una intención: la
**propiedad de datos**. Existe porque el sistema es un monolito modular
([ADR-0001](../adr/0001-usar-monolito-modular.md) ·
[ADR-0002](../adr/0002-procesar-calificacion-de-forma-asincrona.md)) con siete módulos que se
prueban por frontera (`test_fronteras.py`), y una frontera de *imports* sin una frontera
equivalente de *datos* solo previene un tipo de acoplamiento y deja pasar el otro: dos módulos
que no se importan entre sí pueden seguir escribiendo la misma entidad sin que ninguna prueba
actual lo detecte.

**La regla.** Cada entidad de datos del dominio tiene **exactamente un módulo dueño**: el único
módulo autorizado a decidir el contenido de sus campos de negocio, es decir, a construir una
instancia con valores nuevos o a mutar los que ya tiene. Los demás módulos pueden importar el
tipo, pasarlo como parámetro, o —en el caso de un adaptador de persistencia— reconstituirlo
fielmente a partir de lo que el dueño ya escribió, pero no pueden decidir por su cuenta qué
significa un campo ni qué valor le corresponde. Esta es la regla contra la que se
contrastan las no conformidades de este documento.

---

## Tabla módulo → dato

Una fila por entidad existente en el código, con su dueño, la ruta del archivo donde está
**declarada** y la línea exacta. La tabla no incluye datos que todavía no tienen clase propia:
eso se trata aparte, en [«Entidades previstas»](#entidades-previstas-sin-construir).

| Entidad | Módulo dueño | Ruta | Línea |
|---|---|---|---|
| `ArchivoCargado` | `ingesta` | [`backend/infraestructura/modelo.py`](../../backend/infraestructura/modelo.py) | 37 |
| `HojaAceptada` | `ingesta` | [`backend/infraestructura/modelo.py`](../../backend/infraestructura/modelo.py) | 48 |
| `ArchivoRechazado` | `ingesta` | [`backend/infraestructura/modelo.py`](../../backend/infraestructura/modelo.py) | 69 |
| `ResultadoRecepcion` | `ingesta` | [`backend/infraestructura/modelo.py`](../../backend/infraestructura/modelo.py) | 80 |
| `EntradaDeBitacora` | `ingesta` | [`backend/infraestructura/modelo.py`](../../backend/infraestructura/modelo.py) | 96 |

**Por qué el dueño de las cinco es `ingesta` y no `infraestructura`, si las cinco clases están
declaradas en `infraestructura/modelo.py`.** La ruta y la línea son de dónde vive la
*declaración*, no de quién decide el *contenido*. `modelo.py` dice de sí mismo por qué está en
`infraestructura` y no en otro módulo: es el único que los siete `__init__.py` declaran poder
importar todos, así que ubicar ahí el modelo compartido no exige mover ninguna frontera. Pero
propiedad no es lo mismo que ubicación: quien decide qué significa cada campo y en qué momento
cambia de valor es `ingesta.recepcion.recibir_lote`, que es donde se construyen las cinco
instancias con datos reales —el motivo de un rechazo, el estado `encolada` o
`pendiente_de_encolar`, el `trabajo_id`— y no `infraestructura`, que no conoce esas reglas de
negocio. `api/main.py` construye un `ArchivoCargado` en la línea 85, pero solo como el adaptador
HTTP que traduce el `multipart/form-data` de la petición al tipo que `ingesta` ya definió; no
decide ningún campo de negocio, se limita a copiar nombre y bytes.

**La única aparente excepción, y por qué no rompe la regla.** `infraestructura/bitacora.py`
reconstruye un `EntradaDeBitacora` en su línea 117, dentro de `BitacoraEnDisco.pendientes()`.
No es una segunda autoría: es la lectura de vuelta de exactamente los mismos cuatro campos que
`ingesta` ya escribió en la línea 138 de `recepcion.py`, deserializados desde el JSON Lines que
la propia bitácora produjo. `BitacoraDeRecepcion` es un puerto (`Protocol`) que `ingesta`
declara y que `infraestructura` implementa; el adaptador puede rearmar el dato que le
confiaron, pero no le añade ni le cambia ningún campo. Si algún día `BitacoraEnDisco` empezara a
inferir o corregir un campo al releerlo —por ejemplo, a decidir un `estado` que `ingesta` no le
dio— ahí sí pasaría a tener dos dueños, y esta tabla es la que lo haría visible.

---

## Entidades previstas (sin construir)

Los aspectos A-02 a A-05 todavía no tienen código ([`docs/aspectos.md`](../aspectos.md)), así que
sus datos no pueden llevar ruta ni línea sin inventarlas. Se dejan aquí, con dueño previsto según
la responsabilidad que cada módulo ya declara en su `__init__.py`, para que la tabla de arriba se
complete por adición y no se reescriba cuando esos aspectos se especifiquen.

| Entidad prevista | Módulo dueño previsto | Aspecto | Estado |
|---|---|---|---|
| Marca detectada y su nivel de confianza | `omr` | A-02 | Pendiente (S4) |
| Nota / resultado de calificación | `calificacion` | A-03 | Pendiente (S4) |
| Banco de preguntas y clave de respuestas | `autoria` | A-04 | Pendiente (S6) |
| Distractor diagnóstico (RF-11, opcional) | `autoria` | A-04 | Pendiente (S6) |
| Usuario, rol y curso | `identidad` | A-05 | Pendiente (S6) |

Que el dueño previsto de la nota sea `calificacion` y no `omr` ni `dashboard` es deliberado:
`calificacion` es el único módulo cuyo `__init__.py` declara la responsabilidad de «cálculo de
notas»; `omr` entrega la detección y su confianza, `dashboard` solo agrega y presenta lo que
`calificacion` ya decidió. Si al construir A-03 una nota terminara mutándose desde `dashboard`
—por ejemplo, para redondear una cifra visible— esta tabla es la que declara que eso está fuera
de regla, sin esperar a que una prueba de fronteras lo detecte primero.

---

## Aspectos ↔ contextos

Esta sección conecta la propiedad de datos con la columna «Contexto C4 (Nivel 1)» que se agregó
a la [tabla de trazabilidad de `aspectos.md`](../aspectos.md#tabla-de-trazabilidad): para cada
aspecto, qué módulo es dueño de sus datos y con qué relación del diagrama de contexto se
corresponde ese trabajo.

| Aspecto | Módulo(s) dueño(s) de datos | Entidades que crea | Contexto C4 (Nivel 1) |
|---|---|---|---|
| [A-01](../aspectos.md#a-01) | `ingesta` | `ArchivoCargado`, `HojaAceptada`, `ArchivoRechazado`, `ResultadoRecepcion`, `EntradaDeBitacora` | [Rel. 1](../c4/doc-c4.md#relaciones): Profesor/TA → Sistema |
| [A-02](../aspectos.md#a-02) | `omr` (previsto) | Marca detectada y confianza (previsto) | Sin contexto propio — proceso interno |
| [A-03](../aspectos.md#a-03) | `calificacion` (previsto) | Nota / resultado (previsto) | [Rel. 2](../c4/doc-c4.md#relaciones): Sistema → Profesor/TA |
| [A-04](../aspectos.md#a-04) | `autoria` (previsto) | Banco, clave, distractor (previsto) | [Rel. 1 y 3](../c4/doc-c4.md#relaciones): Profesor/TA → Sistema · Sistema → Proveedor de LLM |
| [A-05](../aspectos.md#a-05) | `identidad` (previsto) | Usuario, rol, curso (previsto) | [Rel. 1 y 2](../c4/doc-c4.md#relaciones): transversal a ambas |

La fila de A-02 es la misma excepción en las dos tablas, y por la misma razón: un aspecto que no
cruza la frontera del sistema tampoco tiene, todavía, un actor externo a quien rendirle cuentas
sobre sus datos. Eso no lo exime de la regla de propiedad —seguirá teniendo un único dueño,
`omr`— pero sí explica por qué es el único que no aparece en ninguna relación del Nivel 1.
