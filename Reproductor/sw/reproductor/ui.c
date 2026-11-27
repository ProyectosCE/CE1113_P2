#include "ui.h"
#include "filtros.h"
#include "hex.h"
#include "jtag_uart.h"
#include "leds.h"
#include "player.h"
#include "volumen.h"

/*
 * LEDR[1:0] = filtro activo, LEDR8 = reproduciendo, LEDR9 = pausado.
 * HEX3-0 = MM:SS, HEX5-4 = numero de cancion (1..N).
 * Consola: una linea en cada cambio de estado, cancion, filtro o volumen (pasos de 10 %).
 */

static uint32_t cambios_vistos = 0xFFFFFFFFu;
static filtro_t filtro_visto = (filtro_t)-1;
static uint32_t volumen_visto = 0xFFFFFFFFu;

void ui_iniciar(void)
{
    hex_encender(true, true);
}

void ui_actualizar(void)
{
    player_estado_t e = player_estado();
    filtro_t f = filtros_actual();
    uint32_t vol = volumen_porcentaje() / 10u * 10u;

    hex_tiempo(player_segundos());
    hex_cancion(player_cancion() + 1u);
    leds_escribir((uint32_t)f
                  | (e == PLAYER_REPRODUCIENDO ? 1u << 8 : 0u)
                  | (e == PLAYER_PAUSADO ? 1u << 9 : 0u));

    if (player_cambios() != cambios_vistos || f != filtro_visto || vol != volumen_visto) {
        cambios_vistos = player_cambios();
        filtro_visto = f;
        volumen_visto = vol;
        uart_puts("cancion ");
        uart_putu(player_cancion() + 1u);
        uart_puts("/");
        uart_putu(player_total());
        uart_puts("  ");
        uart_puts(player_estado_nombre(e));
        uart_puts("  filtro: ");
        uart_puts(filtros_nombre(f));
        uart_puts("  volumen: ");
        uart_putu(vol);
        uart_puts(" %\r\n");
    }
    /* TODO: metadatos (titulo, artista, album, duracion) en pantalla externa */
}
