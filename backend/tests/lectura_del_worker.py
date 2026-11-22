"""Las claves y el registro de resultados del worker, en la carpeta de una prueba.

Las pruebas de mensajería no miran la lectura: guardan bytes que no son una hoja, que el worker
registra como ilegibles y confirma. Les basta con que la fuente de claves y el registro existan y
no escriban fuera de su carpeta temporal."""

from pathlib import Path
from typing import TypedDict

from infraestructura.claves import ClavesEnDisco, FuenteDeClaves
from infraestructura.resultados import RegistroDeResultados, ResultadosEnDisco


class LecturaDelWorker(TypedDict):
    claves: FuenteDeClaves
    resultados: RegistroDeResultados


def lectura_en(raiz: Path) -> LecturaDelWorker:
    return {
        "claves": ClavesEnDisco(raiz / "claves"),
        "resultados": ResultadosEnDisco(raiz / "resultados-de-lectura.jsonl"),
    }
