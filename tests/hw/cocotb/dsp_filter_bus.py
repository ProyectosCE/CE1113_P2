"""Acceso a dsp_filter desde cocotb, como lo hace el ARM por el puente Avalon-MM.

Las señales del bus cambian en el flanco de bajada y el RTL las captura en el de subida, igual que
en tests/hw/tb_dsp_filter.sv, para que el testbench y el diseño nunca cambien en el mismo instante.
"""

from pathlib import Path

from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, ReadOnly, RisingEdge

# Registros: avs_address = offset / 4
CTRL, STATUS, DATA_IN, DATA_OUT, COEF_IDX, COEF_DATA, INFO = range(7)

CTRL_EN = 1 << 0
CTRL_LIMPIAR = 1 << 1
CTRL_CANAL = 1 << 2

STATUS_LISTO = 1 << 0
STATUS_OCUPADO = 1 << 1
STATUS_SATURO = 1 << 2

NUM_COEF = 15
PERIODO_NS = 20     # 50 MHz, el reloj del puente lightweight
ESPERA_MAX = 100    # ciclos máximos esperando LISTO

RAIZ = Path(__file__).resolve().parents[3]
VECTORES = RAIZ / "dsp" / "vectors"     # vectores del modelo (dsp/vectors/README.md)
MODELO = RAIZ / "dsp" / "model"         # modelo bit-exacto (fixed_model.py)


def con_signo(valor, bits=32):
    """Interpreta un entero sin signo de `bits` bits como número con signo."""
    valor &= (1 << bits) - 1
    return valor - (1 << bits) if valor >> (bits - 1) else valor


def leer_hex(ruta, bits):
    """Lee un archivo .hex de los vectores (un valor por línea) como enteros con signo."""
    with open(ruta) as f:
        return [con_signo(int(linea, 16), bits) for linea in f if linea.strip()]


class DspFilter:
    """Maneja un dsp_filter simulado: reloj, reset y accesos a sus registros."""

    def __init__(self, dut):
        self.dut = dut

    @classmethod
    async def iniciar(cls, dut):
        """Arranca el reloj de 50 MHz, deja el bus en reposo y hace un reset de 3 ciclos."""
        dsp = cls(dut)
        Clock(dut.clk, PERIODO_NS, unit="ns").start()
        dut.avs_address.value = 0
        dut.avs_read.value = 0
        dut.avs_write.value = 0
        dut.avs_writedata.value = 0
        dut.reset.value = 1
        for _ in range(3):
            await FallingEdge(dut.clk)
        dut.reset.value = 0
        return dsp

    async def escribir(self, registro, valor):
        """Escribe un registro: write = 1 durante un ciclo."""
        await FallingEdge(self.dut.clk)
        self.dut.avs_address.value = registro
        self.dut.avs_writedata.value = valor & 0xFFFFFFFF
        self.dut.avs_write.value = 1
        await FallingEdge(self.dut.clk)
        self.dut.avs_write.value = 0

    async def leer(self, registro):
        """Lee un registro (latencia de 1 ciclo) y devuelve el valor de 32 bits sin signo."""
        await FallingEdge(self.dut.clk)
        self.dut.avs_address.value = registro
        self.dut.avs_read.value = 1
        await FallingEdge(self.dut.clk)
        self.dut.avs_read.value = 0
        return self.dut.avs_readdata.value.to_unsigned()

    async def cargar_coeficientes(self, coefs):
        """Carga los 15 coeficientes Q3.15 (enteros con signo); también borra el estado."""
        assert len(coefs) == NUM_COEF, f"se esperaban {NUM_COEF} coeficientes"
        for i, c in enumerate(coefs):
            await self.escribir(COEF_IDX, i)
            await self.escribir(COEF_DATA, c)

    async def procesar(self, muestra, canal=0, en=True):
        """Procesa una muestra como el driver del ARM: CTRL, DATA_IN, esperar LISTO, DATA_OUT.

        Devuelve (salida, ciclos). `ciclos` cuenta los flancos de subida desde el que acepta
        DATA_IN (el primero) hasta el que pone LISTO en 1: 20 con el filtro y 2 en bypass. Se mide
        con la señal interna `listo` para que sea exacto; DATA_OUT se lee por el bus.
        """
        await self.escribir(CTRL, (CTRL_EN if en else 0) | (CTRL_CANAL if canal else 0))
        await self.escribir(DATA_IN, muestra & 0xFFFF)
        ciclos = 1
        while str(self.dut.listo.value) != "1":
            assert ciclos < ESPERA_MAX, f"LISTO no subió en {ESPERA_MAX} ciclos"
            await RisingEdge(self.dut.clk)
            await ReadOnly()
            ciclos += 1
        salida = con_signo(await self.leer(DATA_OUT))
        return salida, ciclos
