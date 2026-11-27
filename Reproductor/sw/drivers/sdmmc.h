/* Controlador SD/MMC del HPS: lectura de bloques de 512 bytes de la microSD. */
#ifndef SDMMC_H
#define SDMMC_H

#include <stdint.h>

#define SDMMC_BLOQUE    512u

int sdmmc_iniciar(void);                                       /* 0 = tarjeta lista */
int sdmmc_leer(uint32_t lba, uint32_t bloques, void *destino);  /* 0 = ok */

#endif
