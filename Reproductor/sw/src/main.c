/* Programa base Nios V.  Con RAM pequena use alt_putstr() en lugar de printf(). */
#include <stdint.h>
#include "sys/alt_stdio.h"
#include "system.h"   /* generado por el BSP: bases de los perifericos (XXX_BASE) */

int main(void)
{
    alt_putstr("Hola desde el Nios V\n");
#ifdef LEDS_BASE
    volatile uint32_t *leds = (volatile uint32_t *)LEDS_BASE;
    for (uint32_t i = 0;; ++i) {
        *leds = i;
        for (volatile uint32_t d = 0; d < 200000; ++d) {}
    }
#else
    for (;;) {}
#endif
}
