/* Consola de depuracion por la JTAG UART (scripts/general/terminal.sh). */
#ifndef JTAG_UART_H
#define JTAG_UART_H

#include <stdint.h>

void uart_putc(char c);
void uart_puts(const char *s);
void uart_putu(uint32_t v);        /* decimal */
void uart_puthex(uint32_t v);      /* 0x + 8 digitos */

#endif
