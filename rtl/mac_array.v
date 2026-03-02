
module mac_array (
    /* verilator lint_off UNOPTFLAT */
    input wire clk,
    input wire load_w,
    input wire signed [7:0] activation_in,
    input wire signed [7:0] weight_in,
    input wire [3:0] col_sel, //new sig to help choose where weights go
    input wire [3:0] row_sel,
    output wire signed [511:0] PSUM_out

);
    // connection between MACs

    wire signed [31:0] psum_wire [0:15][0:16];
    wire signed [7:0] activation_wire [0:15][0:16];

    genvar r,c;

    generate
        for (r=0; r<16; r=r+1) begin: row
            assign psum_wire[r][0] = 32'd0;
            assign activation_wire[r][0] = activation_in;

            for (c =0; c<16; c=c+1) begin: col
                mac_unit mac (
                    .clk(clk),
                    .load_w(load_w & (row_sel == r) & (col_sel == c)),
                    .weight_in(weight_in),
                    .activation_out(activation_wire[r][c+1]),
                    .activation_in(activation_wire[r][c]),
                    .PSUM_in(psum_wire[r][c]),
                    .PSUM_out(psum_wire[r][c+1])

                );
            end

            assign PSUM_out[r*32+:32]= psum_wire[r][16];
        end


    endgenerate





endmodule
