# fpga-face

FPGA-based neural network accelerator for face recognition, targeting the Altera Cyclone IV EP4CE115 (DE2-115 board). Pipeline: camera -> BlazeFace detection -> crop -> MobileFaceNet recognition -> cosine similarity.

Companion to [tinyml-face](https://github.com/Felixnsg/tinyml-face), which runs the same task on an ESP32.

## Status

In progress. Five RTL modules complete and verified in simulation.

| Module | Tests |
|---|---|
| `mac_unit` | 6/6 |
| `mac_array` (16x16) | 6/6 |
| `requant_unit` | 8/8 |
| `bram_buffer` | 6/6 |
| `dma_engine` | 6/6 |

Currently implementing the depthwise separable convolution engine.

## Architecture

- 16x16 weight-stationary systolic array (256 INT8 MACs) for pointwise convolution
- Separate 16-channel depthwise engine (planned)
- Hybrid memory: weights in external SRAM, activations in external SDRAM, double-buffered on-chip BRAM tiles
- INT32 to INT8 requantization with per-channel scaling

## Target hardware

DE2-115 (Cyclone IV EP4CE115):

- 114,480 logic elements
- 266 embedded 18x18 multipliers (up to 532 INT8 MACs in 9x9 mode)
- 432 M9K BRAM blocks (486 KB on-chip)
- 2 MB external SRAM, 128 MB external SDRAM

## Running the tests

Requires Icarus Verilog and cocotb.

```
cd tb
make -f Makefile.mac
make -f Makefile.array
make -f Makefile.requant
make -f Makefile.bram
make -f Makefile.dma
```

## Stack

Verilog, Icarus Verilog, Verilator, cocotb, Yosys, Surfer, Quartus.
