/*
 * Conversion de la frecuencia del WAV (8, 16 o 44.1 kHz) a la del codec (44.1 kHz) por
 * interpolacion lineal. Trabaja con muestras estereo (el mono se duplica antes).
 */
#ifndef REMUESTREO_H
#define REMUESTREO_H

#include <stdint.h>

typedef struct {
    uint32_t paso;          /* frecuencia de entrada / 44100 en punto fijo 16.16 */
    uint32_t fase;          /* posicion entre "a" y "b" en 16.16 (0 = a, 65536 = b) */
    int      cargadas;      /* muestras de entrada cargadas al iniciar (hasta 2) */
    int16_t  a_izq, a_der;  /* muestra de entrada anterior */
    int16_t  b_izq, b_der;  /* muestra de entrada siguiente */
} remuestreo_t;

void remuestreo_iniciar(remuestreo_t *r, uint32_t frecuencia_entrada);

/* 1 si hay que entregar otra muestra de entrada antes de pedir la siguiente salida. */
int remuestreo_necesita(const remuestreo_t *r);

void remuestreo_entrada(remuestreo_t *r, int16_t izq, int16_t der);

/* Produce la siguiente muestra a 44.1 kHz. */
void remuestreo_salida(remuestreo_t *r, int16_t *izq, int16_t *der);

#endif
