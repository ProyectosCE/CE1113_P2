"""Modelo bit-exacto en punto fijo del filtro (cascada de biquads).

Es la referencia contra la que se verifica el hardware: con las mismas
entradas y los mismos coeficientes, el RTL debe producir exactamente las
mismas salidas, bit a bit.

Ruta de datos de una etapa (Forma Directa I)
Las señales internas tienen formato Q1.F con F = state_bits - 1 (rango
[-1, 1)). Con state_bits = 16 es el mismo formato del audio (Q1.15); con
state_bits = 24 es Q1.23 (más bits de fracción, menos ruido de redondeo).
Los coeficientes son Q3.15 de 18 bits.

Por cada muestra, la MAC acumula en este orden exacto:

    acc  = r[n-1]             <- residuo del redondeo anterior (ver abajo)
    acc += b0 * x[n]
    acc += b1 * x[n-1]
    acc += b2 * x[n-2]
    acc -= a1 * y[n-1]        <- se resta el producto; NO se niega a1
    acc -= a2 * y[n-2]           (negar -4.0 no cabe en Q3.15)

    q    = redondear(acc, 15 bits)
    r[n] = acc - q * 2^15     <- bits descartados, en [-2^14, 2^14): 15 bits
    y[n] = saturar(q, state_bits)

- Realimentación del error de redondeo: el residuo r[n] se guarda y el
  acumulador de la siguiente muestra arranca con él en vez de con 0. Así
  los errores de redondeo se compensan en lugar de acumularse, y el filtro
  vuelve exactamente a 0 en silencio (sin ciclos límite). En hardware no
  agrega ciclos: el acumulador se carga con el residuo en vez de limpiarse.
  Se puede desactivar (error_feedback=False) solo para comparar.
- Producto: state_bits + 18 bits.  Acumulador: state_bits + 24 bits.
  Ninguna suma parcial puede desbordar el acumulador (se verifica).
- Redondeo al más cercano, empates hacia +infinito (ver fixed_point.py).
- Saturación a la salida de cada etapa.
- Luego se desplazan los estados: x[n-2] <- x[n-1] <- x[n], y igual con y.
  El residuo se guarda aunque la salida se haya saturado.

Cascada
- La entrada de 16 bits se extiende al formato interno (desplazamiento a la
  izquierda de state_bits - 16 bits, sin pérdida).
- Se procesan las 3 etapas en orden; la salida de una es la entrada de la
  siguiente.
- La salida final se redondea y satura de vuelta a 16 bits.
- Bypass: la muestra sale igual a la entrada y el estado no se modifica.
- Reinicio: x, y y el residuo de todas las etapas vuelven a 0.
- Cargar coeficientes nuevos (cambiar de filtro) reinicia el estado a cero.

Uso rápido:
    python dsp/model/fixed_model.py
"""

import time

import numpy as np

from fixed_coefficients import FixedBiquad, build_fixed_filters
from fixed_point import COEF_FORMAT, SAMPLE_FORMAT, check_fits, round_shift, saturate

SAMPLE_BITS = SAMPLE_FORMAT.total_bits     # 16
COEF_BITS = COEF_FORMAT.total_bits         # 18
COEF_FRAC = COEF_FORMAT.frac_bits          # 15
DEFAULT_STATE_BITS = 16                    # precisión entre etapas (16 o 24)
RESIDUE_BITS = COEF_FRAC                   # el residuo de redondear 15 bits cabe en 15

def datapath_widths(state_bits: int) -> dict[str, int]:
    """Anchos de bits de la ruta de datos para una precisión interna dada."""
    product_bits = state_bits + COEF_BITS
    return {
        "muestra": SAMPLE_BITS,
        "estado": state_bits,
        "coeficiente": COEF_BITS,
        "producto": product_bits,
        "acumulador": product_bits + 6,   # 5 sumas necesitan 3 bits; 6 dan margen
    }

# Una etapa biquad
class FixedBiquadStage:
    """Una etapa biquad en Forma Directa I con su estado."""

    def __init__(self, coefs: FixedBiquad, state_bits: int, error_feedback: bool = True):
        self.coefs = coefs
        self.state_bits = state_bits
        self.error_feedback = error_feedback
        widths = datapath_widths(state_bits)
        self.product_bits = widths["producto"]
        self.acc_bits = widths["acumulador"]
        self.saturations = 0
        self.reset()

    def reset(self) -> None:
        self.x1 = self.x2 = self.y1 = self.y2 = 0
        self.residue = 0

    def process(self, x: int) -> int:
        """Procesa una muestra en formato interno y devuelve la salida."""
        b0, b1, b2, a1, a2 = self.coefs
        terms = (
            (b0, x, +1),
            (b1, self.x1, +1),
            (b2, self.x2, +1),
            (a1, self.y1, -1),
            (a2, self.y2, -1),
        )

        acc = self.residue if self.error_feedback else 0
        for coef, value, sign in terms:
            product = check_fits(coef * value, self.product_bits, "producto")
            acc = check_fits(acc + sign * product, self.acc_bits, "acumulador")

        rounded = round_shift(acc, COEF_FRAC)
        self.residue = check_fits(acc - (rounded << COEF_FRAC), RESIDUE_BITS, "residuo")
        y = saturate(rounded, self.state_bits)
        if y != rounded:
            self.saturations += 1

        self.x2, self.x1 = self.x1, x
        self.y2, self.y1 = self.y1, y
        return y

# Cascada de etapas (un canal)
class FixedBiquadCascade:
    """Cascada de etapas biquad para un canal, con bypass y reinicio."""

    def __init__(
        self,
        stages: list[FixedBiquad],
        state_bits: int = DEFAULT_STATE_BITS,
        error_feedback: bool = True,
    ):
        if state_bits < SAMPLE_BITS:
            raise ValueError(f"state_bits debe ser al menos {SAMPLE_BITS}")
        self.state_bits = state_bits
        self.error_feedback = error_feedback
        self.extra_bits = state_bits - SAMPLE_BITS
        self.bypass = False
        self.load_coefficients(stages)

    def load_coefficients(self, stages: list[FixedBiquad]) -> None:
        """Carga coeficientes nuevos y reinicia el estado (cambio de filtro)."""
        self.stages = [FixedBiquadStage(c, self.state_bits, self.error_feedback)
                       for c in stages]

    def reset(self) -> None:
        for stage in self.stages:
            stage.reset()

    @property
    def saturations(self) -> int:
        """Cantidad de veces que se saturó alguna etapa (bit de overflow)."""
        return sum(stage.saturations for stage in self.stages)

    def process_sample(self, sample: int) -> int:
        """Procesa una muestra de 16 bits y devuelve la salida de 16 bits."""
        check_fits(sample, SAMPLE_BITS, "muestra de entrada")
        if self.bypass:
            return sample

        value = sample << self.extra_bits
        for stage in self.stages:
            value = stage.process(value)
        return saturate(round_shift(value, self.extra_bits), SAMPLE_BITS)

# Procesamiento de bloques (mono o estéreo)
def process_fixed(
    samples: np.ndarray,
    stages: list[FixedBiquad],
    state_bits: int = DEFAULT_STATE_BITS,
    bypass: bool = False,
    error_feedback: bool = True,
) -> tuple[np.ndarray, int]:
    """Filtra muestras int16 con el modelo bit-exacto.

    Cada canal tiene su propia cascada (su propio estado) y todos usan los
    mismos coeficientes. Devuelve (salida_int16, saturaciones).
    """
    data = np.asarray(samples)
    mono = data.ndim == 1
    channels = data.reshape(-1, 1) if mono else data
    out = np.empty_like(channels, dtype=np.int16)
    saturations = 0

    for ch in range(channels.shape[1]):
        cascade = FixedBiquadCascade(stages, state_bits, error_feedback)
        cascade.bypass = bypass
        column = channels[:, ch].tolist()
        out[:, ch] = [cascade.process_sample(int(s)) for s in column]
        saturations += cascade.saturations

    return (out[:, 0] if mono else out), saturations


# Demostración
if __name__ == "__main__":
    fs = 44100
    filters = build_fixed_filters(fs)

    for state_bits in (16, 24):
        widths = datapath_widths(state_bits)
        print(f"Ruta de datos con estado de {state_bits} bits: "
              + ", ".join(f"{k} {v}" for k, v in widths.items()))

    impulse = np.zeros(8, dtype=np.int16)
    impulse[0] = 16384   # 0.5 en Q1.15
    print(f"\nRespuesta al impulso (0.5) del pasa-altos a {fs} Hz, primeras 8 muestras:")
    for state_bits in (16, 24):
        out, _ = process_fixed(impulse, filters["highpass"], state_bits)
        print(f"  estado de {state_bits} bits: {out.tolist()}")

    out, _ = process_fixed(impulse, filters["highpass"], bypass=True)
    print(f"  bypass:             {out.tolist()}")

    noise = np.random.default_rng(0).uniform(-0.5, 0.5, 2000) * 32767
    burst = np.concatenate([np.round(noise), np.zeros(8000)]).astype(np.int16)
    print(f"\nEcualizador a {fs} Hz: valor final después de ruido y 8000 muestras de silencio")
    for state_bits in (16, 24):
        for feedback in (False, True):
            out, _ = process_fixed(burst, filters["equalizer"], state_bits,
                                   error_feedback=feedback)
            label = "con realimentación" if feedback else "sin realimentación"
            print(f"  estado de {state_bits} bits, {label:<19}: {int(out[-1])}")

    t = np.arange(fs) / fs
    tone = np.round(0.5 * np.sin(2 * np.pi * 1000 * t) * 32768).astype(np.int16)
    start = time.perf_counter()
    _, saturations = process_fixed(tone, filters["equalizer"])
    elapsed = time.perf_counter() - start
    print(f"\n1 s de audio mono por el ecualizador: {elapsed:.1f} s de cálculo, "
          f"{saturations} saturaciones")