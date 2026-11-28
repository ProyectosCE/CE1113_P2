# Documentación del filtro DSP

Diseño, modelo de referencia y verificación del filtro de audio en hardware propio
(`dsp_filter`). Los tres filtros del reproductor (pasa-altos, pasa-banda y ecualizador de
3 bandas) se implementan en este módulo, sobre un mismo núcleo biquad.

| Documento | Contenido |
|---|---|
| [`entorno-python.md`](entorno-python.md) | Entorno virtual de Python para el modelo (`dsp/`) |
| [`diseno-filtros-flotante.md`](diseno-filtros-flotante.md) | Diseño de los filtros en punto flotante, comparación FIR contra IIR y coeficientes |
| [`modelo-punto-fijo.md`](modelo-punto-fijo.md) | Ruta de datos en punto fijo, modelo bit-exacto y vectores de prueba para el testbench |
| [`especificacion-modulo.md`](especificacion-modulo.md) | Especificación del módulo `dsp_filter`: registros, ruta de datos, FSM y diagramas de tiempo |
| [`../../tests/hw/README.md`](../../tests/hw/README.md) | Verificación del RTL: prueba de humo en Questa y pruebas de cocotb contra el modelo, con casos, resultados y formas de onda |

| Carpeta | Contenido |
|---|---|
| [`../../dsp/model/`](../../dsp/model/) | Código del modelo en Python |
| [`../../dsp/tests/`](../../dsp/tests/) | Pruebas del modelo (`pytest`) |
| [`../../dsp/vectors/`](../../dsp/vectors/) | Vectores de prueba para el testbench (`$readmemh`) |
| [`img/`](img/) | Gráficas usadas en estos documentos |
| [`../../Reproductor/ip/dsp_filter/`](../../Reproductor/ip/dsp_filter/) | Hardware: `dsp_filter.sv` y su componente de Platform Designer |
| [`../../tests/hw/cocotb/`](../../tests/hw/cocotb/) | Pruebas de cocotb del RTL (`scripts/hw/docker.sh pytest tests/hw/cocotb`) |
