`timescale 1ns/1ps

module tb_reg;
reg [4:0] source_reg1,source_reg2,dest_reg;
reg [v:0]write_data ;
reg reset,clk,write;
integer i;

wire [v:0] rd_data1,rd_data2;

32_register Re (rd_data1,rd_data2,source_reg1,source_reg2,dest_reg,write_data,reset,write,clk);

initial
clk=0;

always #5 clk=~clk;

initial
begin
    reset=1; write=0; 
    #8 reset=0; write=1; 
    for(i=0;i<=31;i=i+1)
    begin
        #2 dest_reg=i; write_data=i*10;
    end
    for(i=2;i<=31;i=i+2)
    begin
        #2 source_reg1=i-1; source_reg2=i;
    end
end

initial
begin
    $dumpfile("tb_reg.vcd");
    $dumpvars(0,tb_reg);
    #100 $finish;
end

