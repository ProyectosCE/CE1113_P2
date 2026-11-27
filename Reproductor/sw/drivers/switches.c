#include "switches.h"
#include "hw.h"

uint32_t switches_leer(void)
{
    return REG32(SWITCHES_BASE) & 0x3FFu;
}
