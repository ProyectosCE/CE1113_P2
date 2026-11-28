/*
 * vga_texto_0: pantalla VGA de texto de 80 x 30 caracteres con 16 colores.
 *
 * Se guarda una copia de la pantalla en memoria y solo se escriben al hardware las celdas que
 * cambian, asi que se puede redibujar una linea completa sin costo.
 *
 * Los textos pueden venir en UTF-8 o Latin-1 (metadatos de los WAV): se muestran las letras del
 * espanol (a e i o u con tilde, n con virgulilla, u con dieresis, signos de apertura); las demas
 * letras acentuadas se muestran sin acento.
 */
#ifndef VGA_H
#define VGA_H

#include <stdint.h>

#define VGA_COLUMNAS    80
#define VGA_FILAS       30

enum {
    VGA_NEGRO, VGA_AZUL, VGA_VERDE, VGA_CIAN, VGA_ROJO, VGA_MAGENTA, VGA_CAFE, VGA_GRIS,
    VGA_GRIS_OSCURO, VGA_AZUL_CLARO, VGA_VERDE_CLARO, VGA_CIAN_CLARO, VGA_ROJO_CLARO,
    VGA_MAGENTA_CLARO, VGA_AMARILLO, VGA_BLANCO,
};
#define VGA_COLOR(letra, fondo)   ((uint8_t)(((fondo) << 4) | (letra)))

/* Simbolos propios de la fuente (vga_fuente.sv) */
#define VGA_SIM_LLENO   0x01u
#define VGA_SIM_PLAY    0x02u
#define VGA_SIM_PAUSA   0x03u
#define VGA_SIM_STOP    0x04u
#define VGA_SIM_VACIO   0x05u
#define VGA_SIM_LINEA   0x06u
#define VGA_SIM_NOTA    0x07u
#define VGA_SIM_FLECHA  0x08u

/* 0 si el hardware responde (lee el ID). Deja la pantalla en negro. */
int vga_iniciar(void);
int vga_presente(void);

void vga_limpiar(uint8_t color);
void vga_celda(int col, int fila, uint8_t codigo, uint8_t color);
void vga_repetir(int col, int fila, int n, uint8_t codigo, uint8_t color);

/* Escribe texto desde (col, fila). Si ancho > 0, rellena con espacios o corta a ese ancho.
 * Devuelve las columnas escritas. */
int vga_texto(int col, int fila, const char *s, uint8_t color, int ancho);

#endif
