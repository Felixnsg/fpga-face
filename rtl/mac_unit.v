
module mac_unit (
    input wire clk,
    input wire load_w,
    input wire signed [31:0] PSUM_in,
    input wire signed [7:0] activation_in,
    input wire signed [7:0] weight_in,
    output wire signed [7:0] activation_out,
    output wire signed [31:0] PSUM_out
);

reg signed [7:0] weight;
wire signed [15:0] mult;
wire signed [31:0] ext_mult;
wire signed [31:0] sum;


assign mult = activation_in * weight;

assign ext_mult = {{16{mult[15]}}, mult};


assign sum = ext_mult+PSUM_in;

assign activation_out = activation_in;
assign PSUM_out = sum;

always @(posedge clk) begin
    
    if (load_w)
 
        weight <= weight_in;

end




endmodule
