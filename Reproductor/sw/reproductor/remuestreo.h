/* Conversion de la frecuencia del WAV (8, 16 o 44.1 kHz) a la del codec (44.1 kHz). */
#ifndef REMUESTREO_H
#define REMUESTREO_H

#include <stdint.h>

typedef struct {
    uint32_t paso;      /* frecuencia de entrada / 44100, en punto fijo 16.16 */
    uint32_t fase;      /* posicion entre la muestra anterior y la actual, 16.16 */
    int16_t anterior;
    int16_t actual;
} remuestreo_t;

void remuestreo_iniciar(remuestreo_t *r, uint32_t frecuencia_entrada);

/* Cuantas muestras de entrada hay que consumir antes de producir la siguiente salida. */
uint32_t remuestreo_necesita(const remuestreo_t *r);

/* Entrega una muestra de entrada nueva. */
void remuestreo_entrada(remuestreo_t *r, int16_t muestra);

/* Produce la siguiente muestra a 44.1 kHz. */
int16_t remuestreo_salida(remuestreo_t *r);

#endif
