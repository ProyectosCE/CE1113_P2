# Software del reproductor (ARM Cortex-A9, bare metal)

Corre en el HPS sin sistema operativo, en la OCRAM (64 KB en `0xFFFF0000`), y se carga por JTAG.
Acceso directo a registros, sin HAL. Todas las direcciones están en `include/hw.h`.

## Compilar, cargar y ver la consola

Desde `Reproductor/`, con la FPGA ya programada (`make prog`):

```bash
make sw          # compila sw/build/reproductor.elf (muestra el tamaño)
make gdbserver   # terminal 1: gdb-server del Cortex-A9 (se queda corriendo)
make consola     # terminal 2: consola JTAG UART
make load        # terminal 3: carga el programa y lo deja corriendo
make debug       # en vez de load: carga y abre gdb detenido en main
```

Requiere `gcc-arm-none-eabi`, `binutils-arm-none-eabi` y `gdb-multiarch`.

## Estructura

```
sw/
├── arranque/
│   ├── start.S        vectores, watchdog, VBAR, pilas IRQ/SVC, .bss, salto a main
│   └── ocram.ld       mapa de memoria: código y datos en la OCRAM, pilas al final
├── include/hw.h       direcciones del HPS y del sistema de Platform Designer, IDs de IRQ
├── drivers/           un módulo por periférico
├── reproductor/       lógica del reproductor
├── main.c             inicialización y lazo principal
└── cargar.gdb         script de make debug
```

### Drivers

| Módulo | Periférico | Estado |
|---|---|---|
| `hps` | Puentes HPS→FPGA, watchdog del BootROM | Listo |
| `gic` | Controlador de interrupciones: registro de manejadores y despacho | Listo |
| `jtag_uart` | Consola de depuración | Listo |
| `leds`, `switches` | PIO | Listo |
| `keys` | Botones por interrupción (GIC ID 73); entrega eventos al lazo principal | Listo |
| `adc` | LTC2308, conversión continua | Listo |
| `audio` | Audio Core por interrupción (GIC ID 72) con cola de 2048 tramas; si la cola se vacía manda silencio | Listo |
| `hex` | `hex_ctrl_0` | Listo |
| `dsp` | `dsp_filter_0`: habilitar, coeficientes, procesar una muestra | Listo (el hardware es aún paso directo) |
| `sdmmc` | Controlador SD/MMC del HPS: inicialización (CMD0/8, ACMD41, CMD2/3/7, ACMD6) y lectura de sectores por sondeo; bus de 4 bits con respaldo a 1 bit | Listo (solo lectura) |

### Reproductor

| Módulo | Función | Estado |
|---|---|---|
| `player` | Estados, botones, abre el WAV de la canción actual y entrega sus muestras ya remuestreadas a 44.1 kHz (`player_muestra`); avanza solo al terminar | Listo |
| `filtros` | Selección con SW[1:0] y procesamiento por muestra | Bypass y filtro en hardware conectados; filtros de software **pendientes** |
| `volumen` | Factor de ganancia a partir del ADC | Básico (lineal); pendiente curva logarítmica |
| `ui` | HEX (MM:SS, canción), LEDs (filtro y estado), consola | Listo; pendiente pantalla externa |
| `fat` | FAT32 de la SD (con MBR o sin particiones): lista los `.wav` del directorio raíz con nombre largo, abre, lee y busca | Listo (solo raíz, nombres ASCII) |
| `wav` | Cabecera WAV (PCM 16 bits, mono/estéreo) y metadatos `LIST/INFO` (título, artista, álbum) antes o después de `data` | Listo |
| `remuestreo` | Cualquier frecuencia de 4 a 48 kHz → 44.1 kHz, interpolación lineal | Listo |
| `tono` | Tono de 441 Hz de prueba | Respaldo: suena solo si no hay SD o no tiene `.wav` |

## Qué hace hoy el programa

Sirve como prueba de humo de toda la base:

| Acción | Resultado |
|---|---|
| Arranque | La consola muestra `hex_ctrl`, `dsp_filter`, la SD (bus, capacidad) y la lista de `.wav` |
| KEY0 | Play / pausa de la canción actual; el tiempo corre en HEX3–0 |
| KEY1 | Stop: vuelve al inicio de la canción, tiempo a 00:00 |
| KEY2 / KEY3 | Canción anterior / siguiente de la SD, número en HEX5–4; la consola muestra título, artista, álbum y duración |
| SW[1:0] | Filtro: 0 bypass, 1 hardware, 2 y 3 software (pendientes); se ve en LEDR[1:0] |
| Potenciómetro | Volumen |
| LEDR8 / LEDR9 | Reproduciendo / pausado |

Cada cambio se informa en la consola.

## La tarjeta SD

- **Encienda la placa con la SD ya puesta.** El BootROM es el que configura el reloj y los
  pines del controlador; si la SD se mete después, `sdmmc_iniciar` falla.
- FAT32 (lo normal en tarjetas de hasta 32 GB). Los `.wav` van en la raíz; las carpetas como
  `System Volume Information`, los archivos ocultos y los `._*` de macOS se ignoran.
- WAV PCM de 16 bits, mono o estéreo, de 4 a 48 kHz (se remuestrea a 44.1 kHz).
- Si la SD falla, la consola dice en qué paso (`sdmmc_error`) y el programa sigue con el tono.

`fat.c`, `wav.c` y `remuestreo.c` se probaron en la computadora contra una imagen FAT32 de
prueba (nombre largo, archivo fragmentado, `LIST` antes y después de `data`, 8/16/44.1 kHz):
los datos leídos son idénticos a los originales.

## Relojes, caché e interrupciones (sin preloader)

Al cargar por JTAG no corre ningún preloader, así que el firmware hace lo que él haría:

- `hps_iniciar()` → `hps_relojes()` programa el PLL principal: CPU a 800 MHz, L3/L4 a
  200/100 MHz. Sin esto todo el HPS corre con el oscilador de 25 MHz y no alcanza para leer la
  SD y reproducir. `h2f_user0` y el reloj de la SD se dejan en 25 MHz, como estaban.
- `start.S` enciende la caché de instrucciones y la predicción de saltos.
- `gic_iniciar()` cierra las interrupciones que hayan quedado activas: el GIC no se reinicia al
  volver a hacer `make load`, y si gdb detuvo el programa dentro de una interrupción, el audio
  y los botones quedaban bloqueados.
- El Makefile compila con `-mno-unaligned-access`: sin MMU la memoria es *strongly-ordered* y
  un acceso desalineado (gcc junta lecturas de bytes) da *data abort*.
- La consola por JTAG UART es lenta: imprimir mucho mientras suena vacía la cola de audio y se
  oyen pausas. Imprima solo en eventos (botones, cambio de canción).

## Memoria

Con `make sw` se imprime el tamaño; el detalle por símbolo queda en `build/reproductor.map`.
El código, los datos y las pilas (IRQ 1 KB, SVC 2 KB) deben caber en los 64 KB de la OCRAM; el
linker falla con un mensaje si no caben. Los buffers de lectura de la SD (bloques de 512 bytes)
y de audio deben dimensionarse con eso en mente.
