// sram_bist -- built-in self-test for the sram_64x32 macro: March C- over all 64 words, run
// twice with two data backgrounds (solid and checkerboard).
//
//   March C-:  up(w0); up(r0,w1); up(r1,w0); down(r0,w1); down(r1,w0); down(r0)
//
// One memory operation is issued per clock. The macro samples its inputs on the next rising
// edge and presents read data before the edge after that. dout only has half a clock period
// (minus the clock-to-output delay) to reach a flip-flop, so it is registered first and compared
// one cycle later: every read is checked three edges after it was issued.
`default_nettype none
module sram_bist (
    input  wire        clk,
    input  wire        rst,        // synchronous reset
    input  wire        start,      // pulse while idle: run the test
    output reg         busy,
    output reg         done,       // high from the end of the test until the next start
    output reg         fail,       // valid when done
    output reg  [5:0]  fail_addr,  // address of the first mismatch
    // memory port
    output reg         mem_en,
    output reg         mem_we,
    output wire [3:0]  mem_wmask,
    output reg  [5:0]  mem_addr,
    output reg  [31:0] mem_din,
    input  wire [31:0] mem_dout
);
    assign mem_wmask = 4'hF;

    localparam [31:0] BG0 = 32'h00000000, BG1 = 32'h55555555;
    localparam [1:0]  IDLE = 2'd0, RUN = 2'd1, DRAIN = 2'd2;

    reg  [1:0]  st;
    reg  [1:0]  drain;
    reg  [2:0]  elem;          // march element 0..5
    reg         phase;         // 0: first operation of the element, 1: second
    reg         bg;            // data background
    reg  [5:0]  a;
    // expected read data, delayed to line up with mem_dout
    reg         v1, v2, v3;
    reg  [31:0] e1, e2, e3;
    reg  [5:0]  a1, a2, a3;
    reg  [31:0] dout_q;        // read data, registered

    wire [31:0] d0      = bg ? BG1 : BG0;
    wire [31:0] d1      = ~d0;
    wire        two     = (elem != 3'd0) && (elem != 3'd5);      // read followed by write
    wire        rd_now  = (elem == 3'd5) || (two && !phase);
    wire        rd_one  = (elem == 3'd2) || (elem == 3'd4);      // this element reads the inverted background
    wire        wr_one  = (elem == 3'd1) || (elem == 3'd3);      // ... writes the inverted background
    wire        down    = (elem >= 3'd3);
    wire        last    = down ? (a == 6'd0) : (a == 6'd63);
    wire        addr_done = !two || phase;

    always @(posedge clk) begin
        if (rst) begin
            st <= IDLE; drain <= 2'd0; elem <= 3'd0; phase <= 1'b0; bg <= 1'b0; a <= 6'd0;
            busy <= 1'b0; done <= 1'b0; fail <= 1'b0; fail_addr <= 6'd0;
            mem_en <= 1'b0; mem_we <= 1'b0; mem_addr <= 6'd0; mem_din <= 32'd0;
            v1 <= 1'b0; v2 <= 1'b0; v3 <= 1'b0; e1 <= 32'd0; e2 <= 32'd0; e3 <= 32'd0;
            a1 <= 6'd0; a2 <= 6'd0; a3 <= 6'd0; dout_q <= 32'd0;
        end else begin
            dout_q <= mem_dout;
            if (v3 && (dout_q !== e3) && !fail) begin
                fail      <= 1'b1;
                fail_addr <= a3;
            end
            v3 <= v2; e3 <= e2; a3 <= a2;
            v2 <= v1; e2 <= e1; a2 <= a1;
            v1 <= 1'b0;
            mem_en <= 1'b0;
            mem_we <= 1'b0;
            case (st)
                IDLE: if (start) begin
                    st <= RUN; busy <= 1'b1; done <= 1'b0; fail <= 1'b0;
                    elem <= 3'd0; phase <= 1'b0; bg <= 1'b0; a <= 6'd0;
                end
                RUN: begin
                    mem_en   <= 1'b1;
                    mem_addr <= a;
                    if (rd_now) begin
                        v1 <= 1'b1; e1 <= rd_one ? d1 : d0; a1 <= a;
                    end else begin
                        mem_we  <= 1'b1;
                        mem_din <= wr_one ? d1 : d0;
                    end
                    if (!addr_done) begin
                        phase <= 1'b1;
                    end else begin
                        phase <= 1'b0;
                        if (!last) begin
                            a <= down ? a - 6'd1 : a + 6'd1;
                        end else if (elem != 3'd5) begin
                            elem <= elem + 3'd1;
                            a    <= (elem >= 3'd2) ? 6'd63 : 6'd0;      // elements 3..5 run downwards
                        end else if (!bg) begin
                            bg <= 1'b1; elem <= 3'd0; a <= 6'd0;
                        end else begin
                            st <= DRAIN; drain <= 2'd3;
                        end
                    end
                end
                DRAIN: begin
                    drain <= drain - 2'd1;
                    if (drain == 2'd0) begin
                        st <= IDLE; busy <= 1'b0; done <= 1'b1;
                    end
                end
                default: st <= IDLE;
            endcase
        end
    end
endmodule
`default_nettype wire
