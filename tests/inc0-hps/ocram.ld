/* Incremento 0 - todo en la OCRAM del HPS (64 KB en 0xFFFF0000). */
MEMORY
{
    OCRAM (rwx) : ORIGIN = 0xFFFF0000, LENGTH = 64K
}

ENTRY(_start)

SECTIONS
{
    .text : {
        KEEP(*(.vectors))
        *(.text*)
        *(.rodata*)
    } > OCRAM

    .data : { *(.data*) } > OCRAM

    .bss (NOLOAD) : {
        . = ALIGN(4);
        __bss_start = .;
        *(.bss*)
        *(COMMON)
        . = ALIGN(4);
        __bss_end = .;
    } > OCRAM

    /* Pila al final de la OCRAM (ORIGIN + LENGTH desborda 32 bits, por eso el -8) */
    __stack_top = ORIGIN(OCRAM) + LENGTH(OCRAM) - 8;
    ASSERT(__bss_end <= __stack_top - 2048, "No queda espacio para la pila en la OCRAM")
}
