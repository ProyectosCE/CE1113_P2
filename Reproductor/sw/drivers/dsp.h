/* dsp_filter_0 (hardware propio): filtro de audio. Hoy es un esqueleto de paso directo. */
#ifndef DSP_H
#define DSP_H

#include <stdbool.h>
#include <stdint.h>

int dsp_iniciar(void);                                  /* 0 si responde con el ID esperado */
void dsp_habilitar(bool filtrar);                       /* false = bypass */
void dsp_cargar_coeficientes(const int16_t *c, unsigned n);   /* Q1.15 */
int16_t dsp_procesar(int16_t muestra);                  /* una muestra, espera el resultado */
uint32_t dsp_info(void);                                /* ID, version, numero de coeficientes */

#endif
