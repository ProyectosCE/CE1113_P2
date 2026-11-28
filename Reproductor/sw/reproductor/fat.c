/*
 * FAT32 de solo lectura.
 *
 *   sector 0 (MBR) -> particion FAT32 -> sector de arranque (BPB) -> FAT y directorio raiz
 *
 * Se aceptan tarjetas con tabla de particiones (lo normal) o formateadas sin ella. Del
 * directorio raiz se guardan los archivos *.WAV (con su nombre largo si lo tienen); se ignoran
 * carpetas (por ejemplo "System Volume Information"), archivos ocultos y los "._*" de macOS.
 *
 * Memoria: un sector de datos y un sector de la FAT en cache (1 KB en total).
 */
#include "fat.h"
#include "sdmmc.h"

#define FIN_CADENA      0x0FFFFFF8u

typedef struct {
    char     nombre[FAT_NOMBRE_MAX];
    uint32_t primer_cluster;
    uint32_t tamano;
} entrada_t;

static fat_volumen_t vol;
static int montada;
static entrada_t canciones[FAT_MAX_CANCIONES];
static int total;

static uint8_t cache_datos[SDMMC_BLOQUE];
static uint32_t cache_datos_lba = 0xFFFFFFFFu;
static uint8_t cache_fat[SDMMC_BLOQUE];
static uint32_t cache_fat_lba = 0xFFFFFFFFu;

/* ---------------- Utilidades ---------------- */

static uint16_t le16(const uint8_t *p) { return (uint16_t)(p[0] | (p[1] << 8)); }
static uint32_t le32(const uint8_t *p)
{
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

static int leer_sector(uint32_t lba, uint8_t *buf, uint32_t *cache_lba)
{
    if (*cache_lba == lba)
        return FAT_OK;
    if (sdmmc_leer(lba, 1, buf) != 0) {
        *cache_lba = 0xFFFFFFFFu;
        return FAT_E_SD;
    }
    *cache_lba = lba;
    return FAT_OK;
}

static uint32_t bytes_cluster(void)
{
    return vol.sectores_cluster * SDMMC_BLOQUE;
}

static uint32_t lba_cluster(uint32_t cluster)
{
    return vol.inicio_datos + (cluster - 2u) * vol.sectores_cluster;
}

/* Siguiente cluster de la cadena; >= FIN_CADENA al final. 0 si hubo error de lectura. */
static uint32_t siguiente_cluster(uint32_t cluster)
{
    uint32_t desplazamiento = cluster * 4u;
    uint32_t lba = vol.inicio_fat + desplazamiento / SDMMC_BLOQUE;
    if (leer_sector(lba, cache_fat, &cache_fat_lba) != FAT_OK)
        return 0;
    return le32(cache_fat + desplazamiento % SDMMC_BLOQUE) & 0x0FFFFFFFu;
}

static int es_sector_arranque_fat32(const uint8_t *s)
{
    return s[510] == 0x55 && s[511] == 0xAA &&
           s[82] == 'F' && s[83] == 'A' && s[84] == 'T' && s[85] == '3' && s[86] == '2';
}

static char a_mayuscula(char c)
{
    return (c >= 'a' && c <= 'z') ? (char)(c - 'a' + 'A') : c;
}

/* ---------------- Directorio raiz ---------------- */

/* Acumula un nombre largo (LFN): 13 caracteres UTF-16 por entrada; se guarda solo ASCII. */
static void lfn_agregar(char *lfn, const uint8_t *e)
{
    static const uint8_t pos[13] = { 1, 3, 5, 7, 9, 14, 16, 18, 20, 22, 24, 28, 30 };
    int orden = (e[0] & 0x1F) - 1;
    for (int i = 0; i < 13; ++i) {
        int k = orden * 13 + i;
        if (k >= FAT_NOMBRE_MAX - 1)
            break;
        uint16_t c = le16(e + pos[i]);
        if (c == 0x0000 || c == 0xFFFF) {
            lfn[k] = '\0';
            break;
        }
        lfn[k] = (c < 128) ? (char)c : '?';
    }
    if ((e[0] & 0x40) && (orden + 1) * 13 < FAT_NOMBRE_MAX)
        lfn[(orden + 1) * 13] = '\0';       /* la ultima entrada LFN marca el fin */
}

/* Nombre corto 8.3 -> "NOMBRE.EXT" */
static void nombre_corto(char *dst, const uint8_t *e)
{
    int k = 0;
    for (int i = 0; i < 8 && e[i] != ' '; ++i)
        dst[k++] = (char)e[i];
    dst[k++] = '.';
    for (int i = 8; i < 11 && e[i] != ' '; ++i)
        dst[k++] = (char)e[i];
    dst[k] = '\0';
}

static void agregar_si_es_wav(const uint8_t *e, const char *lfn)
{
    uint8_t atributos = e[11];
    if (atributos & (0x02 | 0x08 | 0x10))   /* oculto, etiqueta de volumen, carpeta */
        return;
    if (!(a_mayuscula((char)e[8]) == 'W' && a_mayuscula((char)e[9]) == 'A' &&
          a_mayuscula((char)e[10]) == 'V'))
        return;
    if (lfn[0] == '.' && lfn[1] == '_')     /* "._cancion.wav" de macOS */
        return;
    if (total >= FAT_MAX_CANCIONES)
        return;

    entrada_t *c = &canciones[total];
    if (lfn[0]) {
        int i = 0;
        for (; lfn[i] && i < FAT_NOMBRE_MAX - 1; ++i)
            c->nombre[i] = lfn[i];
        c->nombre[i] = '\0';
    } else {
        nombre_corto(c->nombre, e);
    }
    c->primer_cluster = ((uint32_t)le16(e + 20) << 16) | le16(e + 26);
    c->tamano = le32(e + 28);
    if (c->primer_cluster >= 2 && c->tamano > 0)
        ++total;
}

static int recorrer_raiz(void)
{
    char lfn[FAT_NOMBRE_MAX];
    lfn[0] = '\0';
    total = 0;

    uint32_t cluster = vol.cluster_raiz;
    for (int vueltas = 0; cluster >= 2 && cluster < FIN_CADENA && vueltas < 4096; ++vueltas) {
        for (uint32_t s = 0; s < vol.sectores_cluster; ++s) {
            if (leer_sector(lba_cluster(cluster) + s, cache_datos, &cache_datos_lba) != FAT_OK)
                return FAT_E_SD;
            for (uint32_t off = 0; off < SDMMC_BLOQUE; off += 32) {
                const uint8_t *e = cache_datos + off;
                if (e[0] == 0x00)
                    return FAT_OK;                  /* fin del directorio */
                if (e[0] == 0xE5) {                 /* entrada borrada */
                    lfn[0] = '\0';
                    continue;
                }
                if (e[11] == 0x0F) {                /* parte de un nombre largo */
                    if (e[0] & 0x40) {              /* primera entrada leida = ultima parte */
                        for (int i = 0; i < FAT_NOMBRE_MAX; ++i)
                            lfn[i] = '\0';
                    }
                    lfn_agregar(lfn, e);
                    continue;
                }
                agregar_si_es_wav(e, lfn);
                lfn[0] = '\0';
            }
        }
        cluster = siguiente_cluster(cluster);
    }
    return FAT_OK;
}

/* ---------------- API ---------------- */

const char *fat_error(int codigo)
{
    switch (codigo) {
    case FAT_OK:            return "ok";
    case FAT_E_SD:          return "error de lectura de la SD";
    case FAT_E_NO_FAT32:    return "no hay particion FAT32 (formatear la tarjeta en FAT32)";
    case FAT_E_FORMATO:     return "sector de arranque FAT32 invalido";
    case FAT_E_INDICE:      return "no existe esa cancion";
    case FAT_E_NO_MONTADA:  return "la tarjeta no esta montada";
    }
    return "error desconocido";
}

int fat_montar(void)
{
    montada = 0;
    total = 0;
    cache_datos_lba = cache_fat_lba = 0xFFFFFFFFu;

    if (leer_sector(0, cache_datos, &cache_datos_lba) != FAT_OK)
        return FAT_E_SD;

    /* Tarjeta con tabla de particiones (MBR) o formateada sin ella */
    vol.inicio_particion = 0;
    if (!es_sector_arranque_fat32(cache_datos)) {
        if (cache_datos[510] != 0x55 || cache_datos[511] != 0xAA)
            return FAT_E_NO_FAT32;
        for (int i = 0; i < 4; ++i) {
            const uint8_t *p = cache_datos + 446 + 16 * i;
            if (p[4] == 0x0B || p[4] == 0x0C) {
                vol.inicio_particion = le32(p + 8);
                break;
            }
        }
        if (vol.inicio_particion == 0)
            return FAT_E_NO_FAT32;
        if (leer_sector(vol.inicio_particion, cache_datos, &cache_datos_lba) != FAT_OK)
            return FAT_E_SD;
        if (!es_sector_arranque_fat32(cache_datos))
            return FAT_E_NO_FAT32;
    }

    /* Sector de arranque (BPB) */
    const uint8_t *b = cache_datos;
    if (le16(b + 11) != SDMMC_BLOQUE || b[13] == 0 || b[16] == 0)
        return FAT_E_FORMATO;
    vol.sectores_cluster = b[13];
    vol.inicio_fat = vol.inicio_particion + le16(b + 14);
    vol.inicio_datos = vol.inicio_fat + (uint32_t)b[16] * le32(b + 36);
    vol.cluster_raiz = le32(b + 44);
    for (int i = 0; i < 11; ++i)
        vol.etiqueta[i] = (char)b[71 + i];
    vol.etiqueta[11] = '\0';

    int r = recorrer_raiz();
    if (r != FAT_OK)
        return r;
    montada = 1;
    return FAT_OK;
}

const fat_volumen_t *fat_volumen(void)
{
    return &vol;
}

int fat_contar_wav(void)
{
    return montada ? total : 0;
}

const char *fat_nombre_wav(int indice)
{
    return (montada && indice >= 0 && indice < total) ? canciones[indice].nombre : "";
}

uint32_t fat_tamano_wav(int indice)
{
    return (montada && indice >= 0 && indice < total) ? canciones[indice].tamano : 0;
}

int fat_abrir_wav(int indice, fat_archivo_t *a)
{
    if (!montada)
        return FAT_E_NO_MONTADA;
    if (indice < 0 || indice >= total)
        return FAT_E_INDICE;
    a->primer_cluster = canciones[indice].primer_cluster;
    a->tamano = canciones[indice].tamano;
    a->posicion = 0;
    a->cluster_actual = a->primer_cluster;
    a->cluster_indice = 0;
    return FAT_OK;
}

int fat_buscar(fat_archivo_t *a, uint32_t posicion)
{
    if (posicion > a->tamano)
        posicion = a->tamano;
    uint32_t indice = posicion / bytes_cluster();
    if (indice < a->cluster_indice) {               /* hacia atras: desde el inicio */
        a->cluster_actual = a->primer_cluster;
        a->cluster_indice = 0;
    }
    while (a->cluster_indice < indice) {
        uint32_t c = siguiente_cluster(a->cluster_actual);
        if (c < 2 || c >= FIN_CADENA)
            return FAT_E_SD;
        a->cluster_actual = c;
        ++a->cluster_indice;
    }
    a->posicion = posicion;
    return FAT_OK;
}

int fat_leer(fat_archivo_t *a, void *destino, uint32_t bytes)
{
    uint8_t *d = destino;
    uint32_t leidos = 0;

    while (bytes > 0 && a->posicion < a->tamano) {
        /* Avanzar de cluster si la posicion paso al siguiente */
        if (fat_buscar(a, a->posicion) != FAT_OK)
            return FAT_E_SD;

        uint32_t en_cluster = a->posicion % bytes_cluster();
        uint32_t lba = lba_cluster(a->cluster_actual) + en_cluster / SDMMC_BLOQUE;
        if (leer_sector(lba, cache_datos, &cache_datos_lba) != FAT_OK)
            return FAT_E_SD;

        uint32_t en_sector = a->posicion % SDMMC_BLOQUE;
        uint32_t n = SDMMC_BLOQUE - en_sector;
        if (n > bytes)
            n = bytes;
        if (n > a->tamano - a->posicion)
            n = a->tamano - a->posicion;
        for (uint32_t i = 0; i < n; ++i)
            d[i] = cache_datos[en_sector + i];

        d += n;
        bytes -= n;
        leidos += n;
        a->posicion += n;
    }
    return (int)leidos;
}
