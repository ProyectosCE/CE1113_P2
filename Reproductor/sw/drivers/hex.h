/* hex_ctrl_0 (hardware propio): MM:SS en HEX3-0 y numero de cancion en HEX5-4. */
#ifndef HEX_H
#define HEX_H

#include <stdbool.h>
#include <stdint.h>

void hex_encender(bool tiempo, bool cancion);
void hex_tiempo(uint32_t segundos);   /* se muestra como MM:SS (minutos hasta 99) */
void hex_cancion(uint32_t numero);    /* 0..99 */
uint32_t hex_id(void);                /* 0x4E58 si el modulo responde */

#endif
