@cocotb.test()
async def register_test(dut):
    ConfigDB().set(None, "uvm_test_top.env.agent.driver", "DUT", dut)
    ConfigDB().set(None, "uvm_test_top.env.agent.monitor", "DUT", dut)

    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())

    await Timer(1, unit="ns")
    await pyuvm.uvm_root().run_test("RegTest")
