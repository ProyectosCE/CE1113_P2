# Ejemplo: SoC Nios V con Platform Designer

SoC en `hello.qsys`: Nios V/m, RAM on-chip de 8 KB, JTAG UART y 8 LEDs (PIO `leds`).
El programa (`sw/src/main.c`) saluda por la JTAG UART y cuenta en binario en LEDR[7:0].

| Archivo | Funcion |
|---|---|
| `hello.qsys` | Sistema Platform Designer (top-level `hello`) |
| `pines.qsf` | Pines: `clk_clk`, `reset_reset_n` (KEY0), `leds_external_connection_export[7:0]` (LEDR) |
| `timing.sdc` | Reloj de 50 MHz |
| `sw/` | Proyecto de software (`src/main.c`), compilado por `build-sw.sh` |
| `Makefile` | Encadena los scripts de `../scripts/general/` y `../scripts/nios/` |

## Pasos

Requisitos: Quartus 25.1std con Nios V y RiscFree, `cmake`, y la DE1-SoC conectada por USB-Blaster.

### Flujo por defecto: descarga por JTAG

El hardware se compila una vez; para cada cambio de software solo se recompila y se descarga el ELF
(el CPU se resetea y arranca el programa nuevo), sin tocar el bitstream.

```bash
cd ejemplo-niosv
make hw      # 1. qsys-generate -> .qip/.sopcinfo -> proyecto -> output/hello.sof
make sw      # 2. crea sw/ desde hello.sopcinfo y compila -> sw/build/app/build/app.elf
make prog    # 3. programa la FPGA con output/hello.sof
make dl      # 4. resetea el CPU, descarga el ELF por JTAG y lo ejecuta
make run     # 5. consola JTAG UART (Ctrl+C para salir)
```

Para cambiar el programa: edite `sw/src/main.c` y repita `make dl` (no hace falta reprogramar).
`dl` usa `scripts/nios/download.sh` (reset con `swreset 2`: el `-r` de `niosv-download` falla en 25.1).
Si cambia `hello.qsys`, repita desde `make hw` (el BSP se regenera solo al cambiar el `.sopcinfo`).

### Alternativa: firmware dentro del bitstream (`bake`, como el Proyecto I)

No usa depurador. La RAM se inicializa desde `ram.hex` (en ceros en `make hw`) y
`scripts/nios/bake.sh` reemplaza su contenido en el `.sof` en segundos
(`quartus_cdb --update_mif` + `quartus_asm`):

```bash
make bake      # output/hello_fw.sof (con firmware); conserva output/hello.sof (sin firmware)
make prog-fw   # programa hello_fw.sof: el CPU arranca solo
make run
```

### Variante sin modulo de debug

`hello_nodebug.qsys` es el mismo sistema con `enableDebug=false`. Sin debug no hay descarga por JTAG;
solo `bake`:

```bash
make SYS=hello_nodebug all bake prog-fw   # salida en output-hello_nodebug/ y sw-hello_nodebug/
make run
```

## Modulo de debug del Nios V

`hello.qsys` tiene `enableDebug=true` (y `enableDebugReset=true`, con `dbg_reset_out` conectado a
`ndm_reset_in`). El modulo de debug es lo que permite descargar el ELF y depurar por JTAG
(`dm_agent`); la JTAG UART es un periferico aparte y funciona sin el.

**Verificado en la placa:** sin el modulo de debug el CPU corre y la JTAG UART funciona (con `bake`), pero
no se puede descargar el ELF por JTAG: el debug es indispensable para la descarga, no para ejecutar.
Quitarlo tambien es una medida de seguridad: con debug encendido, quien tenga el cable JTAG puede pausar
el CPU y leer cualquier direccion que alcance (p. ej. secretos en perifericos). El Proyecto I del curso de
Seguridad del Hardware lo deja apagado por esa razon y carga el firmware con `bake`.

## Estado

Verificado en la placa con `hello.qsys`: la descarga por JTAG (`make prog`, `make dl`, `make run`) y `bake`
(el saludo sale por la JTAG UART y los LEDs cuentan).
La variante sin debug (`hello_nodebug`) funciona **solo con `bake`**; `make SYS=hello_nodebug dl` falla
(`Cannot lock device 2 ... USB driver error`: el gdb-server no encuentra un depurador).

Nota de diseno: en `hello.qsys` la JTAG UART y los LEDs deben colgar de `data_manager` (no de
`instruction_manager`) y no solaparse con el timer (`0x12000-0x1203f`); un error ahi dejaba al CPU
colgado esperando la UART.

Con el modulo de debug activado (`enableDebug`), `dm_agent` debe estar conectado **tanto a `data_manager`
como a `instruction_manager`**, con la misma direccion base (`0x0`, sin solaparse con la RAM en `0x10000`).
Los maestros "entran" al agente: el CPU ejecuta la ROM del modulo de debug a traves de esos dos buses.
Si falta, `make dl` falla con `Could not halt the target: timeout occurred` (el hart nunca puede
detenerse), aunque `enableDebug` este en `true` y el sistema se genere sin errores. Con RAM de 8 KB no cabe `printf`; use `alt_putstr()`.

## Reconstruir todo a mano (sin Makefile)

Los mismos pasos que hace el `Makefile`, ejecutando los scripts uno por uno. Parta de una copia
limpia: solo `hello.qsys`, `pines.qsf` y `timing.sdc` (`sw/src/main.c` es opcional: si falta, el paso 2 genera
un hola mundo).
Todas las rutas son relativas a `ejemplo-niosv/`; `S` abrevia la carpeta de scripts.

```bash
cd ~/quartus-tools/ejemplo-niosv
S=../scripts
```

### 1. Hardware: sistema Platform Designer + sintesis

```bash
$S/general/build.sh -t hello -p pines.qsf -q hello.qsys -m zero -o output timing.sdc
```

Hace, en orden: `qsys-generate` de `hello.qsys` (deja `hello/synthesis/hello.qip` y `hello.sopcinfo`),
crea el proyecto Quartus en `output/` con el `.qip`, `pines.qsf` y `timing.sdc`, crea `output/ram.hex`
en ceros (`-m zero`, la RAM se inicializa desde ese archivo) y compila (sintesis, fitter, assembler).
Resultado: `output/hello.sof` y `hello.sopcinfo`. Tarda unos 3 minutos. Para solo crear el proyecto
sin compilar, use `$S/general/create-project.sh` con los mismos argumentos.

### 2. Software: BSP y programa desde el `.sopcinfo`

```bash
$S/nios/build-sw.sh hello.sopcinfo                 # crea/usa sw/ junto al .sopcinfo
$S/nios/build-sw.sh hello.sopcinfo otro_dir -n fw   # directorio propio y ELF fw.elf
$S/nios/build-sw.sh hello.sopcinfo sw -s ../codigo  # fuentes en otra carpeta (relativa a sw/)
```

Si `sw/` no existe lo crea; si `sw/src/` ya tiene codigo (el de este ejemplo) lo usa tal cual, y si
no, escribe un `main.c` minimo (hola mundo). Genera el BSP en `sw/bsp/` (con `system.h`) y compila:
resultado `sw/build/app/build/app.elf` y `onchip_memory2_0.hex`. Opciones: `[directorio]`, `-n nombre`
del ELF, `-s fuentes`, `-f` (regenerar el BSP).

El script solo encadena `niosv-bsp`, `niosv-app`, `cmake` y `make` (y crea `main.c` si falta). Sin el, a mano
(con `sw/src/` que ya tenga codigo):

```bash
source $S/general/env.sh
cd sw
niosv-bsp --create --type=hal --sopcinfo=../hello.sopcinfo bsp/settings.bsp \
  --cmd="set_setting hal.enable_reduced_device_drivers true" \
  --cmd="set_setting hal.enable_lightweight_device_driver_api true" \
  --cmd="set_setting hal.enable_exit false" \
  --cmd="set_setting hal.enable_clean_exit false" \
  --cmd="set_setting hal.make.cflags_optimization -Os"
niosv-app --app-dir=build/app --bsp-dir=bsp --srcs=src --elf-name=app.elf
cmake -G "Unix Makefiles" -S build/app -B build/app/build
make -C build/app/build
cd ..
```

(Ignore el aviso `Failed to find stack top symbol __alt_heap_limit`: es del reporte de pila y no
afecta al programa.)

### 3. Programar la FPGA

```bash
$S/general/program.sh output/hello.sof
```

### 4. Descargar el ELF y ejecutarlo

```bash
$S/nios/download.sh sw/build/app/build/app.elf
```

Resetea el CPU (`swreset 2 1`), carga el ELF por JTAG y lo arranca (`swreset 2 0`). Opciones:
`--no-run` (solo carga) y `--no-reset`.

### 5. Consola JTAG UART

```bash
$S/general/terminal.sh        # Ctrl+C para salir
```

Debe aparecer `Hola desde el Nios V` y los LEDR[7:0] cuentan en binario.

### Alternativa: firmware dentro del bitstream (`bake`)

Despues de los pasos 1 y 2 (sin programar todavia):

```bash
$S/nios/bake.sh output/hello.qpf sw/build/app/build/onchip_memory2_0.hex
$S/general/program.sh output/hello_fw.sof
$S/general/terminal.sh
```

`bake.sh` reemplaza el contenido de `ram.hex` en el `.sof` (`quartus_cdb --update_mif` y
`quartus_asm`) sin re-sintetizar, y deja `output/hello_fw.sof` con firmware conservando
`output/hello.sof` sin el. Programar la FPGA reinicia el CPU, que arranca solo.

### Cuando cambia algo

| Cambio | Repetir desde |
|---|---|
| `sw/src/*.c` | paso 2 y paso 4 (no hace falta reprogramar la FPGA) |
| `hello.qsys` | paso 1 y paso 2 (el BSP se regenera solo al cambiar el `.sopcinfo`) |
| `pines.qsf` o `timing.sdc` | paso 1 |
