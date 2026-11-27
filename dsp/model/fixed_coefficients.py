"""Cuantización de los coeficientes de los filtros a enteros Q3.15 (18 bits).

Convierte los coeficientes decimales de la Fase 1 en los enteros que usará
el hardware y que el software escribirá en los registros del filtro.

Al redondear se conservan exactamente las relaciones de diseño entre
coeficientes. Se detectan en los valores decimales y, si existen, se
redondea un solo coeficiente y los demás se calculan a partir de él:

    b2 =  b0        (pasa-altos)           -> b2 = b0 entero
    b2 = -b0        (pasa-banda)           -> b2 = -b0 entero
    b1 = -2*b0      (pasa-altos)           -> b1 = -2 * b0 entero
    a1 =  b1        (peaking)              -> a1 = b1 entero

Así, por ejemplo, el pasa-altos sigue eliminando por completo la componente
continua (b0 + b1 + b2 = 0 exacto).

Uso:
    python dsp/model/fixed_coefficients.py
"""

import csv
import math
from pathlib import Path
from typing import NamedTuple

from biquad_design import Biquad
from export_coefficients import max_response_error_db, pole_radius
from filter_config import FILTER_NAMES, SAMPLE_RATES, build_filters
from fixed_point import COEF_FORMAT, check_fits, to_fixed, to_float, to_hex

OUTPUT_DIR = Path(__file__).resolve().parents[1] / "output" / "coefficients"

COEF_BITS = COEF_FORMAT.total_bits   # 18
REGISTER_BITS = 32                   # ancho de los registros del bus

# Tolerancia para decidir si dos coeficientes decimales guardan una relación
RELATION_TOL = 1e-9

class FixedBiquad(NamedTuple):
    """Coeficientes de un biquad como enteros Q3.15 (a0 = 1 implícito)."""

    b0: int
    b1: int
    b2: int
    a1: int
    a2: int

# Cuantización
def _same(x: float, y: float) -> bool:
    return math.isclose(x, y, rel_tol=RELATION_TOL, abs_tol=RELATION_TOL)

def quantize_stage(stage: Biquad) -> tuple[FixedBiquad, list[str]]:
    """Cuantiza una etapa a Q3.15 conservando sus relaciones de diseño.

    Devuelve (etapa_entera, relaciones_aplicadas).
    """
    b0 = to_fixed(stage.b0, COEF_FORMAT)
    b1 = to_fixed(stage.b1, COEF_FORMAT)
    b2 = to_fixed(stage.b2, COEF_FORMAT)
    a1 = to_fixed(stage.a1, COEF_FORMAT)
    a2 = to_fixed(stage.a2, COEF_FORMAT)
    relations = []

    if stage.b0 != 0 and _same(stage.b2, stage.b0):
        b2 = b0
        relations.append("b2 = b0")
    elif stage.b0 != 0 and _same(stage.b2, -stage.b0):
        b2 = -b0
        relations.append("b2 = -b0")

    if stage.b0 != 0 and _same(stage.b1, -2 * stage.b0):
        b1 = -2 * b0
        relations.append("b1 = -2*b0")

    if stage.b1 != 0 and _same(stage.a1, stage.b1):
        a1 = b1
        relations.append("a1 = b1")

    # Los valores calculados también deben caber en 18 bits
    for name, value in (("b1", b1), ("b2", b2), ("a1", a1)):
        check_fits(value, COEF_BITS, name)

    return FixedBiquad(b0, b1, b2, a1, a2), relations

def to_float_stage(stage: FixedBiquad) -> Biquad:
    """Valores decimales que representan los enteros Q3.15 de una etapa."""
    return Biquad(*(to_float(v, COEF_FORMAT) for v in stage))

def build_fixed_filters(fs: int) -> dict[str, list[FixedBiquad]]:
    """Etapas enteras Q3.15 de todos los filtros para una frecuencia fs."""
    return {
        name: [quantize_stage(stage)[0] for stage in stages]
        for name, stages in build_filters(fs).items()
    }

# Reporte
def coefficient_rows() -> list[dict]:
    """Una fila por coeficiente con su valor decimal, entero y hexadecimal."""
    rows = []
    for fs in SAMPLE_RATES:
        for index, (name, stages) in enumerate(build_filters(fs).items()):
            for number, stage in enumerate(stages):
                fixed, _ = quantize_stage(stage)
                for field in FixedBiquad._fields:
                    value = getattr(fixed, field)
                    rows.append({
                        "fs": fs,
                        "filtro": index,
                        "nombre": name,
                        "etapa": number,
                        "coef": field,
                        "decimal": getattr(stage, field),
                        "entero": value,
                        "hex18": to_hex(value, COEF_BITS),
                        "hex32": to_hex(value, REGISTER_BITS),
                    })
    return rows

def write_csv(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow({**row, "decimal": f"{row['decimal']:.10f}"})

def print_report() -> bool:
    """Imprime la tabla y el análisis. Devuelve True si todo es estable."""
    all_stable = True
    for fs in SAMPLE_RATES:
        print(f"=== fs = {fs} Hz ===")
        for index, (name, stages) in enumerate(build_filters(fs).items()):
            fixed_stages = []
            for number, stage in enumerate(stages):
                fixed, relations = quantize_stage(stage)
                fixed_stages.append(fixed)
                values = "  ".join(f"{f}={v:>7d} ({to_hex(v, COEF_BITS)})"
                                   for f, v in fixed._asdict().items())
                print(f"[{index}] {name:<10} etapa {number}: {values}")

                radius_before = pole_radius(stage)
                radius_after = pole_radius(to_float_stage(fixed))
                stable = radius_after < 1
                all_stable &= stable
                note = ", ".join(relations) if relations else "sin relaciones"
                print(f"{'':<25} radio {radius_before:.6f} -> {radius_after:.6f} "
                      f"{'estable' if stable else 'INESTABLE'}; {note}")

            error = max_response_error_db(
                stages, [to_float_stage(s) for s in fixed_stages], fs)
            print(f"{'':<25} error abs máx de la respuesta: {error:.1f} dB\n")
    return all_stable

def main() -> None:
    stable = print_report()

    path = OUTPUT_DIR / "coeficientes_q3_15.csv"
    write_csv(coefficient_rows(), path)
    print(f"Tabla de enteros guardada en {path}")

    if not stable:
        raise SystemExit("Error: hay etapas inestables después de cuantizar")


if __name__ == "__main__":
    main()