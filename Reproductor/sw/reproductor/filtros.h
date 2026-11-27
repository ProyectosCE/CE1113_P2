/* Filtros de audio seleccionables con SW[1:0]. Al menos uno en hardware (dsp_filter_0). */
#ifndef FILTROS_H
#define FILTROS_H

#include <stdint.h>

typedef enum {
    FILTRO_BYPASS   = 0,    /* sin filtro */
    FILTRO_HW       = 1,    /* dsp_filter_0 (hardware propio) */
    FILTRO_SW_1     = 2,    /* filtro en software (por definir) */
    FILTRO_SW_2     = 3,    /* filtro en software (por definir) */
} filtro_t;

void filtros_iniciar(void);
void filtros_seleccionar(filtro_t f);   /* cambio inmediato (requisito < 100 ms) */
filtro_t filtros_actual(void);
const char *filtros_nombre(filtro_t f);
int16_t filtros_procesar(int16_t muestra, int canal);   /* canal 0 = izq, 1 = der */

#endif
