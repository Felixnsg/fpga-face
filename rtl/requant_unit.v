
/* verilator lint_off UNUSEDSIGNAL */
module requant_unit (

    input wire signed [31:0] PSUM_in,
    input wire clk,
    input wire load_p,
    input wire signed [31:0] big_int_in,
    input wire [4:0] shift_log_in,
    input wire signed [7:0] zp_in,
    output wire signed [7:0] PSUM_out_q

);
//not sure how much space they are gonna take so I assume 32 randomly.
reg signed [31:0] big_int;
reg signed [4:0] shift_logic;
reg signed [31:0] zp_val;

wire signed [63:0] sum1;
wire signed [63:0] shifted_full;  
wire signed [31:0] shifted_sum;
wire signed [31:0] zp_sum;

assign sum1 = PSUM_in * big_int;
assign shifted_full = sum1 >>> shift_logic;
assign shifted_sum = shifted_full[31:0];
assign zp_sum = shifted_sum + zp_val;

assign PSUM_out_q = (zp_sum>127) ? 8'd127 :
                    (zp_sum<-128) ? -8'd128:
                    zp_sum[7:0];

always @(posedge clk) begin
    if (load_p) begin

        big_int <= big_int_in;
        shift_logic <= shift_log_in;
        zp_val <= {{24{zp_in[7]}}, zp_in};
    end

end








endmodule
