"""La nota de una hoja (RF-04) y su recálculo tras la revisión manual (RF-08).

Las reglas son las de la pantalla de revisión del frontend: si el backend calculara distinto, el
docente vería en pantalla una nota y recibiría otra. El caso del diseño («4,2 / 5,0» y «4,6 si se
acepta A») se reproduce aquí con los mismos pesos."""

from datetime import datetime, timezone

import pytest

from calificacion import (
    ClaveIncompatible,
    ClaveNoHabilitada,
    calificar,
    nota_vigente,
    recalcular,
    resolucion_con_opcion,
    resoluciones_vigentes,
)
from infraestructura.modelo import (
    ANULADA,
    CODIGO_COMPLETO,
    CODIGO_INCOMPLETO,
    CORRECTA,
    DOBLE_MARCA,
    DUDOSA,
    INCORRECTA,
    POR_REVISAR,
    SIN_MARCA,
    UNA_MARCA,
    ClaveDeRespuestas,
    Habilitacion,
    LecturaDeHoja,
    LecturaDelCodigo,
    LecturaDePregunta,
    PreguntaDeLaClave,
    ResolucionDelProfesor,
)

AHORA = datetime(2026, 11, 3, 12, 0, tzinfo=timezone.utc)
HABILITADA = Habilitacion(por="Docente de prueba", en=AHORA)


def _lectura(*filas: str, codigo: str = CODIGO_COMPLETO) -> LecturaDeHoja:
    """Una lectura con una fila por argumento: una letra es una marca, dos letras una doble
    marca, `-` una fila en blanco y `?` una dudosa."""

    def fila(numero: int, texto: str) -> LecturaDePregunta:
        if texto == "-":
            return LecturaDePregunta(numero, SIN_MARCA, None, 95, ())
        if texto == "?":
            return LecturaDePregunta(numero, DUDOSA, None, 50, ())
        if len(texto) == 2:
            return LecturaDePregunta(numero, DOBLE_MARCA, None, 90, ())
        return LecturaDePregunta(numero, UNA_MARCA, texto, 95, ())

    if codigo == CODIGO_COMPLETO:
        lectura_del_codigo = LecturaDelCodigo(codigo, "T12345678")
    else:
        lectura_del_codigo = LecturaDelCodigo(codigo, "T12?45678", (3,))
    return LecturaDeHoja(
        version_del_formato="quantia-hoja-v1",
        codigo=lectura_del_codigo,
        preguntas=tuple(fila(n, texto) for n, texto in enumerate(filas, start=1)),
        umbral_de_confianza=70,
        duracion_ms=1.0,
    )


def _clave(correctas: str, pesos: tuple[float, ...] | None = None) -> ClaveDeRespuestas:
    pesos = pesos or (1.0,) * len(correctas)
    return ClaveDeRespuestas(
        examen_id="examen-sintetico",
        preguntas=tuple(
            PreguntaDeLaClave(numero, correcta, peso)
            for numero, (correcta, peso) in enumerate(zip(correctas, pesos), start=1)
        ),
        habilitacion=HABILITADA,
    )


def _resolucion(numero: int, veredicto: str, opcion: str | None) -> ResolucionDelProfesor:
    return ResolucionDelProfesor(numero, veredicto, opcion, por="Docente de prueba", en=AHORA)


# --- Calificar -------------------------------------------------------------------------------


def test_el_caso_del_diseno_da_4_2_provisional_y_4_6_al_aceptar_la_marca():
    """15 preguntas, diez de peso 1,0 y cinco de 0,5 (12,5 puntos). Hay 10,5 asegurados y la
    pregunta 10, de peso 1,0 y clave A, quedó dudosa."""
    clave = _clave("ABCDABCDAA" + "BBBBB", pesos=(1.0,) * 10 + (0.5,) * 5)
    lectura = _lectura("A", "B", "C", "D", "A", "B", "C", "D", "A", "?", "B", "B", "B", "C", "-")

    tentativa = calificar(lectura, clave)

    assert (tentativa.puntos, tentativa.puntos_posibles) == (10.5, 12.5)
    assert tentativa.nota_en_decimas == 42
    assert tentativa.provisional
    assert tentativa.preguntas[9].veredicto == POR_REVISAR

    resuelta = recalcular(tentativa, (_resolucion(10, CORRECTA, "A"),))

    assert resuelta.nota_en_decimas == 46
    assert not resuelta.provisional
    assert resuelta.preguntas[9].resuelta_por_el_profesor


def test_la_nota_redondea_la_mitad_hacia_arriba_como_el_frontend():
    """1 de 4 da 12,5 décimas. El `round()` de Python daría 12; Dart, y la pantalla, 13."""
    calificacion = calificar(_lectura("A", "-", "-", "-"), _clave("AAAA"))

    assert calificacion.nota_en_decimas == 13


def test_sin_marca_es_incorrecta_y_no_deja_la_nota_provisional():
    calificacion = calificar(_lectura("A", "-"), _clave("AB"))

    assert [r.veredicto for r in calificacion.preguntas] == [CORRECTA, INCORRECTA]
    assert calificacion.nota_en_decimas == 25
    assert not calificacion.provisional


def test_una_dudosa_o_una_doble_marca_quedan_por_revisar_y_suman_cero():
    calificacion = calificar(_lectura("?", "AC", "D"), _clave("ACD"))

    assert [r.veredicto for r in calificacion.preguntas] == [POR_REVISAR, POR_REVISAR, CORRECTA]
    assert [r.marcada for r in calificacion.preguntas] == [None, None, "D"]
    assert calificacion.puntos == 1.0
    assert calificacion.provisional


def test_las_filas_que_la_clave_no_menciona_no_cuentan():
    """La hoja imprime 40 preguntas; un examen de 3 deja el resto en blanco, o con garabatos."""
    calificacion = calificar(_lectura("A", "B", "C", "?", "AB"), _clave("ABC"))

    assert len(calificacion.preguntas) == 3
    assert calificacion.nota_en_decimas == 50
    assert not calificacion.provisional


def test_con_el_codigo_incompleto_la_nota_es_provisional():
    calificacion = calificar(_lectura("A", "B", codigo=CODIGO_INCOMPLETO), _clave("AB"))

    assert calificacion.nota_en_decimas == 50
    assert calificacion.codigo_por_revisar
    assert calificacion.provisional


def test_sin_habilitacion_no_se_califica():
    clave = ClaveDeRespuestas("examen-sintetico", _clave("AB").preguntas, habilitacion=None)

    with pytest.raises(ClaveNoHabilitada):
        calificar(_lectura("A", "B"), clave)


@pytest.mark.parametrize(
    "preguntas",
    [
        (),
        (PreguntaDeLaClave(1, "A"), PreguntaDeLaClave(3, "B")),
        (PreguntaDeLaClave(1, "A"), PreguntaDeLaClave(1, "B")),
        (PreguntaDeLaClave(1, "E"),),
        (PreguntaDeLaClave(1, "A", 0.0),),
        (PreguntaDeLaClave(1, "A", -1.0),),
        (PreguntaDeLaClave(1, "A", float("nan")),),
    ],
    ids=["vacia", "pregunta-que-no-imprime", "repetida", "opcion-E", "peso-0", "peso-negativo",
         "peso-nan"],
)
def test_una_clave_que_no_cabe_en_la_hoja_es_incompatible(preguntas):
    clave = ClaveDeRespuestas("examen-sintetico", preguntas, habilitacion=HABILITADA)

    with pytest.raises(ClaveIncompatible):
        calificar(_lectura("A", "B"), clave)


# --- Recalcular ------------------------------------------------------------------------------


def test_anular_no_suma_ni_resta_y_deja_la_nota_en_la_tentativa():
    tentativa = calificar(_lectura("A", "?"), _clave("AB"))

    anulada = recalcular(tentativa, (_resolucion(2, ANULADA, None),))

    assert anulada.preguntas[1].veredicto == ANULADA
    assert anulada.puntos_posibles == tentativa.puntos_posibles
    assert anulada.nota_en_decimas == tentativa.nota_en_decimas == 25
    assert not anulada.provisional


def test_resolver_como_incorrecta_guarda_la_opcion_que_reconoce_el_profesor():
    tentativa = calificar(_lectura("AC"), _clave("A"))

    resuelta = recalcular(tentativa, (_resolucion(1, INCORRECTA, "C"),))

    assert (resuelta.preguntas[0].veredicto, resuelta.preguntas[0].marcada) == (INCORRECTA, "C")
    assert resuelta.nota_en_decimas == 0


def test_la_calificacion_anterior_queda_como_estaba():
    tentativa = calificar(_lectura("?"), _clave("A"))

    recalcular(tentativa, (_resolucion(1, CORRECTA, "A"),))

    assert tentativa.provisional
    assert tentativa.preguntas[0].veredicto == POR_REVISAR


def test_resolver_preguntas_no_quita_lo_provisional_de_un_codigo_incompleto():
    tentativa = calificar(_lectura("?", codigo=CODIGO_INCOMPLETO), _clave("A"))

    resuelta = recalcular(tentativa, (_resolucion(1, CORRECTA, "A"),))

    assert resuelta.provisional


@pytest.mark.parametrize(
    "resoluciones",
    [
        (_resolucion(1, CORRECTA, "A"),),
        (_resolucion(2, CORRECTA, "B"), _resolucion(2, ANULADA, None)),
        (_resolucion(5, ANULADA, None),),
        (_resolucion(2, CORRECTA, "C"),),
        (_resolucion(2, INCORRECTA, "B"),),
        (_resolucion(2, INCORRECTA, None),),
        (_resolucion(2, ANULADA, "B"),),
        (_resolucion(2, POR_REVISAR, None),),
    ],
    ids=["no-esta-en-revision", "dos-veces", "no-existe", "correcta-con-otra-opcion",
         "incorrecta-con-la-clave", "incorrecta-sin-opcion", "anulada-con-opcion",
         "veredicto-por-revisar"],
)
def test_una_resolucion_que_la_pantalla_no_ofrece_es_un_error(resoluciones):
    tentativa = calificar(_lectura("A", "?"), _clave("AB"))

    with pytest.raises(ValueError):
        recalcular(tentativa, resoluciones)


# --- Lo que el profesor vio marcado (la pantalla no conoce la clave) -------------------------


def test_la_opcion_que_vio_el_profesor_se_vuelve_veredicto_con_la_clave():
    tentativa = calificar(_lectura("?", "?", "AB"), _clave("ACD"))
    [p1, p2, p3] = tentativa.preguntas

    assert resolucion_con_opcion(p1, "A", "Docente", AHORA).veredicto == CORRECTA
    assert resolucion_con_opcion(p2, "B", "Docente", AHORA).veredicto == INCORRECTA
    assert resolucion_con_opcion(p3, None, "Docente", AHORA).veredicto == ANULADA
    with pytest.raises(ValueError):
        resolucion_con_opcion(p1, "E", "Docente", AHORA)


def test_la_ultima_resolucion_de_cada_pregunta_manda():
    """Cambiar de opinión es otra resolución: la anterior queda como historia."""
    tentativa = calificar(_lectura("?", "?", "C"), _clave("ABC"))
    resoluciones = (
        _resolucion(1, INCORRECTA, "B"),
        _resolucion(2, CORRECTA, "B"),
        _resolucion(1, CORRECTA, "A"),
    )

    vigentes = resoluciones_vigentes(tentativa, resoluciones)

    assert [(r.numero, r.veredicto, r.opcion) for r in vigentes] == [
        (1, CORRECTA, "A"),
        (2, CORRECTA, "B"),
    ]
    nota = nota_vigente(tentativa, resoluciones)
    assert (nota.nota_en_decimas, nota.provisional) == (50, False)


def test_una_resolucion_de_una_pregunta_que_ya_no_esta_en_revision_no_aplica():
    """La hoja se volvió a leer y la pregunta 1 ahora se ve bien: lo que decidió el profesor
    antes queda como historia y no choca con la lectura nueva."""
    releida = calificar(_lectura("A", "?"), _clave("AB"))

    vigentes = resoluciones_vigentes(releida, (_resolucion(1, INCORRECTA, "C"),))

    assert vigentes == ()
    assert nota_vigente(releida, (_resolucion(1, INCORRECTA, "C"),)) == releida


def test_el_veredicto_se_deduce_otra_vez_con_la_clave_vigente():
    """El profesor vio una B. Si después se corrige la clave y la correcta pasa a ser B, la
    pregunta cuenta como correcta sin que el profesor la resuelva de nuevo."""
    con_la_clave_corregida = calificar(_lectura("?"), _clave("B"))

    [vigente] = resoluciones_vigentes(con_la_clave_corregida, (_resolucion(1, INCORRECTA, "B"),))

    assert (vigente.veredicto, vigente.opcion) == (CORRECTA, "B")
