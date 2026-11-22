#!/usr/bin/env bash
# Entorno de Quartus / Nios V / Questa.   Uso:  source ~/quartus-tools/env.sh
: "${ALTERA_ROOT:=$HOME/altera_lite/25.1std}"
if [ ! -d "$ALTERA_ROOT/quartus" ]; then
    echo "ERROR: no encuentro Quartus en '$ALTERA_ROOT/quartus' (exporte ALTERA_ROOT)." >&2
    return 1 2>/dev/null || exit 1
fi
export ALTERA_ROOT
export QUARTUS_ROOTDIR="$ALTERA_ROOT/quartus"
export PATH="$QUARTUS_ROOTDIR/bin:$QUARTUS_ROOTDIR/linux64:$QUARTUS_ROOTDIR/sopc_builder/bin:$ALTERA_ROOT/niosv/bin:$ALTERA_ROOT/riscfree/toolchain/riscv32-unknown-elf/bin:$ALTERA_ROOT/riscfree/debugger/gdbserver-riscv:$ALTERA_ROOT/questa_fse/bin:$PATH"
# Questa Altera Starter usa SALT, no LM_LICENSE_FILE.
: "${SALT_LICENSE_SERVER:=$HOME/.altera.quartus/questa_lic.dat}"
export SALT_LICENSE_SERVER

# El reloj JTAG por defecto (24 MHz, el maximo del USB-Blaster II) corrompe
# scans de forma intermitente en cables/conexiones no ideales, lo que
# desincroniza la UART virtual (JTAG UART) a mitad de una transmision y la
# deja trabada para siempre (no hay retransmision en ese protocolo).
# jtagd no recuerda este ajuste entre reinicios, asi que se fija aqui en
# cada sesion. Si no hay cable conectado/jtagd no corre, esto no debe
# interrumpir el resto del entorno.
if command -v jtagconfig >/dev/null 2>&1; then
    while IFS= read -r cable; do
        jtagconfig --setparam "$cable" JtagClock 6M >/dev/null 2>&1
    done < <(jtagconfig 2>/dev/null | sed -n 's/^[0-9]\+) //p')
fi

echo "Entorno Quartus listo: ALTERA_ROOT=$ALTERA_ROOT"

# Scripts de este repo (general/ y nios/) en el PATH, para llamarlos sin ruta completa
_QT_SCRIPTS="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
for _d in "$_QT_SCRIPTS/general" "$_QT_SCRIPTS/nios"; do
    case ":$PATH:" in *":$_d:"*) ;; *) PATH="$_d:$PATH" ;; esac
done
export PATH
unset _QT_SCRIPTS _d
