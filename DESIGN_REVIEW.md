# Vamora75 - design review of rev 0.1 and what changed in rev 1.0 / 1.1

> **rev 1.1 update:** the arrow cluster sits 0.25u left and 0.25u down so it no longer crowds the
> Del/Home/PgUp/PgDn/End column. Switch, stabiliser, diode, USB-C and passive footprints and their 3D
> models now come from Joe Scotto's ScottoKicad library, and his MX switch model is shown on the board.
> The PCB front carries a very large "Vamora75" (no logo), the back keeps *Nam Quốc Sơn Hà*, and the
> case and plate show only the name. See `CHANGELOG.md`.

## Is it gasket mount?

**Yes. Rev 0.1 was already a tab-gasket ("sandwich") mount, and rev 1.0 keeps that mount style
and refines it.**

The evidence in the rev 0.1 sources (`Archive/rev0.1/Source/build_mechanical.py`):

* The FR4 plate had six tabs (24 x 6 mm), three on the front edge and three on the rear edge.
* Twelve foam strips (24 x 5.5 x 2 mm) sat in pockets: one under and one over each tab. The
  pockets were cut into the bottom case (Z 18.5-21) and the top case (Z 19.9-23.2).
* The case split at Z 20.0, inside the plate's thickness (plate Z 20.1-21.6). So the only path
  from the plate to the case went through the gaskets.
* The PCB hung from the switches. Nothing screwed the PCB or the plate to the case, and the
  build guide said not to add standoffs.

In rev 1.0 the plate has **8 tabs** (3 front, 3 rear, 1 left, 1 right) and **16 gaskets**
(20 x 4.5 x 2.0 mm). The pockets set each gasket to exactly 1.6 mm, which is 20 % compression.
An optional flex-cut plate adds relief slots behind every tab. The PCB and plate still float as
one unit: the 8 case screws only join the two case halves.

## Review findings and fixes

| Area | Rev 0.1 finding | Consequence | Rev 1.0 |
|---|---|---|---|
| Controller | Waveshare RP2040-Zero module soldered upside-down under the PCB on headers, 3.5 mm gap set with a home-made spacer jig | Tall stack (module board plus its parts under the main PCB), so the case was 28 mm with no typing angle. The module had to be hand-soldered at an exact height. BOOT/RESET could only be reached through an open hole in the case floor. The tunnel had to be 20 x 8.5 mm. | RP2040 on the PCB, using the Raspberry Pi Pico core circuit (W25Q16JV, 12 MHz ABM8 crystal, 1 kΩ XOUT resistor, 15 pF). Added USBLC6-2SC6 ESD protection, a 0.5 A PTC fuse, 5.1 kΩ CC resistors, an XC6206 LDO, BOOT/RESET buttons and test pads, all machine-placed. USB-C sits at the PCB rear edge behind a 14 x 8 mm tunnel; BOOT is reachable through a 2.2 mm pin-hole. |
| Matrix | 7 x 12 (84 slots) for 6 physical rows; GP7-15 + GP26-28 columns | Rows did not match the physical rows, and the matrix could not be fanned out cleanly from a bare MCU | 6 x 16 COL2ROW. Each row is one physical row. GPIOs were chosen so the QFN fans out with no crossings. GP9-15 and GP25 are left free. |
| PCB | Inherited routing, cleaned from 5,820 to 1,686 segments; COL9 kept its original routing after a failed shortcut | Hard to maintain or modify | Re-routed from scratch by a deterministic generator: rows on B.Cu at y+3 mm, columns on F.Cu, a column bus in the 0.5u gap, and the controller fan-out by a grid A* router. GND pour on both layers. Zero DRC violations under JLCPCB-legal rules (0.15 mm only inside three named fan-out areas). |
| Hot-swap footprint | Keyboard75 MX hot-swap footprints | No accurate 3D model or bottom-side courtyard data for assembly | ScottoKicad `Hotswap_MX_*` footprints (Kailh CPG151101S11 on B.Cu) and `Stabilizer_MX_*` footprints with keep-outs, with Scotto's socket, switch and stabiliser models (rev 1.1; rev 1.0 used generated equivalents). LCSC part C5156480. All SMT parts are on the bottom side, so JLCPCB can assemble the board in one pass. |
| Plate openings | Sharp 14 mm squares; stabiliser openings were plain 8 x 18.4 mm boxes | FR4 is routed with cutters of 1 mm or more, so true sharp corners are impossible. The stabiliser openings did not follow any stabiliser specification. | 14.0 mm openings with 0.5 mm corners (router-native; MX housings have chamfered corners). Stabiliser openings use ai03's "MX simple" profile (6.75 x 14 mm, +6/-8 mm). The minimum FR4 web is 1.56 mm. |
| Stabilisers | Spacebar stabiliser drilled reversed relative to the 2u keys | Needs reversed wires or a different stabiliser part | All four stabilisers (Backspace, Enter, LShift, Space) use the standard Cherry orientation. |
| Mount | 6 tabs, long edges only | Plate support was uneven along the short edges | 8 tabs, pockets sized for 20 % gasket compression, optional flex cuts |
| Case | Flat (0 deg), 28 mm tall, needed a 359 mm print bed; M3 screws tapped into 2.5 mm printed pilots and cut to 24 mm | Uncomfortable typing angle, threads that wear out, and few printers could print it | 6 deg wedge (21.0 mm at the front, 37.1 mm at the rear). M3x8 screws into heat-set inserts. A 4-piece split with staggered seams and dowels fits 250 x 210 mm beds. Added bumper recesses, a BOOT pin-hole and a USB tunnel sized for the largest overmould the USB spec allows. |
| Manufacturing | BOM without assembly data | Needed manual sourcing and hand assembly | JLCPCB BOM with LCSC numbers, a CPL with socket centroid correction, Gerbers/drill, schematic PDF and bottom assembly drawing. The plate is ordered as a PCB with a gold ENIG logo. |
| Branding | Generic "V / mountain / river" mark | Did not reflect the team | Rev 1.0 had a keycap-and-star badge (archived). Rev 1.1 uses the name only: a very large "Vamora75" across the PCB front, engraved on the case and in gold on the plate (see `Artwork/NAME.md`). The PCB back keeps *Nam Quốc Sơn Hà*. |
| Firmware | QMK for the module pin-out; CircuitPython UF2 for the RP2040-Zero | That UF2 drives GP16 as a NeoPixel, which is now a matrix column | QMK (data-driven) + VIA keymap and definition; CircuitPython for the Raspberry Pi Pico build. 30 automated checks, including netlist vs. firmware pins. |

## Kept from rev 0.1

* Layout: 82-key exploded 75 % Windows ANSI with the same key positions, except the arrow
  cluster, which rev 1.1 moved 0.25u left and down (the PCB grew to 334.6125 x 134.5875 mm).
* Kailh CPG151101S11 sockets, 1N4148W SOD-123 diodes, COL2ROW.
* FR4 plate, tab-gasket mount, two-piece case.
* *Nam Quốc Sơn Hà* on the PCB bottom silkscreen, centred under the F-row in rev 1.1.

## Open items - verify on the first prototype

1. **QMK compile** (`qmk compile -kb vamora75 -km via`). The sources are statically checked but have
   not been compiled here.
2. **JLCPCB stock and rotations**: check the stock of C5156480 (Kailh socket), C2040 (RP2040),
   C2843335 (flash), C20625731 (crystal) and C165948 (USB-C). In the placement preview, check every
   bottom-side part, in particular the socket orientation, U1 pin 1 and the diode cathode (pad 1 = ROW).
3. **USB-C on the bottom side**: the plug enters below the PCB through the rear tunnel. Use a cable
   whose overmould is 12.35 x 6.5 mm or smaller (most are).
4. **Printed tolerances**: tab pockets have 0.5 mm clearance and insert holes are 4.0 mm. Print one
   corner first.
5. **Plate thickness**: designed for 1.5 mm. 1.6 mm also fits, with about 0.05 mm more compression per gasket.
6. **Electrical bring-up**: before plugging in, check the test pads TP1-TP4 for shorts. The board must
   show up as `RPI-RP2` with blank flash (see `BUILD_GUIDE.md`).
