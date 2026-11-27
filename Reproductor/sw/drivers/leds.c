#include "leds.h"
#include "hw.h"

void leds_escribir(uint32_t valor)
{
    REG32(LEDS_BASE) = valor & 0x3FFu;
}
