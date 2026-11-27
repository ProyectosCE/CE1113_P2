/*
 * Incremento 0 - arranque minimo del Cortex-A9 (core 0) corriendo en la OCRAM.
 * Se carga por JTAG con gdb; "load" deja el PC en _start.
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
    b       .               /* IRQ */
    b       .               /* FIQ */

    .text
reset:
    cpsid   if                      /* sin interrupciones en esta prueba */

    /* El BootROM puede dejar activo el watchdog L4WD0: si la placa se resetea sola a los
     * pocos segundos, es eso. Se retiene en reset con RSTMGR.permodrst (0xFFD05014), bit 6
     * (l4wd0). Verificar el bit en el Cyclone V HPS Technical Reference Manual. */
    ldr     r0, =0xFFD05014
    ldr     r1, [r0]
    orr     r1, r1, #(1 << 6)
    str     r1, [r0]

    ldr     sp, =__stack_top

    /* Poner .bss en cero */
    ldr     r0, =__bss_start
    ldr     r1, =__bss_end
    mov     r2, #0
1:  cmp     r0, r1
    strlo   r2, [r0], #4
    blo     1b

    bl      main
2:  b       2b
