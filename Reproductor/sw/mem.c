/*
 * memset, memcpy, memmove y memcmp minimos. No hay biblioteca de C (-nostdlib), pero GCC puede
 * generar llamadas a estas funciones por su cuenta (al inicializar estructuras o copiar
 * arreglos), y fat.c / wav.c las van a necesitar. El atributo evita que GCC convierta estos
 * mismos bucles en llamadas a si mismos.
 */
#include <stddef.h>
#include <stdint.h>

#define SIN_PATRONES __attribute__((optimize("no-tree-loop-distribute-patterns")))

SIN_PATRONES void *memset(void *d, int c, size_t n)
{
    uint8_t *p = d;
    while (n--)
        *p++ = (uint8_t)c;
    return d;
}

SIN_PATRONES void *memcpy(void *restrict d, const void *restrict s, size_t n)
{
    uint8_t *pd = d;
    const uint8_t *ps = s;
    while (n--)
        *pd++ = *ps++;
    return d;
}

SIN_PATRONES void *memmove(void *d, const void *s, size_t n)
{
    uint8_t *pd = d;
    const uint8_t *ps = s;
    if (pd < ps) {
        while (n--)
            *pd++ = *ps++;
    } else {
        pd += n;
        ps += n;
        while (n--)
            *--pd = *--ps;
    }
    return d;
}

SIN_PATRONES int memcmp(const void *a, const void *b, size_t n)
{
    const uint8_t *pa = a, *pb = b;
    for (; n; --n, ++pa, ++pb) {
        if (*pa != *pb)
            return *pa - *pb;
    }
    return 0;
}