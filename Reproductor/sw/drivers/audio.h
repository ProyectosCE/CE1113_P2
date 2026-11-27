/* Audio Core (salida, 16 bits) hacia el codec WM8731 a 44.1 kHz. */
#ifndef AUDIO_H
#define AUDIO_H

#include <stdint.h>

void audio_iniciar(void);                         /* vacia los FIFOs de salida */
uint32_t audio_espacio(void);                     /* muestras que caben ahora (min. izq/der) */
void audio_escribir(int16_t izq, int16_t der);    /* una muestra estereo */

#endif
