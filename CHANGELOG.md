# Changelog

## rev 1.2 - 2026-10-03

Designed by Kevin Le, Sammy DeGraaff and Mohammed-Mehdi Hamdaoui.

**Stabilisers (PCB-mount, screw-in)**
- Plate: the stabiliser openings are **7.0 mm wide** (were 6.75 mm), still 14 mm long. A 3D check
  against Joe Scotto's stabiliser model showed its housing is 6.8 mm wide where it passes through
  the plate, so the 6.75 mm opening would have rubbed it. The new opening leaves 0.1 mm a side
  even for that housing.
- PCB: the stabiliser holes are now **plated, with copper reinforcement rings** on both sides
  (4.6 mm rings on the 3.05 mm holes, 6.0 mm rings on the 3.99 mm screw holes, exposed and gold
  with ENIG). The plated barrels and rings stiffen the board where the screws and washers clamp it
  and where the housings sit. The finished hole sizes are unchanged. The bottom-layer keep-outs now
  extend 0.5 mm beyond each ring, and two column traces near LShift were re-routed around the rings.
- Plate foam: one window per stabilised key over both housings and the wire. Close to the PCB the
  housing base is longer than the plate opening, so the old foam cut-outs would have pressed on it.
- Two new interference checks: plate x stabilisers and plate foam x stabilisers (both 0 mm³).

**Top case**
- The opening now **follows the key clusters** instead of being one rectangle over the key field:
  the case covers every gap between clusters (Esc-F1, the band under the F-row, the gaps between the
  F-key groups, the area around Del and the nav column, around the arrows and under the bottom row),
  so the plate is no longer visible inside the keyboard. Each key keeps at least 0.7 mm of clearance
  around its keycap; the narrowest bridge between clusters is 4.3 mm wide and sits 1 mm above the
  plate, so the plate still floats on its gaskets. The gold name on the plate is now under the case.

**PCB**
- **Black solder mask**, white silkscreen, ENIG finish: set in the board stackup, so KiCad's 3D
  viewer, the renders and the fabrication notes all show the black board.
- The back silkscreen adds the designers: "DESIGNED BY Kevin Le · Sammy DeGraaff ·
  Mohammed-Mehdi Hamdaoui", under the space bar. The poem and the name on the front are unchanged.
- The title blocks name the team instead of countries.
- The board file had lost all of its footprint-to-schematic links during a KiCad editing session;
  the rebuild restored them (schematic parity is clean). The schematic labels that were tidied by
  hand in that session (power symbols near the RP2040, the crystal value) are kept.

**3D model and renders**
- Sculpted keycaps (Cherry-like row profile with a dished top) replace the flat CAD keycaps in the
  assembly and the renders.
- `Mechanical/Vamora75_assembly.step` now keeps KiCad's colours: black solder mask, white silkscreen,
  gold pads, and the real colours of every part, including Scotto's switches.
- New: **`Mechanical/Vamora75_PCB_plate.step`** and **`.glb`**, the PCB, plate and every component
  (switches, stabilisers, sockets, SMD parts) without the case. The .glb opens in Windows 3D Viewer
  or any web glTF viewer.
- New renders with studio lighting, physically based materials, ambient occlusion and soft
  shadows, plus a top view and a PCB + plate view. KiCad renders use the board's stackup colours.
- New colourway: graphite case, bone alphas, slate modifiers, brass Esc and Enter.

**Docs**
- README rewritten. References to countries and flags were removed from the files, the firmware
  headers and the colour palette (the archived revisions are unchanged).

The rev 1.1 outputs are kept in `Archive/rev1.1_outputs.zip`.

## rev 1.1 - 2026-10-02

**Layout**
- The arrow cluster moved **0.25u left and 0.25u down**. Up no longer touches End, and Right no
  longer sits in the Del/Home/PgUp/PgDn/End column; there is a 0.25u gap on both sides. The PCB,
  plate and case are 4.76 mm deeper (PCB 334.61 x 134.59 mm).

**Joe Scotto's ScottoKicad library**
- Switch footprints are now ScottoKicad `Hotswap_MX_*` (Kailh CPG151101S11 on B.Cu), and the
  stabilisers are separate ScottoKicad `Stabilizer_MX_2.00u/6.25u` footprints.
- The diode, HRO USB-C, 0402 R/C and SOT-23(-6) footprints also come from ScottoKicad. Their pads
  are identical to the KiCad-stock parts they replace, so the controller routing is unchanged.
- His 3D models are used: socket, MX switch, stabilisers, USB-C, diode, and the MX keycaps in the
  assembly STEP and renders. His MX switch model is shown on every switch footprint, so the
  KiCad 3D viewer and `Mechanical/Vamora75_PCBA.step` show the board with switches fitted.

**Branding**
- No logo. The PCB **front** carries one very large "Vamora75" (240 mm wide) across the middle,
  knocked out around every hole and exposed pad; Scotto's switch outlines run through the letters.
  The case bottom is engraved "Vamora75" (180 mm), and the plate carries "Vamora75" in gold.
- The PCB **back** keeps *Nam Quốc Sơn Hà*, now centred under the F-row and larger than in rev 1.0
  (2.4 mm letters, title over the two couplets), next to the BOOT/RESET labels and "rev 1.1".
- Removed from the PCB: the badge, tagline, credits and per-key legends.

**Board**
- Re-routed: row lines jog to the lowered arrows, column 15 and the ROW5 feed were re-planned, and a
  router clean-up step removes vias left connected on one layer only.
- ERC, DRC, unconnected items and schematic parity are all clean again.
- CPL: the sockets are reported as bottom-side parts (the ScottoKicad switch footprints sit on the
  top layer).

**Everything else** (plate, case, foams, firmware layout data, renders, Gerbers, BOM/CPL) was
regenerated for the new outline. The rev 1.0 outputs are kept in `Archive/rev1.0_outputs.zip`.

## rev 1.0 - 2026-10-02

The whole design was rebuilt from the same layout. See [DESIGN_REVIEW.md](DESIGN_REVIEW.md) for the reasons.

**Electronics**
- The RP2040-Zero module is replaced by an RP2040 on the board, using the Pico core circuit:
  W25Q16JV flash, 12 MHz ABM8-272-T3 crystal, XC6206 3.3 V LDO, USBLC6-2SC6 ESD protection, 0.5 A
  PTC fuse, HRO TYPE-C-31-M-12 at the rear edge, BOOT and RESET buttons, and 4 test pads.
- Matrix changed from 7 x 12 to 6 x 16 COL2ROW, with a crossing-free GPIO map and GP9-15/GP25 left free.
- New footprints for the Kailh CPG151101S11 sockets (1u-6.25u, PCB-mount stabiliser holes), with
  3D models of the socket, the MX switch, the USB-C receptacle and the tact switch.
- Re-routed from scratch on 2 layers with a GND pour on both. All parts are on the bottom side.
  ERC, DRC, unconnected items and schematic parity are all clean in KiCad 10.0.6.
- JLCPCB BOM (LCSC numbers) and CPL, Gerbers/drill, schematic PDF and bottom assembly drawing.

**Plate**
- MX openings with 0.5 mm router corners and ai03 "MX simple" stabiliser openings. All stabilisers
  are in the standard orientation (the spacebar was reversed in rev 0.1).
- 8 gasket tabs (rev 0.1 had 6), an optional flex-cut variant, and a gold ENIG emblem and wordmark in
  the visible gaps. Ordered as a KiCad board.

**Case**
- 6° wedge (rev 0.1 was flat), 21.0 mm at the front and 37.1 mm at the rear.
- Tab-gasket sandwich kept: 16 gaskets with pockets sized for 20 % compression.
- M3 x 8 screws into heat-set inserts (rev 0.1 tapped printed pilots and cut screws to length).
- 4-piece print split for 250 x 210 mm beds, with dowels.
- USB tunnel sized for the largest USB-IF overmould, BOOT pin-hole, bumper recesses, and the badge
  engraved on the bottom.
- 12 automated interference checks: case, PCBA, plate, gaskets, switches, keycaps pressed down,
  and the USB plug.

**Firmware**
- QMK data-driven `keyboard.json` + default and VIA keymaps, VIA definition, CircuitPython for the
  Pico UF2, and KLE layout. 30 automated checks, including netlist vs. firmware pins.

**Brand**
- A badge logo (keycap emblem and wordmark) on the PCB silkscreen, the plate and the case engraving,
  with SVG/PNG/DXF files (replaced by the plain name in rev 1.1). *Nam Quốc Sơn Hà* stays on the PCB.

**Project**
- Everything is generated by `Source/build_all.py` and validated in `validation/STATUS.md`.
- The superseded rev 0.1 files are kept unchanged in `Archive/rev0.1/`.

## rev 0.1 - 2026-10-01

The first coordinated design: RP2040-Zero module under the PCB, Kailh hot-swap, FR4 plate, flat
printed tab-gasket case and CircuitPython firmware. See `Archive/rev0.1/README.md`.
