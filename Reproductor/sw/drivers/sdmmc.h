/* Controlador SD/MMC del HPS: lectura de bloques de 512 bytes de la microSD. */
#ifndef SDMMC_H
#define SDMMC_H

#include <stdint.h>

#define SDMMC_BLOQUE    512u

/* Codigos de retorno (0 = ok) */
#define SDMMC_OK            0
#define SDMMC_E_CONTROLADOR (-1)    /* el controlador no salio de reset o no acepta comandos */
#define SDMMC_E_SIN_TARJETA (-2)    /* la tarjeta no responde a CMD0/CMD8/ACMD41 */
#define SDMMC_E_TIMEOUT     (-3)    /* timeout esperando respuesta o datos */
#define SDMMC_E_RESPUESTA   (-4)    /* error de respuesta o de CRC en un comando */
#define SDMMC_E_DATOS       (-5)    /* error de CRC o de bits de inicio/fin en los datos */
#define SDMMC_E_NO_LISTA    (-6)    /* sdmmc_leer() antes de sdmmc_iniciar() */

typedef struct {
    int      lista;          /* 1 despues de una inicializacion correcta */
    int      alta_capacidad; /* 1 = SDHC/SDXC (direccion en bloques), 0 = SDSC (en bytes) */
    int      version2;       /* 1 = respondio a CMD8 (SD 2.0 o posterior) */
    int      bus_4bits;      /* 1 = bus de datos de 4 bits (ACMD6), 0 = 1 bit */
    uint32_t rca;            /* direccion relativa asignada por la tarjeta */
    uint32_t ocr;            /* registro OCR (respuesta de ACMD41) */
    uint32_t cid[4];         /* identificacion de la tarjeta (fabricante, nombre, serie) */
    uint32_t verid;          /* version del controlador (registro VERID) */
    int      paso;           /* ultimo paso de la inicializacion alcanzado (para depurar) */
} sdmmc_info_t;

int sdmmc_iniciar(void);                                       /* 0 = tarjeta lista */
int sdmmc_leer(uint32_t lba, uint32_t bloques, void *destino);  /* 0 = ok */
const sdmmc_info_t *sdmmc_info(void);
const char *sdmmc_error(int codigo);                            /* texto del codigo */

#endif