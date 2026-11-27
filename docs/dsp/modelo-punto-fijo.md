# Modelo en punto fijo bit-exacto

Este documento describe la ruta de datos en punto fijo del filtro y el modelo
de referencia en Python contra el que se verificará el hardware. El hardware
debe producir, con las mismas entradas y coeficientes, exactamente las mismas
salidas que el modelo, bit a bit.

Código en `dsp/model/`, pruebas en `dsp/tests/` y vectores en `dsp/vectors/`.
El diseño de los filtros en punto flotante está en
[diseno-filtros-flotante.md](diseno-filtros-flotante.md).

---

## 1. Ruta de datos

| Señal | Ancho | Formato |
|---|---:|---|
| Muestra de entrada y salida | 16 bits | Q1.15 |
| Estado entre etapas (`x` e `y` guardados) | 24 bits | Q1.23 |
| Coeficientes | 18 bits | Q3.15 |
| Producto muestra × coeficiente | 42 bits | Q4.38 |
| Acumulador | 48 bits | Q10.38 |
| Residuo del redondeo | 15 bits | — |

Un formato Qm.n tiene m bits enteros (incluido el signo) y n bits de
fracción, en complemento a dos. Su rango es [−2^(m−1), 2^(m−1)).

- **Muestras, Q1.15:** el formato del audio WAV de 16 bits, rango [−1, 1).
- **Coeficientes, Q3.15:** el coeficiente de mayor magnitud es
  `b1 = −2,1737` (high-shelf a 44,1 kHz), por lo que se necesitan 3 bits
  enteros. Rango [−4, 4).
- **Estado, Q1.23:** las señales internas tienen más bits de fracción que el
  audio para reducir el error de redondeo (sección 5).
- **Acumulador de 48 bits:** la suma de los 5 productos necesita 3 bits más
  que el producto; se dejan 6 de margen. El modelo verifica en cada suma
  parcial que el acumulador no se desborde.

---

## 2. Operación de una etapa (Forma Directa I)

Cada etapa biquad procesa una muestra con esta secuencia exacta, que el RTL
debe reproducir en el mismo orden:

```text
acc  = r[n-1]             residuo del redondeo de la muestra anterior
acc += b0 · x[n]
acc += b1 · x[n-1]
acc += b2 · x[n-2]
acc -= a1 · y[n-1]        se RESTA el producto
acc -= a2 · y[n-2]

q    = redondear(acc, 15 bits)
r[n] = acc − q · 2^15     residuo: bits descartados, en [−2^14, 2^14)
y[n] = saturar(q, 24 bits)

x[n-2] ← x[n-1] ← x[n]
y[n-2] ← y[n-1] ← y[n]
```

Reglas que el hardware debe cumplir:

- **Se resta el producto de `a1` y `a2`; no se niega el coeficiente.** En
  Q3.15 el valor −4,0 existe pero +4,0 no cabe, así que negar un coeficiente
  podría desbordarse.
- **Redondeo al más cercano con empates hacia +∞:** se suma 2^14 y se hace un
  desplazamiento aritmético de 15 bits a la derecha. Ejemplos: +0,5 → 1,
  −0,5 → 0, −1,5 → −1. En SystemVerilog, sobre un valor `signed`:
  `(acc + (1 <<< 14)) >>> 15`.
- **Saturación a la salida de cada etapa:** si el resultado no cabe en
  24 bits, se reemplaza por el máximo o el mínimo representable. Nunca "da
  la vuelta".
- **El residuo se guarda aunque la salida se haya saturado.**

---

## 3. Cascada, bypass y estados

- Cada filtro son **3 etapas en cascada**; la salida de una es la entrada de
  la siguiente. Las etapas que un filtro no usa son identidad
  (`b0 = 1`, el resto 0) y dejan pasar la señal exacta.
- La **entrada de 16 bits** se extiende a 24 bits desplazándola 8 bits a la
  izquierda (sin pérdida).
- La **salida final** se redondea de 24 a 16 bits (misma regla de redondeo,
  descartando 8 bits) y se satura a 16 bits.
- **Bypass:** la muestra sale igual a la entrada y el estado no se modifica.
- **Reinicio y cambio de filtro:** `x`, `y` y el residuo de todas las etapas
  vuelven a 0. Cargar coeficientes nuevos reinicia el estado para que restos
  del filtro anterior no produzcan un chasquido.
- **Estéreo:** cada canal tiene su propio estado; los coeficientes son los
  mismos para ambos.
- **Saturaciones:** el modelo cuenta cuántas veces satura alguna etapa; en
  hardware corresponde al bit de overflow del registro de estado.

---

## 4. Realimentación del error de redondeo

**Problema encontrado.** Al probar el modelo con una señal seguida de
silencio, varios filtros no volvían a cero: la salida se quedaba pegada en
un valor constante para siempre (ciclo límite). El peor caso fue el
ecualizador a 44,1 kHz, con estado de 16 bits, que quedaba en **819 LSB**
(un 2,5 % de la escala). La causa es el low-shelf de 200 Hz, cuyo polo está
en 0,983: cada salida es casi igual a la anterior y el pequeño cambio que
debería hacerla bajar se pierde por debajo de medio LSB al redondear.

Un valor constante no se oye como sonido, pero resta margen antes de
saturar, produce un clic al cambiar de filtro o entrar en bypass y hace que
el silencio entre canciones no sea cero.

**Solución.** Al redondear, los 15 bits descartados (el residuo) se guardan
y el acumulador de la siguiente muestra empieza con ese valor en vez de con
0. Así los errores de redondeo se compensan en lugar de acumularse.

| Opción (ecualizador a 44,1 kHz) | Error máximo contra el flotante | Silencio |
|---|---:|---|
| 16 bits, solo redondeo | ~130 LSB | se pega en 819 |
| 24 bits, solo redondeo | 1 LSB | se pega en 3 |
| 16 bits + realimentación | 5 LSB | vuelve a 0 |
| **24 bits + realimentación** | **1 LSB** | **vuelve a 0** |
| 16 bits, truncando hacia cero | 344 LSB | vuelve a 0 |

**Costo en hardware:** un registro de 15 bits por etapa y por canal. No
agrega ciclos: el acumulador se carga con el residuo en lugar de limpiarse.

---

## 5. Precisión entre etapas: 24 bits

Medido con `dsp/model/measure_fixed.py` sobre todos los filtros y
frecuencias de muestreo, con ruido más chirp a nivel normal y con un tono
suave de −40 dBFS. "Ideal" es la referencia flotante redondeada a 16 bits:
lo mejor que se puede lograr con salida de 16 bits.

| Configuración | Señal | Error máx (LSB) | SNR mínima (dB) | Pérdida vs ideal (dB) | Silencio |
|---|---|---:|---:|---:|---:|
| Ideal | normal | 0,50 | 78,3 | 0,0 | 0 |
| Ideal | suave | 0,50 | 46,6 | 0,0 | 0 |
| 16 bits | normal | 5,12 | 68,1 | 13,2 | 0 |
| 16 bits | suave | 4,39 | 37,6 | 13,9 | 0 |
| **24 bits** | normal | **0,51** | **78,3** | **0,0** | 0 |
| **24 bits** | suave | **0,51** | **46,6** | **0,0** | 0 |

*Peor caso entre todos los filtros y frecuencias de muestreo, ambos con
realimentación del error.*

**Decisión: 24 bits.** Con 24 bits el modelo es indistinguible del ideal;
con 16 bits el ecualizador pierde hasta 14 dB de SNR (ruido de redondeo de
unos −87 dBFS frente a −101 dBFS del ideal).

**Costo:** el multiplicador pasa de 16×18 a 24×18. Con una sola MAC
secuencial ocupa un bloque DSP del Cyclone V en cualquiera de los dos casos
(cada bloque funciona como dos multiplicadores de 18×18 o uno de 27×27). Lo
que crece es el ancho de los registros de estado (8 bits más por cada `x` e
`y` guardado) y del acumulador (de 40 a 48 bits). Se confirmará con el
reporte de recursos de Quartus.

---

## 6. Coeficientes en punto fijo

Los coeficientes se convierten a enteros Q3.15 redondeando al más cercano
(`dsp/model/fixed_coefficients.py`). Si los coeficientes decimales guardan
una relación de diseño, se redondea uno solo y los demás se calculan a
partir de él, para que la relación se conserve exactamente:

| Filtro | Relación | Qué garantiza |
|---|---|---|
| Pasa-altos | `b2 = b0`, `b1 = −2·b0` | `b0 + b1 + b2 = 0`: elimina por completo la componente continua |
| Pasa-banda | `b1 = 0`, `b2 = −b0` | cero exacto en 0 Hz y en Nyquist |
| Peaking | `a1 = b1` | respuesta plana exacta a 0 dB de ganancia |

Con esto, el error de respuesta del pasa-altos a 44,1 kHz bajó de −51,9 dB
(redondeando cada coeficiente por separado) a −65,8 dB. Todas las etapas
siguen siendo estables; el low-shelf a 44,1 kHz pasa de radio 0,983189 a
0,983196.

Etapas activas (las demás son identidad: `b0 = 32768` = `08000`, resto 0).
Cada celda muestra el entero y su hexadecimal de 18 bits:

| fs (Hz) | Filtro | Etapa | b0 | b1 | b2 | a1 | a2 |
|---:|---|---:|---:|---:|---:|---:|---:|
| 8000 | 0 (pasa-altos) | 0 | 20937 (`051C9`) | -41874 (`35C6E`) | 20937 (`051C9`) | -37453 (`36DB3`) | 13527 (`034D7`) |
| 8000 | 1 (pasa-banda) | 0 | 17206 (`04336`) | 0 (`00000`) | -17206 (`3BCCA`) | -22876 (`3A6A4`) | -1645 (`3F993`) |
| 8000 | 2 (ecualizador) | 0 | 17066 (`042AA`) | -29652 (`38C2C`) | 13109 (`03335`) | -59423 (`317E1`) | 27179 (`06A2B`) |
| 8000 | 2 (ecualizador) | 1 | 29936 (`074F0`) | -32630 (`3808A`) | 16209 (`03F51`) | -32630 (`3808A`) | 13378 (`03442`) |
| 8000 | 2 (ecualizador) | 2 | 37014 (`09096`) | 30983 (`07907`) | 11040 (`02B20`) | 34133 (`08555`) | 12136 (`02F68`) |
| 16000 | 0 (pasa-altos) | 0 | 26234 (`0667A`) | -52468 (`3330C`) | 26234 (`0667A`) | -51151 (`33831`) | 21016 (`05218`) |
| 16000 | 1 (pasa-banda) | 0 | 11425 (`02CA1`) | 0 (`00000`) | -11425 (`3D35F`) | -39758 (`364B2`) | 9918 (`026BE`) |
| 16000 | 2 (ecualizador) | 0 | 16742 (`04166`) | -31278 (`385D2`) | 14672 (`03950`) | -62475 (`30BF5`) | 29844 (`07494`) |
| 16000 | 2 (ecualizador) | 1 | 30995 (`07913`) | -49329 (`33F4F`) | 22399 (`0577F`) | -49329 (`33F4F`) | 20626 (`05092`) |
| 16000 | 2 (ecualizador) | 2 | 43507 (`0A9F3`) | -25562 (`39C26`) | 10149 (`027A5`) | -10945 (`3D53F`) | 6271 (`0187F`) |
| 44100 | 0 (pasa-altos) | 0 | 30230 (`07616`) | -60460 (`313D4`) | 30230 (`07616`) | -60264 (`31498`) | 27890 (`06CF2`) |
| 44100 | 1 (pasa-banda) | 0 | 5291 (`014AB`) | 0 (`00000`) | -5291 (`3EB55`) | -54452 (`32B4C`) | 22185 (`056A9`) |
| 44100 | 2 (ecualizador) | 0 | 16538 (`0409A`) | -32284 (`381E4`) | 15765 (`03D95`) | -64425 (`30457`) | 31676 (`07BBC`) |
| 44100 | 2 (ecualizador) | 1 | 32023 (`07D17`) | -59824 (`31650`) | 28413 (`06EFD`) | -59824 (`31650`) | 27668 (`06C14`) |
| 44100 | 2 (ecualizador) | 2 | 48504 (`0BD78`) | -71229 (`2E9C3`) | 28262 (`06E66`) | -43920 (`35470`) | 16690 (`04132`) |

Si los registros del bus son de 32 bits, el software escribe el valor
extendido en signo (por ejemplo, −71229 como `FFFEE9C3`) y el hardware toma
los 18 bits de abajo. La tabla completa, con la versión de 32 bits, se
genera con `python dsp/model/fixed_coefficients.py`.

---

## 7. Vectores de prueba

`python dsp/model/generate_vectors.py` genera en `dsp/vectors/<fs>/<modo>/`
los archivos `coefs.hex`, `input.hex` y `expected.hex` para las 3 frecuencias
de muestreo y los 4 modos (pasa-altos, pasa-banda, ecualizador y bypass).
Cada caso tiene 3700 muestras con impulso, escalones, senos, valores
extremos (que provocan saturación), chirp, ruido y silencio final.

El formato, el orden de los coeficientes y la posición de cada señal están
en [`dsp/vectors/README.md`](../../dsp/vectors/README.md). Los archivos
están listos para `$readmemh`.

Las pruebas de `dsp/tests/test_vectors.py` recalculan `expected.hex` con el
modelo a partir del `input.hex` del repositorio: si el modelo o los
coeficientes cambian sin regenerar los vectores, fallan.

---

## 8. Verificación del modelo

`pytest dsp` ejecuta 336 pruebas. Las de esta fase revisan:

| Archivo | Qué verifica |
|---|---|
| `test_fixed_point.py` | redondeo (negativos y empates), saturación, conversión decimal ↔ punto fijo, hexadecimal en complemento a dos |
| `test_fixed_coefficients.py` | rango de 18 bits, relaciones de diseño exactas, estabilidad y respuesta tras cuantizar |
| `test_fixed_model.py` | cercanía al flotante (≤ 1 LSB con 24 bits), identidad y bypass exactos, saturación sin "dar la vuelta", acumulador sin desborde con entradas extremas, retorno exacto a 0 en silencio, canales independientes |
| `test_vectors.py` | vectores completos, en formato correcto y coincidentes con el modelo actual |

---

## 9. Cómo reproducir los resultados

```bash
source scripts/dsp/setup-env.sh

pytest dsp                                      # todas las pruebas
python dsp/model/fixed_point.py                 # formatos y ejemplos de redondeo
python dsp/model/fixed_coefficients.py          # coeficientes enteros y estabilidad
python dsp/model/fixed_model.py                 # demostración del modelo
python dsp/model/measure_fixed.py               # medición de 16 contra 24 bits
python dsp/model/measure_fixed.py --wav dsp/audio/cancion.wav   # escuchar el modelo
python dsp/model/generate_vectors.py            # regenerar los vectores
```

| Archivo | Contenido |
|---|---|
| `dsp/model/fixed_point.py` | formatos Q, redondeo, saturación y hexadecimal |
| `dsp/model/fixed_coefficients.py` | cuantización de coeficientes a Q3.15 |
| `dsp/model/fixed_model.py` | modelo bit-exacto: etapa, cascada, bypass y realimentación del error |
| `dsp/model/measure_fixed.py` | medición de error y SNR; filtrado de WAV con el modelo |
| `dsp/model/generate_vectors.py` | generador de los vectores de prueba |
| `dsp/vectors/` | vectores de prueba para el testbench |
