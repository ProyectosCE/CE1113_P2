/*
 * Incremento 0 - prueba del flujo compilar -> cargar por JTAG -> ejecutar en el ARM.
 *
 * Resultado (leerlo desde gdb tras detener el CPU con Ctrl+C):
 *   firma    == 0xC0FFEE00  -> el CPU lee y escribe bien los 40 KB de "relleno"
 *   firma    == 0xDEAD....  -> fallo; los 16 bits bajos cuentan las palabras erroneas
 *   contador -> debe aumentar entre dos lecturas (el programa sigue corriendo)
 */
#include <stdint.h>

#define PALABRAS (40u * 1024u / 4u)   /* 40 KB: obliga a usar mas de los primeros 8 KB */

static uint32_t relleno[PALABRAS];     /* en .bss, despues del codigo */
volatile uint32_t firma;
volatile uint32_t contador;

int main(void)
{
    uint32_t errores = 0;

    for (uint32_t i = 0; i < PALABRAS; ++i)
        relleno[i] = i ^ 0xA5A5A5A5u;
    for (uint32_t i = 0; i < PALABRAS; ++i)
        if (relleno[i] != (i ^ 0xA5A5A5A5u))
            ++errores;

    firma = errores ? (0xDEAD0000u | (errores & 0xFFFFu)) : 0xC0FFEE00u;

    for (;;)
        ++contador;
}
