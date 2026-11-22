// Ejemplo minimo: LED0 parpadea (~0.75 Hz) y KEY0 (activo en bajo) lo apaga.
module blink (
    input        CLOCK_50,
    input  [0:0] KEY,
    output [0:0] LEDR
);
    reg [25:0] cuenta = 26'd0;
    always @(posedge CLOCK_50) cuenta <= cuenta + 1'b1;
    assign LEDR[0] = cuenta[25] & KEY[0];
endmodule
