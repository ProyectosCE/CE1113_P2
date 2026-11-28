// vga_texto - controlador VGA de texto para la DE1-SoC (esclavo Avalon-MM).
//
// Pantalla de 80 x 30 caracteres de 8x16 pixeles a 640x480 y ~60 Hz. Cada celda tiene un
// caracter (fuente en vga_fuente.sv) y un color de letra y de fondo (paleta de 16 colores).
// El software solo escribe celdas; el hardware genera la imagen y las senales del ADV7123.
//
// Mapa de registros (palabras de 32 bits; offset en bytes = 4 * palabra):
//   palabra 0 .. 2399  CELDA  W   celda (fila * 80 + columna):
//                                 bits 7:0  codigo del caracter
//                                 bits 11:8 color de la letra   (paleta)
//                                 bits 15:12 color del fondo    (paleta)
//   palabra 4095       CTRL   W   bit 0: 1 = video encendido (valor al salir de reset), 0 = negro
//                             R   ID: bits 31:16 = 0x5647 ("VG"), 15:8 = columnas (80),
//                                 7:0 = filas (30). Cualquier otra direccion tambien lee el ID.
//
// Paleta (tipo CGA): 0 negro, 1 azul, 2 verde, 3 cian, 4 rojo, 5 magenta, 6 cafe, 7 gris claro,
//   8 gris oscuro, 9 azul claro, 10 verde claro, 11 cian claro, 12 rojo claro, 13 magenta claro,
//   14 amarillo, 15 blanco.
//
// Reloj: clk debe ser de 50 MHz; el pixel avanza cada 2 ciclos (25 MHz). vga_clk sube a la mitad
// de cada pixel, que es cuando el ADV7123 toma los datos.
module vga_texto (
    input  logic        clk,
    input  logic        reset,

    input  logic [11:0] avs_address,
    input  logic        avs_read,
    output logic [31:0] avs_readdata,     // latencia de lectura fija de 1 ciclo
    input  logic        avs_write,
    input  logic [31:0] avs_writedata,

    output logic [7:0]  vga_r,
    output logic [7:0]  vga_g,
    output logic [7:0]  vga_b,
    output logic        vga_hs,
    output logic        vga_vs,
    output logic        vga_clk,
    output logic        vga_blank_n,
    output logic        vga_sync_n
);

    localparam int COLUMNAS = 80;
    localparam int FILAS    = 30;
    localparam int CELDAS   = COLUMNAS * FILAS;               // 2400
    localparam logic [31:0] ID = {16'h5647, 8'(COLUMNAS), 8'(FILAS)};
    localparam logic [11:0] DIR_CTRL = 12'hFFF;

    // 640x480 @ 60 Hz: visible, frente, sincronia, fondo
    localparam int H_VIS = 640, H_FP = 16, H_SYNC = 96, H_BP = 48;
    localparam int V_VIS = 480, V_FP = 10, V_SYNC = 2,  V_BP = 33;
    localparam int H_TOTAL = H_VIS + H_FP + H_SYNC + H_BP;   // 800
    localparam int V_TOTAL = V_VIS + V_FP + V_SYNC + V_BP;   // 525

    // ---------------- Avalon ----------------
    logic encendido;
    logic [15:0] texto [0:CELDAS-1];

    always_ff @(posedge clk) begin
        if (reset)
            encendido <= 1'b1;
        else if (avs_write && avs_address == DIR_CTRL)
            encendido <= avs_writedata[0];
    end

    always_ff @(posedge clk) begin
        if (avs_write && avs_address < 12'(CELDAS))
            texto[avs_address] <= avs_writedata[15:0];
    end

    always_ff @(posedge clk)
        avs_readdata <= ID;

    // ---------------- Barrido ----------------
    logic       px_en;                    // 1 de cada 2 ciclos: un pixel
    logic [9:0] hx, vy;

    always_ff @(posedge clk) begin
        if (reset)
            px_en <= 1'b0;
        else
            px_en <= ~px_en;
    end

    always_ff @(posedge clk) begin
        if (reset) begin
            hx <= '0;
            vy <= '0;
        end else if (px_en) begin
            if (hx == 10'(H_TOTAL - 1)) begin
                hx <= '0;
                vy <= (vy == 10'(V_TOTAL - 1)) ? '0 : vy + 10'd1;
            end else begin
                hx <= hx + 10'd1;
            end
        end
    end

    logic visible, hs, vs;
    assign visible = (hx < 10'(H_VIS)) && (vy < 10'(V_VIS));
    assign hs = ~((hx >= 10'(H_VIS + H_FP)) && (hx < 10'(H_VIS + H_FP + H_SYNC)));
    assign vs = ~((vy >= 10'(V_VIS + V_FP)) && (vy < 10'(V_VIS + V_FP + V_SYNC)));

    // Celda del pixel actual: fila * 80 + columna = fila * 64 + fila * 16 + columna
    logic [6:0]  col;
    logic [4:0]  fila;
    logic [11:0] dir_celda;
    assign col  = hx[9:3];
    assign fila = vy[8:4];
    assign dir_celda = visible ? ({1'b0, fila, 6'b0} + {3'b0, fila, 4'b0} + {5'b0, col}) : 12'd0;

    // ---------------- Tuberia (avanza con px_en) ----------------
    // Etapa 1: leer la celda.     Etapa 2: leer la fila del caracter.     Etapa 3: color.
    logic [15:0] celda;
    logic [2:0]  x1, x2;
    logic [3:0]  y1;
    logic [7:0]  color1;
    logic [7:0]  color2;
    logic        vis1, vis2, hs1, hs2, vs1, vs2;
    logic [7:0]  pixeles;

    always_ff @(posedge clk) begin
        if (px_en)
            celda <= texto[dir_celda];
    end

    always_ff @(posedge clk) begin
        if (reset) begin
            {vis1, vis2} <= '0;
            {hs1, hs2, vs1, vs2} <= '1;
        end else if (px_en) begin
            x1 <= hx[2:0];   y1 <= vy[3:0];   vis1 <= visible; hs1 <= hs; vs1 <= vs;
            x2 <= x1;        color2 <= color1; vis2 <= vis1;   hs2 <= hs1; vs2 <= vs1;
        end
    end
    assign color1 = celda[15:8];

    vga_fuente fuente (
        .clk  (clk),
        .en   (px_en),
        .addr ({celda[7:0], y1}),
        .q    (pixeles)
    );

    // Paleta
    function automatic logic [23:0] paleta(input logic [3:0] i);
        case (i)
            4'd0:  paleta = 24'h000000;
            4'd1:  paleta = 24'h0000AA;
            4'd2:  paleta = 24'h00AA00;
            4'd3:  paleta = 24'h00AAAA;
            4'd4:  paleta = 24'hAA0000;
            4'd5:  paleta = 24'hAA00AA;
            4'd6:  paleta = 24'hAA5500;
            4'd7:  paleta = 24'hAAAAAA;
            4'd8:  paleta = 24'h555555;
            4'd9:  paleta = 24'h5555FF;
            4'd10: paleta = 24'h55FF55;
            4'd11: paleta = 24'h55FFFF;
            4'd12: paleta = 24'hFF5555;
            4'd13: paleta = 24'hFF55FF;
            4'd14: paleta = 24'hFFFF55;
            default: paleta = 24'hFFFFFF;
        endcase
    endfunction

    // Etapa 3: salida registrada
    logic        letra;
    logic [23:0] rgb;
    assign letra = pixeles[3'd7 - x2];
    assign rgb   = (vis2 && encendido) ? paleta(letra ? color2[3:0] : color2[7:4]) : 24'h000000;

    always_ff @(posedge clk) begin
        if (reset) begin
            {vga_r, vga_g, vga_b} <= '0;
            vga_hs      <= 1'b1;
            vga_vs      <= 1'b1;
            vga_blank_n <= 1'b0;
            vga_clk     <= 1'b0;
        end else begin
            vga_clk <= ~px_en;            // sube un ciclo despues de cambiar los datos
            if (px_en) begin
                {vga_r, vga_g, vga_b} <= rgb;
                vga_hs      <= hs2;
                vga_vs      <= vs2;
                vga_blank_n <= vis2;
            end
        end
    end

    assign vga_sync_n = 1'b0;             // sin sincronia en verde

endmodule
