/*
 * Mapa de direcciones del sistema "reproductor" (Reproductor/reproductor.qsys) y del HPS.
 * Es la unica fuente de direcciones del software: si cambia una base en Platform Designer,
 * se cambia aqui.
 */
#ifndef HW_H
#define HW_H

#include <stdint.h>

#define REG32(dir)              (*(volatile uint32_t *)(uintptr_t)(dir))

/* ---- HPS ---- */
#define HPS_RSTMGR_PERMODRST    0xFFD05014u     /* reset de perifericos (bit 6 = watchdog L4WD0) */
#define HPS_RSTMGR_BRGMODRST    0xFFD0501Cu     /* reset de los puentes HPS<->FPGA */
#define HPS_L3_REMAP            0xFF800000u     /* bit 3 = puente H2F, bit 4 = puente LW */
#define HPS_GICD_BASE           0xFFFED000u     /* GIC: distribuidor */
#define HPS_GICC_BASE           0xFFFEC100u     /* GIC: interfaz de CPU */
#define HPS_SDMMC_BASE          0xFF704000u     /* controlador SD/MMC */

/* ---- Perifericos de la FPGA (puente lightweight) ---- */
#define LW_BASE                 0xFF200000u
#define LEDS_BASE               (LW_BASE + 0x0000u)
#define HEX_BASE                (LW_BASE + 0x0020u)     /* hex_ctrl_0 (propio) */
#define SWITCHES_BASE           (LW_BASE + 0x0040u)
#define KEYS_BASE               (LW_BASE + 0x0050u)
#define JTAG_UART_BASE          (LW_BASE + 0x1000u)
#define AV_CONFIG_BASE          (LW_BASE + 0x3000u)
#define AUDIO_BASE              (LW_BASE + 0x3040u)
#define ADC_BASE                (LW_BASE + 0x4000u)
#define DSP_BASE                (LW_BASE + 0x5000u)     /* dsp_filter_0 (propio) */

/* ---- Interrupciones (f2h_irq0[n] -> GIC ID 72 + n) ---- */
#define IRQ_FPGA_BASE           72u
#define IRQ_AUDIO               (IRQ_FPGA_BASE + 0u)
#define IRQ_KEYS                (IRQ_FPGA_BASE + 1u)

/* ---- Audio ---- */
#define AUDIO_FS                44100u          /* el codec trabaja fijo a 44.1 kHz */

#endif
