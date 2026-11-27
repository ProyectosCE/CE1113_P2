# Reproductor de audio — DE1-SoC

Proyecto II de CE-1113 Sistemas Empotrados: reproductor de audio WAV desde la microSD, con filtros
digitales (al menos uno en hardware propio), control por botones con interrupciones, tiempo en los
7 segmentos y metadatos por VGA.

**Arquitectura:** el HPS (ARM Cortex-A9) corre en bare metal y es el único procesador. Los
periféricos de la FPGA (audio, botones, switches, ADC, 7 segmentos, filtro DSP propio) cuelgan del
puente lightweight HPS-to-FPGA (`0xFF20_0000`).

> Estado de la base, módulos y pendientes: [`docs/README.md`](../docs/README.md).
>
> Placa: **DE1-SoC rev. F/G** (ADC LTC2308, no AD7928 como dice el enunciado).

## Archivos

| Archivo | Función |
|---|---|
| `reproductor.qsys` | Sistema de Platform Designer (top-level `reproductor`) |
| `pines.qsf` | Asignación de pines de la FPGA (los del HPS son dedicados) |
| `timing.sdc` | Reloj de 50 MHz (`clk_clk`) |
| `Makefile` | Hardware (`qsys-generate`, Quartus, programación) y software del ARM (`make sw`, `make load`) |
| `ip/` | Componentes propios: `hex_ctrl`, `dsp_filter` |
| `sw/` | Software del ARM (bare metal) |

## Requisitos

- Quartus Prime Lite **25.1std** en `~/altera_lite/25.1std` (otra ruta: `export ALTERA_ROOT=...`).
- IP del **University Program** en el IP Catalog (audio, ADC y VGA). Vienen con Quartus 25.1std.
- DE1-SoC conectada por el USB-Blaster II y reglas udev instaladas (ver *Reglas udev del
  USB-Blaster* en el [README raíz](../README.md)). `jtagconfig` debe mostrar `4BA00477 SOCVHPS` (1)
  y `02D120DD 5CSE(BA5|MA5)` (2).
- Software del ARM: compilador de 32 bits y gdb con soporte ARM:
  `sudo apt install gcc-arm-none-eabi binutils-arm-none-eabi gdb-multiarch`.
  El gdb-server para el Cortex-A9 es el de Ashling que viene con Quartus
  (`riscfree/debugger/gdbserver-arm/ash-arm-gdb-server`); se arranca con `scripts/hps/gdb-server.sh`.

Entorno en cada terminal:

```bash
source ../scripts/general/env.sh
```

## Compilar el hardware

```bash
cd Reproductor
make qsys      # (opcional) editar el sistema en Platform Designer
make hw        # qsys-generate -> proyecto -> pines DDR3 -> síntesis/fitter -> output/reproductor.sof
make prog      # programa la FPGA por JTAG
make report    # resumen de recursos (ALMs, registros, memoria, DSP)
```

Qué hace `make hw`:

1. `build.sh -C` genera el sistema (`qsys-generate`) y crea `output/reproductor.qpf` con el `.qip`,
   los pines y el `.sdc`.
2. `quartus_map` (Analysis & Synthesis).
3. `quartus_sta -t .../hps_sdram_p0_pin_assignments.tcl` agrega al proyecto las asignaciones de los
   pines de la DDR3 del HPS. Sin este paso el fitter falla con errores de I/O en `memory_*`.
4. Compilación completa -> `output/reproductor.sof`.

Logs: `output/map.log`, `output/pin_assign.log`, `output/build.log`.

Si el paso 3 falla desde la terminal, abra `output/reproductor.qpf` en Quartus, corra *Analysis &
Synthesis*, luego **Tools > Tcl Scripts** -> `hps_sdram_p0_pin_assignments.tcl` -> Run, y compile.

## Software del ARM

```bash
make sw          # compila sw/build/reproductor.elf
make gdbserver   # terminal 1 (se queda corriendo)
make consola     # terminal 2
make load        # terminal 3: carga y ejecuta (o make debug para abrir gdb en main)
```

Estructura, módulos y estado: [`sw/README.md`](sw/README.md).

## Probar el puente HPS->FPGA (LEDs)

Con la FPGA programada, el gdb-server corriendo (`../scripts/hps/gdb-server.sh`) y gdb conectado
(`gdb-multiarch -ex "set architecture armv7" -ex "target remote :3334"`):

```gdb
set *(unsigned int*)0xFFD05014 = *(unsigned int*)0xFFD05014 | 0x40   # watchdog del BootROM off
set *(unsigned int*)0xFFD0501C = 0        # saca los puentes HPS<->FPGA de reset
set *(unsigned int*)0xFF800000 = 0x18     # habilita los puentes LW y H2F (L3 remap)
set *(unsigned int*)0xFF200000 = 0x3FF    # enciende LEDR[9:0]
```

## Mapa de memoria (puente LW, base `0xFF20_0000`)

| Periférico | Dirección | IRQ (`f2h_irq0` -> GIC ID) |
|---|---|---|
| `leds` (PIO, 10 bits) | `0xFF20_0000` | — |
| `hex_ctrl` (propio) | `0xFF20_0020` | — |
| `switches` (PIO) | `0xFF20_0040` | — |
| `keys` (PIO + IRQ) | `0xFF20_0050` | 1 -> 73 |
| `jtag_uart_0` | `0xFF20_1000` | — |
| `av_config` | `0xFF20_3000` | — |
| `audio` | `0xFF20_3040` | 0 -> 72 |
| `adc` | `0xFF20_4000` | — |
| `dsp_filter` (propio) | `0xFF20_5000` | — |

## Audio

El codec WM8731 trabaja fijo a **44.1 kHz**: el Audio Clock genera `AUD_XCK` = 11.2896 MHz y el
codec divide su reloj maestro entre 256. En `av_config` el *Sampling Rate* dice 48 kHz porque el IP
no ofrece 44.1 kHz; con ese reloj el resultado es 44.1 kHz. Verificado con
[`tests/inc2-audio/`](../tests/inc2-audio/README.md).

## Limpiar

```bash
make clean     # borra output/, reproductor/ y reproductor.sopcinfo
```
