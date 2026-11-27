# Incremento 0 - conecta, apaga el watchdog del BootROM, carga inc0.elf y para en main.
# Uso (con el gdb-server corriendo):  gdb-multiarch -x cargar.gdb inc0.elf
set architecture armv7
set confirm off
set pagination off
target remote :3334

# Retener en reset el watchdog L4WD0 (RSTMGR.permodrst, bit 6) antes de que reinicie el HPS
set *(unsigned int *)0xFFD05014 = *(unsigned int *)0xFFD05014 | 0x40

load
break main
continue
