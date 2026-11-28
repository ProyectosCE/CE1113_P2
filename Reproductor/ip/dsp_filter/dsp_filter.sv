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

    // ---------------- Nucleo: estado del filtro ----------------
    // Historiales y residuo de cada etapa, separados por canal: [canal][etapa]
    logic [1:0][2:0][23:0] x1, x2, y1, y2;      // Q1.23
    logic [1:0][2:0][14:0] residuo;             // error de redondeo de la ultima muestra

    typedef enum logic [1:0] {
        REPOSO       = 2'd0,
        MAC          = 2'd1,
        CIERRE_ETAPA = 2'd2,
        SALIDA       = 2'd3
    } estado_t;

    estado_t            estado;
    logic [1:0]         etapa;        // etapa en proceso (0 .. 2)
    logic [2:0]         paso;         // producto en proceso: 0 b0*x, 1 b1*x1, 2 b2*x2, 3 a1*y1, 4 a2*y2
    logic               canal_act;    // canal de la muestra en proceso
    logic signed [23:0] x;            // entrada de la etapa en proceso (Q1.23)
    logic signed [47:0] acc;          // acumulador de la MAC

    // Residuo de 15 bits extendido en signo al ancho del acumulador
    function automatic logic signed [47:0] extender(input logic [14:0] r);
        return $signed({{33{r[14]}}, r});
    endfunction

    // ---------------- Nucleo: ruta de datos (combinacional) ----------------
    logic signed [23:0] operando;     // operando del multiplicador segun paso
    logic        [3:0]  idx_mac;      // coeficiente de la MAC: etapa*5 + paso
    logic signed [17:0] coef_mac;
    logic signed [41:0] producto;     // 24 x 18 bits
    logic signed [47:0] producto_ext;
    logic signed [47:0] acc_red;      // acc + 2^14 (redondeo al mas cercano)
    logic signed [32:0] q;            // acc redondeado a 15 bits de fraccion, sin saturar
    logic               satura;       // q no cabe en 24 bits
    logic signed [23:0] y;            // salida de la etapa: q saturado a 24 bits
    logic        [24:0] x_red;        // x + 2^7 en 25 bits (redondeo de 24 a 16 bits)
    logic        [16:0] r_sal;        // x redondeado, sin saturar
    logic signed [15:0] salida;       // resultado final saturado a 16 bits

    always_comb begin
        case (paso)
            3'd0:    operando = x;
            3'd1:    operando = x1[canal_act][etapa];
            3'd2:    operando = x2[canal_act][etapa];
            3'd3:    operando = y1[canal_act][etapa];
            default: operando = y2[canal_act][etapa];
        endcase
    end

    assign idx_mac      = {2'b00, etapa} * 4'd5 + {1'b0, paso};
    assign coef_mac     = coef[idx_mac];
    assign producto     = 42'(operando) * 42'(coef_mac);   // el producto completo cabe en 42 bits
    assign producto_ext = $signed({{6{producto[41]}}, producto});

    // Redondeo: q = (acc + 2^14) >>> 15. El residuo nuevo es acc[14:0] (lo que se descarta,
    // visto como numero con signo de 15 bits), igual que acc - q*2^15 en el modelo.
    assign acc_red = acc + 48'sd16384;
    assign q       = acc_red[47:15];
    assign satura  = (q[32:23] != {10{q[23]}});
    assign y       = !satura ? q[23:0] : (q[32] ? 24'sh800000 : 24'sh7FFFFF);

    // Salida: (x + 2^7) >>> 8 saturado a 16 bits. Con x = muestra*256 (bypass) da la muestra exacta
    assign x_red  = {x[23], x} + 25'd128;
    assign r_sal  = x_red[24:8];
    assign salida = (r_sal[16] == r_sal[15]) ? r_sal[15:0] : (r_sal[16] ? 16'sh8000 : 16'sh7FFF);

    // ---------------- Nucleo: FSM y registros de control ----------------
    // REPOSO -> MAC (5 ciclos) -> CIERRE_ETAPA, tres veces, -> SALIDA: 20 ciclos por muestra.
    // En bypass (EN = 0): REPOSO -> SALIDA, 2 ciclos, sin tocar el estado.
    // En el mismo flanco en que se acepta DATA_IN, LISTO baja y OCUPADO sube (asi una lectura
    // de STATUS justo despues de la escritura nunca ve el LISTO de la muestra anterior).
    always_ff @(posedge clk) begin
        if (reset) begin
            estado    <= REPOSO;
            etapa     <= '0;
            paso      <= '0;
            canal_act <= 1'b0;
            x         <= '0;
            acc       <= '0;
            data_out  <= '0;
            listo     <= 1'b0;
            ocupado   <= 1'b0;
            saturo    <= 1'b0;
        end else begin
            if (borrar_estado)
                saturo <= 1'b0;
            else if ((estado == CIERRE_ETAPA) && satura)
                saturo <= 1'b1;

            case (estado)
                REPOSO: begin
                    if (acepta_dato) begin
                        listo     <= 1'b0;
                        ocupado   <= 1'b1;
                        canal_act <= canal;
                        x         <= {avs_writedata[15:0], 8'd0};   // muestra * 256 (Q1.23)
                        etapa     <= '0;
                        paso      <= '0;
                        acc       <= extender(residuo[canal][0]);
                        estado    <= en ? MAC : SALIDA;
                    end
                end
                MAC: begin
                    acc <= (paso >= 3'd3) ? acc - producto_ext : acc + producto_ext;
                    if (paso == 3'd4)
                        estado <= CIERRE_ETAPA;
                    else
                        paso <= paso + 3'd1;
                end
                CIERRE_ETAPA: begin
                    x    <= y;                 // entrada de la siguiente etapa
                    paso <= '0;
                    if (etapa == 2'd2)
                        estado <= SALIDA;
                    else begin
                        etapa  <= etapa + 2'd1;
                        acc    <= extender(residuo[canal_act][etapa + 2'd1]);
                        estado <= MAC;
                    end
                end
                SALIDA: begin
                    data_out <= salida;
                    listo    <= 1'b1;
                    ocupado  <= 1'b0;
                    estado   <= REPOSO;
                end
                default: estado <= REPOSO;
            endcase
        end
    end

    // Estado del filtro: se borra con el reset, LIMPIAR o COEF_DATA, y se actualiza al cerrar
    // cada etapa (se desplazan los historiales y se guarda el residuo, aunque la salida sature)
    always_ff @(posedge clk) begin
        if (reset || borrar_estado) begin
            x1      <= '0;
            x2      <= '0;
            y1      <= '0;
            y2      <= '0;
            residuo <= '0;
        end else if (estado == CIERRE_ETAPA) begin
            x2[canal_act][etapa]      <= x1[canal_act][etapa];
            x1[canal_act][etapa]      <= x;
            y2[canal_act][etapa]      <= y1[canal_act][etapa];
            y1[canal_act][etapa]      <= y;
            residuo[canal_act][etapa] <= acc[14:0];
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
