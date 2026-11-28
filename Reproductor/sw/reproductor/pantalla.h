/*
 * Pantalla VGA del reproductor (vga_texto, 80 x 30): metadatos de la cancion, numero de cancion
 * y total, estado, tiempo con barra de avance, volumen, filtro activo y lista de canciones.
 */
#ifndef PANTALLA_H
#define PANTALLA_H

int pantalla_iniciar(void);     /* 0 = hay VGA; si no, las demas funciones no hacen nada */
void pantalla_actualizar(void); /* llamar seguido: solo redibuja lo que cambio */

#endif
