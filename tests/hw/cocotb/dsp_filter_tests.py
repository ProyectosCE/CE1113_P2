"""Pruebas de cocotb para dsp_filter.

No se corren directamente: test_dsp_filter.py compila el RTL y las lanza dentro del simulador.
"""

import random
import sys

import cocotb
from cocotb.triggers import FallingEdge, ReadOnly, RisingEdge

from dsp_filter_bus import (COEF_DATA, COEF_IDX, CTRL, CTRL_EN, CTRL_LIMPIAR, DATA_IN, DATA_OUT,
                            INFO, MODELO, STATUS, STATUS_LISTO, STATUS_OCUPADO, STATUS_SATURO,
                            VECTORES, DspFilter, con_signo, leer_hex)

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
    repite una corrida con COCOTB_RANDOM_SEED=<semilla>).
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


# ---------------- Tiempos y protocolo (sección 10 de la especificación) ----------------
# El ciclo 0 es el de la escritura de DATA_IN; sus efectos se ven desde el ciclo 1. Las señales
# internas se miran ciclo a ciclo para que la cuenta sea exacta.

REPOSO, MAC, CIERRE_ETAPA, SALIDA = range(4)
FSM_FILTRO = ([MAC] * 5 + [CIERRE_ETAPA]) * 3 + [SALIDA]      # ciclos 1 a 19
ESTADO_FILTRO = ("x1", "x2", "y1", "y2", "residuo")


def valor(senal):
    """Valor entero (sin signo) de una señal del RTL, de 1 bit o de varios."""
    v = senal.value
    return v.to_unsigned() if hasattr(v, "to_unsigned") else int(str(v))


def foto_estado(dut):
    """Historiales y residuo de los dos canales y las tres etapas, como enteros."""
    return {nombre: valor(getattr(dut, nombre)) for nombre in ESTADO_FILTRO}


async def seguir(dut, ciclos):
    """Desde el ciclo 1 (justo después de la escritura) anota estado, listo y ocupado de cada
    ciclo hasta `ciclos`. Devuelve una lista cuyo índice es el número de ciclo (el 0 sin usar)."""
    traza = [None]
    for n in range(1, ciclos + 1):
        if n > 1:
            await RisingEdge(dut.clk)
            await ReadOnly()
        traza.append((valor(dut.estado), valor(dut.listo), valor(dut.ocupado), valor(dut.data_out)))
    return traza


@cocotb.test()
async def tiempos_filtro(dut):
    """Sección 10.1: ciclos 1-19 con OCUPADO; MAC x5 y CIERRE por etapa, SALIDA en el 19;
    desde el ciclo 20 LISTO = 1, OCUPADO = 0 y DATA_OUT con el resultado."""
    dsp = await DspFilter.iniciar(dut)          # coeficientes de reset: identidad
    await dsp.escribir(CTRL, CTRL_EN)
    await dsp.escribir(DATA_IN, 1000)
    traza = await seguir(dut, 21)

    for n in range(1, 20):
        estado, listo, ocupado, _ = traza[n]
        assert estado == FSM_FILTRO[n - 1], f"ciclo {n}: estado {estado}, esperado {FSM_FILTRO[n - 1]}"
        assert (listo, ocupado) == (0, 1), f"ciclo {n}: LISTO = {listo}, OCUPADO = {ocupado}"
    for n in (20, 21):
        estado, listo, ocupado, data_out = traza[n]
        assert (estado, listo, ocupado) == (REPOSO, 1, 0), f"ciclo {n}: {traza[n]}"
        assert data_out == 1000, f"ciclo {n}: DATA_OUT = {data_out}"
    dut._log.info("filtro: OCUPADO en los ciclos 1-19, LISTO desde el ciclo 20")


@cocotb.test()
async def tiempos_bypass(dut):
    """Sección 10.3: con EN = 0 la FSM va de REPOSO a SALIDA; LISTO = 1 desde el ciclo 2."""
    dsp = await DspFilter.iniciar(dut)
    await dsp.escribir(CTRL, 0)
    await dsp.escribir(DATA_IN, 1234)
    traza = await seguir(dut, 3)

    assert traza[1][:3] == (SALIDA, 0, 1), f"ciclo 1: {traza[1]}"
    for n in (2, 3):
        estado, listo, ocupado, data_out = traza[n]
        assert (estado, listo, ocupado) == (REPOSO, 1, 0), f"ciclo {n}: {traza[n]}"
        assert data_out == 1234, f"ciclo {n}: DATA_OUT = {data_out}"
    dut._log.info("bypass: OCUPADO en el ciclo 1, LISTO desde el ciclo 2")


@cocotb.test()
async def bypass_conserva_estado(dut):
    """Sección 10.3: una muestra en bypass no cambia x1, x2, y1, y2 ni el residuo."""
    dsp = await DspFilter.iniciar(dut)
    await dsp.cargar_coeficientes(coeficientes(build_fixed_filters(FS_PLACA)["bandpass"]))
    for x in ruido(40):
        await dsp.procesar(x, canal=0, en=True)
        await dsp.procesar(-x, canal=1, en=True)

    antes = foto_estado(dut)
    assert all(antes.values()), f"el estado debía ser distinto de cero: {antes}"
    await dsp.procesar(12345, canal=0, en=False)
    await dsp.procesar(-12345, canal=1, en=False)
    despues = foto_estado(dut)
    assert despues == antes, "el bypass cambió el estado del filtro"


@cocotb.test()
async def carga_coeficiente(dut):
    """Sección 10.2: escribir COEF_DATA guarda el coeficiente y, en el mismo flanco, borra el
    estado de los dos canales y SATURO; OCUPADO sigue en 0."""
    dsp = await DspFilter.iniciar(dut)
    ganancia4 = [0x1FFFF, 0, 0, 0, 0] + [0x08000, 0, 0, 0, 0] * 2    # b0 ~ 4 en la etapa 0
    await dsp.cargar_coeficientes(ganancia4)
    for x in (32767, 1000, -3000):                  # 32767 satura la etapa 0; con tres muestras
        await dsp.procesar(x, canal=0, en=True)     # por canal se llenan x2 e y2
        await dsp.procesar(-x, canal=1, en=True)
    assert valor(dut.saturo) == 1, "SATURO debía quedar en 1"
    assert all(foto_estado(dut).values()), "el estado debía ser distinto de cero"

    await dsp.escribir(COEF_IDX, 6)
    await dsp.escribir(COEF_DATA, 0xFFFF1650)       # ejemplo de la sección 5.4
    # Ciclo 1: ya pasó el flanco de la escritura
    assert all(v == 0 for v in foto_estado(dut).values()), "el estado no se borró"
    assert valor(dut.saturo) == 0, "SATURO no se borró"
    assert valor(dut.ocupado) == 0, "OCUPADO debía seguir en 0"
    leido = await dsp.leer(COEF_DATA)
    assert leido == 0xFFFF1650, f"COEF_DATA = {leido:#010x}"


@cocotb.test()
async def protocolo_status(dut):
    """STATUS leído justo después de escribir DATA_IN da OCUPADO = 1 y nunca el LISTO de la
    muestra anterior; después LISTO y DATA_OUT se mantienen hasta la siguiente muestra."""
    dsp = await DspFilter.iniciar(dut)
    await dsp.procesar(111, canal=0, en=True)       # LISTO = 1 de esta muestra

    await dsp.escribir(DATA_IN, 222)
    st = await dsp.leer(STATUS)
    assert st & (STATUS_LISTO | STATUS_OCUPADO) == STATUS_OCUPADO, f"STATUS = {st:#x}"

    lecturas = 0
    while not (await dsp.leer(STATUS)) & STATUS_LISTO:
        lecturas += 1
        assert lecturas < 50, "LISTO no subió"
    for _ in range(25):                             # más que una muestra entera
        st = await dsp.leer(STATUS)
        assert st & (STATUS_LISTO | STATUS_OCUPADO) == STATUS_LISTO, f"STATUS = {st:#x}"
        salida = con_signo(await dsp.leer(DATA_OUT))
        assert salida == 222, f"DATA_OUT = {salida}"


@cocotb.test()
async def descarte_data_in(dut):
    """Sección 4.3: una escritura de DATA_IN con OCUPADO = 1 se ignora: LISTO llega en el ciclo
    20 de la primera muestra y DATA_OUT es su resultado."""
    dsp = await DspFilter.iniciar(dut)
    await dsp.escribir(CTRL, CTRL_EN)
    await dsp.escribir(DATA_IN, 111)
    tarea = cocotb.start_soon(seguir(dut, 21))      # anota mientras se hace la segunda escritura
    for _ in range(3):
        await FallingEdge(dut.clk)
    await dsp.escribir(DATA_IN, 222)                # en pleno procesamiento
    traza = await tarea

    for n in range(1, 20):
        assert traza[n][1:3] == (0, 1), f"ciclo {n}: LISTO/OCUPADO = {traza[n][1:3]}"
    assert traza[20][1:4] == (1, 0, 111), f"ciclo 20: {traza[20]}"
    assert valor(dut.data_in) == 111, "DATA_IN debía conservar la primera muestra"
