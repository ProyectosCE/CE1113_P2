"""Pruebas de la cuantización de coeficientes a Q3.15.

Revisan que los enteros quepan en 18 bits, que se conserven exactamente las
relaciones de diseño, que los filtros sigan estables y que su respuesta
cambie muy poco respecto a la versión en punto flotante.

Uso:
    pytest dsp -v
"""

import pytest

from biquad_design import Biquad
from export_coefficients import max_response_error_db, pole_radius
from filter_config import FILTER_NAMES, SAMPLE_RATES, build_filters
from fixed_coefficients import (
    COEF_BITS,
    FixedBiquad,
    build_fixed_filters,
    coefficient_rows,
    quantize_stage,
    to_float_stage,
)
from fixed_point import COEF_FORMAT, fits, from_hex

ONE = 1 << COEF_FORMAT.frac_bits          # 1.0 en Q3.15 = 32768
IDENTITY_FIXED = FixedBiquad(ONE, 0, 0, 0, 0)
ALL_FILTERS = [(fs, name) for fs in SAMPLE_RATES for name in FILTER_NAMES]

# Rango y exactitud
@pytest.mark.parametrize("fs, name", ALL_FILTERS)
def test_todos_los_coeficientes_caben_en_18_bits(fs, name):
    for stage in build_fixed_filters(fs)[name]:
        assert all(fits(value, COEF_BITS) for value in stage)

@pytest.mark.parametrize("fs, name", ALL_FILTERS)
def test_error_de_cada_coeficiente_menor_a_un_lsb(fs, name):
    # Los redondeados directamente tienen error <= 0.5 LSB; los calculados
    # a partir de otro (por ejemplo b1 = -2*b0) pueden llegar a 1 LSB
    for stage in build_filters(fs)[name]:
        fixed, _ = quantize_stage(stage)
        for exact, rounded in zip(stage, fixed):
            assert abs(rounded - exact * ONE) <= 1

@pytest.mark.parametrize("fs", SAMPLE_RATES)
def test_etapas_identidad_exactas(fs):
    filters = build_fixed_filters(fs)
    for name in ("highpass", "bandpass"):
        assert filters[name][1:] == [IDENTITY_FIXED, IDENTITY_FIXED]

# Relaciones de diseño
@pytest.mark.parametrize("fs", SAMPLE_RATES)
def test_pasa_altos_conserva_cero_en_continua(fs):
    hp = build_fixed_filters(fs)["highpass"][0]
    assert hp.b2 == hp.b0
    assert hp.b1 == -2 * hp.b0
    assert hp.b0 + hp.b1 + hp.b2 == 0

@pytest.mark.parametrize("fs", SAMPLE_RATES)
def test_pasa_banda_conserva_sus_relaciones(fs):
    bp = build_fixed_filters(fs)["bandpass"][0]
    assert bp.b1 == 0
    assert bp.b2 == -bp.b0

@pytest.mark.parametrize("fs", SAMPLE_RATES)
def test_peaking_conserva_a1_igual_a_b1(fs):
    peaking = build_fixed_filters(fs)["equalizer"][1]
    assert peaking.a1 == peaking.b1

def test_relacion_negativa_en_un_empate_de_redondeo():
    # b0 = 1.5 LSB: redondeado por separado daría b0 = 2 y b2 = -1, porque los
    # empates van hacia +infinito. Con la relación, b2 debe ser exactamente -2.
    lsb = 1 / ONE
    stage = Biquad(b0=1.5 * lsb, b1=0.0, b2=-1.5 * lsb, a1=0.0, a2=0.0)
    fixed, relations = quantize_stage(stage)
    assert (fixed.b0, fixed.b2) == (2, -2)
    assert "b2 = -b0" in relations

def test_no_aplica_relaciones_que_no_existen():
    stage = Biquad(b0=0.5, b1=-0.9, b2=0.4, a1=-1.2, a2=0.5)
    _, relations = quantize_stage(stage)
    assert relations == []

def test_coeficiente_fuera_de_rango_lanza_error():
    with pytest.raises(OverflowError):
        quantize_stage(Biquad(b0=5.0, b1=0.0, b2=0.0, a1=0.0, a2=0.0))

# Estabilidad y respuesta
@pytest.mark.parametrize("fs, name", ALL_FILTERS)
def test_estable_despues_de_cuantizar(fs, name):
    for original in build_filters(fs)[name]:
        fixed, _ = quantize_stage(original)
        radius = pole_radius(to_float_stage(fixed))
        assert radius < 1
        # El redondeo apenas mueve los polos
        assert radius == pytest.approx(pole_radius(original), abs=1e-4)

@pytest.mark.parametrize("fs, name", ALL_FILTERS)
def test_respuesta_cuantizada_cercana_a_la_original(fs, name):
    original = build_filters(fs)[name]
    quantized = [to_float_stage(s) for s in build_fixed_filters(fs)[name]]
    # -40 dB = la respuesta cambia como máximo un 1 % de la escala completa
    assert max_response_error_db(original, quantized, fs) < -40

# Tabla exportada
def test_tabla_tiene_todos_los_coeficientes():
    rows = coefficient_rows()
    assert len(rows) == len(SAMPLE_RATES) * len(FILTER_NAMES) * 3 * 5


def test_hexadecimales_de_la_tabla_coinciden_con_el_entero():
    for row in coefficient_rows():
        assert from_hex(row["hex18"], 18) == row["entero"]
        assert from_hex(row["hex32"], 32) == row["entero"]   # extendido en signo