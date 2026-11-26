// sram_64x32 -- behavioural simulation model of the hard macro (SKY130, 64 words x 32 bits).
//
// Interface timing (see the datasheet for the numbers):
//   * en, we, wmask, addr and din are sampled on the rising edge of clk.
//   * The access itself happens while clk is low. Read data appears on dout a short time
//     (T_CQ) after the falling edge and then holds until the next read. Capture it on the
//     next rising edge.
//   * A write stores din in the bytes selected by wmask; dout keeps its previous value.
//   * With en = 0 nothing happens and dout keeps its value.
//   * dout is unknown until the first read; the memory content is unknown until written.
`timescale 1ns/1ps
`default_nettype none
module sram_64x32 #(
    parameter real T_CQ = 1.6          // clk falling edge to dout, typical corner [ns]
) (
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
    output reg  [31:0] dout
);
    reg [31:0] mem [0:63];
    reg        en_q, we_q;
    reg [3:0]  wmask_q;
    reg [5:0]  addr_q;
    reg [31:0] din_q;
    integer    b;

    always @(posedge clk) begin
        en_q    <= en;
        we_q    <= we;
        wmask_q <= wmask;
        addr_q  <= addr;
        din_q   <= din;
    end

    always @(negedge clk) begin
        if (en_q === 1'b1) begin
            if (we_q === 1'b1) begin
                for (b = 0; b < 4; b = b + 1)
                    if (wmask_q[b]) mem[addr_q][8*b +: 8] <= din_q[8*b +: 8];
            end else if (we_q === 1'b0) begin
                dout <= #(T_CQ) mem[addr_q];
            end else begin
                dout <= #(T_CQ) 32'bx;
            end
        end else if (en_q !== 1'b0) begin
            dout <= #(T_CQ) 32'bx;
        end
    end
endmodule
`default_nettype wire
