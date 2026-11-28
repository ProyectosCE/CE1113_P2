# Pull Request

<!-- El título del PR sigue el mismo formato que los commits: [TAG] Descripción, por ejemplo: [ADD] Agrega el núcleo del filtro biquad. Tags y reglas: docs/development/commit-convention.md. El CI lo valida en los PR hacia develop y main. -->

## Descripción

<!-- Explicar brevemente qué cambia este Pull Request y por qué es necesario. -->

## Issue relacionado

<!-- Usar "Closes #<número>" si este PR cierra un issue, o "Related to #<número>" si solo está relacionado. -->

Closes #

## Tipo de cambio

<!-- Marcar las opciones que correspondan: -->

- [ ] Hardware (RTL SystemVerilog, Platform Designer, pines)
- [ ] Software / firmware
- [ ] DSP / filtros
- [ ] Verificación (testbench, pruebas)
- [ ] Corrección de error
- [ ] Refactorización
- [ ] Documentación
- [ ] Build / CI / configuración

## Cambios realizados

<!-- Resumir los cambios principales realizados en este PR. -->

-
-

## Impacto en el sistema

<!-- Marcar si aplica. Estos cambios obligan al resto del equipo a regenerar el hardware o el BSP. -->

- [ ] Modifica el sistema de Platform Designer (`.qsys`) o el mapa de memoria.
- [ ] Modifica registros o la interfaz de un módulo de hardware.
- [ ] Modifica la asignación de pines o la configuración del proyecto de Quartus.

**Detalle del impacto:**

<!-- Ejemplo: nuevo periférico en 0x0001_0000, cambio de offset en el registro de control del filtro, etc. -->

## Validación

<!-- Indicar brevemente cómo se verificó que los cambios funcionan correctamente. -->

- [ ] El hardware se genera y sintetiza correctamente en Quartus, si aplica.
- [ ] El firmware compila correctamente, si aplica.
- [ ] La simulación o el testbench en Questa pasa correctamente, si aplica.
- [ ] Se probó en tarjeta (DE1-SoC / DE10-Standard), si aplica.
- [ ] Se revisó la documentación modificada, si aplica.

**Detalle de validación:**

<!-- Ejemplo: simulación del filtro contra el modelo de referencia, prueba de audio en la DE1-SoC, revisión manual, etc. Adjuntar capturas o formas de onda si es útil. -->

## Checklist

- [ ] El PR apunta a la rama correcta (`develop`, o su rama padre si es una rama hija; `main` solo para versiones estables).
- [ ] El PR contiene únicamente cambios relacionados con su objetivo.
- [ ] No se agregaron archivos generados por Quartus, Questa o la compilación, ni temporales o de caché.
- [ ] La documentación fue actualizada si el cambio lo requiere.
- [ ] El PR está listo para revisión.
