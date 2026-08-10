import cocotb
from cocotb.triggers import RisingEdge, FallingEdge, Timer
import pyuvm
from pyuvm import *
import random


# ---------------- Sequence Item ----------------
# One "transaction" = one cycle's worth of DUT inputs (+ later, monitored outputs)
class RegItem(uvm_sequence_item):
    def __init__(self, name="RegItem"):
        super().__init__(name)
        self.reset = 0
        self.write = 0
        self.source_reg1 = 0
        self.source_reg2 = 0
        self.dest_reg = 0
        self.write_data = 0
        # filled in by monitor, not driver
        self.rd_data1 = 0
        self.rd_data2 = 0

    def randomize(self):
        self.source_reg1 = random.randint(0, 31)
        self.source_reg2 = random.randint(0, 31)
        self.dest_reg = random.randint(0, 31)
        self.write_data = random.randint(0, 2**32 - 1)
        self.write = random.choice([0, 1])

    def __str__(self):
        return (f"src1={self.source_reg1} src2={self.source_reg2} "
                f"dest={self.dest_reg} wdata={self.write_data} "
                f"write={self.write} reset={self.reset} "
                f"rd1={self.rd_data1} rd2={self.rd_data2}")


# ---------------- Sequence ----------------
class RegSeq(uvm_sequence):
    async def body(self):
        # start with a reset transaction
        rst = RegItem("rst")
        rst.reset = 1
        await self.start_item(rst)
        await self.finish_item(rst)

        # directed edge cases first (good interview talking point:
        # always cover boundaries, not just random)
        edge_cases = [
            dict(dest_reg=0, write_data=0xFFFFFFFF, write=1),
            dict(dest_reg=31, write_data=0xFFFFFFFF, write=1),
            dict(source_reg1=0, source_reg2=0, write=0),   # read same reg twice
        ]
        for case in edge_cases:
            item = RegItem("edge")
            item.reset = 0
            for k, v in case.items():
                setattr(item, k, v)
            await self.start_item(item)
            await self.finish_item(item)

        # random stimulus
        for _ in range(200):
            item = RegItem("rand")
            item.randomize()
            item.reset = 0
            await self.start_item(item)
            await self.finish_item(item)


# ---------------- Driver ----------------
class RegDriver(uvm_driver):
    def build_phase(self):
        self.dut = ConfigDB().get(self, "", "DUT")

    async def run_phase(self):
        await FallingEdge(self.dut.clk)  # drive on negedge, away from monitor's posedge sample
        while True:
            item = await self.seq_item_port.get_next_item()
            self.dut.reset.value = item.reset
            self.dut.write.value = item.write
            self.dut.source_reg1.value = item.source_reg1
            self.dut.source_reg2.value = item.source_reg2
            self.dut.dest_reg.value = item.dest_reg
            self.dut.write_data.value = item.write_data
            await FallingEdge(self.dut.clk)
            self.seq_item_port.item_done()


# ---------------- Monitor ----------------
class RegMonitor(uvm_component):
    def build_phase(self):
        self.dut = ConfigDB().get(self, "", "DUT")
        self.ap = uvm_analysis_port("ap", self)

    async def run_phase(self):
        while True:
            await RisingEdge(self.dut.clk)
            await Timer(1, units="ns")  # let combinational logic settle post-edge
            item = RegItem("mon")
            item.reset = int(self.dut.reset.value)
            item.write = int(self.dut.write.value)
            item.source_reg1 = int(self.dut.source_reg1.value)
            item.source_reg2 = int(self.dut.source_reg2.value)
            item.dest_reg = int(self.dut.dest_reg.value)
            item.write_data = int(self.dut.write_data.value)
            item.rd_data1 = int(self.dut.rd_data1.value)
            item.rd_data2 = int(self.dut.rd_data2.value)
            self.ap.write(item)


# ---------------- Scoreboard (gold model lives here) ----------------
class RegScoreboard(uvm_component):
    def build_phase(self):
        self.fifo = uvm_tlm_analysis_fifo("fifo", self)
        self.port = uvm_get_port("port", self)
        self.model = [0] * 32       # <-- the Python gold model
        self.passed = 0
        self.failed = 0

    def connect_phase(self):
        self.port.connect(self.fifo.get_export)

    def check_phase(self):
        while self.port.can_get():
            _, item = self.port.try_get()

            # IMPORTANT nuance: the write on this cycle already lands in the
            # register array combinationally visible to the read in the SAME
            # cycle (non-blocking assign + continuous assign resolve together).
            # So update the model FIRST, then compute expected reads.
            if item.reset:
                self.model = [0] * 32
            elif item.write:
                self.model[item.dest_reg] = item.write_data

            exp1 = self.model[item.source_reg1]
            exp2 = self.model[item.source_reg2]

            if item.rd_data1 == exp1 and item.rd_data2 == exp2:
                self.passed += 1
            else:
                self.failed += 1
                self.logger.error(
                    f"MISMATCH: {item}  expected rd1={exp1} rd2={exp2}"
                )

    def report_phase(self):
        self.logger.info(f"Scoreboard: passed={self.passed} failed={self.failed}")
        assert self.failed == 0, f"{self.failed} mismatches found — see log above"


# ---------------- Coverage ----------------
class RegCoverage(uvm_component):
    def build_phase(self):
        self.fifo = uvm_tlm_analysis_fifo("cov_fifo", self)
        self.port = uvm_get_port("cov_port", self)
        self.dest_hit = set()
        self.saw_same_src = False
        self.saw_min_data = False
        self.saw_max_data = False
        self.saw_reset = False

    def connect_phase(self):
        self.port.connect(self.fifo.get_export)

    def check_phase(self):
        while self.port.can_get():
            _, item = self.port.try_get()
            if item.write:
                self.dest_hit.add(item.dest_reg)
                if item.write_data == 0:
                    self.saw_min_data = True
                if item.write_data == 0xFFFFFFFF:
                    self.saw_max_data = True
            if item.source_reg1 == item.source_reg2:
                self.saw_same_src = True
            if item.reset:
                self.saw_reset = True

    def report_phase(self):
        pct = len(self.dest_hit) / 32 * 100
        self.logger.info(f"COVERAGE: dest_reg hit {len(self.dest_hit)}/32 ({pct:.1f}%)")
        self.logger.info(f"COVERAGE: same-src-read hit={self.saw_same_src}")
        self.logger.info(f"COVERAGE: min-data hit={self.saw_min_data}, max-data hit={self.saw_max_data}")
        self.logger.info(f"COVERAGE: reset hit={self.saw_reset}")


# ---------------- Agent ----------------
class RegAgent(uvm_agent):
    def build_phase(self):
        self.seqr = uvm_sequencer("seqr", self)
        self.driver = RegDriver("driver", self)
        self.monitor = RegMonitor("monitor", self)

    def connect_phase(self):
        self.driver.seq_item_port.connect(self.seqr.seq_item_export)


# ---------------- Env ----------------
class RegEnv(uvm_env):
    def build_phase(self):
        self.agent = RegAgent("agent", self)
        self.scoreboard = RegScoreboard("scoreboard", self)
        self.coverage = RegCoverage("coverage", self)

    def connect_phase(self):
        self.agent.monitor.ap.connect(self.scoreboard.fifo.analysis_export)
        self.agent.monitor.ap.connect(self.coverage.fifo.analysis_export)


# ---------------- Test ----------------
class RegTest(uvm_test):
    def build_phase(self):
        self.env = RegEnv("env", self)

    async def run_phase(self):
        self.raise_objection()
        seq = RegSeq("seq")
        await seq.start(self.env.agent.seqr)
        self.drop_objection()

@cocotb.test()
async def register_test(dut):
    ConfigDB().set(None, "*", "DUT", dut)
    await uvm_root().run_test("RegTest")
