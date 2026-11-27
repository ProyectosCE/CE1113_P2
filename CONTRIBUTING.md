# Guía de colaboración

Cómo trabajar en grupo sobre la base del reproductor sin romper lo que ya funciona.

- **Si es tu primera vez: [`docs/GUIA_INICIO.md`](docs/GUIA_INICIO.md)** (instalar, compilar y ver la base funcionando)
- Estado de la base y descripción de cada módulo: [`docs/README.md`](docs/README.md)
- Tareas pendientes y reparto: [`docs/TAREAS.md`](docs/TAREAS.md)
- Ramas: [`docs/development/branching-strategy.md`](docs/development/branching-strategy.md)
- Commits: [`docs/development/commit-convention.md`](docs/development/commit-convention.md)

---

## 1. Entorno y sesión de trabajo

La instalación y la primera ejecución están en [`docs/GUIA_INICIO.md`](docs/GUIA_INICIO.md). Para
el día a día, después de cada encendido de la placa:

```bash
cd Reproductor
make prog              # 1. programar la FPGA (primero y solo, sin otras herramientas JTAG abiertas)
make gdbserver         # 2. terminal 1
make consola           # 3. terminal 2
make sw && make load   # 4. terminal 3
```

**Nunca usar `sudo`** con los scripts ni con `make`.

| Necesito… | Comando |
|---|---|
| Recompilar el hardware | `make hw` (luego `make prog`; cerrar antes gdb-server y consola) |
| Depurar paso a paso | `make debug` (en vez de `make load`): gdb detenido en `main` |
| Simular el hardware propio | `tests/hw/sim.sh todos` (desde la raíz del repo) |
| Ver recursos usados | `make report` |
| Verificar los pines | `grep <puerto> output/reproductor.pin` |

Problemas frecuentes: tabla *Si algo falla* de la guía de inicio. Uno más al tocar hardware: si un
periférico nuevo no responde o lee siempre 0 / 4095, casi seguro el nombre del puerto en
`pines.qsf` no coincide con el del top (revisar `output/reproductor.pin`).

---

## 2. Dónde vive cada cosa

```
Reproductor/
├── reproductor.qsys       sistema de Platform Designer
├── pines.qsf              pines de la FPGA
├── ip/                    hardware propio (SystemVerilog + _hw.tcl): hex_ctrl, dsp_filter
├── sw/                    software del ARM (ver sw/README.md)
│   ├── include/hw.h       TODAS las direcciones e IRQ
│   ├── drivers/           un archivo por periférico
│   └── reproductor/       lógica del reproductor
└── Makefile
tests/                     pruebas: simulación (hw/) y pruebas en placa
scripts/                   scripts de Quartus, Nios V y HPS
docs/                      estado, tareas, convenciones
```

---

## 3. Reglas para no romper la base

### Hardware

1. **Una sola persona a la vez modifica `reproductor.qsys`.** Es XML generado por la herramienta y
   los conflictos de Git en ese archivo son muy difíciles de resolver. Avisar en el grupo antes de
   abrirlo, hacer el cambio, compilar, probar y subirlo rápido.
2. **El mapa de direcciones es fijo.** Si se agrega un periférico, usar una base libre y bloquearla
   (*Lock Base Address*). Si se cambia una base, actualizar en el mismo PR `sw/include/hw.h`,
   `docs/README.md` y `Reproductor/README.md`.
3. **Cada puerto nuevo del top va en `pines.qsf` con el nombre exacto del top**, y se verifica en
   `output/reproductor.pin` después de compilar. Quartus no da error si el nombre no coincide.
4. **Hardware propio: simular antes de integrar.** Todo cambio en `ip/` va con su testbench en
   `tests/hw/` pasando (`RESULTADO ...: OK`). Si cambia un registro, actualizar el encabezado del
   `.sv`, el testbench, el driver en `sw/drivers/` y la tabla de registros en `docs/README.md`.
5. No subir archivos generados: `output/`, `reproductor/`, `*.sopcinfo`, `sw/build/`, `*.elf`
   (ya están en `.gitignore`).

### Software

1. **Sin HAL:** acceso directo a registros con `REG32()` y las direcciones de `hw.h`. Nada de
   bibliotecas de abstracción sin consultarlo con el grupo (y el profesor, si aplica).
2. Un driver por periférico en `drivers/`; la lógica del reproductor en `reproductor/`. Los drivers
   no llaman a módulos del reproductor.
3. **Memoria:** todo corre en 64 KB de OCRAM. Nada de arreglos grandes; revisar el tamaño que
   imprime `make sw` y `sw/build/reproductor.map` en cada PR.
4. **Interrupciones:** los manejadores hacen lo mínimo (leer, limpiar, marcar un evento) y el
   trabajo pesado va en el lazo principal. Registrar manejadores con `gic_registrar()`.
5. `make sw` debe compilar **sin warnings**.
6. Los `TODO` del esqueleto marcan lo pendiente: al implementar uno, borrar el `TODO`.

---

## 4. Flujo de Git

1. Tomar un paquete de [`docs/TAREAS.md`](docs/TAREAS.md) y crear (o asignarse) su **issue**.
2. Rama desde `develop`: `feature/lectura-sd`, `feature/filtro-fir-hw`, `fix/...`, `docs/...`, `test/...`
3. Commits pequeños y descriptivos (ver la convención).
4. Antes del PR: `git merge develop` en la rama, compilar (`make hw` si tocó hardware, `make sw`),
   simular si tocó `ip/`, probar en la placa.
5. PR hacia `develop` con la plantilla completa (*Impacto en el sistema* y *Validación*), enlazando
   el issue (`Closes #N`). Al menos una persona lo revisa.
6. Borrar la rama después de integrarla. `develop` → `main` solo para versiones estables.

> **Atención — convención de commits:** el enunciado evalúa (10 %) un historial que siga
> **Conventional Commits** (`feat(sd): ...`, `fix(dsp): ...`, `docs: ...`), y la plantilla de PR
> también lo pide, pero `docs/development/commit-convention.md` usa etiquetas `[ADD]`, `[FIX]`...
> El grupo debe decidir una sola convención antes de seguir; lo recomendable es Conventional
> Commits para cumplir la rúbrica y actualizar ese documento.

---

## 5. Antes de pedir revisión: lista corta

- [ ] Compila (`make hw` y/o `make sw` sin warnings).
- [ ] Simulación pasando, si tocó `ip/`.
- [ ] Probado en la placa; resultado anotado en el README de la prueba correspondiente.
- [ ] Mapa de direcciones, pines y documentación actualizados, si cambiaron.
- [ ] Sin archivos generados en el commit.
