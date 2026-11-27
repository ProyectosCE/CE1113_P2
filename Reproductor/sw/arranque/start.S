/*
 * Arranque del reproductor en el Cortex-A9 (core 0), corriendo en la OCRAM del HPS.
 *
 * 1. Retiene en reset el watchdog que deja activo el BootROM.
 * 2. Pone la tabla de vectores en VBAR.
 * 3. Prepara las pilas de los modos IRQ y SVC.
 * 4. Pone .bss en cero y salta a main().
 *
 * Las interrupciones entran por irq_entry y se despachan en C con irq_despachar() (gic.c).
 */
    .section .vectors, "ax"
    .arm
    .global _start
_start:
    b       reset
    b       .               /* undefined instruction */
    b       .               /* SVC */
    b       .               /* prefetch abort */
    b       .               /* data abort */
    b       .               /* reservado */
    b       irq_entry       /* IRQ */
    b       .               /* FIQ */

    .text
reset:
    cpsid   if

    /* Watchdog L4WD0 del BootROM en reset (RSTMGR.permodrst, bit 6) */
    ldr     r0, =0xFFD05014
    ldr     r1, [r0]
    orr     r1, r1, #(1 << 6)
    str     r1, [r0]

    /* Vectores: VBAR = _start, SCTLR.V = 0 */
    ldr     r0, =_start
    mcr     p15, 0, r0, c12, c0, 0
    mrc     p15, 0, r0, c1, c0, 0
    bic     r0, r0, #(1 << 13)
    mcr     p15, 0, r0, c1, c0, 0
    isb

    /* Pilas (tamaños en ocram.ld) */
    cps     #0x12                       /* modo IRQ */
    ldr     sp, =__pila_irq_tope
    cps     #0x13                       /* modo SVC */
    ldr     sp, =__pila_svc_tope

    /* .bss en cero */
    ldr     r0, =__bss_start
    ldr     r1, =__bss_end
    mov     r2, #0
1:  cmp     r0, r1
    strlo   r2, [r0], #4
    blo     1b

    bl      main
2:  b       2b

/* Entrada de IRQ: guarda los registros que C puede modificar y vuelve con LR-4 */
irq_entry:
    sub     lr, lr, #4
    push    {r0-r3, r12, lr}
    bl      irq_despachar
    ldmfd   sp!, {r0-r3, r12, pc}^
