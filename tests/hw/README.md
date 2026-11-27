# Verificación aislada del hardware propio (simulación)

El enunciado exige verificar el hardware propio de forma aislada antes de integrarlo, y
documentar los casos de prueba y sus resultados. Estos testbenches son autoverificables: cada
uno compara las salidas contra lo esperado con `assert` (cada falla sale como `** Error` de Questa)
e imprime `RESULTADO <módulo>: OK` o el número de fallas. Módulos y testbenches en SystemVerilog.

```bash
tests/hw/sim.sh todos          # simula hex_ctrl y dsp_filter en Questa (consola)
tests/hw/sim.sh hex_ctrl -gui  # abre Questa con las formas de onda
```

El script carga `scripts/general/env.sh` (Questa y la licencia SALT) y compila desde
`Reproductor/ip/<módulo>/<módulo>.sv`.

## `hex_ctrl` — `tb_hex_ctrl.sv`

| # | Caso | Se verifica |
|---|---|---|
| 1 | Tras el reset | Todos los displays apagados |
| 2 | Lectura de STATUS | ID = `0x4E58` |
| 3 | Tiempo 03:27 | HEX3..HEX0 = 0, 3, 2, 7 |
| 4 | Tiempo 59:59 y 00:00 | Extremos del rango |
| 5 | Lectura de TIEMPO | Se lee lo escrito (12:34) |
| 6 | Canción 7 | HEX5 = 0, HEX4 = 7 |
| 7 | Segundos = 61 | Satura en 59 y STATUS.FUERA_RANGO = 1; se limpia con un valor válido |
| 8 | EN_TIEMPO = 0 | HEX3..HEX0 apagados, HEX5..HEX4 siguen mostrando la canción |

## `dsp_filter` — `tb_dsp_filter.sv` (esqueleto)

| # | Caso | Se verifica |
|---|---|---|
| 1 | Lectura de INFO | ID = `0xD5F1`, NUM_COEF = 16 |
| 2 | Tras el reset | LISTO = 0, OCUPADO = 0 |
| 3 | 16 coeficientes | Se escriben y se leen de vuelta (valores negativos incluidos) |
| 4 | Muestras 0, 1, −1, 32767, −32768, 1234 con EN = 1 y una con EN = 0 | La salida es igual a la entrada (paso directo) |
| 5 | Lectura de CTRL | EN y CANAL se leen de vuelta; LIMPIAR se lee como 0 |

Cuando se implemente el filtro real, el caso 4 debe comparar contra la respuesta calculada aparte
(por ejemplo con Python u Octave para los mismos coeficientes) y agregarse casos de impulso,
escalón y saturación.

## Resultados

(llenar al simular)
