"""Punto de entrada de pytest: compila dsp_filter.sv con Verilator y corre dsp_filter_tests.py.

Uso, desde la raíz del repositorio:
    scripts/hw/docker.sh pytest tests/hw/cocotb            # resumen
    scripts/hw/docker.sh pytest -s tests/hw/cocotb         # con la salida completa de cocotb
    ONDAS=1 scripts/hw/docker.sh pytest tests/hw/cocotb    # además guarda las formas de onda
                                                           # (sim_build/ondas/dump.fst)
    COCOTB_TEST_FILTER=tiempos scripts/hw/docker.sh ...    # solo las pruebas que coincidan
    COCOTB_RANDOM_SEED=<semilla> scripts/hw/docker.sh ...  # repite una corrida
"""

import os
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

from cocotb_tools.runner import get_runner

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[2]
RTL = RAIZ / "Reproductor" / "ip" / "dsp_filter" / "dsp_filter.sv"


def test_dsp_filter():
    ondas = os.environ.get("ONDAS") == "1"
    build_dir = AQUI / "sim_build" / ("ondas" if ondas else "normal")

    runner = get_runner("verilator")
    runner.build(
        sources=[RTL],
        hdl_toplevel="dsp_filter",
        build_dir=build_dir,
        timescale=("1ns", "1ps"),
        waves=ondas,
        build_args=["--trace-fst", "--trace-structs"] if ondas else [],
    )
    # El resultado va a build_dir; sin esto cocotb lo deja en esta carpeta
    resultados = runner.test(
        hdl_toplevel="dsp_filter",
        test_module="dsp_filter_tests",
        test_dir=AQUI,
        build_dir=build_dir,
        results_xml=str(build_dir / "results.xml"),
        waves=ondas,
    )

    # Verilator escribe dump.fst en la carpeta de trabajo de la simulación (esta); se mueve
    # junto a la compilación para no dejarlo entre los archivos del repo
    if ondas and (AQUI / "dump.fst").exists():
        shutil.move(AQUI / "dump.fst", build_dir / "dump.fst")

    # El resultado de cada prueba de cocotb queda en un XML (formato JUnit)
    casos = ET.parse(resultados).getroot().findall(".//testcase")
    fallas = [c.get("name") for c in casos
              if c.find("failure") is not None or c.find("error") is not None]
    assert casos, "cocotb no corrió ninguna prueba"
    assert not fallas, f"fallaron: {', '.join(fallas)}"
