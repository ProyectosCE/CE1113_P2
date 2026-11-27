#include "wav.h"

/*
 * PENDIENTE: validar "RIFF"/"WAVE", leer el chunk "fmt " (PCM = 1, 16 bits, 8/16/44.1 kHz),
 * recorrer los chunks buscando "LIST"/"INFO" (INAM, IART, IPRD) y "data", y calcular la duracion.
 */

int wav_abrir(fat_archivo_t *archivo, wav_info_t *info)
{
    (void)archivo;
    (void)info;
    return -1;   /* TODO */
}
