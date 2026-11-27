#include "volumen.h"

/* Con el potenciometro a 3.3 V el ADC llega a ~3300 de 4095: ese valor es el volumen maximo. */
#define ADC_MAXIMO  3300u

static uint32_t factor = 32768u;   /* Q15: 32768 = 1.0 */

void volumen_desde_adc(uint16_t lectura)
{
    uint32_t v = lectura > ADC_MAXIMO ? ADC_MAXIMO : lectura;
    factor = (v * 32768u) / ADC_MAXIMO;
    /* TODO: curva logaritmica y filtrar el ruido del ADC (+-3 cuentas) */
}

uint32_t volumen_porcentaje(void)
{
    return (factor * 100u) >> 15;
}

int16_t volumen_aplicar(int16_t muestra)
{
    return (int16_t)(((int32_t)muestra * (int32_t)factor) >> 15);
}
