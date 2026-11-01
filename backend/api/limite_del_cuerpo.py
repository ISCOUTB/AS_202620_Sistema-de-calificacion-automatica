"""Tope del cuerpo de la petición (S13, ADR-0022): ningún cuerpo de más de 100 MB entra a la API.

El presupuesto de carga (`ingesta/presupuesto.py`) decide sobre un lote que ya llegó: antes de
llamar a la ruta, Starlette guardó cada archivo en un temporal del contenedor, que está en el mismo
disco que comparten los equipos del servidor. Cloudflare corta en 100 MB por petición, pero solo lo
que pasa por Cloudflare: la IP del servidor es pública, y Traefik atiende sin tope a quien llegue
directo. Este middleware pone ese mismo tope del lado de la API, para cualquier ruta.

Corta en uno de dos momentos:

1. **Si la petición declara un `Content-Length` mayor que el tope**, responde 413 sin leer el
   cuerpo.
2. **Si no lo declara**, o declara menos de lo que manda, cuenta lo que va llegando y corta al pasar
   el tope. Levanta un `HTTPException`, que FastAPI deja pasar tal cual desde la lectura del cuerpo
   y responde como un 413 más.

Va por dentro de CORS (`api/main.py` lo agrega antes), para que el 413 lleve las cabeceras de CORS
y el sitio pueda leerlo.
"""

from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

__all__ = ["LimiteDelCuerpo", "MB_DEL_CUERPO"]

# El mismo tope que ya pone Cloudflare: por el camino de siempre no cambia nada, y por el directo
# deja de no haber tope. Un lote de un corte (200 hojas de 200 a 400 KB) cabe holgado.
MB_DEL_CUERPO = 100

_UN_MB = 1024 * 1024


class LimiteDelCuerpo:
    """Middleware ASGI que rechaza con 413 todo cuerpo de más de `maximo_bytes`."""

    def __init__(self, app: ASGIApp, maximo_bytes: int = MB_DEL_CUERPO * _UN_MB) -> None:
        self.app = app
        self.maximo_bytes = maximo_bytes
        self.motivo = (
            f"La petición pasa del máximo de {maximo_bytes // _UN_MB or 1} MB. No entró ninguna "
            "hoja: divida el lote en lotes más pequeños."
        )

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        declarado = _content_length(scope)
        if declarado is not None and declarado > self.maximo_bytes:
            await JSONResponse({"detail": self.motivo}, status_code=413)(scope, receive, send)
            return

        recibidos = 0

        async def contar() -> Message:
            nonlocal recibidos
            mensaje = await receive()
            if mensaje["type"] == "http.request":
                recibidos += len(mensaje.get("body", b""))
                if recibidos > self.maximo_bytes:
                    raise HTTPException(status_code=413, detail=self.motivo)
            return mensaje

        await self.app(scope, contar, send)


def _content_length(scope: Scope) -> int | None:
    for nombre, valor in scope.get("headers", []):
        if nombre == b"content-length":
            try:
                return int(valor)
            except ValueError:
                return None
    return None
