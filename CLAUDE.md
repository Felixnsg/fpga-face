# CLAUDE.md - FPGA Neural Network Accelerator

## Project Overview
FPGA-based neural network accelerator for MobileFaceNet + BlazeFace face recognition. Targeting DE2-115 (Cyclone IV EP4CE115) from school. Companion project to tinyml-face (ESP32 version).

## Target Hardware: DE2-115 / Cyclone IV EP4CE115
- 114,480 Logic Elements
- 266 embedded 18x18 multipliers (532 INT8 MACs in 9×9 mode)
- 432 M9K BRAM blocks (486 KB on-chip SRAM)
- 2 MB external SRAM, 128 MB external SDRAM
- Constraint: Can't take board home, no admin on school PCs. Write/simulate on Mac, flash at school.

## Architecture
- 16×16 weight-stationary systolic array (256 MACs) for pointwise convolution
- Dedicated 16-channel depthwise engine (72 multipliers)
- Hybrid memory: weights in SRAM, activations in SDRAM, double-buffered BRAM tiles
- Pipeline: OV7670 camera → BlazeFace → crop → MobileFaceNet → cosine similarity
- Target: ~12-16 ms full pipeline, ~60+ FPS, ~1,200× speedup over ESP32

## Rules
1. **Open communication** — Claude explains everything, never does things silently. Felix designs, Claude guides. When Felix asks "how do I build X?", Claude asks "how do you think it should work?" first. Every question is valid.
2. **Clear checkpoint workflow** — Every module follows: design → write → lint → simulate → view waveforms → verify → commit. No skipping steps.
3. **Documentation as we go** — Write the technical paper while building. Raw log (including failures) + polished version (what worked).
4. **Felix writes the Verilog** — Claude can show code, but Felix types it and understands it. Claude writes Python testbenches, build scripts, automation (not learning scope).
5. **One module at a time** — Don't start the next module until the current one passes simulation.
6. **Golden reference first** — Write Python expected output BEFORE testing the Verilog.
7. **Git after every working module** — Commit when a module passes its testbench. Never break main.
8. **Simulation before synthesis** — Prove design in simulation on Mac before Quartus at school.

## Directory Structure
```
fpga-face/
├── rtl/          # Verilog source files (Felix writes these)
├── tb/           # cocotb testbenches (Claude writes these)
├── sim/          # simulation outputs (waveforms, logs)
├── docs/         # design docs, diagrams, technical paper, roadmap
├── scripts/      # build/sim automation scripts
└── constraints/  # Quartus pin assignments, timing constraints (for school)
```

## Toolchain (all on Mac)
- Icarus Verilog 12.0 — simulator
- Verilator 5.044 — fast simulator + linter
- Surfer 0.6.0 — waveform viewer
- Yosys 0.62 — resource estimation
- Verible — linter/formatter
- cocotb 2.0.1 — Python testbenches
- Quartus — synthesis + programming (school PCs only)

## Checkpoint Workflow (per module)
1. **Design** — discuss hardware architecture, Felix proposes solution
2. **Golden ref** — Claude writes Python expected behavior in cocotb testbench
3. **Write RTL** — Felix writes the Verilog
4. **Lint** — verilator --lint-only, fix warnings
5. **Simulate** — Icarus + cocotb testbench
6. **Waveforms** — open in Surfer, verify signals visually
7. **Resource check** — Yosys for LE/multiplier/BRAM estimates
8. **Commit** — git commit the passing module
9. **Document** — update technical paper

## Build Phases
0. Setup + learning (DONE)
1. Single MAC unit — CURRENT
2. Systolic array (16×16)
3. Requantization unit
4. SDRAM controller integration
5. Multi-layer controller
6. Depthwise convolution engine
7. Full MobileFaceNet inference
8. BlazeFace + full pipeline
9. OV7670 camera integration + live demo

## Roadmap
See docs/roadmap.md for detailed per-phase checkpoints.

## Research
Detailed research notes in Claude's memory files:
- fpga_research_round1.md (hardware, feasibility, open-source projects, silicon path)
- fpga_research_round2.md (SDRAM, INT8, DW conv, PReLU, Nios II, synthesis, testing, etc.)
