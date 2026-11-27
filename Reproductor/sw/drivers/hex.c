#include "hex.h"
#include "hw.h"

#define HEX_CTRL        (HEX_BASE + 0x0u)
#define HEX_TIEMPO      (HEX_BASE + 0x4u)
#define HEX_CANCION     (HEX_BASE + 0x8u)
#define HEX_STATUS      (HEX_BASE + 0xCu)

void hex_encender(bool tiempo, bool cancion)
{
    REG32(HEX_CTRL) = (tiempo ? 1u : 0u) | (cancion ? 2u : 0u);
}

void hex_tiempo(uint32_t segundos)
{
    uint32_t m = (segundos / 60u) % 100u, s = segundos % 60u;
    REG32(HEX_TIEMPO) = (m << 8) | s;
}

void hex_cancion(uint32_t numero)
{
    REG32(HEX_CANCION) = numero;
}

uint32_t hex_id(void)
{
    return REG32(HEX_STATUS) >> 16;
}
