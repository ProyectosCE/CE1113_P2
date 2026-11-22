# Ejemplo: blink (Verilog + archivo de pines)

LED0 de la DE1-SoC parpadea (~0.75 Hz); KEY0 (activo en bajo) lo apaga.

| Archivo | Funcion |
|---|---|
| `blink.v` | Diseno (top-level `blink`) |
| `pines.qsf` | Asignacion de pines: `CLOCK_50`, `KEY[0]`, `LEDR[0]` |
| `timing.sdc` | Reloj de 50 MHz |
| `Makefile` | Llama a los scripts de `../scripts/general/` |

## Pasos

Requisito: Quartus en `~/altera_lite/25.1std` y, para programar, la DE1-SoC encendida y conectada por USB-Blaster.

```bash
cd ejemplo-blink
make          # 1. sintesis + fitter + assembler -> output/blink.sof
make prog     # 2. programa la FPGA con el .sof
make clean    # borra output/
```

Equivale a:

```bash
../scripts/general/build.sh -t blink -p pines.qsf -o output blink.v timing.sdc
../scripts/general/program.sh output/blink.sof
```

Resultado esperado: LEDR0 parpadea; mantener KEY0 presionado lo apaga.
`build.sh` imprime la ruta del `.sof`; el log queda en `output/build.log`.
