# Vamora75

![Vamora75](Previews/assembled.png)

**An 82-key 75 % mechanical keyboard with a 6° typing angle, a tab-gasket mount, hot-swap sockets
and an on-board RP2040.** Designed by **Kevin Le, Sammy DeGraaff and Mohammed-Mehdi Hamdaoui**.

> **Status: revision 1.2, complete and checked in software, not built yet.** ERC, DRC, schematic
> parity, plate DRC, 14 CAD interference checks and 30 firmware tests all pass
> ([validation/STATUS.md](validation/STATUS.md)). Build one prototype before a group order and work
> through the open items in [DESIGN_REVIEW.md](DESIGN_REVIEW.md).

## Features

- Exploded 75 % Windows ANSI layout, 82 keys, with a separated arrow cluster
- Hot-swap Kailh sockets for any 3- or 5-pin MX-compatible switch
- PCB-mount screw-in stabilisers on plated, copper-reinforced holes; the plate openings let the
  stabiliser housings pass through
- Tab-gasket sandwich mount: 8 plate tabs, 16 gaskets at 20 % compression, optional flex-cut plate
- 6° typing angle; two-piece case whose top follows the key clusters, so no plate shows between
  them; printed in one piece, in 4 pieces for 250 x 210 mm beds, or CNC
- RP2040 on the board (the Raspberry Pi Pico core circuit), USB-C, ESD protection, fuse, BOOT and
  RESET buttons
- QMK + VIA, or CircuitPython with no compiler
- Black PCB with ENIG gold; "Vamora75" across the PCB front, engraved under the case and in gold on
  the plate (under the top case); *Nam Quốc Sơn Hà* and the designers' names on the PCB back
- Generated from source: one command rebuilds the PCB, plate, case, firmware, manufacturing files,
  3D models and renders, then re-runs every check

## Gallery

| Exploded | Top |
|---|---|
| ![Exploded](Previews/exploded.png) | ![Top](Previews/top.png) |
| **Profile** | **Underside** |
| ![Side](Previews/side.png) | ![Bottom](Previews/bottom.png) |

**PCB + plate + components** (no case): Joe Scotto's MX switches, the PCB-mount stabilisers, Kailh
sockets and every SMD part ([3D file](Mechanical/Vamora75_PCB_plate.step),
[quick-look .glb](Mechanical/Vamora75_PCB_plate.glb)):

![PCB and plate](Previews/pcb_plate.png)

### PCB

| Front ("Vamora75" silkscreen) | Back (*Nam Quốc Sơn Hà*, designers, gold stabiliser rings) |
|---|---|
| ![PCB front](Previews/pcb_top.png) | ![PCB back](Previews/pcb_bottom.png) |
| **With Joe Scotto's switch models** | **FR4 plate (name in gold ENIG, under the top case)** |
| ![PCB with switches](Previews/pcb_top_switches.png) | ![Plate](Previews/plate_top.png) |

## 3D files

| File | Shows | Open with |
|---|---|---|
| [Mechanical/Vamora75_assembly.step](Mechanical/Vamora75_assembly.step) | The whole keyboard: case, gaskets, foams, plate, PCBA, switches, stabilisers, keycaps | FreeCAD, Fusion 360, Onshape, SolidWorks |
| [Mechanical/Vamora75_PCB_plate.step](Mechanical/Vamora75_PCB_plate.step) | PCB + plate + every component, without the case | any STEP viewer |
| [Mechanical/Vamora75_PCB_plate.glb](Mechanical/Vamora75_PCB_plate.glb) | The same, as a light coloured model | Windows 3D Viewer, Blender, any web glTF viewer |
| [Mechanical/Vamora75_PCBA.step](Mechanical/Vamora75_PCBA.step) | The PCBA only (KiCad export) | any STEP viewer |
| [PCB/Vamora75.kicad_pro](PCB/Vamora75.kicad_pro) | Schematic and board; press Alt+3 for the 3D view | KiCad 10 |

Case parts, the plate and the soft parts are in [Mechanical/](Mechanical) as STEP/STL/DXF.

## Specifications

| | |
|---|---|
| Layout | 82 keys: exploded 75 % Windows ANSI with an F-row in clusters, a Del/Home/PgUp/PgDn/End column, a separated arrow cluster (0.25u gap), 1.75u RShift and 6.25u space ([layout](Previews/layout.png)) |
| Switches | Any MX-compatible switch, 3- or 5-pin, in Kailh CPG151101S11 hot-swap sockets (ScottoKicad `Hotswap_MX` footprints) |
| Stabilisers | PCB-mount screw-in: Backspace (2u), Enter and LShift (2.25u), Space (6.25u), standard orientation. Plated holes with 4.6 / 6.0 mm copper reinforcement rings; plate openings 7.0 x 14 mm |
| Controller | RP2040, W25Q16JV 2 MB flash, 12 MHz crystal (the Raspberry Pi Pico core circuit), BOOT and RESET buttons |
| USB | USB-C (HRO TYPE-C-31-M-12), USB 2.0 full speed, 5.1 kΩ CC resistors (C-C and A-C cables), USBLC6-2SC6 ESD protection, 0.5 A PTC fuse, XC6206 3.3 V LDO |
| Matrix | 6 x 16, COL2ROW, one 1N4148W per key |
| PCB | 334.61 x 134.59 mm, 2 layers, 1.6 mm, black solder mask, white silkscreen, ENIG. All SMT parts on the bottom (one-sided assembly), GND pour on both layers |
| Plate | FR4, 1.5 mm (1.6 mm also fits), black, 8 gasket tabs, optional flex cuts, "Vamora75" in gold ENIG |
| Mount | Tab-gasket sandwich: 16 gaskets of 20 x 4.5 x 2 mm at 20 % compression. PCB and plate float as one unit |
| Case | Two pieces, 6° typing angle, 21.0 mm high at the front and 37.6 mm at the rear, 358.6 x 161.5 mm. The top-case opening follows the key clusters (the case covers every gap between them). 8 M3 screws into heat-set inserts, "Vamora75" engraved underneath |
| Firmware | QMK + VIA, or CircuitPython |

## Bill of materials

<!-- BOM:start (generated by Source/export_manufacturing.py) -->
Full list: [BOM.csv](BOM.csv). The PCBA parts are placed by JLCPCB from
[Vamora75_BOM_JLCPCB.csv](Manufacturing/PCB/Vamora75_BOM_JLCPCB.csv) and
[Vamora75_CPL_JLCPCB.csv](Manufacturing/PCB/Vamora75_CPL_JLCPCB.csv); you only buy the kit items.

**Kit: what to buy or make**

| Item | Qty | Specification | Source / file |
|---|---|---|---|
| PCBA (this design) | 1 | 2-layer FR4 1.6 mm, black mask, ENIG, bottom-side SMT assembled | Manufacturing/PCB - JLCPCB/PCBWay |
| FR4 plate | 1 | 1.5 mm (1.6 mm fits), black mask, ENIG for the gold name | Manufacturing/Plate - any PCB fab |
| Case top | 1 | PETG/ASA print or CNC 6061 | Mechanical/Case |
| Case bottom | 1 | PETG/ASA print or CNC 6061 (solid wedge, 6 deg) | Mechanical/Case |
| MX-compatible switches | 82 | 3-pin or 5-pin | user choice |
| Keycaps | 82 | 1u x 71, 1.25u x 3, 1.5u x 2, 1.75u x 2, 2u x 1, 2.25u x 2, 6.25u x 1 | any MX set with a 75 % kit (1.75u RShift, 6.25u space) |
| PCB-mount screw-in stabilisers | 4 | 3 x 2u (Backspace, Enter, LShift) + 1 x 6.25u (Space) | Durock/Cherry/TX |
| Gaskets | 16 | 20 x 4.5 x 2 mm Poron 4701-50 or 40A silicone | Mechanical/Soft DXF |
| Case foam | 1 | 3 mm PE / Poron | Mechanical/Soft DXF |
| Plate foam (optional) | 1 | 3.5 mm Poron / PE, with stabiliser/wire windows | Mechanical/Soft DXF |
| Screws | 8 | M3 x 8 ISO 4762 socket head |  |
| Heat-set inserts | 8 | M3 x 4 x 4.0 mm heat-set insert (printed top case; tap M3 if CNC) |  |
| Dowel pins (split print only) | 5 | 3 x 12 mm steel dowel (or printed pin) | only for the 4-piece printed case |
| Bumpers | 4 | 10 x 3 mm silicone bumper |  |
| USB-C cable | 1 | overmould <= 12.3 x 6.5 mm |  |

**PCBA: parts on the board** (197 placements, all on the bottom side)

| Part | Qty | Designators | Footprint | LCSC |
|---|---|---|---|---|
| 10uF CL10A106KP8NNNC | 2 | C1-C2 | C_0603_1608Metric | [C19702](https://www.lcsc.com/product-detail/C19702.html) |
| 100nF CL05B104KO5NNNC | 10 | C3-C7, C9-C12, C15 | Capacitor_0402 | [C1525](https://www.lcsc.com/product-detail/C1525.html) |
| 1uF CL05A105KA5NQNC | 2 | C13-C14 | Capacitor_0402 | [C52923](https://www.lcsc.com/product-detail/C52923.html) |
| 15pF 0402CG150J500NT | 2 | C16-C17 | Capacitor_0402 | [C1548](https://www.lcsc.com/product-detail/C1548.html) |
| 1N4148W | 82 | D1-D82 | Diode_SOD-123 | [C81598](https://www.lcsc.com/product-detail/C81598.html) |
| 500mA SMD0805-050 | 1 | F1 | Fuse_0805_2012Metric | [C66452](https://www.lcsc.com/product-detail/C66452.html) |
| HRO TYPE-C-31-M-12 | 1 | J1 | USB_C_HRO_TYPE-C-31-M-12 | [C165948](https://www.lcsc.com/product-detail/C165948.html) |
| 5.1k 0402WGF5101TCE | 2 | R1-R2 | Resistor_0402 | [C25905](https://www.lcsc.com/product-detail/C25905.html) |
| 27R 0402WGF270JTCE | 2 | R3-R4 | Resistor_0402 | [C25100](https://www.lcsc.com/product-detail/C25100.html) |
| 10k 0402WGF1002TCE | 2 | R5, R7 | Resistor_0402 | [C25744](https://www.lcsc.com/product-detail/C25744.html) |
| 1k 0402WGF1001TCE | 2 | R6, R8 | Resistor_0402 | [C11702](https://www.lcsc.com/product-detail/C11702.html) |
| Kailh CPG151101S11 MX hot-swap socket | 82 | SW1-SW82 | Kailh_CPG151101S11 | [C5156480](https://www.lcsc.com/product-detail/C5156480.html) |
| BOOT TS-1187A-B-A-B | 1 | SW90 | SW_Push_1P1T_XKB_TS-1187A | [C318884](https://www.lcsc.com/product-detail/C318884.html) |
| RESET TS-1187A-B-A-B | 1 | SW91 | SW_Push_1P1T_XKB_TS-1187A | [C318884](https://www.lcsc.com/product-detail/C318884.html) |
| RP2040 | 1 | U1 | QFN-56-1EP_7x7mm_P0.4mm_EP3.2x3.2mm_ThermalVias | [C2040](https://www.lcsc.com/product-detail/C2040.html) |
| USBLC6-2SC6 | 1 | U2 | ESD_SOT-23-6 | [C7519](https://www.lcsc.com/product-detail/C7519.html) |
| XC6206P332MR | 1 | U3 | Voltage_SOT-23 | [C5446](https://www.lcsc.com/product-detail/C5446.html) |
| W25Q16JVUXIQ | 1 | U4 | Winbond_USON-8-1EP_3x2mm_P0.5mm_EP0.2x1.6mm | [C2843335](https://www.lcsc.com/product-detail/C2843335.html) |
| 12MHz ABM8-272-T3 | 1 | Y1 | Crystal_SMD_3225-4Pin_3.2x2.5mm | [C20625731](https://www.lcsc.com/product-detail/C20625731.html) |
<!-- BOM:end -->

## Getting started

1. Read [DESIGN_REVIEW.md](DESIGN_REVIEW.md): the mount, the stabilisers, what changed, and what to
   check on the first prototype.
2. Order the PCBA, the plate, the case and the soft parts:
   [Manufacturing/FABRICATION.md](Manufacturing/FABRICATION.md).
3. Assemble it: [BUILD_GUIDE.md](BUILD_GUIDE.md).
4. Flash the firmware: [Firmware/README.md](Firmware/README.md).
5. To change the design, edit the parameter files and rebuild: [Source/README.md](Source/README.md).

## Repository

| Folder | Contents |
|---|---|
| [PCB/](PCB) | KiCad 10 project: schematic, 2-layer board, project footprint library (ScottoKicad + KiCad stock) with 3D models, custom DRC rules |
| [Plate/](Plate) | KiCad boards for ordering the FR4 plate as a PCB (standard and flex-cut) |
| [Mechanical/](Mechanical) | Case (one-piece and 4-piece print split), plate DXF/STEP/STL, gasket and foam DXFs, assembly STEP, PCB + plate STEP/GLB, PCBA STEP, key positions |
| [Manufacturing/](Manufacturing) | JLCPCB-ready Gerbers/drill, BOM + CPL, schematic PDF, assembly drawing, plate Gerbers, kit BOM |
| [Firmware/](Firmware) | QMK + VIA source, VIA definition, CircuitPython, KLE layout |
| [Artwork/](Artwork) | The "Vamora75" name in SVG/PNG/DXF ([NAME.md](Artwork/NAME.md)) |
| [Previews/](Previews) | Renders |
| [Source/](Source) | Python generators for everything (`build_all.py`) |
| [validation/](validation) | ERC/DRC, mechanical, plate and firmware reports |
| [Archive/](Archive) | Earlier revisions: `rev0.1/`, `rev1.0_outputs.zip`, `rev1.1_outputs.zip` |
| [Reference/](Reference) | Input snapshots (Keyboard75, Aster75) |

## Revisions

- **1.2** (2026-10-03): top case covers the gaps between key clusters, plate openings and foam
  windows for PCB-mount stabilisers, plated and reinforced stabiliser holes, black PCB, designers'
  names on the PCB back, sculpted keycaps, new 3D files and renders.
- **1.1**: arrow cluster moved away from the nav column, Joe Scotto's ScottoKicad footprints and
  models, name-only branding.
- **1.0**: on-board RP2040, new matrix and routing, 6° gasket-mount case.

Details: [CHANGELOG.md](CHANGELOG.md).

## Credits

Designed by **Kevin Le, Sammy DeGraaff and Mohammed-Mehdi Hamdaoui** (team Vamora).

Footprints and 3D models for the switches, sockets, stabilisers and several components are from
Joe Scotto's [ScottoKicad](https://github.com/joe-scotto/scottokeebs). Third-party data and licences:
[ATTRIBUTION.md](ATTRIBUTION.md) and [Licenses/](Licenses).
