# FPGA Accelerator Roadmap

## Who Does What
- **Felix writes**: All Verilog/SystemVerilog (hardware design). Every line, every module.
- **Claude writes**: Python testbenches (cocotb), build/sim scripts, automation. Not the learning scope — just support tooling.
- **Both**: Design discussions. Felix proposes, Claude validates/corrects.

---

## Phase 1: Single MAC Unit
*Goal: One working multiply-accumulate unit, fully tested in simulation.*

### 1.1 Design Understanding
- [ ] Felix draws a MAC unit on paper: inputs, outputs, what happens inside
- [ ] Discuss: what are the inputs? (two INT8 numbers, clock, clear signal)
- [ ] Discuss: what is the output? (32-bit accumulator value)
- [ ] Discuss: what happens each clock cycle? (multiply, sign-extend, add to accumulator)
- [ ] Discuss: when does the accumulator reset? (clear signal)
- [ ] Felix draws the timing diagram: clock edges, when data appears, when output updates

### 1.2 Golden Reference (Claude writes)
- [ ] Claude writes a Python function that does the exact same math
- [ ] Claude writes the cocotb testbench skeleton
- [ ] Felix reviews and understands what the testbench checks

### 1.3 Write the Verilog (Felix writes)
- [ ] Felix writes `mac_unit.v` — module declaration, ports, internal signals
- [ ] Felix writes the multiply logic (signed multiplication)
- [ ] Felix writes the accumulate logic (sign extension + addition)
- [ ] Felix writes the clear/reset logic
- [ ] Review together: does this match the paper design?

### 1.4 Lint
- [ ] Run verilator --lint-only on mac_unit.v
- [ ] Fix any warnings (signed/unsigned mismatches, unused signals, etc.)

### 1.5 Simulate
- [ ] Run cocotb testbench with Icarus Verilog
- [ ] All test cases pass (basic multiply, accumulate, clear, edge cases, overflow)

### 1.6 Waveforms
- [ ] Open waveform in Surfer
- [ ] Felix traces through the signals: clock, inputs, product, accumulator
- [ ] Verify timing matches the paper diagram

### 1.7 Resource Estimate
- [ ] Run through Yosys: how many LEs, does it use a hard multiplier?
- [ ] Compare to our budget expectations (~1 multiplier block, ~40-50 LEs)

### 1.8 Commit + Document
- [ ] Git commit mac_unit.v + testbench
- [ ] Write a short entry in the technical doc: what we built, what we learned

---

## Phase 2: Systolic Array (16x16)
*Goal: 256 MAC units organized as a weight-stationary systolic array, tested in simulation.*

### 2.1 Design Understanding
- [ ] Felix draws the 4x4 array on paper first (simpler)
- [ ] Trace data flow: where do weights load, how do activations flow, where do partial sums go
- [ ] Discuss: how do we scale from 4x4 to 16x16
- [ ] Felix draws the timing: fill latency, steady state, drain
- [ ] Discuss: what control signals does the array need

### 2.2 Golden Reference (Claude writes)
- [ ] Python matrix multiply reference
- [ ] cocotb testbench for the array

### 2.3 Build Incrementally (Felix writes)
- [ ] Single PE (processing element) with weight register + partial sum passing
- [ ] 1x4 row (one row of 4 PEs)
- [ ] 4x4 array
- [ ] Test at each step
- [ ] Scale to 16x16
- [ ] Full simulation with known weight/activation matrices

### 2.4 Lint + Simulate + Waveforms + Resource Check + Commit

---

## Phase 3: Requantization Unit
*Goal: INT32 accumulator → INT8 output, bit-exact with TFLite.*

### 3.1 Design Understanding
- [ ] Understand the TFLite requantization pipeline (M0, shift, round, clamp)
- [ ] Felix draws the datapath: multiply by M0, shift, add zero point, clamp
- [ ] Discuss: what precision is needed at each stage

### 3.2-3.8: Same checkpoint pattern as Phase 1

---

## Phase 4: Memory Interface (SDRAM Controller)
*Goal: Read/write data to SDRAM from FPGA.*

(Detailed checkpoints TBD when we get here)

---

## Phase 5: DMA Engine + Multi-Layer Controller
*Goal: FSM that fetches activation data from SDRAM into BRAM buffers, and a controller that orchestrates layer-by-layer inference.*

### 5.1 DMA Engine — Design Understanding
- [x] Felix draws FSM state diagram on paper (5 states: IDLE→REQUEST→WAIT→BURST→DONE)
- [x] Define all transitions (what signal moves between each state)
- [x] Define all outputs per state (what each state drives)
- [x] Explain every port/signal with purpose, width, and direction
- [ ] Felix understands the complete picture and is ready to write

### 5.2 DMA Engine — Golden Reference (Claude writes)
- [ ] Claude writes cocotb testbench with fake SDRAM model
- [ ] Felix reviews and understands what the testbench checks

### 5.3 DMA Engine — Write RTL (Felix writes)
- [ ] Felix writes dma_engine.v — sequential always block (state register + counter)
- [ ] Felix writes dma_engine.v — combinational always block (case statement with 5 states)
- [ ] Review together: does this match the paper FSM?

### 5.4 DMA Engine — Lint + Simulate + Waveforms + Commit

### 5.5 Multi-Layer Controller — Design Understanding
- [ ] Discuss what "layer parameters" the controller needs to store
- [ ] Discuss how it sequences: load weights → load activations → compute → store results → next layer
- [ ] Felix draws the FSM
- [ ] Define all ports, transitions, and outputs

### 5.6-5.8 Multi-Layer Controller — Golden ref, Write RTL, Lint/Sim/Commit

---

## Phase 6: Depthwise Convolution Engine
*Goal: Dedicated 3x3 depthwise conv unit, 16-channel parallel.*

(Detailed checkpoints TBD)

---

## Phase 7: Full MobileFaceNet Inference
*Goal: All layers running end-to-end, correct output verified against TFLite.*

(Detailed checkpoints TBD)

---

## Phase 8: BlazeFace + Full Pipeline
*Goal: Detection → crop → recognition → "Felix detected" output.*

(Detailed checkpoints TBD)

---

## Phase 9: OV7670 Camera Integration
*Goal: Live camera feed → face detection → recognition → real-time demo.*

(Detailed checkpoints TBD)

---

## Current Position
**Phase 5, Step 5.1** — DMA engine design. Phases 1-4 complete. FSM transitions and outputs defined. Felix ready to write Verilog.
