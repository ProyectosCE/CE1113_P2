"""Configuración compartida de las pruebas de DSP.

Al final de cada ejecución de pytest imprime qué tan cerca del límite de
estabilidad está cada etapa (radio del polo más lejano). Mientras más se
acerque a 1, más delicada será la etapa al pasarla a punto fijo.
"""

import numpy as np

from filter_config import FILTER_NAMES, IDENTITY, SAMPLE_RATES, build_filters


def pytest_terminal_summary(terminalreporter):
    write = terminalreporter.write_line
    terminalreporter.section("Radio de los polos (estable si < 1)")
    write(f"{'fs (Hz)':>8}  {'filtro':<10}  {'etapa':>5}  {'radio':>8}")

    for fs in SAMPLE_RATES:
        for name in FILTER_NAMES:
            for number, stage in enumerate(build_filters(fs)[name]):
                if stage == IDENTITY:
                    continue
                radius = max(abs(np.roots(stage.a)))
                note = "  <- cerca del límite" if radius > 0.95 else ""
                write(f"{fs:>8}  {name:<10}  {number:>5}  {radius:>8.4f}{note}")