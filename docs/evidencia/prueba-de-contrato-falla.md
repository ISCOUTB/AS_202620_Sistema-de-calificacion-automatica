# Evidencia de que la prueba de contrato falla

Este documento muestra que el pipeline de integración continua detecta un cambio incompatible
entre el código de la API y el contrato OpenAPI versionado en
[`../contrato/openapi.json`](../contrato/openapi.json). El experimento se puede reproducir con
los commits y los runs de la sección *Referencias*.

Una prueba que pasa siempre no prueba nada. Lo que sigue es la comprobación de que esta falla
cuando debe.

## Qué se cambió

| | |
|---|---|
| Archivo | `backend/api/esquemas.py` |
| Clase | `HojaAceptadaEnRespuesta` |
| Línea | 55, en el commit `6111a53` |
| Cambio | El campo `nombre_archivo` de la respuesta pasó a llamarse `archivo`, **sin regenerar el contrato**. |

Antes, compatible con el contrato:

```python
    nombre_archivo: str = Field(description="Nombre con el que el docente envio el archivo.")
```

Después, incompatible:

```python
    archivo: str = Field(description="Nombre con el que el docente envio el archivo.")
```

**Por qué es un cambio incompatible y no cosmético.** Un consumidor que hoy lee `nombre_archivo`
deja de encontrarlo, y nada se lo avisa hasta que su código falla. No es hipotético: el cliente
Flutter de este mismo repositorio lo lee en
[`frontend/lib/servicio_carga.dart`](../../frontend/lib/servicio_carga.dart) línea 27, con
`json['nombre_archivo'] as String`, y ese `as String` sobre un valor ausente revienta en tiempo
de ejecución.

Se modificó el código y no el contrato a propósito. La prueba existe para detectar que la
implementación se aparta de lo que el repositorio publica, y esa es exactamente la situación que
se reproduce aquí.

## Qué detectó el pipeline

**Paso que falló:** `Prueba de contrato (OpenAPI)`, del job `backend-tests`.

```
__________ test_el_contrato_versionado_es_el_que_genera_la_aplicacion __________
AssertionError: El contrato versionado ya no describe a esta aplicacion:
  esquema cambiado: HojaAceptadaEnRespuesta (campos quitados: ['nombre_archivo']; nuevos: ['archivo'])

Si el cambio era intencional, regeneralo y commitea el diff:
  cd backend && python -m herramientas.exportar_contrato
Si no lo era, el cambio rompe a quien ya consume la API.
tests/test_contrato.py:133: AssertionError

_______ test_una_respuesta_real_trae_exactamente_los_campos_del_contrato _______
pydantic_core._pydantic_core.ValidationError: 1 validation error for HojaAceptadaEnRespuesta
archivo
  Field required [type=missing, input_value=HojaAceptada(examen_id='C...utc), estado='encolada'),
  input_type=HojaAceptada]

=========================== short test summary info ============================
FAILED tests/test_contrato.py::test_el_contrato_versionado_es_el_que_genera_la_aplicacion
FAILED tests/test_contrato.py::test_una_respuesta_real_trae_exactamente_los_campos_del_contrato
2 failed, 4 passed
```

Fallan **dos de las seis** pruebas de contrato, y fallan por motivos distintos, que es lo que
hace útil la evidencia. La primera compara el documento versionado contra el que genera la
aplicación y nombra el esquema que cambió. La segunda ejerce el endpoint de verdad y comprueba
que la respuesta cabe en el esquema publicado; ahí el fallo llega desde Pydantic, porque la
respuesta real ya no encaja en lo que el contrato promete.

El job `backend-tests` terminó con código de salida **1**, el de pruebas fallidas, mientras
`frontend-tests` pasó sin novedad: la regresión está acotada al contrato de la API y no al
resto del sistema.

**La suite completa no llegó a correr.** El paso de contrato se ejecuta antes que
`Suite completa del backend` y, al fallar, el job se detiene. Eso es deliberado: un contrato
desincronizado corta el pipeline en segundos en vez de al final.

## Referencias

| Estado | Commit | Run |
|---|---|---|
| Verde anterior al experimento | `4d5bc85` | [Run 35547431838](https://github.com/ISCOUTB/AS_202620_Sistema-de-calificacion-automatica/actions/runs/35547431838) |
| **Rojo del cambio incompatible** | `6111a53` | [Run 35548751589](https://github.com/ISCOUTB/AS_202620_Sistema-de-calificacion-automatica/actions/runs/35548751589) |
| Verde tras revertir | `942e6ac` | [Run 35549237474](https://github.com/ISCOUTB/AS_202620_Sistema-de-calificacion-automatica/actions/runs/35549237474) |

El commit `942e6ac` restituye el nombre del campo. Su run terminó en *Success* y ejecutó los dos
jobs del workflow, `backend-tests` y `frontend-tests`.

## Qué prueba esto y qué no

**Prueba** que un cambio incompatible del contrato no puede llegar a `master` sin que el pipeline
lo marque. El run rojo quedó en el historial y el posterior, tras revertir, volvió a verde.

**No prueba** que la prueba detecte cualquier cambio incompatible posible. Detecta los que
alteran el documento OpenAPI que genera la aplicación, que es su alcance declarado. Un cambio de
comportamiento que deje intacto el esquema publicado, por ejemplo devolver un valor equivocado
dentro de un campo del tipo correcto, queda fuera de lo que esta prueba verifica.
