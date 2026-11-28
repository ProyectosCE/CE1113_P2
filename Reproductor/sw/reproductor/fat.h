/*
 * Lectura de FAT32 en la microSD (sobre sdmmc.c), solo lectura.
 * Busca los archivos .wav del directorio raiz y permite leerlos de forma secuencial.
 */
#ifndef FAT_H
#define FAT_H

#include <stdint.h>

#define FAT_MAX_CANCIONES   32
#define FAT_NOMBRE_MAX      48

/* Codigos de retorno (0 = ok) */
#define FAT_OK              0
#define FAT_E_SD            (-10)   /* error de lectura de la tarjeta */
#define FAT_E_NO_FAT32      (-11)   /* no hay particion FAT32 (exFAT, NTFS, FAT16...) */
#define FAT_E_FORMATO       (-12)   /* sector de arranque invalido */
#define FAT_E_INDICE        (-13)   /* no existe esa cancion */
#define FAT_E_NO_MONTADA    (-14)

typedef struct {
    uint32_t primer_cluster;
    uint32_t tamano;            /* bytes */
    uint32_t posicion;          /* bytes leidos (posicion actual) */
    uint32_t cluster_actual;    /* cluster que contiene "posicion" */
    uint32_t cluster_indice;    /* numero de cluster dentro del archivo */
} fat_archivo_t;

typedef struct {
    uint32_t inicio_particion;  /* LBA */
    uint32_t sectores_cluster;
    uint32_t inicio_fat;        /* LBA */
    uint32_t inicio_datos;      /* LBA del cluster 2 */
    uint32_t cluster_raiz;
    char     etiqueta[12];
} fat_volumen_t;

int fat_montar(void);                                   /* lee la tarjeta y busca los .wav */
const fat_volumen_t *fat_volumen(void);
int fat_contar_wav(void);
const char *fat_nombre_wav(int indice);                 /* nombre largo si existe, si no 8.3 */
uint32_t fat_tamano_wav(int indice);
int fat_abrir_wav(int indice, fat_archivo_t *archivo);  /* 0 = ok */
int fat_leer(fat_archivo_t *archivo, void *destino, uint32_t bytes);   /* bytes leidos, <0 error */
int fat_buscar(fat_archivo_t *archivo, uint32_t posicion);            /* 0 = ok */
const char *fat_error(int codigo);

#endif
