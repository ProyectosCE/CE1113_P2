/* LEDR[9:0] (PIO leds). */
#ifndef LEDS_H
#define LEDS_H

#include <stdint.h>

void leds_escribir(uint32_t valor);   /* bits 9:0 */

#endif
