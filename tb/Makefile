TOPLEVEL_LANG = verilog
SIM ?= icarus
VERILOG_SOURCES = $(PWD)/../main/register.v
TOPLEVEL = register_32
COCOTB_TEST_MODULES = test_register

include $(shell cocotb-config --makefiles)/Makefile.sim
