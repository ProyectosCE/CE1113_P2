/*
 * Prueba de botones, switches y ADC.
 *
 * - KEY[3:0]: interrupcion por flanco (PIO -> f2h_irq0[1] -> GIC ID 73). Cada pulsacion se
 *   imprime por la JTAG UART con el numero de boton y el total de interrupciones.
 * - SW[9:0]: se leen por sondeo y se copian a LEDR[9:0].
 * - ADC canal 0 (potenciometro): se imprime cuando cambia mas de 32 cuentas.
 *
 * Acceso directo a registros (sin HAL).
 */
#include <stdint.h>

#define REG(dir)            (*(volatile uint32_t *)(dir))
#define REG8(dir)           (*(volatile uint8_t *)(dir))

/* HPS */
#define RSTMGR_BRGMODRST    0xFFD0501Cu
#define L3_REMAP            0xFF800000u

/* GIC del Cortex-A9 MPCore */
#define GICD                0xFFFED000u     /* distribuidor */
#define GICD_CTLR           (GICD + 0x000u)
#define GICD_ISENABLER(n)   (GICD + 0x100u + 4u * (n))
#define GICD_IPRIORITYR(id) (GICD + 0x400u + (id))
#define GICD_ITARGETSR(id)  (GICD + 0x800u + (id))
#define GICC                0xFFFEC100u     /* interfaz de CPU */
#define GICC_CTLR           (GICC + 0x00u)
#define GICC_PMR            (GICC + 0x04u)
#define GICC_IAR            (GICC + 0x0Cu)
#define GICC_EOIR           (GICC + 0x10u)

#define IRQ_FPGA_BASE       72u             /* f2h_irq0[0] */
#define IRQ_KEYS            (IRQ_FPGA_BASE + 1u)

/* Perifericos en el puente lightweight */
#define LW_BASE             0xFF200000u
#define LEDS                (LW_BASE + 0x0000u)
#define SWITCHES            (LW_BASE + 0x0040u)
#define KEYS_DATA           (LW_BASE + 0x0050u)
#define KEYS_IRQMASK        (LW_BASE + 0x0058u)
#define KEYS_EDGECAP        (LW_BASE + 0x005Cu)
#define JTAG_UART_DATA      (LW_BASE + 0x1000u)
#define JTAG_UART_CTRL      (LW_BASE + 0x1004u)
#define ADC_CH0             (LW_BASE + 0x4000u)  /* lectura: canal 0; escritura: convertir */
#define ADC_AUTO            (LW_BASE + 0x4004u)  /* escritura 1: auto-update */

static volatile uint32_t teclas_pendientes;
static volatile uint32_t total_irq;

/* ---- JTAG UART (sin bloquear) ---- */
static void uart_putc(char c)
{
    if (REG(JTAG_UART_CTRL) >> 16)
        REG(JTAG_UART_DATA) = (uint32_t)c;
}

static void uart_puts(const char *s)
{
    while (*s)
        uart_putc(*s++);
}

static void uart_putu(uint32_t v)
{
    char buf[11];
    int i = 0;
    do {
        buf[i++] = (char)('0' + v % 10u);
        v /= 10u;
    } while (v);
    while (i)
        uart_putc(buf[--i]);
}

static void uart_puthex3(uint32_t v)
{
    static const char hex[] = "0123456789ABCDEF";
    uart_puts("0x");
    uart_putc(hex[(v >> 8) & 0xF]);
    uart_putc(hex[(v >> 4) & 0xF]);
    uart_putc(hex[v & 0xF]);
}

/* ---- GIC ---- */
static void gic_init(void)
{
    REG(GICD_CTLR) = 0;
    REG8(GICD_IPRIORITYR(IRQ_KEYS)) = 0xA0;
    REG8(GICD_ITARGETSR(IRQ_KEYS)) = 0x01;                      /* CPU0 */
    REG(GICD_ISENABLER(IRQ_KEYS / 32u)) = 1u << (IRQ_KEYS % 32u);
    REG(GICD_CTLR) = 1;

    REG(GICC_PMR) = 0xFF;                                       /* aceptar todas las prioridades */
    REG(GICC_CTLR) = 1;
}

/* Llamada desde irq_entry (start.S) */
void irq_handler(void)
{
    uint32_t iar = REG(GICC_IAR);
    uint32_t id = iar & 0x3FFu;

    if (id == IRQ_KEYS) {
        uint32_t flancos = REG(KEYS_EDGECAP) & 0xFu;
        REG(KEYS_EDGECAP) = flancos;                            /* limpiar (bit-clearing) */
        teclas_pendientes |= flancos;
        ++total_irq;
    }

    REG(GICC_EOIR) = iar;
}

int main(void)
{
    REG(RSTMGR_BRGMODRST) = 0;
    REG(L3_REMAP) |= (1u << 3) | (1u << 4);

    uart_puts("\r\nprueba io-adc: KEY por IRQ, SW -> LEDR, ADC canal 0\r\n");

    REG(ADC_AUTO) = 1;                                          /* conversion continua */

    REG(KEYS_EDGECAP) = 0xFu;
    REG(KEYS_IRQMASK) = 0xFu;
    gic_init();
    __asm__ volatile("cpsie i" ::: "memory");

    uint32_t adc_anterior = 0xFFFFFFFFu;
    uint32_t sw_anterior = 0xFFFFFFFFu;

    for (;;) {
        uint32_t sw = REG(SWITCHES) & 0x3FFu;
        REG(LEDS) = sw;

        uint32_t pend;
        __asm__ volatile("cpsid i" ::: "memory");
        pend = teclas_pendientes;
        teclas_pendientes = 0;
        __asm__ volatile("cpsie i" ::: "memory");

        for (uint32_t k = 0; k < 4u; ++k) {
            if (pend & (1u << k)) {
                uart_puts("KEY");
                uart_putu(k);
                uart_puts("  (interrupciones: ");
                uart_putu(total_irq);
                uart_puts(")\r\n");
            }
        }

        uint32_t adc = REG(ADC_CH0) & 0xFFFu;
        uint32_t dif = adc > adc_anterior ? adc - adc_anterior : adc_anterior - adc;
        if (adc_anterior == 0xFFFFFFFFu || dif > 32u || sw != sw_anterior) {
            uart_puts("SW=");
            uart_puthex3(sw);
            uart_puts("  ADC0=");
            uart_putu(adc);
            uart_puts(" / 4095\r\n");
            adc_anterior = adc;
            sw_anterior = sw;
        }

        for (volatile uint32_t d = 0; d < 200000u; ++d) {
        }
    }
}
