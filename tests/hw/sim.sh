#!/usr/bin/env bash
# Simula un modulo de hardware propio con su testbench en Questa (sin GUI).
# Uso: tests/hw/sim.sh hex_ctrl | dsp_filter | todos
#   -gui   abre Questa con las formas de onda en vez de correr en consola
set -e
DIR=$(cd "$(dirname "$0")" && pwd)
IP="$DIR/../../Reproductor/ip"
source "$DIR/../../scripts/general/env.sh" >/dev/null

GUI=; MODS=()
for a in "$@"; do case $a in -gui) GUI=1;; todos) MODS+=(hex_ctrl dsp_filter);; *) MODS+=("$a");; esac; done
[ ${#MODS[@]} -gt 0 ] || { echo "Uso: $0 hex_ctrl | dsp_filter | todos [-gui]" >&2; exit 1; }

WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
cd "$WORK"
vlib work >/dev/null

FALLAS=0
for m in "${MODS[@]}"; do
  [ -f "$IP/$m/$m.sv" ] || { echo "No existe $IP/$m/$m.sv" >&2; exit 1; }
  echo ">> $m"
  vlog -sv -quiet "$IP/$m/$m.sv" "$DIR/tb_$m.sv"
  if [ -n "$GUI" ]; then
    vsim "tb_$m" -do "add wave -r /*; run -all"
  else
    vsim -c -quiet "tb_$m" -do "run -all; quit -f" | tee "sim_$m.log" | grep -E "RESULTADO|FALLA|Error" || true
    grep -q "RESULTADO $m: OK" "sim_$m.log" || FALLAS=$((FALLAS + 1))
  fi
done
exit $FALLAS
