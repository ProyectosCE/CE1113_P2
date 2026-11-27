# Pull Request

<!-- El título del PR debe seguir Conventional Commits, por ejemplo: feat(dsp): agregar núcleo del filtro FIR -->

## Descripción

<!-- Explicar brevemente qué cambia este Pull Request y por qué es necesario. -->

Integra a `develop` la base del proyecto: todo el hardware del SoC en Platform Designer compilando y probado en la DE1-SoC, el esqueleto de software del ARM (bare metal) corriendo, pruebas por bloque y la documentación para que el grupo implemente el resto del enunciado sobre esta base.

El HPS (ARM Cortex-A9) en bare metal es el único procesador, porque la microSD solo está cableada al HPS. Los periféricos de la FPGA cuelgan del puente lightweight (`0xFF20_0000`). En esta fase el programa corre en la OCRAM (64 KB) y se carga por JTAG.

## Issue relacionado

<!-- Usar "Closes #<número>" si este PR cierra un issue, o "Related to #<número>" si solo está relacionado. -->

Closes #

## Tipo de cambio

<!-- Marcar las opciones que correspondan: -->

- [x] Hardware (RTL SystemVerilog, Platform Designer, pines)
- [x] Software / firmware
- [ ] DSP / filtros
- [x] Verificación (testbench, pruebas)
- [ ] Corrección de error
- [ ] Refactorización
- [x] Documentación
- [x] Build / CI / configuración

## Cambios realizados

<!-- Resumir los cambios principales realizados en este PR. -->

- `reproductor.qsys`: HPS configurado para la DE1-SoC (DDR3 1 GB a 400 MHz, SD/MMC y UART0, puente lightweight, interrupciones FPGA->HPS); se eliminan Nios V y la RAM on-chip.
- Periféricos en la FPGA: `leds`, `switches`, `keys` (IRQ), `jtag_uart_0`, audio (`audio_pll_0` a 11.2896 MHz, `av_config`, `audio`; codec fijo a 44.1 kHz) y `adc` (LTC2308, placa rev. F/G).
- Hardware propio en SystemVerilog (`Reproductor/ip/`): `hex_ctrl` (MM:SS y número de canción en los 7 segmentos) y `dsp_filter` (mapa de registros completo, procesamiento de paso directo como esqueleto).
- `pines.qsf` con todos los puertos; `Makefile` con `make hw` (incluye los pines de la DDR3 del HPS), `prog`, `report`, `qsys`, `sw`, `gdbserver`, `load`, `debug`, `consola`.
- Software del ARM (`Reproductor/sw/`): arranque y mapa de memoria en OCRAM, `hw.h` con direcciones e IRQ, drivers sin HAL (`hps`, `gic`, `jtag_uart`, `leds`, `switches`, `keys`, `adc`, `audio`, `hex`, `dsp`) y módulos del reproductor (`player`, `filtros`, `volumen`, `ui`; `sdmmc`, `fat`, `wav`, `remuestreo` como esqueleto con `TODO`).
- Pruebas (`tests/`): testbenches autoverificables de `hex_ctrl` y `dsp_filter` (`hw/sim.sh`) y pruebas en la placa (`inc0-hps`, `inc2-audio`, `io-adc`, `hex-dsp`).
- CI en GitHub Actions (`.github/workflows/ci.yml`): valida el formato `[TAG] Descripción` de los commits y del título del PR (`docs/development/commit-convention.md`), lint del SystemVerilog con Verilator y compilación del firmware sin warnings.
- `scripts/hps/gdb-server.sh` para depurar el Cortex-A9 con el gdb-server de Ashling incluido en Quartus.
- Documentación: `README.md` principal del proyecto, `scripts/README.md`, `docs/README.md` (arquitectura y módulos), `docs/TAREAS.md` (lo que falta), `docs/GUIA_INICIO.md` y `CONTRIBUTING.md`.

## Impacto en el sistema

<!-- Marcar si aplica. Estos cambios obligan al resto del equipo a regenerar el hardware o el BSP. -->

- [x] Modifica el sistema de Platform Designer (`.qsys`) o el mapa de memoria.
- [x] Modifica registros o la interfaz de un módulo de hardware.
- [x] Modifica la asignación de pines o la configuración del proyecto de Quartus.

**Detalle del impacto:**

<!-- Ejemplo: nuevo periférico en 0x0001_0000, cambio de offset en el registro de control del filtro, etc. -->

Sistema nuevo completo: todos deben regenerar el hardware (`make clean && make hw`). Mapa del puente lightweight (base `0xFF20_0000`):

| Periférico | Offset | IRQ (`f2h_irq0` -> GIC ID) |
|---|---|---|
| `leds` | `0x0000` | - |
| `hex_ctrl_0` | `0x0020` | - |
| `switches` | `0x0040` | - |
| `keys` | `0x0050` | 1 -> 73 |
| `jtag_uart_0` | `0x1000` | - |
| `av_config` | `0x3000` | - |
| `audio` | `0x3040` | 0 -> 72 |
| `adc` | `0x4000` | - |
| `dsp_filter_0` | `0x5000` | - |

Requisitos nuevos del entorno: `gcc-arm-none-eabi`, `binutils-arm-none-eabi`, `gdb-multiarch` y reglas udev del USB-Blaster (ver `docs/GUIA_INICIO.md`).

## Validación

<!-- Indicar brevemente cómo se verificó que los cambios funcionan correctamente. -->

- [x] El hardware se genera y sintetiza correctamente en Quartus, si aplica.
- [x] El firmware compila correctamente, si aplica.
- [x] La simulación o el testbench en Questa pasa correctamente, si aplica.
- [x] Se probó en tarjeta (DE1-SoC / DE10-Standard), si aplica.
- [x] Se revisó la documentación modificada, si aplica.

**Detalle de validación:**

<!-- Ejemplo: simulación del filtro contra el modelo de referencia, prueba de audio en la DE1-SoC, revisión manual, etc. Adjuntar capturas o formas de onda si es útil. -->

Todo probado en la DE1-SoC rev. F/G:

- Carga por JTAG: el depurador y el CPU acceden a los 64 KB de OCRAM sin preloader (`tests/inc0-hps`).
- Audio: tono de 441 Hz por Line Out; 60 s de audio medidos en ~60 s, codec a 44.1 kHz (`tests/inc2-audio`).
- Botones por interrupción (GIC ID 73), switches a LEDs y ADC de 0 a 3308 con potenciómetro de 10 kΩ a 3.3 V (`tests/io-adc`).
- Simulación en Questa de `hex_ctrl` y `dsp_filter` (`tests/hw/sim.sh todos`).
- `hex_ctrl` (cronómetro MM:SS, número de canción) y `dsp_filter` (ID `0xD5F10110`, paso directo correcto) en la placa (`tests/hex-dsp`).
- Esqueleto de software: play/pausa/stop/anterior/siguiente, tiempo en displays, selección de filtro y volumen funcionando con el tono de prueba.
- Recursos: 1 889 ALMs (6 %), 2 817 registros, 0 bloques DSP.

## Checklist

- [x] El PR apunta a la rama correcta (`develop`, salvo integraciones a `main`).
- [x] El PR contiene únicamente cambios relacionados con su objetivo.
- [ ] No se agregaron archivos generados por Quartus, Questa o la compilación, ni temporales o de caché.
- [x] La documentación fue actualizada si el cambio lo requiere.
- [x] El PR está listo para revisión.
