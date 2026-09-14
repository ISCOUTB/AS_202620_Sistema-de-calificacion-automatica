# 0007 — Declarar los contextos delimitados y la regla de dueño único de los datos

- **Estado:** aceptado
- **Fecha:** 2026-09-13
- **Decide:** Josué Ortega De Arco, María Restrepo Licona, Sebastián Cañas Plata, Susana Rosales Castellar
- **Escenario de calidad relacionado:** ninguno declarado. Esta decisión no persigue una medida; acota el riesgo R-08 (que el proyecto se degrade a un paquete plano)
- **Precisa, sin reemplazar:** [ADR-0002](0002-procesar-calificacion-de-forma-asincrona.md)

---

## Contexto

ADR-0002 dividió el sistema en siete módulos y fijó qué puede importar cada uno. Esa frontera está escrita en la línea `Importa:` del docstring de cada `__init__.py` y la verifica [`test_fronteras.py`](../../backend/tests/test_fronteras.py) en cada ejecución del pipeline, de modo que el riesgo R-08 dejó de depender de la disciplina del equipo.

Lo que ADR-0002 no dijo es **quién es dueño de cada dato**, y esa omisión se volvió visible al construir A-01. Una frontera de *imports* sin una frontera equivalente de *datos* previene un tipo de acoplamiento y deja pasar el otro: dos módulos que no se importan entre sí pueden escribir la misma entidad sin que ninguna prueba actual lo detecte. Las cinco entidades de A-01 están declaradas en `infraestructura/modelo.py`, que es el único módulo que los siete pueden importar, así que hoy cualquier entidad nueva nace al alcance de todos.

Al intentar escribir la tabla módulo a dato aparecieron dos preguntas que no tenían respuesta registrada, y las dos cambian el resultado:

1. **Qué es un contexto en este sistema, y qué relación tiene con los demás.** Los siete módulos eran una descomposición técnica, no una lista de contextos con sus relaciones tipificadas.
2. **Qué significa ser dueño de una entidad.** Con la definición intuitiva («el que la guarda»), `infraestructura` resulta dueña de todo y la tabla no distingue nada, porque ahí viven el modelo, el almacén y la bitácora.

Este ADR responde las dos, y existe porque una regla que solo vive en un documento se degrada igual que la frontera de imports que R-08 describe, y por la misma razón.

### Dónde se localiza el impacto

- **Documentación:** arc42 §8.1 (mapa de contextos), §8.2 (lenguaje ubicuo) y [`08-propiedad-de-datos.md`](../arc42/08-propiedad-de-datos.md), que aplica la regla entidad por entidad.
- **Código:** `backend/infraestructura/modelo.py` y `backend/infraestructura/cola.py`, donde están declaradas las seis entidades existentes; los siete `__init__.py`, que declaran responsabilidad y fronteras; `backend/tests/test_fronteras.py`, que hoy verifica imports y no propiedad.
- **Aspectos:** los cinco. Cada uno realiza un contexto, y la correspondencia en las dos direcciones está en [`docs/aspectos.md`](../aspectos.md#tabla-de-trazabilidad).

---

## Alternativas consideradas

### A. No escribir el ADR y dejar la regla en la sección 8

La definición de dueño y el mapa viven en el arc42, sin decisión registrada.

**A favor:** cuesta cero y el contenido igual queda escrito donde el lector lo busca.

**En contra:** una regla sin ADR no tiene autor, ni fecha, ni alternativas descartadas, así que el día que alguien la encuentre incómoda la cambia sin que nadie sepa qué se estaba protegiendo. Es exactamente la degradación que R-08 describe, aplicada a la documentación en vez de al código.

**Por qué no se eligió:** la regla ya cambió una vez durante esta misma entrega (ver alternativa B), y ese cambio es la clase de cosa que un ADR existe para conservar.

### B. Definir al dueño como el módulo que persiste el dato

El dueño de una entidad es quien la escribe en disco, en la cola o en la base de datos.

**A favor:** es verificable mecánicamente. Basta seguir quién llama al almacén o a la bitácora.

**En contra:** sobre este sistema no distingue nada. `infraestructura` implementa `AlmacenEnDisco`, `BitacoraEnDisco` y la cola, así que resultaría dueña de las seis entidades y la tabla tendría una sola fila útil. Peor: premiaría exactamente el acoplamiento que se quiere evitar, porque convertiría al módulo de soporte en el centro del modelo de negocio.

**Por qué no se eligió:** se probó primero y el resultado fue una tabla que no discriminaba. Se descartó por lo que producía, no por lo que prometía.

### C. Mover cada entidad al módulo que la posee

Un `modelo.py` por módulo, de modo que propiedad y ubicación coincidan y la tabla sobre.

**A favor:** la regla se haría evidente sin documentarla, y no haría falta ninguna prueba nueva: quien no puede importar el tipo no puede construirlo.

**En contra:** `modelo.py` está donde está por una razón registrada, que es ser el único módulo que los siete `__init__.py` declaran poder importar; repartir las entidades obliga a abrir fronteras nuevas entre módulos que hoy no se importan, que es más acoplamiento y no menos. Además supone mover código de A-01, que está construido y medido, sin ningún aspecto que lo justifique.

**Por qué no se eligió:** resuelve el problema de documentación creando uno de arquitectura. Queda anotada por si la persistencia definitiva (R-06) obliga de todos modos a reorganizar el modelo.

### D. Declarar los contextos y definir la propiedad por decisión de contenido (ELEGIDA)

Una lista cerrada de siete contextos con sus relaciones tipificadas, y una regla de dueño único donde el dueño es quien **decide el contenido de los campos de negocio**, no quien los guarda.

**A favor:**

- Distingue de verdad: `ingesta` resulta dueña de las cinco entidades de A-01 aunque estén declaradas en `infraestructura`, e `infraestructura` resulta dueña de `Trabajo`, que es lo único cuyo contenido decide por su cuenta.
- Separa propiedad de ubicación, que es lo que permite dejar `modelo.py` donde está sin que la tabla mienta.
- Se puede auditar contra el código hoy, sin construir nada: cada fila lleva ruta y línea.
- Deja abierta la puerta a verificarla automáticamente más adelante, con el mismo mecanismo que ya funciona para los imports.

**En contra:**

- **La verificación es manual.** Hoy nadie impide que una entidad nueva nazca sin dueño; hace falta que alguien repita el recorrido.
- Exige juicio en los casos de frontera, y ya apareció uno: `Trabajo` lleva un `payload` que arma `ingesta`. Hubo que decidir que un sobre de transporte no se convierte en segundo autor del dato que transporta.

**Por qué se eligió:** es la única que produce una tabla con información, y su punto débil (que nadie la verifica) está declarado como violación abierta con su corrección escrita, en vez de quedar tapado.

---

## Decisión

**1. El sistema se organiza en siete contextos, y la lista es cerrada.** Seis de dominio (Identidad, Ingesta, OMR, Calificación, Autoría, Dashboard) y uno de soporte (Infraestructura), que no modela un subdominio de negocio sino que provee persistencia y servicios técnicos a los otros seis. Renombrar o agregar un contexto exige un ADR nuevo, porque los documentos se apoyan en esos nombres.

**2. Las relaciones entre contextos se declaran tipificadas**, con las tres formas del vocabulario de la semana: núcleo compartido (Infraestructura con los seis, por `modelo.py`), cliente/proveedor (Identidad hacia los cinco, OMR hacia Calificación, Calificación hacia Dashboard) y capa anticorrupción (Autoría hacia el proveedor de LLM, y los puertos de Ingesta hacia Infraestructura como caso interno). Las seis relaciones están en la tabla de arc42 §8.1, cada una con su evidencia en el código.

**3. Cada entidad tiene exactamente un módulo dueño, y el dueño es quien decide el contenido de sus campos de negocio:** el único autorizado a construir una instancia con valores nuevos o a modificar los que ya tiene. Los demás pueden importar el tipo, recibirlo como parámetro o, si son adaptadores de persistencia, reconstituirlo fielmente a partir de lo que el dueño ya escribió.

**4. Propiedad y ubicación son cosas distintas.** Dónde está declarada una clase y quién decide su contenido pueden ser módulos distintos, y en este sistema lo son: las cinco entidades de A-01 viven en `infraestructura/modelo.py` y su dueño es `ingesta`.

**5. Un adaptador que relee un dato no se convierte en segundo dueño**, siempre que devuelva los mismos campos que el dueño escribió sin inferir ni corregir ninguno. Lo mismo vale para un sobre de transporte que lleva un contenido que no interpreta.

**6. La regla se audita a mano y esa es su debilidad conocida.** Su verificación automática, una línea `Posee:` en cada docstring y una prueba que falle si una entidad no aparece declarada por exactamente un módulo, queda registrada como la violación V-5 de [`08-propiedad-de-datos.md`](../arc42/08-propiedad-de-datos.md), con su corrección escrita. No se implementa en esta decisión.

**7. Esta decisión no cierra R-06 ni toca ADR-0002.** No elige medio de persistencia, no mueve ninguna frontera de importación y no cambia la responsabilidad de ningún módulo.

---

## Consecuencias

### Positivas

- La tabla módulo a dato se puede escribir y se puede contrastar contra el código, con ruta y línea por entidad.
- El recorrido de auditoría encontró cinco violaciones que antes no tenían nombre, y cada una tiene ahora una corrección concreta.
- Los aspectos se pueden relacionar con los contextos en las dos direcciones, lo que hizo visible que Dashboard solo se realiza en la mitad de publicación de A-03 y que Infraestructura no tiene aspecto propio a propósito.
- Cuando A-02 declare la marca detectada y A-03 la nota, la pregunta «quién es su dueño» ya tiene forma de respuesta.

### Negativas y costos asumidos

- **Nada verifica la regla.** Entre esta decisión y la corrección de V-5, la tabla se mantiene por disciplina, que es justo lo que R-08 dice que no funciona.
- **Los casos de frontera exigen juicio**, y el juicio no se puede automatizar. `Trabajo` ya obligó a argumentar por escrito por qué su `payload` no le da dos dueños.
- **La palabra «contexto» queda sobrecargada.** En el Nivel 1 del C4 significa la frontera con los actores externos; en el mapa de §8.1 significa la división interna del dominio. Se aclara donde más se nota (la fila de A-02 en `aspectos.md`), pero la ambigüedad persiste en la documentación anterior.
- **La lista cerrada de siete es una apuesta.** Seis contextos no tienen código todavía; puede que al construirlos alguno se parta en dos, y eso exigirá otro ADR.

### Riesgos y qué los dispararía

| Riesgo | Disparador | Mitigación |
|---|---|---|
| Una entidad nueva nace sin dueño declarado. | Construir A-02 o A-03 sin volver a la tabla. | La corrección de V-5: `Posee:` en el docstring más la prueba que lo verifica. |
| Se toma la definición de dueño por la de quien persiste. | Que alguien lea la tabla sin leer la regla. | El punto 4 lo declara y `08-propiedad-de-datos.md` lo argumenta en el caso concreto de las cinco entidades. |
| Un adaptador empieza a inferir campos al releer y nadie lo nota. | Que `BitacoraEnDisco` decida un `estado` que `ingesta` no le dio, al construir el reintento de A-02. | El punto 5 fija el límite, y la tabla es lo que lo haría visible. |

### Qué dato haría revisar esta decisión

- **Que un contexto se parta en dos** al construirlo, o que dos resulten ser el mismo. Entonces la lista cerrada del punto 1 deja de ser cierta y se escribe un ADR nuevo.
- **Que el ADR de persistencia (R-06) obligue a reorganizar el modelo.** Si cada módulo termina con su propio esquema, la alternativa C vuelve a la mesa y esta tabla sobra.
- **Que la regla de dueño único bloquee un caso legítimo.** Si al construir A-03 la nota necesita de verdad dos autores, la regla está mal planteada y hay que decirlo, no forzar el código para que quepa.

**Costo de reversión: bajo.** Esta decisión no agrega código. Revertirla es escribir otro ADR y reescribir dos secciones de documentación.

---

## Trazabilidad

- **Riesgo que acota:** R-08 (arc42 §11), que el proyecto se degrade a un paquete plano. Lo extiende del acoplamiento por imports al acoplamiento por datos.
- **Restricción que no cierra:** R-06. Esta decisión no elige medio de persistencia.
- **Requisitos afectados:** ninguno cambia de enunciado.
- **Aspectos afectados:** los cinco, en su relación con los contextos. Ver [`docs/aspectos.md`](../aspectos.md#tabla-de-trazabilidad).
- **Elementos C4 afectados:** ninguno. El mapa de contextos de §8.1 no es un diagrama C4 y no sustituye a ninguno de los tres niveles.
- **ADR relacionados, no modificados:** [0002](0002-procesar-calificacion-de-forma-asincrona.md), que estableció los siete módulos y sus fronteras de importación. Esta decisión responde una pregunta que 0002 no se planteó, quién posee cada dato, y por eso conviven en lugar de reemplazarse.
- **Documentación que la implementa:** arc42 §8.1 y §8.2, y [`docs/arc42/08-propiedad-de-datos.md`](../arc42/08-propiedad-de-datos.md) con la tabla módulo a dato, el recorrido de la auditoría, las cinco violaciones y su plan de corrección.
- **Pruebas que la cubren:** ninguna todavía, y está declarado. [`test_fronteras.py`](../../backend/tests/test_fronteras.py) verifica las fronteras de importación de ADR-0002, no la propiedad de los datos. Cerrarlo es la corrección de la violación V-5.
