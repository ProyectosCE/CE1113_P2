#include "audio.h"
#include "hw.h"

#define AUDIO_CTRL      (AUDIO_BASE + 0x0u)   /* bit 3 = vaciar FIFOs de salida */
#define AUDIO_FIFOSPACE (AUDIO_BASE + 0x4u)   /* 31:24 libre izq, 23:16 libre der */
#define AUDIO_IZQ       (AUDIO_BASE + 0x8u)
#define AUDIO_DER       (AUDIO_BASE + 0xCu)

void audio_iniciar(void)
{
    REG32(AUDIO_CTRL) = 1u << 3;
    REG32(AUDIO_CTRL) = 0;
    /* TODO: llenar el FIFO por interrupcion (IRQ_AUDIO, bit 1 de CTRL) en vez de sondeo */
}

uint32_t audio_espacio(void)
{
    uint32_t f = REG32(AUDIO_FIFOSPACE);
    uint32_t izq = (f >> 24) & 0xFFu, der = (f >> 16) & 0xFFu;
    return izq < der ? izq : der;
}

void audio_escribir(int16_t izq, int16_t der)
{
    REG32(AUDIO_IZQ) = (uint32_t)(int32_t)izq;
    REG32(AUDIO_DER) = (uint32_t)(int32_t)der;
}
