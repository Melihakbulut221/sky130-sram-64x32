// Testbench of the self-test: a fault-free memory must pass, a memory with one stuck bit must fail.
`timescale 1ns/1ps
module tb_bist;
    reg clk = 0, rst = 1, start = 0;
    always #10 clk = ~clk;

    // fault-free instance
    wire busy, done, fail; wire [5:0] fail_addr;
    sram_bist_top good (.clk(clk), .rst(rst), .start(start), .busy(busy), .done(done), .fail(fail), .fail_addr(fail_addr));

    // instance with a stuck-at-0 bit (bit 8) on the read path of word 41
    wire        f_en, f_we, f_busy, f_done, f_fail;
    wire [3:0]  f_wmask;
    wire [5:0]  f_addr, f_fail_addr;
    wire [31:0] f_din, f_dout;
    reg  [5:0]  rd_addr = 0;         // address of the read whose data is currently on dout
    always @(negedge clk) if (bad_mem.en_q && !bad_mem.we_q) rd_addr <= bad_mem.addr_q;
    wire [31:0] f_dout_faulty = (rd_addr == 6'd41) ? (f_dout & ~32'h00000100) : f_dout;
    sram_bist  bad_bist (.clk(clk), .rst(rst), .start(start), .busy(f_busy), .done(f_done), .fail(f_fail), .fail_addr(f_fail_addr),
                         .mem_en(f_en), .mem_we(f_we), .mem_wmask(f_wmask), .mem_addr(f_addr), .mem_din(f_din), .mem_dout(f_dout_faulty));
    sram_64x32 bad_mem  (.clk(clk), .en(f_en), .we(f_we), .wmask(f_wmask), .addr(f_addr), .din(f_din), .dout(f_dout));

    integer cycles = 0;
    always @(posedge clk) if (busy) cycles = cycles + 1;
    initial begin
        repeat (4) @(posedge clk);
        #1 rst = 0;
        @(posedge clk); #1 start = 1; @(posedge clk); #1 start = 0;
        wait (done && f_done);
        @(posedge clk);
        $display("good memory: done=%b fail=%b (%0d cycles)", done, fail, cycles);
        $display("faulty memory: done=%b fail=%b fail_addr=%0d", f_done, f_fail, f_fail_addr);
        if (done && !fail && f_done && f_fail && f_fail_addr == 6'd41) $display("PASS"); else $display("FAIL");
        $finish;
    end
    initial begin #2000000 $display("TIMEOUT"); $display("FAIL"); $finish; end
endmodule
