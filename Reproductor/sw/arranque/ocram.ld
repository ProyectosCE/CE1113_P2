/*
 * Mapa de memoria del reproductor (fase 1): todo en la OCRAM del HPS, 64 KB en 0xFFFF0000.
 *
 *   0xFFFF0000  .vectors + .text + .rodata + .data + .bss   (crece hacia arriba)
 *        ...    libre
 *   tope - 3 KB pila SVC (2 KB, crece hacia abajo)
 *   tope - 1 KB pila IRQ (1 KB)
 *   0xFFFFFFF8  tope
 */
MEMORY
{
    OCRAM (rwx) : ORIGIN = 0xFFFF0000, LENGTH = 64K
}

ENTRY(_start)

PILA_IRQ = 1K;
PILA_SVC = 2K;

SECTIONS
{
    .text : {
        KEEP(*(.vectors))
        *(.text*)
    } > OCRAM

    .rodata : { *(.rodata*) } > OCRAM

    .ARM.exidx : { *(.ARM.exidx*) } > OCRAM

    .data : { *(.data*) } > OCRAM

    .bss (NOLOAD) : {
        . = ALIGN(4);
        __bss_start = .;
        *(.bss*)
        *(COMMON)
        . = ALIGN(4);
        __bss_end = .;
    } > OCRAM

    /* ORIGIN + LENGTH desborda 32 bits: el tope se deja 8 bytes abajo */
    __pila_irq_tope = ORIGIN(OCRAM) + LENGTH(OCRAM) - 8;
    __pila_svc_tope = __pila_irq_tope - PILA_IRQ;
    __pila_svc_fondo = __pila_svc_tope - PILA_SVC;

    ASSERT(__bss_end <= __pila_svc_fondo, "El programa no cabe en la OCRAM junto con las pilas")
}
