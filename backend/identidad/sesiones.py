"""El token de una sesión: quién entró y hasta cuándo, firmado con el secreto del servidor
(ADR-0025).

El token es `v1.<contenido>.<firma>`: el contenido es el correo y el vencimiento en JSON, en base64
para URL, y la firma es HMAC-SHA256 de `v1.<contenido>` con el secreto. Sin el secreto no se puede
fabricar ni cambiar el correo de un token; con él, la API no necesita guardar las sesiones en
ningún lado. La contracara es que un token no se puede revocar antes de vencer: por eso dura poco
y la API además comprueba, en cada petición, que el correo siga en la lista de docentes."""

import base64
import binascii
import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

VERSION = "v1"


@dataclass(frozen=True)
class Sesion:
    """Quién entró y hasta cuándo vale su token."""

    correo: str
    vence: datetime


def _base64(datos: bytes) -> str:
    return base64.urlsafe_b64encode(datos).rstrip(b"=").decode("ascii")


def _desde_base64(texto: str) -> bytes:
    return base64.urlsafe_b64decode(texto + "=" * (-len(texto) % 4))


def _firma(firmado: str, secreto: str) -> str:
    firma = hmac.new(secreto.encode("utf-8"), firmado.encode("ascii"), hashlib.sha256)
    return _base64(firma.digest())


def emitir_sesion(
    correo: str, ahora: datetime, duracion: timedelta, secreto: str
) -> tuple[str, Sesion]:
    """El token de una sesión nueva y lo que dice. Sin secreto no se emite: falla cerrado."""
    if not secreto:
        raise ValueError("Sin secreto no se firma ninguna sesión.")
    # El vencimiento va en segundos enteros: es lo que viaja en el token, y la sesión devuelta
    # tiene que ser igual a la que se lee de él.
    vence = datetime.fromtimestamp(int((ahora + duracion).timestamp()), tz=timezone.utc)
    contenido = _base64(
        json.dumps({"c": correo, "v": int(vence.timestamp())}, separators=(",", ":")).encode()
    )
    firmado = f"{VERSION}.{contenido}"
    return f"{firmado}.{_firma(firmado, secreto)}", Sesion(correo=correo, vence=vence)


def leer_sesion(token: str, ahora: datetime, secreto: str) -> Sesion | None:
    """La sesión que dice el token, o None si no vale: mal formado, firmado con otro secreto,
    alterado o vencido. Nunca dice por qué, ni lanza: para quien llama, todos son «sin sesión»."""
    # Un token legítimo es ASCII. Lo que no lo es llega de alguien que prueba: compararlo haría
    # fallar a `compare_digest` y la API respondería 500 en vez de 401.
    if not secreto or not token.isascii():
        return None
    partes = token.split(".")
    if len(partes) != 3 or partes[0] != VERSION:
        return None
    version, contenido, firma = partes
    if not hmac.compare_digest(firma, _firma(f"{version}.{contenido}", secreto)):
        return None
    try:
        datos = json.loads(_desde_base64(contenido))
        correo = datos["c"]
        vence = datetime.fromtimestamp(int(datos["v"]), tz=timezone.utc)
    except (binascii.Error, ValueError, KeyError, TypeError, OverflowError, OSError):
        return None
    if not isinstance(correo, str) or ahora >= vence:
        return None
    return Sesion(correo=correo, vence=vence)
