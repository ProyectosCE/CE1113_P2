# Especificación del módulo `dsp_filter`

Este documento especifica, antes de escribir el RTL, el módulo de hardware
propio que aplica los filtros de audio del reproductor: su interfaz
Avalon-MM, el mapa de registros, el acceso a los coeficientes y la forma de
usarlo desde el ARM. Es la referencia para el RTL (Fase 4), el testbench
(Fase 5) y el driver `dsp.c` (Fase 7).

El módulo implementa exactamente la ruta de datos del modelo bit-exacto
descrito en [modelo-punto-fijo.md](modelo-punto-fijo.md); los filtros y sus
coeficientes están en [diseno-filtros-flotante.md](diseno-filtros-flotante.md).

Archivo del hardware: `Reproductor/ip/dsp_filter/dsp_filter.sv` (núcleo e
interfaz en el mismo archivo).

---

## 1. Alcance

`dsp_filter` es un esclavo Avalon-MM en el puente liviano HPS–FPGA. El ARM le
escribe una muestra de 16 bits, el módulo la filtra con una cascada de
3 biquads y el ARM lee el resultado. Los tres filtros del reproductor
(pasa-altos, pasa-banda y ecualizador de 3 bandas) son el mismo hardware con
distintos coeficientes; el software elige el filtro cargando sus
15 coeficientes.

| Característica | Valor |
|---|---|
| Dirección base | `0xFF20_5000` (`LW_BASE + 0x5000`, `DSP_BASE` en `hw.h`) |
| Reloj | 50 MHz |
| Muestras | 16 bits con signo (Q1.15), un canal por vez |
| Canales | 2 (izquierdo y derecho), con estado independiente |
| Filtro | cascada de 3 biquads en Forma Directa I |
| Coeficientes | 15 (3 etapas × 5), Q3.15 de 18 bits |
| Tiempo por muestra | 20 ciclos (0,4 µs) |
| Bypass | la muestra sale igual a la entrada, sin tocar el estado |

### 1.1 Nombres usados en este documento y en el RTL

Los registros que ve el ARM van en mayúsculas (`CTRL`, `COEF_DATA`). Las
señales internas van en minúsculas y son las mismas que tendrá
`dsp_filter.sv`:

| Nombre | Qué es |
|---|---|
| `coef[0:14]` | banco de los 15 coeficientes de 18 bits |
| `acc` | acumulador de 48 bits de la MAC |
| `etapa` | contador de la etapa en proceso (0 a 2) |
| `paso` | contador del producto dentro de la etapa (0 a 4) |
| `x1`, `x2`, `y1`, `y2` | historiales de cada etapa, 24 bits, por canal |
| `residuo` | error de redondeo guardado de cada etapa, 15 bits, por canal |
| `saturo` | bit pegajoso de saturación (se ve en `STATUS`) |

---

## 2. Decisiones de diseño

| Decisión | Elección | Por qué |
|---|---|---|
| Arquitectura de la MAC | secuencial, un solo multiplicador | una muestra usa 20 de los 1133 ciclos que hay en un periodo de muestreo a 44,1 kHz (50 MHz / 44 100); 15 multiplicadores en paralelo gastarían 15 bloques DSP sin necesidad |
| Multiplicar y acumular | en el mismo ciclo, sin pipeline | un bloque DSP en modo 27×27 debería cumplir 20 ns; si la Fase 6 muestra que no, se agrega un registro (un ciclo más por producto) |
| Control | FSM de 4 estados (`REPOSO`, `MAC`, `CIERRE_ETAPA`, `SALIDA`) | ver la sección de la FSM |
| Estado del filtro | registros (flip-flops), separado por etapa y por canal | unos 670 bits; una RAM interna agregaría latencia sin ganancia; separado por etapa refleja el modelo uno a uno |
| Canal | bit `CTRL.CANAL`, capturado al escribir `DATA_IN` | se mantiene el registro del esqueleto; el tiempo sobra para una escritura extra por muestra |
| Coeficientes | acceso indirecto con `COEF_IDX` y `COEF_DATA`, sin autoincremento | 15 coeficientes no caben en las 8 direcciones del módulo; cargar un filtro son 30 escrituras, muy por debajo de los 100 ms del requisito |
| Cambio de filtro | escribir `COEF_DATA` borra el estado de los dos canales | el modelo reinicia el estado al cargar coeficientes; el hardware lo garantiza aunque el software no use `LIMPIAR` |
| Valor de reset de los coeficientes | cada etapa como identidad (`b0 = 1,0`) | si se habilita el filtro sin cargar coeficientes, el audio pasa sin cambios en vez de salir silencio o basura |
| Saturación | bit pegajoso `STATUS.SATURO` | queda en 1 hasta que se borre, así no se pierde una saturación de una sola muestra; sirve para depurar y como evidencia |
| Interfaz Avalon-MM | la del esqueleto, sin cambios | el `_hw.tcl` y `reproductor.qsys` no se tocan |

---

## 3. Interfaz Avalon-MM

| Señal | Dirección | Ancho | Descripción |
|---|---|---:|---|
| `clk` | entrada | 1 | reloj de 50 MHz |
| `reset` | entrada | 1 | reset síncrono, activo en alto |
| `avs_address` | entrada | 3 | dirección en palabras de 32 bits (8 registros) |
| `avs_read` | entrada | 1 | lectura |
| `avs_readdata` | salida | 32 | dato leído, con latencia fija de 1 ciclo |
| `avs_write` | entrada | 1 | escritura |
| `avs_writedata` | entrada | 32 | dato a escribir |

- **Sin `waitrequest`:** el módulo nunca detiene al ARM. Las escrituras toman
  efecto en el flanco en que llegan y las lecturas responden al ciclo
  siguiente.
- **Sin `byteenable`:** todos los accesos son de 32 bits (`REG32` en el
  driver). La dirección en bytes es `avs_address × 4`.
- **Procesamiento asíncrono para el ARM:** escribir `DATA_IN` solo arranca el
  cálculo; el ARM consulta `STATUS.LISTO` hasta que el resultado esté listo.

---

## 4. Mapa de registros

| Offset | Registro | Acceso | Reset | Contenido |
|---|---|---|---|---|
| `0x00` | `CTRL` | RW | `0x0` | control: `EN`, `LIMPIAR`, `CANAL` |
| `0x04` | `STATUS` | R | `0x0` | estado: `LISTO`, `OCUPADO`, `SATURO` |
| `0x08` | `DATA_IN` | RW | `0x0` | muestra de entrada; escribirla inicia el procesamiento |
| `0x0C` | `DATA_OUT` | R | `0x0` | resultado de la última muestra |
| `0x10` | `COEF_IDX` | RW | `0x0` | índice del coeficiente (0 a 14) |
| `0x14` | `COEF_DATA` | RW | ver 5.3 | coeficiente Q3.15 en la posición `COEF_IDX` |
| `0x18` | `INFO` | R | `0xD5F1_020F` | identificación del módulo |
| `0x1C` | — | R | `0x0` | reservado: se lee 0, las escrituras se ignoran |

En todos los registros, los bits no descritos se leen como 0 y se ignoran al
escribir.

### 4.1 `CTRL` (`0x00`, RW)

| Bit | Campo | Acceso | Reset | Descripción |
|---:|---|---|---:|---|
| 0 | `EN` | RW | 0 | 1 = filtrar; 0 = bypass (la muestra sale igual a la entrada y el estado no cambia) |
| 1 | `LIMPIAR` | W | 0 | escribir 1 borra el estado de los dos canales (`x1`, `x2`, `y1`, `y2`, `residuo`) y el bit `SATURO`; se lee siempre como 0 |
| 2 | `CANAL` | RW | 0 | canal de la próxima muestra: 0 = izquierdo, 1 = derecho |

Una escritura en `CTRL` cambia los tres campos a la vez: para cambiar de canal
el software debe volver a escribir el valor de `EN` que quiere mantener, y
`LIMPIAR` en 0. `CANAL` se captura en el momento en que se escribe `DATA_IN`,
así que cambiarlo mientras se procesa una muestra no afecta a esa muestra.

### 4.2 `STATUS` (`0x04`, R)

| Bit | Campo | Reset | Descripción |
|---:|---|---:|---|
| 0 | `LISTO` | 0 | `DATA_OUT` tiene el resultado de la última muestra escrita |
| 1 | `OCUPADO` | 0 | el núcleo está procesando una muestra |
| 2 | `SATURO` | 0 | alguna etapa saturó su salida desde la última vez que se borró (pegajoso) |

- En el mismo flanco en que se escribe `DATA_IN`, `LISTO` baja y `OCUPADO`
  sube. Así, una lectura de `STATUS` justo después de la escritura nunca ve
  el `LISTO` de la muestra anterior (igual que en el esqueleto).
- `LISTO` se queda en 1 hasta la siguiente escritura de `DATA_IN`.
- `SATURO` se enciende cuando la salida de cualquier etapa, en cualquier
  canal, se satura a 24 bits; es lo mismo que cuenta `saturations` en
  `fixed_model.py`. La saturación final de 24 a 16 bits no lo enciende (solo
  puede ocurrir al redondear un valor que ya está en el tope, y el modelo
  tampoco la cuenta). Se borra con `CTRL.LIMPIAR` o al escribir `COEF_DATA`.

### 4.3 `DATA_IN` (`0x08`, RW)

| Bits | Acceso | Descripción |
|---|---|---|
| 15:0 | W | muestra de 16 bits con signo (Q1.15); escribirla inicia el procesamiento |
| 31:0 | R | última muestra aceptada, extendida en signo a 32 bits |

Si se escribe mientras `OCUPADO = 1`, la escritura se descarta por completo:
`DATA_IN` no cambia y no se inicia otro procesamiento.

### 4.4 `DATA_OUT` (`0x0C`, R)

| Bits | Descripción |
|---|---|
| 31:0 | resultado de 16 bits con signo, extendido en signo a 32 bits |

Es válido cuando `STATUS.LISTO = 1`. Mientras se procesa conserva el resultado
anterior. En bypass es igual a la muestra de entrada.

### 4.5 `COEF_IDX` (`0x10`, RW)

| Bits | Descripción |
|---|---|
| 7:0 | índice del coeficiente al que acceden las lecturas y escrituras de `COEF_DATA` |

Acepta cualquier valor de 0 a 255, pero solo 0 a 14 son índices válidos
(sección 5).

### 4.6 `COEF_DATA` (`0x14`, RW)

| Bits | Acceso | Descripción |
|---|---|---|
| 17:0 | W | coeficiente Q3.15; se guarda en `coef[COEF_IDX]`. Los bits 31:18 se ignoran |
| 31:0 | R | `coef[COEF_IDX]` extendido en signo a 32 bits |

- Una escritura con índice válido guarda el coeficiente **y borra el estado
  de los dos canales y el bit `SATURO`**, como un `CTRL.LIMPIAR`.
- Con índice no válido (15 o mayor), la escritura se ignora por completo
  (no guarda nada ni borra el estado) y la lectura devuelve 0.

### 4.7 `INFO` (`0x18`, R)

| Bits | Campo | Valor | Descripción |
|---|---|---|---|
| 31:16 | `ID` | `0xD5F1` | identifica al módulo |
| 15:8 | `VERSION` | `0x02` | `0x01` = esqueleto de paso directo; `0x02` = cascada de biquads |
| 7:0 | `NUM_COEF` | `0x0F` | número de coeficientes (15) |

---

## 5. Coeficientes: acceso indirecto

### 5.1 Cómo funciona

El filtro necesita 15 coeficientes, pero el módulo solo tiene 8 direcciones.
Por eso los coeficientes no tienen un registro cada uno: se accede a ellos a
través de una "ventanilla".

- `COEF_IDX` elige cuál coeficiente se va a leer o escribir.
- `COEF_DATA` es la ventanilla: escribir en ella guarda el valor en
  `coef[COEF_IDX]`, y leerla devuelve `coef[COEF_IDX]`.

`COEF_IDX` solo sirve para que el ARM acceda al banco. Al filtrar, el núcleo
no lo usa: lee directamente `coef[etapa·5 + paso]` con sus propios contadores,
así que el valor que quede en `COEF_IDX` no afecta el filtrado.

### 5.2 Orden de los índices

Es el mismo orden de `coefs.hex` en `dsp/vectors/`, de modo que el testbench
puede cargar el archivo tal cual.

| Índice | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Etapa | 0 | 0 | 0 | 0 | 0 | 1 | 1 | 1 | 1 | 1 | 2 | 2 | 2 | 2 | 2 |
| Coeficiente | b0 | b1 | b2 | a1 | a2 | b0 | b1 | b2 | a1 | a2 | b0 | b1 | b2 | a1 | a2 |

Índice = `etapa·5 + paso`, con `paso` = 0 para b0, 1 para b1, 2 para b2,
3 para a1 y 4 para a2. Los `a` se guardan con el signo que tienen en la
ecuación del filtro; la MAC resta sus productos (no se niegan al cargarlos).

### 5.3 Formato y valores de reset

Los coeficientes son Q3.15 de 18 bits en complemento a dos: el valor real es
el entero dividido entre 2^15 = 32768, con rango [−4, 4).

Al reset, cada etapa queda como identidad (`y = x`):

| Índices | Valor |
|---|---|
| 0, 5, 10 (los `b0`) | `0x08000` (1,0) |
| todos los demás | `0x00000` |

### 5.4 Ejemplo

Coeficiente `b1` de la etapa 1 del ecualizador a 44,1 kHz (el peaking de
1 kHz), índice 6. En `dsp/vectors/44100/equalizer/coefs.hex` vale `31650`,
que en 18 bits es −59824, es decir −59824 / 32768 ≈ −1,826.

```c
REG32(DSP_COEF_IDX)  = 6;            /* elegir el coeficiente 6 */
REG32(DSP_COEF_DATA) = 0xFFFF1650;   /* −59824 extendido en signo a 32 bits */
```

1. La primera escritura solo guarda 6 en `COEF_IDX`.
2. La segunda guarda los bits 17:0 (`0x31650`) en `coef[6]` y, en el mismo
   flanco, borra el estado de los dos canales y `SATURO`.

Para leerlo de vuelta se escribe 6 en `COEF_IDX` y se lee `COEF_DATA`, que
devuelve `0xFFFF1650`.

---

## 6. Uso desde el ARM

Los nombres de las macros son los de `Reproductor/sw/drivers/dsp.c`.

### 6.1 Inicialización

1. Leer `INFO` y comprobar `ID = 0xD5F1` y `VERSION = 0x02`.
2. Escribir `CTRL = LIMPIAR` (bypass, estado en cero).

### 6.2 Cambio de filtro

Se escriben los 15 coeficientes del filtro nuevo y luego se habilita:

```c
for (unsigned i = 0; i < 15; ++i) {
    REG32(DSP_COEF_IDX)  = i;
    REG32(DSP_COEF_DATA) = (uint32_t)c[i];   /* c[i]: int32_t, Q3.15 */
}
REG32(DSP_CTRL) = 1u;                         /* EN = 1 */
```

No hace falta `LIMPIAR`: cada escritura de `COEF_DATA` ya borra el estado. El
cambio se hace entre dos pares de muestras, no entre la muestra izquierda y
la derecha de un mismo par. Son 31 escrituras (unos pocos microsegundos), muy
por debajo de los 100 ms que pide el requisito; el tiempo real se mide en la
Fase 7.

Para pasar a bypass basta con `CTRL = 0`: no se cargan coeficientes y el
estado se conserva.

### 6.3 Procesamiento de un par estéreo

El mismo procedimiento sirve con el filtro activo o en bypass.

```c
uint32_t en = filtrar ? 1u : 0u;

REG32(DSP_CTRL)    = en | (0u << 2);              /* CANAL = izquierdo */
REG32(DSP_DATA_IN) = (uint32_t)(uint16_t)izq;
while ((REG32(DSP_STATUS) & 1u) == 0) { }         /* esperar LISTO */
izq = (int16_t)REG32(DSP_DATA_OUT);

REG32(DSP_CTRL)    = en | (1u << 2);              /* CANAL = derecho */
REG32(DSP_DATA_IN) = (uint32_t)(uint16_t)der;
while ((REG32(DSP_STATUS) & 1u) == 0) { }
der = (int16_t)REG32(DSP_DATA_OUT);
```

El driver real limita la espera a un número de intentos (hoy 100), como
`dsp_procesar()`; con 20 ciclos por muestra el margen sobra.

---

## 7. Casos especiales

| Situación | Comportamiento |
|---|---|
| Escribir `DATA_IN` con `OCUPADO = 1` | se descarta por completo |
| Escribir `CTRL`, `COEF_IDX` o `COEF_DATA` con `OCUPADO = 1` | uso no permitido: el resultado de la muestra en proceso no está definido. No ocurre si el software espera `LISTO` |
| `COEF_IDX` ≥ 15 | escrituras de `COEF_DATA` ignoradas, lecturas en 0 |
| Escribir `COEF_DATA` con índice válido | guarda el coeficiente y borra el estado y `SATURO` |
| `CTRL.EN = 0` (bypass) | la muestra pasa por `DATA_IN` → `LISTO` → `DATA_OUT` sin cambios; el estado no se toca |
| Pasar de bypass a filtrar | se continúa con el estado que había antes del bypass |
| Reset | registros en 0, estado en cero, coeficientes en identidad, `LISTO = 0` |
| Escribir en `INFO`, `STATUS`, `DATA_OUT` o `0x1C` | se ignora |

---

## 8. Cambios pendientes para la Fase 4

Al implementar estos registros, `CONTRIBUTING.md` obliga a actualizar en el
mismo cambio:

| Archivo | Cambio |
|---|---|
| `Reproductor/ip/dsp_filter/dsp_filter.sv` | encabezado con el mapa de registros nuevo; `VERSION = 0x02`; `NUM_COEF` fijo en 15 |
| `tests/hw/tb_dsp_filter.sv` | quitar `#(.NUM_COEF(16))`; probar contra los vectores de `dsp/vectors/` |
| `Reproductor/sw/drivers/dsp.c` y `dsp.h` | coeficientes `int32_t` Q3.15, comprobación de `VERSION`, canal en `CTRL` |
| `docs/README.md` (sección 3.9) | tabla de registros nueva |

El `_hw.tcl` no debería cambiar, porque la interfaz Avalon-MM es la misma; se
confirma en la Fase 4.
