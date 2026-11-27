#include "fat.h"
#include "sdmmc.h"

/*
 * PENDIENTE: leer el MBR y el sector de arranque de la particion FAT32, recorrer el directorio
 * raiz buscando entradas *.WAV y seguir la cadena de clusters en la FAT para leer cada archivo.
 */

int fat_montar(void)
{
    return -1;   /* TODO */
}

int fat_contar_wav(void)
{
    return 0;    /* TODO */
}

int fat_nombre_wav(int indice, char *nombre, int max)
{
    (void)indice;
    if (max > 0)
        nombre[0] = '\0';
    return -1;   /* TODO */
}

int fat_abrir_wav(int indice, fat_archivo_t *archivo)
{
    (void)indice;
    (void)archivo;
    return -1;   /* TODO */
}

int fat_leer(fat_archivo_t *archivo, void *destino, uint32_t bytes)
{
    (void)archivo;
    (void)destino;
    (void)bytes;
    return -1;   /* TODO */
}
