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
| `audio` | Audio Core: espacio libre en el FIFO y escritura de muestras (por sondeo) | Listo; pendiente pasar a interrupción (GIC ID 72) |
| `hex` | `hex_ctrl_0` | Listo |
| `dsp` | `dsp_filter_0`: habilitar, cargar los 15 coeficientes Q3.15, procesar una muestra de un canal, leer SATURO | Listo |
| `sdmmc` | Controlador SD/MMC del HPS | **Pendiente** |

### Reproductor

| Módulo | Función | Estado |
|---|---|---|
| `player` | Estados (detenido, reproduciendo, pausado), botones, canción actual, tiempo | Básico: falta abrir el WAV al cambiar de canción y el avance automático |
| `filtros` | Selección con SW[1:0] y procesamiento por muestra; los tres filtros están en `dsp_filter` | Bypass y `dsp_filter` conectados; falta cargar los coeficientes de cada filtro y procesar los dos canales |
| `volumen` | Factor de ganancia a partir del ADC | Básico (lineal); pendiente curva logarítmica |
| `ui` | HEX (MM:SS, canción), LEDs (filtro y estado), consola | Listo; pendiente pantalla externa |
| `fat` | FAT32 de la SD: contar, nombrar, abrir y leer los `.wav` | **Pendiente** |
| `wav` | Cabecera WAV y metadatos (`LIST/INFO`) | **Pendiente** |
| `remuestreo` | 8/16 kHz → 44.1 kHz | **Pendiente** (hoy deja pasar la muestra) |
| `tono` | Tono de 441 Hz de prueba | Temporal: reemplaza al WAV hasta que existan `fat` y `wav` |

## Qué hace hoy el programa

Sirve como prueba de humo de toda la base:

| Acción | Resultado |
|---|---|
| Arranque | La consola muestra el estado de `hex_ctrl`, `dsp_filter`, SD y FAT (SD y FAT: pendientes) |
| KEY0 | Play / pausa: suena el tono de prueba y corre el tiempo en HEX3–0 |
| KEY1 | Stop: silencio y tiempo a 00:00 |
| KEY2 / KEY3 | Canción anterior / siguiente (10 canciones ficticias), número en HEX5–4 |
| SW[1:0] | Filtro: 0 bypass, 1 pasa-altos, 2 pasa-banda, 3 ecualizador (todos en `dsp_filter`); se ve en LEDR[1:0]. Hoy solo la posición 1 habilita `dsp_filter`, con los coeficientes de reset (identidad) |
| Potenciómetro | Volumen del tono |
| LEDR8 / LEDR9 | Reproduciendo / pausado |

Cada cambio se informa en la consola.

## Memoria

Con `make sw` se imprime el tamaño; el detalle por símbolo queda en `build/reproductor.map`.
El código, los datos y las pilas (IRQ 1 KB, SVC 2 KB) deben caber en los 64 KB de la OCRAM; el
linker falla con un mensaje si no caben. Los buffers de lectura de la SD (bloques de 512 bytes)
y de audio deben dimensionarse con eso en mente.
