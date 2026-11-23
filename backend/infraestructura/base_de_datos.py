"""Los registros en Postgres: los mismos puertos, otro adaptador (ADR-0027, cierra R-06).

**Qué cambia y qué no.** La bitácora de recepción, el registro de resultados y el de revisiones
siguen siendo de solo agregado, con un único escritor cada uno (ADR-0006, ADR-0018 y ADR-0023,
punto 9). Antes cada hecho era una línea de un archivo `.jsonl`; aquí es una fila. Los puertos
(`BitacoraDeRecepcion`, `LectorDeRecepciones`, `RegistroDeResultados`, `LectorDeResultados`,
`RegistroDeRevisiones` y `LectorDeRevisiones`) no cambian, así que `ingesta`, `dashboard`,
`calificacion`, la API y el worker tampoco: quien arma las dependencias elige este adaptador
cuando existe `DATABASE_URL`, y el de disco cuando no.

**Cada fila guarda el hecho completo** en una columna `jsonb`, el mismo documento que escribe el
adaptador de disco (`hecho_de_lectura`, `hecho_ilegible`, `hecho_de_resoluciones`). Las columnas
sueltas (`examen_id`, `hoja_id`, `estado`, `nota_en_decimas`...) son las que se consultan y se
indexan. Así los dos adaptadores devuelven exactamente lo mismo, y las pruebas de los puertos
valen para los dos.

**Lo que siguen siendo archivos.** Las imágenes de las hojas y sus recortes (el almacén) y las
claves de respuestas, que registra la aplicación (ADR-0026).

**Conexiones reusadas, sin biblioteca de pool.** Cada proceso guarda hasta cuatro conexiones
libres por base y las presta, una por operación, con su transacción. Cada una se prueba antes de
prestarla, por si la base se reinició. Sin sentencias preparadas (`prepare_threshold=None`), para
que funcione también detrás de un pooler en modo transacción, como el de Supabase.

**Un fallo de conexión sube como `ConnectionError`**, que es un `OSError`: el worker ya trata el
`OSError` del registro como transitorio y reintenta el trabajo (ADR-0020), igual que con el disco.
"""

from __future__ import annotations

import queue
import threading
from collections.abc import Iterable, Iterator, Mapping
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from infraestructura.bitacora import RecepcionDeHoja
from infraestructura.examenes import DIGITOS_DEL_IDENTIFICADOR
from infraestructura.modelo import (
    CalificacionDeHoja,
    DistractorGuardado,
    DistractoresGuardados,
    EntradaDeBitacora,
    Examen,
    LecturaDeHoja,
    PreguntaDelDocente,
    ResolucionDelProfesor,
)
from infraestructura.resultados import hecho_de_lectura, hecho_ilegible
from infraestructura.revisiones import hecho_de_resoluciones, resolucion_desde

__all__ = [
    "ESQUEMA",
    "crear_esquema",
    "BitacoraEnPostgres",
    "ResultadosEnPostgres",
    "RevisionesEnPostgres",
    "ExamenesEnPostgres",
    "DistractoresEnPostgres",
    "PreguntasEnPostgres",
]

# El esquema completo. Es idempotente: cada proceso lo aplica la primera vez que abre la base, así
# que no hace falta un paso de migración aparte para levantar el sistema.
ESQUEMA = """
CREATE TABLE IF NOT EXISTS bitacora_de_recepcion (
    id              BIGSERIAL PRIMARY KEY,
    hecho           TEXT        NOT NULL CHECK (hecho IN ('recibida', 'encolada')),
    trabajo_id      TEXT        NOT NULL,
    hoja_id         TEXT,
    examen_id       TEXT,
    referencia      TEXT,
    nombre_archivo  TEXT,
    momento         TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS bitacora_por_examen ON bitacora_de_recepcion (examen_id);
CREATE INDEX IF NOT EXISTS bitacora_por_trabajo ON bitacora_de_recepcion (trabajo_id);

CREATE TABLE IF NOT EXISTS resultados_de_lectura (
    id               BIGSERIAL PRIMARY KEY,
    hecho            TEXT        NOT NULL CHECK (hecho IN ('leida', 'ilegible')),
    hoja_id          TEXT        NOT NULL,
    trabajo_id       TEXT        NOT NULL,
    examen_id        TEXT        NOT NULL,
    estado           TEXT        NOT NULL,
    nota_en_decimas  INTEGER,
    provisional      BOOLEAN,
    documento        JSONB       NOT NULL,
    momento          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS resultados_por_examen ON resultados_de_lectura (examen_id, id);

CREATE TABLE IF NOT EXISTS revisiones_del_profesor (
    id          BIGSERIAL PRIMARY KEY,
    hoja_id     TEXT        NOT NULL,
    examen_id   TEXT        NOT NULL,
    documento   JSONB       NOT NULL,
    momento     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS revisiones_por_examen ON revisiones_del_profesor (examen_id, id);

-- ADR-0028: cada examen con su dueño. El identificador lo acuña la secuencia (000001, 000002...);
-- los exámenes anteriores conservan el suyo. Un docente no repite nombre; dos docentes sí.
CREATE SEQUENCE IF NOT EXISTS examenes_numero;
CREATE TABLE IF NOT EXISTS examenes (
    examen_id         TEXT        PRIMARY KEY,
    nombre            TEXT        NOT NULL,
    clave_del_nombre  TEXT        NOT NULL,
    docente           TEXT        NOT NULL,
    creado_en         TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (docente, clave_del_nombre)
);
CREATE INDEX IF NOT EXISTS examenes_por_docente ON examenes (docente, examen_id);

-- ADR-0029: los distractores que cada docente aprobó, uno por docente y pregunta. Guardar otra
-- vez para la misma pregunta reemplaza la fila.
CREATE TABLE IF NOT EXISTS distractores_guardados (
    docente            TEXT        NOT NULL,
    llave              TEXT        NOT NULL,
    enunciado          TEXT        NOT NULL,
    respuesta_correcta TEXT        NOT NULL,
    distractores       JSONB       NOT NULL,
    guardado_en        TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (docente, llave)
);

-- ADR-0030: las preguntas que cada docente agrega en Pauta, el comienzo del banco (RF-06). Una por
-- docente y pregunta: agregarla otra vez no cambia la fila.
CREATE TABLE IF NOT EXISTS preguntas_del_docente (
    docente            TEXT        NOT NULL,
    llave              TEXT        NOT NULL,
    enunciado          TEXT        NOT NULL,
    respuesta_correcta TEXT        NOT NULL,
    agregada_en        TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (docente, llave)
);
"""

_esquemas_aplicados: set[str] = set()
_candado = threading.Lock()


# Conexiones abiertas y libres, por base. Abrir una conexión cuesta más que el INSERT que la usa:
# con una por operación, un lote de 200 hojas tardó 8,8 s en confirmarse con la API en media CPU,
# y pasó el plazo de 8 s de la recepción (55 hojas quedaron pendientes de encolar).
_CONEXIONES_LIBRES_POR_BASE = 4
_libres: dict[str, queue.LifoQueue[psycopg.Connection]] = {}


def _abrir(url: str) -> psycopg.Connection:
    return psycopg.connect(url, connect_timeout=5, prepare_threshold=None, autocommit=True)


def _tomar(url: str) -> psycopg.Connection:
    """Una conexión libre que todavía responde, o una nueva. Una guardada puede haber muerto si la
    base se reinició: se prueba con un `SELECT 1` y, si falla, se descarta."""
    libres = _libres.setdefault(url, queue.LifoQueue(maxsize=_CONEXIONES_LIBRES_POR_BASE))
    while True:
        try:
            conexion = libres.get_nowait()
        except queue.Empty:
            return _abrir(url)
        try:
            conexion.execute("SELECT 1")
            return conexion
        except psycopg.Error:
            conexion.close()


def _devolver(url: str, conexion: psycopg.Connection) -> None:
    if conexion.closed or conexion.broken:
        return
    try:
        _libres[url].put_nowait(conexion)
    except queue.Full:
        conexion.close()


@contextmanager
def _conexion(url: str) -> Iterator[psycopg.Connection]:
    """Una conexión con su transacción: confirma al salir y deshace si algo falla. Un fallo de
    red o de la base sube como `ConnectionError` (ver el docstring del módulo)."""
    try:
        conexion = _tomar(url)
    except psycopg.OperationalError as error:
        raise ConnectionError(f"Postgres no disponible: {error}") from error
    try:
        with conexion.transaction():
            yield conexion
    except psycopg.OperationalError as error:
        conexion.close()
        raise ConnectionError(f"Postgres no disponible: {error}") from error
    finally:
        _devolver(url, conexion)


def crear_esquema(url: str) -> None:
    """Aplica `ESQUEMA`. Se puede llamar las veces que sea."""
    with _conexion(url) as conexion:
        conexion.execute(ESQUEMA)


def _con_esquema(url: str) -> str:
    """Aplica el esquema una sola vez por proceso y por base."""
    if url not in _esquemas_aplicados:
        with _candado:
            if url not in _esquemas_aplicados:
                crear_esquema(url)
                _esquemas_aplicados.add(url)
    return url


def _iso(valor: datetime | None) -> str | None:
    return None if valor is None else valor.astimezone(timezone.utc).isoformat()


class BitacoraEnPostgres:
    """`BitacoraDeRecepcion` y `LectorDeRecepciones` sobre la tabla `bitacora_de_recepcion`.

    Como en disco, cada fila es un hecho: `recibida` cuando la hoja quedó almacenada y `encolada`
    cuando su trabajo llegó a la cola. La durabilidad que en disco daba el `fsync` aquí la da el
    `COMMIT` antes de devolver el control."""

    def __init__(self, url: str) -> None:
        self.url = url

    def registrar(self, entrada: EntradaDeBitacora) -> None:
        with _conexion(_con_esquema(self.url)) as conexion:
            conexion.execute(
                "INSERT INTO bitacora_de_recepcion"
                " (hecho, trabajo_id, hoja_id, examen_id, referencia, nombre_archivo)"
                " VALUES ('recibida', %s, %s, %s, %s, %s)",
                (
                    entrada.trabajo_id,
                    entrada.hoja_id,
                    entrada.examen_id,
                    entrada.referencia,
                    entrada.nombre_archivo,
                ),
            )

    def confirmar_encolada(self, trabajo_id: str) -> None:
        with _conexion(_con_esquema(self.url)) as conexion:
            conexion.execute(
                "INSERT INTO bitacora_de_recepcion (hecho, trabajo_id) VALUES ('encolada', %s)",
                (trabajo_id,),
            )

    def pendientes(self) -> list[EntradaDeBitacora]:
        """Las recibidas sin una `encolada` con su mismo trabajo, en el orden en que llegaron."""
        with _conexion(_con_esquema(self.url)) as conexion:
            filas = conexion.execute(
                "SELECT DISTINCT ON (r.trabajo_id)"
                "       r.trabajo_id, r.examen_id, r.referencia, r.nombre_archivo, r.hoja_id, r.id"
                "  FROM bitacora_de_recepcion r"
                " WHERE r.hecho = 'recibida'"
                "   AND NOT EXISTS (SELECT 1 FROM bitacora_de_recepcion e"
                "                    WHERE e.hecho = 'encolada' AND e.trabajo_id = r.trabajo_id)"
                " ORDER BY r.trabajo_id, r.id DESC"
            ).fetchall()
        filas.sort(key=lambda fila: fila[5])
        return [
            EntradaDeBitacora(
                trabajo_id=trabajo_id,
                examen_id=examen_id,
                referencia=referencia,
                nombre_archivo=nombre_archivo,
                hoja_id=hoja_id or trabajo_id,
            )
            for trabajo_id, examen_id, referencia, nombre_archivo, hoja_id, _ in filas
        ]

    def examenes_mencionados(self) -> set[str]:
        """Cada `examen_id` que aparece en la bitácora: lo usa la adopción de los exámenes
        anteriores a ADR-0028."""
        with _conexion(_con_esquema(self.url)) as conexion:
            filas = conexion.execute(
                "SELECT DISTINCT examen_id FROM bitacora_de_recepcion WHERE examen_id IS NOT NULL"
            ).fetchall()
        return {examen_id for (examen_id,) in filas}

    def recepciones_del_examen(self, examen_id: str) -> dict[str, RecepcionDeHoja]:
        """La primera `recibida` de cada hoja del examen: es cuando llegó."""
        with _conexion(_con_esquema(self.url)) as conexion:
            filas = conexion.execute(
                "SELECT COALESCE(hoja_id, trabajo_id), nombre_archivo, momento"
                "  FROM bitacora_de_recepcion"
                " WHERE hecho = 'recibida' AND examen_id = %s"
                " ORDER BY id",
                (examen_id,),
            ).fetchall()
        recepciones: dict[str, RecepcionDeHoja] = {}
        for hoja_id, nombre_archivo, momento in filas:
            if hoja_id not in recepciones:
                recepciones[hoja_id] = RecepcionDeHoja(nombre_archivo or "", momento)
        return recepciones


class ResultadosEnPostgres:
    """`RegistroDeResultados` y `LectorDeResultados` sobre la tabla `resultados_de_lectura`.

    Solo el worker escribe y la API lee, como con el archivo. La nota vigente de una hoja sigue
    siendo la de su último hecho."""

    def __init__(self, url: str) -> None:
        self.url = url

    def registrar_lectura(
        self,
        hoja_id: str,
        trabajo_id: str,
        examen_id: str,
        lectura: LecturaDeHoja,
        calificacion: CalificacionDeHoja | None,
        motivo_sin_nota: str | None = None,
        recortes: Mapping[int, str] | None = None,
    ) -> None:
        hecho = hecho_de_lectura(
            hoja_id, trabajo_id, examen_id, lectura, calificacion, motivo_sin_nota, recortes
        )
        self._agregar(
            hecho,
            None if calificacion is None else calificacion.nota_en_decimas,
            None if calificacion is None else calificacion.provisional,
        )

    def registrar_lectura_imposible(
        self, hoja_id: str, trabajo_id: str, examen_id: str, motivo: str
    ) -> None:
        self._agregar(hecho_ilegible(hoja_id, trabajo_id, examen_id, motivo), None, None)

    def hechos_del_examen(self, examen_id: str) -> list[dict[str, Any]]:
        with _conexion(_con_esquema(self.url)) as conexion:
            filas = conexion.execute(
                "SELECT documento FROM resultados_de_lectura WHERE examen_id = %s ORDER BY id",
                (examen_id,),
            ).fetchall()
        return [documento for (documento,) in filas]

    def _agregar(
        self, hecho: dict[str, Any], nota_en_decimas: int | None, provisional: bool | None
    ) -> None:
        with _conexion(_con_esquema(self.url)) as conexion:
            conexion.execute(
                "INSERT INTO resultados_de_lectura"
                " (hecho, hoja_id, trabajo_id, examen_id, estado, nota_en_decimas, provisional,"
                "  documento)"
                " VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    hecho["hecho"],
                    hecho["hoja_id"],
                    hecho["trabajo_id"],
                    hecho["examen_id"],
                    hecho["estado"],
                    nota_en_decimas,
                    provisional,
                    Jsonb(hecho),
                ),
            )


class RevisionesEnPostgres:
    """`RegistroDeRevisiones` y `LectorDeRevisiones` sobre la tabla `revisiones_del_profesor`.
    Solo la API escribe; cambiar de opinión es otra fila, y la última manda."""

    def __init__(self, url: str) -> None:
        self.url = url

    def registrar_resoluciones(
        self, hoja_id: str, examen_id: str, resoluciones: Iterable[ResolucionDelProfesor]
    ) -> None:
        hecho = hecho_de_resoluciones(hoja_id, examen_id, resoluciones)
        with _conexion(_con_esquema(self.url)) as conexion:
            conexion.execute(
                "INSERT INTO revisiones_del_profesor (hoja_id, examen_id, documento)"
                " VALUES (%s, %s, %s)",
                (hoja_id, examen_id, Jsonb(hecho)),
            )

    def resoluciones_del_examen(
        self, examen_id: str
    ) -> dict[str, tuple[ResolucionDelProfesor, ...]]:
        with _conexion(_con_esquema(self.url)) as conexion:
            filas = conexion.execute(
                "SELECT hoja_id, documento FROM revisiones_del_profesor"
                " WHERE examen_id = %s ORDER BY id",
                (examen_id,),
            ).fetchall()
        por_hoja: dict[str, list[ResolucionDelProfesor]] = {}
        for hoja_id, documento in filas:
            por_hoja.setdefault(hoja_id, []).extend(
                resolucion_desde(datos) for datos in documento["resoluciones"]
            )
        return {hoja_id: tuple(lista) for hoja_id, lista in por_hoja.items()}


class ExamenesEnPostgres:
    """`RegistroDeExamenes` sobre la tabla `examenes` (ADR-0028). Solo la API escribe.

    La unicidad del nombre por docente la garantiza la restricción `UNIQUE`, no una consulta previa:
    dos pestañas que crean a la vez el mismo examen terminan con uno solo."""

    def __init__(self, url: str) -> None:
        self.url = url

    def crear(
        self, nombre: str, clave_del_nombre: str, docente: str, en: datetime
    ) -> tuple[Examen, bool]:
        with _conexion(_con_esquema(self.url)) as conexion:
            existente = self._del_docente_con_clave(conexion, docente, clave_del_nombre)
            if existente is not None:
                return existente, False
            # Un examen adoptado podría llevar ya un identificador numérico: se salta.
            while True:
                siguiente = conexion.execute("SELECT nextval('examenes_numero')").fetchone()
                assert siguiente is not None  # nextval siempre devuelve una fila
                (numero,) = siguiente
                examen_id = f"{numero:0{DIGITOS_DEL_IDENTIFICADOR}d}"
                fila = conexion.execute(
                    "INSERT INTO examenes (examen_id, nombre, clave_del_nombre, docente, creado_en)"
                    " VALUES (%s, %s, %s, %s, %s)"
                    " ON CONFLICT DO NOTHING"
                    " RETURNING examen_id, nombre, docente, creado_en",
                    (examen_id, nombre, clave_del_nombre, docente, en),
                ).fetchone()
                if fila is not None:
                    return Examen(*fila), True
                # El conflicto pudo ser el nombre (otra petición lo creó a la vez) o el número.
                existente = self._del_docente_con_clave(conexion, docente, clave_del_nombre)
                if existente is not None:
                    return existente, False

    def examen(self, examen_id: str) -> Examen | None:
        with _conexion(_con_esquema(self.url)) as conexion:
            fila = conexion.execute(
                "SELECT examen_id, nombre, docente, creado_en FROM examenes WHERE examen_id = %s",
                (examen_id,),
            ).fetchone()
        return None if fila is None else Examen(*fila)

    def examenes_del_docente(self, docente: str) -> tuple[Examen, ...]:
        with _conexion(_con_esquema(self.url)) as conexion:
            filas = conexion.execute(
                "SELECT examen_id, nombre, docente, creado_en FROM examenes"
                " WHERE docente = %s ORDER BY examen_id",
                (docente,),
            ).fetchall()
        return tuple(Examen(*fila) for fila in filas)

    def adoptar(self, examen_id: str, docente: str, en: datetime) -> bool:
        with _conexion(_con_esquema(self.url)) as conexion:
            clave = examen_id.casefold()
            if self._del_docente_con_clave(conexion, docente, clave) is not None:
                clave = f"{clave}#{examen_id}"
            fila = conexion.execute(
                "INSERT INTO examenes (examen_id, nombre, clave_del_nombre, docente, creado_en)"
                " VALUES (%s, %s, %s, %s, %s) ON CONFLICT DO NOTHING RETURNING examen_id",
                (examen_id, examen_id, clave, docente, en),
            ).fetchone()
        return fila is not None

    @staticmethod
    def _del_docente_con_clave(
        conexion: psycopg.Connection, docente: str, clave_del_nombre: str
    ) -> Examen | None:
        fila = conexion.execute(
            "SELECT examen_id, nombre, docente, creado_en FROM examenes"
            " WHERE docente = %s AND clave_del_nombre = %s",
            (docente, clave_del_nombre),
        ).fetchone()
        return None if fila is None else Examen(*fila)


class DistractoresEnPostgres:
    """`RegistroDeDistractores` sobre la tabla `distractores_guardados` (ADR-0029). Solo la API
    escribe. Guardar es un `INSERT ... ON CONFLICT DO UPDATE`: dos pestañas que guardan a la vez
    dejan una sola fila, la última."""

    def __init__(self, url: str) -> None:
        self.url = url

    def guardar(self, llave: str, guardados: DistractoresGuardados) -> None:
        distractores = [
            {"expresion": d.expresion, "error": d.error} for d in guardados.distractores
        ]
        with _conexion(_con_esquema(self.url)) as conexion:
            conexion.execute(
                "INSERT INTO distractores_guardados"
                " (docente, llave, enunciado, respuesta_correcta, distractores, guardado_en)"
                " VALUES (%s, %s, %s, %s, %s, %s)"
                " ON CONFLICT (docente, llave) DO UPDATE SET"
                " enunciado = EXCLUDED.enunciado,"
                " respuesta_correcta = EXCLUDED.respuesta_correcta,"
                " distractores = EXCLUDED.distractores,"
                " guardado_en = EXCLUDED.guardado_en",
                (
                    guardados.docente,
                    llave,
                    guardados.enunciado,
                    guardados.respuesta_correcta,
                    Jsonb(distractores),
                    guardados.guardado_en,
                ),
            )

    def del_docente(self, docente: str) -> list[tuple[str, DistractoresGuardados]]:
        with _conexion(_con_esquema(self.url)) as conexion:
            filas = conexion.execute(
                "SELECT llave, enunciado, respuesta_correcta, distractores, guardado_en"
                " FROM distractores_guardados WHERE docente = %s ORDER BY guardado_en, llave",
                (docente,),
            ).fetchall()
        return [
            (
                llave,
                DistractoresGuardados(
                    docente=docente,
                    enunciado=enunciado,
                    respuesta_correcta=respuesta_correcta,
                    distractores=tuple(
                        DistractorGuardado(d["expresion"], d["error"]) for d in distractores
                    ),
                    guardado_en=guardado_en,
                ),
            )
            for llave, enunciado, respuesta_correcta, distractores, guardado_en in filas
        ]

    def eliminar(self, docente: str, llave: str) -> bool:
        with _conexion(_con_esquema(self.url)) as conexion:
            fila = conexion.execute(
                "DELETE FROM distractores_guardados WHERE docente = %s AND llave = %s"
                " RETURNING llave",
                (docente, llave),
            ).fetchone()
        return fila is not None


class PreguntasEnPostgres:
    """`RegistroDePreguntas` sobre la tabla `preguntas_del_docente` (ADR-0030). Solo la API
    escribe. Agregar es un `INSERT ... ON CONFLICT DO NOTHING`: si dos pestañas agregan la misma
    pregunta a la vez, queda una fila y la segunda recibe False."""

    def __init__(self, url: str) -> None:
        self.url = url

    def agregar(self, llave: str, pregunta: PreguntaDelDocente) -> bool:
        with _conexion(_con_esquema(self.url)) as conexion:
            fila = conexion.execute(
                "INSERT INTO preguntas_del_docente"
                " (docente, llave, enunciado, respuesta_correcta, agregada_en)"
                " VALUES (%s, %s, %s, %s, %s)"
                " ON CONFLICT (docente, llave) DO NOTHING RETURNING llave",
                (
                    pregunta.docente,
                    llave,
                    pregunta.enunciado,
                    pregunta.respuesta_correcta,
                    pregunta.agregada_en,
                ),
            ).fetchone()
        return fila is not None

    def del_docente(self, docente: str) -> list[tuple[str, PreguntaDelDocente]]:
        with _conexion(_con_esquema(self.url)) as conexion:
            filas = conexion.execute(
                "SELECT llave, enunciado, respuesta_correcta, agregada_en"
                " FROM preguntas_del_docente WHERE docente = %s ORDER BY agregada_en DESC, llave",
                (docente,),
            ).fetchall()
        return [
            (llave, PreguntaDelDocente(docente, enunciado, respuesta_correcta, agregada_en))
            for llave, enunciado, respuesta_correcta, agregada_en in filas
        ]

    def eliminar(self, docente: str, llave: str) -> bool:
        with _conexion(_con_esquema(self.url)) as conexion:
            fila = conexion.execute(
                "DELETE FROM preguntas_del_docente WHERE docente = %s AND llave = %s"
                " RETURNING llave",
                (docente, llave),
            ).fetchone()
        return fila is not None
