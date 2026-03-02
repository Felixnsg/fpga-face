"""
Golden reference testbench for requantization unit.
Tests: basic requant, clamp high, clamp low, negative values,
       zero point offset, parameter loading, random values.
"""
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge
import random


def requant_golden(psum, multiplier, shift, zero_point):
    """Python golden reference for requantization."""
    # Multiply
    product = psum * multiplier
    # Arithmetic right shift
    if shift > 0:
        # Python >> on negative numbers already does arithmetic shift
        shifted = product >> shift
    else:
        shifted = product
    # Add zero point
    result = shifted + zero_point
    # Clamp to INT8 range
    if result > 127:
        result = 127
    elif result < -128:
        result = -128
    return result


async def load_params(dut, multiplier, shift, zero_point):
    """Load requantization parameters."""
    dut.load_p.value = 1
    dut.big_int_in.value = multiplier & 0xFFFFFFFF
    dut.shift_log_in.value = shift & 0x1F
    dut.zp_in.value = zero_point & 0xFF
    await RisingEdge(dut.clk)
    dut.load_p.value = 0


@cocotb.test()
async def test_basic_requant(dut):
    """PSUM=1000, multiplier=1073741824, shift=28, zp=0. Should give ~4."""
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())

    # multiplier=1073741824, shift=28 => scale ~= 1073741824/2^28 = 4.0
    # So PSUM=1000 * 4.0 = 4000... wait that's too big
    # Let's use: multiplier=1073741824, shift=30 => scale ~= 1.0
    # PSUM=50 => 50 * 1.0 = 50
    multiplier = 1073741824  # ~2^30
    shift = 30
    zp = 0

    await load_params(dut, multiplier, shift, zp)

    dut.PSUM_in.value = 50
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)

    expected = requant_golden(50, multiplier, shift, zp)
    got = dut.PSUM_out_q.value.to_signed()
    assert got == expected, f"Expected {expected}, got {got}"
    cocotb.log.info(f"PASS: basic requant, 50 -> {expected}")


@cocotb.test()
async def test_clamp_high(dut):
    """Result exceeds 127, should clamp to 127."""
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())

    # scale ~= 1.0, PSUM=200 => should clamp to 127
    multiplier = 1073741824
    shift = 30
    zp = 0

    await load_params(dut, multiplier, shift, zp)

    dut.PSUM_in.value = 200
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)

    got = dut.PSUM_out_q.value.to_signed()
    assert got == 127, f"Expected 127 (clamped), got {got}"
    cocotb.log.info("PASS: clamp high works")


@cocotb.test()
async def test_clamp_low(dut):
    """Result below -128, should clamp to -128."""
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())

    multiplier = 1073741824
    shift = 30
    zp = 0

    await load_params(dut, multiplier, shift, zp)

    dut.PSUM_in.value = (-200) & 0xFFFFFFFF
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)

    got = dut.PSUM_out_q.value.to_signed()
    assert got == -128, f"Expected -128 (clamped), got {got}"
    cocotb.log.info("PASS: clamp low works")


@cocotb.test()
async def test_with_zero_point(dut):
    """Zero point shifts the output."""
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())

    # scale ~= 1.0, PSUM=50, zp=10 => 50+10 = 60
    multiplier = 1073741824
    shift = 30
    zp = 10

    await load_params(dut, multiplier, shift, zp)

    dut.PSUM_in.value = 50
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)

    expected = requant_golden(50, multiplier, shift, zp)
    got = dut.PSUM_out_q.value.to_signed()
    assert got == expected, f"Expected {expected}, got {got}"
    cocotb.log.info(f"PASS: zero point works, 50 + zp=10 -> {expected}")


@cocotb.test()
async def test_negative_zero_point(dut):
    """Negative zero point."""
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())

    multiplier = 1073741824
    shift = 30
    zp = -5

    await load_params(dut, multiplier, shift, zp)

    dut.PSUM_in.value = 50
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)

    expected = requant_golden(50, multiplier, shift, zp)
    got = dut.PSUM_out_q.value.to_signed()
    assert got == expected, f"Expected {expected}, got {got}"
    cocotb.log.info(f"PASS: negative zero point, 50 + zp=-5 -> {expected}")


@cocotb.test()
async def test_small_scale(dut):
    """Small scale factor — large PSUM gets scaled down."""
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())

    # scale = 1073741824 / 2^30 * (1/100) ≈ 0.01
    # Actually let's do: multiplier=10737418, shift=30 => ~0.01
    multiplier = 10737418
    shift = 30
    zp = 0

    await load_params(dut, multiplier, shift, zp)

    dut.PSUM_in.value = 5000
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)

    expected = requant_golden(5000, multiplier, shift, zp)
    got = dut.PSUM_out_q.value.to_signed()
    assert got == expected, f"Expected {expected}, got {got}"
    cocotb.log.info(f"PASS: small scale, 5000 -> {expected}")


@cocotb.test()
async def test_param_reload(dut):
    """Load params, compute, reload different params, compute again."""
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())

    # First params: scale ~= 1.0
    await load_params(dut, 1073741824, 30, 0)
    dut.PSUM_in.value = 42
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)

    got1 = dut.PSUM_out_q.value.to_signed()
    expected1 = requant_golden(42, 1073741824, 30, 0)
    assert got1 == expected1, f"First: expected {expected1}, got {got1}"

    # Reload with scale ~= 0.5
    await load_params(dut, 536870912, 30, 5)
    dut.PSUM_in.value = 42
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)

    got2 = dut.PSUM_out_q.value.to_signed()
    expected2 = requant_golden(42, 536870912, 30, 5)
    assert got2 == expected2, f"Second: expected {expected2}, got {got2}"

    cocotb.log.info(f"PASS: param reload works, {got1} then {got2}")


@cocotb.test()
async def test_random_values(dut):
    """30 random PSUM/param combinations against golden reference."""
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())

    random.seed(42)
    errors = 0

    for i in range(30):
        psum = random.randint(-100000, 100000)
        multiplier = random.randint(1, 2**31 - 1)
        shift = random.randint(20, 31)
        zp = random.randint(-128, 127)

        await load_params(dut, multiplier, shift, zp)

        dut.PSUM_in.value = psum & 0xFFFFFFFF
        await RisingEdge(dut.clk)
        await RisingEdge(dut.clk)

        expected = requant_golden(psum, multiplier, shift, zp)
        got = dut.PSUM_out_q.value.to_signed()

        if got != expected:
            cocotb.log.error(
                f"FAIL [{i}]: psum={psum}, mult={multiplier}, "
                f"shift={shift}, zp={zp}: expected {expected}, got {got}")
            errors += 1

    assert errors == 0, f"{errors}/30 random tests failed"
    cocotb.log.info("PASS: all 30 random tests passed")
