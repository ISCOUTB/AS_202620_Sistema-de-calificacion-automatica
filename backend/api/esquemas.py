"""Esquemas de la interfaz HTTP: la forma exacta del cuerpo que la API promete devolver.

Viven en `api` y no en `infraestructura/modelo.py` a proposito. Las dataclasses del modelo son
el vocabulario del dominio y solo dependen de la biblioteca estandar; estas clases son el
contrato de una puerta concreta, saben de Pydantic y de OpenAPI, y cambian cuando cambia la API
aunque el dominio no se mueva. Declararlas alla obligaria a `infraestructura` a importar
Pydantic y romperia su linea `Importa: ninguno`, que es lo que verifica `test_fronteras.py`.

Lo que gana el contrato al declararlas: sin `response_model`, `/openapi.json` describe cada
respuesta como un objeto vacio, porque las dos rutas estaban anotadas `-> dict`. Con estas
clases el documento dice campo por campo que devuelve cada ruta y de que tipo, que es lo que un
consumidor necesita para generar su cliente y lo que la prueba de contrato compara.
"""

from datetime import datetime
from typing import Literal, get_args

from pydantic import BaseModel, ConfigDict, Field

from infraestructura.modelo import (
    CALIFICADA,
    EN_REVISION,
    ENCOLADA,
    ILEGIBLE,
    OPCIONES_DE_RESPUESTA,
    PENDIENTE_DE_ENCOLAR,
    SIN_CLAVE_HABILITADA,
)

# Version del contrato, no del proyecto. Se declara aqui, junto a los esquemas que versiona,
# para que cambiar uno sin tocar la otra sea visible en el mismo diff.
#
# 1.1.0 agrega la ruta de distractores (RF-11). Sube la version menor y no la mayor porque solo
# agrega: las dos rutas de 1.0.0 y sus esquemas siguen identicos, asi que nadie que ya consuma la
# API tiene que cambiar nada.
#
# 1.2.0 agrega `GET /metricas` y el 429 de la ruta de distractores (escenario del segundo corte,
# EC-09, ADR-0015). Vuelve a subir la menor y no la mayor por la misma razón: las rutas y los
# esquemas de 1.1.0 siguen identicos. Un cliente que ya consume `/distractores` puede recibir
# ahora un 429, pero ese codigo no reemplaza a ninguno de los que ya conocia: solo aparece cuando
# antes la solicitud habria agotado la cuota del proveedor.
#
# 1.3.0 agrega `hoja_id` a cada hoja aceptada (ADR-0018): la identidad de la hoja, separada de la
# de su trabajo. Solo agrega un campo a una respuesta, así que vuelve a subir la menor: un cliente
# que ya lee `trabajo_id` lo sigue recibiendo igual.
#
# 1.4.0 agrega la cache de propuestas (ADR-0019): el campo opcional `otras` en la solicitud de
# distractores, `desde_la_cache` en su respuesta y el estado de la cache en `GET /metricas`. Todo
# agrega; un cliente que no manda `otras` recibe lo mismo que antes, ahora quiza sin gastar cupo.
#
# 1.5.0 agrega el presupuesto de carga (S13, ADR-0022): el 413 y el 429 de la ruta de carga y su
# estado en `GET /metricas`. Vuelve a subir la menor: un lote que cabe recibe la misma respuesta
# que antes, y los dos codigos nuevos solo aparecen donde antes el lote habria entrado sin tope.
#
# 1.6.0 agrega `GET /examenes/{examen_id}/resultados`, como quedo cada hoja leida (A-02 y A-03,
# ADR-0023). Solo agrega una ruta: las demas siguen identicas.
#
# 1.7.0 agrega `GET /examenes`, los examenes con clave registrada, para que la pantalla de carga
# los ofrezca en una lista. Solo agrega una ruta, sin las respuestas de la clave.
#
# 1.8.0 agrega la revision manual (RF-08): las preguntas que esperan al profesor, su recorte y la
# ruta que guarda lo que resolvio, mas el campo `revisada` en el resultado de cada hoja. Todo
# agrega; un cliente que no conoce `revisada` recibe lo mismo de antes.
VERSION_DEL_CONTRATO = "1.8.0"

EstadoDeHoja = Literal["encolada", "pendiente_de_encolar"]

# `Literal` exige literales, asi que el tipo de arriba no puede construirse desde las constantes
# del dominio. Se comprueba aqui que no se separen: si alguien renombra un estado en
# `modelo.py`, esto falla al importar en vez de publicar un contrato que miente sobre los
# valores que el docente va a recibir.
if set(get_args(EstadoDeHoja)) != {ENCOLADA, PENDIENTE_DE_ENCOLAR}:
    raise RuntimeError(
        "Los estados declarados en el contrato HTTP no coinciden con los de "
        "infraestructura/modelo.py. Actualiza EstadoDeHoja y la version del contrato."
    )


EstadoDeLectura = Literal["calificada", "en_revision", "sin_clave_habilitada", "ilegible"]

if set(get_args(EstadoDeLectura)) != {CALIFICADA, EN_REVISION, SIN_CLAVE_HABILITADA, ILEGIBLE}:
    raise RuntimeError(
        "Los estados de lectura declarados en el contrato HTTP no coinciden con los de "
        "infraestructura/modelo.py. Actualiza EstadoDeLectura y la version del contrato."
    )


OpcionDeRespuesta = Literal["A", "B", "C", "D"]

if get_args(OpcionDeRespuesta) != OPCIONES_DE_RESPUESTA:
    raise RuntimeError(
        "Las opciones declaradas en el contrato HTTP no coinciden con las que imprime la hoja "
        "(infraestructura/modelo.py). Actualiza OpcionDeRespuesta y la version del contrato."
    )


class RespuestaDeSalud(BaseModel):
    """Lo que devuelve la sonda de vida. Hoy tiene un unico valor posible y el esquema lo dice
    asi: declararlo como texto libre prometeria una variedad que la ruta no tiene."""

    status: Literal["ok"] = Field(description="Unico valor posible mientras la API responde.")


class HojaAceptadaEnRespuesta(BaseModel):
    """Una hoja que paso la validacion y quedo almacenada.

    No lleva `examen_id` porque ya viaja una sola vez en la raiz de la respuesta, y repetirlo
    por hoja invitaria a un consumidor a suponer que un lote puede mezclar examenes. La
    dataclass del dominio si lo trae, y `model_validate` lo descarta al construir esta."""

    model_config = ConfigDict(from_attributes=True)

    nombre_archivo: str = Field(description="Nombre con el que el docente envio el archivo.")
    referencia: str = Field(
        description=(
            "Ubicacion que devolvio el almacen. Opaca a proposito: el consumidor no debe "
            "suponer que es una ruta de disco, porque el ADR de persistencia (R-06) puede "
            "convertirla en una clave de objeto sin que este contrato cambie."
        )
    )
    hoja_id: str = Field(
        description=(
            "Identidad de la hoja, acunada una sola vez al aceptarla (ADR-0018). Es la que "
            "referencia todo lo que se sepa de la hoja despues; una hoja puede tener mas de un "
            "trabajo, y todos llevan este mismo valor."
        )
    )
    trabajo_id: str = Field(
        description=(
            "Identificador del trabajo de procesamiento. Se acuna antes de tocar la cola, asi "
            "que existe tambien cuando el estado es pendiente_de_encolar."
        )
    )
    recibida_en: datetime = Field(description="Momento en que el sistema acepto la hoja.")
    estado: EstadoDeHoja = Field(
        description=(
            "encolada: su trabajo llego a la cola. pendiente_de_encolar: la hoja esta "
            "almacenada y registrada en la bitacora, pero su trabajo no llego a la cola y el "
            "sistema debe reintentarlo (ADR-0006)."
        )
    )


class ArchivoRechazadoEnRespuesta(BaseModel):
    """Un archivo que no se admitio, con el motivo en texto legible para el docente.

    El motivo es obligatorio: EC-07 exige que ningun archivo desaparezca sin dejar traza, y un
    rechazo sin explicacion es indistinguible de una perdida desde el lado del usuario."""

    model_config = ConfigDict(from_attributes=True)

    nombre_archivo: str = Field(description="Nombre con el que el docente envio el archivo.")
    motivo: str = Field(description="Por que no se admitio, redactado para el docente.")


class RespuestaDeCarga(BaseModel):
    """Lo que responde la carga de hojas: que entro y que no.

    La invariante que promete es la de EC-07: `total_procesados` es igual al numero de
    elementos de `aceptadas` mas los de `rechazados`, y ese numero es el de archivos que el
    docente envio. Ningun archivo se pierde en silencio."""

    examen_id: str = Field(description="Examen al que se cargaron las hojas.")
    total_procesados: int = Field(
        description="Aceptadas mas rechazados. Igual al numero de archivos enviados (EC-07)."
    )
    aceptadas: list[HojaAceptadaEnRespuesta]
    rechazados: list[ArchivoRechazadoEnRespuesta]


class ResultadoDeHojaEnRespuesta(BaseModel):
    """Como quedo una hoja despues de leerla y calificarla.

    **No lleva el codigo del estudiante.** La API no tiene inicio de sesion hasta A-05, y esta
    ruta es tan publica como las demas; el codigo queda en el registro del servidor (AM-02)."""

    model_config = ConfigDict(from_attributes=True)

    hoja_id: str = Field(
        description="La identidad que devolvio la carga al recibir la hoja (ADR-0018)."
    )
    estado: EstadoDeLectura = Field(
        description=(
            "calificada: tiene nota y nada espera al profesor. en_revision: tiene nota "
            "provisional, con preguntas por revisar. sin_clave_habilitada: se leyo, pero el "
            "examen no tiene una clave habilitada. ilegible: no se pudo leer, y hay que volver "
            "a tomar la foto."
        )
    )
    motivo: str | None = Field(
        description=(
            "Por que no tiene nota (sin_clave, clave_sin_habilitar, clave_mal_escrita) o por que "
            "no se pudo leer (por ejemplo imagen_ilegible o marcas_de_registro_no_encontradas)."
        )
    )
    nota_en_decimas: int | None = Field(
        description="La nota de 0 a 50 (42 es 4,2). Nula sin clave o si la hoja es ilegible.",
        ge=0,
        le=50,
    )
    provisional: bool = Field(description="Verdadero mientras haya preguntas por revisar.")
    preguntas_por_revisar: list[int] = Field(
        description="Los numeros de las preguntas que esperan al profesor."
    )
    codigo_completo: bool | None = Field(
        description=(
            "Si el codigo del estudiante se leyo en sus ocho columnas. Nulo si la hoja es "
            "ilegible. El codigo mismo no viaja."
        )
    )
    momento: datetime = Field(description="Cuando quedo este resultado.")
    revisada: bool = Field(
        description=(
            "Si la nota incluye lo que resolvio el profesor en las preguntas en revision (RF-08). "
            "Distingue una nota corregida a mano de una automatica (RNF-15)."
        )
    )


class ResultadosDelExamenEnRespuesta(BaseModel):
    """Las hojas leidas de un examen, cada una con su ultimo resultado. Una hoja recibida que
    todavia no aparece esta en la cola o leyendose."""

    examen_id: str
    hojas: list[ResultadoDeHojaEnRespuesta]


class BurbujaEnRespuesta(BaseModel):
    """Lo que se midio en una burbuja de una pregunta en revision."""

    model_config = ConfigDict(from_attributes=True)

    opcion: OpcionDeRespuesta
    tipo: str = Field(description="vacia, tenue, borron o completa.")
    confianza: int = Field(
        ge=0, le=100, description="Que tan probable es que la marca sea intencional."
    )


class PreguntaEnRevisionEnRespuesta(BaseModel):
    """Una pregunta que la lectura no pudo decidir. **No lleva la respuesta correcta**: el profesor
    dice que marco el estudiante y el sistema decide si es correcto."""

    model_config = ConfigDict(from_attributes=True)

    numero: int
    burbujas: list[BurbujaEnRespuesta]
    con_recorte: bool = Field(
        description="Si hay un recorte de la fila para mostrar en `.../preguntas/{numero}/recorte`."
    )
    resuelta: bool
    opcion_resuelta: OpcionDeRespuesta | None = Field(
        description="La opcion que el profesor vio marcada, o nula si dijo que ninguna vale."
    )
    resuelta_por: str | None = Field(
        description="El nombre que escribio quien la resolvio. Sin verificar hasta A-05."
    )
    resuelta_en: datetime | None


class HojaEnRevisionEnRespuesta(BaseModel):
    """Una hoja con preguntas en revision, con su nota vigente. Sin el codigo del estudiante."""

    model_config = ConfigDict(from_attributes=True)

    hoja_id: str
    nota_en_decimas: int = Field(ge=0, le=50)
    provisional: bool
    codigo_completo: bool
    preguntas: list[PreguntaEnRevisionEnRespuesta]


class RevisionDelExamenEnRespuesta(BaseModel):
    """Las hojas de un examen que tienen o tuvieron preguntas en revision."""

    examen_id: str
    hojas: list[HojaEnRevisionEnRespuesta]


class ResolucionEnSolicitud(BaseModel):
    """Lo que el profesor vio marcado en una pregunta: una opcion, o nula si ninguna vale (en
    blanco o con dos marcas)."""

    numero: int = Field(ge=1)
    opcion: OpcionDeRespuesta | None


class SolicitudDeRevision(BaseModel):
    """Lo que el profesor resolvio en una hoja, todo junto. `por` queda registrado con cada
    resolucion (RF-10); es un nombre escrito a mano hasta A-05."""

    por: str = Field(min_length=1, max_length=80)
    resoluciones: list[ResolucionEnSolicitud] = Field(min_length=1, max_length=100)


class ExamenEnRespuesta(BaseModel):
    """Un examen con clave registrada. **No lleva las respuestas**: la ruta es publica hasta A-05,
    y para elegir el examen basta con su identificador."""

    model_config = ConfigDict(from_attributes=True)

    examen_id: str
    habilitada: bool = Field(
        description="Si la clave ya esta habilitada. Sin habilitar, las hojas se leen sin nota."
    )


class ExamenesEnRespuesta(BaseModel):
    """Los examenes con clave registrada, ordenados por identificador."""

    examenes: list[ExamenEnRespuesta]


class SolicitudDeDistractores(BaseModel):
    """Lo que el profesor envia para pedir distractores diagnosticos (RF-11).

    Son los mismos tres campos de `PreguntaParaDistractores` y ninguno mas: es lo unico que puede
    llegar al proveedor de LLM, y por eso RNF-13 se cumple desde la puerta. Los limites de largo
    acotan lo que cuesta cada solicitud en tokens."""

    enunciado: str = Field(
        min_length=1, max_length=1000, description="Enunciado de la pregunta, en texto plano."
    )
    respuesta_correcta: str = Field(
        min_length=1, max_length=300, description="La respuesta correcta de la clave."
    )
    cantidad: int = Field(
        default=3, ge=1, le=5, description="Cuantos distractores se piden. Entre 1 y 5."
    )
    # No viaja al proveedor: decide si se lee la cache (ADR-0019). RNF-13 sigue cumpliendose,
    # porque lo que llega al proveedor sigue siendo `PreguntaParaDistractores`.
    otras: bool = Field(
        default=False,
        description=(
            "true para pedir propuestas nuevas: no se leen las guardadas para esta misma pregunta, "
            "se piden al proveedor y reemplazan a las guardadas (ADR-0019). Gasta cupo."
        ),
    )


class DistractorEnRespuesta(BaseModel):
    """Una opcion incorrecta propuesta, con el error de procedimiento que representa. Es una
    propuesta: no entra a ningun examen hasta que el profesor la acepte y lo habilite (RF-07)."""

    model_config = ConfigDict(from_attributes=True)

    expresion: str = Field(description="La opcion incorrecta, en texto plano.")
    error: str = Field(description="El error de procedimiento que la produce.")


class DescartadoEnRespuesta(BaseModel):
    """Una propuesta del modelo que no llego al profesor, con el motivo."""

    model_config = ConfigDict(from_attributes=True)

    expresion: str = Field(description="Lo que propuso el modelo.")
    motivo: str = Field(description="Por que no se muestra, redactado para el profesor.")


class RespuestaDeDistractores(BaseModel):
    """Lo que responde la solicitud de distractores: lo que paso la regla y lo que no.

    Ninguna propuesta de `distractores` repite la respuesta correcta (medida M1 de EC-08). Las
    descartadas se devuelven con su motivo para que el profesor sepa por que recibio menos de lo
    que pidio."""

    distractores: list[DistractorEnRespuesta]
    descartados: list[DescartadoEnRespuesta]
    desde_la_cache: bool = Field(
        description=(
            "true si las propuestas salieron de una solicitud anterior igual, guardada hace menos "
            "de 24 horas, sin llamar al proveedor ni gastar cupo (ADR-0019). La regla se aplico "
            "otra vez sobre ellas."
        )
    )


class ProveedorNoDisponibleEnRespuesta(BaseModel):
    """Cuerpo del 503: el proveedor no esta configurado, no respondio a tiempo o fallo.

    Usa el campo `detail` de los errores de FastAPI para que un cliente lea igual este error y
    los demas."""

    detail: str = Field(description="Que paso, redactado para el profesor.")


class PresupuestoAgotadoEnRespuesta(BaseModel):
    """Cuerpo del 429: la solicitud no cabe en el presupuesto y no se envio al proveedor (ADR-0015).

    La respuesta lleva ademas la cabecera `Retry-After` con los segundos que faltan para que haya
    cupo. Usa `detail`, como el 503, para que un cliente lea los dos errores igual."""

    detail: str = Field(
        description="Que paso y cuando volver a pedirlo, redactado para el profesor."
    )


class EstadoDelPresupuestoEnRespuesta(BaseModel):
    """Cuanto del presupuesto de solicitudes al proveedor de LLM se ha usado.

    Las dos ventanas deslizantes son las que deciden si una solicitud cabe. Los contadores
    `desde_el_arranque` son observabilidad y vuelven a cero cuando el proceso se reinicia."""

    model_config = ConfigDict(from_attributes=True)

    limite_por_minuto: int = Field(description="Solicitudes al proveedor admitidas por minuto.")
    limite_por_dia: int = Field(description="Solicitudes al proveedor admitidas en 24 horas.")
    usadas_en_el_ultimo_minuto: int = Field(description="Enviadas en los ultimos 60 s.")
    usadas_en_las_ultimas_24_horas: int = Field(description="Enviadas en las ultimas 24 horas.")
    enviadas_desde_el_arranque: int = Field(
        description="Solicitudes que salieron hacia el proveedor desde que arranco el proceso."
    )
    rechazadas_desde_el_arranque: int = Field(
        description=(
            "Solicitudes cortadas con 429, sin salir a la red, desde que arranco el proceso."
        )
    )
    arrancado_en: datetime = Field(description="Momento en que arranco el proceso de la API.")


class EstadoDeLaCacheEnRespuesta(BaseModel):
    """Cuanto se ha usado la cache de propuestas de distractores (ADR-0019).

    Son cuentas desde el arranque del proceso: la cache vive en su memoria y se vacia con cada
    reinicio."""

    model_config = ConfigDict(from_attributes=True)

    capacidad: int = Field(description="Cuantas preguntas caben como mucho.")
    vigencia_segundos: int = Field(description="Cuanto vale una entrada desde que se guardo.")
    entradas: int = Field(description="Preguntas guardadas ahora.")
    aciertos: int = Field(description="Solicitudes respondidas desde la cache, sin gastar cupo.")
    fallos: int = Field(description="Lecturas sin una entrada vigente, que salieron al proveedor.")
    guardadas: int = Field(description="Respuestas del proveedor guardadas o reemplazadas.")
    vencidas: int = Field(description="Entradas descartadas por pasar de su vigencia.")
    expulsadas: int = Field(description="Entradas que salieron porque la cache estaba llena.")


class LoteFueraDePresupuestoEnRespuesta(BaseModel):
    """Cuerpo del 413 y del 429 de la ruta de carga: el lote no cabe en el presupuesto de carga y
    no entro ninguna de sus hojas (ADR-0022).

    El 429 lleva ademas la cabecera `Retry-After` con los segundos que faltan para que el lote
    quepa. Usa `detail`, como los demas errores, para que un cliente los lea igual."""

    detail: str = Field(description="Que paso y que hacer, redactado para el docente.")


class EstadoDelPresupuestoDeCargaEnRespuesta(BaseModel):
    """Cuanto del presupuesto de carga se ha usado (ADR-0022).

    La ventana de 24 horas es la que decide si un lote cabe. Los contadores `desde_el_arranque`
    son observabilidad y vuelven a cero cuando el proceso se reinicia."""

    model_config = ConfigDict(from_attributes=True)

    limite_de_hojas_por_lote: int = Field(description="Hojas que admite un lote como mucho.")
    limite_de_bytes_por_dia: int = Field(description="Bytes de hojas admitidos en 24 horas.")
    bytes_en_las_ultimas_24_horas: int = Field(
        description="Bytes de los lotes que entraron en las ultimas 24 horas."
    )
    lotes_admitidos_desde_el_arranque: int = Field(
        description="Lotes que cupieron en el presupuesto desde que arranco el proceso."
    )
    lotes_rechazados_desde_el_arranque: int = Field(
        description="Lotes cortados con 413 o 429, sin leer sus hojas, desde que arranco el proceso."
    )
    arrancado_en: datetime = Field(description="Momento en que arranco el proceso de la API.")


class RespuestaDeMetricas(BaseModel):
    """Lo que devuelve `GET /metricas`: el estado del presupuesto del proveedor de LLM.

    Es la metrica de EC-09 consultable en vivo, como `lote_confirmado` en el registro lo es de
    EC-07. Desde la S13 publica tambien el presupuesto de carga (ADR-0022). Solo publica cuentas:
    ningun dato de un profesor, de una pregunta ni de una hoja."""

    presupuesto_de_distractores: EstadoDelPresupuestoEnRespuesta
    cache_de_distractores: EstadoDeLaCacheEnRespuesta
    presupuesto_de_carga: EstadoDelPresupuestoDeCargaEnRespuesta
