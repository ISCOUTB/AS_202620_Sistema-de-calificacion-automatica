"""Proveedor de LLM simulado, con el límite por minuto que publica Groq, para medir EC-09 en local.

El experimento del segundo corte (`docs/evidencia/experimento-presupuesto.md`) mide qué pasa
cuando una ráfaga golpea `POST /distractores`. Contra Groq de verdad, cada corrida gasta la cuota
del equipo y el resultado depende de lo que otros hayan gastado ese minuto. Este servidor responde
como el endpoint `/chat/completions` de Groq y aplica su límite publicado de **8 000 tokens por
minuto**, de modo que la corrida local aísla una sola variable: el presupuesto de la API.

Qué imita y qué no
------------------
- Imita la forma de la respuesta (`choices[0].message.content` con un JSON de distractores, y
  `usage`) y el **429** que Groq devuelve cuando se pasa del límite por minuto.
- Cada solicitud gasta lo que gastó en promedio la corrida oficial de EC-08: 243 tokens de entrada
  y 613 de salida (856). La ventana es deslizante, de 60 s.
- Tarda `--demora` segundos en responder (1,7 por omisión, la mediana medida en el entorno
  desplegado en `presupuesto-antes.json`).
- No imita el límite por día, ni la variación de tokens entre preguntas, ni que Groq pueda dejar
  pasar algo más que su límite nominal en una ráfaga: en la línea base desplegada pasaron 12, y
  aquí pasan 9. Por eso la corrida local no reemplaza a la desplegada; la complementa.

Escucha solo en `127.0.0.1:8090`, sin cifrar porque no sale de esta máquina. Ningún argumento
decide la dirección, como en las otras herramientas.

Por qué HTTP y no HTTPS
-----------------------
SonarCloud marca `serve_forever()` porque el servidor habla HTTP sin cifrar. Aquí no aplica:
la dirección está fija en la interfaz de loopback, así que ningún byte cruza la red y no hay a
quién cifrarle el tráfico. Pasarlo a HTTPS exigiría un certificado autofirmado y que la API
desactivara la verificación TLS para aceptarlo, que sí sería un problema de seguridad y que
SonarCloud también marca. Por eso el aviso se suprime en esa línea con su motivo, como el de
`medir_ec07.py` (AE-12), y `_verificar_que_es_local` impide que alguien cambie `DIRECCION` sin
darse cuenta de lo que implica.

Uso, desde backend/, en una terminal:

    python -m herramientas.proveedor_simulado

y la API, en otra, apuntando a él:

    LLM_URL_BASE=http://127.0.0.1:8090/v1 LLM_API_KEY=simulada uvicorn api.main:app --port 8000
"""

import argparse
import http.server
import json
import sys
import threading
import time
from collections import deque
from typing import Any

DIRECCION = ("127.0.0.1", 8090)
TOKENS_POR_MINUTO = 8000
TOKENS_ENTRADA = 243
TOKENS_SALIDA = 613

_CONTENIDO = json.dumps(
    {
        "distractores": [
            {"expresion": "x", "error": "Se bajó el exponente sin multiplicar"},
            {"expresion": "2", "error": "Se derivó como si fuera lineal"},
            {"expresion": "0", "error": "Se derivó como si fuera constante"},
        ]
    },
    ensure_ascii=False,
)


class _Cuota:
    """Ventana deslizante de 60 s sobre los tokens gastados, compartida por todos los hilos."""

    def __init__(self) -> None:
        self._candado = threading.Lock()
        self._gastado: deque[tuple[float, int]] = deque()
        self.respondidas = 0
        self.cortadas = 0

    def cabe(self, tokens: int) -> bool:
        with self._candado:
            ahora = time.monotonic()
            while self._gastado and ahora - self._gastado[0][0] >= 60:
                self._gastado.popleft()
            if sum(t for _, t in self._gastado) + tokens > TOKENS_POR_MINUTO:
                self.cortadas += 1
                return False
            self._gastado.append((ahora, tokens))
            self.respondidas += 1
            return True


def _manejador(cuota: _Cuota, demora: float) -> type[http.server.BaseHTTPRequestHandler]:
    class Manejador(http.server.BaseHTTPRequestHandler):
        def _responder(self, codigo: int, cuerpo: dict[str, Any]) -> None:
            datos = json.dumps(cuerpo).encode("utf-8")
            self.send_response(codigo)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(datos)))
            self.end_headers()
            self.wfile.write(datos)

        def do_POST(self) -> None:  # noqa: N802 (nombre que exige http.server)
            self.rfile.read(int(self.headers.get("Content-Length", 0)))
            if not self.path.endswith("/chat/completions"):
                self._responder(404, {"error": {"message": "ruta desconocida"}})
                return
            if not cuota.cabe(TOKENS_ENTRADA + TOKENS_SALIDA):
                self._responder(429, {"error": {"message": "Rate limit reached: tokens per minute",
                                                "type": "tokens", "code": "rate_limit_exceeded"}})
                return
            time.sleep(demora)
            self._responder(200, {
                "choices": [{"message": {"role": "assistant", "content": _CONTENIDO}}],
                "usage": {"prompt_tokens": TOKENS_ENTRADA, "completion_tokens": TOKENS_SALIDA},
            })

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
            pass

    return Manejador


def _verificar_que_es_local(direccion: tuple[str, int]) -> None:
    """Falla si la dirección no es la de loopback: lo que justifica servir HTTP sin cifrar es que
    nada salga de esta máquina, y eso tiene que seguir siendo cierto aunque alguien edite la
    constante."""
    if direccion[0] != "127.0.0.1":
        raise SystemExit(
            f"El proveedor simulado solo puede escuchar en 127.0.0.1, no en {direccion[0]}: "
            "sirve HTTP sin cifrar."
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Proveedor de LLM simulado con el límite por minuto de Groq (EC-09).")
    parser.add_argument("--demora", type=float, default=1.7,
                        help="segundos que tarda cada respuesta admitida")
    args = parser.parse_args(argv)

    _verificar_que_es_local(DIRECCION)
    cuota = _Cuota()
    servidor = http.server.ThreadingHTTPServer(DIRECCION, _manejador(cuota, args.demora))
    servidor.daemon_threads = True
    print(f"Proveedor simulado en http://{DIRECCION[0]}:{DIRECCION[1]}/v1 "
          f"({TOKENS_POR_MINUTO} tokens por minuto, "
          f"{TOKENS_ENTRADA + TOKENS_SALIDA} por solicitud)",
          file=sys.stderr, flush=True)
    try:
        # Solo loopback: ver «Por qué HTTP y no HTTPS» en el docstring.
        servidor.serve_forever()  # NOSONAR
    except KeyboardInterrupt:
        pass
    finally:
        servidor.server_close()
        print(f"Respondidas: {cuota.respondidas} · cortadas con 429: {cuota.cortadas}",
              file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
