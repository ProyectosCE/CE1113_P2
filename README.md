# quartus-tools

Scripts para trabajar con Quartus Prime Lite 25.1std y la DE1-SoC desde la terminal.

Todos los scripts viven en `scripts/` (los ejemplos solo tienen Makefiles), por categoria:

**`scripts/general/`** (cualquier proyecto Quartus / DE1-SoC)

| Script | Funcion |
|---|---|
| `env.sh` | Configura el entorno (Quartus, Nios V, toolchain RISC-V, Questa, licencia SALT) |
| `build.sh` | Sintesis, fitter y assembler: genera el `.sof` desde fuentes + pines, un `.qsys` o un `.qpf` |
| `create-project.sh` | Solo crea el proyecto (.qpf/.qsf) desde un `.qsys`/`.qip` + pines, sin compilar |
| `program.sh` | Programa la FPGA de la DE1-SoC con un `.sof` por JTAG |
| `terminal.sh` | Abre la consola JTAG UART (`juart-terminal`) |

**`scripts/nios/`** (software para el Nios V)

| Script | Funcion |
|---|---|
| `build-sw.sh` | Desde un `.sopcinfo`: crea (si falta) el proyecto de software, genera el BSP y compila el ELF |
| `download.sh` | Descarga un `.elf` al Nios V por JTAG y lo ejecuta |

Plantilla de pines: `de1-soc-pines.qsf` (CLOCK, KEY, SW, LEDR, HEX0-5).

## Requisitos

- Quartus instalado en `~/altera_lite/25.1std` (otra ruta: `export ALTERA_ROOT=/ruta/a/altera_lite/25.1std`).
- DE1-SoC conectada por el USB-Blaster (puerto USB-Blaster II/USB de la placa) y encendida.
- Reglas udev del USB-Blaster (`/etc/udev/rules.d/51-usbblaster.rules`, ya presentes).

## Uso

### Entorno

```bash
source ~/quartus-tools/scripts/general/env.sh
```

Agrega las herramientas al `PATH` de la sesión actual y define `QUARTUS_ROOTDIR` y
`SALT_LICENSE_SERVER` (Questa usa SALT, no `LM_LICENSE_FILE`; por defecto
`~/.altera.quartus/questa_lic.dat`). Tambien agrega `scripts/general/` y `scripts/nios/` al `PATH`,
asi que despues de hacer `source` se pueden llamar sin ruta (`build.sh`, `program.sh`, `terminal.sh`,
`download.sh`, `bake.sh`, `build-sw.sh`, `create-project.sh`). Los demás scripts lo cargan solos.

Para tenerlo en cada terminal: `echo 'source ~/quartus-tools/scripts/general/env.sh' >> ~/.bashrc`.

### Compilar (sintesis -> bitstream)

```bash
# Fuentes + archivo de pines (crea el proyecto automaticamente en ./output)
~/quartus-tools/scripts/general/build.sh -t top_module -p pines.qsf top_module.v otro.sv timing.sdc

# Opciones: -d dispositivo (def. 5CSEMA5F31C6), -o directorio de salida, -n nombre
# Proyecto Quartus existente
~/quartus-tools/scripts/general/build.sh ruta/proyecto.qpf
```

- `-t` es el modulo top-level; las fuentes pueden ser `.v .sv .vhd .qip .sdc`. Con `-q sistema.qsys`
  `-t` es opcional: por defecto es el nombre del sistema (`hello.qsys` -> `hello`); sin HDL propio, un
  `-t` distinto da un error inmediato. `-n` cambia solo el nombre del proyecto (`-t hello -n hello_auto`).
- El archivo de pines es cualquier `.qsf`/`.tcl` con `set_location_assignment` e
  `set_instance_assignment` (p. ej. el de Terasic para la DE1-SoC; los nombres de puerto
  del top deben coincidir con los del archivo, como `CLOCK_50`, `LEDR[0]`).
- Incluya un `.sdc` (p. ej. `create_clock -period 20 [get_ports CLOCK_50]`); sin el, Quartus
  avisa y no optimiza la temporizacion.
- Imprime la ruta del `.sof`; el log completo queda en `build.log`. El `.sof` queda en el directorio de salida (`./output`).

### Sistemas Platform Designer (.qsys)

```bash
# Genera el .qip con qsys-generate, crea el proyecto y compila
~/quartus-tools/scripts/general/build.sh -t hello -p pines.qsf -q hello.qsys timing.sdc
# Solo crear el proyecto (abrirlo en Quartus), sin compilar
~/quartus-tools/scripts/general/create-project.sh -t hello -p pines.qsf -q hello.qsys timing.sdc
# Si ya tiene el .qip generado, pasarlo como fuente
~/quartus-tools/scripts/general/create-project.sh -t hello -p pines.qsf hello/synthesis/hello.qip timing.sdc
```

### Software para Nios V

El `.sopcinfo` (generado junto con el `.qip` por Platform Designer/`qsys-generate`) describe
la plataforma: de el salen el BSP (`system.h` con las bases de cada periferico, linker script,
drivers). Requisitos: `niosv-bsp`/`niosv-app` (incluidos en `env.sh`), `cmake`, la toolchain
`riscv32-unknown-elf` y el USB-Blaster para descargar.

```bash
~/quartus-tools/scripts/nios/build-sw.sh sistema.sopcinfo [directorio] [-n nombre] [-s fuentes] [-f]
```

Un solo comando, solo con el `.sopcinfo` como argumento obligatorio:
- el directorio del proyecto (por defecto `sw/` junto al `.sopcinfo`) se crea si no existe;
- si ya hay codigo (`.c`, `.cpp`, `.S`) en `src/` lo usa tal cual; si no, escribe un `src/main.c`
  minimo (hola mundo por la JTAG UART; cuenta en los LEDs si el sistema tiene un PIO `leds`);
- genera el BSP (`bsp/`, con `system.h`) y lo regenera solo si cambia el `.sopcinfo` (`-f` lo fuerza);
- compila y deja `build/app/build/<nombre>.elf` (por defecto `app.elf`) y `onchip_memory2_0.hex`.

Agregue sus `.c`/`.h` en `src/` y vuelva a ejecutarlo (la app se regenera cada vez). Los ajustes del
BSP estan en la variable `BSP_SETTINGS` (por defecto: drivers reducidos, `-Os`, sin `exit`, pensados
para RAM de 8 KB, donde no cabe `printf`: use `alt_putstr()`). Luego se descarga con
`download.sh build/app/build/app.elf`.

### Programar la FPGA

```bash
~/quartus-tools/scripts/general/program.sh diseno.sof        # dispositivo 2 (FPGA)
~/quartus-tools/scripts/general/program.sh diseno.sof 2      # indice explicito
```

La cadena JTAG de la DE1-SoC tiene dos dispositivos: `1` = HPS (ARM, `SOCVHPS`) y
`2` = FPGA (Cyclone V). Se puede verificar con `jtagconfig`.

### Terminal JTAG UART

```bash
~/quartus-tools/scripts/general/terminal.sh          # instancia 0
~/quartus-tools/scripts/general/terminal.sh 1        # otra instancia de JTAG UART
DEVICE=2 ~/quartus-tools/scripts/general/terminal.sh # dispositivo de la cadena (2 por defecto)
```

Salir con `Ctrl+C`. Requiere que la FPGA ya este programada con un diseno que
incluya el IP *JTAG UART*.

## Flujo tipico

```bash
~/quartus-tools/scripts/general/build.sh -t top -p pines.qsf top.v timing.sdc
~/quartus-tools/scripts/general/program.sh output/top.sof
~/quartus-tools/scripts/general/terminal.sh
```

## Problemas comunes

- **"No se detecta el USB-Blaster"**: revise cable y alimentacion; pruebe `jtagconfig`.
  Si falla, reinicie el demonio: `jtagconfig --stop` (o `killall jtagd`) y reintente.
- **El terminal no muestra nada**: confirme que la FPGA esta programada y que la
  instancia coincide con la de su JTAG UART.

### Descargar un ELF a mano

```bash
~/quartus-tools/scripts/nios/download.sh programa.elf [--no-run] [--no-reset]
```

## Ejemplos

Cada ejemplo tiene su propio `README.md` con los pasos: `ejemplo-blink/` (Verilog + pines) y `ejemplo-niosv/` (Platform Designer + software).

## Ejemplo: blink en la DE1-SoC

`ejemplo-blink/` es un diseno minimo para recorrer todo el flujo: `blink.v` (LED0
parpadea, KEY0 lo apaga), `pines.qsf` (pines de la DE1-SoC) y `timing.sdc` (reloj de 50 MHz).

```bash
cd ejemplo-blink
make          # sintesis + fitter + assembler -> output/blink.sof
make prog     # ademas programa la placa
```

Equivale a:

```bash
../scripts/general/build.sh -t blink -p pines.qsf -o output blink.v timing.sdc
../scripts/general/program.sh output/blink.sof
```

## Ejemplo: SoC Nios V (Platform Designer)

`ejemplo-niosv/` contiene `hello.qsys` (Nios V/m + RAM 8 KB + JTAG UART + 8 LEDs),
`pines.qsf` (reloj, reset en KEY0 y LEDR[7:0], con los nombres de puerto del sistema),
`timing.sdc` y `sw/main.c`. `make hw` genera el qip y sintetiza el `.sof`; `make sw` crea y compila el proyecto de
software; `make prog` programa la FPGA; `make run` descarga el ELF y abre la consola.

> Estado: el hardware y el software compilan, la FPGA se programa y el ELF se descarga y ejecuta (el CPU corre y llega a la JTAG UART).
> La salida de texto en la consola JTAG UART todavia no esta verificada (pendiente de diagnostico).

## Licencia

MIT (ver `LICENSE`).
