"""Prueba 5: recepción de hojas (aspecto A-01, RF-01, escenario EC-07).

Corre sin Redis y sin servidor: `ingesta.recibir_lote` recibe bytes y colaboradores, así que se
puede ejercitar entero con un almacén sobre `tmp_path` y una cola de mentira. Es la prueba que
sostiene la parte verificable de EC-07 —**0 % de pérdida silenciosa**— y la que justifica que
la fila A-01 de `docs/aspectos.md` pueda llegar hasta la columna «Pruebas».

Lo que estas pruebas **no** cubren, y conviene tenerlo escrito para no confundir alcance con
evidencia: la durabilidad tras un reinicio y el tiempo de confirmación de ≤10 s. La primera
depende del ADR de persistencia todavía abierto (R-06); el segundo es una medición que no se
ha hecho. Ambas quedan como «Evidencia» pendiente, no como pruebas ausentes por descuido."""

import pytest

from infraestructura.almacen import AlmacenEnDisco
from infraestructura.modelo import ArchivoCargado
from ingesta import recibir_lote

JPG = b"\xff\xd8\xff" + b"\x00" * 32
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
PDF = b"%PDF-1.7\n" + b"\x00" * 32

EXAMEN = "CALC-2026-01"
COLA = "procesamiento"


class ColaFalsa:
    """Sustituto del cliente Redis: guarda lo que se le empuja. Deja pasar el `encolar` real de
    `infraestructura.cola`, así que la serialización del trabajo sí se ejercita; lo único que
    se reemplaza es el servidor."""

    def __init__(self) -> None:
        self.empujados: list[tuple[str, str]] = []

    def rpush(self, cola: str, valor: str) -> int:
        self.empujados.append((cola, valor))
        return len(self.empujados)


@pytest.fixture
def almacen(tmp_path):
    return AlmacenEnDisco(tmp_path)


@pytest.fixture
def cola():
    return ColaFalsa()


def _recibir(archivos, almacen, cola):
    return recibir_lote(EXAMEN, archivos, almacen, cola, COLA)


@pytest.mark.parametrize(
    "nombre, contenido",
    [
        ("hoja.jpg", JPG),
        ("hoja.jpeg", JPG),
        ("hoja.PNG", PNG),
        ("lote.pdf", PDF),
    ],
)
def test_acepta_los_formatos_declarados(nombre, contenido, almacen, cola):
    """RF-01 nombra JPG, PNG y PDF. La extensión se compara en minúsculas porque un escáner
    que entrega `.PNG` no está entregando un formato distinto."""
    resultado = _recibir([ArchivoCargado(nombre, contenido)], almacen, cola)

    assert resultado.rechazados == ()
    assert len(resultado.aceptadas) == 1
    assert resultado.aceptadas[0].nombre_archivo == nombre


@pytest.mark.parametrize(
    "nombre, contenido, fragmento_esperado",
    [
        ("notas.txt", b"texto plano", "Extensión no admitida"),
        ("hoja", JPG, "Extensión no admitida"),
        ("hoja.jpg", b"", "vacío"),
        ("hoja.jpg", b"esto no es un JPG", "no corresponde"),
        ("hoja.pdf", PNG, "no corresponde"),
    ],
)
def test_rechaza_con_motivo_legible(nombre, contenido, fragmento_esperado, almacen, cola):
    """Un rechazo sin motivo es indistinguible de una pérdida desde el lado del docente, así
    que el motivo es parte de lo que se verifica, no solo el hecho del rechazo.

    Los dos últimos casos son los que justifican revisar los primeros bytes y no solo la
    extensión: renombrar un archivo es trivial, y si el engaño pasa aquí el error reaparece
    dentro del worker, cuando ya no hay a quién avisarle."""
    resultado = _recibir([ArchivoCargado(nombre, contenido)], almacen, cola)

    assert resultado.aceptadas == ()
    assert len(resultado.rechazados) == 1
    assert fragmento_esperado in resultado.rechazados[0].motivo
    assert resultado.rechazados[0].nombre_archivo == nombre


def test_ningun_archivo_del_lote_desaparece(almacen, cola):
    """La medida de EC-07: todo archivo cargado sale como aceptado o como rechazado con motivo.
    Es el invariante del aspecto, y por eso se verifica sobre el conteo completo y no sobre los
    aceptados."""
    archivos = [
        ArchivoCargado("h1.jpg", JPG),
        ArchivoCargado("h2.png", PNG),
        ArchivoCargado("apuntes.txt", b"texto"),
        ArchivoCargado("h3.pdf", PDF),
        ArchivoCargado("h4.jpg", b""),
    ]

    resultado = _recibir(archivos, almacen, cola)

    assert resultado.total_procesados == len(archivos)
    nombres_reportados = {h.nombre_archivo for h in resultado.aceptadas} | {
        r.nombre_archivo for r in resultado.rechazados
    }
    assert nombres_reportados == {a.nombre for a in archivos}


def test_un_archivo_invalido_no_tumba_el_lote(almacen, cola):
    """Doscientas hojas y una corrupta no pueden costar volver a subir las otras ciento noventa
    y nueve."""
    archivos = [
        ArchivoCargado("mala.txt", b"x"),
        ArchivoCargado("buena1.jpg", JPG),
        ArchivoCargado("buena2.png", PNG),
    ]

    resultado = _recibir(archivos, almacen, cola)

    assert len(resultado.aceptadas) == 2
    assert len(resultado.rechazados) == 1


def test_encola_un_trabajo_por_hoja_aceptada_y_ninguno_por_rechazada(almacen, cola):
    """El número de trabajos encolados es lo que el worker va a procesar. Si no coincide con el
    de hojas aceptadas, o el docente ve confirmada una hoja que nadie califica, o se califica
    dos veces la misma."""
    archivos = [
        ArchivoCargado("h1.jpg", JPG),
        ArchivoCargado("h2.png", PNG),
        ArchivoCargado("mala.doc", b"x"),
    ]

    resultado = _recibir(archivos, almacen, cola)

    assert len(cola.empujados) == len(resultado.aceptadas) == 2
    assert {nombre_cola for nombre_cola, _ in cola.empujados} == {COLA}
    # Identificadores distintos: dos hojas no pueden compartir trabajo.
    assert len({h.trabajo_id for h in resultado.aceptadas}) == 2


def test_la_hoja_queda_almacenada_con_su_contenido_intacto(tmp_path, cola):
    """Primero se almacena y después se encola: al revés, el worker podría recibir un trabajo
    que apunta a una imagen que todavía no existe. Aquí se comprueba el resultado de ese orden,
    leyendo del disco lo que la referencia dice."""
    almacen = AlmacenEnDisco(tmp_path)

    resultado = _recibir([ArchivoCargado("hoja 3.jpg", JPG)], almacen, cola)

    referencia = resultado.aceptadas[0].referencia
    assert (tmp_path / referencia).read_bytes() == JPG


def test_un_nombre_con_rutas_no_escapa_del_directorio_del_examen(tmp_path, cola):
    """El nombre del archivo lo controla quien sube, no el sistema. Se verifica que la
    referencia quede dentro del directorio del examen y que el nombre original se conserve en
    el reporte, que es lo que el docente necesita reconocer.

    Al provocar la falla se descubrió algo que conviene dejar escrito: `nombre_seguro` tiene
    dos defensas —quedarse con el último segmento de la ruta y sustituir los caracteres fuera
    de la lista blanca— y **cada una basta por separado**, así que esta prueba solo se pone en
    rojo si se quitan las dos. Verifica la propiedad (la referencia no sale del directorio del
    examen), no el mecanismo, que es como debe ser; pero nadie debería borrar una de las dos
    líneas creyendo que esta prueba lo detectaría."""
    almacen = AlmacenEnDisco(tmp_path)
    nombre_hostil = "../../../etc/passwd.png"

    resultado = _recibir([ArchivoCargado(nombre_hostil, PNG)], almacen, cola)

    hoja = resultado.aceptadas[0]
    destino = (tmp_path / hoja.referencia).resolve()
    assert destino.is_relative_to((tmp_path / EXAMEN).resolve())
    assert hoja.nombre_archivo == nombre_hostil
