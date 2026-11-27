"""Pruebas de las funciones de punto fijo.

Revisan los casos límite donde suelen aparecer errores: números negativos,
empates en el redondeo, valores extremos de cada formato y saturación.

Uso:
    pytest dsp -v
"""

import math
import pytest

from fixed_point import (
    ACC_FORMAT,
    COEF_FORMAT,
    PRODUCT_FORMAT,
    SAMPLE_FORMAT,
    QFormat,
    check_fits,
    fits,
    from_hex,
    from_unsigned,
    round_shift,
    saturate,
    to_fixed,
    to_float,
    to_hex,
    to_unsigned,
)

# Formatos
@pytest.mark.parametrize("fmt, bits, name", [
    (SAMPLE_FORMAT, 16, "Q1.15"),
    (COEF_FORMAT, 18, "Q3.15"),
    (PRODUCT_FORMAT, 34, "Q4.30"),
    (ACC_FORMAT, 40, "Q10.30"),
])
def test_formatos_de_la_ruta_de_datos(fmt, bits, name):
    assert fmt.total_bits == bits
    assert fmt.name == name
    assert fmt.min_int == -(2 ** (bits - 1))
    assert fmt.max_int == 2 ** (bits - 1) - 1

def test_producto_conserva_todos_los_bits():
    # Q1.15 x Q3.15 = Q4.30: se suman bits enteros y bits de fracción
    assert PRODUCT_FORMAT.int_bits == SAMPLE_FORMAT.int_bits + COEF_FORMAT.int_bits
    assert PRODUCT_FORMAT.frac_bits == SAMPLE_FORMAT.frac_bits + COEF_FORMAT.frac_bits
    assert ACC_FORMAT.frac_bits == PRODUCT_FORMAT.frac_bits

def test_producto_extremo_cabe_en_34_bits():
    # El caso más grande: mínimo por mínimo da un resultado positivo de 2^32
    worst = SAMPLE_FORMAT.min_int * COEF_FORMAT.min_int
    assert fits(worst, PRODUCT_FORMAT.total_bits)

def test_acumulador_soporta_cinco_productos_extremos():
    worst = 5 * SAMPLE_FORMAT.min_int * COEF_FORMAT.min_int
    assert fits(worst, ACC_FORMAT.total_bits)
    assert fits(-worst, ACC_FORMAT.total_bits)

# Redondeo
@pytest.mark.parametrize("value, shift, expected", [
    (3, 1, 2),      # 1.5  -> 2  (empate hacia arriba)
    (1, 1, 1),      # 0.5  -> 1  (empate hacia arriba)
    (-1, 1, 0),     # -0.5 -> 0  (empate hacia arriba, no hacia -1)
    (-3, 1, -1),    # -1.5 -> -1 (empate hacia arriba)
    (-4, 1, -2),    # -2.0 -> -2 (exacto)
    (5, 2, 1),      # 1.25 -> 1
    (7, 2, 2),      # 1.75 -> 2
    (-5, 2, -1),    # -1.25 -> -1
    (-7, 2, -2),    # -1.75 -> -2
    (123, 0, 123),  # sin desplazamiento no cambia
])
def test_redondeo_casos_conocidos(value, shift, expected):
    assert round_shift(value, shift) == expected

@pytest.mark.parametrize("shift", [1, 2, 3, 15])
def test_redondeo_igual_a_floor_mas_medio(shift):
    # Regla de redondeo: floor(valor / 2^shift + 0.5), en un rango completo
    for value in range(-70000, 70000, 37):
        assert round_shift(value, shift) == math.floor(value / 2 ** shift + 0.5)

def test_redondeo_rechaza_desplazamiento_negativo():
    with pytest.raises(ValueError):
        round_shift(10, -1)

# Rango y saturación
@pytest.mark.parametrize("value, expected", [
    (40000, 32767),
    (32768, 32767),
    (32767, 32767),
    (0, 0),
    (-32768, -32768),
    (-32769, -32768),
    (-40000, -32768),
])
def test_saturacion_a_16_bits(value, expected):
    assert saturate(value, 16) == expected

def test_fits_en_los_bordes():
    assert fits(32767, 16) and fits(-32768, 16)
    assert not fits(32768, 16) and not fits(-32769, 16)

def test_check_fits_detecta_desborde():
    assert check_fits(100, 16) == 100
    with pytest.raises(OverflowError):
        check_fits(1 << 39, ACC_FORMAT.total_bits, "acumulador")

# Conversión entre decimal y punto fijo
def test_valores_exactos():
    assert to_fixed(1.0, COEF_FORMAT) == 32768       # el 1.0 de las etapas identidad
    assert to_fixed(-1.0, SAMPLE_FORMAT) == -32768
    assert to_fixed(0.0, SAMPLE_FORMAT) == 0
    assert to_fixed(-4.0, COEF_FORMAT) == COEF_FORMAT.min_int

def test_fuera_de_rango_lanza_error_o_satura():
    with pytest.raises(OverflowError):
        to_fixed(1.0, SAMPLE_FORMAT)   # Q1.15 llega hasta 0.99997
    with pytest.raises(OverflowError):
        to_fixed(4.0, COEF_FORMAT)
    assert to_fixed(1.0, SAMPLE_FORMAT, saturate_result=True) == SAMPLE_FORMAT.max_int
    assert to_fixed(-9.0, COEF_FORMAT, saturate_result=True) == COEF_FORMAT.min_int

def test_conversion_usa_la_misma_regla_de_empates():
    half = SAMPLE_FORMAT.step / 2
    assert to_fixed(half, SAMPLE_FORMAT) == 1     # +0.5 LSB -> 1
    assert to_fixed(-half, SAMPLE_FORMAT) == 0    # -0.5 LSB -> 0

@pytest.mark.parametrize("fmt", [SAMPLE_FORMAT, COEF_FORMAT])
def test_ida_y_vuelta_con_error_menor_a_medio_paso(fmt):
    low = to_float(fmt.min_int, fmt)
    high = to_float(fmt.max_int, fmt)
    for i in range(2001):
        value = low + (high - low) * i / 2000
        error = abs(to_float(to_fixed(value, fmt), fmt) - value)
        assert error <= fmt.step / 2

# Complemento a dos y hexadecimal
@pytest.mark.parametrize("value, bits, text", [
    (0, 16, "0000"),
    (1, 16, "0001"),
    (-1, 16, "FFFF"),
    (32767, 16, "7FFF"),
    (-32768, 16, "8000"),
    (32768, 18, "08000"),
    (-71229, 18, "2E9C3"),
    (-1, 18, "3FFFF"),
])
def test_hexadecimal_conocido(value, bits, text):
    assert to_hex(value, bits) == text
    assert from_hex(text, bits) == value


def test_ida_y_vuelta_hexadecimal_todos_los_valores_de_16_bits():
    for value in range(-32768, 32768):
        assert from_hex(to_hex(value, 16), 16) == value


def test_complemento_a_dos_fuera_de_rango():
    with pytest.raises(OverflowError):
        to_unsigned(32768, 16)
    with pytest.raises(ValueError):
        from_unsigned(1 << 16, 16)


def test_formato_personalizado():
    fmt = QFormat(int_bits=2, frac_bits=6)
    assert fmt.total_bits == 8
    assert fmt.step == 1 / 64
    assert to_fixed(1.5, fmt) == 96