# Vectores de prueba del filtro DSP

Archivo generado con `python dsp/model/generate_vectors.py`. No editar a mano:
si cambia el modelo o los coeficientes, se regeneran con ese comando.

## Organización

```text
dsp/vectors/<fs>/<modo>/
├── coefs.hex      15 coeficientes de 18 bits (5 dígitos hex)
├── input.hex      3200 muestras de entrada de 16 bits (4 dígitos hex)
└── expected.hex   3200 muestras de salida esperada de 16 bits
```

- `<fs>`: 8000, 16000, 44100
- `<modo>`: highpass, bandpass, equalizer, bypass

Todos los valores están en complemento a dos, uno por línea, listos para
`$readmemh`. Ejemplo: `FFFF` = -1 en 16 bits; `3FFFF` = -1 en 18 bits.

## Coeficientes

Formato Q3.15 (18 bits). Orden de las 15 líneas de `coefs.hex`:

```text
etapa 0: b0 b1 b2 a1 a2
etapa 1: b0 b1 b2 a1 a2
etapa 2: b0 b1 b2 a1 a2
```

En el modo `bypass` se cargan los coeficientes del ecualizador con el bypass
activo; la salida esperada debe ser igual a la entrada.

## Configuración del modelo

- Muestras de entrada y salida: 16 bits, Q1.15.
- Estado entre etapas: 24 bits.
- Realimentación del error de redondeo activada.
- El filtro se reinicia (estado en cero) una sola vez, antes de la primera
  muestra; todas las señales se procesan seguidas.

## Señales de entrada

Las mismas en todos los casos, en este orden (índices de muestra):

| Muestras | Señal | Descripción |
|---|---|---|
| 0 – 299 | `impulso` | un impulso de 0.5 seguido de ceros |
| 300 – 599 | `escalon_pos` | escalón de +0.5 |
| 600 – 899 | `escalon_neg` | escalón de -0.5 |
| 900 – 1199 | `seno_grave` | seno de 100 Hz, amplitud 0.5 |
| 1200 – 1499 | `seno_medio` | seno de 1 kHz, amplitud 0.5 |
| 1500 – 1799 | `seno_agudo` | seno de 0.35*fs, amplitud 0.5 |
| 1800 – 1999 | `extremos` | +32767 y -32768 constantes y alternados (saturación) |
| 2000 – 2399 | `chirp` | barrido de 20 Hz a 0.45*fs, amplitud 0.5 |
| 2400 – 2699 | `ruido` | ruido uniforme de amplitud 0.5, semilla 1234 |
| 2700 – 3199 | `silencio` | ceros: la salida debe volver a 0 |
