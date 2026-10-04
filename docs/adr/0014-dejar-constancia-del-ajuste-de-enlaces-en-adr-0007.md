# 0014 · Dejar constancia del ajuste de enlaces en ADR-0007

- **Estado:** aceptado
- **Fecha:** 2026-10-04
- **Decide:** Josué Ortega De Arco, María Restrepo Licona, Sebastián Cañas Plata, Susana Rosales Castellar
- **Relación con otros ADR:** precisa [ADR-0007](0007-declarar-los-contextos-delimitados-y-la-regla-de-dueno-unico.md) sin reemplazarlo. Su decisión, sus alternativas y sus consecuencias siguen vigentes

**La decisión, en una frase:** ADR-0007 se editó después de aceptarse solo para mover cuatro referencias a un archivo que se retiró; aquí queda la constancia de qué cambió y por qué, y se fija qué se puede tocar en un ADR aceptado: sus decisiones nunca, y los ajustes menores que no son de arquitectura, como un enlace o una errata, solo si quedan registrados.

---

## Contexto

El 26 de septiembre la propiedad de datos, que vivía en `docs/arc42/08-propiedad-de-datos.md`, pasó a ser la sección 8.3 del arc42 (`62fac14`), y el archivo se retiró (`e7571d9`). Fue porque el docente confirmó que su agente revisa la sección 8 dentro del arc42.

ADR-0007 apuntaba a ese archivo en cuatro lugares. Para que no quedaran apuntando a un archivo que dejaba de existir, el commit `1c8bcfb` (26-sep, «actualizar en el 0007 dónde está la propiedad de datos») cambió esas cuatro líneas. La decisión, sus alternativas y sus consecuencias no cambiaron en nada.

CONTRATO §4 dice: «Un ADR aceptado no se edita ni se borra». La revisión definitiva de la S8 y la preliminar de la S9 registraron la edición en la fila «ADR aceptados no reescritos», y la retroalimentación de la S8 propuso la salida: «si solo cambian referencias internas, háganlo con un nuevo ADR que lo precise, o dejen constancia del ajuste».

## Alternativas consideradas

**A. Revertir la edición de ADR-0007.** Devolvería tres enlaces a un archivo que ya no existe, y sería una segunda edición del mismo ADR aceptado. Descartada.

**B. Un ADR que reemplace a ADR-0007, igual pero con los enlaces nuevos.** Duplicaría una decisión que no cambió, y obligaría a cambiar la línea de estado de ADR-0007 a «reemplazado». Descartada.

**C. Un ADR que precise a ADR-0007 y deje constancia del ajuste (elegida).** No toca ADR-0007, deja escrito qué cambió, cuándo y por qué, y fija la regla para lo que venga.

## Decisión

**1. Constancia del ajuste.** En `1c8bcfb` cambiaron cuatro líneas de ADR-0007, y ninguna otra:

| Qué decía | Qué dice |
|---|---|
| Un enlace a `08-propiedad-de-datos.md` en «Documentación», en el encabezado | Un enlace a la [sección 8.3 del arc42](../arc42/arc42-template-ES.md#83-propiedad-de-datos) |
| Un enlace al mismo archivo en el punto 6 de la decisión | Un enlace a la sección 8.3 |
| La mención de `08-propiedad-de-datos.md` en la tabla de riesgos | «la sección 8.3 del arc42» |
| Un enlace a `docs/arc42/08-propiedad-de-datos.md` en «Documentación que la implementa» | Un enlace a §8.3 |

**2. ADR-0007 sigue vigente:** su decisión, sus alternativas y sus consecuencias no cambiaron.

**3. Qué se puede tocar en un ADR aceptado, desde ahora:**

- **Las decisiones escritas en un ADR no se modifican ni se borran**, y tampoco su contexto, sus
  alternativas ni sus consecuencias. Si una decisión cambia, se escribe un ADR nuevo que la
  reemplace o la precise, como pide CONTRATO §4.
- **Los ajustes menores, que no son de arquitectura, sí se pueden hacer**: un enlace que dejó de
  funcionar, una errata, el formato. Cada uno queda registrado: el título del commit dice que es un
  ajuste menor del ADR y su descripción, qué cambió y por qué no toca la decisión, y la sección 9 del
  arc42 lo anota. Es la «constancia del ajuste» que pidió la retroalimentación de la S8.
- **Se descartó prohibir toda edición**: dejaría enlaces rotos en ADR vigentes, que es peor para
  quien los lee y no protege ninguna decisión.

## Consecuencias

### Positivas

- Quien lea ADR-0007 y encuentre `1c8bcfb` en su historia encuentra aquí qué cambió y por qué.
- Queda una regla explícita que separa lo que nunca se toca (la decisión) de lo que se puede ajustar
  dejando constancia (un enlace, una errata).
- Un enlace roto en un ADR vigente se puede arreglar sin escribir un ADR nuevo.

### Negativas

- La edición de `1c8bcfb` sigue en el historial de git: esta constancia la explica, no la borra. La
  fila transversal puede seguir registrándola.
- La regla del punto 3 es más flexible que la letra de CONTRATO §4 («Un ADR aceptado no se edita ni
  se borra»). Una revisión puede registrar un ajuste menor como edición; por eso cada ajuste deja su
  constancia, para que se pueda comprobar que no tocó ninguna decisión.

## Trazabilidad

- **ADR que precisa:** [ADR-0007](0007-declarar-los-contextos-delimitados-y-la-regla-de-dueno-unico.md).
- **Commits:** `62fac14` (la propiedad de datos entra a la sección 8.3), `1c8bcfb` (el ajuste de ADR-0007) y `e7571d9` (se retira el archivo).
- **Documentación:** arc42 [§8.3](../arc42/arc42-template-ES.md#83-propiedad-de-datos) y §9, que registra este ADR.
