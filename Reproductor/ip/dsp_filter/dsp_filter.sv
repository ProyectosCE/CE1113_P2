// dsp_filter - filtro de audio en hardware propio (esclavo Avalon-MM).
//
// ESQUELETO: la interfaz de registros esta completa, pero el procesamiento todavia no esta
// implementado: la muestra de entrada pasa sin cambios a la salida. El filtro real (por ejemplo
// un FIR de NUM_COEF coeficientes con multiplicador-acumulador) reemplaza el bloque marcado
// "PROCESAMIENTO" sin cambiar el mapa de registros.
//
// Uso desde el ARM, por muestra:
//   1. escribir la muestra en DATA_IN
//   2. esperar STATUS.LISTO = 1
//   3. leer DATA_OUT
//
// Mapa de registros (offset en bytes, palabras de 32 bits):
//   0x00 CTRL      RW  bit 0 EN    : 1 = filtrar, 0 = bypass (la muestra pasa sin cambios)
//                      bit 1 LIMPIAR: escribir 1 borra el estado interno del filtro
//                                     (lineas de retardo); se lee siempre como 0
//                      bit 2 CANAL : canal de la proxima muestra (0 = izquierdo, 1 = derecho);
//                                     cada canal tendra su propio estado
//   0x04 STATUS    R   bit 0 LISTO : DATA_OUT tiene el resultado de la ultima muestra escrita
//                      bit 1 OCUPADO: el filtro esta procesando
//   0x08 DATA_IN   W   bits 15:0 muestra de 16 bits con signo; escribirla inicia el procesamiento
//                  R   ultima muestra escrita
//   0x0C DATA_OUT  R   bits 15:0 resultado (16 bits con signo, extendido a 32 bits)
//   0x10 COEF_IDX  RW  indice del coeficiente (0 .. NUM_COEF-1)
//   0x14 COEF_DATA RW  coeficiente en formato Q1.15 en la posicion COEF_IDX
//   0x18 INFO      R   bits 31:16 ID = 0xD5F1, bits 15:8 version, bits 7:0 NUM_COEF
//   0x1C           R   0 (reservado)
module dsp_filter #(
    parameter int NUM_COEF = 16
) (
    input  logic        clk,
    input  logic        reset,

    input  logic [2:0]  avs_address,
    input  logic        avs_read,
    output logic [31:0] avs_readdata,     // latencia de lectura fija de 1 ciclo
    input  logic        avs_write,
    input  logic [31:0] avs_writedata
);

    localparam logic [15:0] ID      = 16'hD5F1;
    localparam logic [7:0]  VERSION = 8'h01;   // 0x01 = esqueleto (paso directo)
    localparam logic [7:0]  NCOEF8  = NUM_COEF;

    typedef enum logic [2:0] {
        R_CTRL      = 3'd0,
        R_STATUS    = 3'd1,
        R_DATA_IN   = 3'd2,
        R_DATA_OUT  = 3'd3,
        R_COEF_IDX  = 3'd4,
        R_COEF_DATA = 3'd5,
        R_INFO      = 3'd6
    } registro_t;

    logic               en;
    logic               canal;
    logic signed [15:0] data_in;
    logic signed [15:0] data_out;
    logic               listo;
    logic               ocupado;
    logic        [7:0]  coef_idx;
    logic signed [15:0] coef [0:NUM_COEF-1];

    logic escribe_dato, coef_valido;
    assign escribe_dato = avs_write && (avs_address == R_DATA_IN);
    assign coef_valido  = (coef_idx < NUM_COEF);

    // ---------------- Escritura de registros ----------------
    always_ff @(posedge clk) begin
        if (reset) begin
            en       <= 1'b0;
            canal    <= 1'b0;
            data_in  <= '0;
            coef_idx <= '0;
            for (int i = 0; i < NUM_COEF; i++)
                coef[i] <= '0;
        end else if (avs_write) begin
            case (avs_address)
                R_CTRL: begin
                    en    <= avs_writedata[0];
                    canal <= avs_writedata[2];
                    // avs_writedata[1] (LIMPIAR): sin efecto en el esqueleto, no hay estado
                end
                R_DATA_IN:   data_in  <= avs_writedata[15:0];
                R_COEF_IDX:  coef_idx <= avs_writedata[7:0];
                R_COEF_DATA: if (coef_valido) coef[coef_idx] <= avs_writedata[15:0];
                default: ;
            endcase
        end
    end

    // ---------------- PROCESAMIENTO (esqueleto: paso directo) ----------------
    // En el mismo flanco en que se escribe DATA_IN, LISTO baja y OCUPADO sube (asi una lectura
    // de STATUS justo despues de la escritura nunca ve el LISTO de la muestra anterior). Al ciclo
    // siguiente DATA_OUT tiene el resultado y LISTO sube. El filtro real puede tardar mas ciclos
    // manteniendo OCUPADO = 1 hasta terminar.
    always_ff @(posedge clk) begin
        if (reset) begin
            data_out <= '0;
            listo    <= 1'b0;
            ocupado  <= 1'b0;
        end else if (escribe_dato) begin
            listo   <= 1'b0;
            ocupado <= 1'b1;
        end else if (ocupado) begin
            data_out <= data_in;          // en el filtro real: resultado si en = 1, data_in si en = 0
            ocupado  <= 1'b0;
            listo    <= 1'b1;
        end
    end

    // ---------------- Lectura de registros (1 ciclo de latencia) ----------------
    always_ff @(posedge clk) begin
        if (reset)
            avs_readdata <= '0;
        else if (avs_read) begin
            case (avs_address)
                R_CTRL:      avs_readdata <= {29'd0, canal, 1'b0, en};
                R_STATUS:    avs_readdata <= {30'd0, ocupado, listo};
                R_DATA_IN:   avs_readdata <= {{16{data_in[15]}}, data_in};
                R_DATA_OUT:  avs_readdata <= {{16{data_out[15]}}, data_out};
                R_COEF_IDX:  avs_readdata <= {24'd0, coef_idx};
                R_COEF_DATA: avs_readdata <= coef_valido ? {{16{coef[coef_idx][15]}}, coef[coef_idx]} : '0;
                R_INFO:      avs_readdata <= {ID, VERSION, NCOEF8};
                default:     avs_readdata <= '0;
            endcase
        end
    end

endmodule
