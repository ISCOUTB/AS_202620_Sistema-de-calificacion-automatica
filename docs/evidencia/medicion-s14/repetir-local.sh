#!/bin/bash
# Repeticiones de EC-03 y EC-04 de la S14, sin Docker, con los límites de CPU del servidor.
#
# Cada repetición arranca un sistema nuevo y vacío (Redis, la API y el worker, como procesos), le
# pone al worker 0,25 CPU y a la API 0,5 con limitar.py, sube las hojas con
# herramientas.medir_procesamiento y analiza el registro de los dos procesos. Redis va con el tope
# de memoria del servidor (32 MB, noeviction) y sin persistencia.
#
# Cada proceso va fijo a un núcleo (taskset): OpenCV lee con dos hilos, y sin eso los dos correrían a
# la vez en la fracción de tiempo que limitar.py les deja, más CPU de la que da el tope de Docker.
#
# La medición del 6-nov corrió con `docker compose` y los límites de deploy/compose.lab.yaml
# (medicion-lectura-omr.md, sección 3). Esta la repite en una máquina sin Docker.
#
# Uso, desde backend/, con el entorno del proyecto, redis-server, curl y taskset instalados:
#
#     bash ../docs/evidencia/medicion-s14/repetir-local.sh ec03 2026
#     bash ../docs/evidencia/medicion-s14/repetir-local.sh ec04 4
#
# El primer argumento es el escenario y el segundo la semilla de las hojas. Deja todo en SALIDA.
set -u
ESCENARIO=$1; SEMILLA=$2
PY=${PY:-python}
AQUI=$(cd "$(dirname "$0")" && pwd)
SALIDA=${SALIDA:-$(mktemp -d)}
EXAMEN=S14-${ESCENARIO^^}-S$SEMILLA
DATOS=$(mktemp -d)
PUERTO_REDIS=${PUERTO_REDIS:-6390}; PUERTO_API=${PUERTO_API:-8010}
export REDIS_URL=redis://localhost:$PUERTO_REDIS/0
export RUTA_ALMACEN=$DATOS/almacen RUTA_BITACORA=$DATOS/almacen/bitacora.jsonl
export RUTA_CLAVES=$DATOS/claves RUTA_RESULTADOS=$DATOS/resultados/resultados-de-lectura.jsonl
export RUTA_REVISIONES=$DATOS/resultados/revisiones-del-profesor.jsonl
mkdir -p "$RUTA_ALMACEN" "$RUTA_CLAVES" "$DATOS/resultados" "$SALIDA"

redis-server --port "$PUERTO_REDIS" --save "" --appendonly no --maxmemory 32mb \
    --maxmemory-policy noeviction --daemonize yes --logfile "$DATOS/redis.log"
sleep 0.5
taskset -c 0 $PY -m uvicorn api.main:app --port "$PUERTO_API" 2> "$SALIDA/$EXAMEN-api.log" >/dev/null &
API=$!
taskset -c 1 $PY -m worker.main 2> "$SALIDA/$EXAMEN-worker.log" &
WORKER=$!
for _ in $(seq 1 50); do curl -s "localhost:$PUERTO_API/health" >/dev/null && break; sleep 0.2; done
$PY "$AQUI/limitar.py" --muestras "$SALIDA/$EXAMEN-muestras.jsonl" \
    "worker:$WORKER:0.25" "api:$API:0.5" &
LIMITE=$!

# La clave del examen va al volumen antes de subir las hojas, como en la medición del 6-nov.
if [ "$ESCENARIO" = ec03 ]; then
    $PY -m herramientas.medir_procesamiento cargar --url "http://localhost:$PUERTO_API" \
        --examen "$EXAMEN" --hojas 20 --pausa 8 --semilla "$SEMILLA" \
        --clave "$RUTA_CLAVES/$EXAMEN.json" > "$SALIDA/$EXAMEN-carga.jsonl" 2>&1
    ESPERADAS=20
else
    $PY -m herramientas.medir_procesamiento cargar --url "http://localhost:$PUERTO_API" \
        --examen "$EXAMEN" --hojas 200 --semilla "$SEMILLA" \
        --clave "$RUTA_CLAVES/$EXAMEN.json" > "$SALIDA/$EXAMEN-carga.jsonl" 2>&1
    ESPERADAS=200
fi
# Espera a que el worker termine (con un tope de 15 min, más que el umbral de EC-04).
for _ in $(seq 1 900); do
    [ "$(grep -c '"hoja_procesada"' "$SALIDA/$EXAMEN-worker.log")" -ge "$ESPERADAS" ] && break
    sleep 1
done
sleep 3
kill $LIMITE; wait $LIMITE 2>/dev/null
kill $WORKER $API; wait 2>/dev/null
redis-cli -p "$PUERTO_REDIS" shutdown nosave >/dev/null 2>&1
cat "$SALIDA/$EXAMEN-api.log" "$SALIDA/$EXAMEN-worker.log" | grep '{' > "$SALIDA/$EXAMEN-registro.jsonl"
$PY -m herramientas.medir_procesamiento analizar "$SALIDA/$EXAMEN-registro.jsonl" \
    --examen "$EXAMEN" > "$SALIDA/$EXAMEN.json"
rm -rf "$DATOS"
cat "$SALIDA/$EXAMEN.json"
