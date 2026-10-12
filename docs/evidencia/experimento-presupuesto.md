# Experimento del segundo corte: una ráfaga contra la ruta de distractores

Este documento es la evidencia del escenario operativo del segundo corte, de **límite de costo**,
y del escenario de calidad que lo mide, [EC-09](../arc42/arc42-template-ES.md#ec-09). Contiene la
hipótesis, el montaje, la ejecución, el resultado y la conclusión, con los informes en crudo y el
procedimiento para repetir cada corrida. La decisión que separa el antes del después es
[ADR-0015](../adr/0015-limitar-el-gasto-del-proveedor-de-llm-con-un-presupuesto-en-la-api.md).

---

## 1. El escenario

`POST /distractores` es pública y sin autenticación (R-17), y cada solicitud gasta cuota de la capa
gratuita de Groq. La pregunta que el segundo corte le hace al MVP desplegado es qué pasa cuando
alguien la golpea con una ráfaga: un profesor que hace doble clic veinte veces, un script, o
alguien fuera del curso que encontró la URL.

**La línea base, medida antes de cambiar nada** (11-oct-2026, 16:31, entorno desplegado, desde
internet residencial en Cartagena; [`presupuesto-antes.json`](presupuesto-antes.json)): de 20
solicitudes seguidas, **las 20 llegaron al proveedor**; 12 recibieron propuestas y **8 terminaron
en 503 porque Groq cortó por cuota**. La ráfaga duró 22,3 s, y en los primeros 18 una sola persona
agotó el límite por minuto de todo el sistema. `/health` siguió en 200: la API no se cayó, pero la
ruta quedó inutilizable para cualquier otro profesor durante ese minuto.

## 2. Hipótesis

> **Si** la API reserva un cupo antes de salir a la red, con un presupuesto de 6 solicitudes por
> minuto y 150 por día ([ADR-0015](../adr/0015-limitar-el-gasto-del-proveedor-de-llm-con-un-presupuesto-en-la-api.md)),
> **entonces** una ráfaga de 20 solicitudes seguidas no agota la cuota del proveedor: a lo sumo 6
> llegan a él, ninguna termina en 503 por cuota, las demás reciben un 429 propio en menos de 1 s
> con `Retry-After`, y `/health` sigue respondiendo 200.

**Criterios de aceptación**, fijados antes de medir. Son las medidas de EC-09:

| Medida | Umbral | De dónde sale |
|---|---|---|
| **M1:** solicitudes de la ráfaga que el proveedor corta por cuota (503) | 0 | El problema medido en la línea base: 8 |
| **M2:** solicitudes de la ráfaga que llegan al proveedor | 6 o menos | El presupuesto por minuto |
| **M3:** p95 del tiempo de respuesta de un 429 de la API, medido desde el cliente | 1 s o menos | Un rechazo que no sale a la red no puede tardar como una solicitud al modelo (mediana de 1,7 s) |
| **M4:** `/health` durante y después de la ráfaga | 200 en todas las consultas | El resto de la API no puede enterarse |

La hipótesis se rechaza si falla cualquiera de las cuatro.

## 3. Montaje

Hay dos montajes, y cada uno responde una pregunta distinta.

| | A · Local, con proveedor simulado | B · Entorno desplegado, con Groq |
|---|---|---|
| Qué responde | ¿El presupuesto, y solo él, cambia el resultado? | ¿Responde así el MVP desplegado? |
| API | `uvicorn api.main:app` en `127.0.0.1:8000`, un proceso, como en Render | `https://quantia-utb-api.onrender.com`, servicio web Free de Render, despierto por el monitor |
| Proveedor | [`proveedor_simulado.py`](../../backend/herramientas/proveedor_simulado.py): imita `/chat/completions` de Groq, aplica su límite publicado de 8 000 tokens por minuto, gasta 856 tokens por solicitud y tarda 1,7 s en responder | Groq, `openai/gpt-oss-120b`, capa gratuita y sin tarjeta |
| Antes | El código de `master` en `544a469`, sin presupuesto | El código de `master` en `7201193`, sin presupuesto |
| Después | El código con ADR-0015 | El código con ADR-0015, desplegado por Render tras el CI en verde |
| Ventaja | Aísla una sola variable: el proveedor se comporta igual en las dos corridas y no gasta cuota | Es el sistema real, con la red real y el proveedor real |
| Limitación | El simulador no imita la tolerancia de Groq en ráfaga (en la línea base dejó pasar 12, el simulador deja pasar 9) | La cuota que otros hayan gastado ese minuto puede cambiar el resultado |

**La carga es la misma en las cuatro corridas:** 20 solicitudes seguidas, sin pausa, con las
preguntas del conjunto de evaluación de EC-08 en orden, lanzadas por
[`medir_presupuesto.py`](../../backend/herramientas/medir_presupuesto.py). La herramienta
consulta `/health` antes, cada 5 solicitudes y después, y lee `GET /metricas` antes y después de
la ráfaga cuando la API la publica.

## 4. Ejecución

**Montaje A**, el 11-oct-2026 entre las 21:06 y las 21:08 (−05:00), en la máquina de desarrollo,
con Python 3.12 y las dependencias del lock. En una terminal el proveedor simulado y en otra la API,
del código correspondiente:

```
cd backend
python -m herramientas.proveedor_simulado
LLM_URL_BASE=http://127.0.0.1:8090/v1 LLM_API_KEY=simulada uvicorn api.main:app --port 8000
python -m herramientas.medir_presupuesto --destino local --solicitudes 20 \
    --red "local, proveedor simulado con el límite por minuto de Groq" \
    > ../docs/evidencia/presupuesto-local-antes.json
```

y lo mismo hacia `presupuesto-local-despues.json` sobre el código con ADR-0015. Desde `4db20eb` la
herramienta no escribe archivos: imprime el informe completo en JSON y se guarda con `>`, desde
Git Bash (en PowerShell 5.1 el `>` lo guardaría en UTF-16). Las dos corridas locales se hicieron
con la versión anterior, que lo escribía con `--informe`; el informe tiene el mismo contenido. El
simulador y la API se reiniciaron entre las dos corridas, para que ninguna heredara la ventana de la otra. Una primera
corrida del después se descartó por eso mismo: el simulador de la corrida anterior seguía vivo con
su ventana llena, y las 6 solicitudes que el presupuesto dejó pasar las cortó él. No se usó como
evidencia.

**Montaje B**: la línea base se midió el 11-oct-2026 a las 16:31; el después, con el código
desplegado, el ⟦FECHA Y HORA DE LA CORRIDA DESPLEGADA⟧:

```
cd backend
python -m herramientas.medir_presupuesto --destino desplegada --solicitudes 20 \
    --red "internet residencial, Cartagena" --etiqueta "después: con el presupuesto de ADR-0015" \
    > ../docs/evidencia/presupuesto-despues.json
```

## 5. Resultado

### Montaje A · local, proveedor simulado

| Medida | Umbral | Antes | Después | |
|---|---|---|---|---|
| **M1:** cortadas por el proveedor por cuota | 0 | **11** | **0** | Cumple |
| **M2:** llegaron al proveedor | ≤ 6 | 20 | **6** | Cumple |
| **M3:** p95 de un 429 de la API | ≤ 1 s | no había 429 | **0,005 s** (mediana 0,002 s, 14 muestras) | Cumple |
| **M4:** `/health` | 200 siempre | 200 en 6 de 6 | 200 en 6 de 6 | Cumple |
| Recibieron propuestas | | 9 | 6 | |
| Duración de la ráfaga | | 16,4 s | 10,5 s | |

En orden, los códigos de la ráfaga fueron `200 ×9, 503 ×11` antes y `200 ×6, 429 ×14` después.
Los 429 llegaron con `Retry-After: 50`, que es lo que faltaba para que la primera solicitud saliera
de la ventana de un minuto. `GET /metricas`, leída al terminar, dijo `enviadas_desde_el_arranque: 6`
y `rechazadas_desde_el_arranque: 14`, las mismas cuentas que vio el cliente.

Informes en crudo: [`presupuesto-local-antes.json`](presupuesto-local-antes.json) ·
[`presupuesto-local-despues.json`](presupuesto-local-despues.json).

### Montaje B · entorno desplegado, Groq

| Medida | Umbral | Antes (`7201193`) | Después (ADR-0015) | |
|---|---|---|---|---|
| **M1:** cortadas por el proveedor por cuota | 0 | **8** | **⟦M1⟧** | ⟦CUMPLE M1⟧ |
| **M2:** llegaron al proveedor | ≤ 6 | 20 | **⟦M2⟧** | ⟦CUMPLE M2⟧ |
| **M3:** p95 de un 429 de la API | ≤ 1 s | no había 429 | **⟦M3⟧ s** | ⟦CUMPLE M3⟧ |
| **M4:** `/health` | 200 siempre | 200 en 6 de 6 | ⟦M4⟧ | ⟦CUMPLE M4⟧ |
| Recibieron propuestas | | 12 | ⟦PROPUESTAS⟧ | |
| Duración de la ráfaga | | 22,3 s | ⟦DURACIÓN⟧ s | |

Informes en crudo: [`presupuesto-antes.json`](presupuesto-antes.json) ·
[`presupuesto-despues.json`](presupuesto-despues.json).

## 6. Observabilidad

El escenario se ve desde fuera del código de tres maneras, y las tres se usaron en la medición:

- **El evento `presupuesto_agotado`** en el registro JSON de la API, uno por solicitud cortada. Una
  línea real de la corrida local del después:

      {"momento": "2026-10-12T02:06:44.128+00:00", "nivel": "WARNING", "registro": "api", "mensaje": "Presupuesto agotado", "evento": "presupuesto_agotado", "ventana": "minuto", "reintentar_en_segundos": 50, "usadas_en_el_ultimo_minuto": 6, "usadas_en_las_ultimas_24_horas": 6, "rechazadas_desde_el_arranque": 1}

  La corrida dejó 14 eventos de este tipo, uno por cada 429.
- **El evento `distractores_propuestos`**, que ya existía desde la S9, uno por cada solicitud que
  sí salió al proveedor, con su duración y sus tokens.
- **`GET /metricas`**, que publica el estado del presupuesto sin tocar la red ni el disco:

      {"presupuesto_de_distractores": {"limite_por_minuto": 6, "limite_por_dia": 150, "usadas_en_el_ultimo_minuto": 6, "usadas_en_las_ultimas_24_horas": 6, "enviadas_desde_el_arranque": 6, "rechazadas_desde_el_arranque": 14, "arrancado_en": "2026-10-12T02:06:30.844257Z"}}

En el entorno desplegado, los mismos eventos se buscan en los logs de `quantia-utb-api` en Render
filtrando por `presupuesto_agotado`, y `/metricas` responde en
https://quantia-utb-api.onrender.com/metricas.

## 7. Conclusión

**En el montaje A, la hipótesis se acepta en sus cuatro medidas.** Con el mismo proveedor y la
misma carga, el presupuesto es lo único que cambió, y cambió exactamente lo que predecía: pasó de
20 solicitudes en el proveedor y 11 cortes por cuota a 6 y 0. Los 14 rechazos los dio la API en 2 ms
de mediana, sin salir a la red, con la cabecera que dice cuándo volver.

**En el montaje B,** ⟦CONCLUSIÓN DESPLEGADA⟧

**El costo de la respuesta:** en la ráfaga, el profesor recibe 6 propuestas en vez de 12 (en la
línea base desplegada). Es la consecuencia buscada: las 6 que faltan no las pierde, se las difiere
el `Retry-After` un minuto, y a cambio la cuota del minuto y del día queda para el resto de los
profesores. El límite es conservador a propósito, porque sale del peor caso de tokens medido y no de
lo que Groq tolere un día dado (ADR-0015).

**Qué decisión cambió.** El experimento no invalidó ninguna decisión anterior: ADR-0013 sigue
vigente en sus nueve puntos (el 503 ante una falla del proveedor no cambia). Lo que cambió es la
mitigación de R-17, que ADR-0013 dejaba en «sin tarjeta, el peor caso es agotar la cuota», y que la
línea base mostró insuficiente. Por eso ADR-0015 precisa a ADR-0013 y no lo reemplaza.

## 8. Límites de validez

- **Una ráfaga de un solo cliente.** El presupuesto es global, así que veinte clientes a la vez dan
  el mismo resultado agregado, pero no se midió cómo se reparte entre ellos: no se reparte (R-19).
- **No se midió el límite por día en el entorno desplegado**, porque exige 150 solicitudes y gasta
  un día de cuota. Lo cubren las pruebas con reloj falso (`test_presupuesto.py`).
- **El presupuesto vive en memoria** y se vacía en cada despliegue (R-18). Un reinicio a mitad de
  una ráfaga devolvería el cupo; no se provocó.
- **El simulador del montaje A es más estricto que Groq en ráfaga** (9 frente a 12 en la línea base):
  por eso la cifra de «antes» del montaje A no se compara con la del montaje B, solo con su propio
  después.
- **M3 incluye la red del cliente en el montaje B** y no en el A. El umbral de 1 s deja margen para
  eso: un `/health` desde la misma red tarda entre 0,12 y 0,2 s.

## 9. Cómo repetir

```
# desde Git Bash: la herramienta imprime el informe y `>` lo guarda en UTF-8
cd backend
pip install -r requirements.txt

# montaje A: tres terminales
python -m herramientas.proveedor_simulado
LLM_URL_BASE=http://127.0.0.1:8090/v1 LLM_API_KEY=simulada uvicorn api.main:app --port 8000
python -m herramientas.medir_presupuesto --destino local \
    > ../docs/evidencia/presupuesto-local-despues.json

# montaje B: contra el entorno desplegado (gasta hasta 6 solicitudes de cuota de Groq)
python -m herramientas.medir_presupuesto --destino desplegada \
    > ../docs/evidencia/presupuesto-despues.json
```

Para la corrida de «antes» del montaje A, se hace lo mismo sobre un clon en `4db20eb`, el último
commit sin presupuesto, copiándole `herramientas/proveedor_simulado.py` y guardando en
`presupuesto-local-antes.json`. La corrida guardada se hizo sobre `544a469`, cuya API es la misma:
`4db20eb` solo cambió la herramienta de medición y un comentario. Entre una corrida y otra hay que
detener el simulador y la API: si queda uno vivo, la siguiente corrida hereda su ventana.

Las pruebas que sostienen el mecanismo corren en cada push, en el paso «Escenario del segundo
corte (presupuesto del proveedor de LLM)» del pipeline, y dentro de la suite completa.
