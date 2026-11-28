/*
 * Audio Core (salida, 16 bits) hacia el codec WM8731 a 44.1 kHz.
 *
 * El FIFO del codec se llena por interrupcion (GIC ID 72) desde una cola en memoria: el lazo
 * principal encola muestras ya procesadas (lectura de la SD, remuestreo, filtros, volumen) y la
 * interrupcion las entrega al codec. Asi, leer la SD no corta el sonido. Si la cola se vacia, la
 * interrupcion envia silencio.
 */
#ifndef AUDIO_H
#define AUDIO_H

#include <stdint.h>

#define AUDIO_COLA      4096u    /* muestras estereo en cola (~93 ms a 44.1 kHz); potencia de 2 */

/* Configura el Audio Core y registra su interrupcion (llamar despues de gic_iniciar). */
void audio_iniciar(void);

/* Lugares libres en la cola. */
uint32_t audio_libres(void);

/* Encola una muestra estereo. Devuelve 0 si la cola esta llena. */
int audio_encolar(int16_t izq, int16_t der);

/* Nombres que usa el lazo de main.c (equivalentes a audio_libres / audio_encolar). */
uint32_t audio_espacio(void);
void audio_escribir(int16_t izq, int16_t der);

/* Descarta lo que haya en la cola (cambio de cancion, stop) y reinicia el contador. */
void audio_vaciar(void);

/* Muestras de la cola enviadas al codec desde el ultimo audio_vaciar() (sin contar silencio). */
uint32_t audio_reproducidas(void);

/* Diagnostico: muestras de silencio que la interrupcion tuvo que mandar porque la cola estaba
 * vacia (el lazo principal no alcanzo a producir). Debe quedarse en 0 durante la reproduccion. */
uint32_t audio_faltantes(void);
uint32_t audio_irqs(void);          /* interrupciones atendidas */
uint32_t audio_al_codec(void);      /* muestras escritas al FIFO del codec (reloj real: 44100/s) */
uint32_t audio_encoladas(void);     /* muestras que el lazo principal metio a la cola */

#endif
