#!/usr/bin/env bash
# Programa la DE1-SoC (FPGA) con un .sof por JTAG (USB-Blaster).
# Uso: program.sh archivo.sof [indice-dispositivo]   (por defecto 2: la FPGA, el 1 es el HPS/ARM)
set -e
SOF="${1:?Uso: $0 archivo.sof [indice-dispositivo]}"
DEV="${2:-2}"
[ -f "$SOF" ] || { echo "No existe $SOF" >&2; exit 1; }
source "$(dirname "$(readlink -f "$0")")/env.sh" >/dev/null
jtagconfig || true
CABLE="$(jtagconfig 2>/dev/null | sed -n 's/^1) //p' | head -1)"
[ -n "$CABLE" ] || { echo "No se detecta el USB-Blaster (cable, reglas udev, jtagd)." >&2; exit 1; }
echo "Cable: $CABLE"
quartus_pgm -m jtag -c "$CABLE" -o "p;$(readlink -f "$SOF")@$DEV"
