/* Logica de reproduccion: estados, botones, cancion actual y tiempo transcurrido. */
#ifndef PLAYER_H
#define PLAYER_H

#include <stdint.h>

typedef enum {
    PLAYER_DETENIDO,
    PLAYER_REPRODUCIENDO,
    PLAYER_PAUSADO,
} player_estado_t;

void player_iniciar(uint32_t total_canciones);
void player_eventos(uint32_t eventos);            /* bits KEY_* de keys.h */
void player_muestra_enviada(void);                /* llamar por cada muestra reproducida */

player_estado_t player_estado(void);
const char *player_estado_nombre(player_estado_t e);
uint32_t player_cancion(void);                    /* 0 .. total-1 */
uint32_t player_total(void);
uint32_t player_segundos(void);                   /* tiempo transcurrido de la cancion */
uint32_t player_cambios(void);                    /* cuenta cambios de estado o cancion */

#endif
