#include "remuestreo.h"
#include "hw.h"

/*
 * PENDIENTE: interpolacion lineal entre "anterior" y "actual" segun "fase". Por ahora la salida
 * es la ultima muestra de entrada, que solo es correcta a 44.1 kHz.
 */

void remuestreo_iniciar(remuestreo_t *r, uint32_t frecuencia_entrada)
{
    r->paso = (uint32_t)(((uint64_t)frecuencia_entrada << 16) / AUDIO_FS);
    r->fase = 0;
    r->anterior = 0;
    r->actual = 0;
}

uint32_t remuestreo_necesita(const remuestreo_t *r)
{
    (void)r;
    return 1;   /* TODO: segun fase y paso */
}

void remuestreo_entrada(remuestreo_t *r, int16_t muestra)
{
    r->anterior = r->actual;
    r->actual = muestra;
}

int16_t remuestreo_salida(remuestreo_t *r)
{
    return r->actual;   /* TODO: interpolar */
}
