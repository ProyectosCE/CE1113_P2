"""Pruebas de los vectores de prueba de dsp/vectors/.

La verificación principal recalcula la salida esperada con el modelo
bit-exacto a partir del input.hex que está en el repositorio. Así se detecta
si el modelo o los coeficientes cambiaron sin regenerar los vectores, y la
prueba da el mismo resultado en cualquier máquina.

Uso:
    pytest dsp -v
"""

from pathlib import Path

import numpy as np
import pytest

from filter_config import SAMPLE_RATES
from fixed_coefficients import COEF_BITS
from fixed_model import SAMPLE_BITS
from fixed_point import from_hex
from generate_vectors import (
    MODES,
    SEGMENTS,
    VECTORS_DIR,
    build_input,
    case_coefficients,
    expected_output,
    readme_text,
    segment_starts,
)

CASES = [(fs, mode) for fs in SAMPLE_RATES for mode in MODES]
TOTAL_SAMPLES = sum(n for _, n, _ in SEGMENTS)

# Señales calculadas solo con enteros: deben coincidir exactamente en
# cualquier máquina (las de senos, chirp y ruido usan decimales)
EXACT_SEGMENTS = ("impulso", "escalon_pos", "escalon_neg", "extremos", "silencio")

def read_hex(path: Path, bits: int) -> list[int]:
    lines = path.read_text().splitlines()
    digits = (bits + 3) // 4
    for line in lines:
        assert len(line) == digits, f"{path}: '{line}' no tiene {digits} dígitos"
        assert line == line.upper(), f"{path}: '{line}' debe ir en mayúsculas"
    return [from_hex(line, bits) for line in lines]

def case_dir(fs: int, mode: str) -> Path:
    return VECTORS_DIR / str(fs) / mode

# Estructura
@pytest.mark.parametrize("fs, mode", CASES)
def test_cada_caso_tiene_sus_tres_archivos(fs, mode):
    for name in ("coefs.hex", "input.hex", "expected.hex"):
        assert (case_dir(fs, mode) / name).is_file()

def test_readme_al_dia():
    assert (VECTORS_DIR / "README.md").read_text() == readme_text()

# Contenido
@pytest.mark.parametrize("fs, mode", CASES)
def test_coeficientes_al_dia(fs, mode):
    coefs = read_hex(case_dir(fs, mode) / "coefs.hex", COEF_BITS)
    assert len(coefs) == 15
    assert coefs == case_coefficients(fs, mode)

@pytest.mark.parametrize("fs, mode", CASES)
def test_entrada_tiene_la_longitud_y_las_senales_exactas(fs, mode):
    samples = read_hex(case_dir(fs, mode) / "input.hex", SAMPLE_BITS)
    assert len(samples) == TOTAL_SAMPLES

    generated = build_input(fs).tolist()
    for name, start, end in segment_starts():
        if name in EXACT_SEGMENTS:
            assert samples[start:end + 1] == generated[start:end + 1], name

@pytest.mark.parametrize("fs", SAMPLE_RATES)
def test_misma_entrada_en_todos_los_modos(fs):
    inputs = [(case_dir(fs, mode) / "input.hex").read_text() for mode in MODES]
    assert all(text == inputs[0] for text in inputs)

@pytest.mark.parametrize("fs, mode", CASES)
def test_salida_esperada_coincide_con_el_modelo(fs, mode):
    # Verificación principal: el modelo actual, con la entrada del repo,
    # debe dar exactamente expected.hex
    samples = np.array(read_hex(case_dir(fs, mode) / "input.hex", SAMPLE_BITS), dtype=np.int16)
    expected = read_hex(case_dir(fs, mode) / "expected.hex", SAMPLE_BITS)
    assert expected_output(fs, mode, samples).tolist() == expected

# Propiedades esperadas
@pytest.mark.parametrize("fs", SAMPLE_RATES)
def test_bypass_igual_a_la_entrada(fs):
    folder = case_dir(fs, "bypass")
    assert (folder / "expected.hex").read_text() == (folder / "input.hex").read_text()


@pytest.mark.parametrize("fs, mode", CASES)
def test_termina_en_silencio_exacto(fs, mode):
    expected = read_hex(case_dir(fs, mode) / "expected.hex", SAMPLE_BITS)
    assert expected[-100:] == [0] * 100