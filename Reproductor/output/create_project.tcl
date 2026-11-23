project_new hello -overwrite
set_global_assignment -name FAMILY "Cyclone V"
set_global_assignment -name DEVICE 5CSEMA5F31C6
set_global_assignment -name TOP_LEVEL_ENTITY hello
set_global_assignment -name QIP_FILE "/home/jecampos/CE1113_P2/Reproductor/hello/synthesis/hello.qip"
set_global_assignment -name SDC_FILE "/home/jecampos/CE1113_P2/Reproductor/timing.sdc"
source "/home/jecampos/CE1113_P2/Reproductor/pines.qsf"
project_close
