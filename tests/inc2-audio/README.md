# Prueba de audio

Toca un tono triangular de **441 Hz** por **Line Out** (jack verde) y verifica que el codec trabaje a
**44.1 kHz**. Usa el arranque y el linker script de `../inc0-hps/`.

| Indicador | Significado |
|---|---|
| LEDR9 encendido | El programa arrancó y los puentes HPS→FPGA están habilitados |
| LEDR0 parpadea | Cambia cada 44 100 muestras enviadas (cada 1 s si el codec va a 44.1 kHz) |
| JTAG UART | Cada 10 s de audio imprime `audio enviado: N s` |

## Pasos

Requisitos: FPGA programada con el sistema de `Reproductor/` (`make hw && make prog`) y audífonos o parlantes en Line Out, **a volumen bajo** al principio.

```bash
# Compilar
cd tests/inc2-audio
arm-none-eabi-gcc -mcpu=cortex-a9 -marm -O1 -g -nostdlib -ffreestanding \
    -T ../inc0-hps/ocram.ld ../inc0-hps/start.S main.c -o inc2.elf

# Terminal 1: gdb-server
../../scripts/hps/gdb-server.sh

# Terminal 2: cargar y ejecutar
gdb-multiarch -x ../inc0-hps/cargar.gdb inc2.elf
(gdb) continue

# Terminal 3: consola JTAG UART
../../scripts/general/terminal.sh
```

## Verificación de la frecuencia de muestreo

Con un cronómetro, mida cuánto tarda la consola en pasar de `audio enviado: 10 s` a
`audio enviado: 70 s`:

| Tiempo medido | Frecuencia real del codec |
|---|---|
| ~60 s | **44.1 kHz** (correcto) |
| ~55 s | 48 kHz: revisar `AUD_XCK` (Audio Clock en 12.288 MHz) |
| no avanza | El FIFO no se vacía: el codec no recibe reloj o no se configuró por I2C |

## Resultados

Prueba hecha el 2026-11-26 en la DE1-SoC rev. F/G del grupo.

| Prueba | Resultado |
|---|---|
| Tono de 441 Hz por Line Out | Se escucha |
| De `audio enviado: 10 s` a `70 s` | **~60 s** con cronómetro → codec a **44.1 kHz** |

Configuración del sistema con la que se probó: Audio Clock a 11.2896 MHz y `av_config` con
*Sampling Rate* = 48 kHz (el IP no ofrece 44.1 kHz; como el codec divide su reloj maestro entre 256,
11.2896 MHz / 256 = 44.1 kHz). Audio Core de 16 bits, solo salida, memory-mapped.
