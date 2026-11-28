# Componente de Platform Designer: vga_texto (hardware propio del reproductor).
# Platform Designer lo encuentra solo porque esta en Reproductor/ip/: aparece en el IP Catalog
# en el grupo "Reproductor".
package require -exact qsys 16.1

set_module_property NAME vga_texto
set_module_property VERSION 1.0
set_module_property GROUP "Reproductor"
set_module_property DISPLAY_NAME "vga_texto (pantalla VGA de texto 80x30)"
set_module_property DESCRIPTION "Controlador VGA 640x480 de texto: 80x30 caracteres de 8x16 con 16 colores"
set_module_property AUTHOR "CE1113 Proyecto II"
set_module_property INSTANTIATE_IN_SYSTEM_MODULE true
set_module_property EDITABLE false
set_module_property REPORT_TO_TALKBACK false
set_module_property ALLOW_GREYBOX_GENERATION false
set_module_property REPORT_HIERARCHY false

# ---- Archivos ----
add_fileset QUARTUS_SYNTH QUARTUS_SYNTH "" ""
set_fileset_property QUARTUS_SYNTH TOP_LEVEL vga_texto
add_fileset_file vga_texto.sv SYSTEM_VERILOG PATH vga_texto.sv TOP_LEVEL_FILE
add_fileset_file vga_fuente.sv SYSTEM_VERILOG PATH vga_fuente.sv

add_fileset SIM_VERILOG SIM_VERILOG "" ""
set_fileset_property SIM_VERILOG TOP_LEVEL vga_texto
add_fileset_file vga_texto.sv SYSTEM_VERILOG PATH vga_texto.sv
add_fileset_file vga_fuente.sv SYSTEM_VERILOG PATH vga_fuente.sv

# ---- Reloj (50 MHz) y reset ----
add_interface clock clock end
set_interface_property clock clockRate 50000000
add_interface_port clock clk clk Input 1

add_interface reset reset end
set_interface_property reset associatedClock clock
set_interface_property reset synchronousEdges DEASSERT
add_interface_port reset reset reset Input 1

# ---- Esclavo Avalon-MM (4096 palabras = 16 KB; lectura con latencia fija de 1 ciclo) ----
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

add_interface_port s0 avs_address address Input 12
add_interface_port s0 avs_read read Input 1
add_interface_port s0 avs_readdata readdata Output 32
add_interface_port s0 avs_write write Input 1
add_interface_port s0 avs_writedata writedata Input 32

# ---- Salida al conector VGA (se exporta como "vga": puertos vga_r, vga_g, ... vga_sync_n) ----
add_interface vga conduit end
set_interface_property vga associatedClock clock
set_interface_property vga associatedReset reset
add_interface_port vga vga_r       r       Output 8
add_interface_port vga vga_g       g       Output 8
add_interface_port vga vga_b       b       Output 8
add_interface_port vga vga_hs      hs      Output 1
add_interface_port vga vga_vs      vs      Output 1
add_interface_port vga vga_clk     clk     Output 1
add_interface_port vga vga_blank_n blank_n Output 1
add_interface_port vga vga_sync_n  sync_n  Output 1
