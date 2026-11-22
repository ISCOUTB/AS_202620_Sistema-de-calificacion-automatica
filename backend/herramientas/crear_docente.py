"""Arma la línea de un docente para la variable `DOCENTES` de Dokploy (ADR-0025).

    cd backend
    python -m herramientas.crear_docente profe@utb.edu.co

Pide la contraseña dos veces sin mostrarla e imprime `correo=cifrada`. Esa línea es lo único que
va al panel: la contraseña en claro no se guarda en ningún lado. Para varios docentes, las líneas
van separadas por comas en la misma variable. Cambiar la contraseña de alguien es generar su
línea otra vez y reemplazarla."""

import argparse
import getpass
import sys

from identidad import cifrar, normalizar_correo

MINIMO_DE_CARACTERES = 10


def linea_del_docente(correo: str, contrasena: str) -> str:
    """La entrada de un docente en `DOCENTES`. Rechaza un correo que no lo parece, uno con los
    signos que separan la lista, y una contraseña de menos de diez caracteres."""
    normalizado = normalizar_correo(correo)
    if "@" not in normalizado or set(",= \n") & set(normalizado):
        raise ValueError(f"«{correo}» no parece un correo.")
    if len(contrasena) < MINIMO_DE_CARACTERES:
        raise ValueError(f"La contraseña necesita al menos {MINIMO_DE_CARACTERES} caracteres.")
    return f"{normalizado}={cifrar(contrasena)}"


def main(argumentos: list[str] | None = None) -> int:
    lector = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    lector.add_argument("correo", help="El correo con el que el docente va a entrar.")
    correo = lector.parse_args(argumentos).correo

    contrasena = getpass.getpass("Contraseña: ")
    if getpass.getpass("Otra vez: ") != contrasena:
        print("Las contraseñas no coinciden. No se generó nada.", file=sys.stderr)
        return 1
    try:
        print(linea_del_docente(correo, contrasena))
    except ValueError as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
