/* SW[9:0] (PIO switches), leidos por sondeo. */
#ifndef SWITCHES_H
#define SWITCHES_H

#include <stdint.h>

uint32_t switches_leer(void);         /* bits 9:0 */

#endif
