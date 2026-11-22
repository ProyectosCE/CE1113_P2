#!/usr/bin/env bash
# Compila el software de un Nios V a partir del .sopcinfo; crea lo que falte.
# Uso: build-sw.sh sistema.sopcinfo [directorio-proyecto] [opciones]
#   directorio-proyecto   def. "sw" junto al .sopcinfo
#   -n nombre             nombre del ELF sin extension (def. app)
#   -s dir_fuentes        fuentes, relativo al proyecto (def. src)
#   -f                    fuerza regenerar el BSP (por defecto solo si cambio el .sopcinfo)
#   --bsp-only            solo genera el BSP
#
# Si el directorio del proyecto o las fuentes no existen, los crea: si ya hay codigo (.c/.cpp/.S)
# en dir_fuentes lo usa tal cual; si no, escribe un src/main.c minimo (hola mundo por la JTAG UART,
# y cuenta en los LEDs si el sistema tiene un PIO llamado "leds").
# Genera: <proyecto>/bsp/ (BSP HAL) y <proyecto>/build/app/build/<nombre>.elf (+ onchip_memory2_0.hex).
#
# Variable BSP_SETTINGS: ajustes del BSP "clave=valor" separados por espacios. Por defecto estan
# pensados para RAM pequena (8 KB): drivers reducidos, sin exit, -Os.
set -e
NAME=app; SRC=src; FORCE=; BSPONLY=; POS=()
while [ $# -gt 0 ]; do case $1 in
  -n) NAME=$2; shift 2;; -s) SRC=$2; shift 2;; -f) FORCE=1; shift;; --bsp-only) BSPONLY=1; shift;;
  -h|--help) sed -n 2,16p "$0"; exit 0;;
  -*) echo "Opcion desconocida: $1" >&2; exit 1;; *) POS+=("$1"); shift;;
esac; done
SOPC=$(readlink -f "${POS[0]:?Uso: $0 sistema.sopcinfo [directorio-proyecto] [opciones]}")
[ -f "$SOPC" ] || { echo "No existe $SOPC (genere el sistema antes: build.sh -q ...)" >&2; exit 1; }
DIR=$(readlink -m "${POS[1]:-$(dirname "$SOPC")/sw}")
: "${BSP_SETTINGS:=hal.enable_reduced_device_drivers=true hal.enable_lightweight_device_driver_api=true hal.enable_exit=false hal.enable_clean_exit=false hal.make.cflags_optimization=-Os}"
source "$(dirname "$(readlink -f "$0")")/../general/env.sh" >/dev/null

mkdir -p "$DIR"; cd "$DIR"

# Fuentes: usar las existentes o crear un hola mundo minimo
if [ -z "$BSPONLY" ] && ! find "$SRC" -type f \( -name '*.c' -o -name '*.cpp' -o -name '*.S' \) 2>/dev/null | grep -q .; then
  mkdir -p "$SRC"
  cat > "$SRC/main.c" <<'C'
/* Programa base Nios V.  Con RAM pequena use alt_putstr() en lugar de printf(). */
#include <stdint.h>
#include "sys/alt_stdio.h"
#include "system.h"   /* generado por el BSP: bases de los perifericos (XXX_BASE) */

int main(void)
{
    alt_putstr("Hola desde el Nios V\n");
#ifdef LEDS_BASE
    volatile uint32_t *leds = (volatile uint32_t *)LEDS_BASE;
    for (uint32_t i = 0;; ++i) {
        *leds = i;
        for (volatile uint32_t d = 0; d < 200000; ++d) {}
    }
#else
    for (;;) {}
#endif
}
C
  echo ">> No habia codigo fuente: creado $DIR/$SRC/main.c (hola mundo)."
fi

# BSP: se regenera si falta o si el .sopcinfo es mas nuevo
if [ -n "$FORCE" ] || [ ! -f bsp/settings.bsp ] || [ "$SOPC" -nt bsp/settings.bsp ]; then
  CMDS=(); for kv in $BSP_SETTINGS; do CMDS+=(--cmd="set_setting ${kv%%=*} ${kv#*=}"); done
  rm -rf bsp
  niosv-bsp --create --type=hal --sopcinfo="$SOPC" bsp/settings.bsp "${CMDS[@]}"
fi
[ -z "$BSPONLY" ] || exit 0

# Aplicacion: niosv-app lista las fuentes al generar, por eso se regenera siempre
rm -rf build/app
niosv-app --app-dir=build/app --bsp-dir=bsp --srcs="$SRC" --elf-name="$NAME.elf" >/dev/null
cmake -G "Unix Makefiles" -S build/app -B build/app/build >/dev/null
make --no-print-directory -C build/app/build
echo "ELF: $DIR/build/app/build/$NAME.elf"
