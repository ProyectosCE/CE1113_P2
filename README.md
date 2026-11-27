# Instituto Tecnológico de Costa Rica

## Co-diseño Hardware/Software de SoC con Hardware Personalizado para Reproductor de Audio Avanzado

## Sistemas Empotrados (CE1113)

---

### Estudiantes

- José Bernardo Barquero Bonilla (2023150476)
- Jose Eduardo Campos Salazar (2023135620)
- Jimmy Feng Feng (2023060347)
- Alexander Montero Vargas (2023166058)

### Profesor

- Jeferson González Gómez <jgonzalez@itcr.ac.cr>

---

### Objetivo

Mediante el desarrollo de este proyecto el estudiante aplicará los conceptos de diseño a nivel de sistema (System Level Design) y co-diseño hardware/software mediante el modelado, análisis de trade-offs y implementación de un sistema en chip (SoC) para un reproductor de audio portable avanzado.

Al finalizar este proyecto, el estudiante habrá puesto en práctica metodologías modernas de diseño de sistemas embebidos, incluyendo la toma de decisiones arquitecturales sobre la partición hardware/software, así como aplicado técnicas de programación de bajo nivel Bare Metal y diseño de hardware personalizado.

---

### Descripción del sistema

Reproductor de audio WAV sobre la tarjeta **DE1-SoC** (Cyclone V SoC):

- **HPS (ARM Cortex-A9) en bare metal:** lectura de canciones desde la microSD, metadatos,
  lógica de reproducción, filtros en software e interfaz de usuario.
- **FPGA (Platform Designer):** salida de audio por el codec WM8731, botones con interrupción,
  switches, ADC para el volumen, y hardware propio: controlador de displays de 7 segmentos
  (`hex_ctrl`) y filtro de audio (`dsp_filter`).

Arquitectura, decisiones de diseño y estado de cada módulo: [`docs/README.md`](docs/README.md).

### Estado

La **base** del proyecto está lista y probada en la placa: todo el hardware integrado y compilando,
y el esqueleto de software corriendo en el ARM (botones, tiempo en los displays, audio de prueba,
selección de filtro y volumen). Falta implementar la funcionalidad del enunciado: lectura de la SD,
WAV y metadatos, filtros, pantalla externa y arranque desde la SD ([`docs/TAREAS.md`](docs/TAREAS.md)).

---

### Documentación

| Para... | Ver |
|---|---|
| Empezar: instalar, compilar y correr la base | [`docs/GUIA_INICIO.md`](docs/GUIA_INICIO.md) |
| Arquitectura, módulos y estado | [`docs/README.md`](docs/README.md) |
| Lo que falta y reparto de tareas | [`docs/TAREAS.md`](docs/TAREAS.md) |
| Reglas de colaboración y flujo de Git | [`CONTRIBUTING.md`](CONTRIBUTING.md) |
| Compilar el hardware, mapa de memoria | [`Reproductor/README.md`](Reproductor/README.md) |
| Software del ARM | [`Reproductor/sw/README.md`](Reproductor/sw/README.md) |
| Scripts de línea de comandos (Quartus, USB-Blaster) | [`scripts/README.md`](scripts/README.md) |

### Estructura del repositorio

```
CE1113_P2/
├── Reproductor/        el proyecto: sistema de Platform Designer, pines, hardware propio (ip/),
│                       software del ARM (sw/) y Makefile
├── tests/              simulación del hardware propio (hw/) y pruebas en la placa
├── scripts/            scripts de Quartus, Nios V y HPS
├── docs/               estado, tareas, guía de inicio y convenciones de Git
├── ejemplo-blink/      ejemplos de referencia (no son parte del reproductor)
└── ejemplo-niosv/
```

### Inicio rápido

Con el entorno instalado (ver la guía de inicio) y la placa conectada:

```bash
cd Reproductor
make hw && make prog    # hardware
make gdbserver          # terminal 1
make consola            # terminal 2
make sw && make load    # terminal 3: software del ARM
```

---

### Licencia

MIT (ver [`LICENSE`](LICENSE)).
