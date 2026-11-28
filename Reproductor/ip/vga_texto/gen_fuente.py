#!/usr/bin/env python3
"""
Genera vga_fuente.sv: la ROM de caracteres (256 x 8x16) de vga_texto.

Fuente base: "Misc Fixed" 8x16 de X11 (dominio publico), archivo koi8x16.pcf del paquete
xfonts-cyrillic. Solo se usan los caracteres ASCII 0x20-0x7E. A partir de ellos se arman:
  - Letras del espanol en Latin-1: a e i o u con tilde (minusculas y mayusculas), n con
    virgulilla, u con dieresis, signos de apertura de pregunta y exclamacion.
  - Simbolos propios en 0x01-0x0F (ver SIMBOLOS).

No hace falta correrlo para compilar: vga_fuente.sv ya esta generado en el repositorio.
Uso:  python3 gen_fuente.py ruta/a/koi8x16.pcf > vga_fuente.sv
"""
import sys
from PIL import PcfFontFile

ruta = sys.argv[1] if len(sys.argv) > 1 else "koi8x16.pcf"
fuente = PcfFontFile.PcfFontFile(open(ruta, "rb"))


def glifo(c):
    im = fuente.glyph[ord(c)][3]
    return [sum((1 << (7 - x)) for x in range(8) if im.getpixel((x, y))) for y in range(16)]


rom = [[0] * 16 for _ in range(256)]
for c in range(0x20, 0x7F):
    rom[c] = glifo(chr(c))


def desde_dibujo(dibujo):
    filas = [f for f in dibujo.strip("\n").split("\n")]
    assert len(filas) == 16, len(filas)
    return [int(f.replace(".", "0").replace("#", "1"), 2) for f in filas]


# Acentos: filas (desplazamiento, patron)
AGUDO = [0b00001000, 0b00010000]
DIERESIS = [0b00100100]
TILDE_N = [0b00110010, 0b01001100]


def con_marca(base, marca, fila):
    g = list(rom[ord(base)])
    if base == "i":                     # i sin punto antes de poner la tilde
        g[3] = g[4] = 0
    for k, p in enumerate(marca):
        g[fila + k] |= p
    return g


for base, cod in zip("aeiou", (0xE1, 0xE9, 0xED, 0xF3, 0xFA)):
    rom[cod] = con_marca(base, AGUDO, 3)
for base, cod in zip("AEIOU", (0xC1, 0xC9, 0xCD, 0xD3, 0xDA)):
    rom[cod] = con_marca(base, AGUDO, 1)
rom[0xF1] = con_marca("n", TILDE_N, 3)          # n con virgulilla
rom[0xD1] = con_marca("N", TILDE_N, 1)
rom[0xFC] = con_marca("u", DIERESIS, 4)
rom[0xDC] = con_marca("U", DIERESIS, 2)
# Signos de apertura: el de cierre de cabeza (filas 4-13 invertidas, bits espejados)
espejo = lambda b: int(f"{b:08b}"[::-1], 2)
for cierre, cod in (("?", 0xBF), ("!", 0xA1)):
    g = rom[ord(cierre)]
    nuevo = [0] * 16
    for y in range(4, 14):
        nuevo[4 + 13 - y] = espejo(g[y])
    rom[cod] = nuevo

SIMBOLOS = {
    0x01: "lleno",      # bloque completo (barras)
    0x02: "play",
    0x03: "pausa",
    0x04: "stop",
    0x05: "vacio",      # parte vacia de una barra
    0x06: "horiz",      # linea horizontal
    0x07: "nota",       # nota musical
    0x08: "flecha",     # flecha a la derecha (seleccion)
}
dibujos = {
"lleno": "\n".join(["########"] * 16),
"vacio": "\n".join(["........", "........", "........", "........", "........", "........",
                     ".#.#.#.#", "........", ".#.#.#.#", "........",
                     "........", "........", "........", "........", "........", "........"]),
"horiz": "\n".join(["........"] * 7 + ["########"] + ["........"] * 8),
"play": """
........
........
........
.#......
.##.....
.###....
.####...
.#####..
.######.
.#####..
.####...
.###....
.##.....
.#......
........
........""",
"pausa": """
........
........
........
.##..##.
.##..##.
.##..##.
.##..##.
.##..##.
.##..##.
.##..##.
.##..##.
.##..##.
.##..##.
.##..##.
........
........""",
"stop": """
........
........
........
........
.######.
.######.
.######.
.######.
.######.
.######.
.######.
.######.
.######.
........
........
........""",
"nota": """
........
........
........
...####.
...#..#.
...#..#.
...#..#.
...#..#.
...#..#.
...#..#.
.###.##.
####.###
.##...#.
........
........
........""",
"flecha": """
........
........
........
........
...#....
...##...
...###..
######..
#######.
######..
...###..
...##...
...#....
........
........
........""",
}
for cod, nombre in SIMBOLOS.items():
    rom[cod] = desde_dibujo(dibujos[nombre])

print("// GENERADO por gen_fuente.py - no editar a mano.")
print("// ROM de caracteres de vga_texto: 256 caracteres de 8x16 pixeles.")
print("// Direccion = {codigo[7:0], fila[3:0]}; bit 7 = pixel de la izquierda.")
print("// Base: fuente \"Misc Fixed\" 8x16 de X11 (dominio publico).")
print("module vga_fuente (")
print("    input  logic        clk,")
print("    input  logic        en,")
print("    input  logic [11:0] addr,")
print("    output logic [7:0]  q")
print(");")
print("    always_ff @(posedge clk) begin")
print("        if (en) begin")
print("            case (addr)")
for c in range(256):
    for y in range(16):
        if rom[c][y]:
            print(f"                12'h{(c << 4) | y:03X}: q <= 8'h{rom[c][y]:02X};")
print("                default: q <= 8'h00;")
print("            endcase")
print("        end")
print("    end")
print("endmodule")
