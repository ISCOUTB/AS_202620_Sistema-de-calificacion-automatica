"""Las contraseñas de los docentes: se guardan cifradas con scrypt y nunca en claro (ADR-0025).

La cifrada lleva el algoritmo, sus parámetros, la sal y la clave derivada, separados por `:`. No usa
`$` (el formato habitual) porque la lista de docentes vive en una variable de Dokploy, y compose
interpreta `$` en el `.env`: la cifrada llegaría cortada a la API. Tampoco lleva `,` ni `=`, que
separan las entradas de esa lista. Todo es de la biblioteca estándar: no suma dependencias."""

import hashlib
import hmac
import secrets

ALGORITMO = "scrypt"

# Costo de scrypt: con n = 2^14 y r = 8 cada verificación usa 16 MiB y unos 50 ms. Alcanza para que
# probar contraseñas una por una sea lento, y la API (un solo proceso) lo paga solo al entrar.
N = 2**14
R = 8
P = 1
LARGO_DE_LA_SAL = 16
LARGO_DE_LA_CLAVE = 32


def cifrar(contrasena: str, *, sal: bytes | None = None) -> str:
    """La contraseña cifrada, lista para la lista de docentes. Cada llamada usa una sal nueva."""
    sal = secrets.token_bytes(LARGO_DE_LA_SAL) if sal is None else sal
    clave = hashlib.scrypt(
        contrasena.encode("utf-8"), salt=sal, n=N, r=R, p=P, dklen=LARGO_DE_LA_CLAVE
    )
    return f"{ALGORITMO}:{N}:{R}:{P}:{sal.hex()}:{clave.hex()}"


def verificar(contrasena: str, cifrada: str) -> bool:
    """Si la contraseña es la que se cifró. Una cifrada mal escrita no verifica nada y no falla."""
    try:
        algoritmo, n, r, p, sal, clave = cifrada.split(":")
        if algoritmo != ALGORITMO:
            return False
        esperada = bytes.fromhex(clave)
        calculada = hashlib.scrypt(
            contrasena.encode("utf-8"),
            salt=bytes.fromhex(sal),
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(esperada),
        )
    except ValueError:
        return False
    # Comparación en tiempo constante: el tiempo de respuesta no dice cuántos bytes coincidieron.
    return hmac.compare_digest(calculada, esperada)
