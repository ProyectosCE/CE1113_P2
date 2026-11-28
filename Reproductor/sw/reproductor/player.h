/*
 * Logica de reproduccion: estados, botones, cancion actual y tiempo transcurrido.
 *
 * Fuente de audio: las canciones .wav de la microSD (fat.c + wav.c + remuestreo.c). Si la SD no
 * se pudo leer o no tiene canciones, player_muestra() entrega el tono de prueba (tono.c).
 */
#ifndef PLAYER_H
#define PLAYER_H

#include <stdint.h>
#include "wav.h"

typedef enum {
    PLAYER_DETENIDO,
    PLAYER_REPRODUCIENDO,
    PLAYER_PAUSADO,
} player_estado_t;

/* Si fat_contar_wav() > 0 usa las canciones de la SD; si no, total_canciones ficticias + tono. */
void player_iniciar(uint32_t total_canciones);
void player_eventos(uint32_t eventos);            /* bits KEY_* de keys.h */

/* Siguiente muestra a 44.1 kHz de la cancion actual. 0 = no hay muestra (mandar silencio).
 * Al terminar una cancion pasa sola a la siguiente. */
int player_muestra(int16_t *izq, int16_t *der);
void player_muestra_enviada(void);                /* llamar por cada muestra reproducida */

player_estado_t player_estado(void);
const char *player_estado_nombre(player_estado_t e);
uint32_t player_cancion(void);                    /* 0 .. total-1 */
uint32_t player_total(void);
uint32_t player_segundos(void);                   /* tiempo transcurrido de la cancion */
uint32_t player_cambios(void);                    /* cuenta cambios de estado o cancion */

int player_usa_sd(void);                          /* 0 = tono de prueba */
const wav_info_t *player_wav(void);               /* formato y metadatos (0 si no hay) */
const char *player_titulo(void);                  /* titulo, o nombre del archivo */
int player_error(void);                           /* ultimo error al abrir (0 = ninguno) */

/* Diagnostico */
uint32_t player_errores_lectura(void);            /* lecturas de la SD que fallaron */
int player_ultimo_error_lectura(void);            /* codigo del ultimo fallo (fat_error) */
const uint8_t *player_primeros(void);             /* primeros 16 bytes de "data" leidos */

#endif
