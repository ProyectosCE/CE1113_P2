#include "sdmmc.h"
#include "hw.h"

/*
 * PENDIENTE. Pasos previstos (Cyclone V HPS Technical Reference Manual, capitulo SD/MMC):
 *  - reloj y reset del controlador (en fase 1 el BootROM ya los dejo listos al intentar arrancar
 *    desde la SD; en fase 2 los configura el preloader)
 *  - secuencia de inicializacion de la tarjeta: CMD0, CMD8, ACMD41, CMD2, CMD3, CMD7, ACMD6 (4 bits)
 *  - lectura por bloques: CMD17 / CMD18 leyendo el FIFO del controlador
 */

int sdmmc_iniciar(void)
{
    return -1;   /* TODO */
}

int sdmmc_leer(uint32_t lba, uint32_t bloques, void *destino)
{
    (void)lba;
    (void)bloques;
    (void)destino;
    return -1;   /* TODO */
}
