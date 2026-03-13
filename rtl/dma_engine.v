// DMA Engine — FSM that reads SDRAM bursts into BRAM buffer
// Interfaces with AngeloJacobo SDRAM controller + our bram_buffer
// Felix writes this

module dma_engine (
    input wire clk,
    input wire rst,

    // From multi-layer controller
    input wire start,
    input wire [14:0] sdram_addr,    // row[14:2] + bank[1:0] for SDRAM controller

    // To multi-layer controller
    output reg done,

    // SDRAM controller openinterface (AngeloJacobo)
    input wire ready,
    input wire [15:0] s2f_data,
    input wire s2f_data_valid,
    output reg rw,
    output reg rw_en,
    output reg [14:0] f_addr,

    // BRAM buffer write port (Port A)
    output reg we_a,
    output reg [8:0] addr_a,
    output reg [15:0] din_a
);

// State definitions
localparam IDLE    = 3'd0;
localparam REQUEST = 3'd1;
localparam WAIT    = 3'd2;
localparam BURST   = 3'd3;
localparam DONE    = 3'd4;

//lets avoid them latches



// State register
reg [8:0] count;
reg [2:0] state, next_state;

// Sequential: state register, here we write the sequential checks

always @(posedge clk) begin
    if (rst) begin
        state <= IDLE;
        count <= 0;
    end 
    else begin
    
    state <= next_state;

    if (state == WAIT) //count is zero to count, but i think this is not good logic cause it assumes we do only design or rather it is fine, cause by next time there wont be any data because they would be in mac array.
        count <= 0;

    if (state == BURST && s2f_data_valid)
        count <= count + 1;

    end


end
// Combinational: next state + output logic

always @(*) begin

    rw = 1'b0;
    f_addr = 15'b0;
    we_a = 1'b0;
    din_a = 16'b0;
    addr_a = 9'b0;
    rw_en = 1'b0;

    next_state = state; //if no change, stay there.
    done = 1'b0;

    case(state)

        default: begin
            next_state = IDLE;
        end
        
        
        IDLE:  begin

            if (start) //if start is 1 we go on
                next_state = REQUEST;
            
        end

        REQUEST: begin

            rw = 1'b1;
            rw_en = 1'b1;
            f_addr = sdram_addr;

            if (ready)
                
                next_state = WAIT;

        end

        WAIT: begin

            if (s2f_data_valid)

                next_state = BURST;
            
        end

        BURST: begin

            we_a = 1'b1;
            din_a = s2f_data;
            addr_a = count;

            if (s2f_data_valid != 1'b1)

                next_state = DONE;

        end

        DONE: begin

            done = 1'b1;

            next_state = IDLE;

        end

    endcase


end

    


endmodule
