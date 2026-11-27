// Testbench autoverificable de hex_ctrl. Uso: tests/hw/sim.sh hex_ctrl
`timescale 1ns/1ps
module tb_hex_ctrl;

    logic        clk = 0, reset = 1;
    logic [1:0]  address = '0;
    logic        read = 0, write = 0;
    logic [31:0] writedata = '0;
    logic [31:0] readdata;
    logic [6:0]  hex0, hex1, hex2, hex3, hex4, hex5;

    int errores = 0;

    localparam logic [6:0] APAGADO = 7'b1111111;
    localparam logic [1:0] CTRL = 2'd0, TIEMPO = 2'd1, CANCION = 2'd2, STATUS = 2'd3;

    hex_ctrl dut (
        .clk, .reset,
        .avs_address(address), .avs_read(read), .avs_readdata(readdata),
        .avs_write(write), .avs_writedata(writedata),
        .hex0, .hex1, .hex2, .hex3, .hex4, .hex5
    );

    always #10 clk = ~clk;   // 50 MHz

    // Codigos esperados (activo en bajo, {g,f,e,d,c,b,a})
    function automatic logic [6:0] seg(int d);
        case (d)
            0: return 7'b1000000;  1: return 7'b1111001;  2: return 7'b0100100;
            3: return 7'b0110000;  4: return 7'b0011001;  5: return 7'b0010010;
            6: return 7'b0000010;  7: return 7'b1111000;  8: return 7'b0000000;
            9: return 7'b0010000;  default: return APAGADO;
        endcase
    endfunction

    task automatic escribir(logic [1:0] a, logic [31:0] d);
        @(negedge clk); address = a; writedata = d; write = 1;
        @(negedge clk); write = 0;
    endtask

    task automatic leer(logic [1:0] a, output logic [31:0] d);
        @(negedge clk); address = a; read = 1;
        @(negedge clk); read = 0;     // latencia 1: el dato ya esta en readdata
        d = readdata;
    endtask

    task automatic revisar(string nombre, logic [6:0] obtenido, logic [6:0] esperado);
        assert (obtenido === esperado)
        else begin
            $error("%s: obtenido %b, esperado %b", nombre, obtenido, esperado);
            errores++;
        end
    endtask

    task automatic revisar_tiempo(int m, int s);
        revisar($sformatf("HEX3 (%0d:%0d)", m, s), hex3, seg(m / 10));
        revisar($sformatf("HEX2 (%0d:%0d)", m, s), hex2, seg(m % 10));
        revisar($sformatf("HEX1 (%0d:%0d)", m, s), hex1, seg(s / 10));
        revisar($sformatf("HEX0 (%0d:%0d)", m, s), hex0, seg(s % 10));
    endtask

    task automatic revisar_dato(string nombre, logic ok, logic [31:0] dato);
        assert (ok)
        else begin
            $error("%s: leido %h", nombre, dato);
            errores++;
        end
    endtask

    initial begin
        logic [31:0] dato;

        repeat (3) @(negedge clk);
        reset = 0;

        // 1. Tras el reset todo apagado
        revisar("reset HEX0", hex0, APAGADO);
        revisar("reset HEX5", hex5, APAGADO);

        // 2. ID en STATUS
        leer(STATUS, dato);
        revisar_dato("ID", dato[31:16] === 16'h4E58, dato);

        // 3. Tiempo 03:27 con displays encendidos
        escribir(CTRL, 32'h3);
        escribir(TIEMPO, {16'd0, 8'd3, 8'd27});
        revisar_tiempo(3, 27);

        // 4. Extremos 59:59 y 00:00
        escribir(TIEMPO, {16'd0, 8'd59, 8'd59});  revisar_tiempo(59, 59);
        escribir(TIEMPO, 32'd0);                   revisar_tiempo(0, 0);

        // 5. Lectura del registro TIEMPO
        escribir(TIEMPO, {16'd0, 8'd12, 8'd34});
        leer(TIEMPO, dato);
        revisar_dato("lectura TIEMPO", dato[14:8] === 7'd12 && dato[5:0] === 6'd34, dato);

        // 6. Cancion 7 en HEX5-4
        escribir(CANCION, 32'd7);
        revisar("HEX5 cancion", hex5, seg(0));
        revisar("HEX4 cancion", hex4, seg(7));

        // 7. Fuera de rango: segundos = 61 -> satura en 59 y STATUS.bit0 = 1
        escribir(TIEMPO, {16'd0, 8'd1, 8'd61});
        revisar_tiempo(1, 59);
        leer(STATUS, dato);
        revisar_dato("FUERA_RANGO activo", dato[0] === 1'b1, dato);
        escribir(TIEMPO, {16'd0, 8'd1, 8'd2});
        leer(STATUS, dato);
        revisar_dato("FUERA_RANGO limpio", dato[0] === 1'b0, dato);

        // 8. EN_TIEMPO = 0 apaga HEX3-0 pero no HEX5-4
        escribir(CTRL, 32'h2);
        revisar("apagado HEX0", hex0, APAGADO);
        revisar("apagado HEX3", hex3, APAGADO);
        revisar("cancion sigue HEX4", hex4, seg(7));

        if (errores == 0) $display("RESULTADO hex_ctrl: OK (todas las pruebas pasaron)");
        else              $display("RESULTADO hex_ctrl: %0d FALLAS", errores);
        $finish;
    end

endmodule
