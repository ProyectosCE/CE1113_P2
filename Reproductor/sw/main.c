/*
 * Reproductor de audio - DE1-SoC, HPS en bare metal.
 *
 * Esqueleto de la aplicacion: inicializa todos los perifericos y corre el lazo principal
 * (botones -> player, switches -> filtro, ADC -> volumen, audio, interfaz). La fuente de audio
 * son los .wav de la SD (player.c); si la SD no responde o no tiene .wav, suena un tono de
 * prueba (tono.c).
 */
#include <stdint.h>

#include "adc.h"
#include "audio.h"
#include "dsp.h"
#include "gic.h"
#include "hex.h"
#include "hps.h"
#include "jtag_uart.h"
#include "keys.h"
#include "sdmmc.h"
#include "switches.h"

#include "fat.h"
#include "filtros.h"
#include "player.h"
#include "ui.h"
#include "volumen.h"

#define CANCIONES_PRUEBA    10u     /* si la SD no tiene .wav (tono de prueba) */

static void informar(const char *nombre, int ok)
{
    uart_puts(nombre);
    uart_puts(ok ? ": ok\r\n" : ": PENDIENTE / no responde\r\n");
}

int main(void)
{
    hps_iniciar();
    uart_puts("\r\n=== Reproductor DE1-SoC ===\r\n");

    gic_iniciar();
    keys_iniciar();
    audio_iniciar();
    adc_iniciar();
    ui_iniciar();
    filtros_iniciar();

    informar("hex_ctrl", hex_id() == 0x4E58u);
    informar("dsp_filter", dsp_iniciar() == 0);
    informar("SD", sdmmc_iniciar() == 0);
    informar("FAT", fat_montar() == 0);

    int n = fat_contar_wav();
    for (int i = 0; i < n; ++i) {                   /* canciones encontradas en la SD */
        uart_puts("  ");
        uart_putu((uint32_t)i + 1u);
        uart_puts(". ");
        uart_puts(fat_nombre_wav(i));
        uart_puts("\r\n");
    }
    player_iniciar(n > 0 ? (uint32_t)n : CANCIONES_PRUEBA);
    irq_habilitar();

    for (;;) {
        /* Entradas */
        player_eventos(keys_eventos());
        filtros_seleccionar((filtro_t)(switches_leer() & 0x3u));
        volumen_desde_adc(adc_leer(0));

        /* Audio: llenar la cola del codec (la interrupcion la pasa al FIFO) */
        for (uint32_t libre = audio_espacio(); libre > 0; --libre) {
            int16_t izq = 0, der = 0;
            if (player_estado() == PLAYER_REPRODUCIENDO && player_muestra(&izq, &der))
                player_muestra_enviada();
            izq = volumen_aplicar(filtros_procesar(izq, 0));
            der = volumen_aplicar(filtros_procesar(der, 1));
            audio_escribir(izq, der);
        }

        /* Salidas */
        ui_actualizar();
    }
}