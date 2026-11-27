#include "keys.h"
#include "gic.h"
#include "hw.h"

#define KEYS_DATA       (KEYS_BASE + 0x0u)
#define KEYS_IRQMASK    (KEYS_BASE + 0x8u)
#define KEYS_EDGECAP    (KEYS_BASE + 0xCu)   /* se limpia escribiendo 1 en cada bit */

static volatile uint32_t pendientes;

static void keys_irq(void)
{
    uint32_t flancos = REG32(KEYS_EDGECAP) & 0xFu;
    REG32(KEYS_EDGECAP) = flancos;
    pendientes |= flancos;
}

void keys_iniciar(void)
{
    REG32(KEYS_EDGECAP) = 0xFu;
    REG32(KEYS_IRQMASK) = 0xFu;
    gic_registrar(IRQ_KEYS, keys_irq);
}

uint32_t keys_eventos(void)
{
    irq_deshabilitar();
    uint32_t e = pendientes;
    pendientes = 0;
    irq_habilitar();
    return e;
}
