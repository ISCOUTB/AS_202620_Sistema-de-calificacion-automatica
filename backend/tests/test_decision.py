"""Las decisiones de la lectura (RF-03, EC-02): de relleno a tipo de marca, y de burbujas a una
pregunta o al código del estudiante.

Se prueban con números escritos a mano, sin imágenes: es lo que permite separar `decision` de
`vision`. Los cortes de relleno son supuestos hasta la hoja del prototipo (R-05); estas pruebas
fijan la regla, no los números, salvo donde el número es la regla."""

import itertools

import pytest

from infraestructura.modelo import (
    BORRON,
    CODIGO_COMPLETO,
    CODIGO_INCOMPLETO,
    COMPLETA,
    DOBLE_MARCA,
    DUDOSA,
    SIN_MARCA,
    TENUE,
    UNA_MARCA,
    VACIA,
    LecturaDeBurbuja,
)
from omr.decision import (
    CORTE_DE_INTENCION_POR_OMISION,
    DISPERSION_MINIMA_PARA_DUDAR,
    RELLENO_MAXIMO_DE_UNA_VACIA,
    RELLENO_MINIMO_DE_UNA_COMPLETA,
    clasificar_burbuja,
    comprobar_corte_de_intencion,
    comprobar_umbral_de_confianza,
    decidir_codigo,
    decidir_pregunta,
)

UMBRAL = 70


def _fila(*confianzas: int) -> tuple[LecturaDeBurbuja, ...]:
    """Una fila de burbujas A, B, C... con esas confianzas. El tipo y el relleno no cuentan para
    decidir: la regla solo mira la confianza."""
    return tuple(
        LecturaDeBurbuja(opcion, confianza / 100, COMPLETA, confianza)
        for opcion, confianza in zip("ABCD", confianzas)
    )


def _columna(digito: int | None) -> tuple[LecturaDeBurbuja, ...]:
    """Una columna del código con ese dígito marcado, o en blanco si es None."""
    return tuple(
        LecturaDeBurbuja(str(d), 0.0, VACIA, 95 if d == digito else 0) for d in range(10)
    )


# --- Una burbuja -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "relleno, tipo",
    [
        (0.0, VACIA),
        (RELLENO_MAXIMO_DE_UNA_VACIA, VACIA),
        (0.15, BORRON),
        (0.40, TENUE),
        (RELLENO_MINIMO_DE_UNA_COMPLETA, COMPLETA),
        (1.0, COMPLETA),
    ],
)
def test_el_tipo_de_marca_sale_del_relleno(relleno, tipo):
    assert clasificar_burbuja("A", relleno).tipo == tipo


def test_la_confianza_crece_con_el_relleno_y_va_de_0_a_100():
    confianzas = [clasificar_burbuja("A", i / 100).confianza for i in range(101)]

    assert confianzas[0] == 0
    assert confianzas[-1] == 100
    assert confianzas == sorted(confianzas)


def test_con_el_umbral_por_omision_una_completa_se_acepta_y_una_vacia_se_descarta():
    """El tipo que ve el docente no contradice lo que el sistema decidió solo."""
    for i in range(101):
        burbuja = clasificar_burbuja("A", i / 100)
        if burbuja.tipo == COMPLETA:
            assert burbuja.confianza >= UMBRAL
        elif burbuja.tipo == VACIA:
            assert 100 - burbuja.confianza >= UMBRAL
        else:
            assert 100 - UMBRAL < burbuja.confianza < UMBRAL


@pytest.mark.parametrize("relleno", [-0.01, 1.01, float("nan")])
def test_un_relleno_fuera_de_0_a_1_es_un_error(relleno):
    with pytest.raises(ValueError):
        clasificar_burbuja("A", relleno)


@pytest.mark.parametrize(
    "dispersion, contorno",
    [(DISPERSION_MINIMA_PARA_DUDAR, 1.0), (0.0, 0.0)],
    ids=["despareja", "sin-contorno"],
)
def test_una_burbuja_que_no_se_ve_bien_no_se_da_por_vacia(dispersion, contorno):
    """R-05: el reflejo del grafito o algo que tapa la burbuja la hacen ver vacía. Con confianza
    50, la pregunta va a revisión con cualquier umbral válido."""
    burbuja = clasificar_burbuja("A", 0.0, dispersion, contorno)

    assert burbuja.confianza == 50
    assert burbuja.tipo == BORRON
    for umbral in (51, 70, 100):
        assert decidir_pregunta(1, (burbuja,) + _fila(0, 0, 0)[1:], umbral).estado == DUDOSA


def test_una_marca_completa_despareja_sigue_completa():
    assert clasificar_burbuja("A", 0.95, dispersion=0.3).tipo == COMPLETA


def test_pareja_y_con_contorno_una_burbuja_en_blanco_sigue_vacia():
    burbuja = clasificar_burbuja("A", 0.0, 0.01, 0.8)

    assert (burbuja.tipo, burbuja.confianza) == (VACIA, 0)


@pytest.mark.parametrize("dispersion", [-0.1, float("nan")])
def test_una_dispersion_negativa_es_un_error(dispersion):
    with pytest.raises(ValueError):
        clasificar_burbuja("A", 0.0, dispersion)


# --- Una pregunta ----------------------------------------------------------------------------


def test_una_sola_marca_clara_se_asigna_sola():
    pregunta = decidir_pregunta(7, _fila(2, 95, 0, 1), UMBRAL)

    assert (pregunta.numero, pregunta.estado, pregunta.opcion) == (7, UNA_MARCA, "B")
    assert pregunta.confianza == 95


def test_dos_marcas_claras_son_doble_marca_y_no_se_elige_ninguna():
    pregunta = decidir_pregunta(1, _fila(92, 0, 80, 0), UMBRAL)

    assert (pregunta.estado, pregunta.opcion, pregunta.confianza) == (DOBLE_MARCA, None, 80)


def test_una_fila_en_blanco_es_sin_marca():
    pregunta = decidir_pregunta(1, _fila(3, 0, 10, 0), UMBRAL)

    assert (pregunta.estado, pregunta.opcion, pregunta.confianza) == (SIN_MARCA, None, 90)


def test_una_marca_tenue_va_a_revision_con_la_confianza_de_esa_marca():
    """El caso de la pantalla de revisión: A tenue al 58 %, C borrón al 42 %."""
    pregunta = decidir_pregunta(1, _fila(58, 0, 42, 0), UMBRAL)

    assert (pregunta.estado, pregunta.opcion, pregunta.confianza) == (DUDOSA, None, 58)


def test_una_marca_completa_junto_a_un_borron_que_se_ve_va_a_revision():
    pregunta = decidir_pregunta(1, _fila(95, 35, 0, 0), UMBRAL)

    assert pregunta.estado == DUDOSA


def test_una_marca_completa_junto_a_un_borron_leve_se_asigna_sola():
    pregunta = decidir_pregunta(1, _fila(95, 30, 0, 0), UMBRAL)

    assert (pregunta.estado, pregunta.opcion, pregunta.confianza) == (UNA_MARCA, "A", 70)


def test_el_umbral_lo_decide_quien_llama():
    fila = _fila(65, 0, 0, 0)

    assert decidir_pregunta(1, fila, 70).estado == DUDOSA
    assert decidir_pregunta(1, fila, 60).estado == UNA_MARCA


def test_nunca_elige_entre_candidatas():
    """EC-02 recorriendo todas las combinaciones de tres burbujas, de 5 en 5, con tres umbrales:
    una `UNA_MARCA` siempre tiene la elegida por encima del umbral y todas las demás descartadas
    con la misma exigencia."""
    for umbral in (60, 70, 85):
        for confianzas in itertools.product(range(0, 101, 5), repeat=3):
            pregunta = decidir_pregunta(1, _fila(*confianzas), umbral)
            if pregunta.estado == UNA_MARCA:
                elegida = "ABC".index(pregunta.opcion)
                otras = [c for i, c in enumerate(confianzas) if i != elegida]
                assert confianzas[elegida] >= umbral
                assert all(100 - c >= umbral for c in otras)
            if pregunta.estado == DUDOSA:
                assert pregunta.confianza < umbral


@pytest.mark.parametrize("umbral", [50, 0, 101])
def test_un_umbral_que_contradice_la_regla_es_un_error(umbral):
    with pytest.raises(ValueError):
        decidir_pregunta(1, _fila(95, 0, 0, 0), umbral)


def test_el_worker_puede_comprobar_el_umbral_antes_de_leer_la_primera_hoja():
    assert comprobar_umbral_de_confianza(70) == 70
    with pytest.raises(ValueError):
        comprobar_umbral_de_confianza(50)


def test_una_fila_sin_burbujas_es_un_error():
    with pytest.raises(ValueError):
        decidir_pregunta(1, (), UMBRAL)


# --- La sugerencia de una pregunta en revisión ------------------------------------------------


def test_una_sola_marca_tenue_llega_sugerida():
    pregunta = decidir_pregunta(1, _fila(50, 0, 0, 0), UMBRAL)

    assert (pregunta.estado, pregunta.opcion, pregunta.opcion_sugerida) == (DUDOSA, None, "A")


def test_una_marca_junto_a_un_borron_bajo_el_corte_sugiere_la_marca():
    pregunta = decidir_pregunta(1, _fila(80, 35, 0, 0), UMBRAL)

    assert (pregunta.estado, pregunta.opcion_sugerida) == (DUDOSA, "A")


def test_dos_intenciones_no_sugieren_nada():
    """RF-03: el sistema nunca elige entre candidatas, ni siquiera como sugerencia."""
    tenues = decidir_pregunta(1, _fila(55, 52, 0, 0), UMBRAL)
    claras = decidir_pregunta(1, _fila(90, 85, 0, 0), UMBRAL)

    assert (tenues.estado, tenues.opcion_sugerida) == (DUDOSA, None)
    assert (claras.estado, claras.opcion_sugerida) == (DOBLE_MARCA, None)


def test_un_borron_solo_no_sugiere_nada():
    pregunta = decidir_pregunta(1, _fila(35, 0, 0, 0), UMBRAL)

    assert (pregunta.estado, pregunta.opcion_sugerida) == (DUDOSA, None)


def test_fuera_de_revision_no_hay_sugerencia():
    una = decidir_pregunta(1, _fila(90, 0, 0, 0), UMBRAL)
    ninguna = decidir_pregunta(1, _fila(0, 0, 0, 0), UMBRAL)

    assert (una.estado, una.opcion_sugerida) == (UNA_MARCA, None)
    assert (ninguna.estado, ninguna.opcion_sugerida) == (SIN_MARCA, None)


def test_el_corte_lo_decide_quien_llama():
    fila = _fila(45, 0, 0, 0)

    assert decidir_pregunta(1, fila, UMBRAL, corte_de_intencion=50).opcion_sugerida is None
    assert decidir_pregunta(1, fila, UMBRAL, corte_de_intencion=40).opcion_sugerida == "A"


def test_por_omision_el_corte_es_40():
    assert CORTE_DE_INTENCION_POR_OMISION == 40
    assert decidir_pregunta(1, _fila(40, 0, 0, 0), UMBRAL).opcion_sugerida == "A"
    assert decidir_pregunta(1, _fila(39, 0, 0, 0), UMBRAL).opcion_sugerida is None


@pytest.mark.parametrize("corte", [30, 51, 0, 100])
def test_un_corte_fuera_de_31_a_50_es_un_error(corte):
    with pytest.raises(ValueError):
        comprobar_corte_de_intencion(corte)
    with pytest.raises(ValueError):
        decidir_pregunta(1, _fila(50, 0, 0, 0), UMBRAL, corte_de_intencion=corte)


@pytest.mark.parametrize("corte", [31, 40, 50])
def test_un_corte_de_31_a_50_se_admite(corte):
    assert comprobar_corte_de_intencion(corte) == corte


def test_una_burbuja_que_no_se_ve_bien_cuenta_como_intencion_con_cualquier_corte():
    """La «D borrón (50 %)» de la foto inclinada es una marca completa con brillo: la lectura la
    deja en 50, y 50 llega a cualquier corte permitido."""
    burbuja = clasificar_burbuja("D", 0.0, DISPERSION_MINIMA_PARA_DUDAR)
    fila = _fila(0, 0, 0) + (burbuja,)

    for corte in (31, 40, 50):
        assert decidir_pregunta(1, fila, UMBRAL, corte_de_intencion=corte).opcion_sugerida == "D"


def test_la_sugerida_siempre_es_la_unica_intencion_de_la_fila():
    """Recorre todas las filas de tres burbujas, de 5 en 5: si hay sugerencia, solo esa burbuja
    llega al corte y la pregunta va a revisión."""
    for confianzas in itertools.product(range(0, 101, 5), repeat=3):
        pregunta = decidir_pregunta(1, _fila(*confianzas), UMBRAL)
        intenciones = [i for i, c in enumerate(confianzas) if c >= 40]
        if pregunta.opcion_sugerida is not None:
            assert pregunta.estado in (DUDOSA, DOBLE_MARCA)
            assert intenciones == ["ABC".index(pregunta.opcion_sugerida)]
        elif pregunta.estado == DUDOSA:
            assert len(intenciones) != 1


# --- El código del estudiante ----------------------------------------------------------------


def test_un_codigo_con_las_ocho_columnas_claras_es_completo():
    codigo = decidir_codigo(tuple(_columna(d) for d in (1, 2, 3, 4, 5, 6, 7, 8)), UMBRAL)

    assert codigo.estado == CODIGO_COMPLETO
    assert codigo.valor == "T12345678"
    assert codigo.columnas_por_revisar == ()


def test_una_columna_sin_marca_deja_el_codigo_incompleto_y_dice_cual():
    codigo = decidir_codigo(tuple(_columna(d) for d in (1, 2, None, 4, 5, 6, 7, 8)), UMBRAL)

    assert codigo.estado == CODIGO_INCOMPLETO
    assert codigo.valor == "T12?45678"
    assert codigo.columnas_por_revisar == (3,)


def _columna_con(**confianzas: int) -> tuple[LecturaDeBurbuja, ...]:
    """Una columna del código con esas confianzas por dígito (`**{"3": 50}`) y 0 en las demás."""
    return tuple(
        LecturaDeBurbuja(str(d), 0.0, VACIA, confianzas.get(str(d), 0)) for d in range(10)
    )


def _codigo_con_la_tercera(columna: tuple[LecturaDeBurbuja, ...]):
    columnas = tuple(_columna(d) for d in (1, 2, 3, 4, 5, 6, 7, 8))
    return decidir_codigo(columnas[:2] + (columna,) + columnas[3:], UMBRAL)


def test_una_columna_con_una_sola_intencion_tenue_se_acepta():
    codigo = _codigo_con_la_tercera(_columna_con(**{"3": 50}))

    assert (codigo.estado, codigo.valor, codigo.columnas_por_revisar) == (
        CODIGO_COMPLETO,
        "T12345678",
        (),
    )


def test_una_intencion_con_un_borron_al_lado_se_acepta():
    codigo = _codigo_con_la_tercera(_columna_con(**{"3": 60, "7": 35}))

    assert (codigo.estado, codigo.valor) == (CODIGO_COMPLETO, "T12345678")


def test_dos_intenciones_dejan_la_columna_por_revisar():
    codigo = _codigo_con_la_tercera(_columna_con(**{"3": 55, "7": 52}))

    assert (codigo.estado, codigo.valor, codigo.columnas_por_revisar) == (
        CODIGO_INCOMPLETO,
        "T12?45678",
        (3,),
    )


def test_un_borron_solo_deja_la_columna_por_revisar():
    codigo = _codigo_con_la_tercera(_columna_con(**{"3": 35}))

    assert (codigo.valor, codigo.columnas_por_revisar) == ("T12?45678", (3,))


def test_el_corte_del_codigo_lo_decide_quien_llama():
    columnas = (_columna_con(**{"3": 45}),) * 8

    assert decidir_codigo(columnas, UMBRAL, corte_de_intencion=50).estado == CODIGO_INCOMPLETO
    assert decidir_codigo(columnas, UMBRAL, corte_de_intencion=40).valor == "T33333333"


def test_el_codigo_del_estudiante_no_sale_en_el_repr():
    """El `repr` es lo que escribe un log descuidado (RNF-12)."""
    codigo = decidir_codigo(tuple(_columna(d) for d in (1, 2, 3, 4, 5, 6, 7, 8)), UMBRAL)

    assert "12345678" not in repr(codigo)
