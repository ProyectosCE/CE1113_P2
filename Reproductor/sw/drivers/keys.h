/* KEY[3:0] (PIO keys) por interrupcion: cada pulsacion queda como evento pendiente. */
#ifndef KEYS_H
#define KEYS_H

#include <stdint.h>

/* Bits de evento (uno por boton) */
#define KEY_PLAY_PAUSA  (1u << 0)   /* KEY0 */
#define KEY_STOP        (1u << 1)   /* KEY1 */
#define KEY_ANTERIOR    (1u << 2)   /* KEY2 */
#define KEY_SIGUIENTE   (1u << 3)   /* KEY3 */

/* Configura el PIO y registra la interrupcion en el GIC (llamar despues de gic_iniciar). */
void keys_iniciar(void);

/* Devuelve los botones pulsados desde la ultima llamada y los borra. */
uint32_t keys_eventos(void);

#endif
