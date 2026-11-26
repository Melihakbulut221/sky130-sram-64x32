// sram_64x32 -- 64-word x 32-bit single-port synchronous SRAM for SkyWater SKY130 (1.8 V).
//
// A full-custom 6T bit-cell array (hard macro sram_array_64x32) wrapped in standard-cell
// periphery. There is no analog sense amplifier and no self-timed pulse: the bit lines swing
// rail to rail and every internal event is derived from one of the two clock phases, so the
// memory works at any clock frequency below its maximum.
//
//   rising clk     en, we, wmask, addr, din are sampled by flip-flops
//   clk high       bit lines precharge to VDD, the address decodes
//   clk low        (if en) one word line is on; read: the cell discharges BL or BLB and the
//                  result is captured in an SR latch; write: a tri-state driver pulls BL or
//                  BLB low for the selected bytes
//   next rising    dout is valid (it changes shortly after the falling edge and then holds)
//
// Cells that must not be restructured by synthesis are instantiated by hand and named keep_*.
`default_nettype none

module sram_64x32 (
`ifdef USE_POWER_PINS
    inout  wire        VPWR,
    inout  wire        VGND,
`endif
    input  wire        clk,
    input  wire        en,       // chip enable
    input  wire        we,       // write enable (1 = write, 0 = read)
    input  wire [3:0]  wmask,    // byte write mask, wmask[b] covers din[8*b+7 : 8*b]
    input  wire [5:0]  addr,
    input  wire [31:0] din,
    output wire [31:0] dout      // read data, holds until the next read
);
    localparam AW = 6, DW = 32, NW = 64, NB = 4;

    // ------------------------------------------------------------------ clock buffer + input registers
    wire clk_i;
    sky130_fd_sc_hd__clkbuf_8 keep_clkbuf (.A(clk), .X(clk_i));

    reg            en_q, we_q;
    reg [NB-1:0]   wmask_q;
    reg [AW-1:0]   addr_q;
    reg [DW-1:0]   din_q;
    always @(posedge clk_i) begin
        en_q    <= en;
        we_q    <= we;
        wmask_q <= wmask;
        addr_q  <= addr;
        din_q   <= din;
    end

    // ------------------------------------------------------------------ phase clock
    // phi is high during the low half of clk when the memory is enabled. The clock gate
    // latches en_q while clkb is low, so phi never glitches. The distribution is built by
    // hand (one buffer for the word-line gates, one per half of the columns) because the
    // phase clock ends in ordinary gates, not in flip-flops.
    wire       clkb, phi_root, phi_wl, phi_d1, phi_d2, phi_d;
    wire [1:0] phi_c;
    sky130_fd_sc_hd__clkinv_2      keep_clkinv    (.A(clk_i), .Y(clkb));
    sky130_fd_sc_hd__dlclkp_4      keep_icg       (.CLK(clkb), .GATE(en_q), .GCLK(phi_root));
    sky130_fd_sc_hd__clkbuf_16     keep_phibuf_wl (.A(phi_root), .X(phi_wl));
    sky130_fd_sc_hd__clkbuf_16     keep_phibuf_c0 (.A(phi_root), .X(phi_c[0]));
    sky130_fd_sc_hd__clkbuf_16     keep_phibuf_c1 (.A(phi_root), .X(phi_c[1]));
    // Delayed copy of phi. The hold latches below are transparent while phi_d is low, so they
    // open about 1 ns after the word line and the write drivers have been switched off.
    sky130_fd_sc_hd__dlygate4sd3_1 keep_dly0      (.A(phi_root), .X(phi_d1));
    sky130_fd_sc_hd__dlygate4sd3_1 keep_dly1      (.A(phi_d1),   .X(phi_d2));
    sky130_fd_sc_hd__clkbuf_8      keep_dlybuf    (.A(phi_d2),   .X(phi_d));

    // ------------------------------------------------------------------ hold latches
    // They block the new flip-flop values at the rising clock edge until the evaluate phase
    // of the previous cycle has completely ended.
    wire            we_l;
    wire [NB-1:0]   wmask_l;
    wire [AW-1:0]   addr_l;
    wire [DW-1:0]   din_l;
    sky130_fd_sc_hd__dlxtn_1 keep_lat_we (.D(we_q), .GATE_N(phi_d), .Q(we_l));
    genvar i;
    generate
        for (i = 0; i < NB; i = i + 1) begin : g_lm
            sky130_fd_sc_hd__dlxtn_1 keep_lat (.D(wmask_q[i]), .GATE_N(phi_d), .Q(wmask_l[i]));
        end
        for (i = 0; i < AW; i = i + 1) begin : g_la
            sky130_fd_sc_hd__dlxtn_1 keep_lat (.D(addr_q[i]), .GATE_N(phi_d), .Q(addr_l[i]));
        end
        for (i = 0; i < DW; i = i + 1) begin : g_ld
            sky130_fd_sc_hd__dlxtn_1 keep_lat (.D(din_q[i]), .GATE_N(phi_d), .Q(din_l[i]));
        end
    endgenerate

    // ------------------------------------------------------------------ row decoder + word lines
    wire [NW-1:0] dec = {{(NW-1){1'b0}}, 1'b1} << addr_l;
    wire [NW-1:0] wl;
    generate
        for (i = 0; i < NW; i = i + 1) begin : g_wl
            sky130_fd_sc_hd__and2_4 keep_and (.A(dec[i]), .B(phi_wl), .X(wl[i]));
        end
    endgenerate

    // ------------------------------------------------------------------ write and read enables
    wire [NB-1:0] wen;      // per-byte write pulse
    wire [NB-1:0] rd;       // read pulse (one copy per byte to limit the fan-out)
    generate
        for (i = 0; i < NB; i = i + 1) begin : g_en
            sky130_fd_sc_hd__and3_4  keep_and (.A(phi_c[i/2]), .B(we_l), .C(wmask_l[i]), .X(wen[i]));
            sky130_fd_sc_hd__and2b_4 keep_rd  (.A_N(we_l), .B(phi_c[i/2]), .X(rd[i]));
        end
    endgenerate

    // ------------------------------------------------------------------ columns
    wire [DW-1:0] bl, blb;          // bit lines (to the array macro)
    wire [DW-1:0] sa, sb;           // sa = BL is low, sb = BLB is low
    wire [DW-1:0] w0n, w1n;         // low while this column is being written with 0 / 1
    wire [DW-1:0] te_bl, te_blb;    // tri-state enables (active low)
    wire [DW-1:0] din_n = ~din_l;
    wire [DW-1:0] s_n, r_n, q, q_n;
    generate
        for (i = 0; i < DW; i = i + 1) begin : g_col
            // write data: pull BL low to store 0, pull BLB low to store 1
            sky130_fd_sc_hd__nand2_1  keep_w0  (.A(wen[i/8]), .B(din_n[i]), .Y(w0n[i]));
            sky130_fd_sc_hd__nand2_1  keep_w1  (.A(wen[i/8]), .B(din_l[i]), .Y(w1n[i]));
            // One tri-state driver per bit line does three jobs:
            //   phi low                -> drives 1            (precharge)
            //   phi high, writing      -> drives 0            (write)
            //   phi high, other line 0 -> drives 1            (keeper: the high line never floats)
            //   otherwise              -> off                 (the cell discharges the line)
            sky130_fd_sc_hd__and3b_1  keep_te0 (.A_N(sb[i]), .B(phi_c[i/16]), .C(w0n[i]), .X(te_bl[i]));
            sky130_fd_sc_hd__and3b_1  keep_te1 (.A_N(sa[i]), .B(phi_c[i/16]), .C(w1n[i]), .X(te_blb[i]));
            sky130_fd_sc_hd__ebufn_2  keep_drv0 (.A(w0n[i]), .TE_B(te_bl[i]),  .Z(bl[i]));
            sky130_fd_sc_hd__ebufn_2  keep_drv1 (.A(w1n[i]), .TE_B(te_blb[i]), .Z(blb[i]));
            // sensing: a plain inverter on each bit line
            sky130_fd_sc_hd__inv_2    keep_sa  (.A(bl[i]),  .Y(sa[i]));
            sky130_fd_sc_hd__inv_2    keep_sb  (.A(blb[i]), .Y(sb[i]));
            // output latch: set when BLB went low (cell holds 1), reset when BL went low
            sky130_fd_sc_hd__nand2_1  keep_s   (.A(rd[i/8]), .B(sb[i]), .Y(s_n[i]));
            sky130_fd_sc_hd__nand2_1  keep_r   (.A(rd[i/8]), .B(sa[i]), .Y(r_n[i]));
            sky130_fd_sc_hd__nand2_1  keep_q   (.A(s_n[i]), .B(q_n[i]), .Y(q[i]));
            sky130_fd_sc_hd__nand2_1  keep_qn  (.A(r_n[i]), .B(q[i]),   .Y(q_n[i]));
            sky130_fd_sc_hd__buf_2    keep_out (.A(q[i]), .X(dout[i]));
        end
    endgenerate

    // ------------------------------------------------------------------ bit-cell array
    sram_array_64x32 u_array (
`ifdef USE_POWER_PINS
        .VDD(VPWR),
        .GND(VGND),
`endif
        .WL(wl),
        .BL(bl),
        .BLB(blb)
    );
endmodule
`default_nettype wire
