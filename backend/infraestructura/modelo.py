"""Modelo de datos compartido por los siete módulos del dominio.

Vive en `infraestructura` porque es el único módulo que todos los demás declaran poder
importar (ver la línea `Importa:` de cada `__init__.py`), así que ubicarlo aquí no obliga a
mover ninguna frontera ni a escribir un ADR para habilitarlo.

Solo depende de la biblioteca estándar: `infraestructura` declara `Importa: ninguno` y este
archivo no puede ser la excepción. Tampoco conoce FastAPI ni Redis; el dominio no debe saber
por qué puerta entró un archivo ni a dónde se guardó.

Cubre el aspecto A-01 (carga de examen para calificación) y, desde la fase 1 del OMR, las
estructuras de la lectura (A-02), la nota (A-03) y la clave (A-04). Que vivan aquí no las
hace de `infraestructura` (ADR-0007, punto 4): la lectura es de `omr`, la nota de
`calificacion` y la clave de `autoria`, y cada `__init__.py` lo declara en su línea `Posee:`.
Están aquí por la misma razón que las de A-01: los adaptadores de persistencia, que viven en
`infraestructura`, tienen que poder escribirlas y releerlas sin importar a sus dueños.
"""

from dataclasses import dataclass, field
from datetime import datetime

__all__ = [
    "ArchivoCargado",
    "HojaAceptada",
    "ArchivoRechazado",
    "ResultadoRecepcion",
    "EntradaDeBitacora",
    "ENCOLADA",
    "PENDIENTE_DE_ENCOLAR",
    "CALIFICADA",
    "EN_REVISION",
    "SIN_CLAVE_HABILITADA",
    "ILEGIBLE",
    "OPCIONES_DE_RESPUESTA",
    "Habilitacion",
    "PreguntaDeLaClave",
    "ClaveDeRespuestas",
    "VACIA",
    "TENUE",
    "BORRON",
    "COMPLETA",
    "UNA_MARCA",
    "SIN_MARCA",
    "DOBLE_MARCA",
    "DUDOSA",
    "CODIGO_COMPLETO",
    "CODIGO_INCOMPLETO",
    "LecturaDeBurbuja",
    "LecturaDePregunta",
    "LecturaDelCodigo",
    "LecturaDeHoja",
    "CORRECTA",
    "INCORRECTA",
    "ANULADA",
    "POR_REVISAR",
    "ResultadoDePregunta",
    "CalificacionDeHoja",
    "ResolucionDelProfesor",
]

# Estados en los que puede quedar una hoja aceptada. Son dos y no uno desde
# [ADR-0006](../../docs/adr/0006-registrar-la-recepcion-en-una-bitacora-antes-de-encolar.md):
# una hoja puede estar almacenada y registrada sin que su trabajo haya llegado a la cola, y
# EC-07 exige que el docente vea esa diferencia en lugar de no ver la hoja.
ENCOLADA = "encolada"
PENDIENTE_DE_ENCOLAR = "pendiente_de_encolar"

# Estados en los que puede terminar una hoja después de que el worker la procesa (A-02 y A-03).
# Son hechos que se derivan de lo registrado, no una columna que se reescribe (ADR-0018).
# `ILEGIBLE` se separa de `EN_REVISION` porque al docente le pide otra cosa: no decidir una
# marca, sino volver a escanear la hoja.
CALIFICADA = "calificada"
EN_REVISION = "en_revision"
SIN_CLAVE_HABILITADA = "sin_clave_habilitada"
ILEGIBLE = "ilegible"


@dataclass(frozen=True)
class ArchivoCargado:
    """Un archivo tal como llega, antes de que nadie lo haya juzgado.

    Es deliberadamente pobre: nombre y bytes. Que el transporte haya sido una petición HTTP
    multipart es asunto de `api`, no del dominio."""

    nombre: str
    contenido: bytes


@dataclass(frozen=True)
class HojaAceptada:
    """Una hoja que pasó la validación y quedó almacenada, con su trabajo encolado o pendiente.

    `referencia` es la ubicación que devolvió el almacén, opaca a propósito: quien la recibe no
    debe suponer que es una ruta de disco, porque el ADR de persistencia (R-06) puede
    convertirla en una clave de objeto sin que este modelo cambie.

    `estado` distingue la hoja cuyo trabajo llegó a la cola de la que quedó almacenada y
    registrada en la bitácora esperando un reintento. El `trabajo_id` existe en ambos casos:
    se acuña antes de tocar la cola, precisamente para que la entrada de bitácora y el trabajo
    que llegue después se refieran al mismo identificador.

    **`hoja_id` y `trabajo_id` son dos identidades distintas** desde
    [ADR-0018](../../docs/adr/0018-dar-a-la-hoja-una-identidad-propia-y-derivar-su-estado-de-la-bitacora.md).
    `hoja_id` es la de la hoja: se acuña una sola vez, al aceptarla, y es la que referenciará todo
    lo que se sepa de ella después (la detección, la nota, la revisión manual). `trabajo_id` es
    la de un encargo de procesarla: el reintento desde la bitácora conserva el mismo, y volver a
    procesar la hoja (por ejemplo, para recalificarla tras corregir la clave) será un trabajo
    nuevo de la misma hoja. Usar uno para las dos cosas obligaba a elegir entre poder
    reprocesar y que el worker no procese dos veces el mismo encargo (ADR-0016).

    **`estado` es una instantánea del momento de la respuesta, no el estado vigente.** El
    estado vigente de una hoja se deriva de la bitácora, que es su fuente de verdad (ADR-0018 y
    la violación V-3 del arc42 §8.3): una hoja `pendiente_de_encolar` que después se reintente
    seguirá diciendo `pendiente_de_encolar` en esta copia."""

    examen_id: str
    nombre_archivo: str
    referencia: str
    trabajo_id: str
    recibida_en: datetime
    hoja_id: str
    estado: str = ENCOLADA


@dataclass(frozen=True)
class ArchivoRechazado:
    """Un archivo que no se admitió, con el motivo en texto legible para el docente.

    El motivo es obligatorio: EC-07 exige que ningún archivo desaparezca sin dejar traza, y un
    rechazo sin explicación es indistinguible de una pérdida desde el lado del usuario."""

    nombre_archivo: str
    motivo: str


@dataclass(frozen=True)
class ResultadoRecepcion:
    """Lo que se le responde al docente tras una carga: qué entró y qué no.

    Su invariante es la promesa de EC-07: la suma de aceptadas y rechazados es igual al número
    de archivos que se cargaron. Ningún archivo se pierde en silencio."""

    examen_id: str
    aceptadas: tuple[HojaAceptada, ...]
    rechazados: tuple[ArchivoRechazado, ...]

    @property
    def total_procesados(self) -> int:
        return len(self.aceptadas) + len(self.rechazados)


@dataclass(frozen=True)
class EntradaDeBitacora:
    """Una hoja almacenada cuyo procesamiento se va a encolar, o quedó pendiente de encolarse.

    Es lo mínimo que hace falta para reintentar sin volver a pedirle el archivo al docente: el
    identificador del trabajo, dónde quedó la imagen y de qué examen es. Desde ADR-0018 lleva
    también la identidad de la hoja, para que el reintento publique un trabajo de la misma hoja
    y no una hoja nueva."""

    trabajo_id: str
    examen_id: str
    referencia: str
    nombre_archivo: str
    hoja_id: str
<<<<<<< HEAD
=======


# ---------------------------------------------------------------------------------------------
# A-04 · La clave de respuestas. Dueño: `autoria` (ADR-0007). Mientras A-04 no esté construido,
# la escribe a mano quien prepara un examen sintético, y `infraestructura.claves` la relee.
# ---------------------------------------------------------------------------------------------

# Las opciones que imprime la hoja. La pantalla de revisión del frontend trabaja con las mismas.
OPCIONES_DE_RESPUESTA = ("A", "B", "C", "D")


@dataclass(frozen=True)
class Habilitacion:
    """Quién habilitó el examen para calificarlo, y cuándo (RF-07, EC-05).

    `por` es hoy un nombre escrito a mano: la identidad autenticada llega con A-05."""

    por: str
    en: datetime


@dataclass(frozen=True)
class PreguntaDeLaClave:
    """La respuesta correcta de una pregunta y lo que vale.

    `numero` es el que está impreso en la hoja, de 1 al máximo del formato. El peso es libre
    (la pantalla de revisión usa 1,0 y 0,5); la nota se normaliza contra la suma de los pesos."""

    numero: int
    correcta: str
    peso: float = 1.0


@dataclass(frozen=True)
class ClaveDeRespuestas:
    """La clave de un examen tal como la registró el profesor.

    Cuántas preguntas tiene el examen lo dice la clave, no la hoja: la hoja imprime el máximo
    del formato y las filas sobrantes quedan en blanco. Una clave sin `habilitacion` existe
    (el profesor la está revisando) pero no se puede calificar con ella: esa regla la aplica
    `calificacion`, no el adaptador que la lee."""

    examen_id: str
    preguntas: tuple[PreguntaDeLaClave, ...]
    habilitacion: Habilitacion | None = None


# ---------------------------------------------------------------------------------------------
# A-02 · La lectura de una hoja. Dueño: `omr`. Solo números y letras: la imagen no viaja aquí.
# ---------------------------------------------------------------------------------------------

# Tipos de marca de una burbuja: los cuatro que ya muestra la pantalla de revisión.
VACIA = "vacia"
TENUE = "tenue"
BORRON = "borron"
COMPLETA = "completa"

# Cómo queda decidida una pregunta. `DUDOSA` es toda pregunta cuya confianza no llega al umbral:
# va a revisión manual y el sistema no elige por el profesor (RF-03, EC-02).
UNA_MARCA = "una_marca"
SIN_MARCA = "sin_marca"
DOBLE_MARCA = "doble_marca"
DUDOSA = "dudosa"

# Cómo queda el código del estudiante.
CODIGO_COMPLETO = "completo"
CODIGO_INCOMPLETO = "incompleto"


@dataclass(frozen=True)
class LecturaDeBurbuja:
    """Lo que se midió en una burbuja.

    `opcion` es la letra (A a D) en una pregunta o el dígito (0 a 9) en el código. `relleno` es
    la proporción de píxeles oscuros dentro de la burbuja, de 0 a 1, y `confianza`, de 0 a 100,
    la probabilidad de que la marca sea una respuesta intencional, como la define la pantalla de
    revisión (que no la muestra en una burbuja vacía)."""

    opcion: str
    relleno: float
    tipo: str
    confianza: int


@dataclass(frozen=True)
class LecturaDePregunta:
    """Una fila de respuestas ya decidida. `opcion` solo tiene valor con `UNA_MARCA`, y
    `confianza` es la de la decisión que se tomó (la regla está en `omr.decision`)."""

    numero: int
    estado: str
    opcion: str | None
    confianza: int
    burbujas: tuple[LecturaDeBurbuja, ...]


@dataclass(frozen=True)
class LecturaDelCodigo:
    """El código del estudiante, una `T` impresa y ocho dígitos marcados.

    **Es un dato personal** (RNF-12, arc42 §8.7): `valor` va fuera del `repr` para que un
    registro descuidado de la lectura no lo escriba en el log. `columnas_por_revisar` dice qué
    posiciones (1 a 8) quedaron sin marca, con dos o dudosas; sin ellas el código es completo."""

    estado: str
    valor: str | None = field(default=None, repr=False)
    columnas_por_revisar: tuple[int, ...] = ()


@dataclass(frozen=True)
class LecturaDeHoja:
    """Lo que `omr` leyó en una hoja, sin juzgar todavía si está bien o mal.

    Trae todas las filas que imprime el formato, en orden, aunque el examen tenga menos
    preguntas. Guarda el umbral con el que se decidió para que la lectura se pueda reproducir
    y comparar cuando el umbral se calibre (R-04)."""

    version_del_formato: str
    codigo: LecturaDelCodigo
    preguntas: tuple[LecturaDePregunta, ...]
    umbral_de_confianza: int
    duracion_ms: float


# ---------------------------------------------------------------------------------------------
# A-03 · La nota de una hoja. Dueño: `calificacion`.
# ---------------------------------------------------------------------------------------------

# Veredictos de una pregunta. Los tres primeros son los de la pantalla de revisión; `POR_REVISAR`
# es el de una pregunta dudosa o con doble marca que el profesor todavía no resolvió.
CORRECTA = "correcta"
INCORRECTA = "incorrecta"
ANULADA = "anulada"
POR_REVISAR = "por_revisar"


@dataclass(frozen=True)
class ResultadoDePregunta:
    """Una pregunta comparada contra la clave. `marcada` es la opción leída o la que fijó el
    profesor al resolverla; `puntos` es lo que suma a la nota."""

    numero: int
    veredicto: str
    marcada: str | None
    correcta: str
    peso: float
    puntos: float
    resuelta_por_el_profesor: bool = False


@dataclass(frozen=True)
class CalificacionDeHoja:
    """La nota de una hoja en la escala de la UTB.

    Se guarda en décimas, como en el frontend (42 es 4,2), para que el redondeo y la comparación
    con el corte de aprobación no dependan de flotantes. Es `provisional` mientras quede alguna
    pregunta `POR_REVISAR` o el código esté incompleto (ADR-0002)."""

    examen_id: str
    nota_en_decimas: int
    puntos: float
    puntos_posibles: float
    provisional: bool
    codigo_por_revisar: bool
    preguntas: tuple[ResultadoDePregunta, ...]


@dataclass(frozen=True)
class ResolucionDelProfesor:
    """Lo que el profesor decidió sobre una pregunta en revisión (RF-08), con quién y cuándo
    para que la modificación quede consultable (RF-10). `opcion` es la que reconoce como
    marcada, si aplica."""

    numero: int
    veredicto: str
    opcion: str | None
    por: str
    en: datetime
>>>>>>> 32a2567 (feat(omr): leer la hoja en posiciones fijas y medir cada burbuja contra su papel (A-02))
