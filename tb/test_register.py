import cocotb
from cocotb.clock import Clock
from cocotb.triggers import Timer
import pyuvm
import register_tb

@cocotb.test()
async def register_test(dut):
    register_tb.DUT = dut
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())
    await Timer(1, unit="ns")
    await pyuvm.uvm_root().run_test("RegTest")
