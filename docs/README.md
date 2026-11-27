# Estado de la base del proyecto

Reproductor de audio WAV para la DE1-SoC (CE-1113 Sistemas Empotrados, Proyecto II).

La **base** es el punto de partida sobre el que se implementa el enunciado: todo el hardware del
SoC integrado en Platform Designer y compilando, con direcciones, interrupciones y pines fijos; las
herramientas para cargar código en el ARM por JTAG; y pruebas mínimas que confirman que cada bloque
responde. La funcionalidad del reproductor (filtros, lectura de la SD, metadatos, interfaz) se
construye encima.

Fecha de este estado: 2026-11-26. La base completa (hardware y software) se probó en la placa.

- Para empezar a trabajar: [`GUIA_INICIO.md`](GUIA_INICIO.md)
- Lo que falta y cómo repartirlo: [`TAREAS.md`](TAREAS.md)
- Reglas de colaboración: [`../CONTRIBUTING.md`](../CONTRIBUTING.md)

---

## 1. Resumen

| Parte | Estado |
|---|---|
| HPS (ARM Cortex-A9) en bare metal, cargado por JTAG | Funciona |
| Puente lightweight HPS→FPGA | Funciona |
| LEDs, switches, botones con interrupción | Funciona |
| Audio (codec WM8731 a 44.1 kHz) | Funciona |
| ADC (potenciómetro de volumen) | Funciona |
| Controlador de 7 segmentos (hardware propio) | Funciona |
| Filtro DSP (hardware propio) | Esqueleto integrado (registros completos, paso directo); falta el filtro |
| Pantalla externa para metadatos (VGA/LCD) | Pendiente, fuera de la base |
| Esqueleto de software del reproductor (`Reproductor/sw/`) | Hecho: compila y corre; módulos del enunciado con `TODO` |
| Funcionalidad del enunciado | Pendiente (ver sección 6) |

Uso actual del FPGA (fitter, 2026-11-26): **1 889 ALMs (6 %)**, 2 817 registros, 5 120 bits de
memoria en 4 bloques RAM, 0 bloques DSP, 1 PLL, 157 pines.

---

## 2. Arquitectura

```mermaid
flowchart LR
    subgraph HPS["HPS (Cortex-A9, bare metal)"]
        CPU["Core 0<br/>programa en OCRAM 64 KB"]
        GIC["GIC"]
        SD["Controlador SD/MMC"]
        DDR["DDR3 1 GB<br/>(sin usar en fase 1)"]
    end
    subgraph FPGA["FPGA (reproductor.qsys)"]
        LW["Puente LW<br/>0xFF20_0000"]
        LEDS["leds"]
        SW["switches"]
        KEYS["keys"]
        ADC["adc (LTC2308)"]
        AVC["av_config (I2C)"]
        AUD["audio"]
        PLL["audio_pll_0<br/>11.2896 MHz"]
        JU["jtag_uart_0"]
        HEX["hex_ctrl_0 (propio)"]
        DSP["dsp_filter_0 (propio)"]
        VGA["Pantalla (pendiente)"]
    end
    MSD[("microSD")] --- SD
    CPU --> LW
    LW --> LEDS & SW & KEYS & ADC & AVC & AUD & JU & HEX & DSP
    LW -.-> VGA
    HEX --> DISP(["HEX5..HEX0"])
    KEYS -- "IRQ 1 (ID 73)" --> GIC
    AUD -- "IRQ 0 (ID 72)" --> GIC
    GIC --> CPU
    AVC --> CODEC["WM8731"]
    AUD --> CODEC
    PLL -- AUD_XCK --> CODEC
    CODEC --> OUT(["Line Out"])
```

Las líneas punteadas son bloques pendientes.

**Decisiones de diseño tomadas:**

| Decisión | Motivo |
|---|---|
| El HPS es el único procesador; no se usa Nios V | La microSD solo está cableada al HPS, así que el ARM es obligatorio. Un segundo procesador no tendría una función justificada |
| Fase 1: el programa corre en la **OCRAM** (64 KB) y se carga por JTAG | Probado: sin preloader, el depurador y el CPU acceden a toda la OCRAM. No hace falta inicializar la DDR3 ni tocar la SD con las canciones |
| Codec fijo a **44.1 kHz** | El WM8731 no tiene modo de 16 kHz. Con una sola frecuencia, los WAV de 44.1 kHz suenan sin remuestrear, los filtros usan un solo juego de coeficientes y no se reconfigura el codec entre canciones. Los WAV de 8 y 16 kHz se remuestrean en software |
| ADC **LTC2308** en vez de AD7928 | La placa del grupo es rev. F/G, que trae el LTC2308. El IP y el mapa de registros son los mismos |
| 4 botones para 5 controles | KEY0 = play/pausa (alterna), KEY1 = stop, KEY2 = anterior, KEY3 = siguiente |

---

## 3. Hardware: estado de cada módulo

Todos los periféricos de la FPGA están en el puente lightweight. La dirección para el ARM es
`0xFF20_0000` + offset.

| Módulo | Offset | IRQ (`f2h_irq0` → GIC ID) | Estado | Verificado con |
|---|---|---|---|---|
| `hps_0` | — | — | Funciona | `tests/inc0-hps/` |
| `clk_0` | — | — | Funciona | — |
| `leds` | `0x0000` | — | Funciona | `tests/io-adc/` |
| `hex_ctrl_0` (propio) | `0x0020` | — | Funciona | `tests/hw/`, `tests/hex-dsp/` |
| `switches` | `0x0040` | — | Funciona | `tests/io-adc/` |
| `keys` | `0x0050` | 1 → 73 | Funciona | `tests/io-adc/` |
| `jtag_uart_0` | `0x1000` | — | Funciona | todas las pruebas |
| `av_config` | `0x3000` | — | Funciona | `tests/inc2-audio/` |
| `audio` | `0x3040` | 0 → 72 | Funciona | `tests/inc2-audio/` |
| `audio_pll_0` | — | — | Funciona | `tests/inc2-audio/` |
| `adc` | `0x4000` | — | Funciona | `tests/io-adc/` |
| `dsp_filter_0` (propio) | `0x5000` | — | Esqueleto (paso directo) | `tests/hw/`, `tests/hex-dsp/` |
| Pantalla externa (VGA/LCD) | por definir | — | Pendiente, fuera de la base | — |

### 3.1 `hps_0` — Hard Processor System

El ARM Cortex-A9 que ejecuta todo el software. Configuración relevante:

- **DDR3:** 1 GB a 400 MHz, 32 bits (parámetros de la GHRD de Terasic). No se usa en la fase 1,
  pero debe estar bien configurada para que el fitter ubique los pines y para la fase 2.
- **Pines del HPS:** SD/MMC (HPS I/O Set 0, 4 bits) para la microSD y UART0 (Set 0) para la fase 2.
  Son pines dedicados: no ocupan la FPGA.
- **Interfaces con la FPGA:** solo el puente **lightweight** (maestro hacia los periféricos) y las
  **interrupciones FPGA→HPS**. Los puentes completos y los puertos FPGA→SDRAM están deshabilitados
  porque ningún bloque de la FPGA necesita acceder a la memoria del HPS.
- **Reset:** `h2f_reset` alimenta el reset de toda la lógica de la FPGA, que sale de reset junto con
  el HPS.

Antes de usar los periféricos, el software debe sacar los puentes de reset (`0xFFD0501C` = 0) y
habilitarlos en el L3 (`0xFF800000` |= `0x18`). Sin SD, el BootROM deja activo un watchdog que hay
que retener en reset (`0xFFD05014` |= `0x40`).

### 3.2 `leds` — PIO de salida, 10 bits

LEDR[9:0]. Uso previsto: indicar el filtro activo y el estado de reproducción (requisito "estado
de filtros: indicación visual").

### 3.3 `switches` — PIO de entrada, 10 bits

SW[9:0], leídos por sondeo. Uso previsto: selección del filtro activo. Con un ciclo de sondeo de
pocos milisegundos se cumple el requisito de cambio de filtro en menos de 100 ms.

### 3.4 `keys` — PIO de entrada con interrupción, 4 bits

KEY[3:0]. Captura flancos de bajada (los botones son activos en bajo y la placa ya les quita el
rebote), con limpieza bit a bit del registro de captura e interrupción por flanco. Registros:
datos `+0x0`, máscara de interrupción `+0x8`, captura de flancos `+0xC` (se limpia escribiendo 1
en cada bit).

### 3.5 `jtag_uart_0` — consola de depuración

Consola de texto por el mismo cable USB-Blaster (`scripts/general/terminal.sh`). Se usa porque
en la fase 1 no hay preloader que configure la UART0 del HPS. **Hay que justificarlo en la
documentación o quitarlo antes de la entrega** (requisito: no se permiten componentes sin
funcionalidad justificada).

### 3.6 `audio_pll_0`, `av_config` y `audio` — cadena de audio

| Módulo | Función | Configuración |
|---|---|---|
| `audio_pll_0` (Audio Clock) | Genera el reloj maestro del codec (`AUD_XCK`) | 11.2896 MHz desde los 50 MHz |
| `av_config` (Audio and Video Config) | Configura el WM8731 por I2C al arrancar | 16 bits, Left Justified, Line In sin bypass, *Sampling Rate* 48 kHz (el IP no ofrece 44.1 kHz; con 11.2896 MHz el codec queda en 11.2896 MHz / 256 = 44.1 kHz) |
| `audio` (Audio Core) | FIFOs de 128 muestras por canal hacia el codec | Memory-mapped, solo salida, 16 bits |

Registros del Audio Core: control `+0x0` (bit 1 = interrupción de escritura, bit 3 = vaciar FIFOs
de salida), `fifospace` `+0x4` (bits 31:24 y 23:16 = espacio libre izquierdo/derecho), datos
izquierdo `+0x8` y derecho `+0xC`. La interrupción (ID 72) servirá para llenar el FIFO sin sondeo.

Ajuste pendiente: en `av_config`, *DE Board* quedó en **DE10-Standard**. Funciona porque esa
placa usa el mismo codec, pero conviene cambiarlo a DE1-SoC.

### 3.7 `adc` — ADC Controller for DE-series Boards (LTC2308)

Lee el potenciómetro de volumen en el canal 0 (12 bits). Configurado para DE1-SoC rev. F+, 1 canal,
reloj de 12.5 MHz. Se habilita la conversión continua escribiendo 1 en `+0x4`; el canal 0 se lee
en `+0x0` (bits 11:0). Con el potenciómetro de 10 kΩ entre GND y 3.3 V se lee de 0 a ~3300.

### 3.8 `hex_ctrl` — controlador de 7 segmentos (hardware propio)

Componente Avalon-MM escrito por el grupo en SystemVerilog (`Reproductor/ip/hex_ctrl/`). El software escribe el
tiempo en binario y el hardware hace la conversión a decimal y a 7 segmentos: MM:SS en HEX3–HEX0 y
número de canción en HEX5–HEX4. Cumple el requisito de manejo de los displays en hardware.

| Offset | Registro | Acceso | Contenido |
|---|---|---|---|
| `0x0` | CTRL | RW | bit 0 = encender HEX3–0 (tiempo), bit 1 = encender HEX5–4 (canción) |
| `0x4` | TIEMPO | RW | bits 14:8 minutos (0–99), bits 5:0 segundos (0–59) |
| `0x8` | CANCION | RW | bits 6:0 número de canción (0–99) |
| `0xC` | STATUS | R | bit 0 = el último valor estaba fuera de rango (se muestra saturado); bits 31:16 = ID `0x4E58` |

Verificado en simulación (`tests/hw/`, 8 casos) y en la placa (`tests/hex-dsp/`).

### 3.9 `dsp_filter` — filtro DSP (hardware propio, esqueleto)

El filtro obligatorio en HDL propio, en SystemVerilog (`Reproductor/ip/dsp_filter/`). La interfaz de registros ya está
completa; el procesamiento todavía deja pasar la muestra sin cambios. El filtro real (por ejemplo
un FIR con multiplicador-acumulador) se escribe en el bloque `PROCESAMIENTO` de `dsp_filter.sv` sin
cambiar el mapa de registros.

| Offset | Registro | Acceso | Contenido |
|---|---|---|---|
| `0x00` | CTRL | RW | bit 0 EN (1 = filtrar, 0 = bypass), bit 1 LIMPIAR (borra el estado), bit 2 CANAL (0 = izq., 1 = der.) |
| `0x04` | STATUS | R | bit 0 LISTO, bit 1 OCUPADO |
| `0x08` | DATA_IN | RW | muestra de 16 bits con signo; escribirla inicia el procesamiento |
| `0x0C` | DATA_OUT | R | resultado de 16 bits con signo |
| `0x10` | COEF_IDX | RW | índice del coeficiente |
| `0x14` | COEF_DATA | RW | coeficiente Q1.15 en la posición COEF_IDX |
| `0x18` | INFO | R | ID `0xD5F1`, versión (`0x01` = esqueleto), número de coeficientes (16) |

Uso por muestra: escribir DATA_IN → esperar STATUS.LISTO → leer DATA_OUT. Verificado en
simulación (`tests/hw/`, 5 casos) y en la placa (`tests/hex-dsp/`).

### 3.10 Pantalla externa para metadatos (pendiente, fuera de la base)

Se decidió dejarla para después de la base. Opción prevista con VGA: IP del University Program
*Video Clocks for DE-series Boards* (25 MHz), *Character Buffer* (texto de 80×60 en memoria interna)
y *VGA Controller*. Mostrará título, artista, álbum, duración, número de canción, estado y filtro.

---

## 4. Software: lo que existe

| Ruta | Contenido |
|---|---|
| `scripts/hps/gdb-server.sh` | Arranca el gdb-server de Ashling (incluido en Quartus) para el Cortex-A9 |
| `tests/inc0-hps/` | Arranque mínimo (`start.S`), linker script de la OCRAM (`ocram.ld`), script de carga con gdb (`cargar.gdb`) y prueba de acceso a la OCRAM |
| `tests/inc2-audio/` | Tono de 441 Hz por Line Out; verifica que el codec va a 44.1 kHz |
| `tests/hw/` | Testbenches autoverificables de `hex_ctrl` y `dsp_filter` en Questa (`sim.sh`) |
| `tests/hex-dsp/` | `hex_ctrl` y `dsp_filter` en la placa: cronómetro en los displays y paso directo del filtro |
| `tests/io-adc/` | Arranque con interrupciones (vectores, pila IRQ), configuración del GIC, botones por IRQ, switches y ADC |

Todo usa acceso directo a registros, sin HAL. Flujo de trabajo:

```bash
cd Reproductor && make hw && make prog          # hardware
scripts/hps/gdb-server.sh                         # terminal 1
gdb-multiarch -x tests/inc0-hps/cargar.gdb X.elf  # terminal 2: carga y para en main
scripts/general/terminal.sh                       # terminal 3: consola JTAG UART
```

---

## 5. Software del reproductor

El esqueleto está en `Reproductor/sw/` y se describe en [`Reproductor/sw/README.md`](../Reproductor/sw/README.md):
estructura, estado de cada driver y módulo, y cómo compilar y cargar (`make sw`, `make load`).

Resumen de los módulos y el requisito que cubre cada uno:

| Módulo | Qué hace | Requisito que cubre | Estado |
|---|---|---|---|
| `arranque/` | Vectores, pilas IRQ/SVC, `.bss`, mapa de memoria en OCRAM | Gestión de memoria | Listo |
| `gic`, `keys` | Interrupciones; botones como eventos | Botones por interrupción | Listo |
| `sdmmc` + `fat` | Lectura de la microSD (controlador del HPS) y FAT32 | SD mediante el HPS; ≥10 canciones | Pendiente |
| `wav` | Formato (PCM 16 bits, 8/16/44.1 kHz) y metadatos `LIST/INFO` | Formatos; metadatos | Pendiente |
| `remuestreo` | 8/16 kHz → 44.1 kHz | Formatos (codec fijo a 44.1 kHz) | Pendiente |
| `filtros` + `dsp` | 4 posiciones con SW[1:0]: bypass, hardware, 2 de software | Filtros; latencia < 100 ms | Selección y hardware conectados; faltan los filtros |
| `volumen` + `adc` | Ganancia desde el potenciómetro | Control de volumen | Básico |
| `audio` | FIFO del codec | Reproducción sin cortes | Por sondeo; pendiente por interrupción |
| `player` | Estados, botones, canción, tiempo | Controles; reproducción continua; cambio < 2 s | Básico |
| `ui` + `hex` | MM:SS y canción en 7 segmentos, LEDs, consola | Visualización | Listo salvo pantalla externa |

### 5.1 Las canciones y la microSD (sin Linux)

No se usa Linux en ningún momento: el ARM corre en bare metal y lee la microSD con código propio.

- **Preparar la tarjeta** (en la PC, una vez): formatearla en **FAT32** y copiar los `.wav` (16 bits,
  8/16/44.1 kHz) a la raíz. Los metadatos van dentro del WAV, en el chunk `LIST/INFO`; por ejemplo:
  `ffmpeg -i original.mp3 -ar 44100 -ac 2 -c:a pcm_s16le -metadata title="..." -metadata artist="..." -metadata album="..." cancion01.wav`.
- **En la placa:** `sdmmc.c` maneja el controlador SD/MMC del HPS (comandos de la tarjeta y lectura de
  bloques de 512 bytes), `fat.c` interpreta FAT32 para encontrar y leer los `.wav`, y `wav.c`
  extrae formato y metadatos. Es el requisito "control de almacenamiento (SD) mediante el HPS".
- **Fase 1 (ahora):** el programa se carga por JTAG; la SD solo guarda canciones.
- **Fase 2 (arranque desde la SD):** la misma tarjeta lleva además una partición pequeña con el
  preloader y el programa, y la partición FAT32 con las canciones. Sigue sin haber Linux.

El enunciado pide para el HPS un "sistema operativo mínimo sin visualización ni interacción
directa": el programa bare metal cumple eso.

## 6. Qué falta

### 6.1 Para cerrar la base

- [x] `hex_ctrl`: HDL, componente en Platform Designer, pines HEX0–HEX5.
- [x] `dsp_filter`: esqueleto HDL (registros y paso directo), componente en Platform Designer y
      *testbench* inicial.
- [ ] `av_config`: cambiar *DE Board* a DE1-SoC.
- [x] Esqueleto `sw/` (drivers, módulos con `TODO`) y targets `make sw`, `make load`, `make debug`.
- [ ] Prueba de humo de la base completa.

### 6.2 Funcionalidad del enunciado (sobre la base)

| Requisito | Módulo | Estado |
|---|---|---|
| ≥10 canciones WAV en la SD, leídas por el HPS | `sdmmc.c`, `fat.c` | Pendiente |
| WAV 16 bits a 8, 16 y 44.1 kHz | `wav.c`, `remuestreo.c` | Pendiente |
| Metadatos: título, artista, álbum, duración | `wav.c` | Pendiente (los WAV deben llevar chunk `LIST/INFO`, por ejemplo con `ffmpeg -metadata`) |
| Play, pausa, stop, anterior, siguiente por botones con interrupción | `player.c`, `keys.c`, `gic.c` | Hardware listo; lógica pendiente |
| Estado de reproducción visible | `ui.c` | Pendiente |
| Reproducción continua (siguiente canción al terminar) | `player.c` | Pendiente |
| Tiempo MM:SS en 7 segmentos (hardware) | `hex_ctrl`, `hex.c` | Hardware listo; falta llevar el tiempo de reproducción |
| Metadatos, número de canción y filtro en pantalla | Pantalla externa, `ui.c` | Pendiente (después de la base) |
| ≥3 filtros por switches, uno en HDL propio | `dsp_filter`, `filtros.c` | Interfaz del filtro en hardware lista; faltan los filtros |
| Cambio de filtro < 100 ms; bypass sin distorsión | `filtros.c` | Pendiente |
| Volumen con potenciómetro (ADC) | `adc.c`, `volumen.c` | Hardware listo; lógica pendiente |
| Respuesta a botones < 200 ms; cambio de canción < 2 s | `player.c` | Pendiente |
| Sistema funcionando en < 10 s tras el reset | Fase 2 | Pendiente: con carga por JTAG un reset borra el programa |

### 6.3 Entregables y cierre

- [ ] **Fase 2:** arranque desde la SD (preloader + programa en la tarjeta) para cumplir el tiempo
      de inicio tras el reset.
- [ ] Verificación aislada del `dsp_filter` (*testbench*, casos y resultados documentados).
- [ ] Reporte de recursos (sistema completo y `dsp_filter` por separado) y de potencia
      (PowerPlay Power Analyzer), con la discusión de la partición hardware/software.
- [ ] Justificar o quitar `jtag_uart_0`.
- [ ] Documentos de diseño: software, metodología (incluye las decisiones de la sección 2),
      hardware propio (diagrama de bloques, registros, mapa de memoria, diagramas de tiempo).
- [ ] README final con instalación, compilación, uso, diagramas, evidencias de los filtros,
      capturas y videos.
