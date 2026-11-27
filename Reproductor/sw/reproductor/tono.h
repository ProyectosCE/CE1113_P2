/*
 * Fuente de audio de prueba: tono triangular de 441 Hz. Reemplaza a la lectura del WAV mientras
 * fat.c y wav.c no esten implementados, para poder probar toda la cadena de audio.
 */
#ifndef TONO_H
#define TONO_H

#include <stdint.h>

int16_t tono_siguiente(void);

#endif
