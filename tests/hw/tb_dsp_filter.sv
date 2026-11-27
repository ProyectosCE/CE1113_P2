// Testbench autoverificable de dsp_filter (version esqueleto: paso directo).
// Uso: tests/hw/sim.sh dsp_filter
// Cuando se implemente el filtro real, la prueba 4 debe compararse contra la respuesta esperada
// (por ejemplo, la calculada con Python/Octave para los mismos coeficientes).
`timescale 1ns/1ps
module tb_dsp_filter;

    logic        clk = 0, reset = 1;
    logic [2:0]  address = '0;
    logic        read = 0, write = 0;
    logic [31:0] writedata = '0;
    logic [31:0] readdata;

    int errores = 0;

    // Muestras de prueba: cero, +-1, extremos de 16 bits y un valor cualquiera
    logic signed [15:0] entrada [6] = '{16'sd0, 16'sd1, -16'sd1, 16'sd32767, -16'sd32768, 16'sd1234};

    localparam logic [2:0] CTRL = 3'd0, STATUS = 3'd1, DATA_IN = 3'd2, DATA_OUT = 3'd3,
                           COEF_IDX = 3'd4, COEF_DATA = 3'd5, INFO = 3'd6;

    dsp_filter #(.NUM_COEF(16)) dut (
        .clk, .reset,
        .avs_address(address), .avs_read(read), .avs_readdata(readdata),
        .avs_write(write), .avs_writedata(writedata)
    );

    always #10 clk = ~clk;   // 50 MHz

    task automatic escribir(logic [2:0] a, logic [31:0] d);
        @(negedge clk); address = a; writedata = d; write = 1;
        @(negedge clk); write = 0;
    endtask

    task automatic leer(logic [2:0] a, output logic [31:0] d);
        @(negedge clk); address = a; read = 1;
        @(negedge clk); read = 0;
        d = readdata;
    endtask

    task automatic revisar(string nombre, logic ok, logic [31:0] dato);
        assert (ok)
        else begin
            $error("%s: leido %h (%0d)", nombre, dato, $signed(dato));
            errores++;
        end
    endtask

    // Escribe una muestra, espera LISTO y devuelve DATA_OUT
    task automatic procesar(logic signed [15:0] muestra, output logic signed [31:0] salida);
        logic [31:0] st = '0;
        int espera = 0;
        escribir(DATA_IN, {16'd0, muestra});
        while (st[0] !== 1'b1 && espera < 100) begin
            leer(STATUS, st);
            espera++;
        end
        revisar("LISTO subio", espera < 100, st);
        leer(DATA_OUT, salida);
    endtask

    initial begin
        logic [31:0] dato;
        logic signed [31:0] salida;

        repeat (3) @(negedge clk);
        reset = 0;

        // 1. INFO: ID, version y numero de coeficientes
        leer(INFO, dato);
        revisar("INFO", dato[31:16] === 16'hD5F1 && dato[7:0] === 8'd16, dato);

        // 2. Tras el reset: LISTO = 0, OCUPADO = 0
        leer(STATUS, dato);
        revisar("STATUS tras reset", dato[1:0] === 2'b00, dato);

        // 3. Coeficientes: escribir 16 valores (con negativos) y leerlos de vuelta
        for (int i = 0; i < 16; i++) begin
            escribir(COEF_IDX, i);
            escribir(COEF_DATA, i * 1000 - 8000);
        end
        for (int i = 0; i < 16; i++) begin
            escribir(COEF_IDX, i);
            leer(COEF_DATA, dato);
            revisar($sformatf("coeficiente %0d", i), $signed(dato) == i * 1000 - 8000, dato);
        end

        // 4. Muestras con EN = 1 y con EN = 0: en el esqueleto la salida es igual a la entrada
        escribir(CTRL, 32'h1);
        foreach (entrada[i]) begin
            procesar(entrada[i], salida);
            revisar($sformatf("muestra %0d (EN=1)", entrada[i]), salida == entrada[i], salida);
        end
        escribir(CTRL, 32'h0);
        procesar(entrada[5], salida);
        revisar("bypass (EN=0)", salida == entrada[5], salida);

        // 5. CTRL se lee de vuelta (EN y CANAL; LIMPIAR siempre 0)
        escribir(CTRL, 32'h7);
        leer(CTRL, dato);
        revisar("lectura CTRL", dato[2:0] === 3'b101, dato);

        if (errores == 0) $display("RESULTADO dsp_filter: OK (todas las pruebas pasaron)");
        else              $display("RESULTADO dsp_filter: %0d FALLAS", errores);
        $finish;
    end

endmodule
