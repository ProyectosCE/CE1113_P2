#!/usr/bin/env bash
# Arranca el gdb-server de Ashling (incluido en Quartus/RiscFree) para un core del
# Cortex-A9 del HPS de la DE1-SoC. Se queda corriendo: use otra terminal para gdb.
#
# Uso: gdb-server.sh [core]        core 0 (def.) o 1
# Variables: GDB_PORT (def. 3334; el 3333 lo usa download.sh del Nios V)
set -e
source "$(dirname "$(readlink -f "$0")")/../general/env.sh" >/dev/null

SRV="$ALTERA_ROOT/riscfree/debugger/gdbserver-arm/ash-arm-gdb-server"
[ -x "$SRV" ] || { echo "No encuentro $SRV (instale RiscFree con Quartus)." >&2; exit 1; }

CORE=${1:-0}
PORT=${GDB_PORT:-3334}

# IDCODE del HPS en la cadena JTAG (en la DE1-SoC: 4BA00477, "SOCVHPS")
IDCODE=$(jtagconfig 2>/dev/null | awk '/SOCVHPS/{print $1; exit}')
[ -n "$IDCODE" ] || { echo "jtagconfig no muestra el HPS (SOCVHPS). Revise cable y alimentacion." >&2; exit 1; }

echo "HPS IDCODE $IDCODE, core $CORE, puerto gdb $PORT  (Ctrl+C para cerrar)"
exec "$SRV" --device "$IDCODE" --auto-detect true --probe-type usb-blaster-2 \
    --core-number "$CORE" --gdb-port "$PORT" ${JTAG_FREQ:+--jtag-frequency "$JTAG_FREQ"}
