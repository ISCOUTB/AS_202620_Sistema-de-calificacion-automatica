# Evidencia de que la prueba de contrato falla

Este documento muestra que el pipeline de integración continua detecta un cambio incompatible entre el código de la API y el contrato OpenAPI versionado en `docs/api/openapi.json`. Se puede reproducir con los enlaces de la sección "Referencias".

## Qué se cambió

- Archivo: `backend/api/esquemas.py`
- Clase: `HojaAceptadaEnRespuesta`
- Línea: 55 (en el commit `6111a53`)
- Cambio: el campo `nombre_archivo` de la respuesta pasó a llamarse `archivo`. El contrato `docs/api/openapi.json` no se modificó.

Antes (compatible con el contrato):

```python
    nombre_archivo: str = Field(description="Nombre con el que el docente envio el archivo.")
```

Después (incompatible):

```python
    archivo: str = Field(description="Nombre con el que el docente envio el archivo.")
```

El cambio es incompatible y no cosmético porque un consumidor que hoy lee `nombre_archivo` deja de encontrarlo, y nada se lo avisa hasta que su código falla. Es el caso del cliente Flutter, que interpreta ese campo en `frontend/lib/servicio_carga.dart`.

Se rompió el código y no el contrato de forma deliberada. La prueba debe fallar cuando la implementación se aparta del contrato publicado, y esa es la situación que se reproduce aquí.

## Qué detectó el pipeline

- Paso que falló: `<nombre del paso tal como aparece en la pestaña Actions>`
- Mensaje de error completo:

```
<pegar aquí la salida completa del fallo de pytest>
```

La suite completa no llegó a correr, porque la prueba de contrato corta antes: el paso de contrato se ejecuta primero y, al fallar, el job se detiene sin ejecutar el resto de las pruebas.

## Referencias

| Estado | Commit | Enlace |
| --- | --- | --- |
| Run verde anterior | `<hash>` | `<URL del run>` |
| Run rojo | `6111a53` | [Commit 6111a53](https://github.com/ISCOUTB/AS_202620_Sistema-de-calificacion-automatica/commit/6111a535aa410b0c68a6143d8716c8cd202e0e5b) |
| Run verde del revert | `942e6ac` | [Run 35549237474](https://github.com/ISCOUTB/AS_202620_Sistema-de-calificacion-automatica/actions/runs/35549237474) |

El commit `942e6ac` ("Rename 'archivo' to 'nombre_archivo' in esquemas.py") restituye el nombre del campo. Su run terminó en estado Success y ejecutó los dos jobs del workflow, `backend-tests` y `frontend-tests`.

## Qué prueba esto y qué no

Prueba que un cambio incompatible del contrato no puede llegar a `master` sin que el pipeline lo marque: el run rojo quedó en el historial de `master` y el run posterior, tras revertir, volvió a verde.

No prueba que la prueba detecte cualquier cambio incompatible posible. Detecta los que alteran el documento OpenAPI que genera la aplicación, que es su alcance declarado. Un cambio de comportamiento que deje intacto el esquema publicado, por ejemplo un valor incorrecto dentro de un campo con el tipo correcto, queda fuera de lo que esta prueba verifica.
