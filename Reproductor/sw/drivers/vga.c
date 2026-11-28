#include "vga.h"
#include "hw.h"

#define VGA_CELDAS      (VGA_COLUMNAS * VGA_FILAS)
#define VGA_REG_CTRL    0xFFFu                  /* palabra de control / ID */
#define VGA_ID          0x5647u

static uint16_t sombra[VGA_CELDAS];             /* copia de lo que tiene el hardware */
static int presente;

int vga_iniciar(void)
{
    presente = (REG32(VGA_BASE + 4u * VGA_REG_CTRL) >> 16) == VGA_ID;
    if (!presente)
        return -1;
    for (int i = 0; i < VGA_CELDAS; ++i)
        sombra[i] = 0xFFFFu;                    /* forzar la primera escritura */
    vga_limpiar(VGA_COLOR(VGA_BLANCO, VGA_NEGRO));
    REG32(VGA_BASE + 4u * VGA_REG_CTRL) = 1u;   /* video encendido */
    return 0;
}

int vga_presente(void)
{
    return presente;
}

void vga_celda(int col, int fila, uint8_t codigo, uint8_t color)
{
    if (!presente || col < 0 || col >= VGA_COLUMNAS || fila < 0 || fila >= VGA_FILAS)
        return;
    int i = fila * VGA_COLUMNAS + col;
    uint16_t v = (uint16_t)((color << 8) | codigo);
    if (sombra[i] != v) {
        sombra[i] = v;
        REG32(VGA_BASE + 4u * (uint32_t)i) = v;
    }
}

void vga_repetir(int col, int fila, int n, uint8_t codigo, uint8_t color)
{
    for (int k = 0; k < n; ++k)
        vga_celda(col + k, fila, codigo, color);
}

void vga_limpiar(uint8_t color)
{
    for (int f = 0; f < VGA_FILAS; ++f)
        vga_repetir(0, f, VGA_COLUMNAS, ' ', color);
}

/* ---------------- Texto: UTF-8 / Latin-1 -> fuente ---------------- */

/* Letras de Latin-1 que tienen dibujo propio en la fuente */
static int tiene_dibujo(uint32_t c)
{
    switch (c) {
    case 0xA1: case 0xBF:                                   /* signos de apertura */
    case 0xC1: case 0xC9: case 0xCD: case 0xD3: case 0xDA:  /* A E I O U con tilde */
    case 0xE1: case 0xE9: case 0xED: case 0xF3: case 0xFA:  /* a e i o u con tilde */
    case 0xD1: case 0xF1: case 0xDC: case 0xFC:             /* N n con virgulilla, U u dieresis */
        return 1;
    }
    return 0;
}

/* Las demas letras de Latin-1 (0xC0-0xFF) sin acento */
static const char sin_acento[64] =
    "AAAAAAACEEEEIIIIDNOOOOOxOUUUUYPs"
    "aaaaaaaceeeeiiiidnooooo/ouuuuypy";

static uint8_t a_fuente(uint32_t c)
{
    if (c >= 0x20u && c < 0x7Fu)
        return (uint8_t)c;
    if (c < 0x20u)
        return ' ';
    if (tiene_dibujo(c))
        return (uint8_t)c;
    if (c >= 0xC0u && c <= 0xFFu)
        return (uint8_t)sin_acento[c - 0xC0u];
    return '?';
}

/* Siguiente caracter de s (UTF-8 si es valido; si no, Latin-1). Avanza *s. */
static uint32_t siguiente(const uint8_t **s)
{
    const uint8_t *p = *s;
    uint32_t c = p[0];
    if (c < 0x80u) {
        *s = p + 1;
        return c;
    }
    int n = (c & 0xE0u) == 0xC0u ? 1 : (c & 0xF0u) == 0xE0u ? 2 : (c & 0xF8u) == 0xF0u ? 3 : 0;
    for (int k = 1; k <= n; ++k) {
        if ((p[k] & 0xC0u) != 0x80u) {
            n = 0;                                  /* no es UTF-8: tomar el byte como Latin-1 */
            break;
        }
    }
    if (n == 0) {
        *s = p + 1;
        return c;
    }
    *s = p + 1 + n;
    if (n == 1)
        return ((c & 0x1Fu) << 6) | (p[1] & 0x3Fu);
    return 0xFFFFu;                                 /* fuera de Latin-1 */
}

int vga_texto(int col, int fila, const char *s, uint8_t color, int ancho)
{
    const uint8_t *p = (const uint8_t *)s;
    int k = 0;
    while (*p && (ancho <= 0 || k < ancho) && col + k < VGA_COLUMNAS) {
        vga_celda(col + k, fila, a_fuente(siguiente(&p)), color);
        ++k;
    }
    int escritas = k;
    while (ancho > 0 && k < ancho)
        vga_celda(col + k++, fila, ' ', color);
    return escritas;
}
