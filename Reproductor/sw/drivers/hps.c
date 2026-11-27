#include "hps.h"
#include "hw.h"

void hps_iniciar(void)
{
    REG32(HPS_RSTMGR_PERMODRST) |= 1u << 6;        /* watchdog L4WD0 en reset */
    REG32(HPS_RSTMGR_BRGMODRST) = 0;               /* puentes fuera de reset */
    REG32(HPS_L3_REMAP) |= (1u << 3) | (1u << 4);  /* puentes H2F y LW visibles */
}
