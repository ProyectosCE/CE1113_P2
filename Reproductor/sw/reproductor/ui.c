#include "ui.h"
#include "audio.h"
#include "fat.h"
#include "filtros.h"
#include "hex.h"
#include "hps.h"
#include "jtag_uart.h"
#include "leds.h"
#include "player.h"
#include "volumen.h"

/*
 * LEDR[1:0] = filtro activo, LEDR8 = reproduciendo, LEDR9 = pausado.
 * HEX3-0 = MM:SS, HEX5-4 = numero de cancion (1..N).
 * Consola: datos de la cancion al cambiar de cancion, y una linea en cada cambio de estado,
 * filtro o volumen (pasos de 10 %).
 */

static uint32_t cambios_vistos = 0xFFFFFFFFu;
static uint32_t cancion_vista = 0xFFFFFFFFu;
static filtro_t filtro_visto = (filtro_t)-1;
static uint32_t volumen_visto = 0xFFFFFFFFu;

static void tiempo(uint32_t s)
{
    uart_putu(s / 60u);
    uart_putc(':');
    uart_putc((char)('0' + (s % 60u) / 10u));
    uart_putc((char)('0' + s % 10u));
}

static void mostrar_cancion(void)
{
    uart_puts("\r\n--- cancion ");
    uart_putu(player_cancion() + 1u);
    uart_puts("/");
    uart_putu(player_total());
    uart_puts(": ");
    uart_puts(player_titulo());
    uart_puts("\r\n");

    const wav_info_t *w = player_wav();
    if (w) {
        if (w->artista[0]) {
            uart_puts("    artista: ");
            uart_puts(w->artista);
            uart_puts("\r\n");
        }
        if (w->album[0]) {
            uart_puts("    album:   ");
            uart_puts(w->album);
            uart_puts("\r\n");
        }
        uart_puts("    duracion: ");
        tiempo(w->duracion_s);
        uart_puts(", ");
        uart_putu(w->frecuencia);
        uart_puts(w->canales == 2 ? " Hz estereo\r\n" : " Hz mono\r\n");
        uart_puts("    data: desde el byte ");
        uart_putu(w->inicio_datos);
        uart_puts(", ");
        uart_putu(w->bytes_datos);
        uart_puts(" bytes\r\n");
    } else if (player_usa_sd() && player_error()) {
        uart_puts("    no se pudo abrir: ");
        uart_puts(wav_error(player_error()));
        uart_puts("\r\n");
    }
}

void ui_iniciar(void)
{
    uart_puts("CPU: ");
    uart_putu(hps_mhz());
    uart_puts(" MHz\r\n");

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

    if (player_cancion() != cancion_vista) {
        cancion_vista = player_cancion();
        mostrar_cancion();
    }

    if (player_cambios() != cambios_vistos || f != filtro_visto || vol != volumen_visto) {
        cambios_vistos = player_cambios();
        filtro_visto = f;
        volumen_visto = vol;
        uart_puts(player_estado_nombre(e));
        uart_puts("  filtro: ");
        uart_puts(filtros_nombre(f));
        uart_puts("  volumen: ");
        uart_putu(vol);
        uart_puts(" %\r\n");
    }
    /* TODO: metadatos en pantalla externa */
}
