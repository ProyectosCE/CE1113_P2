/* ADC LTC2308 (ADC Controller for DE-series Boards). Canal 0 = potenciometro de volumen. */
#ifndef ADC_H
#define ADC_H

#include <stdint.h>

void adc_iniciar(void);              /* activa la conversion continua */
uint16_t adc_leer(unsigned canal);   /* 0..4095 */

#endif
