# Pull Request

## Descripción

Integra a `Develop` la **base del proyecto**: todo el hardware del SoC en Platform Designer compilando y probado en la DE1-SoC, el esqueleto de software del ARM (bare metal) corriendo, pruebas por bloque y la documentación para que el grupo implemente el resto del enunciado sobre esta base.

Arquitectura elegida: el **HPS (ARM Cortex-A9) en bare metal** es el único procesador (la microSD solo está cableada al HPS); los periféricos de la FPGA cuelgan del puente lightweight (`0xFF20_0000`). En esta fase el programa corre en la OCRAM (64 KB) y se carga por JTAG.

## Issue relacionado

Related to #

## Tipo de cambio

- [x] Hardware (RTL SystemVerilog, Platform Designer, pines)
- [x] Software / firmware
- [ ] DSP / filtros
- [x] Verificación (testbench, pruebas)
- [ ] Corrección de error
- [ ] Refactorización
- [x] Documentación
- [x] Build / CI / configuración

## Cambios realizados

**Hardware (`Reproductor/`)**
- `reproductor.qsys`: HPS configurado para la DE1-SoC (DDR3 1 GB a 400 MHz, SD/MMC y UART0 en pines del HPS, puente lightweight, interrupciones FPGA→HPS); se eliminan Nios V y RAM on-chip.
- Periféricos: `leds`, `switches`, `keys` (IRQ), `jtag_uart_0`, cadena de audio (`audio_pll_0` a 11.2896 MHz, `av_config`, `audio`; codec fijo a 44.1 kHz) y `adc` (LTC2308, placa rev. F/G).
- Hardware propio en SystemVerilog (`ip/`): `hex_ctrl` (MM:SS y número de canción en los 7 segmentos, completo) y `dsp_filter` (mapa de registros completo, procesamiento de paso directo como esqueleto).
- `pines.qsf` con todos los puertos; `Makefile` con `make hw` (incluye la asignación de pines de la DDR3 del HPS), `prog`, `report`, `qsys`.

**Software del ARM (`Reproductor/sw/`)**
- Arranque (`start.S`: vectores, watchdog del BootROM, pilas IRQ/SVC) y `ocram.ld`.
- `include/hw.h` con todas las direcciones e IRQ.
- Drivers sin HAL: `hps`, `gic`, `jtag_uart`, `leds`, `switches`, `keys`, `adc`, `audio`, `hex`, `dsp`; `sdmmc` como esqueleto.
- Módulos del reproductor: `player`, `filtros`, `volumen`, `ui` funcionando en versión básica; `fat`, `wav`, `remuestreo` como esqueleto con `TODO`; `tono` como fuente de audio de prueba.
- `Makefile`: `make sw`, `gdbserver`, `load`, `debug`, `consola`.

**Pruebas (`tests/`)**
- `hw/`: testbenches autoverificables de `hex_ctrl` y `dsp_filter` en Questa (`sim.sh`).
- Pruebas en la placa: `inc0-hps` (carga por JTAG y OCRAM), `inc2-audio` (codec a 44.1 kHz), `io-adc` (botones por IRQ, switches, ADC), `hex-dsp` (hardware propio).

**Scripts y documentación**
- `scripts/hps/gdb-server.sh`: gdb-server de Ashling (incluido en Quartus) para el Cortex-A9.
- `README.md` principal del proyecto; la documentación de los scripts pasa a `scripts/README.md`.
- `docs/README.md` (arquitectura, decisiones, módulos y registros), `docs/TAREAS.md` (lo que falta, paquetes y reparto), `docs/GUIA_INICIO.md`, `CONTRIBUTING.md`.

## Impacto en el sistema

- [x] Modifica el sistema de Platform Designer (`.qsys`) o el mapa de memoria.
- [x] Modifica registros o la interfaz de un módulo de hardware.
- [x] Modifica la asignación de pines o la configuración del proyecto de Quartus.

**Detalle del impacto:**

Sistema nuevo completo; todos deben regenerar el hardware (`make clean && make hw`). Mapa del puente lightweight (base `0xFF20_0000`):

| Periférico | Offset | IRQ (`f2h_irq0` → GIC ID) |
|---|---|---|
| `leds` | `0x0000` | — |
| `hex_ctrl_0` | `0x0020` | — |
| `switches` | `0x0040` | — |
| `keys` | `0x0050` | 1 → 73 |
| `jtag_uart_0` | `0x1000` | — |
| `av_config` | `0x3000` | — |
| `audio` | `0x3040` | 0 → 72 |
| `adc` | `0x4000` | — |
| `dsp_filter_0` | `0x5000` | — |

Requisitos nuevos del entorno: `gcc-arm-none-eabi`, `binutils-arm-none-eabi`, `gdb-multiarch` y reglas udev del USB-Blaster (ver `docs/GUIA_INICIO.md`).

## Validación

- [x] El hardware se genera y sintetiza correctamente en Quartus, si aplica.
- [x] El firmware compila correctamente, si aplica.
- [ ] La simulación o el testbench en Questa pasa correctamente, si aplica. <!-- marcar tras correr tests/hw/sim.sh todos -->
- [x] Se probó en tarjeta (DE1-SoC / DE10-Standard), si aplica.
- [x] Se revisó la documentación modificada, si aplica.

**Detalle de validación:**

Todo probado en la DE1-SoC rev. F/G:

- Carga por JTAG: el depurador y el CPU acceden a los 64 KB de OCRAM sin preloader (`tests/inc0-hps`).
- Audio: tono de 441 Hz por Line Out; 60 s de audio medidos en ~60 s, codec a 44.1 kHz (`tests/inc2-audio`).
- Botones por interrupción (GIC ID 73), switches a LEDs y ADC de 0 a 3308 con potenciómetro de 10 kΩ a 3.3 V (`tests/io-adc`).
- `hex_ctrl` (cronómetro MM:SS, número de canción) y `dsp_filter` (ID `0xD5F10110`, paso directo correcto) en la placa (`tests/hex-dsp`).
- Esqueleto de software completo: play/pausa/stop/anterior/siguiente, tiempo en displays, selección de filtro y volumen funcionando con el tono de prueba.
- Recursos: 1 889 ALMs (6 %), 2 817 registros, 0 bloques DSP.

## Checklist

- [x] El PR apunta a la rama correcta (`develop`, salvo integraciones a `main`).
- [x] El PR contiene únicamente cambios relacionados con su objetivo.
- [ ] No se agregaron archivos generados por Quartus, Questa o la compilación, ni temporales o de caché. <!-- revisar git status / la pestaña Files changed -->
- [x] La documentación fue actualizada si el cambio lo requiere.
- [x] El PR está listo para revisión.
