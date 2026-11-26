// Black-box declaration of the sram_64x32 hard macro (for synthesis and place & route).
(* blackbox *)
module sram_64x32 (
`ifdef USE_POWER_PINS
    inout  wire        VPWR,
    inout  wire        VGND,
`endif
    input  wire        clk,
    input  wire        en,
    input  wire        we,
    input  wire [3:0]  wmask,
    input  wire [5:0]  addr,
    input  wire [31:0] din,
    output wire [31:0] dout
);
endmodule
