#!/usr/bin/env bash
# Sintesis + fitter + assembler (bitstream .sof) desde linea de comandos.
#
# Modo A (proyecto existente):  build.sh proyecto.qpf [-r revision]
# Modo B (fuentes + pines):     build.sh -t TOP -p pines.qsf [-d DISPOSITIVO] [-o dir] fuentes...
#   fuentes: .v .sv .vhd .qip .sdc  (se agregan segun extension)
#   pines:   archivo .qsf/.tcl con set_location_assignment / set_instance_assignment
#
# Extras:   -q sistema.qsys  genera el sistema Platform Designer (qsys-generate) y agrega su .qip
#           -C                solo crea el proyecto (.qpf/.qsf); no compila
#           -m hex|zero       copia "hex" como <salida>/ram.hex (init de la RAM on-chip) o, con
#                             "zero", crea uno en ceros (ZERO_WORDS palabras, def. 2032 = 8128 B)
# Opciones: -t top-level (opcional con -q: por defecto el sistema del .qsys)  -p pines  -d dispositivo (def. 5CSEMA5F31C6, DE1-SoC)
#           -o directorio de salida (def. ./output)  -n nombre proyecto (def. TOP)
set -e
source "$(dirname "$(readlink -f "$0")")/env.sh" >/dev/null

DEVICE=5CSEMA5F31C6; OUT=output; TOP=; PINS=; NAME=; REV=; QSYS=; ONLY=; MEM=
while getopts "t:p:d:o:n:r:q:m:Ch" o; do
  case $o in t) TOP=$OPTARG;; p) PINS=$OPTARG;; d) DEVICE=$OPTARG;; o) OUT=$OPTARG;;
             n) NAME=$OPTARG;; q) QSYS=$OPTARG;; m) MEM=$OPTARG;; C) ONLY=1;; r) REV=$OPTARG;; *) sed -n '2,12p' "$0"; exit 1;; esac
done
shift $((OPTIND-1))
# Con un .qsys, el top-level por defecto es el sistema generado (nombre del .qsys sin extension)
[ -n "$TOP" ] || [ -z "$QSYS" ] || TOP=$(basename "$QSYS" .qsys)

if [[ "${1:-}" == *.qpf ]]; then
  QPF=$(readlink -f "$1"); cd "$(dirname "$QPF")"
  NAME=$(basename "$QPF" .qpf); REV=${REV:-$NAME}
else
  [ -n "$TOP" ] && { [ $# -gt 0 ] || [ -n "$QSYS" ]; } || { sed -n '2,12p' "$0"; exit 1; }
  NAME=${NAME:-$TOP}; REV=$NAME
  # Sin HDL propio, el top-level tiene que ser el sistema que genera el .qsys: avisar antes de
  # sintetizar (si no, Quartus falla con "Top-level design entity ... is undefined")
  if [ -n "$QSYS" ] && [ "$TOP" != "$(basename "$QSYS" .qsys)" ]; then
    HDL=; for f in "$@"; do case "$f" in *.v|*.sv|*.vhd|*.vhdl) HDL=1;; esac; done
    if [ -z "$HDL" ]; then
      QN=$(basename "$QSYS" .qsys)
      echo "ERROR: el top-level '$TOP' no existe: el sistema generado por $(basename "$QSYS") se llama '$QN'." >&2
      echo "       Use -t $QN (o omita -t) y, si quiere otro nombre para el proyecto, -n $TOP;" >&2
      echo "       o agregue el .v/.sv que define el top '$TOP'." >&2
      exit 1
    fi
  fi
  FILES=()
  if [ -n "$QSYS" ]; then
    QSYS=$(readlink -f "$QSYS"); QDIR=$(dirname "$QSYS"); QN=$(basename "$QSYS" .qsys)
    (cd "$QDIR" && qsys-generate "$QSYS" --synthesis=VERILOG --family="Cyclone V" --part="$DEVICE" \
        --output-directory="$QDIR/$QN") >&2
    FILES+=("$QDIR/$QN/synthesis/$QN.qip")
  fi
  for f in "$@"; do [ -f "$f" ] || { echo "No existe $f" >&2; exit 1; }; FILES+=("$(readlink -f "$f")"); done
  [ -z "$PINS" ] || PINS=$(readlink -f "$PINS")
  [ -z "$MEM" ] || [ "$MEM" = zero ] || MEM=$(readlink -f "$MEM")
  mkdir -p "$OUT"; cd "$OUT"
  if [ "$MEM" = zero ]; then
    awk -v n="${ZERO_WORDS:-2032}" 'BEGIN{for(a=0;a<n;a++){cs=(256-((4+int(a/256)+a%256)%256))%256; printf(":04%04X0000000000%02X\n",a,cs)} print ":00000001FF"}' > ram.hex
  elif [ -n "$MEM" ]; then cp "$MEM" ram.hex; fi
  {
    echo "project_new $NAME -overwrite"
    echo "set_global_assignment -name FAMILY \"Cyclone V\""
    echo "set_global_assignment -name DEVICE $DEVICE"
    echo "set_global_assignment -name TOP_LEVEL_ENTITY $TOP"
    for f in "${FILES[@]}"; do
      case "$f" in
        *.sv) t=SYSTEMVERILOG_FILE;; *.v) t=VERILOG_FILE;; *.vhd|*.vhdl) t=VHDL_FILE;;
        *.qip) t=QIP_FILE;; *.sdc) t=SDC_FILE;; *) echo "Extension no soportada: $f" >&2; exit 1;;
      esac
      echo "set_global_assignment -name $t \"$f\""
    done
    [ -z "$PINS" ] || echo "source \"$PINS\""
    echo "project_close"
  } > create_project.tcl
  quartus_sh -t create_project.tcl
fi

if [ -n "$ONLY" ]; then echo "Proyecto: $(pwd)/$NAME.qpf"; exit 0; fi
quartus_sh --flow compile "$NAME" ${REV:+-c "$REV"} 2>&1 | tee build.log | grep -E "^(Info: Quartus Prime .* was (successful|unsuccessful)|Error|Critical Warning)" || true
SOF=$(ls output_files/*.sof 2>/dev/null | head -1 || true)
[ -n "$SOF" ] || SOF=$(ls *.sof 2>/dev/null | head -1 || true)
[ -n "$SOF" ] || { echo "FALLO: no se genero .sof (ver $(pwd)/build.log)" >&2; exit 1; }
echo "Bitstream: $(readlink -f "$SOF")"
