# Entorno de Python para DSP

El diseño y modelado de los filtros se hace en Python 3.11 o superior dentro de un entorno virtual ubicado en `dsp/.venv` (no se sube al repositorio).

## Requisitos

- Python 3.11 o superior con el módulo `venv`
  (Ubuntu/Debian: `sudo apt install python3.11 python3.11-venv`)
  (Ubuntu 24.04/26.04: `sudo apt install python3-venv`)

## Uso

Desde la raíz del repositorio:

```bash
source scripts/dsp/setup-env.sh
```

La primera vez crea el entorno e instala las dependencias de
`dsp/requirements.txt`. Las siguientes veces solo lo activa, salvo que
`requirements.txt` haya cambiado, en cuyo caso instala lo nuevo.

Para verificar el entorno:

```bash
python dsp/model/check_env.py
```

Para salir del entorno:

```bash
deactivate
```

## Agregar una biblioteca

1. Agregarla a `dsp/requirements.txt` con un rango de versiones.
2. Volver a ejecutar `source scripts/dsp/setup-env.sh`.

## Archivos de audio

Los archivos de audio de trabajo van en `dsp/audio/`. Ningún archivo de
audio se sube al repositorio (ver `.gitignore`).
