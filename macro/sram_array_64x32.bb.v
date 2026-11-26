// Black-box view of the bit-cell array macro (for synthesis and place & route).
(* blackbox *)
module sram_array_64x32 (
`ifdef USE_POWER_PINS
    inout  wire        VDD,
    inout  wire        GND,
`endif
    input  wire [63:0] WL,
    inout  wire [31:0] BL,
    inout  wire [31:0] BLB
);
endmodule
