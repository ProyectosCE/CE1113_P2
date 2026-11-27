/* Sistema de archivos FAT32 de la microSD (sobre sdmmc.c): lista y lee los archivos .wav. */
#ifndef FAT_H
#define FAT_H

#include <stdint.h>

#define FAT_MAX_CANCIONES   32u

typedef struct {
    uint32_t primer_cluster;
    uint32_t tamano;            /* bytes */
    uint32_t posicion;          /* bytes leidos */
    uint32_t cluster_actual;
} fat_archivo_t;

int fat_montar(void);                                      /* 0 = ok */
int fat_contar_wav(void);                                  /* numero de .wav en la raiz */
int fat_nombre_wav(int indice, char *nombre, int max);     /* nombre del .wav numero indice */
int fat_abrir_wav(int indice, fat_archivo_t *archivo);     /* 0 = ok */
int fat_leer(fat_archivo_t *archivo, void *destino, uint32_t bytes);   /* bytes leidos, <0 error */

#endif
