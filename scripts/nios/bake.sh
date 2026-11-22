#!/usr/bin/env bash
# "Hornea" un firmware en el bitstream sin volver a sintetizar (como el Proyecto I):
# reemplaza el contenido inicial de la RAM on-chip (ram.hex) y regenera el .sof.
# El CPU arranca con el programa ya en la RAM; reprogramar la FPGA = reiniciar.
# Uso: bake.sh proyecto.qpf firmware.hex
#   Deja el resultado en <proyecto>_fw.sof y conserva <proyecto>.sof (RAM sin firmware),
#   que sirve para probar la descarga por depurador (download.sh).
#   firmware.hex: el onchip_memory2_0.hex que deja el proyecto de software (make en sw/)
# Requiere que el sistema se haya compilado con la RAM inicializada desde ram.hex
# (parametro de la RAM en el .qsys) y que build.sh haya corrido antes (-m zero).
set -e
QPF=$(readlink -f "${1:?Uso: $0 proyecto.qpf firmware.hex}")
HEX=$(readlink -f "${2:?falta firmware.hex}")
[ -f "$QPF" ] && [ -f "$HEX" ] || { echo "No existe $QPF o $HEX" >&2; exit 1; }
source "$(dirname "$(readlink -f "$0")")/../general/env.sh" >/dev/null
cd "$(dirname "$QPF")"; P=$(basename "$QPF" .qpf)
[ -f "output_files/$P.sof" ] || [ -f "$P.sof" ] || { echo "Falta compilar el proyecto (build.sh) antes de hornear." >&2; exit 1; }
SOF=$(ls $P.sof output_files/$P.sof 2>/dev/null | head -1)
cp "$SOF" "$SOF.base"            # conserva el .sof sin firmware
cp "$HEX" ram.hex
quartus_cdb "$P" --update_mif 2>&1 | grep -E "Error|successful" || true
quartus_asm "$P" 2>&1 | grep -E "Error|successful" || true
mv "$SOF" "${SOF%.sof}_fw.sof"; mv "$SOF.base" "$SOF"
echo "Con firmware: $(readlink -f "${SOF%.sof}_fw.sof")"
echo "Sin firmware: $(readlink -f "$SOF")"
