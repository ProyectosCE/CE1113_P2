# Reproductor de audio — DE1-SoC

Proyecto II de CE-1113 Sistemas Empotrados: reproductor de audio WAV desde la microSD, con filtros
digitales (al menos uno en hardware propio), control por botones con interrupciones, tiempo en los
7 segmentos y metadatos por VGA.

**Arquitectura:** el HPS (ARM Cortex-A9) corre en bare metal y es el único procesador. Los
periféricos de la FPGA (audio, botones, switches, ADC, 7 segmentos, filtro DSP propio) cuelgan del
puente lightweight HPS-to-FPGA (`0xFF20_0000`).

> Estado: incrementos 0, 1 y 2 ok (ARM cargado por JTAG en la OCRAM; HPS + puente LW + LEDs; audio
> con el codec a 44.1 kHz, ver [`tests/inc2-audio/`](../tests/inc2-audio/README.md)).
>
> Placa: **DE1-SoC rev. F/G** (ADC LTC2308, no AD7928 como dice el enunciado).

## Archivos

| Archivo | Función |
|---|---|
| `reproductor.qsys` | Sistema de Platform Designer (top-level `reproductor`) |
| `pines.qsf` | Asignación de pines de la FPGA (los del HPS son dedicados) |
| `timing.sdc` | Reloj de 50 MHz (`clk_clk`) |
| `Makefile` | Encadena `qsys-generate`, Quartus y la programación por JTAG |

## Requisitos

- Quartus Prime Lite **25.1std** en `~/altera_lite/25.1std` (otra ruta: `export ALTERA_ROOT=...`).
- IP del **University Program** en el IP Catalog (para audio, ADC y VGA; a partir del incremento 2).
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

## Probar el incremento 1

Con la FPGA programada, el gdb-server corriendo (`../scripts/hps/gdb-server.sh`) y gdb conectado
(`gdb-multiarch -ex "set architecture armv7" -ex "target remote :3334"`):

```gdb
set *(unsigned int*)0xFFD05014 = *(unsigned int*)0xFFD05014 | 0x40   # watchdog del BootROM off
set *(unsigned int*)0xFFD0501C = 0        # saca los puentes HPS<->FPGA de reset
set *(unsigned int*)0xFF800000 = 0x18     # habilita los puentes LW y H2F (L3 remap)
set *(unsigned int*)0xFF200000 = 0x3FF    # enciende LEDR[9:0]
```

## Mapa de memoria (puente LW, base `0xFF20_0000`)

| Periférico | Dirección | IRQ (`f2h_irq0` -> GIC ID) | Incremento |
|---|---|---|---|
| `leds` (PIO, 10 bits) | `0xFF20_0000` | — | 1 |
| `hex_ctrl` (propio) | `0xFF20_0020` | — | 4 |
| `switches` (PIO) | `0xFF20_0040` | — | 3 |
| `keys` (PIO + IRQ) | `0xFF20_0050` | 1 -> 73 | 3 |
| `jtag_uart_0` | `0xFF20_1000` | — | 1 |
| `av_config` | `0xFF20_3000` | — | 2 |
| `audio` | `0xFF20_3040` | 0 -> 72 | 2 |
| `adc` | `0xFF20_4000` | — | 3 |
| `dsp_filter` (propio) | `0xFF20_5000` | — | 4 |
| VGA (Character Buffer) | por definir | — | 5 |

## Limpiar

```bash
make clean     # borra output/, reproductor/ y reproductor.sopcinfo
```
