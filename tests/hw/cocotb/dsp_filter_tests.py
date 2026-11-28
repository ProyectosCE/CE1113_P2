"""Pruebas de cocotb para dsp_filter.

No se corren directamente: test_dsp_filter.py compila el RTL y las lanza dentro del simulador.
"""

import cocotb

from dsp_filter_bus import INFO, VECTORES, DspFilter, leer_hex

FRECUENCIAS = [8000, 16000, 44100]
MODOS = ["highpass", "bandpass", "equalizer", "bypass"]


@cocotb.test()
async def info_e_identidad(dut):
    """INFO y la identidad de reset: con EN = 1 y sin cargar coeficientes la muestra sale igual."""
    dsp = await DspFilter.iniciar(dut)

    info = await dsp.leer(INFO)
    assert info == 0xD5F1020F, f"INFO = {info:#010x}"

    for muestra in (0, 1, -1, 32767, -32768, 1234):
        salida, _ = await dsp.procesar(muestra, canal=0, en=True)
        assert salida == muestra, f"muestra {muestra}: salida {salida}"


@cocotb.test()
@cocotb.parametrize(fs=FRECUENCIAS, modo=MODOS)
async def vectores(dut, fs, modo):
    """Los vectores de dsp/vectors/<fs>/<modo>: salida igual a fixed_model.py, muestra por muestra.

    En bypass se cargan los coeficientes del ecualizador con EN = 0: la salida es la entrada.
    """
    carpeta = VECTORES / str(fs) / modo
    coefs = leer_hex(carpeta / "coefs.hex", 18)
    entrada = leer_hex(carpeta / "input.hex", 16)
    esperado = leer_hex(carpeta / "expected.hex", 16)

    dsp = await DspFilter.iniciar(dut)      # reset: el estado arranca en cero, como el modelo
    await dsp.cargar_coeficientes(coefs)

    distintas = []
    for i, (x, y_esp) in enumerate(zip(entrada, esperado)):
        y, _ = await dsp.procesar(x, canal=0, en=(modo != "bypass"))
        if y != y_esp:
            distintas.append((i, x, y_esp, y))

    detalle = "\n".join(f"  muestra {i}: entrada {x}, esperado {e}, obtenido {o}"
                         for i, x, e, o in distintas[:5])
    assert not distintas, (f"{fs}/{modo}: {len(distintas)} de {len(entrada)} muestras distintas\n"
                           + detalle)
