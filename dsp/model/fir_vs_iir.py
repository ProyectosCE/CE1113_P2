"""Comparación entre un pasa-altos FIR y el pasa-altos IIR (biquad).

Para cada frecuencia de muestreo se diseña el FIR más corto que cumple la
misma especificación que el biquad:
  - banda de paso: desde donde el biquad está a -1 dB, ganancia >= -1 dB
  - banda de rechazo: hasta 100 Hz, al menos la misma atenuación del biquad

Luego se comparan coeficientes, multiplicaciones, memoria, ciclos de la MAC
y retardo, y se guarda una gráfica en dsp/output/plots/.

Uso:
    python dsp/model/fir_vs_iir.py
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy import signal

from filter_config import HIGHPASS, SAMPLE_RATES, build_filters

OUTPUT_DIR = Path(__file__).resolve().parents[1] / "output" / "plots"

STOPBAND_EDGE_HZ = 100.0     # borde de la banda de rechazo
DELAY_FREQ_HZ = 2000.0       # frecuencia a la que se mide el retardo
PASSBAND_DROP_DB = -1.0      # caída máxima permitida en la banda de paso
CLOCK_HZ = 50e6              # reloj del FPGA
MAX_TAPS = 4001              # límite de búsqueda

# Especificación a partir del biquad
def magnitude_db(b, a, freqs, fs) -> np.ndarray:
    _, h = signal.freqz(b, a, worN=freqs, fs=fs)
    return 20 * np.log10(np.maximum(np.abs(h), 1e-12))


def iir_spec(fs: int) -> dict:
    """Bordes y atenuación que logra el biquad pasa-altos."""
    stage = build_filters(fs)["highpass"][0]
    freqs = np.linspace(1, 0.999 * fs / 2, 20000)
    mag = magnitude_db(stage.b, stage.a, freqs, fs)

    passband_edge = float(freqs[np.argmax(mag >= PASSBAND_DROP_DB)])
    stop_atten = float(-magnitude_db(stage.b, stage.a, [STOPBAND_EDGE_HZ], fs)[0])
    return {"stage": stage, "passband_edge": passband_edge, "stop_atten_db": stop_atten}


# Diseño del FIR
def meets_spec(taps: np.ndarray, fs: int, spec: dict) -> bool:
    stop = np.linspace(1, STOPBAND_EDGE_HZ, 200)
    passband = np.linspace(spec["passband_edge"], 0.999 * fs / 2, 400)
    stop_ok = magnitude_db(taps, [1.0], stop, fs).max() <= -spec["stop_atten_db"]
    pass_ok = abs(magnitude_db(taps, [1.0], passband, fs)).max() <= abs(PASSBAND_DROP_DB)
    return bool(stop_ok and pass_ok)


def design_fir(fs: int, spec: dict) -> np.ndarray:
    """FIR pasa-altos (ventana de Kaiser) más corto que cumple la especificación."""
    width = spec["passband_edge"] - STOPBAND_EDGE_HZ
    cutoff = (spec["passband_edge"] + STOPBAND_EDGE_HZ) / 2
    _, beta = signal.kaiserord(spec["stop_atten_db"], width / (fs / 2))

    # Un pasa-altos FIR de fase lineal necesita un número impar de coeficientes
    for numtaps in range(3, MAX_TAPS, 2):
        taps = signal.firwin(numtaps, cutoff, window=("kaiser", beta),
                             pass_zero=False, fs=fs)
        if meets_spec(taps, fs, spec):
            return taps
    raise RuntimeError(f"No se encontró un FIR con menos de {MAX_TAPS} coeficientes")


# Comparación
def compare(fs: int) -> dict:
    spec = iir_spec(fs)
    taps = design_fir(fs, spec)
    n = len(taps)
    cycles_available = int(CLOCK_HZ // fs)

    # Retardo de grupo (cuánto se atrasa la señal) en la banda de paso
    stage = spec["stage"]
    _, iir_delay = signal.group_delay((stage.b, stage.a), w=[DELAY_FREQ_HZ], fs=fs)
    _, fir_delay = signal.group_delay((taps, [1.0]), w=[DELAY_FREQ_HZ], fs=fs)

    return {
        "fs": fs,
        "spec": spec,
        "taps": taps,
        "rows": [
            ("Coeficientes", 5, n),
            ("Multiplicaciones por muestra", 5, n),
            ("Muestras guardadas (memoria)", 4, n - 1),
            ("Ciclos de MAC por muestra estéreo", 2 * 5, 2 * n),
            ("Ciclos disponibles por muestra", cycles_available, cycles_available),
            (f"Retardo a {DELAY_FREQ_HZ:.0f} Hz (ms)",
             float(iir_delay[0]) / fs * 1000, float(fir_delay[0]) / fs * 1000),
        ],
    }


def print_comparison(result: dict) -> None:
    spec = result["spec"]
    print(f"=== fs = {result['fs']} Hz ===")
    print(f"Especificación: rechazo >= {spec['stop_atten_db']:.1f} dB hasta "
          f"{STOPBAND_EDGE_HZ:.0f} Hz; paso >= {PASSBAND_DROP_DB:.0f} dB desde "
          f"{spec['passband_edge']:.0f} Hz")
    print(f"{'':<36} {'IIR biquad':>12} {'FIR':>12}")
    for label, iir, fir in result["rows"]:
        if isinstance(iir, float):
            print(f"{label:<36} {iir:>12.2f} {fir:>12.2f}")
        else:
            print(f"{label:<36} {iir:>12d} {fir:>12d}")
    print()


def plot_comparison(result: dict) -> Path:
    fs = result["fs"]
    spec = result["spec"]
    freqs = np.geomspace(20, 0.999 * fs / 2, 2000)

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(freqs, magnitude_db(spec["stage"].b, spec["stage"].a, freqs, fs),
            linewidth=2, label="IIR biquad (5 coeficientes)")
    ax.plot(freqs, magnitude_db(result["taps"], [1.0], freqs, fs),
            linestyle="--", label=f"FIR ({len(result['taps'])} coeficientes)")

    ax.axvline(HIGHPASS["f0"], color="gray", linestyle=":", linewidth=1)
    ax.axvline(STOPBAND_EDGE_HZ, color="gray", linestyle=":", linewidth=1)
    ax.axhline(-spec["stop_atten_db"], color="gray", linestyle="--", linewidth=0.8)
    ax.set_xscale("log")
    ax.set_xlim(20, fs / 2)
    ax.set_ylim(-80, 5)
    ax.set_xlabel("Frecuencia (Hz)")
    ax.set_ylabel("Magnitud (dB)")
    ax.set_title(f"Pasa-altos FIR vs IIR con la misma especificación (fs = {fs} Hz)")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend(loc="lower right")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / f"fir_vs_iir_{fs}.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    return path


def main() -> None:
    results = [compare(fs) for fs in SAMPLE_RATES]
    for result in results:
        print_comparison(result)

    path = plot_comparison(results[-1])
    print(f"Gráfica guardada en {path}")


if __name__ == "__main__":
    main()