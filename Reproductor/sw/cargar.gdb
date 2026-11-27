# Conecta al gdb-server, apaga el watchdog del BootROM, carga el ELF y para en main.
# Uso: make debug   (o gdb-multiarch -x sw/cargar.gdb sw/build/reproductor.elf)
set architecture armv7
set confirm off
set pagination off
target remote :3334
set *(unsigned int *)0xFFD05014 = *(unsigned int *)0xFFD05014 | 0x40
load
break main
continue
