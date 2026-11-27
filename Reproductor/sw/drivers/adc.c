#include "adc.h"
#include "hw.h"

#define ADC_CANAL(n)    (ADC_BASE + 4u * (n))   /* lectura: canal n (bits 11:0) */
#define ADC_AUTO        (ADC_BASE + 0x4u)       /* escritura 1: conversion continua */

void adc_iniciar(void)
{
    REG32(ADC_AUTO) = 1;
}

uint16_t adc_leer(unsigned canal)
{
    return (uint16_t)(REG32(ADC_CANAL(canal & 7u)) & 0xFFFu);
}
