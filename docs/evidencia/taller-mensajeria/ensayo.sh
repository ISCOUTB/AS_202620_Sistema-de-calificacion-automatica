#!/bin/bash
# Ensayo del taller de mensajería (ADR-0020): la API, Redis y el worker de verdad, en local.
#
# Sube un lote de tres hojas por HTTP y provoca, antes de arrancar el worker, los cuatro casos que
# el taller pide ver: un mensaje duplicado, uno que un worker anterior tomó y no confirmó, un fallo
# recuperable (la imagen de la hoja 2 desaparece unos segundos) y uno que no se recupera (la imagen
# de la hoja 3 se borra, como tras un despliegue en Render). Deja en ENSAYO el registro de los dos
# procesos, el estado de la cola en cada paso y el seguimiento de cada mensaje.
#
# Uso, desde backend/, con el entorno del proyecto y Redis en localhost (docker compose up -d redis):
#
#     bash ../docs/evidencia/taller-mensajeria/ensayo.sh
#
# Usa la cola `evidencia`, no la de siempre, y el puerto 8077. Tarda un minuto.
set -u
ENSAYO=${ENSAYO:-$(mktemp -d)}
PY=${PY:-python}
export REDIS_URL=${REDIS_URL:-redis://localhost:6379/0}
export NOMBRE_COLA=evidencia
export RUTA_ALMACEN=$ENSAYO/almacen
export RUTA_BITACORA=$ENSAYO/almacen/bitacora.jsonl
mkdir -p "$RUTA_ALMACEN"
redis-cli -u "$REDIS_URL" del evidencia evidencia:en-curso evidencia:reintentos evidencia:fallidos >/dev/null

$PY -m uvicorn api.main:app --port 8077 2> "$ENSAYO/api.log" >/dev/null &
API=$!
for _ in $(seq 1 30); do curl -s localhost:8077/health >/dev/null && break; sleep 0.3; done

# 1. El lote: tres hojas por HTTP, como las sube el sitio.
$PY - <<'P' > "$ENSAYO/respuesta-de-la-carga.json"
import httpx, json
jpg = b"\xff\xd8\xff" + b"\x00" * 2048
archivos = [("archivos", (f"hoja-{i}.jpg", jpg, "image/jpeg")) for i in (1, 2, 3)]
r = httpx.post("http://localhost:8077/examenes/EVID-1/hojas", files=archivos)
print(json.dumps(r.json(), ensure_ascii=False, indent=2))
P
echo "== 1. Estado tras la carga, sin worker" > "$ENSAYO/pasos.txt"
$PY -m herramientas.cola_de_fallidos --cola evidencia >> "$ENSAYO/pasos.txt" 2>/dev/null

# 2. Duplicado: el mensaje de la hoja 1 se publica otra vez, con el mismo id.
redis-cli -u "$REDIS_URL" rpush evidencia "$(redis-cli -u "$REDIS_URL" lindex evidencia 0)" >/dev/null
# 3. Un worker anterior tomó el mensaje de la hoja 1 y murió sin confirmarlo.
redis-cli -u "$REDIS_URL" blmove evidencia evidencia:en-curso LEFT RIGHT 1 >/dev/null
# 4 y 5. La imagen de la hoja 2 se aparta un momento; la de la hoja 3 se borra.
referencia() { $PY -c "import json,sys;print(json.load(open(sys.argv[1]))['aceptadas'][int(sys.argv[2])]['referencia'])" "$ENSAYO/respuesta-de-la-carga.json" "$1"; }
REF2=$(referencia 1); REF3=$(referencia 2)
mv "$RUTA_ALMACEN/$REF2" "$ENSAYO/hoja2-aparte"
rm "$RUTA_ALMACEN/$REF3"
echo "== 2. Antes de arrancar el worker: duplicado publicado, uno en curso de un worker caído" >> "$ENSAYO/pasos.txt"
$PY -m herramientas.cola_de_fallidos --cola evidencia >> "$ENSAYO/pasos.txt" 2>/dev/null

$PY -m worker.main 2> "$ENSAYO/worker.log" &
WORKER=$!
sleep 7
mv "$ENSAYO/hoja2-aparte" "$RUTA_ALMACEN/$REF2"   # la imagen de la hoja 2 vuelve
sleep 45
kill $WORKER $API; wait 2>/dev/null

echo "== 3. Al final" >> "$ENSAYO/pasos.txt"
$PY -m herramientas.cola_de_fallidos --cola evidencia --ver >> "$ENSAYO/pasos.txt" 2>/dev/null
cat "$ENSAYO/api.log" "$ENSAYO/worker.log" | grep '^{' > "$ENSAYO/registro.jsonl"
$PY -m herramientas.seguir_trabajo - --todos < "$ENSAYO/registro.jsonl" > "$ENSAYO/seguimiento.json"
echo "Resultados en $ENSAYO"
