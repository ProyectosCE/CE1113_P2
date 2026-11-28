#include "remuestreo.h"
#include "hw.h"

#define UNO     65536u

void remuestreo_iniciar(remuestreo_t *r, uint32_t frecuencia_entrada)
{
    r->paso = (uint32_t)(((uint64_t)frecuencia_entrada << 16) / AUDIO_FS);
    r->fase = 0;
    r->cargadas = 0;
    r->a_izq = r->a_der = r->b_izq = r->b_der = 0;
}

int remuestreo_necesita(const remuestreo_t *r)
{
    return r->cargadas < 2 || r->fase >= UNO;
}

void remuestreo_entrada(remuestreo_t *r, int16_t izq, int16_t der)
{
    if (r->cargadas < 2) {
        if (r->cargadas == 0) {
            r->a_izq = izq;
            r->a_der = der;
        } else {
            r->b_izq = izq;
            r->b_der = der;
        }
        ++r->cargadas;
        return;
    }
    r->a_izq = r->b_izq;
    r->a_der = r->b_der;
    r->b_izq = izq;
    r->b_der = der;
    r->fase -= UNO;
}

/* a + (b - a) * fase, con fase en 16.16 (< 1.0). Se usa fase/2 (15 bits) para no desbordar. */
static int16_t interpolar(int16_t a, int16_t b, uint32_t fase)
{
    return (int16_t)(a + ((((int32_t)b - a) * (int32_t)(fase >> 1)) >> 15));
}

void remuestreo_salida(remuestreo_t *r, int16_t *izq, int16_t *der)
{
    *izq = interpolar(r->a_izq, r->b_izq, r->fase);
    *der = interpolar(r->a_der, r->b_der, r->fase);
    r->fase += r->paso;
}
