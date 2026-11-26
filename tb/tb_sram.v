// Self-checking testbench for sram_64x32 (RTL or gate-level netlist + array model).
`timescale 1ns/1ps
module tb_sram;
    parameter real TCLK = 20.0;
    reg         clk = 0, en = 0, we = 0;
    reg  [3:0]  wmask = 0;
    reg  [5:0]  addr = 0;
    reg  [31:0] din = 0;
    wire [31:0] dout;
`ifdef USE_POWER_PINS
    supply1 VPWR; supply0 VGND;
    sram_64x32 dut (.VPWR(VPWR), .VGND(VGND), .clk(clk), .en(en), .we(we), .wmask(wmask), .addr(addr), .din(din), .dout(dout));
`else
    sram_64x32 dut (.clk(clk), .en(en), .we(we), .wmask(wmask), .addr(addr), .din(din), .dout(dout));
`endif
    always #(TCLK/2) clk = ~clk;

    reg [31:0] model [0:63];
    reg [31:0] expect_q;          // what dout must show at the next rising edge
    reg        expect_v;
    integer    errors = 0, checks = 0, k, seed = 1;
    reg [31:0] m;

    // Inputs change shortly after the rising edge, like outputs of flip-flops on the same clock.
    // At the sampling edge dout still shows the result of the previous operation, so that is
    // where the previous read is checked.
    task op(input e, input w, input [3:0] wm, input [5:0] a, input [31:0] d);
        begin
            #1 en = e; we = w; wmask = wm; addr = a; din = d;
            @(posedge clk);
            if (expect_v) begin
                checks = checks + 1;
                if (dout !== expect_q) begin
                    errors = errors + 1;
                    if (errors < 20) $display("MISMATCH t=%0t dout=%h expected=%h", $time, dout, expect_q);
                end
            end
            if (e && w) begin
                m = {{8{wm[3]}}, {8{wm[2]}}, {8{wm[1]}}, {8{wm[0]}}};
                model[a] = (model[a] & ~m) | (d & m);
            end
            if (e && !w) begin expect_q = model[a]; expect_v = 1; end   // otherwise dout must hold
        end
    endtask

    initial begin
`ifdef VCD
        $dumpfile("tb_sram.vcd"); $dumpvars(0, tb_sram);
`endif
        expect_v = 0;
        repeat (3) @(posedge clk);
        // 1. write every word, then read every word
        for (k = 0; k < 64; k = k + 1) op(1, 1, 4'hF, k[5:0], 32'hA5A50000 ^ (k * 32'h01010101) ^ {k[5:0], 26'd0});
        for (k = 0; k < 64; k = k + 1) op(1, 0, 4'h0, k[5:0], 32'h0);
        // 2. complement pattern
        for (k = 0; k < 64; k = k + 1) op(1, 1, 4'hF, k[5:0], ~(32'hA5A50000 ^ (k * 32'h01010101) ^ {k[5:0], 26'd0}));
        for (k = 63; k >= 0; k = k - 1) op(1, 0, 4'h0, k[5:0], 32'h0);
        // 3. byte writes
        for (k = 0; k < 64; k = k + 1) op(1, 1, 4'h1 << (k % 4), k[5:0], 32'h12345678 + k);
        for (k = 0; k < 64; k = k + 1) op(1, 0, 4'h0, k[5:0], 32'h0);
        // 4. disabled cycles must neither write nor change dout
        op(1, 0, 0, 6'd5, 0);
        op(0, 1, 4'hF, 6'd5, 32'hDEADBEEF);
        op(0, 0, 4'h0, 6'd9, 0);
        op(1, 0, 0, 6'd5, 0);
        // 5. walking ones / zeros on one word, alternating write and read
        for (k = 0; k < 32; k = k + 1) begin
            op(1, 1, 4'hF, 6'd33, 32'h1 << k);       op(1, 0, 0, 6'd33, 0);
            op(1, 1, 4'hF, 6'd33, ~(32'h1 << k));    op(1, 0, 0, 6'd33, 0);
        end
        // 6. random traffic
        for (k = 0; k < 4000; k = k + 1)
            op($random(seed) % 8 != 0, $random(seed), $random(seed), $random(seed), $random(seed));
        op(0, 0, 0, 0, 0);
        op(0, 0, 0, 0, 0);
        $display("RESULT checks=%0d errors=%0d", checks, errors);
        if (errors == 0 && checks > 2000) $display("PASS"); else $display("FAIL");
        $finish;
    end
endmodule
