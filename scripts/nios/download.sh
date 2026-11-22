#!/usr/bin/env bash
# Descarga un ELF a un Nios V por JTAG (USB-Blaster) y lo ejecuta.
# Uso: download.sh programa.elf [--no-run] [--no-reset]
#   --no-run    solo carga, deja el CPU detenido
#   --no-reset  no resetea el CPU antes de cargar
#
# Por que no usa "niosv-download -r": en Quartus 25.1 esa opcion envia
# "monitor swreset 1 1" al servidor Ashling, que responde "Invalid reset option"
# (solo acepta los modos 2 y 3). Aqui se hace la misma secuencia con "swreset 2 1"
# (reset del sistema y CPU detenido en el vector de reset).
#
# Variables: DEVICE (posicion del FPGA en la cadena JTAG, def. 2), GDB_PORT (def. 3333)
set -e
ELF=; RUN=1; RST=1
for a in "$@"; do case $a in
  --no-run) RUN=;; --no-reset) RST=;; -*) echo "Opcion desconocida: $a" >&2; exit 1;; *) ELF=$a;;
esac; done
[ -f "$ELF" ] || { echo "Uso: $0 programa.elf [--no-run] [--no-reset]" >&2; exit 1; }
ELF=$(readlink -f "$ELF")
source "$(dirname "$(readlink -f "$0")")/../general/env.sh" >/dev/null
DEVICE=${DEVICE:-2}; PORT=${GDB_PORT:-3333}

# IDCODE del dispositivo DEVICE de la cadena del cable 1 (lineas con 8 hex de jtagconfig)
IDCODE=$(jtagconfig 2>/dev/null | awk '/^1\)/{c=1;next} /^[0-9]+\)/{c=0} c&&/^ +[0-9A-F]{8} /{n++; if(n=='"$DEVICE"'){print $1; exit}}')
[ -n "$IDCODE" ] || { echo "No encuentro el dispositivo $DEVICE en el cable 1 (jtagconfig)." >&2; exit 1; }

LOG=$(mktemp); cleanup() { kill "$SRV" 2>/dev/null || true; rm -f "$LOG"; }; trap cleanup EXIT
ash-riscv-gdb-server --auto-detect true --probe-type usb-blaster-2 --instance 1 \
    --device "$IDCODE" --core-number 0 --gdb-port "$PORT" >"$LOG" 2>&1 &
SRV=$!; disown "$SRV"   # sin aviso "Killed" al terminar
for _ in $(seq 40); do grep -q "Waiting for debugger connection" "$LOG" && break; sleep 0.5; done
grep -q "Waiting for debugger connection" "$LOG" || { echo "El gdb-server no arranco:" >&2; cat "$LOG" >&2; exit 1; }

ARGS=(-batch -ex "set non-stop on" -ex "set arch riscv:rv32" -ex "set remotetimeout 60"
      -ex "target extended-remote localhost:$PORT")
[ -z "$RST" ] || ARGS+=(-ex "monitor swreset 2 1")
ARGS+=(-ex "load $ELF")
# Arrancar: "continue&" en gdb -batch no es fiable (gdb sale antes de reanudar y el CPU
# queda detenido).  Un reset con ejecucion arranca desde el vector de reset, donde esta el ELF.
[ -z "$RUN" ] || ARGS+=(-ex "monitor swreset 2 0")
riscv32-unknown-elf-gdb "${ARGS[@]}" 2>&1 | grep -E "Loading section|Start address|rror|Invalid|Software reset" || true
echo "ELF descargado${RUN:+ y en ejecucion}."
