"""Genera los vectores de prueba en hexadecimal para el testbench del filtro.

Por cada frecuencia de muestreo y cada modo (pasa-altos, pasa-banda,
ecualizador y bypass) genera en dsp/vectors/<fs>/<modo>/:

  - coefs.hex    : 15 coeficientes de 18 bits (5 dígitos hex), en el orden
                   etapa 0 (b0 b1 b2 a1 a2), etapa 1, etapa 2
  - input.hex    : muestras de entrada de 16 bits (4 dígitos hex)
  - expected.hex : salida esperada de 16 bits, calculada con el modelo
                   bit-exacto (fixed_model.py)

Todos los valores van en complemento a dos, uno por línea, listos para
$readmemh. La entrada es la misma secuencia de señales en todos los casos
(ver SEGMENTS) y el filtro se reinicia una sola vez, al principio.

En el modo bypass se cargan los coeficientes del ecualizador con el bypass
activo: la salida esperada es igual a la entrada.

Uso:
    python dsp/model/generate_vectors.py
"""

import argparse
from pathlib import Path

import numpy as np
from scipy import signal

from filter_config import FILTER_NAMES, SAMPLE_RATES
from fixed_coefficients import COEF_BITS, build_fixed_filters
from fixed_model import DEFAULT_STATE_BITS, SAMPLE_BITS, process_fixed
from fixed_point import to_hex

VECTORS_DIR = Path(__file__).resolve().parents[1] / "vectors"
MODES = (*FILTER_NAMES, "bypass")
BYPASS_COEFS_FROM = "equalizer"

HALF_SCALE = 16384      # 0.5 en Q1.15
MAX_SAMPLE = 32767
MIN_SAMPLE = -32768
NOISE_SEED = 1234

# Señales de entrada, en orden: (nombre, cantidad de muestras, descripción)
SEGMENTS = (
    ("impulso", 300, "un impulso de 0.5 seguido de ceros"),
    ("escalon_pos", 300, "escalón de +0.5"),
    ("escalon_neg", 300, "escalón de -0.5"),
    ("seno_grave", 300, "seno de 100 Hz, amplitud 0.5"),
    ("seno_medio", 300, "seno de 1 kHz, amplitud 0.5"),
    ("seno_agudo", 300, "seno de 0.35*fs, amplitud 0.5"),
    ("extremos", 200, "+32767 y -32768 constantes y alternados (saturación)"),
    ("chirp", 400, "barrido de 20 Hz a 0.45*fs, amplitud 0.5"),
    ("ruido", 300, f"ruido uniforme de amplitud 0.5, semilla {NOISE_SEED}"),
    ("silencio", 500, "ceros: la salida debe volver a 0"),
)

# Señal de entrada
def _to_int16(x: np.ndarray) -> np.ndarray:
    return np.clip(np.round(x * 32768), MIN_SAMPLE, MAX_SAMPLE).astype(np.int16)

def _segment(name: str, n: int, fs: int) -> np.ndarray:
    t = np.arange(n) / fs
    if name == "impulso":
        x = np.zeros(n, dtype=np.int16)
        x[0] = HALF_SCALE
        return x
    if name == "escalon_pos":
        return np.full(n, HALF_SCALE, dtype=np.int16)
    if name == "escalon_neg":
        return np.full(n, -HALF_SCALE, dtype=np.int16)
    if name == "seno_grave":
        return _to_int16(0.5 * np.sin(2 * np.pi * 100 * t))
    if name == "seno_medio":
        return _to_int16(0.5 * np.sin(2 * np.pi * 1000 * t))
    if name == "seno_agudo":
        return _to_int16(0.5 * np.sin(2 * np.pi * 0.35 * fs * t))
    if name == "extremos":
        quarter = n // 4
        constant = [MAX_SAMPLE] * quarter + [MIN_SAMPLE] * quarter
        alternating = [MAX_SAMPLE, MIN_SAMPLE] * ((n - 2 * quarter) // 2)
        return np.array(constant + alternating, dtype=np.int16)
    if name == "chirp":
        duration = n / fs
        return _to_int16(0.5 * signal.chirp(t, f0=20, t1=duration, f1=0.45 * fs,
                                             method="logarithmic"))
    if name == "ruido":
        rng = np.random.default_rng(NOISE_SEED)
        return _to_int16(rng.uniform(-0.5, 0.5, n))
    if name == "silencio":
        return np.zeros(n, dtype=np.int16)
    raise ValueError(f"Señal desconocida: {name}")

def build_input(fs: int) -> np.ndarray:
    """Concatena todas las señales de SEGMENTS para una frecuencia fs."""
    return np.concatenate([_segment(name, n, fs) for name, n, _ in SEGMENTS])

def segment_starts() -> list[tuple[str, int, int]]:
    """(nombre, primera muestra, última muestra) de cada señal."""
    starts, position = [], 0
    for name, n, _ in SEGMENTS:
        starts.append((name, position, position + n - 1))
        position += n
    return starts

# Casos
def case_coefficients(fs: int, mode: str) -> list[int]:
    """Los 15 coeficientes enteros del caso, en orden de carga."""
    name = BYPASS_COEFS_FROM if mode == "bypass" else mode
    return [value for stage in build_fixed_filters(fs)[name] for value in stage]

def expected_output(fs: int, mode: str, samples: np.ndarray) -> np.ndarray:
    """Salida del modelo bit-exacto para una entrada dada."""
    name = BYPASS_COEFS_FROM if mode == "bypass" else mode
    stages = build_fixed_filters(fs)[name]
    y, _ = process_fixed(samples, stages, DEFAULT_STATE_BITS, bypass=(mode == "bypass"))
    return y

def _write_hex(path: Path, values, bits: int) -> None:
    path.write_text("".join(f"{to_hex(int(v), bits)}\n" for v in values))

def write_case(out_dir: Path, fs: int, mode: str) -> Path:
    case_dir = out_dir / str(fs) / mode
    case_dir.mkdir(parents=True, exist_ok=True)

    samples = build_input(fs)
    _write_hex(case_dir / "coefs.hex", case_coefficients(fs, mode), COEF_BITS)
    _write_hex(case_dir / "input.hex", samples, SAMPLE_BITS)
    _write_hex(case_dir / "expected.hex", expected_output(fs, mode, samples), SAMPLE_BITS)
    return case_dir

# README de los vectores
def readme_text() -> str:
    total = sum(n for _, n, _ in SEGMENTS)
    rows = "\n".join(
        f"| {start} – {end} | `{name}` | {description} |"
        for (name, start, end), (_, _, description) in zip(segment_starts(), SEGMENTS)
    )
    return f"""# Vectores de prueba del filtro DSP

Archivo generado con `python dsp/model/generate_vectors.py`. No editar a mano:
si cambia el modelo o los coeficientes, se regeneran con ese comando.

## Organización

```text
dsp/vectors/<fs>/<modo>/
├── coefs.hex      15 coeficientes de 18 bits (5 dígitos hex)
├── input.hex      {total} muestras de entrada de 16 bits (4 dígitos hex)
└── expected.hex   {total} muestras de salida esperada de 16 bits
```

- `<fs>`: {", ".join(str(fs) for fs in SAMPLE_RATES)}
- `<modo>`: {", ".join(MODES)}

Todos los valores están en complemento a dos, uno por línea, listos para
`$readmemh`. Ejemplo: `FFFF` = -1 en 16 bits; `3FFFF` = -1 en 18 bits.

## Coeficientes

Formato Q3.15 (18 bits). Orden de las 15 líneas de `coefs.hex`:

```text
etapa 0: b0 b1 b2 a1 a2
etapa 1: b0 b1 b2 a1 a2
etapa 2: b0 b1 b2 a1 a2
```

En el modo `bypass` se cargan los coeficientes del ecualizador con el bypass
activo; la salida esperada debe ser igual a la entrada.

## Configuración del modelo

- Muestras de entrada y salida: 16 bits, Q1.15.
- Estado entre etapas: {DEFAULT_STATE_BITS} bits.
- Realimentación del error de redondeo activada.
- El filtro se reinicia (estado en cero) una sola vez, antes de la primera
  muestra; todas las señales se procesan seguidas.

## Señales de entrada

Las mismas en todos los casos, en este orden (índices de muestra):

| Muestras | Señal | Descripción |
|---|---|---|
{rows}
"""


def write_vectors(out_dir: Path = VECTORS_DIR) -> list[Path]:
    """Genera todos los casos y el README. Devuelve las carpetas creadas."""
    out_dir.mkdir(parents=True, exist_ok=True)
    cases = [write_case(out_dir, fs, mode) for fs in SAMPLE_RATES for mode in MODES]
    (out_dir / "README.md").write_text(readme_text())
    return cases


def main() -> None:
    parser = argparse.ArgumentParser(description="Genera los vectores de prueba")
    parser.add_argument("--out", type=Path, default=VECTORS_DIR,
                        help="carpeta de salida (por defecto dsp/vectors)")
    args = parser.parse_args()

    cases = write_vectors(args.out)
    total = sum(n for _, n, _ in SEGMENTS)
    print(f"{len(cases)} casos generados en {args.out} ({total} muestras cada uno):")
    for case in cases:
        print(f"  {case.relative_to(args.out)}")


if __name__ == "__main__":
    main()