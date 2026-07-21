`timescale 1ns/1ps

module register_32(rd_data1,rd_data2,source_reg1,source_reg2,dest_reg,write_data,reset,write,clk);

parameter v = 31 ;

input [4:0] source_reg1,source_reg2,dest_reg;
input [v:0]write_data ;
input reset,clk,write;

output [v:0] rd_data1,rd_data2;

reg [v:0] register [0:v];
integer i;

assign rd_data1 = register[source_reg1];
assign rd_data2 = register[source_reg2];

always@(posedge clk)
begin
    if(reset)
    begin
        for(i=0; i<=v; i++)
        register[i]=0;
    end
    else
    begin
        if(write)
        register[dest_reg]<=write_data;
    end
end
endmodule
