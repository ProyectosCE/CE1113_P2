"""Gráficas de respuesta en frecuencia y diagramas de polos y ceros.

Genera en dsp/output/plots/:
  - respuesta_<filtro>.png      : magnitud de cada filtro en las 3 fs
  - ecualizador_bandas_44100.png: cada etapa del ecualizador y el total
  - polos_ceros_44100.png       : polos y ceros de cada filtro

Uso:
    python dsp/model/plot_response.py          # solo guarda los PNG
    python dsp/model/plot_response.py --show   # además abre las ventanas
"""

import argparse
from pathlib import Path

import matplotlib
import numpy as np
from scipy import signal

from biquad_design import Biquad
from filter_config import (
    BANDPASS,
    EQUALIZER,
    FILTER_NAMES,
    HIGHPASS,
    IDENTITY,
    SAMPLE_RATES,
    build_filters,
)

# Carpeta de salida: dsp/output/plots (no se sube al repositorio)
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "output" / "plots"

# Nombres legibles para títulos y leyendas
TITLES = {
    "highpass": "Pasa-altos",
    "bandpass": "Pasa-banda",
    "equalizer": "Ecualizador de 3 bandas",
}

# Frecuencias de diseño que se marcan con líneas verticales
DESIGN_FREQS = {
    "highpass": [HIGHPASS["f0"]],
    "bandpass": [BANDPASS["f_low"], BANDPASS["f_high"]],
    "equalizer": [
        EQUALIZER["low_shelf"]["f0"],
        EQUALIZER["peaking"]["f0"],
        EQUALIZER["high_shelf"]["f0"],
    ],
}

F_MIN = 20.0     # frecuencia mínima graficada (Hz)
DB_MIN = -60.0   # límite inferior del eje de magnitud (dB)
DB_MAX = 12.0    # límite superior del eje de magnitud (dB)


# Cálculos
def frequency_axis(fs: float, points: int = 2000) -> np.ndarray:
    """Frecuencias espaciadas logarítmicamente entre F_MIN y casi Nyquist."""
    return np.geomspace(F_MIN, 0.999 * fs / 2, points)


def cascade_response_db(stages: list[Biquad], freqs: np.ndarray, fs: float) -> np.ndarray:
    """Magnitud en dB de una cascada de biquads en las frecuencias dadas."""
    h = np.ones_like(freqs, dtype=complex)
    for stage in stages:
        _, hs = signal.freqz(stage.b, stage.a, worN=freqs, fs=fs)
        h *= hs
    return 20 * np.log10(np.maximum(np.abs(h), 1e-12))


def active_stages(stages: list[Biquad]) -> list[Biquad]:
    """Etapas que no son identidad (las de relleno no aportan nada)."""
    return [stage for stage in stages if stage != IDENTITY]


# Gráficas
def _format_magnitude_axis(ax, name: str) -> None:
    for f in DESIGN_FREQS.get(name, []):
        ax.axvline(f, color="gray", linestyle=":", linewidth=1)
    ax.axhline(-3, color="gray", linestyle="--", linewidth=0.8)
    ax.set_xscale("log")
    ax.set_xlim(F_MIN, max(SAMPLE_RATES) / 2)
    ax.set_ylim(DB_MIN, DB_MAX)
    ax.set_xlabel("Frecuencia (Hz)")
    ax.set_ylabel("Magnitud (dB)")
    ax.grid(True, which="both", alpha=0.3)
    ax.legend(loc="lower right")


def plot_filter_response(plt, name: str) -> Path:
    """Respuesta de un filtro en todas las frecuencias de muestreo."""
    fig, ax = plt.subplots(figsize=(9, 5))
    for fs in SAMPLE_RATES:
        freqs = frequency_axis(fs)
        stages = build_filters(fs)[name]
        ax.plot(freqs, cascade_response_db(stages, freqs, fs), label=f"fs = {fs} Hz")

    ax.set_title(f"{TITLES[name]}: respuesta en frecuencia")
    _format_magnitude_axis(ax, name)

    path = OUTPUT_DIR / f"respuesta_{name}.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    return path


def plot_equalizer_bands(plt, fs: int = 44100) -> Path:
    """Cada etapa del ecualizador por separado y la respuesta total."""
    stages = build_filters(fs)["equalizer"]
    labels = [
        f"Low-shelf {EQUALIZER['low_shelf']['f0']:.0f} Hz "
        f"(incluye pre-ganancia {EQUALIZER['pre_gain_db']:+.0f} dB)",
        f"Peaking {EQUALIZER['peaking']['f0']:.0f} Hz",
        f"High-shelf {EQUALIZER['high_shelf']['f0']:.0f} Hz",
    ]
    freqs = frequency_axis(fs)

    fig, ax = plt.subplots(figsize=(9, 5))
    for stage, label in zip(stages, labels):
        ax.plot(freqs, cascade_response_db([stage], freqs, fs), linestyle="--", label=label)
    ax.plot(freqs, cascade_response_db(stages, freqs, fs), color="black", linewidth=2, label="Total")

    ax.set_title(f"Ecualizador por etapas (fs = {fs} Hz)")
    _format_magnitude_axis(ax, "equalizer")
    ax.set_ylim(-15, 10)
    ax.legend(loc="lower left")

    path = OUTPUT_DIR / f"ecualizador_bandas_{fs}.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    return path


def plot_pole_zero(plt, fs: int = 44100) -> Path:
    """Diagrama de polos y ceros de cada filtro con el círculo unitario."""
    filters = build_filters(fs)
    fig, axes = plt.subplots(1, len(FILTER_NAMES), figsize=(15, 5))
    theta = np.linspace(0, 2 * np.pi, 400)

    for ax, name in zip(axes, FILTER_NAMES):
        ax.plot(np.cos(theta), np.sin(theta), color="gray", linewidth=1)
        ax.axhline(0, color="gray", linewidth=0.5)
        ax.axvline(0, color="gray", linewidth=0.5)

        for number, stage in enumerate(active_stages(filters[name])):
            zeros = np.roots(stage.b)
            poles = np.roots(stage.a)
            color = f"C{number}"
            ax.scatter(zeros.real, zeros.imag, marker="o", facecolors="none",
                       edgecolors=color, s=60, label=f"etapa {number}: ceros")
            ax.scatter(poles.real, poles.imag, marker="x", color=color,
                       s=60, label=f"etapa {number}: polos")

        ax.set_title(TITLES[name])
        ax.set_xlabel("Parte real")
        ax.set_ylabel("Parte imaginaria")
        ax.set_aspect("equal")
        ax.set_xlim(-1.3, 1.3)
        ax.set_ylim(-1.3, 1.3)
        ax.grid(True, alpha=0.3)
        ax.legend(loc="lower left", fontsize=7)

    fig.suptitle(f"Polos (x) y ceros (o), fs = {fs} Hz: estable si los polos están dentro del círculo")
    path = OUTPUT_DIR / f"polos_ceros_{fs}.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    return path


# Programa principal
def main() -> None:
    parser = argparse.ArgumentParser(description="Genera las gráficas de los filtros")
    parser.add_argument("--show", action="store_true", help="abre las gráficas en ventanas")
    args = parser.parse_args()

    # Sin --show se usa un backend que no abre ventanas (sirve sin pantalla)
    if not args.show:
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    paths = [plot_filter_response(plt, name) for name in FILTER_NAMES]
    paths.append(plot_equalizer_bands(plt))
    paths.append(plot_pole_zero(plt))

    print("Gráficas generadas:")
    for path in paths:
        print(f"  {path}")

    if args.show:
        plt.show()


if __name__ == "__main__":
    main()