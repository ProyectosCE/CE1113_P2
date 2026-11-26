"""Cálculo de coeficientes de filtros biquad según el Audio EQ Cookbook.

Referencia: R. Bristow-Johnson, "Cookbook formulae for audio EQ biquad
filter coefficients" (W3C Audio EQ Cookbook).

Un biquad es un filtro IIR de segundo orden con función de transferencia

            b0 + b1*z^-1 + b2*z^-2
    H(z) = ------------------------
             1 + a1*z^-1 + a2*z^-2

Todos los coeficientes se devuelven normalizados (a0 = 1), así que la
ecuación en diferencias que implementará el hardware es:

    y[n] = b0*x[n] + b1*x[n-1] + b2*x[n-2] - a1*y[n-1] - a2*y[n-2]

Uso rápido:
    python dsp/model/biquad_design.py
"""

import math
from typing import NamedTuple

class Biquad(NamedTuple):
    """Coeficientes normalizados de un biquad (a0 = 1)."""

    b0: float
    b1: float
    b2: float
    a1: float
    a2: float

    @property
    def b(self) -> list[float]:
        """Numerador en el formato de scipy.signal."""
        return [self.b0, self.b1, self.b2]

    @property
    def a(self) -> list[float]:
        """Denominador en el formato de scipy.signal (incluye a0 = 1)."""
        return [1.0, self.a1, self.a2]

# Funciones auxiliares
def _check_frequency(fs: float, f0: float) -> None:
    """Verifica que la frecuencia esté entre 0 y la frecuencia de Nyquist."""
    if fs <= 0:
        raise ValueError(f"fs debe ser positiva (fs={fs})")
    if not 0 < f0 < fs / 2:
        raise ValueError(
            f"f0={f0} Hz debe estar entre 0 y fs/2={fs / 2} Hz (Nyquist)"
        )


def _normalize(b0, b1, b2, a0, a1, a2) -> Biquad:
    """Divide todos los coeficientes entre a0 para que a0 = 1."""
    return Biquad(b0 / a0, b1 / a0, b2 / a0, a1 / a0, a2 / a0)

# Filtros del Cookbook
def highpass(fs: float, f0: float, q: float = 1 / math.sqrt(2)) -> Biquad:
    """Pasa-altos de segundo orden.

    fs: frecuencia de muestreo (Hz)
    f0: frecuencia de corte (Hz)
    q:  factor de calidad; 1/sqrt(2) ~ 0.707 da un Butterworth
    """
    _check_frequency(fs, f0)
    w0 = 2 * math.pi * f0 / fs
    cos_w0 = math.cos(w0)
    alpha = math.sin(w0) / (2 * q)

    return _normalize(
        b0=(1 + cos_w0) / 2,
        b1=-(1 + cos_w0),
        b2=(1 + cos_w0) / 2,
        a0=1 + alpha,
        a1=-2 * cos_w0,
        a2=1 - alpha,
    )

def bandpass(fs: float, f_low: float, f_high: float) -> Biquad:
    """Pasa-banda de segundo orden con ganancia de 0 dB en el centro.

    Se define por sus dos frecuencias de corte (-3 dB). La frecuencia
    central es la media geométrica sqrt(f_low * f_high) y el ancho de
    banda se expresa en octavas, como indica el Cookbook.
    """
    if not 0 < f_low < f_high:
        raise ValueError(f"Se requiere 0 < f_low < f_high ({f_low}, {f_high})")
    _check_frequency(fs, f_high)

    f0 = math.sqrt(f_low * f_high)
    bw_octaves = math.log2(f_high / f_low)

    w0 = 2 * math.pi * f0 / fs
    sin_w0 = math.sin(w0)
    cos_w0 = math.cos(w0)
    alpha = sin_w0 * math.sinh(math.log(2) / 2 * bw_octaves * w0 / sin_w0)

    return _normalize(
        b0=alpha,
        b1=0.0,
        b2=-alpha,
        a0=1 + alpha,
        a1=-2 * cos_w0,
        a2=1 - alpha,
    )

def peaking(fs: float, f0: float, gain_db: float, q: float = 1.0) -> Biquad:
    """Filtro peaking (campana): refuerza o atenúa alrededor de f0.

    gain_db > 0 refuerza, gain_db < 0 atenúa, 0 deja la señal igual.
    """
    _check_frequency(fs, f0)
    amp = 10 ** (gain_db / 40)
    w0 = 2 * math.pi * f0 / fs
    cos_w0 = math.cos(w0)
    alpha = math.sin(w0) / (2 * q)

    return _normalize(
        b0=1 + alpha * amp,
        b1=-2 * cos_w0,
        b2=1 - alpha * amp,
        a0=1 + alpha / amp,
        a1=-2 * cos_w0,
        a2=1 - alpha / amp,
    )

def lowshelf(fs: float, f0: float, gain_db: float, slope: float = 1.0) -> Biquad:
    """Low-shelf: cambia la ganancia de las frecuencias por debajo de f0.

    f0 es el punto medio de la transición (mitad de la ganancia en dB).
    slope = 1 es la pendiente más pronunciada sin sobrepicos.
    """
    _check_frequency(fs, f0)
    amp = 10 ** (gain_db / 40)
    w0 = 2 * math.pi * f0 / fs
    cos_w0 = math.cos(w0)
    alpha = math.sin(w0) / 2 * math.sqrt((amp + 1 / amp) * (1 / slope - 1) + 2)
    k = 2 * math.sqrt(amp) * alpha

    return _normalize(
        b0=amp * ((amp + 1) - (amp - 1) * cos_w0 + k),
        b1=2 * amp * ((amp - 1) - (amp + 1) * cos_w0),
        b2=amp * ((amp + 1) - (amp - 1) * cos_w0 - k),
        a0=(amp + 1) + (amp - 1) * cos_w0 + k,
        a1=-2 * ((amp - 1) + (amp + 1) * cos_w0),
        a2=(amp + 1) + (amp - 1) * cos_w0 - k,
    )

def highshelf(fs: float, f0: float, gain_db: float, slope: float = 1.0) -> Biquad:
    """High-shelf: cambia la ganancia de las frecuencias por encima de f0.

    f0 es el punto medio de la transición (mitad de la ganancia en dB).
    slope = 1 es la pendiente más pronunciada sin sobrepicos.
    """
    _check_frequency(fs, f0)
    amp = 10 ** (gain_db / 40)
    w0 = 2 * math.pi * f0 / fs
    cos_w0 = math.cos(w0)
    alpha = math.sin(w0) / 2 * math.sqrt((amp + 1 / amp) * (1 / slope - 1) + 2)
    k = 2 * math.sqrt(amp) * alpha

    return _normalize(
        b0=amp * ((amp + 1) + (amp - 1) * cos_w0 + k),
        b1=-2 * amp * ((amp - 1) + (amp + 1) * cos_w0),
        b2=amp * ((amp + 1) + (amp - 1) * cos_w0 - k),
        a0=(amp + 1) - (amp - 1) * cos_w0 + k,
        a1=2 * ((amp - 1) - (amp + 1) * cos_w0),
        a2=(amp + 1) - (amp - 1) * cos_w0 - k,
    )

# Demostración
def _print_biquad(name: str, coeffs: Biquad) -> None:
    values = "  ".join(f"{field}={value:+.6f}" for field, value in coeffs._asdict().items())
    print(f"{name:<22} {values}")


if __name__ == "__main__":
    fs = 44100
    print(f"Coeficientes de ejemplo a fs = {fs} Hz\n")
    _print_biquad("Pasa-altos 800 Hz", highpass(fs, 800))
    _print_biquad("Pasa-banda 300-3000 Hz", bandpass(fs, 300, 3000))
    _print_biquad("Low-shelf 200 Hz +6 dB", lowshelf(fs, 200, 6))
    _print_biquad("Peaking 1 kHz -3 dB", peaking(fs, 1000, -3))
    _print_biquad("High-shelf 3 kHz +4 dB", highshelf(fs, 3000, 4))