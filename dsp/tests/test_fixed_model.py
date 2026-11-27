"""Pruebas del modelo bit-exacto en punto fijo.

Revisan que el modelo se comporte como debe hacerlo el hardware: que se
acerque a la versión en punto flotante, que las etapas identidad y el bypass
no alteren la señal, que la saturación nunca "dé la vuelta", que el
acumulador no se desborde, que los canales sean independientes y que, gracias
a la realimentación del error de redondeo, el filtro vuelva a 0 en silencio.

Uso:
    pytest dsp -v
"""

import numpy as np
import pytest

from filter_config import FILTER_NAMES, SAMPLE_RATES
from filter_wav import apply_filter
from fixed_coefficients import FixedBiquad, build_fixed_filters, to_float_stage
from fixed_model import (
    DEFAULT_STATE_BITS,
    FixedBiquadCascade,
    FixedBiquadStage,
    datapath_widths,
    process_fixed,
)
from fixed_point import COEF_FORMAT

ONE = 1 << COEF_FORMAT.frac_bits                 # 1.0 en Q3.15
IDENTITY = FixedBiquad(ONE, 0, 0, 0, 0)
GAIN_2 = FixedBiquad(2 * ONE, 0, 0, 0, 0)        # multiplica por 2
STATE_BITS = (16, 24)
ALL_FILTERS = [(fs, name) for fs in SAMPLE_RATES for name in FILTER_NAMES]

# Error máximo permitido contra el flotante (en LSB de 16 bits), con la
# realimentación del error activada (valor por defecto del modelo)
MAX_ERROR_LSB = {16: 8, 24: 1}

def state_of(stage: FixedBiquadStage) -> tuple[int, ...]:
    return (stage.x1, stage.x2, stage.y1, stage.y2, stage.residue)

def noise(n: int, amplitude: float, seed: int = 0) -> np.ndarray:
    """Ruido uniforme reproducible en int16."""
    rng = np.random.default_rng(seed)
    return np.round(rng.uniform(-amplitude, amplitude, n) * 32767).astype(np.int16)

# Ruta de datos
@pytest.mark.parametrize("state_bits, product, acc", [(16, 34, 40), (24, 42, 48)])
def test_anchos_de_la_ruta_de_datos(state_bits, product, acc):
    widths = datapath_widths(state_bits)
    assert widths["producto"] == product
    assert widths["acumulador"] == acc

def test_precision_por_defecto_es_24_bits():
    # Decisión de diseño tomada con measure_fixed.py; el RTL debe usar lo mismo
    assert DEFAULT_STATE_BITS == 24
    assert FixedBiquadCascade([IDENTITY]).state_bits == 24
    widths = datapath_widths(DEFAULT_STATE_BITS)
    assert (widths["producto"], widths["acumulador"]) == (42, 48)

def test_estado_menor_a_16_bits_no_permitido():
    with pytest.raises(ValueError):
        FixedBiquadCascade([IDENTITY], state_bits=12)

def test_muestra_fuera_de_rango_lanza_error():
    cascade = FixedBiquadCascade([IDENTITY])
    with pytest.raises(OverflowError):
        cascade.process_sample(40000)

# Comparación contra el punto flotante
@pytest.mark.parametrize("state_bits", STATE_BITS)
@pytest.mark.parametrize("fs, name", ALL_FILTERS)
def test_cercano_al_flotante(fs, name, state_bits):
    # Mismos coeficientes cuantizados en ambos: solo se mide el efecto de
    # calcular en punto fijo. Amplitud moderada para que nada sature.
    x = noise(3000, amplitude=0.4, seed=fs)
    stages = build_fixed_filters(fs)[name]
    reference, _ = apply_filter(x, [to_float_stage(s) for s in stages])

    y, saturations = process_fixed(x, stages, state_bits)

    assert saturations == 0
    error = np.max(np.abs(y.astype(int) - reference.astype(int)))
    assert error <= MAX_ERROR_LSB[state_bits]

# Identidad y bypass
@pytest.mark.parametrize("state_bits", STATE_BITS)
def test_etapas_identidad_no_alteran_la_senal(state_bits):
    x = np.concatenate([noise(2000, 1.0), [32767, -32768, 0, 1, -1]]).astype(np.int16)
    y, saturations = process_fixed(x, [IDENTITY] * 3, state_bits)
    np.testing.assert_array_equal(y, x)
    assert saturations == 0

def test_bypass_no_altera_la_senal_ni_el_estado():
    cascade = FixedBiquadCascade(build_fixed_filters(44100)["equalizer"])
    cascade.bypass = True
    x = noise(500, 1.0)
    y = [cascade.process_sample(int(s)) for s in x]
    assert y == x.tolist()
    for stage in cascade.stages:
        assert state_of(stage) == (0, 0, 0, 0, 0)

# Estado: reinicio, cambio de filtro y repetibilidad
def test_reinicio_pone_el_estado_en_cero():
    cascade = FixedBiquadCascade(build_fixed_filters(44100)["highpass"])
    for s in noise(100, 0.5):
        cascade.process_sample(int(s))
    cascade.reset()
    for stage in cascade.stages:
        assert state_of(stage) == (0, 0, 0, 0, 0)

def test_cambio_de_filtro_reinicia_el_estado():
    filters = build_fixed_filters(44100)
    cascade = FixedBiquadCascade(filters["highpass"])
    for s in noise(100, 0.5):
        cascade.process_sample(int(s))
    cascade.load_coefficients(filters["bandpass"])
    assert [stage.coefs for stage in cascade.stages] == filters["bandpass"]
    for stage in cascade.stages:
        assert state_of(stage) == (0, 0, 0, 0, 0)

def test_misma_entrada_misma_salida_despues_de_reiniciar():
    cascade = FixedBiquadCascade(build_fixed_filters(16000)["equalizer"])
    x = noise(1000, 0.5)
    first = [cascade.process_sample(int(s)) for s in x]
    cascade.reset()
    second = [cascade.process_sample(int(s)) for s in x]
    assert first == second

# Saturación y desborde
@pytest.mark.parametrize("state_bits", STATE_BITS)
def test_saturacion_no_da_la_vuelta(state_bits):
    # Ganancia 2 con entrada fuerte: la salida debe quedarse en el límite,
    # nunca cambiar de signo
    x = np.array([30000, -30000, 20000, -20000, 100, -100], dtype=np.int16)
    y, saturations = process_fixed(x, [GAIN_2, IDENTITY, IDENTITY], state_bits)
    assert y.tolist() == [32767, -32768, 32767, -32768, 200, -200]
    assert saturations == 4

def test_saturacion_cuenta_por_etapa():
    stage = FixedBiquadStage(GAIN_2, state_bits=16)
    stage.process(30000)
    stage.process(100)
    assert stage.saturations == 1

EXTREME_INPUTS = {
    "cuadrada en Nyquist": np.tile(np.array([32767, -32768], dtype=np.int16), 2000),
    "escalón máximo": np.concatenate([np.zeros(10), np.full(3000, 32767)]).astype(np.int16),
    "escalón mínimo": np.concatenate([np.zeros(10), np.full(3000, -32768)]).astype(np.int16),
    "ruido a escala completa": noise(4000, 1.0, seed=7),
}

@pytest.mark.parametrize("state_bits", STATE_BITS)
@pytest.mark.parametrize("signal_name", EXTREME_INPUTS)
@pytest.mark.parametrize("fs, name", ALL_FILTERS)
def test_acumulador_no_se_desborda_con_entradas_extremas(fs, name, signal_name, state_bits):
    # Si alguna suma parcial no cupiera en el acumulador, el modelo lanzaría
    # OverflowError. Puede haber saturación, pero nunca desborde.
    y, _ = process_fixed(EXTREME_INPUTS[signal_name], build_fixed_filters(fs)[name], state_bits)
    assert y.dtype == np.int16

# Realimentación del error de redondeo y silencio
def signal_then_silence(fs: int) -> np.ndarray:
    return np.concatenate([noise(2000, 0.5, seed=fs), np.zeros(8000)]).astype(np.int16)

@pytest.mark.parametrize("state_bits", STATE_BITS)
@pytest.mark.parametrize("fs, name", ALL_FILTERS)
def test_vuelve_exactamente_a_cero_en_silencio(fs, name, state_bits):
    y, _ = process_fixed(signal_then_silence(fs), build_fixed_filters(fs)[name], state_bits)
    # Las últimas 2000 muestras deben ser exactamente 0: sin ciclos límite
    assert not np.any(y[-2000:])

def test_sin_realimentacion_el_ecualizador_se_queda_pegado():
    # Documenta el problema que resuelve la realimentación: sin ella, el
    # low-shelf (polo en 0.983) deja la salida trabada en un valor constante
    y, _ = process_fixed(signal_then_silence(44100), build_fixed_filters(44100)["equalizer"],
                         state_bits=16, error_feedback=False)
    assert abs(int(y[-1])) > 100
    assert len(set(y[-2000:].tolist())) == 1   # valor constante

def test_residuo_cabe_en_15_bits():
    # El modelo lanzaría OverflowError si el residuo no cupiera; además se
    # revisa su rango esperado [-2^14, 2^14)
    stage = FixedBiquadStage(build_fixed_filters(44100)["equalizer"][0], state_bits=16)
    for s in noise(5000, 1.0, seed=11):
        stage.process(int(s))
        assert -(1 << 14) <= stage.residue < (1 << 14)

def test_identidad_no_genera_residuo():
    stage = FixedBiquadStage(IDENTITY, state_bits=16)
    for s in noise(500, 1.0):
        stage.process(int(s))
        assert stage.residue == 0

# Estéreo
def test_canales_independientes():
    stages = build_fixed_filters(44100)["equalizer"]
    left = noise(1000, 0.5, seed=1)
    right = noise(1000, 0.5, seed=2)

    stereo, _ = process_fixed(np.column_stack([left, right]), stages)
    mono_left, _ = process_fixed(left, stages)
    mono_right, _ = process_fixed(right, stages)

    assert stereo.shape == (1000, 2)
    np.testing.assert_array_equal(stereo[:, 0], mono_left)
    np.testing.assert_array_equal(stereo[:, 1], mono_right)