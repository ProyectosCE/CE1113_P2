/* Configuracion minima del HPS para trabajar sin preloader (fase 1, carga por JTAG). */
#ifndef HPS_H
#define HPS_H

/* Saca los puentes HPS->FPGA de reset y los habilita; deja el watchdog del BootROM en reset. */
void hps_iniciar(void);

#endif
