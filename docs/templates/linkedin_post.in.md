# LinkedIn post: SKY130 SRAM

🧠 A 6T SRAM in 130 nm, from a Python script to a sign-off-clean layout, with open-source tools only

This is a 64-word × 32-bit static RAM on SkyWater's open-source SKY130 process: schematic, layout and verification generated from code.

The design in three ideas:
🔹 The bit cell is full custom, but drawn by code. One Python function turns the transistor sizes and the design rules into the layout of the 6T cell; the array, the well taps and the power rails follow from it
🔹 No SRAM rule waivers. The cell uses the ordinary logic design rules, so the stock DRC decks apply as they are. The price: about twice the area of the foundry's cell
🔹 No sense amplifier, no self-timed pulses. The bit lines swing rail to rail, a plain inverter senses them, and one tri-state buffer per bit line does precharge, write and keeper. The periphery is ordinary Verilog, placed and routed by OpenROAD

📊 Results (sign-off checks and SPICE on the final layout; no silicon):
✅ %MOSFETS% transistors in 225 × 156 µm
✅ 0 DRC violations in Magic and in KLayout's PDK deck, two independent checkers
✅ LVS matches transistor by transistor, flat, no black boxes: %LVSDEV% devices
✅ Post-layout SPICE passes at the slow, typical and fast corners; data is out %TCQ_TT% ns after the clock edge (typical), %TCQ_SS% ns at the slow corner
✅ Still works with a clock period of %TMIN_SS% ns at the slow corner in SPICE; the data sheet specifies %TSPEC_SS% ns (%FSPEC_SS% MHz)
✅ Cell margins: read noise margin ≥ %READ_WORST% mV over all corners, 0 failures in %MC_N% Monte Carlo cells per condition
✅ GDS, LEF, Liberty for three corners and a Verilog model, plus a March C- self-test that was placed and routed together with the macro
⚠️ Nothing has been fabricated. Clean sign-off makes a design ready for a test chip, not proven
⚠️ The Monte Carlo spread is only as good as the PDK's mismatch models
⚠️ Wire resistance is not in the SPICE netlist, and there is no redundancy or ECC

What the project taught me:
💡 Robust beats clever. For a small memory, full-swing bit lines and two clock phases remove a whole class of analog timing risks. If a phase is too short on silicon, you slow the clock down
💡 Design rules shape the circuit. Without the butted contacts of a foundry cell, the two cross-coupling wires decide how wide the cell is
💡 Tools assume ordinary clocks. The clock-tree tool followed my phase clock through the word-line gates onto the bit lines and crashed. A clock that ends in a memory cell needs its tree built by hand
💡 Simulating 20,000 transistors needed a detour: the simulator copied every model variant of the process for every transistor, about 1 MB each, until the laptop ran out of memory. Writing one model per transistor size fixed it

A short tour, from the cell to the finished layout, is in the video 👇
Code, layout and all reports: %REPO_URL%

#ICDesign #SRAM #MemoryDesign #SKY130 #OpenSourceSilicon #VLSI #Python #EDA
