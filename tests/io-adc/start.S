/*
 * Arranque minimo con interrupciones para el Cortex-A9 (core 0), corriendo en la OCRAM.
 * Igual que ../inc0-hps/start.S, mas: VBAR apuntando a la tabla de vectores, pila de modo IRQ
 * y una entrada de IRQ que llama a irq_handler() en C.
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

    /* Vectores en _start: VBAR = _start y SCTLR.V = 0 (vectores bajos, relativos a VBAR) */
    ldr     r0, =_start
    mcr     p15, 0, r0, c12, c0, 0
    mrc     p15, 0, r0, c1, c0, 0
    bic     r0, r0, #(1 << 13)
    mcr     p15, 0, r0, c1, c0, 0
    isb

    /* Pilas: IRQ arriba (2 KB), SVC debajo */
    cps     #0x12                       /* modo IRQ */
    ldr     sp, =__stack_top
    cps     #0x13                       /* modo SVC */
    ldr     sp, =__stack_top - 0x800

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
    bl      irq_handler
    ldmfd   sp!, {r0-r3, r12, pc}^
