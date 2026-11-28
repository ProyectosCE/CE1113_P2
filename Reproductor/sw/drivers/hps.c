#include "hps.h"
#include "hw.h"

/*
 * Relojes del HPS.
 *
 * Al cargar por JTAG no corre ningun preloader, y el preloader es quien programa los PLL. El
 * BootROM deja el clock manager en modo seguro con los PLL en bypass: el procesador, la OCRAM y
 * los buses corren con el oscilador de 25 MHz. Eso no alcanza para leer la SD, remuestrear y
 * atender el audio a 44.1 kHz.
 *
 * hps_relojes() programa el PLL principal como lo hace el preloader de la DE1-SoC
 * (u-boot, board/terasic/de1-soc/qts/pll_config.h):
 *
 *   VCO = 25 MHz * 64 = 1600 MHz
 *   mpu_clk  = VCO / 2  = 800 MHz        (procesador)
 *   main_clk = VCO / 4  = 400 MHz        l3_mp 200, l3_sp 100, l4_mp 100, l4_sp 100 MHz
 *   dbg_at   = 400 MHz, dbg = 200 MHz    (depuracion por JTAG)
 *   h2f_user0 = VCO / 64 = 25 MHz       (reloj que el HPS le da al FPGA: igual que antes)
 *   main_nand_sdmmc = VCO / 64 = 25 MHz  (la SD queda con el mismo reloj que antes)
 *
 * El PLL de periferia y el de SDRAM se dejan en bypass (no se usan). L4 sale de main_clk / 4 en
 * vez de periferia / 2, con el mismo resultado: 100 MHz.
 */
#define CM                  0xFFD04000u
#define CM_CTRL             (CM + 0x000u)   /* bit 0: modo seguro (escribir 1 lo limpia) */
#define CM_BYPASS           (CM + 0x004u)   /* bit 0: PLL principal en bypass */
#define CM_INTER            (CM + 0x008u)   /* bit 3: perdio el enganche, bit 6: enganchado */
#define CM_STAT             (CM + 0x014u)   /* bit 0: ocupado */
#define CM_MAIN_VCO         (CM + 0x040u)
#define CM_MAIN_MPUCLK      (CM + 0x048u)
#define CM_MAIN_MAINCLK     (CM + 0x04Cu)
#define CM_MAIN_DBGATCLK    (CM + 0x050u)
#define CM_MAIN_QSPICLK     (CM + 0x054u)
#define CM_MAIN_NANDSDMMC   (CM + 0x058u)
#define CM_MAIN_S2FUSER0    (CM + 0x05Cu)
#define CM_MAIN_MAINDIV     (CM + 0x064u)
#define CM_MAIN_DBGDIV      (CM + 0x068u)
#define CM_MAIN_TRACEDIV    (CM + 0x06Cu)
#define CM_MAIN_L4SRC       (CM + 0x070u)
#define CM_ALT_MPUCLK       (CM + 0x0E0u)
#define CM_ALT_MAINCLK      (CM + 0x0E4u)
#define CM_ALT_DBGATCLK     (CM + 0x0E8u)

#define VCO_BGPWRDN         (1u << 0)
#define VCO_EN              (1u << 1)
#define VCO_PWRDN           (1u << 2)
#define VCO_NUMER(m)        ((uint32_t)(m) << 3)
#define VCO_DENOM(n)        ((uint32_t)(n) << 16)
#define VCO_OUTRESETALL     (1u << 24)

#define INTER_MAINPLLLOST   (1u << 3)
#define INTER_MAINPLLLOCKED (1u << 6)

static uint32_t mhz = 25;

static void esperar(uint32_t n)
{
    for (volatile uint32_t i = 0; i < n; ++i) {
    }
}

static int esperar_fsm(void)
{
    for (uint32_t i = 0; i < 1000000u; ++i)
        if ((REG32(CM_STAT) & 1u) == 0)
            return 0;
    return -1;
}

int hps_relojes(void)
{
    if ((REG32(CM_BYPASS) & 1u) == 0 && (REG32(CM_CTRL) & 1u) == 0) {
        mhz = 800;                                  /* ya lo programo un preloader */
        return 0;
    }

    /* 1. PLL principal en bypass (todo sigue con los 25 MHz del oscilador) */
    REG32(CM_BYPASS) |= 1u;
    if (esperar_fsm())
        return -1;

    /* 2. VCO apagado, luego numerador y denominador con el bandgap encendido */
    REG32(CM_MAIN_VCO) = VCO_DENOM(1) | VCO_NUMER(1) | VCO_PWRDN | VCO_BGPWRDN;
    esperar(1000);                                  /* > 5 us */
    uint32_t vco = VCO_DENOM(0) | VCO_NUMER(63);    /* 25 MHz * 64 / 1 = 1600 MHz */
    REG32(CM_MAIN_VCO) = vco;
    esperar(1000);                                  /* > 7 us antes de habilitar */

    /* 3. Divisores de salida (valores del preloader de la DE1-SoC) */
    REG32(CM_MAIN_MPUCLK)    = 0;
    REG32(CM_ALT_MPUCLK)     = 1;                   /* mpu = VCO / 2 */
    REG32(CM_MAIN_MAINCLK)   = 0;
    REG32(CM_ALT_MAINCLK)    = 3;                   /* main = VCO / 4 */
    REG32(CM_MAIN_DBGATCLK)  = 0;
    REG32(CM_ALT_DBGATCLK)   = 3;
    REG32(CM_MAIN_QSPICLK)   = 3;
    REG32(CM_MAIN_NANDSDMMC) = 63;                  /* 25 MHz, igual que en bypass */
    REG32(CM_MAIN_S2FUSER0)  = 63;                  /* h2f_user0: 25 MHz, igual que en bypass */

    /* 4. Habilitar el VCO y poner los divisores internos */
    REG32(CM_MAIN_VCO) = vco | VCO_EN;
    REG32(CM_MAIN_MAINDIV) = (1u << 0)              /* l3_mp = main / 2 */
                           | (1u << 2)              /* l3_sp = l3_mp / 2 */
                           | (2u << 4)              /* l4_mp = main / 4 */
                           | (2u << 7);             /* l4_sp = main / 4 */
    REG32(CM_MAIN_DBGDIV) = (0u << 0) | (1u << 2);
    REG32(CM_MAIN_TRACEDIV) = 0;
    REG32(CM_MAIN_L4SRC) = 0;                       /* L4 desde main_clk */

    /* 5. Esperar el enganche */
    uint32_t i;
    for (i = 0; i < 1000000u; ++i)
        if (REG32(CM_INTER) & INTER_MAINPLLLOCKED)
            break;
    if (i == 1000000u)
        return -2;                                  /* sigue en bypass: 25 MHz */

    /* 6. Alinear las salidas */
    REG32(CM_MAIN_VCO) = vco | VCO_EN | VCO_OUTRESETALL;
    REG32(CM_MAIN_VCO) = vco | VCO_EN;

    /* 7. Salir de bypass y del modo seguro */
    REG32(CM_BYPASS) &= ~1u;
    if (esperar_fsm())
        return -3;
    REG32(CM_CTRL) |= 1u;                           /* escribir 1 limpia el modo seguro */
    if (esperar_fsm())
        return -4;
    REG32(CM_INTER) = INTER_MAINPLLLOST;            /* limpiar la marca de perdida */

    mhz = 800;
    return 0;
}

uint32_t hps_mhz(void)
{
    return mhz;
}

void hps_iniciar(void)
{
    REG32(HPS_RSTMGR_PERMODRST) |= 1u << 6;        /* watchdog L4WD0 en reset */
    (void)hps_relojes();                           /* 800 MHz; ver hps_mhz() */
    REG32(HPS_RSTMGR_BRGMODRST) = 0;               /* puentes fuera de reset */
    REG32(HPS_L3_REMAP) |= (1u << 3) | (1u << 4);  /* puentes H2F y LW visibles */
}
