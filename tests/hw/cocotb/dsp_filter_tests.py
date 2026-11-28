"""Pruebas de cocotb para dsp_filter.

No se corren directamente: test_dsp_filter.py compila el RTL y las lanza dentro del simulador.
"""

import cocotb

from dsp_filter_bus import INFO, DspFilter


@cocotb.test()
async def info_e_identidad(dut):
    """INFO y la identidad de reset: con EN = 1 y sin cargar coeficientes la muestra sale igual."""
    dsp = await DspFilter.iniciar(dut)

    info = await dsp.leer(INFO)
    assert info == 0xD5F1020F, f"INFO = {info:#010x}"

    for muestra in (0, 1, -1, 32767, -32768, 1234):
        salida, _ = await dsp.procesar(muestra, canal=0, en=True)
        assert salida == muestra, f"muestra {muestra}: salida {salida}"
