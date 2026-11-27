/* Controlador de interrupciones (GIC) del Cortex-A9 MPCore. */
#ifndef GIC_H
#define GIC_H

#include <stdint.h>

typedef void (*gic_manejador_t)(void);

/* Deja el distribuidor y la interfaz de CPU habilitados, sin ninguna interrupcion activa. */
void gic_iniciar(void);

/* Asocia un manejador al ID y habilita esa interrupcion hacia el CPU0. 0 = ok, -1 = ID invalido. */
int gic_registrar(uint32_t id, gic_manejador_t manejador);

/* Llamada desde irq_entry (start.S): atiende la interrupcion pendiente. */
void irq_despachar(void);

static inline void irq_habilitar(void)    { __asm__ volatile("cpsie i" ::: "memory"); }
static inline void irq_deshabilitar(void) { __asm__ volatile("cpsid i" ::: "memory"); }

#endif
