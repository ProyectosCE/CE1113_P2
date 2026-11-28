#include "player.h"
#include "audio.h"
#include "fat.h"
#include "hw.h"
#include "keys.h"
#include "remuestreo.h"
#include "tono.h"

static player_estado_t estado;
static uint32_t cancion, total, muestras, segundos, cambios;
static int usa_sd, abierta, error_apertura;

static fat_archivo_t archivo;
static wav_info_t wav;
static remuestreo_t rs;

/* Bloque leido del archivo y posicion dentro de el */
static uint8_t bloque[512];
static uint32_t bloque_len, bloque_pos, restantes;

/* Diagnostico */
static uint32_t errores_lectura;
static int ultimo_error_lectura, primer_bloque;
static uint8_t primeros[16];

/* ---------------- Apertura de canciones ---------------- */

static void abrir(uint32_t indice)
{
    abierta = 0;
    error_apertura = 0;
    bloque_len = bloque_pos = 0;
    if (!usa_sd)
        return;

    int r = fat_abrir_wav((int)indice, &archivo);
    if (r == 0)
        r = wav_abrir(&archivo, &wav);          /* deja el archivo al inicio de "data" */
    if (r != 0) {
        error_apertura = r;
        return;
    }
    restantes = wav.bytes_datos;
    primer_bloque = 1;
    for (int i = 0; i < 16; ++i)
        primeros[i] = 0;
    remuestreo_iniciar(&rs, wav.frecuencia);
    abierta = 1;
}

/* vaciar = 1: descarta lo que queda en la cola de audio (botones); 0: fin de cancion */
static void cambiar(uint32_t nueva, int vaciar)
{
    cancion = nueva;
    muestras = 0;
    segundos = 0;
    ++cambios;
    if (vaciar)
        audio_vaciar();
    abrir(cancion);
}

static void cambiar_cancion(uint32_t nueva)
{
    cambiar(nueva, 1);
}

/* ---------------- Lectura del WAV ---------------- */

static int16_t le16s(const uint8_t *p)
{
    return (int16_t)(uint16_t)(p[0] | (p[1] << 8));
}

/* Una muestra a la frecuencia original del WAV (mono se duplica). 0 = fin del audio. */
static int leer_muestra_wav(int16_t *izq, int16_t *der)
{
    uint32_t tam = wav.canales * 2u;
    if (bloque_pos + tam > bloque_len) {
        uint32_t pedir = restantes < sizeof bloque ? restantes : sizeof bloque;
        pedir -= pedir % tam;
        if (pedir == 0)
            return 0;
        int n = fat_leer(&archivo, bloque, pedir);
        if (n <= 0) {
            ++errores_lectura;
            ultimo_error_lectura = n;
            return 0;
        }
        if (primer_bloque) {
            primer_bloque = 0;
            for (int i = 0; i < 16 && i < n; ++i)
                primeros[i] = bloque[i];
        }
        bloque_len = (uint32_t)n;
        bloque_pos = 0;
        restantes -= (uint32_t)n;
    }
    *izq = le16s(bloque + bloque_pos);
    *der = (wav.canales == 2) ? le16s(bloque + bloque_pos + 2) : *izq;
    bloque_pos += tam;
    return 1;
}

/* Muestra a 44.1 kHz de la cancion abierta. 0 = la cancion termino. */
static int muestra_sd(int16_t *izq, int16_t *der)
{
    while (remuestreo_necesita(&rs)) {
        int16_t a, b;
        if (!leer_muestra_wav(&a, &b))
            return 0;
        remuestreo_entrada(&rs, a, b);
    }
    remuestreo_salida(&rs, izq, der);
    return 1;
}

int player_muestra(int16_t *izq, int16_t *der)
{
    if (!usa_sd) {
        *izq = *der = tono_siguiente();
        return 1;
    }
    if (abierta && muestra_sd(izq, der))
        return 1;

    /* Termino la cancion o no se pudo abrir: pasar a la siguiente sin cortar lo que suena */
    if (abierta || total > 1)
        cambiar((cancion + 1u) % total, 0);
    else
        estado = PLAYER_DETENIDO;               /* unica cancion y no abre */
    return 0;
}

/* ---------------- Estados y botones ---------------- */

void player_iniciar(uint32_t total_canciones)
{
    int n = fat_contar_wav();
    usa_sd = n > 0;
    total = usa_sd ? (uint32_t)n : (total_canciones ? total_canciones : 1u);
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
        cambiar_cancion(cancion);               /* vuelve al inicio */
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
    }
}

player_estado_t player_estado(void)   { return estado; }
uint32_t player_cancion(void)         { return cancion; }
uint32_t player_total(void)           { return total; }
uint32_t player_segundos(void)        { return segundos; }
uint32_t player_cambios(void)         { return cambios; }
int player_usa_sd(void)               { return usa_sd; }
int player_error(void)                { return error_apertura; }
const wav_info_t *player_wav(void)    { return (usa_sd && abierta) ? &wav : 0; }

uint32_t player_errores_lectura(void)     { return errores_lectura; }
int player_ultimo_error_lectura(void)     { return ultimo_error_lectura; }
const uint8_t *player_primeros(void)      { return primeros; }

const char *player_titulo(void)
{
    if (!usa_sd)
        return "Tono de prueba (441 Hz)";
    if (abierta && wav.titulo[0])
        return wav.titulo;
    return fat_nombre_wav((int)cancion);
}

const char *player_estado_nombre(player_estado_t e)
{
    switch (e) {
    case PLAYER_DETENIDO:      return "detenido";
    case PLAYER_REPRODUCIENDO: return "reproduciendo";
    case PLAYER_PAUSADO:       return "pausado";
    }
    return "?";
}
