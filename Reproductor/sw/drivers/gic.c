#include "gic.h"
#include "hw.h"

#define GICD_CTLR               (HPS_GICD_BASE + 0x000u)
#define GICD_ISENABLER(n)       (HPS_GICD_BASE + 0x100u + 4u * (n))
#define GICD_ICENABLER(n)       (HPS_GICD_BASE + 0x180u + 4u * (n))
#define GICD_ICPENDR(n)         (HPS_GICD_BASE + 0x280u + 4u * (n))
#define GICD_ISACTIVER(n)       (HPS_GICD_BASE + 0x300u + 4u * (n))
#define GICD_IPRIORITYR(id)     (HPS_GICD_BASE + 0x400u + (id))
#define GICD_ITARGETSR(id)      (HPS_GICD_BASE + 0x800u + (id))
#define GICC_CTLR               (HPS_GICC_BASE + 0x00u)
#define GICC_PMR                (HPS_GICC_BASE + 0x04u)
#define GICC_IAR                (HPS_GICC_BASE + 0x0Cu)
#define GICC_EOIR               (HPS_GICC_BASE + 0x10u)

#define REG8(dir)               (*(volatile uint8_t *)(uintptr_t)(dir))
#define GIC_MAX_ID              128u

static gic_manejador_t manejadores[GIC_MAX_ID];

void gic_iniciar(void)
{
    REG32(GICC_CTLR) = 0;
    REG32(GICD_CTLR) = 0;
    for (uint32_t n = 0; n < GIC_MAX_ID / 32u; ++n) {
        REG32(GICD_ICENABLER(n)) = 0xFFFFFFFFu;
        REG32(GICD_ICPENDR(n)) = 0xFFFFFFFFu;
    }

    /*
     * El GIC no se reinicia al volver a cargar el programa por JTAG. Si la carga anterior se
     * detuvo dentro de una interrupcion (antes de escribir EOIR), esa interrupcion queda
     * "activa" y bloquea para siempre a todas las de su prioridad: no llegan ni el audio ni
     * los botones. En el GIC del Cortex-A9 el bit de activa es de solo lectura, asi que se
     * cierran escribiendo su ID en EOIR.
     */
    for (uint32_t n = 0; n < GIC_MAX_ID / 32u; ++n) {
        uint32_t activas = REG32(GICD_ISACTIVER(n));
        for (uint32_t b = 0; b < 32u; ++b)
            if (activas & (1u << b))
                REG32(GICC_EOIR) = 32u * n + b;
    }

    REG32(GICD_CTLR) = 1;

    REG32(GICC_PMR) = 0xFFu;   /* aceptar todas las prioridades */
    REG32(GICC_CTLR) = 1;
}

int gic_registrar(uint32_t id, gic_manejador_t manejador)
{
    if (id >= GIC_MAX_ID || manejador == 0)
        return -1;
    manejadores[id] = manejador;
    REG8(GICD_IPRIORITYR(id)) = 0xA0;
    REG8(GICD_ITARGETSR(id)) = 0x01;                     /* CPU0 */
    REG32(GICD_ISENABLER(id / 32u)) = 1u << (id % 32u);
    return 0;
}

void irq_despachar(void)
{
    uint32_t iar = REG32(GICC_IAR);
    uint32_t id = iar & 0x3FFu;

    if (id < GIC_MAX_ID && manejadores[id])
        manejadores[id]();

    REG32(GICC_EOIR) = iar;
}
