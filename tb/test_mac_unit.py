"""
Golden reference testbench for MAC unit.
Tests: basic multiply, accumulate via psum, sign extension,
       negative numbers, weight loading, activation passthrough.
"""
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, ClockCycles
import random


def mac_golden(weight, activation, psum_in):
    """Python golden reference — what the hardware SHOULD compute."""
    # Signed 8-bit multiply = 16-bit product
    product = weight * activation
    # Sign extend to 32 bits + add psum (Python handles this naturally)
    result = product + psum_in
    return result


@cocotb.test()
async def test_basic_multiply(dut):
    """Weight=3, activation=2, psum_in=0 → psum_out should be 6."""
    clock = Clock(dut.clk, 10, units="ns")  # 100 MHz
    cocotb.start_soon(clock.start())

    # Reset / load weight
    dut.load_w.value = 1
    dut.weight_in.value = 3
    dut.activation_in.value = 0
    dut.PSUM_in.value = 0
    await RisingEdge(dut.clk)

    # Weight loaded, now compute
    dut.load_w.value = 0
    dut.activation_in.value = 2
    dut.PSUM_in.value = 0
    await RisingEdge(dut.clk)

    # Check output
    await RisingEdge(dut.clk)
    expected = mac_golden(3, 2, 0)
    assert dut.PSUM_out.value.signed_integer == expected, \
        f"Expected {expected}, got {dut.PSUM_out.value.signed_integer}"
    cocotb.log.info(f"PASS: 3 * 2 + 0 = {expected}")


@cocotb.test()
async def test_with_psum(dut):
    """Weight=3, activation=2, psum_in=10 → psum_out should be 16."""
    clock = Clock(dut.clk, 10, units="ns")
    cocotb.start_soon(clock.start())

    # Load weight
    dut.load_w.value = 1
    dut.weight_in.value = 3
    dut.activation_in.value = 0
    dut.PSUM_in.value = 0
    await RisingEdge(dut.clk)

    # Compute with psum
    dut.load_w.value = 0
    dut.activation_in.value = 2
    dut.PSUM_in.value = 10
    await RisingEdge(dut.clk)

    await RisingEdge(dut.clk)
    expected = mac_golden(3, 2, 10)
    assert dut.PSUM_out.value.signed_integer == expected, \
        f"Expected {expected}, got {dut.PSUM_out.value.signed_integer}"
    cocotb.log.info(f"PASS: 3 * 2 + 10 = {expected}")


@cocotb.test()
async def test_negative_numbers(dut):
    """Weight=3, activation=-1, psum_in=-5 → psum_out should be -8."""
    clock = Clock(dut.clk, 10, units="ns")
    cocotb.start_soon(clock.start())

    # Load weight
    dut.load_w.value = 1
    dut.weight_in.value = 3
    dut.activation_in.value = 0
    dut.PSUM_in.value = 0
    await RisingEdge(dut.clk)

    # Compute with negative values
    dut.load_w.value = 0
    # -1 in signed 8-bit = 0xFF = 255 unsigned
    dut.activation_in.value = (-1) & 0xFF
    # -5 in signed 32-bit
    dut.PSUM_in.value = (-5) & 0xFFFFFFFF
    await RisingEdge(dut.clk)

    await RisingEdge(dut.clk)
    expected = mac_golden(3, -1, -5)
    assert dut.PSUM_out.value.signed_integer == expected, \
        f"Expected {expected}, got {dut.PSUM_out.value.signed_integer}"
    cocotb.log.info(f"PASS: 3 * -1 + -5 = {expected}")


@cocotb.test()
async def test_activation_passthrough(dut):
    """activation_out should always equal activation_in."""
    clock = Clock(dut.clk, 10, units="ns")
    cocotb.start_soon(clock.start())

    # Load weight (don't care about value)
    dut.load_w.value = 1
    dut.weight_in.value = 0
    dut.activation_in.value = 0
    dut.PSUM_in.value = 0
    await RisingEdge(dut.clk)
    dut.load_w.value = 0

    # Test several activation values pass through
    for val in [0, 1, 42, 127, -1, -128]:
        dut.activation_in.value = val & 0xFF
        await RisingEdge(dut.clk)
        await RisingEdge(dut.clk)
        got = dut.activation_out.value.integer & 0xFF
        expected = val & 0xFF
        assert got == expected, \
            f"Passthrough failed: sent {val}, got {got}"
    cocotb.log.info("PASS: activation passthrough works")


@cocotb.test()
async def test_weight_loading(dut):
    """Load different weights and verify they affect computation."""
    clock = Clock(dut.clk, 10, units="ns")
    cocotb.start_soon(clock.start())

    # Load weight = 5
    dut.load_w.value = 1
    dut.weight_in.value = 5
    dut.activation_in.value = 0
    dut.PSUM_in.value = 0
    await RisingEdge(dut.clk)

    # Compute: 5 * 4 + 0 = 20
    dut.load_w.value = 0
    dut.activation_in.value = 4
    dut.PSUM_in.value = 0
    await RisingEdge(dut.clk)

    await RisingEdge(dut.clk)
    assert dut.PSUM_out.value.signed_integer == 20, \
        f"Expected 20, got {dut.PSUM_out.value.signed_integer}"

    # Now load NEW weight = -2
    dut.load_w.value = 1
    dut.weight_in.value = (-2) & 0xFF
    await RisingEdge(dut.clk)

    # Compute: -2 * 4 + 0 = -8
    dut.load_w.value = 0
    dut.activation_in.value = 4
    dut.PSUM_in.value = 0
    await RisingEdge(dut.clk)

    await RisingEdge(dut.clk)
    assert dut.PSUM_out.value.signed_integer == -8, \
        f"Expected -8, got {dut.PSUM_out.value.signed_integer}"
    cocotb.log.info("PASS: weight loading works correctly")


@cocotb.test()
async def test_random_values(dut):
    """Test 50 random weight/activation/psum combinations."""
    clock = Clock(dut.clk, 10, units="ns")
    cocotb.start_soon(clock.start())

    random.seed(42)
    errors = 0

    for i in range(50):
        weight = random.randint(-128, 127)
        activation = random.randint(-128, 127)
        psum_in = random.randint(-2**30, 2**30)

        # Load weight
        dut.load_w.value = 1
        dut.weight_in.value = weight & 0xFF
        dut.activation_in.value = 0
        dut.PSUM_in.value = 0
        await RisingEdge(dut.clk)

        # Compute
        dut.load_w.value = 0
        dut.activation_in.value = activation & 0xFF
        dut.PSUM_in.value = psum_in & 0xFFFFFFFF
        await RisingEdge(dut.clk)

        await RisingEdge(dut.clk)
        expected = mac_golden(weight, activation, psum_in)
        got = dut.PSUM_out.value.signed_integer

        if got != expected:
            cocotb.log.error(f"FAIL [{i}]: {weight} * {activation} + {psum_in} = {expected}, got {got}")
            errors += 1

    assert errors == 0, f"{errors}/50 random tests failed"
    cocotb.log.info("PASS: all 50 random tests passed")
