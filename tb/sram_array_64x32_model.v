// Switch-level behavioural model of the 6T array, for logic simulation of the periphery.
//
// Drive strengths stand in for device sizes:
//   strong  - the tri-state drivers of the periphery (standard-cell models)
//   pull0   - a selected cell discharging the bit line on its "0" side
//   weak1   - a precharged bit line holding its charge
// A cell is overwritten when its word line is high and the periphery forces a bit line low.
`timescale 1ns/1ps
module sram_array_64x32 (
`ifdef USE_POWER_PINS
    inout  wire        VDD,
    inout  wire        GND,
`endif
    input  wire [63:0] WL,
    inout  wire [31:0] BL,
    inout  wire [31:0] BLB
);
    reg [31:0] mem [0:63];
    integer    r, n_on;
    reg [5:0]  row;
    reg        sel;
    always @* begin
        n_on = 0; row = 0;
        for (r = 0; r < 64; r = r + 1)
            if (WL[r] === 1'b1) begin n_on = n_on + 1; row = r[5:0]; end
        sel = (n_on == 1);
        if (n_on > 1) $display("ERROR %m: %0d word lines on at %t", n_on, $time);
    end
    wire [31:0] cellq = mem[row];
    genvar c;
    generate
        for (c = 0; c < 32; c = c + 1) begin : col
            assign (weak1, highz0) BL[c]  = 1'b1;
            assign (weak1, highz0) BLB[c] = 1'b1;
            assign (pull0, highz1) BL[c]  = (sel && cellq[c] === 1'b0) ? 1'b0 : 1'bz;
            assign (pull0, highz1) BLB[c] = (sel && cellq[c] === 1'b1) ? 1'b0 : 1'bz;
            always @(sel or row or BL[c] or BLB[c])
                if (sel) begin
                    if (BL[c] === 1'b0 && BLB[c] !== 1'b0 && cellq[c] !== 1'b0) mem[row][c] = 1'b0;
                    else if (BLB[c] === 1'b0 && BL[c] !== 1'b0 && cellq[c] !== 1'b1) mem[row][c] = 1'b1;
                end
        end
    endgenerate
endmodule
