"""
Golden reference testbench for DMA engine.
Simulates a fake SDRAM controller responding to the DMA's requests.
Tests: basic burst transfer, address passthrough, counter/BRAM addressing,
       write enable timing, done signal, multiple back-to-back transfers.
"""
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer
import random


async def reset_dma(dut):
    """Assert reset for a few cycles."""
    dut.rst.value = 1
    dut.start.value = 0
    dut.sdram_addr.value = 0
    dut.ready.value = 0
    dut.s2f_data.value = 0
    dut.s2f_data_valid.value = 0
    for _ in range(3):
        await RisingEdge(dut.clk)
    dut.rst.value = 0
    await RisingEdge(dut.clk)


async def run_sdram_burst(dut, burst_data, ready_delay=2, activate_delay=3):
    """
    Simulate SDRAM controller behavior:
    1. Wait for rw_en to go high
    2. Wait ready_delay cycles, then assert ready
    3. Wait activate_delay cycles (row activate + CAS latency)
    4. Stream burst_data with s2f_data_valid high
    5. Drop s2f_data_valid and reassert ready
    """
    # Wait for DMA to assert rw_en
    while True:
        await RisingEdge(dut.clk)
        await Timer(1, units="ns")
        if dut.rw_en.value == 1:
            break

    # Simulate controller becoming ready after some delay
    for _ in range(ready_delay):
        await RisingEdge(dut.clk)
    dut.ready.value = 1
    await RisingEdge(dut.clk)
    dut.ready.value = 0

    # Simulate row activate + CAS latency
    for _ in range(activate_delay):
        await RisingEdge(dut.clk)

    # Stream burst data
    # Assert valid one cycle early so DMA transitions WAIT→BURST
    # Then data starts flowing when DMA is in BURST with we_a high
    dut.s2f_data_valid.value = 1
    dut.s2f_data.value = 0
    await RisingEdge(dut.clk)
    for word in burst_data:
        dut.s2f_data.value = word
        await RisingEdge(dut.clk)

    # End burst
    dut.s2f_data_valid.value = 0
    dut.s2f_data.value = 0
    await RisingEdge(dut.clk)

    # Controller ready again
    dut.ready.value = 1


@cocotb.test()
async def test_basic_burst(dut):
    """DMA should complete a full burst and assert done."""
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset_dma(dut)

    burst_data = list(range(10))  # 10 words: 0, 1, 2, ..., 9

    # Start the SDRAM simulation in background
    cocotb.start_soon(run_sdram_burst(dut, burst_data))

    # Tell DMA to go
    dut.sdram_addr.value = 0x1234
    dut.start.value = 1
    await RisingEdge(dut.clk)
    dut.start.value = 0

    # Wait for done
    for _ in range(50):
        await RisingEdge(dut.clk)
        await Timer(1, units="ns")
        if dut.done.value == 1:
            break
    else:
        assert False, "DMA never asserted done"

    cocotb.log.info("PASS: basic burst completed")


@cocotb.test()
async def test_address_passthrough(dut):
    """DMA should pass sdram_addr through to f_addr in REQUEST state."""
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset_dma(dut)

    test_addr = 0x5A5A

    cocotb.start_soon(run_sdram_burst(dut, [0xBEEF]))

    dut.sdram_addr.value = test_addr
    dut.start.value = 1
    await RisingEdge(dut.clk)
    dut.start.value = 0

    # Check f_addr while in REQUEST state
    # DMA should be in REQUEST now, driving f_addr
    await Timer(1, units="ns")
    got = dut.f_addr.value.to_unsigned()
    assert got == test_addr, f"f_addr: expected {hex(test_addr)}, got {hex(got)}"

    # Also check rw is 1 (read mode)
    assert dut.rw.value == 1, "rw should be 1 (read mode) in REQUEST"
    assert dut.rw_en.value == 1, "rw_en should be 1 in REQUEST"

    # Let it finish
    for _ in range(50):
        await RisingEdge(dut.clk)

    cocotb.log.info("PASS: address passthrough correct")


@cocotb.test()
async def test_bram_write_signals(dut):
    """During burst, DMA should drive we_a, din_a, and increment addr_a."""
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset_dma(dut)

    burst_data = [0xAA00, 0xBB11, 0xCC22, 0xDD33, 0xEE44]

    cocotb.start_soon(run_sdram_burst(dut, burst_data))

    dut.sdram_addr.value = 0
    dut.start.value = 1
    await RisingEdge(dut.clk)
    dut.start.value = 0

    # Wait until we_a goes high (BURST state)
    for _ in range(30):
        await RisingEdge(dut.clk)
        await Timer(1, units="ns")
        if dut.we_a.value == 1:
            # Capture this first word too
            captured = [dut.din_a.value.to_unsigned()]
            addresses = [dut.addr_a.value.to_unsigned()]
            break

    # Capture remaining burst writes (stop when data_valid drops)
    while True:
        await RisingEdge(dut.clk)
        await Timer(1, units="ns")
        if dut.s2f_data_valid.value != 1:
            break
        captured.append(dut.din_a.value.to_unsigned())
        addresses.append(dut.addr_a.value.to_unsigned())

    # Verify data matches
    assert captured == burst_data, f"Data mismatch: expected {burst_data}, got {captured}"

    # Verify addresses are sequential starting from 0
    expected_addrs = list(range(len(burst_data)))
    assert addresses == expected_addrs, f"Addresses: expected {expected_addrs}, got {addresses}"

    cocotb.log.info("PASS: BRAM write signals correct")


@cocotb.test()
async def test_we_off_outside_burst(dut):
    """we_a should be 0 when not in BURST state."""
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset_dma(dut)

    # Check we_a is 0 in IDLE
    await Timer(1, units="ns")
    assert dut.we_a.value == 0, "we_a should be 0 in IDLE"

    cocotb.start_soon(run_sdram_burst(dut, [0x1234]))

    dut.sdram_addr.value = 0
    dut.start.value = 1
    await RisingEdge(dut.clk)
    dut.start.value = 0

    # Check we_a is 0 in REQUEST
    await Timer(1, units="ns")
    assert dut.we_a.value == 0, "we_a should be 0 in REQUEST"

    # Wait for done
    for _ in range(50):
        await RisingEdge(dut.clk)
        await Timer(1, units="ns")
        if dut.done.value == 1:
            break

    # Check we_a is 0 in DONE
    assert dut.we_a.value == 0, "we_a should be 0 in DONE"

    cocotb.log.info("PASS: we_a off outside BURST")


@cocotb.test()
async def test_done_pulses_one_cycle(dut):
    """done should be high for exactly one cycle."""
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset_dma(dut)

    cocotb.start_soon(run_sdram_burst(dut, [0x42]))

    dut.sdram_addr.value = 0
    dut.start.value = 1
    await RisingEdge(dut.clk)
    dut.start.value = 0

    # Wait for done
    done_count = 0
    for _ in range(50):
        await RisingEdge(dut.clk)
        await Timer(1, units="ns")
        if dut.done.value == 1:
            done_count += 1

    assert done_count == 1, f"done was high for {done_count} cycles, expected 1"

    cocotb.log.info("PASS: done pulses for exactly one cycle")


@cocotb.test()
async def test_back_to_back_transfers(dut):
    """Run two transfers in a row, verify both complete correctly."""
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset_dma(dut)

    # First transfer
    burst1 = [0x1000 + i for i in range(8)]
    cocotb.start_soon(run_sdram_burst(dut, burst1))

    dut.sdram_addr.value = 0x0010
    dut.start.value = 1
    await RisingEdge(dut.clk)
    dut.start.value = 0

    # Wait for first done
    for _ in range(50):
        await RisingEdge(dut.clk)
        await Timer(1, units="ns")
        if dut.done.value == 1:
            break
    else:
        assert False, "First transfer never completed"

    await RisingEdge(dut.clk)

    # Second transfer
    burst2 = [0x2000 + i for i in range(5)]
    cocotb.start_soon(run_sdram_burst(dut, burst2))

    dut.sdram_addr.value = 0x0020
    dut.start.value = 1
    await RisingEdge(dut.clk)
    dut.start.value = 0

    # Wait for second done
    for _ in range(50):
        await RisingEdge(dut.clk)
        await Timer(1, units="ns")
        if dut.done.value == 1:
            break
    else:
        assert False, "Second transfer never completed"

    cocotb.log.info("PASS: back-to-back transfers work")
