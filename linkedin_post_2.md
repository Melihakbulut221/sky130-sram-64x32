# LinkedIn post 2: SKY130 SRAM (story version)

💥 My laptop ran out of memory while simulating a memory.

The memory holds 2,048 bits. The simulator asked for 18 GB to check it. The laptop has 16.

That was one of four surprises on the way to a 6T SRAM macro on SkyWater's open-source 130 nm process (SKY130), designed, laid out and verified with open-source tools only 👇

🔹 Surprise 1: 1 MB per transistor. The process models wrap every transistor in a package that contains all of its size variants, and the simulator copied that package about 20,000 times. Writing one model per transistor size, ten in total, brought the full post-layout simulation back onto a laptop. Same currents, checked
🔹 Surprise 2: the clock-tree tool crashed. It followed my clock through the word-line gates and onto the bit lines. A clock that ends in a memory cell is not what it expects. Three hand-placed buffers did the job instead
🔹 Surprise 3: the best sense amplifier was no sense amplifier. The bit lines swing rail to rail, a plain inverter reads them, and one tri-state buffer per bit line does precharge, write and keeper. No analog timing to tune: if a phase is too short, you slow the clock down
🔹 Surprise 4: I made the cell twice as big on purpose. Foundry SRAM cells rely on special design rules. This one uses the ordinary logic rules, so the stock DRC decks apply with zero waivers. The price is about 2× the area

And nobody drew the bit cell by hand: one Python function turns transistor sizes and design rules into rectangles.

📊 Where it stands (sign-off checks and SPICE on the final layout):
✅ 19,741 transistors in 225 × 156 µm
✅ 0 DRC violations in two independent checkers, Magic and KLayout
✅ LVS matches flat, transistor by transistor: 18,248 devices
✅ Post-layout SPICE passes at the slow, typical and fast corners; data is out 2.5 ns after the clock edge (typical), 5.0 ns (slow)
✅ Read noise margin ≥ 218 mV over all corners, 0 failures in 1,000 Monte Carlo cells per condition
⚠️ No silicon. Nothing here has been fabricated or measured: it is ready for a test chip, not proven
⚠️ The mismatch numbers are only as good as the PDK's Monte Carlo models

A question for the memory designers here: on a small macro, would you pay 2× cell area for zero rule waivers? 🤔

🎬 Two-minute tour in the video 👇
The full 9-minute walkthrough, the code, the layout and all reports: https://github.com/Melihakbulut221/sky130-sram-64x32

#ICDesign #SRAM #MemoryDesign #SKY130 #OpenSourceSilicon #VLSI #Python #EDA

---

Attach `sram_sky130_short.mp4` (2 min 19 s). Only the first three lines show before "see more", so the opening carries the post.

Alternative openings:

1. 💥 I threw away the sense amplifier and made the bit cell twice as big as the foundry's. On purpose.
2. 💥 19,741 transistors, zero DRC violations, and not one rectangle drawn by hand.
3. 💥 The clock-tree tool followed my clock into a memory cell and crashed. It was right to be confused.
