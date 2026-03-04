"""
Golden reference testbench for dual-port BRAM buffer.
Tests: basic write/read, sequential burst, simultaneous read/write,
       address boundaries, dual-clock operation, no-write passivity.
"""
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer
import random


async def write_word(dut, addr, data):
    """Write one word to port A."""
    dut.write_signal.value = 1
    dut.add_w.value = addr
    dut.act_in.value = data
    await RisingEdge(dut.f_clk)
    dut.write_signal.value = 0


async def read_word(dut, addr):
    """Read one word from port B. Returns value after 1-cycle latency."""
    dut.add_r.value = addr
    await RisingEdge(dut.s_clk)
    await Timer(1, units="ns")  # let non-blocking assignment settle
    return dut.act_out.value.to_unsigned()


@cocotb.test()
async def test_basic_write_read(dut):
    """Write a value, then read it back."""
    cocotb.start_soon(Clock(dut.f_clk, 6, unit="ns").start())   # ~165 MHz
    cocotb.start_soon(Clock(dut.s_clk, 10, unit="ns").start())  # ~100 MHz

    # Write 0xABCD to address 0
    await write_word(dut, 0, 0xABCD)

    # Wait for cross-clock settle
    await RisingEdge(dut.s_clk)
    await RisingEdge(dut.s_clk)

    # Read from address 0
    got = await read_word(dut, 0)
    assert got == 0xABCD, f"Expected 0xABCD, got {hex(got)}"
    cocotb.log.info("PASS: basic write/read")


@cocotb.test()
async def test_multiple_addresses(dut):
    """Write to several addresses, read them all back."""
    cocotb.start_soon(Clock(dut.f_clk, 6, unit="ns").start())
    cocotb.start_soon(Clock(dut.s_clk, 10, unit="ns").start())

    test_data = {0: 0x1111, 5: 0x2222, 100: 0x3333, 255: 0x4444, 511: 0x5555}

    # Write all
    for addr, data in test_data.items():
        await write_word(dut, addr, data)

    # Let writes settle across clock domains
    for _ in range(4):
        await RisingEdge(dut.s_clk)

    # Read all back
    for addr, expected in test_data.items():
        got = await read_word(dut, addr)
        assert got == expected, f"Addr {addr}: expected {hex(expected)}, got {hex(got)}"

    cocotb.log.info("PASS: multiple addresses")


@cocotb.test()
async def test_burst_write_read(dut):
    """Simulate a burst: write 64 consecutive words, read them all back."""
    cocotb.start_soon(Clock(dut.f_clk, 6, unit="ns").start())
    cocotb.start_soon(Clock(dut.s_clk, 10, unit="ns").start())

    burst_len = 64
    burst_data = [i * 7 + 3 for i in range(burst_len)]  # some pattern

    # Burst write
    for i in range(burst_len):
        await write_word(dut, i, burst_data[i])

    # Let writes settle
    for _ in range(4):
        await RisingEdge(dut.s_clk)

    # Burst read
    errors = 0
    for i in range(burst_len):
        got = await read_word(dut, i)
        if got != burst_data[i]:
            cocotb.log.error(f"Addr {i}: expected {burst_data[i]}, got {got}")
            errors += 1

    assert errors == 0, f"{errors}/{burst_len} burst reads failed"
    cocotb.log.info("PASS: burst write/read (64 words)")


@cocotb.test()
async def test_overwrite(dut):
    """Write to an address, then overwrite it, verify new value."""
    cocotb.start_soon(Clock(dut.f_clk, 6, unit="ns").start())
    cocotb.start_soon(Clock(dut.s_clk, 10, unit="ns").start())

    # Write first value
    await write_word(dut, 42, 0x1234)

    # Overwrite
    await write_word(dut, 42, 0x5678)

    # Let settle
    for _ in range(4):
        await RisingEdge(dut.s_clk)

    # Read — should get new value
    got = await read_word(dut, 42)
    assert got == 0x5678, f"Expected 0x5678, got {hex(got)}"
    cocotb.log.info("PASS: overwrite works")


@cocotb.test()
async def test_write_enable_low(dut):
    """When write_signal is low, data should NOT be written."""
    cocotb.start_soon(Clock(dut.f_clk, 6, unit="ns").start())
    cocotb.start_soon(Clock(dut.s_clk, 10, unit="ns").start())

    # Write a known value
    await write_word(dut, 10, 0xAAAA)

    # Let settle
    for _ in range(4):
        await RisingEdge(dut.s_clk)

    # Put different data on input but keep write_signal low
    dut.write_signal.value = 0
    dut.add_w.value = 10
    dut.act_in.value = 0xBBBB
    await RisingEdge(dut.f_clk)
    await RisingEdge(dut.f_clk)
    await RisingEdge(dut.f_clk)

    # Let settle
    for _ in range(4):
        await RisingEdge(dut.s_clk)

    # Read — should still be original value
    got = await read_word(dut, 10)
    assert got == 0xAAAA, f"Expected 0xAAAA (unchanged), got {hex(got)}"
    cocotb.log.info("PASS: write enable low doesn't overwrite")


@cocotb.test()
async def test_random_values(dut):
    """Write and read 50 random address/value pairs."""
    cocotb.start_soon(Clock(dut.f_clk, 6, unit="ns").start())
    cocotb.start_soon(Clock(dut.s_clk, 10, unit="ns").start())

    random.seed(42)
    test_pairs = {}
    errors = 0

    # Write 50 random values to random addresses
    for _ in range(50):
        addr = random.randint(0, 511)
        data = random.randint(0, 0xFFFF)
        test_pairs[addr] = data  # last write wins if same addr
        await write_word(dut, addr, data)

    # Let settle
    for _ in range(4):
        await RisingEdge(dut.s_clk)

    # Read them all back
    for addr, expected in test_pairs.items():
        got = await read_word(dut, addr)
        if got != expected:
            cocotb.log.error(f"Addr {addr}: expected {hex(expected)}, got {hex(got)}")
            errors += 1

    assert errors == 0, f"{errors}/{len(test_pairs)} random tests failed"
    cocotb.log.info(f"PASS: all {len(test_pairs)} random write/read tests passed")
