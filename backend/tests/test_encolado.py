"""Prueba 4: un trabajo encolado se puede recuperar de la cola. Corre contra un Redis real
(servicio `redis` de docker-compose, o el contenedor de servicio del CI) — es el germen de lo
que la semana 4 usará para verificar EC-07 (confirmación fiable de recepción del lote)."""

from infraestructura.cola import encolar, desencolar

NOMBRE_COLA = "prueba_encolado"


def test_trabajo_encolado_se_recupera_de_la_cola(cliente):
    # Un payload que cumple el contrato del mensaje (ADR-0020): `desencolar` lo lee con él.
    payload = {
        "hoja_id": "h-001",
        "examen_id": "calculo-diferencial-2026-1",
        "referencia": "calculo-diferencial-2026-1/hoja-001.png",
        "nombre_archivo": "hoja-001.png",
    }

    trabajo_encolado = encolar(cliente, NOMBRE_COLA, payload)
    trabajo_recuperado = desencolar(cliente, NOMBRE_COLA, timeout=5)

    assert trabajo_recuperado is not None
    assert trabajo_recuperado.id == trabajo_encolado.id
    assert trabajo_recuperado.payload == payload
