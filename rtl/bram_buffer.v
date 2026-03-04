// BRAM Buffer — Dual-port RAM
// Port A: write side (DMA / SDRAM speed)
// Port B: read side (array / compute speed)
// Felix writes this

module bram_buffer #(
    parameter DATA_WIDTH = 16,
    parameter ADDR_WIDTH = 9    // 2^9 = 512 entries = 1 KB
) (
    // Port A — write side
    input wire write_signal,
    input wire [ADDR_WIDTH-1:0] add_w,
    input wire [DATA_WIDTH-1:0] act_in,
    input wire f_clk,


    // Port B — read side
    input wire s_clk,
    input wire [ADDR_WIDTH-1:0] add_r,
    output reg [DATA_WIDTH-1:0] act_out 

);

// Register array
reg [DATA_WIDTH-1:0] mem [0:(2**ADDR_WIDTH)-1];




// Port A: write logic
always @(posedge f_clk) begin
    if (write_signal) begin
        mem[add_w] <= act_in;
    end

end


// Port B: read logic
always @(posedge s_clk) begin
    act_out <= mem[add_r];

end


endmodule
