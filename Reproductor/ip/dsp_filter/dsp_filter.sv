// dsp_filter - filtro de audio en hardware propio (esclavo Avalon-MM).
//
// Cascada de 3 biquads en Forma Directa I con una MAC secuencial (un solo multiplicador de
// 24 x 18 bits, 20 ciclos por muestra). Los tres filtros del reproductor (pasa-altos, pasa-banda
// y ecualizador) son este mismo hardware con distintos coeficientes. Reproduce bit a bit el
// modelo dsp/model/fixed_model.py. Especificacion: docs/dsp/especificacion-modulo.md
//
// Uso desde el ARM, por muestra:
//   1. escribir CTRL con EN y el CANAL de la muestra
//   2. escribir la muestra en DATA_IN
//   3. esperar STATUS.LISTO = 1
//   4. leer DATA_OUT
//
// Mapa de registros (offset en bytes, palabras de 32 bits):
//   0x00 CTRL      RW  bit 0 EN     : 1 = filtrar, 0 = bypass (la muestra pasa sin cambios y el
//                                     estado no se toca)
//                      bit 1 LIMPIAR: escribir 1 borra el estado de los dos canales y SATURO;
//                                     se lee siempre como 0
//                      bit 2 CANAL  : canal de la proxima muestra (0 = izquierdo, 1 = derecho)
//   0x04 STATUS    R   bit 0 LISTO  : DATA_OUT tiene el resultado de la ultima muestra escrita
//                      bit 1 OCUPADO: el filtro esta procesando
//                      bit 2 SATURO : alguna etapa saturo su salida; queda en 1 hasta que se
//                                     borra con LIMPIAR o al escribir COEF_DATA
//   0x08 DATA_IN   W   bits 15:0 muestra de 16 bits con signo; escribirla inicia el
//                      procesamiento. Si OCUPADO = 1 la escritura se descarta
//                  R   ultima muestra aceptada, extendida en signo a 32 bits
//   0x0C DATA_OUT  R   resultado de 16 bits con signo, extendido en signo a 32 bits
//   0x10 COEF_IDX  RW  bits 7:0 indice del coeficiente (validos: 0 .. 14)
//   0x14 COEF_DATA W   bits 17:0 coeficiente Q3.15 que se guarda en coef[COEF_IDX]; con indice
//                      valido tambien borra el estado de los dos canales y SATURO. Con indice
//                      de 15 o mas la escritura se ignora
//                  R   coef[COEF_IDX] extendido en signo a 32 bits (0 si el indice no es valido)
//   0x18 INFO      R   bits 31:16 ID = 0xD5F1, bits 15:8 version = 0x02, bits 7:0 NUM_COEF = 15
//   0x1C           R   0 (reservado)
//
// Coeficientes: indice = etapa*5 + paso, en el orden b0 b1 b2 a1 a2 de cada etapa (el mismo de
// dsp/vectors/<fs>/<modo>/coefs.hex). Al reset cada etapa es la identidad (b0 = 1.0, el resto 0).
module dsp_filter (
    input  logic        clk,
    input  logic        reset,            // sincrono, activo en alto

    input  logic [2:0]  avs_address,
    input  logic        avs_read,
    output logic [31:0] avs_readdata,     // latencia de lectura fija de 1 ciclo
    input  logic        avs_write,
    input  logic [31:0] avs_writedata
);

    localparam int          NUM_COEF = 15;     // 3 etapas x 5 coeficientes
    localparam logic [15:0] ID       = 16'hD5F1;
    localparam logic [7:0]  VERSION  = 8'h02;  // 0x01 = esqueleto, 0x02 = cascada de biquads
    localparam logic [7:0]  NCOEF8   = NUM_COEF[7:0];

    // Valor de reset del banco: cada etapa es la identidad. Elemento 0 = b0 de la etapa 0.
    localparam logic [4:0][17:0] ETAPA_IDENTIDAD =
        {18'h00000, 18'h00000, 18'h00000, 18'h00000, 18'h08000};   // a2 a1 b2 b1 b0 (b0 = 1.0)
    localparam logic [NUM_COEF-1:0][17:0] COEF_IDENTIDAD = {3{ETAPA_IDENTIDAD}};

    typedef enum logic [2:0] {
        R_CTRL      = 3'd0,
        R_STATUS    = 3'd1,
        R_DATA_IN   = 3'd2,
        R_DATA_OUT  = 3'd3,
        R_COEF_IDX  = 3'd4,
        R_COEF_DATA = 3'd5,
        R_INFO      = 3'd6
    } registro_t;

    // ---------------- Registros que ve el ARM ----------------
    logic                       en;
    logic                       canal;
    logic signed [15:0]         data_in;
    logic signed [15:0]         data_out;
    logic                       listo;
    logic                       ocupado;
    logic                       saturo;
    logic        [7:0]          coef_idx;
    logic [NUM_COEF-1:0][17:0]  coef;           // banco de coeficientes Q3.15

    logic        coef_valido;     // COEF_IDX apunta a uno de los 15 coeficientes
    logic [3:0]  idx;             // COEF_IDX recortado para indexar el banco
    logic [17:0] coef_sel;        // coeficiente que se lee por COEF_DATA
    logic        acepta_dato;     // escritura de DATA_IN que inicia una muestra
    logic        borrar_estado;   // LIMPIAR o COEF_DATA con indice valido

    assign coef_valido   = (coef_idx < NCOEF8);
    assign idx           = coef_idx[3:0];
    assign coef_sel      = coef[idx];
    assign acepta_dato   = avs_write && (avs_address == R_DATA_IN) && !ocupado;
    assign borrar_estado = avs_write && (((avs_address == R_CTRL) && avs_writedata[1]) ||
                                         ((avs_address == R_COEF_DATA) && coef_valido));

    // ---------------- Escritura de registros ----------------
    always_ff @(posedge clk) begin
        if (reset) begin
            en       <= 1'b0;
            canal    <= 1'b0;
            data_in  <= '0;
            coef_idx <= '0;
            coef     <= COEF_IDENTIDAD;
        end else if (avs_write) begin
            case (avs_address)
                R_CTRL: begin
                    en    <= avs_writedata[0];
                    canal <= avs_writedata[2];
                    // avs_writedata[1] (LIMPIAR) no se guarda: genera borrar_estado
                end
                R_DATA_IN:   if (!ocupado) data_in <= avs_writedata[15:0];
                R_COEF_IDX:  coef_idx <= avs_writedata[7:0];
                R_COEF_DATA: if (coef_valido) coef[idx] <= avs_writedata[17:0];
                default: ;
            endcase
        end
    end

    // ---------------- Procesamiento (paso directo) ----------------
    // En el mismo flanco en que se acepta DATA_IN, LISTO baja y OCUPADO sube (asi una lectura
    // de STATUS justo despues de la escritura nunca ve el LISTO de la muestra anterior). Al ciclo
    // siguiente DATA_OUT tiene el resultado y LISTO sube.
    always_ff @(posedge clk) begin
        if (reset) begin
            data_out <= '0;
            listo    <= 1'b0;
            ocupado  <= 1'b0;
            saturo   <= 1'b0;
        end else begin
            if (borrar_estado)
                saturo <= 1'b0;

            if (acepta_dato) begin
                listo   <= 1'b0;
                ocupado <= 1'b1;
            end else if (ocupado) begin
                data_out <= data_in;
                ocupado  <= 1'b0;
                listo    <= 1'b1;
            end
        end
    end

    // ---------------- Lectura de registros (1 ciclo de latencia) ----------------
    always_ff @(posedge clk) begin
        if (reset)
            avs_readdata <= '0;
        else if (avs_read) begin
            case (avs_address)
                R_CTRL:      avs_readdata <= {29'd0, canal, 1'b0, en};
                R_STATUS:    avs_readdata <= {29'd0, saturo, ocupado, listo};
                R_DATA_IN:   avs_readdata <= {{16{data_in[15]}}, data_in};
                R_DATA_OUT:  avs_readdata <= {{16{data_out[15]}}, data_out};
                R_COEF_IDX:  avs_readdata <= {24'd0, coef_idx};
                R_COEF_DATA: avs_readdata <= coef_valido ? {{14{coef_sel[17]}}, coef_sel} : '0;
                R_INFO:      avs_readdata <= {ID, VERSION, NCOEF8};
                default:     avs_readdata <= '0;
            endcase
        end
    end

endmodule
