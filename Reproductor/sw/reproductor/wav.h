/* Parser WAV: formato de audio y metadatos (chunk LIST/INFO). */
#ifndef WAV_H
#define WAV_H

#include <stdint.h>
#include "fat.h"

#define WAV_TEXTO_MAX   48

/* Codigos de retorno (0 = ok) */
#define WAV_OK              0
#define WAV_E_LECTURA       (-20)   /* error leyendo el archivo */
#define WAV_E_NO_WAV        (-21)   /* no empieza con RIFF/WAVE */
#define WAV_E_FORMATO       (-22)   /* no es PCM de 16 bits, mono o estereo */
#define WAV_E_SIN_DATOS     (-23)   /* falta el chunk "fmt " o "data" */

typedef struct {
    uint32_t frecuencia;            /* Hz */
    uint16_t canales;               /* 1 o 2 */
    uint16_t bits;                  /* 16 */
    uint32_t inicio_datos;          /* posicion del primer byte de audio en el archivo */
    uint32_t bytes_datos;           /* tamano del audio */
    uint32_t duracion_s;
    char titulo[WAV_TEXTO_MAX];     /* INAM */
    char artista[WAV_TEXTO_MAX];    /* IART */
    char album[WAV_TEXTO_MAX];      /* IPRD */
} wav_info_t;

/*
 * Lee la cabecera del archivo abierto y deja la posicion al inicio del audio.
 * Si el WAV no trae titulo, queda vacio (el player usa el nombre del archivo).
 */
int wav_abrir(fat_archivo_t *archivo, wav_info_t *info);
const char *wav_error(int codigo);

#endif
