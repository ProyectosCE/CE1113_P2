#include "player.h"
#include "keys.h"
#include "hw.h"

static player_estado_t estado;
static uint32_t cancion, total, muestras, segundos, cambios;

static void cambiar_cancion(uint32_t nueva)
{
    cancion = nueva;
    muestras = 0;
    segundos = 0;
    ++cambios;
    /* TODO: cerrar el WAV actual y abrir el nuevo (fat_abrir_wav + wav_abrir), < 2 s */
}

void player_iniciar(uint32_t total_canciones)
{
    total = total_canciones ? total_canciones : 1;
    estado = PLAYER_DETENIDO;
    cambiar_cancion(0);
}

void player_eventos(uint32_t eventos)
{
    if (eventos & KEY_PLAY_PAUSA) {
        estado = (estado == PLAYER_REPRODUCIENDO) ? PLAYER_PAUSADO : PLAYER_REPRODUCIENDO;
        ++cambios;
    }
    if (eventos & KEY_STOP) {
        estado = PLAYER_DETENIDO;
        cambiar_cancion(cancion);   /* vuelve al inicio */
    }
    if (eventos & KEY_ANTERIOR)
        cambiar_cancion(cancion == 0 ? total - 1 : cancion - 1);
    if (eventos & KEY_SIGUIENTE)
        cambiar_cancion((cancion + 1) % total);
}

void player_muestra_enviada(void)
{
    if (++muestras == AUDIO_FS) {
        muestras = 0;
        ++segundos;
        /* TODO: al llegar a la duracion del WAV, pasar a la siguiente (reproduccion continua) */
    }
}

player_estado_t player_estado(void)   { return estado; }
uint32_t player_cancion(void)         { return cancion; }
uint32_t player_total(void)           { return total; }
uint32_t player_segundos(void)        { return segundos; }
uint32_t player_cambios(void)         { return cambios; }

const char *player_estado_nombre(player_estado_t e)
{
    switch (e) {
    case PLAYER_DETENIDO:      return "detenido";
    case PLAYER_REPRODUCIENDO: return "reproduciendo";
    case PLAYER_PAUSADO:       return "pausado";
    }
    return "?";
}
