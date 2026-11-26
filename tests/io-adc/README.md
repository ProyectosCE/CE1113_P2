# Prueba de botones, switches y ADC

Verifica las entradas del reproductor:

| Entrada | Cómo se prueba | Qué se espera |
|---|---|---|
| KEY[3:0] | Interrupción por flanco: PIO `keys` → `f2h_irq0[1]` → GIC ID 73 | Cada pulsación imprime `KEYn (interrupciones: N)`, una sola vez por pulsación |
| SW[9:0] | Sondeo | LEDR[9:0] copia los switches; cada cambio se imprime |
| ADC canal 0 | Auto-update del ADC Controller | Al girar el potenciómetro, `ADC0` va de ~0 a ~3300 (con 3.3 V en el extremo) |

`start.S` es el arranque mínimo con interrupciones: tabla de vectores en `VBAR`, pila de modo IRQ y
entrada de IRQ hacia `irq_handler()`. El GIC se configura en `main.c` (distribuidor en
`0xFFFED000`, interfaz de CPU en `0xFFFEC100`).

## Conexión del potenciómetro

| Pata del potenciómetro de 10 kΩ | Va a |
|---|---|
| Extremo 1 | **GND** (en el conector del ADC o en un GPIO) |
| **Central (cursor)** | **CH0** (`ADC_IN0`) del conector del ADC |
| Extremo 2 | **3.3 V** (de un conector GPIO, JP1 o JP2) |

```
  3.3 V ──────┐
              █  ← potenciómetro 10 kΩ
  CH0 ───────►█  (pata central = cursor)
              █
  GND ────────┘
```

Ubique `ADC_IN0` y GND en la figura del conector del ADC del manual de Terasic, y el pin de 3.3 V
en la figura de los GPIO (en el estándar de Terasic de 40 pines, el 29 es 3.3 V y el 30 es GND;
**confírmelo** en el manual de su placa). Haga las conexiones con la placa **apagada**.

Seguridad:

- **El cursor (pata central) nunca va a la alimentación.** Si 3.3 V entra por el cursor y un
  extremo va a GND, al girar el potenciómetro hasta ese extremo queda un cortocircuito directo.
- Use **3.3 V, no 5 V**. El LTC2308 se alimenta con 5 V, así que 3.3 V en su entrada es seguro y
  queda dentro de su rango de medición (0–4.096 V). Con 5 V la lectura se saturaría en 4095.
- Con los extremos bien conectados, por el potenciómetro circulan solo 3.3 V / 10 kΩ ≈ 0.33 mA, en
  cualquier posición del cursor.
- Opcional: una resistencia de ~1 kΩ entre el cursor y CH0 limita la corriente si algo se conecta
  mal. No cambia la lectura, porque la entrada del ADC casi no consume corriente.

Lectura esperada: girando de un extremo al otro, `ADC0` va de ~0 a ~3300 (3.3 V / 4.096 V × 4095).

## Pasos

Requisitos: FPGA programada con el sistema de `Reproductor/` (`make hw && make prog`) y el
potenciómetro conectado (ver *Conexión del potenciómetro*). Sin potenciómetro, los KEY y los
switches se prueban igual; para el ADC basta un jumper de CH0 a GND (~0) o a 3.3 V (~3300).

```bash
# Compilar
cd tests/io-adc
arm-none-eabi-gcc -mcpu=cortex-a9 -marm -O1 -g -nostdlib -ffreestanding \
    -T ../inc0-hps/ocram.ld start.S main.c -o io-adc.elf

# Terminal 1: gdb-server
../../scripts/hps/gdb-server.sh

# Terminal 2: cargar y ejecutar
gdb-multiarch -x ../inc0-hps/cargar.gdb io-adc.elf
(gdb) continue

# Terminal 3: consola JTAG UART
../../scripts/general/terminal.sh
```

## Si algo falla

| Síntoma | Causa probable |
|---|---|
| Los LEDs siguen los switches pero los KEY no imprimen nada | La IRQ no llega: revisar que `keys.irq` esté en `f2h_irq0` con número 1 y que *Generate IRQ* esté activo. En gdb: `x/x 0xFF20005C` (edge capture) debe cambiar al pulsar |
| Un KEY imprime muchas veces seguidas | El edge capture no se limpia: revisar *Enable bit-clearing for edge capture register* |
| `ADC0` fijo en 0 o en 4095 | Variante del ADC equivocada (AD7928 en vez de LTC2308), pines del ADC o cableado del potenciómetro |
| El programa se cuelga al pulsar un KEY | La IRQ llega pero el vector no: revisar que el `.elf` se haya compilado con `start.S` de esta carpeta |

## Resultados

(llenar al probar)
