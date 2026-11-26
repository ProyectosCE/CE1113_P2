"""Pruebas de los filtros diseñados en punto flotante.

Revisan, para cada filtro y cada frecuencia de muestreo:
  - que todas las etapas sean estables,
  - que la respuesta en frecuencia sea la esperada,
  - que la estructura sea la que procesa el hardware (3 etapas).

Uso:
    pytest dsp -v
"""

import numpy as np
import pytest
from scipy import signal

from biquad_design import Biquad, highpass
from filter_config import (
    FILTER_NAMES,
    HIGHPASS,
    IDENTITY,
    NUM_STAGES,
    SAMPLE_RATES,
    build_filters,
)


# -----------------------------------------------------------------------------
# Funciones auxiliares
# -----------------------------------------------------------------------------
def gain_db(stages: list[Biquad], f: float, fs: float) -> float:
    """Ganancia en dB de una cascada de biquads a la frecuencia f."""
    h = 1.0 + 0j
    for stage in stages:
        _, hs = signal.freqz(stage.b, stage.a, worN=[f], fs=fs)
        h *= hs[0]
    return 20 * np.log10(abs(h))


def is_stable(stage: Biquad) -> bool:
    """Condición de estabilidad de un biquad (polos dentro del círculo unitario)."""
    return abs(stage.a2) < 1 and abs(stage.a1) < 1 + stage.a2


def pole_radius(stage: Biquad) -> float:
    """Distancia del polo más lejano al origen (debe ser menor que 1)."""
    return float(max(abs(np.roots(stage.a))))


# Todas las combinaciones (fs, filtro) para parametrizar las pruebas
ALL_FILTERS = [(fs, name) for fs in SAMPLE_RATES for name in FILTER_NAMES]


# Estructura
@pytest.mark.parametrize("fs, name", ALL_FILTERS)
def test_numero_de_etapas(fs, name):
    assert len(build_filters(fs)[name]) == NUM_STAGES


@pytest.mark.parametrize("fs", SAMPLE_RATES)
def test_etapas_de_relleno_son_identidad(fs):
    filters = build_filters(fs)
    for name in ("highpass", "bandpass"):
        assert filters[name][1:] == [IDENTITY] * (NUM_STAGES - 1)


def test_fs_no_soportada():
    with pytest.raises(ValueError):
        build_filters(22050)


# Estabilidad
@pytest.mark.parametrize("fs, name", ALL_FILTERS)
def test_estabilidad(fs, name):
    for number, stage in enumerate(build_filters(fs)[name]):
        assert is_stable(stage), f"etapa {number} inestable: {stage}"
        # La condición sobre a1 y a2 debe coincidir con el cálculo de polos
        assert pole_radius(stage) < 1


# Respuesta en frecuencia
@pytest.mark.parametrize("fs", SAMPLE_RATES)
def test_pasa_altos_igual_a_butterworth_de_scipy(fs):
    hp = highpass(fs, HIGHPASS["f0"])
    b, a = signal.butter(2, HIGHPASS["f0"], "highpass", fs=fs)
    np.testing.assert_allclose(hp.b, b, atol=1e-12)
    np.testing.assert_allclose(hp.a, a, atol=1e-12)


@pytest.mark.parametrize("fs", SAMPLE_RATES)
def test_pasa_altos(fs):
    stages = build_filters(fs)["highpass"]
    assert gain_db(stages, 800, fs) == pytest.approx(-3.01, abs=0.1)
    assert gain_db(stages, 100, fs) < -30
    assert gain_db(stages, 0.9 * fs / 2, fs) == pytest.approx(0, abs=0.5)


@pytest.mark.parametrize("fs", SAMPLE_RATES)
def test_pasa_banda(fs):
    stages = build_filters(fs)["bandpass"]
    center = np.sqrt(300 * 3000)
    assert gain_db(stages, center, fs) == pytest.approx(0, abs=0.1)
    # A 8 kHz el borde de 3000 Hz da ~-6.4 dB por estar cerca de Nyquist
    for edge in (300, 3000):
        assert -7 < gain_db(stages, edge, fs) < -2, f"borde {edge} Hz"


@pytest.mark.parametrize("fs", SAMPLE_RATES)
def test_ecualizador(fs):
    stages = build_filters(fs)["equalizer"]
    # Ganancias esperadas = ajuste de cada banda + pre-ganancia de -6 dB
    assert gain_db(stages, 20, fs) == pytest.approx(0, abs=0.5)
    assert gain_db(stages, 1000, fs) == pytest.approx(-9, abs=0.5)
    assert gain_db(stages, 0.95 * fs / 2, fs) == pytest.approx(-2, abs=0.5)