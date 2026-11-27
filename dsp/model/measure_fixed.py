"""Mide la calidad del modelo en punto fijo y compara la precisión entre etapas.

Para cada filtro y frecuencia de muestreo compara la salida del modelo
bit-exacto contra una referencia en punto flotante (con los mismos
coeficientes cuantizados, sin redondear la salida) y reporta:

  - error máximo y error RMS, en LSB de 16 bits,
  - SNR: relación entre la señal de referencia y el error, en dB,
  - valor que queda a la salida después de la señal (silencio),
  - cantidad de saturaciones.

Se evalúan tres configuraciones:
  - "ideal": la referencia flotante solo redondeada a 16 bits (lo mejor
    que se puede lograr con salida de 16 bits),
  - estado de 16 bits con realimentación del error,
  - estado de 24 bits con realimentación del error.

Y dos señales de prueba: ruido + chirp a nivel normal (-12 dBFS aprox.) y un
tono suave (-40 dBFS), donde el ruido de redondeo pesa más.

Con --wav filtra además un archivo con el modelo para escucharlo:

Uso:
    python dsp/model/measure_fixed.py
    python dsp/model/measure_fixed.py --wav dsp/audio/cancion.wav --seconds 10
"""

import argparse
import csv
from pathlib import Path

import numpy as np
from scipy import signal

from filter_config import FILTER_NAMES, SAMPLE_RATES
from filter_wav import OUTPUT_AUDIO_DIR, apply_filter, read_wav, rms_db, to_sos, write_wav
from fixed_coefficients import build_fixed_filters, to_float_stage
from fixed_model import process_fixed

OUTPUT_DIR = Path(__file__).resolve().parents[1] / "output" / "measurements"
INT16_SCALE = 32768
SILENCE_SAMPLES = 4000
CONFIGS = ("ideal", 16, 24)

# Señales de prueba
def test_signals(fs: int, seconds: float = 0.5) -> dict[str, np.ndarray]:
    """Señales int16 seguidas de silencio para medir también el final."""
    n = int(fs * seconds)
    t = np.arange(n) / fs
    rng = np.random.default_rng(fs)

    chirp = signal.chirp(t, f0=20, t1=seconds, f1=0.45 * fs, method="logarithmic")
    normal = 0.15 * chirp + rng.uniform(-0.15, 0.15, n)
    quiet = 0.01 * np.sin(2 * np.pi * 440 * t)          # -40 dBFS

    silence = np.zeros(SILENCE_SAMPLES)
    return {
        "normal": np.round(np.concatenate([normal, silence]) * 32767).astype(np.int16),
        "suave": np.round(np.concatenate([quiet, silence]) * 32767).astype(np.int16),
    }

# Medición
def float_reference(x: np.ndarray, stages) -> np.ndarray:
    """Salida flotante (en unidades de LSB de 16 bits) sin redondear."""
    sos = to_sos([to_float_stage(s) for s in stages])
    return signal.sosfilt(sos, x.astype(np.float64))

def metrics(y: np.ndarray, reference: np.ndarray, saturations: int) -> dict:
    active = slice(0, len(y) - SILENCE_SAMPLES)
    error = y[active].astype(np.float64) - reference[active]
    signal_power = np.mean(reference[active] ** 2)
    noise_power = np.mean(error ** 2)
    return {
        "error_max": float(np.max(np.abs(error))),
        "error_rms": float(np.sqrt(noise_power)),
        "snr_db": float(10 * np.log10(signal_power / max(noise_power, 1e-20))),
        "silencio": int(np.max(np.abs(y[-SILENCE_SAMPLES // 2:]))),
        "saturaciones": saturations,
    }

def measure(fs: int, name: str, x: np.ndarray) -> dict:
    stages = build_fixed_filters(fs)[name]
    reference = float_reference(x, stages)
    results = {}
    for config in CONFIGS:
        if config == "ideal":
            y = np.clip(np.round(reference), -32768, 32767).astype(np.int16)
            saturations = 0
        else:
            y, saturations = process_fixed(x, stages, state_bits=config)
        results[config] = metrics(y, reference, saturations)
    return results

def run_measurements() -> list[dict]:
    rows = []
    for fs in SAMPLE_RATES:
        signals = test_signals(fs)
        for name in FILTER_NAMES:
            for signal_name, x in signals.items():
                for config, values in measure(fs, name, x).items():
                    rows.append({"fs": fs, "filtro": name, "senal": signal_name,
                                 "config": config, **values})
    return rows

def print_table(rows: list[dict]) -> None:
    header = (f"{'fs':>6} {'filtro':<10} {'señal':<7} {'config':<7} "
              f"{'err máx':>8} {'err RMS':>8} {'SNR (dB)':>9} {'silencio':>9} {'sat':>4}")
    print(header)
    print("-" * len(header))
    for row in rows:
        config = row["config"] if row["config"] == "ideal" else f"{row['config']} bits"
        print(f"{row['fs']:>6} {row['filtro']:<10} {row['senal']:<7} {config:<7} "
              f"{row['error_max']:>8.2f} {row['error_rms']:>8.3f} {row['snr_db']:>9.1f} "
              f"{row['silencio']:>9d} {row['saturaciones']:>4d}")

def print_summary(rows: list[dict]) -> None:
    print("\nResumen (peor caso de todos los filtros y fs)")
    print(f"{'config':<8} {'señal':<7} {'err máx (LSB)':>14} {'SNR mín (dB)':>13} "
          f"{'pérdida vs ideal (dB)':>22} {'silencio':>9}")
    for config in CONFIGS:
        for signal_name in ("normal", "suave"):
            selected = [r for r in rows if r["config"] == config and r["senal"] == signal_name]
            ideal = {(r["fs"], r["filtro"]): r["snr_db"] for r in rows
                     if r["config"] == "ideal" and r["senal"] == signal_name}
            loss = max(ideal[(r["fs"], r["filtro"])] - r["snr_db"] for r in selected)
            label = config if config == "ideal" else f"{config} bits"
            print(f"{label:<8} {signal_name:<7} "
                  f"{max(r['error_max'] for r in selected):>14.2f} "
                  f"{min(r['snr_db'] for r in selected):>13.1f} "
                  f"{loss:>22.1f} "
                  f"{max(r['silencio'] for r in selected):>9d}")

def write_csv(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

# Filtrado de un WAV con el modelo, para escuchar
def filter_wav_fixed(path: Path, seconds: float, state_bits: int) -> None:
    fs, samples = read_wav(path)
    samples = samples[: int(seconds * fs)]
    filters = build_fixed_filters(fs)

    print(f"\nFiltrando {path.name} ({len(samples) / fs:.1f} s, fs = {fs} Hz) "
          f"con el modelo de {state_bits} bits")
    print(f"{'filtro':<10} {'sat':>5} {'dif. máx vs flotante':>21} {'nivel dif. (dBFS)':>18}")
    for name in FILTER_NAMES:
        stages = filters[name]
        fixed, saturations = process_fixed(samples, stages, state_bits)
        floating, _ = apply_filter(samples, [to_float_stage(s) for s in stages])
        diff = fixed.astype(np.int32) - floating.astype(np.int32)

        write_wav(OUTPUT_AUDIO_DIR / f"{path.stem}_{name}_fijo{state_bits}.wav", fs, fixed)
        write_wav(OUTPUT_AUDIO_DIR / f"{path.stem}_{name}_flotante.wav", fs, floating)
        level = rms_db(np.clip(diff, -32768, 32767).astype(np.int16))
        print(f"{name:<10} {saturations:>5} {int(np.max(np.abs(diff))):>17d} LSB "
              f"{level:>18.1f}")
    print(f"Archivos guardados en {OUTPUT_AUDIO_DIR}")

def main() -> None:
    parser = argparse.ArgumentParser(description="Mide la calidad del modelo en punto fijo")
    parser.add_argument("--wav", type=Path, help="WAV para filtrar con el modelo y escuchar")
    parser.add_argument("--seconds", type=float, default=10.0,
                        help="segundos del WAV a procesar (por defecto 10)")
    parser.add_argument("--state-bits", type=int, default=16, choices=(16, 24),
                        help="precisión entre etapas para el WAV (por defecto 16)")
    args = parser.parse_args()

    rows = run_measurements()
    print_table(rows)
    print_summary(rows)

    path = OUTPUT_DIR / "medicion_punto_fijo.csv"
    write_csv(rows, path)
    print(f"\nTabla guardada en {path}")

    if args.wav:
        try:
            filter_wav_fixed(args.wav, args.seconds, args.state_bits)
        except ValueError as error:
            raise SystemExit(f"Error: {error}")


if __name__ == "__main__":
    main()