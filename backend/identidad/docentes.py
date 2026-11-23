"""Quién puede entrar: la lista de docentes que llega por el entorno, y la comprobación de una
contraseña contra ella (ADR-0025).

La lista es `correo=cifrada`, con las entradas separadas por comas o saltos de línea. La genera
`python -m herramientas.crear_docente` y se pega en la variable `DOCENTES` de Dokploy. No hay
pantalla de registro: agregar o quitar un docente es cambiar esa variable y volver a desplegar."""

from identidad.contrasenas import ALGORITMO, cifrar, verificar


class ConfiguracionDeDocentesInvalida(ValueError):
    """La lista de docentes está mal escrita. El mensaje dice qué entrada por su posición, sin el
    correo ni la cifrada: puede terminar en el registro del servidor."""


def normalizar_correo(correo: str) -> str:
    """El correo como se compara: sin espacios alrededor y en minúsculas."""
    return correo.strip().lower()


def leer_docentes(texto: str) -> dict[str, str]:
    """La lista de docentes, de correo (normalizado) a contraseña cifrada.

    Una entrada mal escrita rechaza la lista entera en vez de saltarse: un docente que falta sin
    aviso se ve igual que una contraseña equivocada, y nadie sabría dónde buscar."""
    docentes: dict[str, str] = {}
    entradas = [entrada.strip() for entrada in texto.replace("\n", ",").split(",")]
    for posicion, entrada in enumerate((e for e in entradas if e), start=1):
        correo, signo, cifrada = entrada.partition("=")
        correo = normalizar_correo(correo)
        if not signo or "@" not in correo:
            raise ConfiguracionDeDocentesInvalida(
                f"La entrada {posicion} de DOCENTES no tiene la forma correo=cifrada."
            )
        if not cifrada.strip().startswith(f"{ALGORITMO}:"):
            raise ConfiguracionDeDocentesInvalida(
                f"La contraseña de la entrada {posicion} de DOCENTES no está cifrada: genérala con "
                "`python -m herramientas.crear_docente`."
            )
        if correo in docentes:
            raise ConfiguracionDeDocentesInvalida(
                f"La entrada {posicion} de DOCENTES repite el correo de una entrada anterior."
            )
        docentes[correo] = cifrada.strip()
    return docentes


# Una cifrada cualquiera, para verificar contra algo cuando el correo no está en la lista: así
# un correo que no existe tarda lo mismo que una contraseña equivocada, y el tiempo de respuesta
# no dice quién tiene cuenta. Se calcula la primera vez que hace falta, no al importar.
_RELLENO: list[str] = []


def _cifrada_de_relleno() -> str:
    if not _RELLENO:
        _RELLENO.append(cifrar("relleno-sin-cuenta"))
    return _RELLENO[0]


def autenticar(correo: str, contrasena: str, docentes: dict[str, str]) -> str | None:
    """El correo (normalizado) si está en la lista y la contraseña es la suya; si no, None. No
    distingue entre un correo que no existe y una contraseña equivocada."""
    normalizado = normalizar_correo(correo)
    cifrada = docentes.get(normalizado)
    if cifrada is None:
        verificar(contrasena, _cifrada_de_relleno())
        return None
    return normalizado if verificar(contrasena, cifrada) else None
