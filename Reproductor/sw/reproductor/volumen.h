/* Volumen a partir del potenciometro (ADC canal 0): escalamiento digital en software. */
#ifndef VOLUMEN_H
#define VOLUMEN_H

#include <stdint.h>

void volumen_desde_adc(uint16_t lectura);   /* 0..4095 */
uint32_t volumen_porcentaje(void);           /* 0..100 */
int16_t volumen_aplicar(int16_t muestra);

#endif
