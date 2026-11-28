# Guía de inicio

Para quien llega al proyecto: de clonar el repo a ver el reproductor funcionando en la placa, y
qué hacer después. Toma unos 30–60 minutos (más la primera compilación del hardware, unos 10).

Sistema: Linux (probado en Ubuntu 24.04). Placa: DE1-SoC (rev. F/G).

---

## Paso 1 — Clonar y conocer el repo

```bash
git clone <url-del-repo> CE1113_P2
cd CE1113_P2
git checkout develop
```

| Ruta | Qué es |
|---|---|
| `Reproductor/` | El proyecto: sistema de Platform Designer, pines, `Makefile`, hardware propio (`ip/`) y software del ARM (`sw/`) |
| `tests/` | Pruebas: simulación del hardware propio (`hw/`) y pruebas en la placa |
| `scripts/` | Scripts de Quartus, del Nios V (ejemplos) y del HPS (gdb-server) |
| `dsp/` | Modelo del filtro DSP en Python (ver [`docs/dsp/README.md`](dsp/README.md)) |
| `docs/` | Estado de la base, tareas, convenciones de Git, esta guía |
| `ejemplo-blink/`, `ejemplo-niosv/` | Ejemplos de referencia (no son parte del reproductor) |

Leer después de esta guía: [`docs/README.md`](README.md) (arquitectura y módulos) y
[`docs/TAREAS.md`](TAREAS.md) (lo que falta).

## Paso 2 — Instalar las herramientas

1. **Quartus Prime Lite 25.1std** con Questa y RiscFree, en `~/altera_lite/25.1std`.
   Si está en otra ruta, agregar a `~/.bashrc`: `export ALTERA_ROOT=/ruta/a/25.1std`.
2. **Licencia de Questa** en `~/.altera.quartus/questa_lic.dat`.
3. **Compilador y depurador para el ARM:**
   ```bash
   sudo apt install gcc-arm-none-eabi binutils-arm-none-eabi gdb-multiarch
   ```
4. **Permisos del USB-Blaster** (sin esto, `jtagconfig` solo funciona con `sudo`):
   ```bash
   sudo tee /etc/udev/rules.d/51-usbblaster.rules > /dev/null <<'EOF'
   SUBSYSTEM=="usb", ATTRS{idVendor}=="09fb", ATTRS{idProduct}=="6001", MODE="0666"
   SUBSYSTEM=="usb", ATTRS{idVendor}=="09fb", ATTRS{idProduct}=="6002", MODE="0666"
   SUBSYSTEM=="usb", ATTRS{idVendor}=="09fb", ATTRS{idProduct}=="6003", MODE="0666"
   SUBSYSTEM=="usb", ATTRS{idVendor}=="09fb", ATTRS{idProduct}=="6010", MODE="0666"
   SUBSYSTEM=="usb", ATTRS{idVendor}=="09fb", ATTRS{idProduct}=="6810", MODE="0666"
   EOF
   sudo udevadm control --reload-rules && sudo udevadm trigger
   ```
5. **Permisos de ejecución** de los scripts (Git a veces los pierde):
   ```bash
   chmod +x scripts/*/*.sh tests/hw/sim.sh
   ```

> No usar `sudo` con `make` ni con los scripts del repo: como root no encuentran Quartus y dejan
> procesos que después bloquean el cable.

## Paso 3 — Conectar la placa

1. **Sacar la microSD** (mientras se trabaja cargando por JTAG).
2. Cable USB al conector **USB-Blaster** (tipo B, junto a la alimentación), no al mini-USB.
3. Encender la placa y verificar:
   ```bash
   source scripts/general/env.sh
   jtagconfig
   ```
   Debe mostrar `4BA00477 SOCVHPS` (el ARM) y `02D120DD 5CSE(BA5|MA5)` (la FPGA).
   Si dice `No JTAG hardware available`: revisar el paso 2.4, desconectar y conectar el cable.

## Paso 4 — Compilar y programar el hardware

```bash
cd Reproductor
make hw      # ~10 min la primera vez: Platform Designer + síntesis + fitter
make prog    # programa la FPGA (hay que repetirlo cada vez que se apaga la placa)
```

`make hw` debe terminar con `Bitstream: .../output/reproductor.sof`. El log completo queda en
`Reproductor/output/build.log`.

## Paso 5 — (Opcional) Simular el hardware propio

Desde la raíz del repo:

```bash
tests/hw/sim.sh todos
```

Debe imprimir `RESULTADO hex_ctrl: OK` y `RESULTADO dsp_filter: OK`.

## Paso 6 — Compilar y correr el software

Tres terminales, todas en `Reproductor/`:

```bash
make gdbserver          # terminal 1: se queda corriendo (Q para salir)
make consola            # terminal 2: consola del programa
make sw && make load    # terminal 3: compila y carga el programa en el ARM
```

En la consola debe aparecer:

```
=== Reproductor DE1-SoC ===
hex_ctrl: ok
dsp_filter: ok
SD: PENDIENTE / no responde
FAT: PENDIENTE / no responde
cancion 1/10  detenido  filtro: bypass  volumen: ...
```

(SD y FAT aparecen como pendientes: todavía no están implementadas.)

## Paso 7 — Probar que todo responde

Conectar audífonos a **Line Out** (jack verde), con volumen bajo.

| Acción | Resultado esperado |
|---|---|
| KEY0 | Suena un tono; el tiempo corre en HEX3–0; LEDR8 encendido. Otra vez: pausa (LEDR9) |
| KEY1 | Se detiene y el tiempo vuelve a 00:00 |
| KEY2 / KEY3 | Canción anterior / siguiente: cambia el número en HEX5–4 |
| SW[1:0] | Cambia el filtro (se ve en LEDR[1:0] y en la consola) |
| Potenciómetro en el conector del ADC (opcional) | Cambia el volumen del tono |

Si todo esto pasa, el entorno está listo.

## Paso 8 — Empezar a trabajar

1. Leer [`CONTRIBUTING.md`](../CONTRIBUTING.md): reglas para no romper la base y flujo de Git.
2. Elegir un paquete en [`docs/TAREAS.md`](TAREAS.md) y asignarse su issue.
3. Crear la rama desde `develop` (por ejemplo `feature/lectura-sd`) y trabajar.
4. Si el paquete es de software, empezar por el `README.md` de `Reproductor/sw/`: los archivos a
   completar ya existen y tienen marcado con `TODO` lo que falta.

---

## Si algo falla

| Síntoma | Solución |
|---|---|
| `jtagconfig`: *No JTAG hardware available* | Paso 2.4 (udev). Con `lsusb \| grep 09fb` se ve si el cable está detectado |
| *Permission denied* al correr un script | `chmod +x <script>` |
| *ERROR: no encuentro Quartus en '/root/...'* | Se usó `sudo`: correr sin `sudo` |
| `make consola`: *no JTAG UARTs available* | La FPGA no está programada: `make prog` |
| gdb-server: *Unexpected error during IR scan* | Se programó la FPGA con el gdb-server abierto: cerrar todo, apagar y encender la placa, repetir pasos 4 (solo `make prog`) y 6 |
| gdb se queda en `Remote debugging using :3334` | `Q` en el gdb-server y volver a arrancarlo |
| La placa se reinicia sola a los pocos segundos | Cargar siempre con `make load` o `make debug` (apagan el watchdog del BootROM) |
| No suena nada | Audífonos en Line Out (verde); KEY0 para reproducir; revisar el volumen (potenciómetro) |

Más detalles por tema: [`scripts/README.md`](../scripts/README.md) (scripts y USB-Blaster),
[`Reproductor/README.md`](../Reproductor/README.md) (compilación del hardware),
[`Reproductor/sw/README.md`](../Reproductor/sw/README.md) (software).
