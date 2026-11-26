"""Exporta la tabla de coeficientes y analiza el formato Q que necesitan.

Genera en dsp/output/coefficients/:
  - coeficientes.csv : tabla completa (fs, filtro, etapa, b0, b1, b2, a1, a2)
  - coeficientes.md  : la misma tabla en Markdown, lista para la documentación

Además imprime:
  - el valor máximo de cada coeficiente y los bits enteros que necesita,
  - el formato Q recomendado para coeficientes de 16 y 18 bits,
  - el efecto de cuantizar los coeficientes a esos formatos: si los filtros
    siguen siendo estables y cuánto cambia su respuesta en frecuencia.

Uso:
    python dsp/model/export_coefficients.py
"""

import csv
from pathlib import Path

import numpy as np
from scipy import signal

from biquad_design import Biquad
from filter_config import FILTER_NAMES, SAMPLE_RATES, build_filters

OUTPUT_DIR = Path(__file__).resolve().parents[1] / "output" / "coefficients"
FIELDS = Biquad._fields   # ("b0", "b1", "b2", "a1", "a2")

# Anchos de coeficiente a evaluar: 16 bits (registro) y 18 bits (multiplicador
# nativo de los bloques DSP del Cyclone V)
CANDIDATE_WIDTHS = (16, 18)

# Tabla de coeficientes
def coefficient_rows() -> list[dict]:
    """Una fila por (fs, filtro, etapa) con sus 5 coeficientes."""
    rows = []
    for fs in SAMPLE_RATES:
        for index, name in enumerate(FILTER_NAMES):
            for stage_number, stage in enumerate(build_filters(fs)[name]):
                rows.append({
                    "fs": fs,
                    "filtro": index,
                    "nombre": name,
                    "etapa": stage_number,
                    **stage._asdict(),
                })
    return rows


def write_csv(rows: list[dict], path: Path) -> None:
    with path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow({k: f"{v:.10f}" if isinstance(v, float) else v
                             for k, v in row.items()})


def write_markdown(rows: list[dict], path: Path) -> None:
    lines = [
        "| fs (Hz) | Filtro | Etapa | b0 | b1 | b2 | a1 | a2 |",
        "|---:|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        values = " | ".join(f"{row[field]:+.6f}" for field in FIELDS)
        lines.append(f"| {row['fs']} | {row['filtro']} ({row['nombre']}) | "
                     f"{row['etapa']} | {values} |")
    path.write_text("\n".join(lines) + "\n")

# Análisis del formato Q
def integer_bits(values) -> int:
    """Bits enteros (incluido el signo) para representar todos los valores.

    Un formato Qm.n con m bits enteros cubre el rango [-2^(m-1), 2^(m-1)).
    """
    m = 1
    while not all(-(2 ** (m - 1)) <= v < 2 ** (m - 1) for v in values):
        m += 1
    return m


def quantize(value: float, frac_bits: int) -> float:
    """Redondea un valor al múltiplo de 2^-frac_bits más cercano."""
    step = 2.0 ** -frac_bits
    return round(value / step) * step


def quantize_stage(stage: Biquad, frac_bits: int) -> Biquad:
    return Biquad(*(quantize(v, frac_bits) for v in stage))


def max_response_error_db(stages, quantized, fs) -> float:
    """Error absoluto máximo entre la respuesta original y la cuantizada.

    Se expresa en dB respecto a la ganancia unitaria: -40 dB significa que
    la respuesta cambió como máximo un 1 % de la escala completa. Se usa el
    error absoluto (no la diferencia de dB) porque en la banda de rechazo,
    donde la respuesta es casi cero, una diferencia en dB exagera cambios
    que no se oyen.
    """
    freqs = np.geomspace(20, 0.95 * fs / 2, 1000)
    h_orig = np.ones_like(freqs, dtype=complex)
    h_quant = np.ones_like(freqs, dtype=complex)
    for original, rounded in zip(stages, quantized):
        h_orig *= signal.freqz(original.b, original.a, worN=freqs, fs=fs)[1]
        h_quant *= signal.freqz(rounded.b, rounded.a, worN=freqs, fs=fs)[1]
    error = np.max(np.abs(h_quant - h_orig))
    return float(20 * np.log10(max(error, 1e-12)))


def pole_radius(stage: Biquad) -> float:
    return float(max(abs(np.roots(stage.a))))

# Programa principal
def main() -> None:
    rows = coefficient_rows()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(rows, OUTPUT_DIR / "coeficientes.csv")
    write_markdown(rows, OUTPUT_DIR / "coeficientes.md")
    print(f"Tabla de {len(rows)} etapas guardada en {OUTPUT_DIR}\n")

    # 1. Rango de cada coeficiente
    print("Rango de los coeficientes")
    print(f"{'coef':<5} {'mínimo':>10} {'máximo':>10} {'bits enteros':>13}")
    for field in FIELDS:
        values = [row[field] for row in rows]
        print(f"{field:<5} {min(values):>+10.4f} {max(values):>+10.4f} "
              f"{integer_bits(values):>13}")

    all_values = [row[field] for row in rows for field in FIELDS]
    m = integer_bits(all_values)
    worst = max(rows, key=lambda r: max(abs(r[f]) for f in FIELDS))
    worst_field = max(FIELDS, key=lambda f: abs(worst[f]))
    print(f"\nValor de mayor magnitud: {worst[worst_field]:+.4f} "
          f"({worst_field} de {worst['nombre']}, etapa {worst['etapa']}, fs = {worst['fs']} Hz)")
    print(f"Bits enteros necesarios (incluido el signo): {m}\n")

    # 2. Efecto de cuantizar con cada ancho candidato
    for width in CANDIDATE_WIDTHS:
        n = width - m
        print(f"Coeficientes de {width} bits -> Q{m}.{n} "
              f"(rango [-{2 ** (m - 1)}, {2 ** (m - 1)}), paso {2.0 ** -n:.2e})")
        print(f"  {'fs':>6}  {'filtro':<10}  {'estable':>7}  {'radio máx':>9}  {'error abs máx':>14}")
        for fs in SAMPLE_RATES:
            for name in FILTER_NAMES:
                stages = build_filters(fs)[name]
                quantized = [quantize_stage(s, n) for s in stages]
                radius = max(pole_radius(s) for s in quantized)
                stable = "sí" if radius < 1 else "NO"
                error = max_response_error_db(stages, quantized, fs)
                print(f"  {fs:>6}  {name:<10}  {stable:>7}  {radius:>9.4f}  {error:>11.1f} dB")
        print()


if __name__ == "__main__":
    main()