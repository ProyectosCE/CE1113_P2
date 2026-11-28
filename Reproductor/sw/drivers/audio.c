#include "audio.h"
#include "gic.h"
#include "hw.h"

#define AUDIO_CTRL      (AUDIO_BASE + 0x0u)   /* bit 1 = interrupcion de escritura, bit 3 = vaciar */
#define AUDIO_FIFOSPACE (AUDIO_BASE + 0x4u)   /* 31:24 libre izq, 23:16 libre der */
#define AUDIO_IZQ       (AUDIO_BASE + 0x8u)
#define AUDIO_DER       (AUDIO_BASE + 0xCu)

#define CTRL_WE         (1u << 1)
#define CTRL_CW         (1u << 3)

/* Cola circular: el lazo principal escribe en "cabeza", la interrupcion lee en "cola". */
static uint32_t muestras[AUDIO_COLA];       /* izq en bits 15:0, der en 31:16 */
static volatile uint32_t cabeza, cola;
static volatile uint32_t reproducidas, faltantes, irqs, al_codec, encoladas;

static uint32_t espacio_fifo(void)
{
    uint32_t f = REG32(AUDIO_FIFOSPACE);
    uint32_t izq = (f >> 24) & 0xFFu, der = (f >> 16) & 0xFFu;
    return izq < der ? izq : der;
}

/* Interrupcion: el FIFO del codec esta al 75 % vacio. Llenarlo completo. */
static void audio_irq(void)
{
    ++irqs;
    for (uint32_t n = espacio_fifo(); n > 0; --n) {
        uint32_t m = 0;                     /* silencio si la cola esta vacia */
        if (cola != cabeza) {
            m = muestras[cola];
            cola = (cola + 1u) & (AUDIO_COLA - 1u);
            ++reproducidas;
        } else {
            ++faltantes;
        }
        REG32(AUDIO_IZQ) = (uint32_t)(int32_t)(int16_t)(m & 0xFFFFu);
        REG32(AUDIO_DER) = (uint32_t)(int32_t)(int16_t)(m >> 16);
        ++al_codec;
    }
}

void audio_iniciar(void)
{
    REG32(AUDIO_CTRL) = CTRL_CW;            /* vaciar los FIFOs de salida */
    REG32(AUDIO_CTRL) = 0;
    cabeza = cola = 0;
    reproducidas = 0;
    gic_registrar(IRQ_AUDIO, audio_irq);
    REG32(AUDIO_CTRL) = CTRL_WE;            /* interrupcion de escritura */
}

uint32_t audio_libres(void)
{
    return (AUDIO_COLA - 1u) - ((cabeza - cola) & (AUDIO_COLA - 1u));
}

int audio_encolar(int16_t izq, int16_t der)
{
    uint32_t siguiente = (cabeza + 1u) & (AUDIO_COLA - 1u);
    if (siguiente == cola)
        return 0;
    muestras[cabeza] = (uint16_t)izq | ((uint32_t)(uint16_t)der << 16);
    cabeza = siguiente;
    ++encoladas;
    return 1;
}

uint32_t audio_espacio(void)
{
    return audio_libres();
}

void audio_escribir(int16_t izq, int16_t der)
{
    (void)audio_encolar(izq, der);
}

void audio_vaciar(void)
{
    uint32_t cpsr;
    __asm__ volatile("mrs %0, cpsr" : "=r"(cpsr));
    irq_deshabilitar();
    cola = cabeza;
    reproducidas = 0;
    if (!(cpsr & (1u << 7)))                /* solo si ya estaban habilitadas */
        irq_habilitar();
}

uint32_t audio_irqs(void)      { return irqs; }
uint32_t audio_al_codec(void)  { return al_codec; }
uint32_t audio_encoladas(void) { return encoladas; }

uint32_t audio_faltantes(void)
{
    return faltantes;
}

uint32_t audio_reproducidas(void)
{
    return reproducidas;
}
