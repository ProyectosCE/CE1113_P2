"""Pruebas de cocotb para dsp_filter.

No se corren directamente: test_dsp_filter.py compila el RTL y las lanza dentro del simulador.
"""

import random
import sys

import cocotb

from dsp_filter_bus import (CTRL, CTRL_EN, CTRL_LIMPIAR, INFO, MODELO, STATUS, STATUS_SATURO,
                            VECTORES, DspFilter, leer_hex)

sys.path.insert(0, str(MODELO))
from fixed_coefficients import build_fixed_filters  # noqa: E402
from fixed_model import FixedBiquadCascade          # noqa: E402

FRECUENCIAS = [8000, 16000, 44100]
MODOS = ["highpass", "bandpass", "equalizer", "bypass"]
FS_PLACA = 44100        # el codec de la placa trabaja a 44,1 kHz


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


# ---------------- Comparación directa con el modelo ----------------

class Referencia:
    """Modelo bit-exacto con un estado por canal y los mismos coeficientes, como el RTL."""

    def __init__(self, etapas):
        self.canales = [FixedBiquadCascade(etapas), FixedBiquadCascade(etapas)]
        self.base = [0, 0]      # saturaciones contadas antes del último borrado de SATURO

    def cargar(self, etapas):
        """Como escribir COEF_DATA: coeficientes nuevos y estado de los dos canales en cero."""
        for c in self.canales:
            c.load_coefficients(etapas)
        self.base = [0, 0]

    def limpiar(self):
        """Como CTRL.LIMPIAR: estado de los dos canales en cero."""
        for c in self.canales:
            c.reset()
        self.base = [c.saturations for c in self.canales]

    def bypass(self, activo):
        for c in self.canales:
            c.bypass = activo

    def procesar(self, muestra, canal):
        return self.canales[canal].process_sample(muestra)

    @property
    def saturo(self):
        """Lo que debe mostrar STATUS.SATURO: alguna etapa saturó desde el último borrado."""
        return any(c.saturations > b for c, b in zip(self.canales, self.base))


def coeficientes(etapas):
    """Los 15 coeficientes en orden de carga (b0 b1 b2 a1 a2 por etapa)."""
    return [valor for etapa in etapas for valor in etapa]


def ruido(n):
    """n muestras de ruido en tramos de 100 con amplitud al azar, algunos a escala completa.

    Usa el módulo random, que cocotb siembra al arrancar (la semilla sale en el registro y se
    repite una corrida con RANDOM_SEED=<semilla>).
    """
    muestras = []
    while len(muestras) < n:
        amplitud = random.choice([500, 2000, 8000, 20000, 32767])
        minimo = -32768 if amplitud == 32767 else -amplitud
        muestras += [random.randint(minimo, amplitud) for _ in range(100)]
    return muestras[:n]


async def tramo_estereo(dut, dsp, ref, pares, en, nombre):
    """Procesa `pares` muestras izquierda/derecha intercaladas (señales distintas en cada canal),
    compara cada salida con el modelo y al final compara STATUS.SATURO."""
    izquierda, derecha = ruido(pares), ruido(pares)
    distintas = []
    for i, (xi, xd) in enumerate(zip(izquierda, derecha)):
        for canal, x in ((0, xi), (1, xd)):
            y, _ = await dsp.procesar(x, canal=canal, en=en)
            y_ref = ref.procesar(x, canal)
            if y != y_ref:
                distintas.append((i, canal, x, y_ref, y))

    detalle = "\n".join(f"  par {i}, canal {c}: entrada {x}, esperado {e}, obtenido {o}"
                         for i, c, x, e, o in distintas[:5])
    assert not distintas, (f"{nombre}: {len(distintas)} de {2 * pares} muestras distintas\n"
                           + detalle)

    saturo = bool(await dsp.leer(STATUS) & STATUS_SATURO)
    assert saturo == ref.saturo, f"{nombre}: SATURO = {int(saturo)}, el modelo dice {int(ref.saturo)}"
    dut._log.info(f"{nombre}: {2 * pares} muestras iguales al modelo, SATURO = {int(saturo)}")


@cocotb.test()
@cocotb.parametrize(filtro=["highpass", "bandpass", "equalizer"])
async def estereo_aleatorio(dut, filtro):
    """Ruido estéreo intercalado a 44,1 kHz: cada canal con su estado, igual al modelo."""
    etapas = build_fixed_filters(FS_PLACA)[filtro]
    dsp = await DspFilter.iniciar(dut)
    await dsp.cargar_coeficientes(coeficientes(etapas))
    ref = Referencia(etapas)
    await tramo_estereo(dut, dsp, ref, 1500, en=True, nombre=filtro)


@cocotb.test()
async def cambio_de_filtro(dut):
    """Secuencia estéreo continua con cambios de filtro, bypass y LIMPIAR a 44,1 kHz.

    El tramo en bypass no recarga coeficientes: al volver a EN = 1 el pasa-banda debe seguir con
    el estado que tenía (EN = 0 no toca el estado).
    """
    filtros = build_fixed_filters(FS_PLACA)
    dsp = await DspFilter.iniciar(dut)
    ref = Referencia(filtros["highpass"])

    await dsp.cargar_coeficientes(coeficientes(filtros["highpass"]))
    await tramo_estereo(dut, dsp, ref, 300, en=True, nombre="pasa-altos")

    await dsp.cargar_coeficientes(coeficientes(filtros["bandpass"]))
    ref.cargar(filtros["bandpass"])
    await tramo_estereo(dut, dsp, ref, 300, en=True, nombre="pasa-banda")

    ref.bypass(True)
    await tramo_estereo(dut, dsp, ref, 200, en=False, nombre="bypass (EN = 0)")
    ref.bypass(False)
    await tramo_estereo(dut, dsp, ref, 300, en=True, nombre="pasa-banda después del bypass")

    await dsp.escribir(CTRL, CTRL_EN | CTRL_LIMPIAR)
    ref.limpiar()
    await tramo_estereo(dut, dsp, ref, 300, en=True, nombre="pasa-banda después de LIMPIAR")

    await dsp.cargar_coeficientes(coeficientes(filtros["equalizer"]))
    ref.cargar(filtros["equalizer"])
    await tramo_estereo(dut, dsp, ref, 300, en=True, nombre="ecualizador")
