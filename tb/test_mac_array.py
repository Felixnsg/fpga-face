"""
Golden reference testbench for 16x16 MAC array.
Tests: uniform weights, per-MAC addressing, row independence,
       negative values, activation broadcast, random full-array test.
"""
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge
import random


def get_psum(dut, row):
    """Extract 32-bit signed PSUM for a given row from the 512-bit bus."""
    full = dut.PSUM_out.value
    # Extract 32 bits for this row
    chunk = (int(full) >> (row * 32)) & 0xFFFFFFFF
    # Convert to signed
    if chunk >= (1 << 31):
        chunk -= (1 << 32)
    return chunk


def array_golden(weights, activation):
    """
    Golden reference for one activation through the array.
    weights[r][c] = weight at row r, column c.
    Each row computes: sum over c of (activation * weights[r][c]).
    With same activation at every column, row r output = activation * sum(weights[r]).
    """
    results = []
    for r in range(16):
        psum = 0
        for c in range(16):
            psum += activation * weights[r][c]
        results.append(psum)
    return results


async def load_weight(dut, row, col, value):
    """Load a single weight into MAC at (row, col)."""
    dut.load_w.value = 1
    dut.row_sel.value = row
    dut.col_sel.value = col
    dut.weight_in.value = value & 0xFF
    await RisingEdge(dut.clk)
    dut.load_w.value = 0


async def load_all_weights(dut, weights):
    """Load a 16x16 weight matrix into the array."""
    for r in range(16):
        for c in range(16):
            await load_weight(dut, r, c, weights[r][c])


@cocotb.test()
async def test_uniform_weights(dut):
    """All MACs have weight=2, activation=3. Each row should output 3*2*16=96."""
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())

    # Load weight=2 into every MAC
    weights = [[2]*16 for _ in range(16)]
    await load_all_weights(dut, weights)

    # Feed activation=3
    dut.activation_in.value = 3
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)

    expected = 3 * 2 * 16  # 96
    for r in range(16):
        got = get_psum(dut, r)
        assert got == expected, \
            f"Row {r}: expected {expected}, got {got}"
    cocotb.log.info(f"PASS: all rows output {expected}")


@cocotb.test()
async def test_row_independence(dut):
    """Each row has a different weight. Verify rows compute independently."""
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())

    # Row r gets weight = r+1 in every column
    weights = [[(r + 1)] * 16 for r in range(16)]
    await load_all_weights(dut, weights)

    # Feed activation=1
    dut.activation_in.value = 1
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)

    for r in range(16):
        expected = 1 * (r + 1) * 16
        got = get_psum(dut, r)
        assert got == expected, \
            f"Row {r}: expected {expected}, got {got}"
    cocotb.log.info("PASS: rows compute independently")


@cocotb.test()
async def test_different_weights_per_column(dut):
    """Each column has a different weight. Tests PSUM chaining."""
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())

    # All rows: weight at column c = c+1 (1,2,3,...,16)
    weights = [[c + 1 for c in range(16)] for _ in range(16)]
    await load_all_weights(dut, weights)

    # Feed activation=2
    dut.activation_in.value = 2
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)

    # Expected: 2 * (1+2+3+...+16) = 2 * 136 = 272
    expected = 2 * sum(range(1, 17))
    for r in range(16):
        got = get_psum(dut, r)
        assert got == expected, \
            f"Row {r}: expected {expected}, got {got}"
    cocotb.log.info(f"PASS: PSUM chains correctly, all rows = {expected}")


@cocotb.test()
async def test_negative_weights(dut):
    """Test with negative weights and activations."""
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())

    # All MACs get weight = -3
    weights = [[-3] * 16 for _ in range(16)]
    await load_all_weights(dut, weights)

    # Feed activation = -2
    dut.activation_in.value = (-2) & 0xFF
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)

    # (-2) * (-3) * 16 = 96
    expected = (-2) * (-3) * 16
    for r in range(16):
        got = get_psum(dut, r)
        assert got == expected, \
            f"Row {r}: expected {expected}, got {got}"
    cocotb.log.info(f"PASS: negative math works, all rows = {expected}")


@cocotb.test()
async def test_single_mac_addressing(dut):
    """Load weight=10 into only MAC(0,0), rest stay 0. Only that MAC contributes."""
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())

    # Load all weights to 0 first
    weights = [[0] * 16 for _ in range(16)]
    await load_all_weights(dut, weights)

    # Now load weight=10 into just MAC(0,0)
    await load_weight(dut, 0, 0, 10)

    # Feed activation=5
    dut.activation_in.value = 5
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)

    # Row 0: 5 * 10 = 50, all other rows: 0
    assert get_psum(dut, 0) == 50, \
        f"Row 0: expected 50, got {get_psum(dut, 0)}"
    for r in range(1, 16):
        assert get_psum(dut, r) == 0, \
            f"Row {r}: expected 0, got {get_psum(dut, r)}"
    cocotb.log.info("PASS: single MAC addressing works")


@cocotb.test()
async def test_random_full_array(dut):
    """Random 16x16 weights, random activation. Compare against golden ref."""
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())

    random.seed(42)

    errors = 0
    for trial in range(5):
        # Random weights
        weights = [[random.randint(-128, 127) for _ in range(16)] for _ in range(16)]
        await load_all_weights(dut, weights)

        # Random activation
        act = random.randint(-128, 127)
        dut.activation_in.value = act & 0xFF
        await RisingEdge(dut.clk)
        await RisingEdge(dut.clk)

        # Check against golden reference
        expected = array_golden(weights, act)
        for r in range(16):
            got = get_psum(dut, r)
            if got != expected[r]:
                cocotb.log.error(
                    f"Trial {trial} Row {r}: expected {expected[r]}, got {got}")
                errors += 1

    assert errors == 0, f"{errors} mismatches in random test"
    cocotb.log.info("PASS: 5 random full-array tests passed")
