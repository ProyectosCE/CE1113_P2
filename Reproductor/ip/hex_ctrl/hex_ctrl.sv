// hex_ctrl - controlador de los displays de 7 segmentos de la DE1-SoC (esclavo Avalon-MM).
//
// El software escribe el tiempo transcurrido (minutos y segundos en binario) y el numero de
// cancion; el hardware hace la conversion a decimal y a 7 segmentos.
//   HEX3 HEX2 : minutos (00-99)      HEX1 HEX0 : segundos (00-59)
//   HEX5 HEX4 : numero de cancion (00-99)
//
// Mapa de registros (offset en bytes, palabras de 32 bits):
//   0x0 CTRL    RW  bit 0 EN_TIEMPO  : 1 = HEX3-0 muestran el tiempo, 0 = apagados
//                   bit 1 EN_CANCION : 1 = HEX5-4 muestran la cancion, 0 = apagados
//   0x4 TIEMPO  RW  bits 14:8 minutos, bits 5:0 segundos (binario)
//   0x8 CANCION RW  bits 6:0 numero de cancion (binario)
//   0xC STATUS  R   bit 0 FUERA_RANGO: el ultimo valor escrito tenia minutos > 99,
//                         segundos > 59 o cancion > 99 (el display muestra el valor saturado)
//                   bits 31:16 ID del modulo = 0x4E58
//
// Displays activos en bajo: segmento encendido = 0. Orden de bits: {g, f, e, d, c, b, a}.
module hex_ctrl (
    input  logic        clk,
    input  logic        reset,

    input  logic [1:0]  avs_address,
    input  logic        avs_read,
    output logic [31:0] avs_readdata,     // latencia de lectura fija de 1 ciclo
    input  logic        avs_write,
    input  logic [31:0] avs_writedata,

    output logic [6:0]  hex0,
    output logic [6:0]  hex1,
    output logic [6:0]  hex2,
    output logic [6:0]  hex3,
    output logic [6:0]  hex4,
    output logic [6:0]  hex5
);

    localparam logic [15:0] ID      = 16'h4E58;
    localparam logic [6:0]  APAGADO = 7'b1111111;

    typedef enum logic [1:0] {
        R_CTRL    = 2'd0,
        R_TIEMPO  = 2'd1,
        R_CANCION = 2'd2,
        R_STATUS  = 2'd3
    } registro_t;

    logic [1:0] ctrl;
    logic [6:0] minutos;
    logic [5:0] segundos;
    logic [6:0] cancion;
    logic       fuera_rango;

    // Campos de la escritura
    logic [6:0] wr_min, wr_can;
    logic [5:0] wr_seg;
    assign wr_min = avs_writedata[14:8];
    assign wr_seg = avs_writedata[5:0];
    assign wr_can = avs_writedata[6:0];

    // ---------------- Escritura de registros ----------------
    always_ff @(posedge clk) begin
        if (reset) begin
            ctrl        <= '0;
            minutos     <= '0;
            segundos    <= '0;
            cancion     <= '0;
            fuera_rango <= 1'b0;
        end else if (avs_write) begin
            unique case (avs_address)
                R_CTRL: ctrl <= avs_writedata[1:0];
                R_TIEMPO: begin
                    minutos     <= (wr_min > 7'd99) ? 7'd99 : wr_min;
                    segundos    <= (wr_seg > 6'd59) ? 6'd59 : wr_seg;
                    fuera_rango <= (wr_min > 7'd99) || (wr_seg > 6'd59);
                end
                R_CANCION: begin
                    cancion     <= (wr_can > 7'd99) ? 7'd99 : wr_can;
                    fuera_rango <= (wr_can > 7'd99);
                end
                R_STATUS: ;   // solo lectura
            endcase
        end
    end

    // ---------------- Lectura de registros (1 ciclo de latencia) ----------------
    always_ff @(posedge clk) begin
        if (reset)
            avs_readdata <= '0;
        else if (avs_read) begin
            unique case (avs_address)
                R_CTRL:    avs_readdata <= {30'd0, ctrl};
                R_TIEMPO:  avs_readdata <= {17'd0, minutos, 2'd0, segundos};
                R_CANCION: avs_readdata <= {25'd0, cancion};
                R_STATUS:  avs_readdata <= {ID, 15'd0, fuera_rango};
            endcase
        end
    end

    // ---------------- Binario (0-99) -> decimal -> 7 segmentos ----------------
    function automatic logic [6:0] seg7(input logic [3:0] d);
        unique case (d)
            4'd0:    return 7'b1000000;
            4'd1:    return 7'b1111001;
            4'd2:    return 7'b0100100;
            4'd3:    return 7'b0110000;
            4'd4:    return 7'b0011001;
            4'd5:    return 7'b0010010;
            4'd6:    return 7'b0000010;
            4'd7:    return 7'b1111000;
            4'd8:    return 7'b0000000;
            4'd9:    return 7'b0010000;
            default: return APAGADO;
        endcase
    endfunction

    // Cocientes y restos de valores <= 99: caben en 4 bits (se trunca el ancho intermedio)
    logic [3:0] min_dec, min_uni, seg_dec, seg_uni, can_dec, can_uni;

    always_comb begin
        min_dec = minutos / 7'd10;
        min_uni = minutos % 7'd10;
        seg_dec = segundos / 6'd10;
        seg_uni = segundos % 6'd10;
        can_dec = cancion / 7'd10;
        can_uni = cancion % 7'd10;

        hex0 = ctrl[0] ? seg7(seg_uni) : APAGADO;
        hex1 = ctrl[0] ? seg7(seg_dec) : APAGADO;
        hex2 = ctrl[0] ? seg7(min_uni) : APAGADO;
        hex3 = ctrl[0] ? seg7(min_dec) : APAGADO;
        hex4 = ctrl[1] ? seg7(can_uni) : APAGADO;
        hex5 = ctrl[1] ? seg7(can_dec) : APAGADO;
    end

endmodule
