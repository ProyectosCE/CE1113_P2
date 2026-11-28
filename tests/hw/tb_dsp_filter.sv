// Testbench autoverificable de dsp_filter (version 0x02: cascada de 3 biquads).
// Uso: tests/hw/sim.sh dsp_filter
// Prueba los registros, el banco de coeficientes, el bypass, la MAC con un filtro sencillo
// calculado a mano (el ejemplo de la seccion 9.5 de docs/dsp/especificacion-modulo.md), el estado
// por canal, LIMPIAR, el bit SATURO y el descarte de DATA_IN con OCUPADO = 1.
`timescale 1ns/1ps
module tb_dsp_filter;

    logic        clk = 0, reset = 1;
    logic [2:0]  address = '0;
    logic        read = 0, write = 0;
    logic [31:0] writedata = '0;
    logic [31:0] readdata;

    int errores = 0;

    localparam logic [2:0] CTRL = 3'd0, STATUS = 3'd1, DATA_IN = 3'd2, DATA_OUT = 3'd3,
                           COEF_IDX = 3'd4, COEF_DATA = 3'd5, INFO = 3'd6;

    // Bits de CTRL
    localparam logic [31:0] EN = 32'h1, LIMPIAR = 32'h2, CANAL1 = 32'h4;

    // Muestras de prueba: cero, +-1, extremos de 16 bits y un valor cualquiera
    logic signed [15:0] entrada [6] = '{16'sd0, 16'sd1, -16'sd1, 16'sd32767, -16'sd32768, 16'sd1234};

    // Bancos de coeficientes (Q3.15, orden b0 b1 b2 a1 a2 por etapa)
    // Identidad: b0 = 1.0 en cada etapa
    logic [17:0] identidad [15] = '{18'h08000, 0, 0, 0, 0,
                                    18'h08000, 0, 0, 0, 0,
                                    18'h08000, 0, 0, 0, 0};
    // Promedio: etapa 0 con y = 0.5*x + 0.5*x1; etapas 1 y 2 identidad
    logic [17:0] promedio  [15] = '{18'h04000, 18'h04000, 0, 0, 0,
                                    18'h08000, 0, 0, 0, 0,
                                    18'h08000, 0, 0, 0, 0};
    // Ganancia ~4 en la etapa 0 (b0 = 0x1FFFF, el maximo de Q3.15): satura con muestras grandes
    logic [17:0] ganancia4 [15] = '{18'h1FFFF, 0, 0, 0, 0,
                                    18'h08000, 0, 0, 0, 0,
                                    18'h08000, 0, 0, 0, 0};
    // Valores para escribir y leer el banco: extremos, -1, 1, 1.0 y otros con y sin signo
    logic [17:0] valores   [15] = '{18'h1FFFF, 18'h20000, 18'h3FFFF, 18'h00001, 18'h08000,
                                    18'h31650, 18'h0409A, 18'h381E4, 18'h03D95, 18'h12345,
                                    18'h2ABCD, 18'h00000, 18'h10000, 18'h30000, 18'h0FFFF};

    dsp_filter dut (
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

    // Carga los 15 coeficientes (cada escritura de COEF_DATA tambien borra el estado)
    task automatic cargar(logic [17:0] c [15]);
        for (int i = 0; i < 15; i++) begin
            escribir(COEF_IDX, i);
            escribir(COEF_DATA, {{14{c[i][17]}}, c[i]});
        end
    endtask

    // Espera STATUS.LISTO (con limite) y devuelve DATA_OUT
    task automatic esperar_resultado(output logic signed [31:0] salida);
        logic [31:0] st = '0;
        int espera = 0;
        while (st[0] !== 1'b1 && espera < 100) begin
            leer(STATUS, st);
            espera++;
        end
        revisar("LISTO subio", espera < 100, st);
        leer(DATA_OUT, salida);
    endtask

    // Escribe una muestra, espera LISTO y devuelve DATA_OUT
    task automatic procesar(logic signed [15:0] muestra, output logic signed [31:0] salida);
        escribir(DATA_IN, {16'd0, muestra});
        esperar_resultado(salida);
    endtask

    initial begin
        logic [31:0] dato;
        logic signed [31:0] salida;

        repeat (3) @(negedge clk);
        reset = 0;

        // 1. INFO: ID, version 0x02 y 15 coeficientes
        leer(INFO, dato);
        revisar("INFO", dato === 32'hD5F1020F, dato);

        // 2. Tras el reset: LISTO = 0, OCUPADO = 0, SATURO = 0
        leer(STATUS, dato);
        revisar("STATUS tras reset", dato[2:0] === 3'b000, dato);

        // 3. Coeficientes de reset: identidad en cada etapa; indice 15 se lee como 0
        for (int i = 0; i < 16; i++) begin
            escribir(COEF_IDX, i);
            leer(COEF_DATA, dato);
            revisar($sformatf("coeficiente %0d tras reset", i),
                    dato === ((i == 0 || i == 5 || i == 10) ? 32'h00008000 : 32'h0), dato);
        end

        // 4. Escribir los 15 coeficientes (con basura en los bits 31:18) y leerlos extendidos en
        //    signo; una escritura con indice 20 se ignora y ese indice se lee como 0
        for (int i = 0; i < 15; i++) begin
            escribir(COEF_IDX, i);
            escribir(COEF_DATA, {14'h2AAA, valores[i]});
        end
        escribir(COEF_IDX, 20);
        escribir(COEF_DATA, 32'h00012345);
        leer(COEF_DATA, dato);
        revisar("coeficiente 20 (no valido)", dato === 32'h0, dato);
        for (int i = 0; i < 15; i++) begin
            escribir(COEF_IDX, i);
            leer(COEF_DATA, dato);
            revisar($sformatf("coeficiente %0d", i),
                    dato === {{14{valores[i][17]}}, valores[i]}, dato);
        end

        // 5. Identidad con EN = 1: la salida es igual a la entrada tras las 3 etapas
        cargar(identidad);
        escribir(CTRL, EN);
        foreach (entrada[i]) begin
            procesar(entrada[i], salida);
            revisar($sformatf("identidad, muestra %0d", entrada[i]), salida == entrada[i], salida);
        end

        // 6. Bypass (EN = 0): la salida es igual a la entrada
        escribir(CTRL, 32'h0);
        foreach (entrada[i]) begin
            procesar(entrada[i], salida);
            revisar($sformatf("bypass, muestra %0d", entrada[i]), salida == entrada[i], salida);
        end

        // 7. Promedio (seccion 9.5 de la especificacion): 1000 -> 500, luego 2000 -> 1500
        cargar(promedio);
        escribir(CTRL, EN);
        procesar(16'sd1000, salida);
        revisar("promedio, 1000", salida == 500, salida);
        procesar(16'sd2000, salida);
        revisar("promedio, 2000 (con 1000 antes)", salida == 1500, salida);

        // 8. Canales independientes: el canal 1 no ve el historial del canal 0
        escribir(CTRL, EN | CANAL1);
        procesar(16'sd1000, salida);
        revisar("canal 1, 1000", salida == 500, salida);

        // 9. LIMPIAR borra el historial: en el canal 0, 1000 -> 500 otra vez (no 1500)
        escribir(CTRL, EN | LIMPIAR);
        procesar(16'sd1000, salida);
        revisar("LIMPIAR, canal 0, 1000", salida == 500, salida);

        // 10. SATURO: con ganancia ~4, 32767 satura la etapa 0; la salida queda en 32767.
        //     Escribir COEF_DATA lo borra
        cargar(ganancia4);
        leer(STATUS, dato);
        revisar("SATURO en 0 antes de saturar", dato[2] === 1'b0, dato);
        procesar(16'sd32767, salida);
        revisar("ganancia 4, 32767", salida == 32767, salida);
        leer(STATUS, dato);
        revisar("SATURO en 1", dato[2] === 1'b1, dato);
        escribir(COEF_IDX, 0);
        escribir(COEF_DATA, 32'h00008000);
        leer(STATUS, dato);
        revisar("SATURO borrado al escribir COEF_DATA", dato[2] === 1'b0, dato);

        // 11. DATA_IN con OCUPADO = 1: la segunda escritura seguida se descarta
        cargar(identidad);
        escribir(CTRL, EN);
        escribir(DATA_IN, 32'd111);
        escribir(DATA_IN, 32'd222);
        esperar_resultado(salida);
        revisar("DATA_OUT con escritura descartada", salida == 111, salida);
        leer(DATA_IN, dato);
        revisar("DATA_IN conserva la primera muestra", dato === 32'd111, dato);

        // 12. CTRL se lee de vuelta (EN y CANAL; LIMPIAR siempre 0)
        escribir(CTRL, 32'h7);
        leer(CTRL, dato);
        revisar("lectura CTRL", dato[2:0] === 3'b101, dato);

        if (errores == 0) $display("RESULTADO dsp_filter: OK (todas las pruebas pasaron)");
        else              $display("RESULTADO dsp_filter: %0d FALLAS", errores);
        $finish;
    end

endmodule
