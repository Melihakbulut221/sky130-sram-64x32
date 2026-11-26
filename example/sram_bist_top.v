// Integration example: the self-test controller and one sram_64x32 hard macro on one die.
`default_nettype none
module sram_bist_top (
`ifdef USE_POWER_PINS
    inout  wire       VPWR,
    inout  wire       VGND,
`endif
    input  wire       clk,
    input  wire       rst,
    input  wire       start,
    output wire       busy,
    output wire       done,
    output wire       fail,
    output wire [5:0] fail_addr
);
    wire        mem_en, mem_we;
    wire [3:0]  mem_wmask;
    wire [5:0]  mem_addr;
    wire [31:0] mem_din, mem_dout;

    sram_bist u_bist (
        .clk(clk), .rst(rst), .start(start), .busy(busy), .done(done), .fail(fail), .fail_addr(fail_addr),
        .mem_en(mem_en), .mem_we(mem_we), .mem_wmask(mem_wmask), .mem_addr(mem_addr), .mem_din(mem_din), .mem_dout(mem_dout)
    );

    sram_64x32 u_mem (
`ifdef USE_POWER_PINS
        .VPWR(VPWR), .VGND(VGND),
`endif
        .clk(clk), .en(mem_en), .we(mem_we), .wmask(mem_wmask), .addr(mem_addr), .din(mem_din), .dout(mem_dout)
    );
endmodule
`default_nettype wire
