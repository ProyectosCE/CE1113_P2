/*
 * Prueba del hardware propio en la placa: hex_ctrl y dsp_filter.
 *
 * - dsp_filter: lee INFO, envia muestras de prueba y verifica que la salida sea igual a la entrada
 *   (el esqueleto deja pasar la muestra). Imprime el resultado por la JTAG UART.
 * - hex_ctrl: HEX3-0 muestran un cronometro MM:SS y HEX5-4 el valor de SW[6:0] (numero de
 *   cancion, se satura en 99). La base de tiempo es el codec: se envian ceros al Audio Core y
 *   cada 44100 muestras pasa 1 s.
 *
 * Acceso directo a registros (sin HAL). Se compila con ../inc0-hps/start.S y ocram.ld.
 */
#include <stdint.h>

#define REG(dir)            (*(volatile uint32_t *)(dir))

#define RSTMGR_BRGMODRST    0xFFD0501Cu
#define L3_REMAP            0xFF800000u

#define LW_BASE             0xFF200000u
#define LEDS                (LW_BASE + 0x0000u)
#define SWITCHES            (LW_BASE + 0x0040u)
#define JTAG_UART_DATA      (LW_BASE + 0x1000u)
#define JTAG_UART_CTRL      (LW_BASE + 0x1004u)
#define AUDIO_CTRL          (LW_BASE + 0x3040u)
#define AUDIO_FIFOSPACE     (LW_BASE + 0x3044u)
#define AUDIO_LEFT          (LW_BASE + 0x3048u)
#define AUDIO_RIGHT         (LW_BASE + 0x304Cu)

#define HEX_BASE            (LW_BASE + 0x0020u)
#define HEX_CTRL            (HEX_BASE + 0x0u)
#define HEX_TIEMPO          (HEX_BASE + 0x4u)
#define HEX_CANCION         (HEX_BASE + 0x8u)
#define HEX_STATUS          (HEX_BASE + 0xCu)

#define DSP_BASE            (LW_BASE + 0x5000u)
#define DSP_CTRL            (DSP_BASE + 0x00u)
#define DSP_STATUS          (DSP_BASE + 0x04u)
#define DSP_DATA_IN         (DSP_BASE + 0x08u)
#define DSP_DATA_OUT        (DSP_BASE + 0x0Cu)
#define DSP_INFO            (DSP_BASE + 0x18u)

#define FS                  44100u

/* Espera a que haya espacio en el FIFO de 64 caracteres; si no hay terminal leyendo, se rinde
 * tras un tiempo y descarta el caracter (asi el programa no se cuelga sin terminal). */
static void uart_putc(char c)
{
    for (uint32_t t = 0; t < 2000000u; ++t) {
        if (REG(JTAG_UART_CTRL) >> 16) {
            REG(JTAG_UART_DATA) = (uint32_t)c;
            return;
        }
    }
}

static void uart_puts(const char *s)
{
    while (*s)
        uart_putc(*s++);
}

static void uart_puthex(uint32_t v)
{
    static const char hex[] = "0123456789ABCDEF";
    uart_puts("0x");
    for (int i = 28; i >= 0; i -= 4)
        uart_putc(hex[(v >> i) & 0xFu]);
}

/* Envia una muestra al dsp_filter y devuelve el resultado; marca *error si LISTO no sube */
static int32_t dsp_procesar(int16_t muestra, int *error)
{
    REG(DSP_DATA_IN) = (uint32_t)(uint16_t)muestra;
    for (int i = 0; i < 1000; ++i) {
        if (REG(DSP_STATUS) & 1u)
            return (int32_t)REG(DSP_DATA_OUT);
    }
    *error = 1;
    return 0;
}

static void probar_dsp(void)
{
    static const int16_t muestras[] = { 0, 1, -1, 32767, -32768, 1234, -4321 };
    int fallas = 0, sin_respuesta = 0;

    uint32_t info = REG(DSP_INFO);
    uart_puts("dsp_filter INFO = ");
    uart_puthex(info);
    uart_puts((info >> 16) == 0xD5F1u ? "  (ID correcto)\r\n" : "  (ID INCORRECTO)\r\n");

    REG(DSP_CTRL) = 1u;   /* EN = 1 */
    for (unsigned i = 0; i < sizeof muestras / sizeof muestras[0]; ++i) {
        int32_t r = dsp_procesar(muestras[i], &sin_respuesta);
        if (r != muestras[i])
            ++fallas;
    }
    REG(DSP_CTRL) = 0u;

    if (sin_respuesta)
        uart_puts("dsp_filter: LISTO nunca subio\r\n");
    uart_puts(fallas == 0 ? "dsp_filter: paso directo OK\r\n" : "dsp_filter: FALLA en paso directo\r\n");
}

int main(void)
{
    REG(RSTMGR_BRGMODRST) = 0;
    REG(L3_REMAP) |= (1u << 3) | (1u << 4);

    uart_puts("\r\nprueba hex-dsp\r\n");
    probar_dsp();

    uint32_t hex_status = REG(HEX_STATUS);
    uart_puts("hex_ctrl STATUS = ");
    uart_puthex(hex_status);
    uart_puts((hex_status >> 16) == 0x4E58u ? "  (ID correcto)\r\n" : "  (ID INCORRECTO)\r\n");

    REG(HEX_CTRL) = 0x3u;          /* tiempo y cancion encendidos */
    REG(AUDIO_CTRL) = 1u << 3;     /* vaciar FIFOs de salida */
    REG(AUDIO_CTRL) = 0;

    uint32_t muestras = 0, segundos = 0;
    REG(HEX_TIEMPO) = 0;

    for (;;) {
        uint32_t sw = REG(SWITCHES) & 0x3FFu;
        REG(LEDS) = sw;
        REG(HEX_CANCION) = sw & 0x7Fu;

        uint32_t libre = REG(AUDIO_FIFOSPACE);
        uint32_t n = ((libre >> 24) & 0xFFu) < ((libre >> 16) & 0xFFu) ?
                     ((libre >> 24) & 0xFFu) : ((libre >> 16) & 0xFFu);
        while (n--) {
            REG(AUDIO_LEFT) = 0;
            REG(AUDIO_RIGHT) = 0;
            if (++muestras == FS) {
                muestras = 0;
                ++segundos;
                uint32_t m = (segundos / 60u) % 100u, s = segundos % 60u;
                REG(HEX_TIEMPO) = (m << 8) | s;
            }
        }
    }
}
