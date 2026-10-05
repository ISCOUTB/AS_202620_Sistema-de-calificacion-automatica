# 0013 · Consumir Groq detrás de un puerto y degradar sin bloquear la autoría

- **Estado:** aceptado
- **Fecha:** 2026-10-04
- **Decide:** Josué Ortega De Arco, María Restrepo Licona, Sebastián Cañas Plata, Susana Rosales Castellar
- **Escenario de calidad relacionado:** [EC-08](../arc42/arc42-template-ES.md#ec-08) (propuesta de distractores diagnósticos)
- **Restricciones que lo acotan:** RNF-11 (ninguna credencial versionada), RNF-13 (ningún dato personal al proveedor), RNF-16 (US$0 y sin tarjeta)
- **Relación con otros ADR:** precisa [ADR-0005](0005-acotar-el-llm-a-la-generacion-de-distractores-diagnosticos.md) sin reemplazarlo, y cierra el riesgo R-02

**La decisión, en una frase:** los distractores diagnósticos de RF-11 los propone Groq, con el modelo `openai/gpt-oss-120b`, llamado desde un adaptador de `autoria` detrás de un puerto; si el proveedor falla o tarda más de 20 s, la ruta responde 503 con el motivo y nada más del sistema se entera.

---

## Contexto

[ADR-0005](0005-acotar-el-llm-a-la-generacion-de-distractores-diagnosticos.md) decidió *dónde*
participa el LLM: solo en la autoría, a pedido del profesor, para proponer distractores
diagnósticos (RF-11), y nunca en la calificación. No decidió *cómo* se consume, y eso quedó como
el riesgo R-02. R-12 advertía además que RF-11 podía quedarse sin construir.

En la S9, la revisión preliminar dejó escrito que el componente generativo existe como capacidad
del sistema, así que hay que evaluarlo con resultados, costo y latencia. El equipo eligió
construir RF-11 como la porción de la semana (aspecto A-06) y decidir aquí cómo se consume.

Lo que acota la decisión:
- **RNF-16:** costo de US$0 y ninguna cuenta con tarjeta.
- **RNF-13:** al proveedor solo puede viajar la pregunta: ni nombres, ni notas, ni hojas.
- **RNF-11:** la clave llega por el entorno, nunca por el repositorio.
- **El arc42 ya fijó la forma:** aislamiento hexagonal solo en `autoria` (§4.1) y una capa
  anticorrupción hacia el proveedor (§8.1, relación 5).
- **La carga es pequeña:** unas pocas solicitudes por examen, en la semana de preparación.

## Alternativas consideradas

Los proveedores se compararon el 4-oct-2026 en sus páginas oficiales; solo Groq se probó con
llamadas reales: una llamada de prueba (HTTP 200 en 1,87 s) y una corrida de 3 preguntas (p95 de
2,3 s).

### 1. El proveedor

| Opción | A favor | En contra | |
|---|---|---|---|
| **Groq** | Sin tarjeta: el pago solo se pide para pasar al plan de pago. La cuota gratuita está publicada: 30 solicitudes por minuto, 1 000 por día, 8 000 tokens por minuto y 200 000 por día. Compatible con el protocolo de OpenAI, con salida JSON. Por defecto no retiene lo que se le envía | La cuota de 8 000 tokens por minuto obliga a espaciar las solicitudes en una evaluación | **Elegida** |
| Google AI Studio (Gemini) | Sin tarjeta y compatible con el protocolo de OpenAI | Su cuota gratuita no está publicada en la documentación, solo en el panel; en la capa gratuita usa lo que se le envía para mejorar sus productos | Respaldo |
| OpenRouter (modelos gratuitos) | Compatible con el protocolo de OpenAI | 50 solicitudes por día sin comprar créditos: no alcanzan para la evaluación | Descartada |
| Mistral | Sin tarjeta | Sus límites y su política de datos no están publicados en las páginas revisadas: este ADR no podría citarlos | Descartada |
| Un modelo local | Nada sale de la instancia | La instancia gratuita de Render tiene 0,1 CPU y 512 MB; R-02 ya lo descartaba por hardware | Descartada |

### 2. Cómo se llama al proveedor

| Opción | | Por qué |
|---|---|---|
| El SDK `openai` | Descartada | Agregar una dependencia obliga a regenerar el lock en Linux, y su método `chat.completions.create(` aparece en el grep de erosión que corre el revisor |
| `urllib.request`, de la biblioteca estándar | Descartada | `httpx` ya es dependencia directa del backend y lo usa `medir_arranque_en_frio.py` |
| **`httpx`** | **Elegida** | No agrega ninguna dependencia, y con `httpx.MockTransport` todo el adaptador se prueba sin red |

### 3. Qué hacer cuando el proveedor falla

| Opción | | Por qué |
|---|---|---|
| Reintentar automáticamente | Descartada | Duplica la cuota gastada y la espera del profesor, justo cuando el proveedor ya está fallando |
| **Esperar como máximo 20 s, no reintentar y responder 503 con el motivo** | **Elegida** | El profesor decide si vuelve a pedir o escribe los distractores a mano; el registro manual y la calificación no dependen del proveedor |

### 4. Detectar automáticamente un distractor equivalente a la respuesta correcta

En la corrida de prueba el modelo propuso `sin(2x)` como distractor de `2·sin(x)·cos(x)`, que es la
misma expresión. Detectarlo exige cálculo simbólico, por ejemplo con SymPy.

**Descartada para esta entrega.** Un prototipo fuera del repositorio midió cómo se vería:
traduce la notación del profesor y del modelo (`x²`, `eˣ`, `√x`, `sin²(x)`, `·`) a SymPy, y compara
simplificando la diferencia o, si eso no decide, evaluando en puntos al azar. Sobre las 120 propuestas
de la corrida oficial más el caso de `sin(2x)`, detectó esa equivalencia y ninguna otra, tardó 15 ms
por comparación y no pudo leer 1 de 121 expresiones, que el modelo escribió con llaves de LaTeX.

No se construyó en esta entrega por tres razones:
- **Con los datos de esta semana no habría descartado nada:** la evaluación no encontró ninguna
  propuesta equivalente en 120.
- **Vuelve a meter la librería que ADR-0004 retiró** por indicación del profesor, con su lock
  regenerado en Linux y un traductor de notación, que es la parte frágil.
- **El profesor revisa cada propuesta igual** antes de habilitar el examen (RF-07, ADR-0005).

El equipo prevé retomarla la próxima semana, con su propio ADR. **Estas dos condiciones la vuelven
obligatoria, aunque ese plan cambie:**
1. una evaluación con el método de la [evaluación de EC-08](../evidencia/evaluacion-distractores.md)
   mide más de una propuesta equivalente a la respuesta correcta por cada 20 preguntas (5 %); en la
   de esta semana fue 0 %;
2. se detecta un examen habilitado con un distractor equivalente a la respuesta correcta.

Mientras tanto, la regla del dominio descarta las repeticiones textuales y las equivalencias las
decide el profesor (ADR-0005), que es lo que R-11 ya describe.

## Decisión

1. **El proveedor es Groq, con el modelo `openai/gpt-oss-120b`**, en su capa gratuita y sin
   tarjeta. Si la latencia no cumpliera M2, el respaldo es `openai/gpt-oss-20b` en el mismo
   proveedor; si Groq dejara de servir, Gemini.
2. **Detrás de un puerto de `autoria`.** `GeneradorDeDistractores` es el puerto, en
   [`autoria/distractores.py`](../../backend/autoria/distractores.py), y
   `GeneradorCompatibleConOpenAI`, en [`autoria/proveedor_llm.py`](../../backend/autoria/proveedor_llm.py),
   es el adaptador: la capa anticorrupción de la relación 5 del mapa de contextos. El formato del
   proveedor no sale de ese archivo.
3. **Con el protocolo de chat compatible con OpenAI**, configurado por tres variables de entorno:
   `LLM_URL_BASE`, `LLM_MODELO` y `LLM_API_KEY`. Cambiar de proveedor es cambiar esas tres, no el
   código.
4. **Con `httpx`**, sin SDK y sin dependencias nuevas.
5. **Ante cualquier falla, 503 con el motivo.** El adaptador espera como máximo 20 s y no
   reintenta. El tiempo agotado, la cuota agotada (429), la clave rechazada, un error del
   proveedor y una respuesta ilegible terminan en `ProveedorNoDisponible`, y la ruta
   `POST /distractores` responde 503 con el motivo para el profesor. Sin clave configurada, la ruta
   responde 503 sin salir a la red.
6. **La regla de qué llega al profesor es del dominio, no del proveedor.**
   `filtrar_propuestas` descarta, con su motivo, la propuesta que repite la respuesta correcta
   (aunque esté escrita distinto: `x²` o `x^2`, `·` o `*`), la repetida, la que no trae la
   etiqueta del error y la que sobra. Ninguna propuesta entra a un examen sin la habilitación del
   profesor (RF-07).
7. **RNF-13 por construcción.** Al proveedor solo viajan los tres campos de
   `PreguntaParaDistractores` con una plantilla fija, y una prueba compara el cuerpo entero de la
   solicitud.
8. **En el entorno desplegado**, la clave se escribe en el panel de Render (`sync: false` en
   `render.yaml`), nunca en el repositorio.
9. **La métrica de EC-08** es el evento `distractores_propuestos` (o `proveedor_no_disponible`),
   con la duración y los tokens, como `lote_confirmado` lo es de EC-07.

## Consecuencias

### Positivas

- R-02 y R-12 quedan cerrados: el proveedor está decidido y RF-11, construido.
- Cambiar de proveedor es cambiar tres variables: el dominio no conoce a Groq.
- La calificación no cambia en nada: el LLM sigue fuera de ella (ADR-0005), y una caída del
  proveedor no la toca.
- El costo es US$0. Sin tarjeta, el peor caso es agotar la cuota y nunca una factura.
- La falla del proveedor queda contenida en una respuesta 503 con un motivo legible.

### Negativas

- **El sistema depende de una cuota externa** que Groq puede cambiar sin aviso. Se mitiga con el
  respaldo del punto 1 y verificando la capa gratuita antes de cada sustentación.
- **La ruta queda pública sin autenticación** en el entorno desplegado, y cada solicitud gasta
  cuota (R-17). Se cierra con `identidad` (A-05).
- **El sistema no detecta un distractor equivalente a la respuesta correcta** (R-11). La
  evaluación de EC-08 no encontró ninguno en 120 propuestas, pero la corrida de prueba mostró
  que puede pasar.
- **La página de Groq no dice nada sobre si entrena con lo que recibe.** Es aceptable porque, por
  RNF-13, solo viaja la pregunta.
- **La latencia de EC-08 se mide dentro del proceso de la API**, sin la red del profesor.

## Trazabilidad

- **Requisito y aspecto:** RF-11, aspecto [A-06](../aspectos.md#a-06).
- **Escenario:** [EC-08](../arc42/arc42-template-ES.md#ec-08), medido en la
  [evaluación](../evidencia/evaluacion-distractores.md) con el
  [conjunto de 20 preguntas](../evidencia/conjunto-evaluacion-distractores.json) y el
  [resultado completo](../evidencia/evaluacion-distractores.json).
- **C4:** relación 3 del Nivel 1, relación 8 del Nivel 2 y `autoria` en el Nivel 3
  ([`c4/doc-c4.md`](../c4/doc-c4.md#relaciones-1)).
- **Código:** [`autoria/distractores.py`](../../backend/autoria/distractores.py),
  [`autoria/proveedor_llm.py`](../../backend/autoria/proveedor_llm.py),
  [`api/main.py`](../../backend/api/main.py) y la herramienta
  [`evaluar_distractores.py`](../../backend/herramientas/evaluar_distractores.py).
- **Pruebas:** [`test_distractores.py`](../../backend/tests/test_distractores.py),
  [`test_proveedor_llm.py`](../../backend/tests/test_proveedor_llm.py) y
  [`test_ruta_distractores.py`](../../backend/tests/test_ruta_distractores.py), más la
  [prueba que falla ante el defecto](../evidencia/prueba-distractores-falla.md).
- **Commits que lo implementan:** `e81dbce` (la regla del dominio), `89dfaae` (su prueba), `aee3a99`
  y `1c93e51` (el adaptador y sus pruebas), `a1b870d` (la interfaz de `autoria`), `dde5e7d` (la ruta
  y el contrato 1.1.0), `3385d67` (la prueba de fronteras), `f5b0ac0` (la herramienta de
  evaluación), `03d69f5` y `12ba9d6` (la configuración), y `8183e96` (la corrida oficial).
- **Fuentes de la comparación de proveedores**, consultadas el 4-oct-2026:
  - Groq: https://console.groq.com/docs/rate-limits, https://console.groq.com/docs/openai, https://console.groq.com/docs/structured-outputs, https://console.groq.com/docs/your-data, https://console.groq.com/docs/billing-faqs y https://console.groq.com/docs/models
  - Gemini: https://ai.google.dev/gemini-api/docs/rate-limits, https://ai.google.dev/gemini-api/docs/pricing, https://ai.google.dev/gemini-api/docs/billing y https://ai.google.dev/gemini-api/docs/openai
  - OpenRouter: https://openrouter.ai/docs/api-reference/limits
  - Mistral: https://docs.mistral.ai/getting-started/quickstarts/studio/activate-and-generate-api-key y https://docs.mistral.ai/admin/user-management-finops/tier
