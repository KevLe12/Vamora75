# Keyboard75 — exploded ANSI, Rev A

82-key, two-layer, full-height MX hot-swap keyboard with a Windows key, standard US ANSI legends, and a USB-C Waveshare RP2040-Zero module. This is a custom PCB, not a drop-in replacement for a commercial 75% case.

## Open the project

Open `Keyboard75_Exploded_ANSI.kicad_pro` in KiCad 7 or newer. The schematic, routed PCB, symbols and footprints are included; no third-party library installation is needed. The controller is an off-the-shelf **original Waveshare RP2040-Zero module**, not a bare RP2040 chip. USB-C, power regulation, flash and decoupling are already on that module.

## Mechanical specification

- PCB: 334.6125 × 129.825 × 1.6 mm FR4, 2 copper layers.
- Switch pitch: 19.05 mm. 82 Kailh CPG151101S11 sockets on the **bottom**. Supports full-height 3-pin and 5-pin MX compatible switches.
- Keycaps: 6.25u spacebar, 1.75u right Shift, 1.25u left modifiers, 1u right Alt/Fn/Ctrl.
- Four stabilized keys: Backspace, Enter, left Shift and Space. Use three 2u Cherry compatible PCB stabilizers and one 6.25u / 100 mm stabilizer pair. Spacebar stabilizers are reversed relative to the other stabilized keys.
- Six 2.2 mm M2 mounting holes. Keep screw head diameter at or below 4.4 mm. Coordinates are in `docs/mounting_holes.csv`.
- Module: 18 × 23.5 mm body mounted underneath, components toward the case bottom. USB-C faces the rear in the Esc/F1 gap, 31.575 mm from the PCB left edge. Module bottom header row is 0.21 mm below the bottom side-row pins; the footprint reflects this.
- The module, pins and sockets require bottom clearance. Design the case using their actual assembled heights. Leave access to module BOOT and RESET buttons.
- Plate DXF uses millimetres: 14 mm switch openings, 8 × 18.4 mm stabilizer clearance openings, M2 holes and PCB outline. Use a nominal 1.5 mm plate and check clip/kerf tolerances against the chosen switches and stabilizers. The plate is a starting mechanical drawing, not a certified fit.

## Circuit and firmware

7 × 12 matrix, one 1N4148W SOD-123 diode per key. Switch pad 1 goes to COL; switch pad 2 goes to diode anode; diode cathode **pad 1** goes to ROW. Use QMK `COL2ROW`. Diode cathode stripe must face the cathode pad marked by the diode footprint.

ROW0–ROW6: GP0–GP6. COL0–COL8: GP7–GP15. COL9–COL11: GP26, GP27, GP28. Module pin 20 / GP29 is unused. There are two spare matrix positions. Module 5V, 3V3 and GND are exposed at three measurement pads; do not connect external power while using USB.

Copy `firmware/qmk/keyboards/custom/kb75_ansi` into a current QMK checkout and run `qmk compile -kb custom/kb75_ansi -km default`. The base layer includes left Windows (GUI) and an Fn key. Fn+Esc enters the bootloader; Fn+F1–F6 controls media, Fn+F12 is Print Screen and Fn+Home is Insert. For initial flashing hold the module BOOT button while connecting USB, then copy the built UF2 to the bootloader drive. Firmware is provided as source and **has not been compiled or tested on hardware**.

## Fabrication and assembly

Use `fabrication/` Gerbers and both PTH and NPTH Excellon drill files. Board defaults: 2 layers, FR4 1.6 mm, 1 oz copper, no impedance control, 0.25 mm traces, 0.20 mm clearance, 0.60/0.30 mm vias. Inspect the boardhouse preview before ordering. Front paste may be empty because sockets and diodes are on the bottom and the measurement pads require no paste.

1. Confirm keycap, plate, stabilizer and case fit using the provided position drawings.
2. Solder the 82 bottom diodes, aligning cathode stripes to pad 1.
3. Solder the 82 bottom hot-swap sockets. Support each socket when inserting a switch.
4. Attach the RP2040-Zero underneath through its 23 header connections. Pin 1 is GP0; pin 23 is 5V. Verify orientation against the schematic and footprint before soldering.
5. Inspect for solder bridges, check resistance between 5V and GND, flash firmware and test every key before completing the case.

## Validation and status

The native KiCad DRC report and independent net/matrix checks are in `checks/`. These checks cover the manufactured PCB connections and geometry, not physical production. **Rev A is an unbuilt prototype**: no hardware, USB enumeration, stabilizer/plate/case fit or firmware build has been tested. Standalone schematic ERC was not run; schematic-to-PCB net agreement is checked separately. Review the mechanical design with the actual parts before ordering a batch.

## Files

Native KiCad project, schematic and routed PCB; self-contained libraries; Gerbers and drill files; plate DXF; layout and PCB SVGs; BOM and coordinate CSVs; matching QMK source; generation/routing scripts and validation reports.

## Sources

- Kailh socket drawing: https://www.kailhswitch.com/uploads/15927/files/CPG151101S11.pdf
- MX socket geometry reference: https://github.com/ai03-2725/MX_V2
- Original module: https://www.waveshare.com/wiki/RP2040-Zero
- Module schematic: https://files.waveshare.com/upload/4/4c/RP2040_Zero.pdf
- QMK RP2040 documentation: https://docs.qmk.fm/platformdev_rp2040

SOD-123 and test point footprints originate from KiCad's standard footprint library. Keyboard/module footprints and project files are included locally. See `sources/KiCad_footprints_copyright.txt` for distribution terms.
