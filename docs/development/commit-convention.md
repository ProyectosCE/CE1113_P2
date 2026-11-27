# Estándar de commits

## 1. Objetivo

Este documento define la convención utilizada para escribir los mensajes de commit en el repositorio.

El repositorio sigue **[Conventional Commits](https://www.conventionalcommits.org/es/v1.0.0/)**, que es lo que pide la especificación del proyecto. El CI (`.github/workflows/ci.yml`) valida cada commit y el título de cada Pull Request con las reglas de `commitlint.config.mjs`; si un mensaje no cumple el formato, el CI falla.

---

## 2. Formato general

```text
tipo(alcance): descripción breve
```

- **tipo:** obligatorio, en minúsculas, de la lista de la sección 3.
- **alcance:** opcional, entre paréntesis, indica la parte del proyecto afectada (sección 4).
- **descripción:** obligatoria, en español, corta y clara (máximo 100 caracteres en total en la línea).

Ejemplos:

```text
feat(sd): agrega lectura de bloques de la microSD
fix(dsp): corrige la saturación del acumulador del filtro
docs: actualiza la guía de inicio
test(hw): agrega casos de impulso al testbench del filtro
```

---

## 3. Tipos

| Tipo | Uso |
|---|---|
| `feat` | Funcionalidad nueva: módulo, driver, componente de hardware, periférico |
| `fix` | Corrección de un error o comportamiento incorrecto |
| `docs` | Solo documentación: README, Markdown, comentarios relevantes |
| `test` | Pruebas: testbenches, pruebas en placa |
| `refactor` | Reorganización del código sin cambiar su comportamiento |
| `perf` | Mejora de rendimiento o de uso de recursos |
| `build` | Sistema de compilación: Makefile, scripts de Quartus, pines, configuración del proyecto |
| `ci` | Integración continua: workflows de GitHub Actions, `commitlint.config.mjs` |
| `chore` | Mantenimiento que no encaja en los anteriores (por ejemplo eliminar archivos obsoletos) |
| `style` | Formato del código sin cambio de lógica |
| `revert` | Revierte un commit anterior |

Equivalencias con la convención anterior del grupo: `[ADD]` → `feat`, `[UPDATE]` → `feat` o `refactor`, `[FIX]` → `fix`, `[DEL]` → `chore`, `[DOCS]` → `docs`, `[TEST]` → `test`, `[REFACTOR]` → `refactor`.

---

## 4. Alcances sugeridos

El CI advierte (sin fallar) si se usa un alcance fuera de esta lista:

| Área | Alcances |
|---|---|
| Hardware | `hw`, `qsys`, `pines`, `hex`, `dsp`, `audio`, `adc`, `keys` |
| Software | `sw`, `drivers`, `sd`, `fat`, `wav`, `player`, `filtros`, `ui`, `volumen` |
| Otros | `tests`, `scripts`, `ci`, `docs` |

---

## 5. Descripción breve

La descripción debe:

* Estar escrita en español.
* Ser corta y clara.
* Explicar qué se modificó.
* Evitar mensajes genéricos.

Ejemplos que deben evitarse:

```text
feat: cambios
fix: arreglo
chore: cosas
```

---

## 6. Cuerpo y cambios incompatibles

El cuerpo del commit es opcional; se separa de la primera línea con una línea en blanco y sirve para explicar la razón del cambio, decisiones técnicas o limitaciones.

Un cambio que obliga al resto del equipo a adaptarse (por ejemplo, mover la dirección de un periférico o cambiar los registros de un módulo) se marca con `!` y una nota en el pie:

```text
feat(dsp)!: agrega registro de ganancia al filtro

BREAKING CHANGE: COEF_DATA pasa del offset 0x14 al 0x18; actualizar dsp.c.
```

---

## 7. Resumen

```text
tipo(alcance): descripción breve
```

Tipos: `feat`, `fix`, `docs`, `test`, `refactor`, `perf`, `build`, `ci`, `chore`, `style`, `revert`.

Cada commit debe representar un cambio lógico. El título del Pull Request sigue el mismo formato, porque al integrar con *squash* se convierte en el commit de `develop`.
