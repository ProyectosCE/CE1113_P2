#include "dsp.h"
#include "hw.h"

#define DSP_CTRL        (DSP_BASE + 0x00u)
#define DSP_STATUS      (DSP_BASE + 0x04u)
#define DSP_DATA_IN     (DSP_BASE + 0x08u)
#define DSP_DATA_OUT    (DSP_BASE + 0x0Cu)
#define DSP_COEF_IDX    (DSP_BASE + 0x10u)
#define DSP_COEF_DATA   (DSP_BASE + 0x14u)
#define DSP_INFO        (DSP_BASE + 0x18u)

#define DSP_ID          0xD5F1u
#define DSP_VERSION     0x02u

#define CTRL_EN         (1u << 0)
#define CTRL_LIMPIAR    (1u << 1)
#define CTRL_CANAL      (1u << 2)

#define STATUS_LISTO    (1u << 0)
#define STATUS_SATURO   (1u << 2)

/* EN se recuerda aqui porque cada escritura de CTRL tambien lleva el canal */
static uint32_t ctrl_en = 0;

uint32_t dsp_info(void)
{
    return REG32(DSP_INFO);
}

int dsp_iniciar(void)
{
    uint32_t info = dsp_info();
    if ((info >> 16) != DSP_ID || ((info >> 8) & 0xFFu) != DSP_VERSION)
        return -1;
    ctrl_en = 0;
    REG32(DSP_CTRL) = CTRL_LIMPIAR;   /* bypass y estado en cero */
    return 0;
}

void dsp_habilitar(bool filtrar)
{
    ctrl_en = filtrar ? CTRL_EN : 0u;
    REG32(DSP_CTRL) = ctrl_en;
}

void dsp_cargar_coeficientes(const int32_t c[DSP_NUM_COEF])
{
    for (unsigned i = 0; i < DSP_NUM_COEF; ++i) {
        REG32(DSP_COEF_IDX) = i;
        REG32(DSP_COEF_DATA) = (uint32_t)c[i];   /* el hardware toma los bits 17:0 */
    }
}

int16_t dsp_procesar(int16_t muestra, int canal)
{
    REG32(DSP_CTRL) = ctrl_en | (canal ? CTRL_CANAL : 0u);
    REG32(DSP_DATA_IN) = (uint32_t)(uint16_t)muestra;
    for (int i = 0; i < 100; ++i) {
        if (REG32(DSP_STATUS) & STATUS_LISTO)
            return (int16_t)REG32(DSP_DATA_OUT);
    }
    return muestra;   /* sin respuesta: dejar pasar la muestra */
}

bool dsp_saturo(void)
{
    return (REG32(DSP_STATUS) & STATUS_SATURO) != 0u;
}
