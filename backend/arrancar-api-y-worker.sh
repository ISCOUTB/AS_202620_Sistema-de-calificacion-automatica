#!/bin/sh
# Arranca la API y el worker en la misma instancia: es el comando del servicio de Render
# (render.yaml). En el entorno local no se usa: docker-compose.yml los levanta como dos servicios.
#
# Va en un archivo y no escrito dentro de render.yaml porque Render no interpreta las comillas de
# `dockerCommand`: le entregó a `sh -c` el comando entero como una sola palabra y el arranque falló
# con «not found».
#
# El ciclo vuelve a levantar el worker si termina, que es lo que hace `restart: unless-stopped` en
# el compose. `exec` deja a uvicorn como proceso principal: si la API cae, cae la instancia y
# Render la reinicia. PORT lo fija Render (10000 por omisión).

(while true; do python -m worker.main; sleep 5; done) &
exec uvicorn api.main:app --host 0.0.0.0 --port "${PORT:-8000}"
