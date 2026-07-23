`timescale 1ns/1ps

module tb_reg;
reg [4:0] source_reg1,source_reg2,dest_reg;
reg [31:0]write_data ;
reg reset,clk,write;
integer i;

wire [31:0] rd_data1,rd_data2;

register_32 Re(rd_data1,rd_data2,source_reg1,source_reg2,dest_reg,write_data,reset,write,clk);

initial
clk=0;

always #5 clk=~clk;

initial
begin
    reset=1; write=0; 
    #6 reset=0; write=1; 
end

initial
begin
    for(i=0;i<=31;i=i+1)
    begin
        #8 dest_reg=i; write_data=i*10;
         $display("time=%0d, source_reg1=%0d, source_reg2=%0d, dest_reg=%0d, write_data=%0d, reg=%0d, rd_data1=%0d, rd_data2=%0d",$time,source_reg1,source_reg2,dest_reg,write_data,Re.register[i],rd_data1,rd_data2);
    end

    #20 write=0;
    for(i=0;i<=30;i=i+1)
    begin
        source_reg1=i; source_reg2=i+1;
         $display("time=%0d, source_reg1=%0d, source_reg2=%0d, dest_reg=%0d, write_data=%0d, reg=%0d, rd_data1=%0d, rd_data2=%0d",$time,source_reg1,source_reg2,dest_reg,write_data,Re.register[i],rd_data1,rd_data2);
        #4;
    end
end

initial
begin
   $dumpfile("tb_reg.vcd");
    $dumpvars(0,tb_reg);
    #1000 $finish;
end
endmodule
