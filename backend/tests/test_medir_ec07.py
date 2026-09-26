"""Prueba 8: la herramienta que mide EC-07 sigue corriendo contra el código de hoy.

`herramientas/medir_ec07.py` es la evidencia reproducible de las dos cifras del escenario
(`docs/evidencia/medicion-ec07.md`): quien quiera repetir la medición la corre y obtiene el
mismo procedimiento. Esa promesa se rompió una vez sin que nadie lo notara. La corrección de un
aviso de SonarQube le quitó a `ColaEnMemoria.rpush` un parámetro que su cuerpo no usaba, pero
que `infraestructura/cola.py` sí pasa, porque llama igual que a redis-py: `rpush(cola, valor)`.
La herramienta quedó terminando en `TypeError` y ninguna prueba la ejecutaba.

Estas pruebas corren las dos mediciones con lotes de pocas hojas. No miden nada: comprueban que
el procedimiento llega al final y que sus cifras salen con el sentido que tienen en la
evidencia. Se validaron provocando la falla: con la firma rota, `rpush(self, valor)`, las tres
fallan con el mismo `TypeError` que dejó la herramienta inservible.
"""

from herramientas.medir_ec07 import ColaEnMemoria, medir_latencia, medir_perdida_silenciosa


def test_la_cola_sustituta_acepta_la_llamada_de_redis_py() -> None:
    cola = ColaEnMemoria()

    assert cola.rpush("procesamiento", "trabajo") == 1
    assert cola.encolados == ["trabajo"]


def test_la_medicion_de_latencia_confirma_el_lote_entero() -> None:
    informe = medir_latencia(hojas=3, kilobytes=1, repeticiones=1)

    assert informe["hojas_confirmadas"] == 3
    assert informe["cumple"] is True


def test_la_medicion_de_perdida_reporta_todas_las_hojas_con_la_cola_caida() -> None:
    informe = medir_perdida_silenciosa(hojas=4, kilobytes=1, fallar_en=2)

    assert informe["codigo_http"] == 200
    assert informe["hojas_sin_reportar"] == 0
    assert informe["trabajos_encolados"] == 2
    assert informe["hojas_recuperables_desde_la_bitacora"] == 2
    assert informe["cumple"] is True
