#include "filtros.h"
#include "dsp.h"

static filtro_t actual = FILTRO_BYPASS;

void filtros_iniciar(void)
{
    actual = FILTRO_BYPASS;
    dsp_habilitar(false);
    /* TODO: dsp_cargar_coeficientes() con los coeficientes del filtro en hardware */
}

void filtros_seleccionar(filtro_t f)
{
    if (f == actual)
        return;
    actual = f;
    dsp_habilitar(f == FILTRO_HW);
    /* TODO: limpiar el estado de los filtros de software al cambiar */
}

filtro_t filtros_actual(void)
{
    return actual;
}

const char *filtros_nombre(filtro_t f)
{
    switch (f) {
    case FILTRO_BYPASS: return "bypass";
    case FILTRO_HW:     return "hardware (dsp_filter)";
    case FILTRO_SW_1:   return "software 1 (pendiente)";
    case FILTRO_SW_2:   return "software 2 (pendiente)";
    }
    return "?";
}

int16_t filtros_procesar(int16_t muestra, int canal)
{
    (void)canal;   /* TODO: estado separado por canal (dsp: bit CANAL de CTRL) */
    switch (actual) {
    case FILTRO_HW:
        return dsp_procesar(muestra);
    case FILTRO_SW_1:   /* TODO */
    case FILTRO_SW_2:   /* TODO */
    case FILTRO_BYPASS:
    default:
        return muestra;
    }
}
