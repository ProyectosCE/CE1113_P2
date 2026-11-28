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

## Entorno Docker: Verilator y cocotb

Además de Questa, el repo trae una imagen de Docker con Verilator 5.040, cocotb 2.0.1 y las
bibliotecas del modelo DSP (`dsp/requirements.txt`), para que todo el grupo haga el lint y las
simulaciones con las mismas versiones sin instalarlas. Se define en `scripts/hw/Dockerfile` y se
usa con `scripts/hw/docker.sh`:

```bash
scripts/hw/docker.sh lint              # lint de todo Reproductor/ip, igual que el CI
scripts/hw/docker.sh lint dsp_filter   # un solo módulo
scripts/hw/docker.sh shell             # terminal dentro del contenedor (en /repo)
scripts/hw/docker.sh <comando ...>     # cualquier comando, p. ej. verilator --version
```

- La imagen se construye sola la primera vez (varios minutos: compila Verilator) y otra vez solo
  si cambian el `Dockerfile` o `dsp/requirements.txt`.
- El repositorio se monta en `/repo` con el usuario actual: lo que se genere dentro del contenedor
  queda a nombre de uno, no de root. El comando corre en la misma carpeta desde la que se llamó.
- Requiere Docker sin `sudo` (usuario en el grupo `docker`).
- Verilator se compila desde el código fuente porque cocotb 2 necesita la versión 5.036 o más
  nueva; el CI usa la de `apt` de Ubuntu 24.04, que es anterior. Si un aviso aparece en una de las
  dos y no en la otra, se corrige el código para que pase en ambas.

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
