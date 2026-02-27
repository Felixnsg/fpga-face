SIM ?= icarus
TOPLEVEL_LANG ?= verilog

# Path to your Verilog source
VERILOG_SOURCES = $(shell pwd)/../rtl/mac_unit.v

# Top-level module name in Verilog
TOPLEVEL = mac_unit

# Python test module name (without .py)
COCOTB_TEST_MODULES = test_mac_unit

# Waveform dump
WAVES = 1


include $(shell cocotb-config --makefiles)/Makefile.sim
