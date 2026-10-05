# Evidencia de que la prueba del defecto falla

Este documento muestra que las pruebas de la porción de la S9 (RF-11, aspecto
[A-06](../aspectos.md#a-06)) detectan el defecto que cubren: que una propuesta igual a la
respuesta correcta llegue al profesor como distractor. Es la medida M1 de
[EC-08](../arc42/arc42-template-ES.md#ec-08). El experimento se puede revisar en el PR y en los
runs de la sección *Referencias*.

A diferencia de la S7, el defecto no entró nunca a `master`: vivió en una rama, el CI corrió sobre
el PR, y el PR se cerró sin fusionar después de una revisión cruzada.

## Qué se cambió

| | |
|---|---|
| Archivo | [`backend/autoria/distractores.py`](../../backend/autoria/distractores.py) |
| Función | `filtrar_propuestas` |
| Líneas | 152 a 159 en `master` |
| Cambio | Se quitó el bloque que descarta la propuesta igual a la respuesta correcta, sin tocar nada más |
| Dónde | Rama `josueacademico17-source-patch-1`, commit `487567c`, [PR #1](https://github.com/ISCOUTB/AS_202620_Sistema-de-calificacion-automatica/pull/1) |

Las ocho líneas que quitó el PR:

```python
        if forma == correcta:
            descartados.append(
                PropuestaDescartada(
                    propuesta.expresion,
                    "Repite la respuesta correcta: la pregunta quedaría con dos respuestas.",
                )
            )
            continue
```

**Por qué es el defecto que importa.** Un distractor igual a la respuesta correcta deja la pregunta
con dos respuestas válidas, y el estudiante que respondió bien pierde el punto: es el problema 2
del proyecto. Un modelo de lenguaje puede proponerlo, así que la regla del dominio no puede confiar
en él.

## Qué detectó el pipeline

**Paso que falló:** `Suite completa del backend`, del job `backend-tests`, en los dos runs de la
rama: el del `push` y el del `pull_request`. El paso `Prueba de contrato (OpenAPI)` pasó, porque
el contrato no cambió, y el job `frontend-tests` también pasó: la falla está acotada al defecto.

Las líneas del log del run del PR (resumen de pytest, recortado):

```
FAILED tests/test_distractores.py::test_la_respuesta_correcta_nunca_llega_como_distractor
  At index 1 diff: 'sin(x) + x·cos(x)' != 'sin(x) - x·cos(x)'
  Left contains one more item: 'sin(x) - x·cos(x)'
FAILED tests/test_distractores.py::test_la_respuesta_correcta_escrita_de_otra_forma_tambien_se_descarta
  At index 0 diff: 'SIN(x)+x*cos(x)' != 'x·cos(x)'
  Left contains one more item: 'x·cos(x)'
FAILED tests/test_distractores.py::test_un_exponente_escrito_con_circunflejo_es_el_mismo_que_en_superindice
  At index 0 diff: '5x^4' != 'x^4'
  Left contains one more item: 'x^4'
FAILED tests/test_ruta_distractores.py::test_devuelve_las_propuestas_y_lo_descartado_con_su_motivo
  Left contains one more item: {'expresion': 'sin(x)+x*cos(x)', 'error': 'Ninguno'}
```

**Fallan cuatro pruebas, y cada una dice qué se coló:**

| Prueba | Qué comprueba | Qué se coló sin el filtro |
|---|---|---|
| [`test_distractores.py`](../../backend/tests/test_distractores.py), `test_la_respuesta_correcta_nunca_llega_como_distractor` | La respuesta correcta, escrita igual | `sin(x) + x·cos(x)` |
| `test_la_respuesta_correcta_escrita_de_otra_forma_tambien_se_descarta` | La respuesta correcta con mayúsculas, sin espacios y con `*` | `SIN(x)+x*cos(x)` |
| `test_un_exponente_escrito_con_circunflejo_es_el_mismo_que_en_superindice` | La respuesta correcta con `^` en lugar del superíndice | `5x^4`, cuando la correcta es `5x⁴` |
| [`test_ruta_distractores.py`](../../backend/tests/test_ruta_distractores.py), `test_devuelve_las_propuestas_y_lo_descartado_con_su_motivo` | Lo mismo, visto desde `POST /distractores` | `sin(x)+x*cos(x)`, entregado al profesor por la API |

El resumen de pytest nombra cada prueba que falla, y en este run nombra estas cuatro y ninguna
más. Las demás pruebas de la suite pasan. El mismo cambio, ensayado antes en local sobre el mismo
código, dio 4 fallas y 101 pruebas en verde (la de encolado se omite sin Redis).

## Cómo terminó

**No hubo que restaurar nada.** El cambio vivió solo en la rama:
- María revisó el PR, dejó su comentario («El CI falla como se esperaba […] Se cierra sin fusionar:
  `master` no cambia») y lo **cerró sin fusionar** el 4-oct-2026 a las 18:47 (−05:00);
- después se borró la rama.

`master` siguió en verde en todo momento, y Render, que solo despliega commits de `master` con el
CI en verde, no desplegó nada del experimento.

## Referencias

| Momento | Commit | Run o enlace | Resultado |
|---|---|---|---|
| `master` antes del experimento | `12ba9d6` | [run 37242078635](https://github.com/ISCOUTB/AS_202620_Sistema-de-calificacion-automatica/actions/runs/37242078635) | Success |
| La rama con el defecto (`push`) | `487567c` | [run 37243370215](https://github.com/ISCOUTB/AS_202620_Sistema-de-calificacion-automatica/actions/runs/37243370215) | **Failure** |
| El PR #1 (`pull_request`) | `487567c` | [run 37244214146](https://github.com/ISCOUTB/AS_202620_Sistema-de-calificacion-automatica/actions/runs/37244214146) | **Failure**, con las 4 pruebas de arriba |
| La revisión y el cierre | | [PR #1](https://github.com/ISCOUTB/AS_202620_Sistema-de-calificacion-automatica/pull/1) | Cerrado sin fusionar, con la revisión de María |

## Cómo se repite

En local, desde `backend/`: quitar de `autoria/distractores.py` el bloque de arriba y correr
`pytest`. Tienen que fallar las mismas cuatro pruebas. Después se deshace el cambio, y la suite
vuelve a quedar entera en verde.

## Por qué con un PR y no con un commit en `master`

En la S7 la prueba de contrato se demostró con un commit incompatible en `master`, su run en rojo
y un revert ([`prueba-de-contrato-falla.md`](prueba-de-contrato-falla.md)). Esta vez se hizo con
un PR que no se fusiona, por tres razones:
- `master` no queda nunca en rojo;
- nadie tiene que dejar de subir mientras dura el experimento;
- queda un PR con revisión cruzada de otro integrante.
