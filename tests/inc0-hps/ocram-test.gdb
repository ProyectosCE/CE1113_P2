# Incremento 0 - prueba de acceso del depurador a la OCRAM (sin programa cargado).
# Escribe y relee una palabra al inicio de cada bloque de 4 KB (16 bloques = 64 KB).
# Uso (con el gdb-server corriendo):
#   gdb-multiarch -batch -x ocram-test.gdb
set architecture armv7
set confirm off
target remote :3334

printf "PC = 0x%08x  CPSR = 0x%08x\n", $pc, $cpsr

set $i = 0
set $fallas = 0
while $i < 16
  set $dir = 0xFFFF0000 + $i * 0x1000
  set $patron = 0x5A000000 + $i
  set *(unsigned int *)$dir = $patron
  set $leido = *(unsigned int *)$dir
  if $leido != $patron
    printf "  FALLA bloque %2d (0x%08x): leido 0x%08x\n", $i, $dir, $leido
    set $fallas = $fallas + 1
  else
    printf "  ok    bloque %2d (0x%08x)\n", $i, $dir
  end
  set $i = $i + 1
end
printf "Bloques de 4 KB con falla: %d de 16\n", $fallas
detach
