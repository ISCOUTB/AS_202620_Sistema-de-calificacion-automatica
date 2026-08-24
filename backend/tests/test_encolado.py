"""Prueba 4: un trabajo encolado se puede recuperar de la cola. Corre contra un Redis real
(servicio `redis` de docker-compose, o el contenedor de servicio del CI) — es el germen de lo
que la semana 4 usará para verificar EC-07 (confirmación fiable de recepción del lote)."""

from infraestructura.cola import encolar, desencolar

NOMBRE_COLA = "prueba_encolado"


def test_trabajo_encolado_se_recupera_de_la_cola(cliente):
    payload = {"archivo": "hoja-001.png", "curso": "calculo-diferencial-2026-1"}

    trabajo_encolado = encolar(cliente, NOMBRE_COLA, payload)
    trabajo_recuperado = desencolar(cliente, NOMBRE_COLA, timeout=5)

    assert trabajo_recuperado is not None
    assert trabajo_recuperado.id == trabajo_encolado.id
    assert trabajo_recuperado.payload == payload
