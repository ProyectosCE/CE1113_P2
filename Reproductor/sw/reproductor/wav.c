/*
 * Parser WAV (RIFF): recorre los chunks del archivo.
 *   "fmt "  -> formato (PCM, canales, frecuencia, bits)
 *   "LIST"  -> tipo "INFO": INAM (titulo), IART (artista), IPRD (album)
 *   "data"  -> audio
 * El chunk LIST puede estar antes o despues de "data"; si esta despues, se busca y se vuelve.
 */
#include "wav.h"

static uint32_t le32(const uint8_t *p)
{
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}
static uint16_t le16(const uint8_t *p) { return (uint16_t)(p[0] | (p[1] << 8)); }

static int igual4(const uint8_t *p, const char *s)
{
    return p[0] == (uint8_t)s[0] && p[1] == (uint8_t)s[1] &&
           p[2] == (uint8_t)s[2] && p[3] == (uint8_t)s[3];
}

static int leer_exacto(fat_archivo_t *a, void *dst, uint32_t n)
{
    return fat_leer(a, dst, n) == (int)n ? 0 : -1;
}

/* Copia un texto del chunk INFO (puede no terminar en 0) */
static int leer_texto(fat_archivo_t *a, char *dst, uint32_t tam)
{
    uint8_t c;
    uint32_t k = 0;
    for (uint32_t i = 0; i < tam; ++i) {
        if (leer_exacto(a, &c, 1) != 0)
            return -1;
        if (c == 0)
            continue;
        if (k < WAV_TEXTO_MAX - 1)
            dst[k++] = (c >= 32 && c < 127) ? (char)c : '?';
    }
    while (k > 0 && dst[k - 1] == ' ')
        --k;
    dst[k] = '\0';
    return 0;
}

static int leer_info(fat_archivo_t *a, uint32_t tam, wav_info_t *in)
{
    uint32_t fin = a->posicion + tam;
    uint8_t h[8];
    while (a->posicion + 8 <= fin) {
        if (leer_exacto(a, h, 8) != 0)
            return -1;
        uint32_t t = le32(h + 4);
        uint32_t siguiente = a->posicion + t + (t & 1u);
        if (igual4(h, "INAM"))
            leer_texto(a, in->titulo, t);
        else if (igual4(h, "IART"))
            leer_texto(a, in->artista, t);
        else if (igual4(h, "IPRD"))
            leer_texto(a, in->album, t);
        if (fat_buscar(a, siguiente) != 0)
            return -1;
    }
    return 0;
}

const char *wav_error(int codigo)
{
    switch (codigo) {
    case WAV_OK:          return "ok";
    case WAV_E_LECTURA:   return "error leyendo el archivo";
    case WAV_E_NO_WAV:    return "no es un archivo WAV";
    case WAV_E_FORMATO:   return "formato no soportado (debe ser PCM de 16 bits, mono o estereo)";
    case WAV_E_SIN_DATOS: return "WAV incompleto (falta fmt o data)";
    }
    return "error desconocido";
}

int wav_abrir(fat_archivo_t *a, wav_info_t *in)
{
    uint8_t h[40];
    int fmt_visto = 0, data_visto = 0, info_vista = 0;

    in->frecuencia = 0;
    in->canales = 0;
    in->bits = 0;
    in->inicio_datos = 0;
    in->bytes_datos = 0;
    in->duracion_s = 0;
    in->titulo[0] = in->artista[0] = in->album[0] = '\0';

    if (fat_buscar(a, 0) != 0 || leer_exacto(a, h, 12) != 0)
        return WAV_E_LECTURA;
    if (!igual4(h, "RIFF") || !igual4(h + 8, "WAVE"))
        return WAV_E_NO_WAV;

    while (a->posicion + 8 <= a->tamano) {
        if (leer_exacto(a, h, 8) != 0)
            return WAV_E_LECTURA;
        uint32_t tam = le32(h + 4);
        uint32_t inicio = a->posicion;
        uint32_t siguiente = inicio + tam + (tam & 1u);

        if (igual4(h, "fmt ")) {
            uint32_t n = tam < sizeof h ? tam : sizeof h;
            if (n < 16 || leer_exacto(a, h, n) != 0)
                return WAV_E_FORMATO;
            uint16_t formato = le16(h);
            in->canales = le16(h + 2);
            in->frecuencia = le32(h + 4);
            in->bits = le16(h + 14);
            if (formato == 0xFFFE && n >= 26)       /* WAVE_FORMAT_EXTENSIBLE */
                formato = le16(h + 24);
            if (formato != 1 || in->bits != 16 || in->canales < 1 || in->canales > 2 ||
                in->frecuencia < 4000 || in->frecuencia > 48000)
                return WAV_E_FORMATO;
            fmt_visto = 1;
        } else if (igual4(h, "LIST") && tam >= 4) {
            uint8_t tipo[4];
            if (leer_exacto(a, tipo, 4) != 0)
                return WAV_E_LECTURA;
            if (igual4(tipo, "INFO")) {
                leer_info(a, tam - 4, in);
                info_vista = 1;
            }
        } else if (igual4(h, "data")) {
            in->inicio_datos = inicio;
            in->bytes_datos = tam;
            if (in->bytes_datos > a->tamano - inicio)  /* archivo truncado */
                in->bytes_datos = a->tamano - inicio;
            data_visto = 1;
            if (info_vista)
                break;
        }
        if (siguiente >= a->tamano)
            break;
        if (fat_buscar(a, siguiente) != 0)
            return WAV_E_LECTURA;
    }

    if (!fmt_visto || !data_visto)
        return WAV_E_SIN_DATOS;

    in->duracion_s = in->bytes_datos / (in->frecuencia * in->canales * 2u);
    if (fat_buscar(a, in->inicio_datos) != 0)
        return WAV_E_LECTURA;
    return WAV_OK;
}
