/* Parser WAV: formato de audio y metadatos (chunk LIST/INFO). */
#ifndef WAV_H
#define WAV_H

#include <stdint.h>
#include "fat.h"

#define WAV_TEXTO_MAX   48

typedef struct {
    uint32_t frecuencia;        /* Hz: 8000, 16000 o 44100 */
    uint16_t canales;           /* 1 o 2 */
    uint16_t bits;              /* 16 */
    uint32_t bytes_datos;       /* tamano del chunk "data" */
    uint32_t duracion_s;        /* bytes_datos / (frecuencia * canales * 2) */
    char titulo[WAV_TEXTO_MAX];     /* INAM */
    char artista[WAV_TEXTO_MAX];    /* IART */
    char album[WAV_TEXTO_MAX];      /* IPRD */
} wav_info_t;

/* Lee la cabecera del archivo abierto y deja la posicion al inicio de las muestras. 0 = ok. */
int wav_abrir(fat_archivo_t *archivo, wav_info_t *info);

#endif
