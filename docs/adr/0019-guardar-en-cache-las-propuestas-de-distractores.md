# 0019 · Guardar en caché las propuestas de distractores

- **Estado:** aceptado
- **Fecha:** 2026-10-24
- **Decide:** Josué Ortega De Arco, María Restrepo Licona, Sebastián Cañas Plata, Susana Rosales Castellar
- **Escenarios de calidad relacionados:** [EC-08](../arc42/arc42-template-ES.md#ec-08) (propuesta de distractores) y [EC-09](../arc42/arc42-template-ES.md#ec-09) (ráfaga contra la ruta, límite de costo)
- **Origen:** la entrega de consistencia y caché, que pide el diseño de una caché con su política de invalidación ([`consistencia-y-cache.md`](../evidencia/consistencia-y-cache.md))
- **Restricciones que lo acotan:** RNF-16 (US$0 y sin tarjeta), RNF-13 (al proveedor solo llega la pregunta), una sola instancia de la API con un solo proceso ([ADR-0009](0009-desplegar-la-api-en-el-servicio-web-gratuito-de-render-y-mantenerla-despierta.md), [ADR-0011](0011-consumir-la-cola-desde-la-instancia-de-la-api-con-el-key-value-gratuito.md))
- **Relación con otros ADR:** precisa [ADR-0013](0013-consumir-groq-detras-de-un-puerto-y-degradar-sin-bloquear-la-autoria.md) y [ADR-0015](0015-limitar-el-gasto-del-proveedor-de-llm-con-un-presupuesto-en-la-api.md) sin reemplazarlos; respeta [ADR-0018](0018-dar-a-la-hoja-una-identidad-propia-y-derivar-su-estado-de-la-bitacora.md), que deja fuera de cualquier caché el estado de una hoja

**La decisión, en una frase:** las propuestas que devuelve el proveedor para una pregunta se guardan
24 horas en la memoria de la API, con el modelo y las instrucciones en la clave, y la misma pregunta
pedida otra vez se responde desde ahí sin llamar al proveedor ni gastar cupo, salvo que el profesor
pida otras.

---

## Contexto

**Lo que cuesta una solicitud.** Cada `POST /distractores` que llega al proveedor gasta uno de los
6 cupos por minuto y 150 por día del presupuesto (ADR-0015) y unos 2,1 s de espera del profesor (la
mediana de EC-08). Con el presupuesto, una ráfaga ya no agota la cuota de Groq, pero un profesor
que vuelve a abrir la misma pregunta sigue gastando un cupo por algo que el sistema ya tenía.

**Lo que se repite.** La misma pregunta se pide más de una vez: el docente vuelve a la pregunta
para revisar las propuestas, el navegador reenvía, y los profesores del mismo curso arman parciales
con las mismas preguntas del banco. Una propuesta para la derivada de `x·sin(x)` no envejece: sirve
igual al día siguiente.

**Lo que no se puede guardar.** El estado de una hoja: es dato del que el docente decide si vuelve a
subir algo, y ADR-0018 dice que sale de la bitácora y de ningún otro lado. Las propuestas no son de
ninguna hoja, de ningún estudiante ni de ningún profesor.

**Lo que hay que respetar.** «Pedir otras propuestas» existe en el sitio para recibir propuestas
**distintas** de las que el profesor ya vio. Una caché que respondiera eso con lo mismo rompería la
pantalla.

## Alternativas consideradas

### 1. Qué se guarda

| Opción | A favor | En contra | |
|---|---|---|---|
| **No guardar nada** (statu quo) | Cero código | Cada repetición gasta un cupo y 2 s | Descartada |
| **La respuesta HTTP ya filtrada** | Una lectura y se responde | Congela la regla: un arreglo como los del 19-oct no valdría para lo guardado hasta que venciera | Descartada |
| **Lo que devolvió el proveedor, sin filtrar, y la regla en cada lectura** | Un cambio de la regla vale desde la solicitud siguiente, sin invalidar nada; la caché es un adaptador más del puerto | La regla corre otra vez en cada acierto (microsegundos) | **Elegida** |

### 2. Dónde vive

| Opción | A favor | En contra | |
|---|---|---|---|
| **En la memoria del proceso de la API** | Sin red, sin dependencias, sin modos de fallo nuevos; con una sola instancia es correcta | Se vacía en cada despliegue; con dos instancias cada una tendría la suya | **Elegida** |
| **En Redis, el Key Value** | Compartida entre instancias, sobrevive a reinicios de la API | Una ida y vuelta de red por solicitud, con los tres modos de fallo de la S11; el Key Value gratuito tampoco persiste; con una sola instancia no hay nada que compartir | Prevista si la API escala (R-27) |
| **En el navegador** | Ni siquiera llega a la API | Solo sirve al mismo profesor en la misma pestaña, y no protege la cuota de los demás | Descartada |

### 3. Cómo se invalida

| Opción | | Por qué |
|---|---|---|
| Solo por tiempo | Descartada | Un cambio de modelo o de instrucciones serviría propuestas del modelo anterior durante 24 h |
| Borrar a mano cuando algo cambia | Descartada | Depende de que alguien se acuerde, que es justo lo que falla |
| **La versión en la clave, más tiempo, capacidad y la petición explícita del profesor** | **Elegida** | Cada cosa que puede volver falsa una propuesta guardada tiene su mecanismo, y ninguno depende de acordarse |

## Decisión

1. **`GeneradorConCache`**, en [`autoria/cache.py`](../../backend/autoria/cache.py), implementa el
   puerto `GeneradorDeDistractores` leyendo de la caché antes de delegar. Va **por fuera** del
   presupuesto: `ruta → regla → caché → presupuesto → Groq`. Un acierto no gasta cupo.
2. **La clave** es el SHA-256 de la versión, el enunciado y la respuesta correcta con los espacios
   normalizados, y la cantidad. **La versión** es el modelo (`LLM_MODELO`) y la huella de las
   instrucciones que recibe (`HUELLA_DE_LAS_INSTRUCCIONES`, un SHA-256 de su texto).
3. **El valor** son las propuestas tal como llegaron del proveedor. La regla corre en cada lectura.
4. **Invalidación:**
   - **por versión**: cambiar el modelo o el texto de las instrucciones cambia las claves;
   - **por tiempo**: 24 horas desde que se guardó, sin renovarse al leer;
   - **por capacidad**: 256 entradas, sale la que lleva más tiempo sin leerse;
   - **por el profesor**: `otras: true` no lee la caché, va al proveedor y reemplaza lo guardado;
   - **por reinicio**: vive en memoria.
5. **No se guarda** un 503, un 429 ni una respuesta sin propuestas.
6. **La respuesta dice `desde_la_cache`**, y `GET /metricas` publica aciertos, fallos, entradas,
   guardadas, vencidas y expulsadas.
7. **«Pedir otras propuestas» manda `otras: true`** desde el sitio. «Volver a pedir», después de una
   falla, no lo necesita: las fallas no se guardan.
8. **Las herramientas de medición mandan `otras: true`** (`medir_presupuesto.py` y
   `evaluar_distractores.py`), para seguir midiendo al proveedor y no a la caché.
9. **El contrato pasa a 1.4.0**: `otras` en la solicitud, `desde_la_cache` en la respuesta y
   `cache_de_distractores` en `/metricas`. Solo agrega.

**Por qué no reemplaza a ADR-0013 ni a ADR-0015.** El proveedor, su adaptador, los 20 s sin
reintentos y el 503 siguen igual; el presupuesto sigue contando cada solicitud que sale a la red.
La caché decide cuántas salen.

## Consecuencias

### Positivas

- **La pregunta repetida no gasta cupo** y se responde aunque el presupuesto del minuto esté
  agotado: un 429 menos para el profesor que vuelve a una pregunta.
- **Se responde en lo que tarda la regla**, en vez de los 2 s del proveedor.
- **Ninguna regla de invalidación depende de acordarse de algo.**
- **No hay modo de fallo nuevo**: no hay red de por medio.

### Negativas

- **El profesor puede recibir propuestas de hasta un día.** Para propuestas de matemática no es un
  problema, y si quiere otras las pide.
- **Con más de una instancia, cada una tendría su caché** y los aciertos bajarían (R-27).
- **Dos pedidos simultáneos de una pregunta nueva salen los dos al proveedor**: no se coordinan.
  Con 6 por minuto no compensa.
- **La exclusión mutua no tiene una prueba que la detecte**: la de hilos comprueba que las cuentas
  cuadran y siguió en verde sin el candado.
- **Las pruebas del presupuesto corren ahora con una caché de capacidad 0**, porque mandan la misma
  pregunta varias veces.

## Reversión

Pasar el generador sin envolver en la ruta de `api/main.py`. El contrato conservaría `otras` y
`desde_la_cache` sin efecto (este último, siempre `false`), que no rompe a ningún cliente.

## Qué dato haría revisar esta decisión

- **Que la API corra en más de una instancia:** la caché pasa a Redis con la misma clave y
  `SET … EX 86400` (R-27).
- **Que `GET /metricas` muestre una proporción de aciertos muy baja con tráfico real:** la caché no
  paga lo que cuesta y se quita.
- **Que un profesor reporte propuestas que no tienen sentido para su pregunta:** revisar si la
  clave confunde dos preguntas distintas.

## Trazabilidad

- **Código:** [`autoria/cache.py`](../../backend/autoria/cache.py),
  [`autoria/proveedor_llm.py`](../../backend/autoria/proveedor_llm.py) (la huella),
  [`api/main.py`](../../backend/api/main.py) (la ruta y `/metricas`),
  [`api/esquemas.py`](../../backend/api/esquemas.py) (contrato 1.4.0) y, en el sitio,
  [`servicio_distractores.dart`](../../frontend/lib/features/pauta/data/servicio_distractores.dart) y
  [`pantalla_pauta.dart`](../../frontend/lib/features/pauta/views/pantalla_pauta.dart).
- **Pruebas:** [`test_cache_de_propuestas.py`](../../backend/tests/test_cache_de_propuestas.py),
  validadas con una mutación por regla de invalidación, y en el sitio
  [`pauta_test.dart`](../../frontend/test/features/pauta_test.dart) y
  [`servicio_distractores_test.dart`](../../frontend/test/features/servicio_distractores_test.dart).
- **Diseño y consistencia:** [`consistencia-y-cache.md`](../evidencia/consistencia-y-cache.md),
  filas C-07 y C-08.
- **Riesgos:** abre R-27 ([arc42 §11](../arc42/arc42-template-ES.md#11-risks-and-technical-debts)).
- **C4:** relación 8 del Nivel 2 y relación 11 del Nivel 3 ([`c4/doc-c4.md`](../c4/doc-c4.md)).
