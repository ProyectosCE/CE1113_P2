"""Aplica los filtros a un archivo WAV para escucharlos.

Lee un WAV de 16 bits (8, 16 o 44,1 kHz, mono o estéreo), lo pasa por cada
filtro y guarda un WAV por filtro en dsp/output/audio/. También imprime,
para cada filtro, cuántas muestras se saturaron y cuánto cambió el volumen.

Uso:
    python dsp/model/filter_wav.py dsp/audio/cancion.wav
    python dsp/model/filter_wav.py dsp/audio/cancion.wav --seconds 30
    python dsp/model/filter_wav.py dsp/audio/cancion.wav --spectrogram
    python dsp/model/filter_wav.py --test-signal
"""

import argparse
from pathlib import Path

import numpy as np
from scipy import signal
from scipy.io import wavfile

from biquad_design import Biquad
from filter_config import FILTER_NAMES, SAMPLE_RATES, build_filters

DSP_DIR = Path(__file__).resolve().parents[1]
AUDIO_DIR = DSP_DIR / "audio"
OUTPUT_AUDIO_DIR = DSP_DIR / "output" / "audio"
OUTPUT_PLOTS_DIR = DSP_DIR / "output" / "plots"

# Escala de 16 bits: las muestras van de -32768 a 32767
INT16_SCALE = 32768
INT16_MIN = -32768
INT16_MAX = 32767

# Señal de prueba: tonos grave, medio y agudo
TEST_SIGNAL_FS = 44100
TEST_SIGNAL_SECONDS = 5.0
TEST_TONES_HZ = (100.0, 1000.0, 6000.0)
TEST_TONE_AMPLITUDE = 0.25   # amplitud de cada tono (1.0 = escala completa)

CONVERSION_HELP = (
    "Convierta el archivo a WAV de 16 bits con una fs soportada, por ejemplo:\n"
    "    ffmpeg -i entrada.wav -ar 44100 -sample_fmt s16 salida.wav\n"
    "o en Audacity: Proyecto a 44100 Hz y Exportar como WAV 'PCM de 16 bits con signo'."
)


# Lectura y escritura de WAV
def read_wav(path: Path) -> tuple[int, np.ndarray]:
    """Lee un WAV y verifica que tenga el formato que soporta el proyecto.

    Devuelve (fs, muestras), con muestras int16 de forma (N,) o (N, canales).
    """
    fs, samples = wavfile.read(path)

    if samples.dtype != np.int16:
        raise ValueError(
            f"{path.name}: las muestras son {samples.dtype}, se requiere PCM de 16 bits.\n"
            + CONVERSION_HELP
        )
    if fs not in SAMPLE_RATES:
        raise ValueError(
            f"{path.name}: fs = {fs} Hz no soportada; use una de {SAMPLE_RATES}.\n"
            + CONVERSION_HELP
        )
    return fs, samples


def write_wav(path: Path, fs: int, samples: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    wavfile.write(path, fs, samples)


def generate_test_signal(
    fs: int = TEST_SIGNAL_FS, seconds: float = TEST_SIGNAL_SECONDS
) -> np.ndarray:
    """Suma de tonos grave, medio y agudo en int16 (mono)."""
    t = np.arange(int(fs * seconds)) / fs
    x = sum(TEST_TONE_AMPLITUDE * np.sin(2 * np.pi * f * t) for f in TEST_TONES_HZ)
    return np.round(x * INT16_SCALE).astype(np.int16)


# Procesamiento
def to_sos(stages: list[Biquad]) -> np.ndarray:
    """Convierte las etapas al formato SOS de scipy: [b0, b1, b2, 1, a1, a2]."""
    return np.array([[s.b0, s.b1, s.b2, 1.0, s.a1, s.a2] for s in stages])


def apply_filter(samples: np.ndarray, stages: list[Biquad]) -> tuple[np.ndarray, int]:
    """Filtra muestras int16 con una cascada de biquads (punto flotante).

    Cada canal se filtra por separado. La salida se redondea a 16 bits y se
    satura al rango de int16. Devuelve (salida_int16, muestras_saturadas).
    """
    x = samples.astype(np.float64) / INT16_SCALE
    y = signal.sosfilt(to_sos(stages), x, axis=0) * INT16_SCALE

    clipped = int(np.count_nonzero((y > INT16_MAX) | (y < INT16_MIN)))
    out = np.clip(np.round(y), INT16_MIN, INT16_MAX).astype(np.int16)
    return out, clipped


def rms_db(samples: np.ndarray) -> float:
    """Nivel RMS en dB respecto a la escala completa (dBFS)."""
    x = samples.astype(np.float64) / INT16_SCALE
    rms = np.sqrt(np.mean(x ** 2))
    return 20 * np.log10(max(rms, 1e-12))

# Espectrogramas
def plot_spectrograms(fs: int, versions: dict[str, np.ndarray], path: Path) -> None:
    """Guarda un espectrograma del original y de cada versión filtrada."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(len(versions), 1, figsize=(10, 2.6 * len(versions)),
                             sharex=True, sharey=True)
    for ax, (label, samples) in zip(axes, versions.items()):
        # Si es estéreo se grafica el promedio de los canales
        mono = samples.astype(np.float64).mean(axis=1) if samples.ndim == 2 else samples
        freqs, times, power = signal.spectrogram(mono / INT16_SCALE, fs=fs, nperseg=4096)
        # Se omite la fila de 0 Hz porque el eje de frecuencia es logarítmico
        image = ax.pcolormesh(times, freqs[1:], 10 * np.log10(power[1:] + 1e-12),
                              shading="auto", vmin=-120, vmax=-20, cmap="magma")
        ax.set_title(label)
        ax.set_ylabel("Frecuencia (Hz)")
        ax.set_yscale("log")
        ax.set_ylim(50, fs / 2)

    axes[-1].set_xlabel("Tiempo (s)")
    fig.colorbar(image, ax=axes, label="Potencia (dB)")
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=120, bbox_inches="tight")

# Programa principal
def main() -> None:
    parser = argparse.ArgumentParser(description="Aplica los filtros a un archivo WAV")
    parser.add_argument("wav", nargs="?", type=Path, help="archivo WAV de entrada")
    parser.add_argument("--seconds", type=float, help="procesa solo los primeros N segundos")
    parser.add_argument("--test-signal", action="store_true",
                        help="genera dsp/audio/tonos_prueba.wav y lo procesa")
    parser.add_argument("--spectrogram", action="store_true",
                        help="guarda espectrogramas en dsp/output/plots/")
    args = parser.parse_args()

    if args.test_signal:
        args.wav = AUDIO_DIR / "tonos_prueba.wav"
        write_wav(args.wav, TEST_SIGNAL_FS, generate_test_signal())
        print(f"Señal de prueba generada: {args.wav}")
    elif args.wav is None:
        parser.error("indique un archivo WAV o use --test-signal")

    try:
        fs, samples = read_wav(args.wav)
    except ValueError as error:
        raise SystemExit(f"Error: {error}")

    if args.seconds:
        samples = samples[: int(args.seconds * fs)]

    channels = 1 if samples.ndim == 1 else samples.shape[1]
    print(f"Entrada: {args.wav.name}  fs = {fs} Hz  canales = {channels}  "
          f"duración = {len(samples) / fs:.1f} s  nivel = {rms_db(samples):.1f} dBFS\n")

    original_level = rms_db(samples)
    versions = {"original": samples}
    filters = build_filters(fs)

    print(f"{'filtro':<10}  {'saturadas':>10}  {'cambio de volumen':>18}  archivo")
    for name in FILTER_NAMES:
        filtered, clipped = apply_filter(samples, filters[name])
        out_path = OUTPUT_AUDIO_DIR / f"{args.wav.stem}_{name}.wav"
        write_wav(out_path, fs, filtered)
        versions[name] = filtered

        change = rms_db(filtered) - original_level
        print(f"{name:<10}  {clipped:>10}  {change:>15.1f} dB  {out_path.name}")

    print(f"\nArchivos guardados en {OUTPUT_AUDIO_DIR}")

    if args.spectrogram:
        plot_path = OUTPUT_PLOTS_DIR / f"espectrograma_{args.wav.stem}.png"
        plot_spectrograms(fs, versions, plot_path)
        print(f"Espectrograma guardado en {plot_path}")


if __name__ == "__main__":
    main()