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

uint32_t dsp_info(void)
{
    return REG32(DSP_INFO);
}

int dsp_iniciar(void)
{
    if ((dsp_info() >> 16) != DSP_ID)
        return -1;
    REG32(DSP_CTRL) = 1u << 1;   /* LIMPIAR, bypass */
    return 0;
}

void dsp_habilitar(bool filtrar)
{
    REG32(DSP_CTRL) = filtrar ? 1u : 0u;
}

void dsp_cargar_coeficientes(const int16_t *c, unsigned n)
{
    for (unsigned i = 0; i < n; ++i) {
        REG32(DSP_COEF_IDX) = i;
        REG32(DSP_COEF_DATA) = (uint32_t)(uint16_t)c[i];
    }
}

int16_t dsp_procesar(int16_t muestra)
{
    REG32(DSP_DATA_IN) = (uint32_t)(uint16_t)muestra;
    for (int i = 0; i < 100; ++i) {
        if (REG32(DSP_STATUS) & 1u)
            return (int16_t)REG32(DSP_DATA_OUT);
    }
    return muestra;   /* sin respuesta: dejar pasar la muestra */
}
