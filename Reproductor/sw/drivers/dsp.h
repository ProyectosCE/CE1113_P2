/* dsp_filter_0 (hardware propio): cascada de 3 biquads con coeficientes Q3.15 de 18 bits.
 * Registros y uso: docs/dsp/especificacion-modulo.md */
#ifndef DSP_H
#define DSP_H

#include <stdbool.h>
#include <stdint.h>

#define DSP_NUM_COEF    15      /* 3 etapas x (b0 b1 b2 a1 a2) */

int dsp_iniciar(void);                  /* 0 si responde con el ID y la version esperados */
void dsp_habilitar(bool filtrar);       /* false = bypass */
void dsp_cargar_coeficientes(const int32_t c[DSP_NUM_COEF]);   /* Q3.15; borra el estado */
int16_t dsp_procesar(int16_t muestra, int canal);   /* una muestra del canal 0 o 1 */
bool dsp_saturo(void);                  /* alguna etapa saturo desde la ultima carga */
uint32_t dsp_info(void);                /* ID, version, numero de coeficientes */

#endif
