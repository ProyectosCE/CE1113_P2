"""Funciones de punto fijo que imitan la aritmética del hardware.

Todo se calcula con enteros de Python, nunca con decimales, para que los
resultados sean exactamente los que producirá el hardware.

Convenciones (las mismas que debe seguir el RTL):

- Un formato Qm.n tiene m bits enteros (incluido el signo) y n bits de
  fracción, en complemento a dos. Su rango es [-2^(m-1), 2^(m-1) - 2^-n].
- Redondeo al más cercano: al descartar k bits se suma 2^(k-1) y se hace
  un desplazamiento aritmético a la derecha. En el caso exacto de la mitad
  se redondea hacia +infinito (+0.5 -> 1, -0.5 -> 0, -1.5 -> -1).
  En SystemVerilog: (valor + (1 <<< (k-1))) >>> k, con valor de tipo signed.
- Saturación: si un valor no cabe en N bits, se reemplaza por el máximo o
  el mínimo representable, en vez de "dar la vuelta".

Uso rápido:
    python dsp/model/fixed_point.py
"""

import math
from dataclasses import dataclass

# Formatos Q
@dataclass(frozen=True)
class QFormat:
    """Formato de punto fijo Qm.n en complemento a dos."""

    int_bits: int    # m: bits enteros, incluido el signo
    frac_bits: int   # n: bits de fracción

    @property
    def total_bits(self) -> int:
        return self.int_bits + self.frac_bits

    @property
    def min_int(self) -> int:
        """Entero más pequeño representable."""
        return -(1 << (self.total_bits - 1))

    @property
    def max_int(self) -> int:
        """Entero más grande representable."""
        return (1 << (self.total_bits - 1)) - 1

    @property
    def step(self) -> float:
        """Valor real de una unidad (LSB)."""
        return 2.0 ** -self.frac_bits

    @property
    def name(self) -> str:
        return f"Q{self.int_bits}.{self.frac_bits}"

# Formatos de la ruta de datos acordados para el filtro
SAMPLE_FORMAT = QFormat(int_bits=1, frac_bits=15)    # 16 bits, audio WAV
COEF_FORMAT = QFormat(int_bits=3, frac_bits=15)      # 18 bits, coeficientes
PRODUCT_FORMAT = QFormat(int_bits=4, frac_bits=30)   # 34 bits = 16 + 18
ACC_FORMAT = QFormat(int_bits=10, frac_bits=30)      # 40 bits, acumulador

FORMATS = {
    "muestra": SAMPLE_FORMAT,
    "coeficiente": COEF_FORMAT,
    "producto": PRODUCT_FORMAT,
    "acumulador": ACC_FORMAT,
}

# Rango y saturación
def min_value(bits: int) -> int:
    return -(1 << (bits - 1))

def max_value(bits: int) -> int:
    return (1 << (bits - 1)) - 1

def fits(value: int, bits: int) -> bool:
    """True si el entero cabe en complemento a dos de 'bits' bits."""
    return min_value(bits) <= value <= max_value(bits)

def check_fits(value: int, bits: int, name: str = "valor") -> int:
    """Devuelve el valor si cabe en 'bits' bits; si no, lanza OverflowError.

    Sirve para detectar desbordes que en el hardware serían un error de diseño,
    por ejemplo en el acumulador.
    """
    if not fits(value, bits):
        raise OverflowError(f"{name} = {value} no cabe en {bits} bits")
    return value

def saturate(value: int, bits: int) -> int:
    """Limita un entero al rango de 'bits' bits en complemento a dos."""
    return max(min_value(bits), min(max_value(bits), value))

# Redondeo
def round_shift(value: int, shift: int) -> int:
    """Descarta 'shift' bits de fracción redondeando al más cercano.

    Equivale a dividir entre 2^shift y redondear, con los empates hacia
    +infinito. Python aplica >> como desplazamiento aritmético en negativos,
    igual que >>> sobre un valor signed en SystemVerilog.
    """
    if shift < 0:
        raise ValueError("shift debe ser mayor o igual a 0")
    if shift == 0:
        return value
    return (value + (1 << (shift - 1))) >> shift

# Conversión entre decimal y punto fijo
def to_fixed(value: float, fmt: QFormat, saturate_result: bool = False) -> int:
    """Convierte un decimal al entero de un formato Q.

    Redondea al más cercano con la misma regla que round_shift. Si el valor
    no cabe en el formato, lanza OverflowError, salvo que saturate_result
    sea True, en cuyo caso se satura.
    """
    scaled = math.floor(value * (1 << fmt.frac_bits) + 0.5)
    if saturate_result:
        return saturate(scaled, fmt.total_bits)
    return check_fits(scaled, fmt.total_bits, f"{value} en {fmt.name}")

def to_float(value: int, fmt: QFormat) -> float:
    """Convierte un entero de un formato Q a su valor decimal."""
    return value / (1 << fmt.frac_bits)

# Complemento a dos y hexadecimal (para registros y vectores de prueba)
def to_unsigned(value: int, bits: int) -> int:
    """Patrón de bits sin signo de un entero en complemento a dos."""
    check_fits(value, bits)
    return value & ((1 << bits) - 1)

def from_unsigned(pattern: int, bits: int) -> int:
    """Interpreta un patrón de bits sin signo como complemento a dos."""
    if not 0 <= pattern < (1 << bits):
        raise ValueError(f"el patrón {pattern} no cabe en {bits} bits")
    return pattern - (1 << bits) if pattern >= (1 << (bits - 1)) else pattern

def to_hex(value: int, bits: int) -> str:
    """Hexadecimal en complemento a dos, con los dígitos justos para 'bits'."""
    digits = (bits + 3) // 4
    return f"{to_unsigned(value, bits):0{digits}X}"

def from_hex(text: str, bits: int) -> int:
    """Lee un hexadecimal en complemento a dos de 'bits' bits."""
    return from_unsigned(int(text, 16), bits)

# Demostración
if __name__ == "__main__":
    print("Formatos de la ruta de datos")
    print(f"{'señal':<12} {'formato':<8} {'bits':>4} {'mínimo':>12} {'máximo':>14} {'paso (LSB)':>12}")
    for label, fmt in FORMATS.items():
        print(f"{label:<12} {fmt.name:<8} {fmt.total_bits:>4} "
              f"{to_float(fmt.min_int, fmt):>12.6f} {to_float(fmt.max_int, fmt):>14.9f} "
              f"{fmt.step:>12.3e}")

    print("\nConversión de un coeficiente a Q3.15 (18 bits)")
    coef = -2.173723
    fixed = to_fixed(coef, COEF_FORMAT)
    print(f"  {coef} -> {fixed} (0x{to_hex(fixed, COEF_FORMAT.total_bits)})"
          f" -> {to_float(fixed, COEF_FORMAT):.6f}")

    print("\nRedondeo al más cercano descartando 1 bit (dividir entre 2)")
    for value in (3, 1, -1, -3, -4):
        print(f"  {value:>3} / 2 = {value / 2:>5} -> {round_shift(value, 1):>3}")

    print("\nSaturación a 16 bits")
    for value in (40000, -40000, 1234):
        print(f"  {value:>7} -> {saturate(value, 16):>7}")