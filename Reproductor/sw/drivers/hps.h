/* Configuracion minima del HPS para trabajar sin preloader (fase 1, carga por JTAG). */
#ifndef HPS_H
#define HPS_H

#include <stdint.h>

/* Saca los puentes HPS->FPGA de reset y los habilita; deja el watchdog del BootROM en reset. */
void hps_iniciar(void);

/* Programa el PLL principal: procesador a 800 MHz, buses L3/L4 a 200/100 MHz (lo llama
 * hps_iniciar). 0 = ok; <0 = se queda en 25 MHz. */
int hps_relojes(void);
uint32_t hps_mhz(void);                 /* 800 si el PLL quedo programado, 25 si no */

#endif
