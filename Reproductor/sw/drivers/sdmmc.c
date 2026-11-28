/*
 * Driver del controlador SD/MMC del HPS (Synopsys DesignWare Mobile Storage Host) para leer la
 * microSD por bloques de 512 bytes. Sin DMA: los datos se sacan del FIFO por sondeo.
 *
 * Referencias: Cyclone V Hard Processor System Technical Reference Manual, capitulo
 * "SD/MMC Controller"; SD Physical Layer Simplified Specification (secuencia de comandos).
 *
 * Requisito en la fase 1 (carga por JTAG, sin preloader): encender la placa CON la microSD
 * puesta. El BootROM intenta arrancar desde la SD y en ese intento deja configurados el reloj
 * del controlador y los pines del HPS; este driver parte de esa configuracion.
 */
#include "sdmmc.h"
#include "hw.h"

/* ---------------- Registros del controlador (offset desde HPS_SDMMC_BASE) ---------------- */
#define SD(off)             REG32(HPS_SDMMC_BASE + (off))
#define SD_CTRL             SD(0x000)
#define SD_PWREN            SD(0x004)
#define SD_CLKDIV           SD(0x008)
#define SD_CLKSRC           SD(0x00C)
#define SD_CLKENA           SD(0x010)
#define SD_TMOUT            SD(0x014)
#define SD_CTYPE            SD(0x018)
#define SD_BLKSIZ           SD(0x01C)
#define SD_BYTCNT           SD(0x020)
#define SD_INTMASK          SD(0x024)
#define SD_CMDARG           SD(0x028)
#define SD_CMD              SD(0x02C)
#define SD_RESP0            SD(0x030)
#define SD_RESP1            SD(0x034)
#define SD_RESP2            SD(0x038)
#define SD_RESP3            SD(0x03C)
#define SD_RINTSTS          SD(0x044)
#define SD_STATUS           SD(0x048)
#define SD_VERID            SD(0x06C)
#define SD_BMOD             SD(0x080)
#define SD_DATA             SD(0x200)       /* FIFO de datos */

/* CTRL */
#define CTRL_RESET_CTRL     (1u << 0)
#define CTRL_RESET_FIFO     (1u << 1)
#define CTRL_RESET_DMA      (1u << 2)
#define CTRL_INT_ENABLE     (1u << 4)
#define CTRL_USE_IDMAC      (1u << 25)

/* CMD */
#define CMD_RESP_EXP        (1u << 6)
#define CMD_RESP_LONG       (1u << 7)
#define CMD_CHECK_CRC       (1u << 8)
#define CMD_DATA_EXP        (1u << 9)
#define CMD_WAIT_PRVDATA    (1u << 13)
#define CMD_SEND_INIT       (1u << 15)
#define CMD_UPD_CLK         (1u << 21)
#define CMD_USE_HOLD_REG    (1u << 29)
#define CMD_START           (1u << 31)

/* RINTSTS (se limpian escribiendo 1) */
#define INT_RE              (1u << 1)       /* error de respuesta */
#define INT_CMD_DONE        (1u << 2)
#define INT_DTO             (1u << 3)       /* transferencia de datos terminada */
#define INT_RXDR            (1u << 5)       /* FIFO con datos para leer */
#define INT_RCRC            (1u << 6)
#define INT_DCRC            (1u << 7)
#define INT_RTO             (1u << 8)       /* timeout de respuesta */
#define INT_DRTO            (1u << 9)       /* timeout de datos */
#define INT_HTO             (1u << 10)
#define INT_HLE             (1u << 12)
#define INT_SBE             (1u << 13)
#define INT_EBE             (1u << 15)
#define INT_ERR_DATOS       (INT_DCRC | INT_DRTO | INT_HTO | INT_SBE | INT_EBE)

/* STATUS */
#define STATUS_DATA_BUSY    (1u << 9)
#define STATUS_FIFO_COUNT(s) (((s) >> 17) & 0x1FFFu)

/* ---------------- Reset y reloj del HPS ---------------- */
#define RSTMGR_PERMODRST_SDMMC  (1u << 22)
#define CLKMGR_PERPLL_EN        0xFFD040A0u
#define CLKMGR_PERPLL_EN_SDMMC  (1u << 8)

/*
 * Divisores del reloj de la tarjeta: cclk_out = cclk_in / (2 * div). Con el reloj que suele
 * recibir el controlador (cclk_in ~50 MHz) quedan ~98 kHz para la identificacion (la norma pide
 * <= 400 kHz) y ~25 MHz para los datos (el maximo de la norma en modo normal). Si el BootROM dejo
 * un cclk_in menor, ambos quedan mas lentos, pero dentro de la norma.
 */
#define DIV_IDENTIFICACION  255u
#define DIV_DATOS           1u      /* cclk_in / 2: ~25 MHz con cclk_in de 50 MHz */

/* Limites de espera en iteraciones de sondeo (sin preloader no se conoce el reloj del CPU) */
#define ESPERA_CORTA        1000000u
#define ESPERA_LARGA        20000000u
#define INTENTOS_ACMD41     2000u

static sdmmc_info_t info;

/* ---------------- Utilidades ---------------- */

static void retardo(uint32_t n)
{
    for (volatile uint32_t i = 0; i < n; ++i) {
    }
}

/* Espera a que los bits de la mascara queden en 0. 0 = ok, -1 = timeout */
static int esperar_ceros(uint32_t dir, uint32_t mascara, uint32_t limite)
{
    for (uint32_t i = 0; i < limite; ++i) {
        if ((REG32(dir) & mascara) == 0)
            return 0;
    }
    return -1;
}

#define DIR(off)    (HPS_SDMMC_BASE + (off))

static int esperar_no_ocupado(void)
{
    return esperar_ceros(DIR(0x048), STATUS_DATA_BUSY, ESPERA_LARGA) == 0 ?
           SDMMC_OK : SDMMC_E_TIMEOUT;
}

/* Comando "solo actualizar reloj": el controlador toma los valores de CLKDIV/CLKENA */
static int actualizar_reloj(void)
{
    SD_CMD = CMD_START | CMD_UPD_CLK | CMD_WAIT_PRVDATA;
    if (esperar_ceros(DIR(0x02C), CMD_START, ESPERA_CORTA) != 0)
        return SDMMC_E_CONTROLADOR;
    if (SD_RINTSTS & INT_HLE) {
        SD_RINTSTS = INT_HLE;
        return SDMMC_E_CONTROLADOR;
    }
    return SDMMC_OK;
}

static int fijar_reloj(uint32_t divisor)
{
    int r;
    SD_CLKENA = 0;
    if ((r = actualizar_reloj()) != SDMMC_OK)
        return r;
    SD_CLKSRC = 0;
    SD_CLKDIV = divisor & 0xFFu;
    if ((r = actualizar_reloj()) != SDMMC_OK)
        return r;
    SD_CLKENA = 1;
    return actualizar_reloj();
}

/* Tipos de respuesta de la norma SD */
typedef enum { R_NINGUNA, R1, R1B, R2, R3, R6, R7 } respuesta_t;

/* Envia un comando y espera su respuesta. "extra": CMD_DATA_EXP o CMD_SEND_INIT */
static int enviar(uint32_t indice, uint32_t argumento, respuesta_t resp, uint32_t extra)
{
    uint32_t flags = (indice & 0x3Fu) | CMD_START | CMD_USE_HOLD_REG | extra;

    if (resp != R_NINGUNA)
        flags |= CMD_RESP_EXP;
    if (resp == R2)
        flags |= CMD_RESP_LONG;
    if (resp != R_NINGUNA && resp != R3)        /* R3 (OCR) no trae CRC valido */
        flags |= CMD_CHECK_CRC;
    if (!(extra & CMD_SEND_INIT))
        flags |= CMD_WAIT_PRVDATA;

    if (esperar_no_ocupado() != SDMMC_OK)
        return SDMMC_E_TIMEOUT;

    SD_RINTSTS = 0xFFFFFFFFu;
    SD_CMDARG = argumento;
    SD_CMD = flags;

    if (esperar_ceros(DIR(0x02C), CMD_START, ESPERA_CORTA) != 0)
        return SDMMC_E_CONTROLADOR;

    uint32_t st = 0;
    for (uint32_t i = 0; i < ESPERA_LARGA; ++i) {
        st = SD_RINTSTS;
        if (st & (INT_CMD_DONE | INT_RTO))
            break;
    }
    if (st & INT_RTO)
        return SDMMC_E_TIMEOUT;
    if (!(st & INT_CMD_DONE))
        return SDMMC_E_TIMEOUT;
    if (st & (INT_RE | INT_HLE))
        return SDMMC_E_RESPUESTA;
    if ((flags & CMD_CHECK_CRC) && (st & INT_RCRC))
        return SDMMC_E_RESPUESTA;

    if (resp == R1B)                            /* la tarjeta queda ocupada en DAT0 */
        return esperar_no_ocupado();
    return SDMMC_OK;
}

/* Comando de aplicacion: CMD55 + ACMDn */
static int enviar_acmd(uint32_t indice, uint32_t argumento, respuesta_t resp)
{
    int r = enviar(55, info.rca << 16, R1, 0);
    if (r != SDMMC_OK)
        return r;
    return enviar(indice, argumento, resp, 0);
}

static int leer_bloque(uint32_t lba, uint8_t *destino);

/* ---------------- API ---------------- */

const sdmmc_info_t *sdmmc_info(void)
{
    return &info;
}

const char *sdmmc_error(int codigo)
{
    switch (codigo) {
    case SDMMC_OK:            return "ok";
    case SDMMC_E_CONTROLADOR: return "el controlador no responde";
    case SDMMC_E_SIN_TARJETA: return "la tarjeta no responde";
    case SDMMC_E_TIMEOUT:     return "timeout";
    case SDMMC_E_RESPUESTA:   return "error de respuesta o CRC del comando";
    case SDMMC_E_DATOS:       return "error de CRC o de transferencia de datos";
    case SDMMC_E_NO_LISTA:    return "tarjeta no inicializada";
    }
    return "error desconocido";
}

int sdmmc_iniciar(void)
{
    int r;

    /* Borrar info campo a campo (sin memset: no hay biblioteca de C) */
    info.lista = 0;
    info.alta_capacidad = 0;
    info.version2 = 0;
    info.rca = 0;
    info.ocr = 0;
    for (int i = 0; i < 4; ++i)
        info.cid[i] = 0;
    info.verid = 0;
    info.bus_4bits = 0;

    /* Paso 1: controlador fuera de reset y con reloj */
    info.paso = 1;
    REG32(HPS_RSTMGR_PERMODRST) &= ~RSTMGR_PERMODRST_SDMMC;
    REG32(CLKMGR_PERPLL_EN) |= CLKMGR_PERPLL_EN_SDMMC;
    info.verid = SD_VERID;

    /* Paso 2: reset interno de controlador, FIFO y DMA; sin interrupciones ni DMA interno */
    info.paso = 2;
    SD_CTRL = CTRL_RESET_CTRL | CTRL_RESET_FIFO | CTRL_RESET_DMA;
    if (esperar_ceros(DIR(0x000), CTRL_RESET_CTRL | CTRL_RESET_FIFO | CTRL_RESET_DMA,
                      ESPERA_CORTA) != 0)
        return SDMMC_E_CONTROLADOR;
    SD_CTRL &= ~(CTRL_INT_ENABLE | CTRL_USE_IDMAC);
    SD_BMOD = 0;
    SD_INTMASK = 0;
    SD_RINTSTS = 0xFFFFFFFFu;
    SD_TMOUT = 0xFFFFFFFFu;     /* timeouts maximos de respuesta y de datos */
    SD_CTYPE = 0;               /* bus de 1 bit */

    /* Paso 3: alimentacion de la tarjeta y reloj lento para la identificacion */
    info.paso = 3;
    SD_PWREN = 1;
    retardo(100000);
    if ((r = fijar_reloj(DIV_IDENTIFICACION)) != SDMMC_OK)
        return r;

    /* Paso 4: CMD0, reiniciar la tarjeta (con los 80 ciclos de inicializacion) */
    info.paso = 4;
    if ((r = enviar(0, 0, R_NINGUNA, CMD_SEND_INIT)) != SDMMC_OK)
        return r;

    /* Paso 5: CMD8, tension 2.7-3.6 V y patron 0xAA. Sin respuesta = tarjeta SD 1.x */
    info.paso = 5;
    r = enviar(8, 0x1AAu, R7, 0);
    if (r == SDMMC_OK) {
        if ((SD_RESP0 & 0xFFFu) != 0x1AAu)
            return SDMMC_E_SIN_TARJETA;
        info.version2 = 1;
    } else if (r != SDMMC_E_TIMEOUT) {
        return r;
    }

    /* Paso 6: ACMD41 hasta que la tarjeta termine su encendido (bit 31 del OCR) */
    info.paso = 6;
    uint32_t arg41 = 0x00FF8000u | (info.version2 ? (1u << 30) : 0u);   /* 2.7-3.6 V, HCS */
    for (uint32_t i = 0; ; ++i) {
        if (i >= INTENTOS_ACMD41)
            return SDMMC_E_SIN_TARJETA;
        r = enviar_acmd(41, arg41, R3);
        if (r != SDMMC_OK)
            return (r == SDMMC_E_TIMEOUT) ? SDMMC_E_SIN_TARJETA : r;
        info.ocr = SD_RESP0;
        if (info.ocr & (1u << 31))
            break;
        retardo(10000);
    }
    info.alta_capacidad = (int)((info.ocr >> 30) & 1u);

    /* Paso 7: CMD2 (identificacion, CID) y CMD3 (direccion relativa, RCA) */
    info.paso = 7;
    if ((r = enviar(2, 0, R2, 0)) != SDMMC_OK)
        return r;
    info.cid[0] = SD_RESP3;     /* bits 127:96 */
    info.cid[1] = SD_RESP2;
    info.cid[2] = SD_RESP1;
    info.cid[3] = SD_RESP0;

    if ((r = enviar(3, 0, R6, 0)) != SDMMC_OK)
        return r;
    info.rca = SD_RESP0 >> 16;

    /* Paso 8: CMD7, seleccionar la tarjeta (pasa a estado de transferencia) */
    info.paso = 8;
    if ((r = enviar(7, info.rca << 16, R1B, 0)) != SDMMC_OK)
        return r;

    /* Paso 9: en tarjetas SDSC, bloques de 512 bytes (en SDHC/SDXC ya es fijo) */
    info.paso = 9;
    if (!info.alta_capacidad && (r = enviar(16, SDMMC_BLOQUE, R1, 0)) != SDMMC_OK)
        return r;

    /* Paso 10: bus de 4 bits (ACMD6, argumento 2). Si la tarjeta no acepta, sigue en 1 bit. */
    info.paso = 10;
    if (enviar_acmd(6, 2, R1) == SDMMC_OK) {
        SD_CTYPE = 1;
        info.bus_4bits = 1;
    }

    /* Paso 11: reloj de datos */
    info.paso = 11;
    if ((r = fijar_reloj(DIV_DATOS)) != SDMMC_OK)
        return r;

    /* Paso 12: lectura de prueba del sector 0. Si falla en 4 bits (pines DAT1-3 sin configurar),
     * volver a 1 bit y probar de nuevo. */
    info.paso = 12;
    static uint8_t prueba[SDMMC_BLOQUE];
    r = leer_bloque(0, prueba);
    if (r != SDMMC_OK && info.bus_4bits) {
        enviar_acmd(6, 0, R1);
        SD_CTYPE = 0;
        info.bus_4bits = 0;
        r = leer_bloque(0, prueba);
    }
    if (r != SDMMC_OK)
        return r;

    info.lista = 1;
    return SDMMC_OK;
}

/* Lee un bloque de 512 bytes con CMD17 */
static int leer_bloque(uint32_t lba, uint8_t *destino)
{
    int r;

    if (esperar_no_ocupado() != SDMMC_OK)
        return SDMMC_E_TIMEOUT;

    SD_CTRL |= CTRL_RESET_FIFO;
    if (esperar_ceros(DIR(0x000), CTRL_RESET_FIFO, ESPERA_CORTA) != 0)
        return SDMMC_E_CONTROLADOR;

    SD_BLKSIZ = SDMMC_BLOQUE;
    SD_BYTCNT = SDMMC_BLOQUE;

    /* SDHC/SDXC se direcciona por bloque; SDSC por byte */
    uint32_t direccion = info.alta_capacidad ? lba : lba * SDMMC_BLOQUE;
    if ((r = enviar(17, direccion, R1, CMD_DATA_EXP)) != SDMMC_OK)
        return r;

    uint32_t palabras = 0;
    for (uint32_t i = 0; i < ESPERA_LARGA && palabras < SDMMC_BLOQUE / 4u; ++i) {
        uint32_t st = SD_RINTSTS;
        if (st & INT_ERR_DATOS) {
            SD_RINTSTS = 0xFFFFFFFFu;
            return SDMMC_E_DATOS;
        }
        uint32_t n = STATUS_FIFO_COUNT(SD_STATUS);
        while (n-- && palabras < SDMMC_BLOQUE / 4u) {
            uint32_t w = SD_DATA;
            destino[0] = (uint8_t)w;
            destino[1] = (uint8_t)(w >> 8);
            destino[2] = (uint8_t)(w >> 16);
            destino[3] = (uint8_t)(w >> 24);
            destino += 4;
            ++palabras;
        }
        if (st & INT_RXDR)
            SD_RINTSTS = INT_RXDR;
    }
    if (palabras < SDMMC_BLOQUE / 4u)
        return SDMMC_E_TIMEOUT;

    /* Esperar el fin de la transferencia */
    for (uint32_t i = 0; i < ESPERA_LARGA; ++i) {
        uint32_t st = SD_RINTSTS;
        if (st & INT_ERR_DATOS) {
            SD_RINTSTS = 0xFFFFFFFFu;
            return SDMMC_E_DATOS;
        }
        if (st & INT_DTO) {
            SD_RINTSTS = 0xFFFFFFFFu;
            return SDMMC_OK;
        }
    }
    return SDMMC_E_TIMEOUT;
}

int sdmmc_leer(uint32_t lba, uint32_t bloques, void *destino)
{
    if (!info.lista)
        return SDMMC_E_NO_LISTA;

    uint8_t *p = destino;
    for (uint32_t i = 0; i < bloques; ++i) {
        int r = leer_bloque(lba + i, p);
        if (r != SDMMC_OK)
            return r;
        p += SDMMC_BLOQUE;
        /* TODO: CMD18 (lectura multiple) para mas velocidad al reproducir */
    }
    return SDMMC_OK;
}