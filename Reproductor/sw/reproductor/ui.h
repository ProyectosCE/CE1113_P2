/* Interfaz de usuario: 7 segmentos, LEDs, consola y pantalla VGA (pantalla.c). */
#ifndef UI_H
#define UI_H

void ui_iniciar(void);
void ui_actualizar(void);   /* llamar periodicamente desde el lazo principal */

#endif
