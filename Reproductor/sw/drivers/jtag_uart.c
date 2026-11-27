#include "jtag_uart.h"
#include "hw.h"

#define JTAG_UART_DATA  (JTAG_UART_BASE + 0x0u)
#define JTAG_UART_CTRL  (JTAG_UART_BASE + 0x4u)    /* bits 31:16 = espacio libre */

/* Espera espacio en el FIFO de 64 caracteres; sin terminal leyendo, se rinde y descarta. */
void uart_putc(char c)
{
    for (uint32_t t = 0; t < 2000000u; ++t) {
        if (REG32(JTAG_UART_CTRL) >> 16) {
            REG32(JTAG_UART_DATA) = (uint32_t)c;
            return;
        }
    }
}

void uart_puts(const char *s)
{
    while (*s)
        uart_putc(*s++);
}

void uart_putu(uint32_t v)
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

void uart_puthex(uint32_t v)
{
    static const char hex[] = "0123456789ABCDEF";
    uart_puts("0x");
    for (int i = 28; i >= 0; i -= 4)
        uart_putc(hex[(v >> i) & 0xFu]);
}
