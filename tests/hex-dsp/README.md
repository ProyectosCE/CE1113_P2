# Prueba del hardware propio en la placa: `hex_ctrl` y `dsp_filter`

Complementa la simulación de `tests/hw/` (que se corre antes de integrar): esta prueba verifica los
dos módulos ya dentro del sistema, accedidos por el ARM a través del puente lightweight.

| Qué se ve | Qué se espera |
|---|---|
| Consola JTAG UART | `dsp_filter INFO = 0xD5F1020F  (ID correcto)` (`0xD5F10110` con la versión `0x01`), `dsp_filter: paso directo OK` (en la versión `0x02` los coeficientes de reset son la identidad) y `hex_ctrl STATUS = 0x4E58....  (ID correcto)` |
| HEX3–HEX0 | Cronómetro `00 00`, `00 01`, … avanzando 1 por segundo (la base de tiempo es el codec a 44.1 kHz) |
| HEX5–HEX4 | El valor de SW[6:0] en decimal (00–99; arriba de 99 se queda en 99) |
| LEDR | Copia de los switches |

## Pasos

```bash
# Compilar
cd tests/hex-dsp
arm-none-eabi-gcc -mcpu=cortex-a9 -marm -O1 -g -nostdlib -ffreestanding \
    -T ../inc0-hps/ocram.ld ../inc0-hps/start.S main.c -o hex-dsp.elf

# Terminal 1: gdb-server
../../scripts/hps/gdb-server.sh

# Terminal 2: cargar y ejecutar
gdb-multiarch -x ../inc0-hps/cargar.gdb hex-dsp.elf
(gdb) continue

# Terminal 3: consola JTAG UART
../../scripts/general/terminal.sh
```

## Si algo falla

| Síntoma | Causa probable |
|---|---|
| Displays apagados o con segmentos sueltos | Pines de HEX sin asignar: `grep hex_hex Reproductor/output/reproductor.pin` debe mostrar los pines de `pines.qsf` |
| Dígitos que no se parecen a números | Orden de los bits de segmento distinto al esperado ({g,f,e,d,c,b,a}) |
| `ID INCORRECTO` o el programa se cuelga al leer | Dirección base distinta: `hex_ctrl` debe estar en `0x0020` y `dsp_filter` en `0x5000` |
| El cronómetro no avanza | El FIFO de audio no se vacía (ver la prueba de audio) |

## Resultados

Prueba hecha el 2026-11-26 en la DE1-SoC rev. F/G del grupo, con la versión `0x01` de `dsp_filter`.

| Qué se probó | Resultado |
|---|---|
| `dsp_filter` INFO | `0xD5F10110`: ID `0xD5F1`, versión `0x01` (esqueleto), 16 coeficientes |
| `dsp_filter` paso directo (7 muestras, incluidos 32767 y −32768) | OK |
| `hex_ctrl` STATUS | `0x4E580000`: ID `0x4E58`, sin fuera de rango |
| Cronómetro en HEX3–HEX0 | Avanza 1 por segundo en formato MM:SS |
| SW[6:0] en HEX5–HEX4 | Muestra el valor en decimal |
| Switches → LEDR | Correcto |

Salida de la consola:

```
prueba hex-dsp
dsp_filter INFO = 0xD5F10110  (ID correcto)
dsp_filter: paso directo OK
hex_ctrl STATUS = 0x4E580000  (ID correcto)
```

En la ejecución real se perdieron 2 caracteres (`dsfilter`): la consola por JTAG puede tardar más
de lo que `uart_putc` espera. No afecta el resultado.

Instancias en `reproductor.qsys`: `hex_ctrl_0` (base `0x0020`, export `hex`) y `dsp_filter_0`
(base `0x5000`).
