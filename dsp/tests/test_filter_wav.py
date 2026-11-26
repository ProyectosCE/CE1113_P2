"""Pruebas de la aplicación de los filtros a señales de audio.

Usan tonos puros para comprobar que cada filtro atenúa o deja pasar las
frecuencias esperadas, y revisan la lectura de WAV y la saturación.

Uso:
    pytest dsp -v
"""

import numpy as np
import pytest
from scipy.io import wavfile

from filter_config import IDENTITY, apply_gain, build_filters
from filter_wav import (
    INT16_MAX,
    INT16_SCALE,
    apply_filter,
    generate_test_signal,
    read_wav,
    rms_db,
)

FS = 44100


def tone(f: float, amplitude: float = 0.5, seconds: float = 1.0, fs: int = FS) -> np.ndarray:
    """Tono puro en int16."""
    t = np.arange(int(fs * seconds)) / fs
    return np.round(amplitude * np.sin(2 * np.pi * f * t) * INT16_SCALE).astype(np.int16)


def gain_on_tone(name: str, f: float, fs: int = FS) -> float:
    """Cambio de nivel (dB) de un tono al pasar por un filtro.

    Se descarta la primera décima de segundo, mientras el filtro se estabiliza.
    """
    x = tone(f, fs=fs)
    y, _ = apply_filter(x, build_filters(fs)[name])
    skip = fs // 10
    return rms_db(y[skip:]) - rms_db(x[skip:])


# Efecto de cada filtro sobre tonos grave (100 Hz), medio (1 kHz) y agudo (6 kHz)
def test_pasa_altos_sobre_tonos():
    assert gain_on_tone("highpass", 100) < -30      # quita el grave
    assert gain_on_tone("highpass", 6000) > -0.5    # deja el agudo


def test_pasa_banda_sobre_tonos():
    assert gain_on_tone("bandpass", 1000) > -0.5    # deja el medio
    assert gain_on_tone("bandpass", 100) < -8       # atenúa el grave
    assert gain_on_tone("bandpass", 6000) < -6      # atenúa el agudo


def test_ecualizador_sobre_tonos():
    assert gain_on_tone("equalizer", 1000) == pytest.approx(-9, abs=0.5)

# Formato y saturación
def test_estereo_conserva_forma_y_canales_independientes():
    left = tone(100)
    right = tone(6000)
    stereo = np.column_stack([left, right])

    y, _ = apply_filter(stereo, build_filters(FS)["highpass"])

    assert y.shape == stereo.shape
    assert y.dtype == np.int16
    # Cada canal se filtra por separado: el resultado coincide con filtrarlo solo
    y_left, _ = apply_filter(left, build_filters(FS)["highpass"])
    np.testing.assert_array_equal(y[:, 0], y_left)


def test_saturacion_se_cuenta_y_se_recorta():
    loud = tone(1000, amplitude=0.9)
    plus_6db = [apply_gain(IDENTITY, 6.0)]   # duplica la amplitud: 0.9 -> 1.8

    y, clipped = apply_filter(loud, plus_6db)

    assert clipped > 0
    assert y.max() == INT16_MAX


def test_filtros_sin_saturacion_con_senal_de_prueba():
    x = generate_test_signal()
    for name, stages in build_filters(FS).items():
        _, clipped = apply_filter(x, stages)
        assert clipped == 0, name

# Lectura de WAV
def test_lee_wav_valido(tmp_path):
    path = tmp_path / "valido.wav"
    wavfile.write(path, FS, tone(1000))
    fs, samples = read_wav(path)
    assert fs == FS
    assert samples.dtype == np.int16


def test_rechaza_fs_no_soportada(tmp_path):
    path = tmp_path / "48k.wav"
    wavfile.write(path, 48000, tone(1000, fs=48000))
    with pytest.raises(ValueError, match="no soportada"):
        read_wav(path)


def test_rechaza_wav_que_no_es_de_16_bits(tmp_path):
    path = tmp_path / "float.wav"
    wavfile.write(path, FS, np.zeros(1000, dtype=np.float32))
    with pytest.raises(ValueError, match="16 bits"):
        read_wav(path)