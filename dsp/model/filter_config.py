"""Parámetros de los filtros de audio y generación de sus coeficientes.

Aquí se definen en un solo lugar los valores acordados para cada filtro.
Si se quiere cambiar un filtro (por ejemplo, su frecuencia de corte), se
cambia solo en este archivo y todo lo demás se recalcula.

Cada filtro se representa como una cascada de exactamente NUM_STAGES
biquads, que es lo que procesa el hardware. Los filtros que usan menos
etapas se completan con biquads identidad (dejan pasar la señal igual).

Uso rápido:
    python dsp/model/filter_config.py
"""

import math

from biquad_design import Biquad, bandpass, highpass, highshelf, lowshelf, peaking

# Configuración general
# Frecuencias de muestreo soportadas (Hz)
SAMPLE_RATES = (8000, 16000, 44100)

# Número de etapas biquad en cascada que procesa el hardware
NUM_STAGES = 3

# Biquad identidad: y[n] = x[n]
IDENTITY = Biquad(b0=1.0, b1=0.0, b2=0.0, a1=0.0, a2=0.0)

# Orden de los filtros; el índice será el número de filtro en el registro CTRL
FILTER_NAMES = ("highpass", "bandpass", "equalizer")

# Parámetros de cada filtro
# Pasa-altos Butterworth de segundo orden
HIGHPASS = {
    "f0": 800.0,                 # frecuencia de corte (Hz)
    "q": 1 / math.sqrt(2),       # ~0.707
}

# Pasa-banda (efecto teléfono / radio vieja)
BANDPASS = {
    "f_low": 300.0,              # corte inferior (Hz)
    "f_high": 3000.0,            # corte superior (Hz)
}

# Ecualizador de 3 bandas con ganancias fijas
EQUALIZER = {
    # Se aplica dentro de la primera etapa para dejar margen y evitar saturación
    "pre_gain_db": -6.0,
    "low_shelf": {"f0": 200.0, "gain_db": 6.0},
    "peaking": {"f0": 1000.0, "gain_db": -3.0, "q": 1.0},
    "high_shelf": {"f0": 3000.0, "gain_db": 4.0},
}

# Funciones auxiliares
def apply_gain(stage: Biquad, gain_db: float) -> Biquad:
    """Multiplica el numerador de un biquad por una ganancia en dB.

    Equivale a poner un amplificador antes de la etapa, pero sin agregar
    un multiplicador extra en el hardware.
    """
    gain = 10 ** (gain_db / 20)
    return stage._replace(b0=stage.b0 * gain, b1=stage.b1 * gain, b2=stage.b2 * gain)


def pad_stages(stages: list[Biquad]) -> list[Biquad]:
    """Completa una lista de etapas con biquads identidad hasta NUM_STAGES."""
    if len(stages) > NUM_STAGES:
        raise ValueError(f"Un filtro no puede tener más de {NUM_STAGES} etapas")
    return stages + [IDENTITY] * (NUM_STAGES - len(stages))


# Construcción de los filtros
def build_filters(fs: int) -> dict[str, list[Biquad]]:
    """Calcula las etapas biquad de todos los filtros para una frecuencia fs.

    Devuelve un diccionario {nombre_filtro: [etapa0, etapa1, etapa2]}
    en el orden de FILTER_NAMES.
    """
    if fs not in SAMPLE_RATES:
        raise ValueError(f"fs={fs} Hz no soportada; use una de {SAMPLE_RATES}")

    eq = EQUALIZER
    equalizer_stages = [
        apply_gain(lowshelf(fs, **eq["low_shelf"]), eq["pre_gain_db"]),
        peaking(fs, **eq["peaking"]),
        highshelf(fs, **eq["high_shelf"]),
    ]

    filters = {
        "highpass": [highpass(fs, **HIGHPASS)],
        "bandpass": [bandpass(fs, **BANDPASS)],
        "equalizer": equalizer_stages,
    }

    return {name: pad_stages(filters[name]) for name in FILTER_NAMES}

# Demostración
def _print_filters(fs: int) -> None:
    print(f"=== fs = {fs} Hz ===")
    for index, (name, stages) in enumerate(build_filters(fs).items()):
        print(f"[{index}] {name}")
        for number, stage in enumerate(stages):
            label = "identidad" if stage == IDENTITY else ""
            values = "  ".join(f"{field}={value:+.6f}" for field, value in stage._asdict().items())
            print(f"    etapa {number}: {values}  {label}")
    print()


if __name__ == "__main__":
    for fs in SAMPLE_RATES:
        _print_filters(fs)