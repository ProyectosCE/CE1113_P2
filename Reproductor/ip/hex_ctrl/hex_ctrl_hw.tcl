# Componente de Platform Designer: hex_ctrl (hardware propio del reproductor).
# Platform Designer lo encuentra solo porque esta en Reproductor/ip/: aparece en el IP Catalog
# en el grupo "Reproductor".
package require -exact qsys 16.1

set_module_property NAME hex_ctrl
set_module_property VERSION 1.0
set_module_property GROUP "Reproductor"
set_module_property DISPLAY_NAME "hex_ctrl (7 segmentos MM:SS)"
set_module_property DESCRIPTION "Displays de 7 segmentos: tiempo MM:SS en HEX3-0 y numero de cancion en HEX5-4"
set_module_property AUTHOR "CE1113 Proyecto II"
set_module_property INSTANTIATE_IN_SYSTEM_MODULE true
set_module_property EDITABLE false
set_module_property REPORT_TO_TALKBACK false
set_module_property ALLOW_GREYBOX_GENERATION false
set_module_property REPORT_HIERARCHY false

# ---- Archivos ----
add_fileset QUARTUS_SYNTH QUARTUS_SYNTH "" ""
set_fileset_property QUARTUS_SYNTH TOP_LEVEL hex_ctrl
add_fileset_file hex_ctrl.sv SYSTEM_VERILOG PATH hex_ctrl.sv TOP_LEVEL_FILE

add_fileset SIM_VERILOG SIM_VERILOG "" ""
set_fileset_property SIM_VERILOG TOP_LEVEL hex_ctrl
add_fileset_file hex_ctrl.sv SYSTEM_VERILOG PATH hex_ctrl.sv

# ---- Reloj y reset ----
add_interface clock clock end
set_interface_property clock clockRate 0
add_interface_port clock clk clk Input 1

add_interface reset reset end
set_interface_property reset associatedClock clock
set_interface_property reset synchronousEdges DEASSERT
add_interface_port reset reset reset Input 1

# ---- Esclavo Avalon-MM (lectura con latencia fija de 1 ciclo) ----
add_interface s0 avalon end
set_interface_property s0 addressUnits WORDS
set_interface_property s0 associatedClock clock
set_interface_property s0 associatedReset reset
set_interface_property s0 bitsPerSymbol 8
set_interface_property s0 burstOnBurstBoundariesOnly false
set_interface_property s0 explicitAddressSpan 0
set_interface_property s0 holdTime 0
set_interface_property s0 linewrapBursts false
set_interface_property s0 maximumPendingReadTransactions 0
set_interface_property s0 readLatency 1
set_interface_property s0 readWaitTime 0
set_interface_property s0 setupTime 0
set_interface_property s0 timingUnits Cycles
set_interface_property s0 writeWaitTime 0

add_interface_port s0 avs_address address Input 2
add_interface_port s0 avs_read read Input 1
add_interface_port s0 avs_readdata readdata Output 32
add_interface_port s0 avs_write write Input 1
add_interface_port s0 avs_writedata writedata Input 32

# ---- Salida a los displays (se exporta como "hex": puertos hex_hex0 ... hex_hex5) ----
add_interface hex conduit end
set_interface_property hex associatedClock clock
set_interface_property hex associatedReset reset
add_interface_port hex hex0 hex0 Output 7
add_interface_port hex hex1 hex1 Output 7
add_interface_port hex hex2 hex2 Output 7
add_interface_port hex hex3 hex3 Output 7
add_interface_port hex hex4 hex4 Output 7
add_interface_port hex hex5 hex5 Output 7
