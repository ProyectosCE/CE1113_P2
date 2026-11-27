#include "tono.h"

#define AMPLITUD    8000
#define PASO        (4 * AMPLITUD / 100)   /* 100 muestras por periodo: 441 Hz a 44.1 kHz */

static int32_t valor = -AMPLITUD;
static int32_t paso = PASO;

int16_t tono_siguiente(void)
{
    int16_t m = (int16_t)valor;
    valor += paso;
    if (valor >= AMPLITUD || valor <= -AMPLITUD)
        paso = -paso;
    return m;
}
