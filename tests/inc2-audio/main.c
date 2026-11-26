/*
 * Incremento 2 - prueba del audio: tono triangular de 441 Hz por Line Out.
 *
 * - Envia muestras al Audio Core por sondeo del registro fifospace.
 * - LEDR0 cambia cada 44100 muestras (1 s de audio si el codec va a 44.1 kHz).
 * - Cada 10 s de audio imprime el total por la JTAG UART (scripts/general/terminal.sh).
 * - LEDR9 encendido = el programa arranco y los puentes HPS->FPGA estan habilitados.
 *
 * Acceso directo a registros (sin HAL). Se compila con ../inc0-hps/start.S y ocram.ld.
 */
#include <stdint.h>

#define REG(dir)            (*(volatile uint32_t *)(dir))

/* HPS */
#define RSTMGR_BRGMODRST    0xFFD0501Cu     /* reset de los puentes HPS<->FPGA */
#define L3_REMAP            0xFF800000u     /* bit 3: H2F, bit 4: LW H2F */

/* Perifericos en el puente lightweight */
#define LW_BASE             0xFF200000u
#define LEDS                (LW_BASE + 0x0000u)
#define JTAG_UART_DATA      (LW_BASE + 0x1000u)
#define JTAG_UART_CTRL      (LW_BASE + 0x1004u)  /* bits 31:16 = espacio libre (WSPACE) */
#define AUDIO_CTRL          (LW_BASE + 0x3040u)
#define AUDIO_FIFOSPACE     (LW_BASE + 0x3044u)  /* 31:24 WSLC, 23:16 WSRC */
#define AUDIO_LEFT          (LW_BASE + 0x3048u)
#define AUDIO_RIGHT         (LW_BASE + 0x304Cu)

#define AUDIO_CTRL_CW       (1u << 3)            /* limpia los FIFOs de salida */

#define FS                  44100u
#define AMPLITUD            8000                 /* ~25 % de escala completa: volumen moderado */
#define PASO                (4 * AMPLITUD / 100) /* triangular de 100 muestras = 441 Hz a 44.1 kHz */

/* Escribe en la JTAG UART sin bloquear: si no hay terminal conectada, descarta. */
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

int main(void)
{
    /* Sacar los puentes de reset y habilitarlos en el L3 */
    REG(RSTMGR_BRGMODRST) = 0;
    REG(L3_REMAP) |= (1u << 3) | (1u << 4);

    uint32_t leds = 1u << 9;
    REG(LEDS) = leds;
    uart_puts("\r\ninc2: tono de 441 Hz por Line Out\r\n");

    /* Vaciar los FIFOs de salida */
    REG(AUDIO_CTRL) = AUDIO_CTRL_CW;
    REG(AUDIO_CTRL) = 0;

    int32_t muestra = -AMPLITUD;
    int32_t paso = PASO;
    uint32_t en_segundo = 0, segundos = 0;

    for (;;) {
        uint32_t libre = REG(AUDIO_FIFOSPACE);
        uint32_t wslc = (libre >> 24) & 0xFFu;
        uint32_t wsrc = (libre >> 16) & 0xFFu;
        uint32_t n = wslc < wsrc ? wslc : wsrc;

        while (n--) {
            REG(AUDIO_LEFT) = (uint32_t)muestra;
            REG(AUDIO_RIGHT) = (uint32_t)muestra;

            muestra += paso;
            if (muestra >= AMPLITUD || muestra <= -AMPLITUD)
                paso = -paso;

            if (++en_segundo == FS) {
                en_segundo = 0;
                ++segundos;
                leds ^= 1u;
                REG(LEDS) = leds;
                if (segundos % 10u == 0) {
                    uart_puts("audio enviado: ");
                    uart_putu(segundos);
                    uart_puts(" s\r\n");
                }
            }
        }
    }
}
