#!/usr/bin/env bash
# Conecta a la JTAG UART (Altera JTAG UART IP). Salir: Ctrl+C.
# Uso: [DEVICE=2] terminal.sh [instancia]   (DE1-SoC: FPGA = dispositivo 2)
source "$(dirname "$(readlink -f "$0")")/env.sh" >/dev/null
INST="${1:-0}"
CABLE="$(jtagconfig 2>/dev/null | sed -n 's/^1) //p' | head -1)"
[ -n "$CABLE" ] || { echo "No se detecta el USB-Blaster." >&2; exit 1; }
exec juart-terminal --cable "$CABLE" --device "${DEVICE:-2}" --instance "$INST"
