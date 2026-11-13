# Rev 1.7 release audit — 2026-11-12

**Digital design review complete; prototype verification remains required.**
This is not a certification that fabricated boards or printed cases will be flawless.
The rebuilt outputs and raw reports accompany this revision.

## Changes from Rev 1.6

- Centred the remaining trace-to-via joins, retaining short approach bends where needed to preserve copper clearance. Enabled `track_not_centered_on_via` as a DRC error.
- Removed the empty optional QMK URL, which conflicts with QMK's keyboard schema.
- Allowed CircuitPython Fn+Esc recovery to proceed if sending the final USB reports raises `OSError`. Three regression cases exercise the generated recovery block.
- Added component-to-component CAD interference checks and checks of the exported print-case screw, driver and insert paths.
- Changed the insert coupon to 5 mm-deep bores, matching the case. The assumed insert remains M3 x 4 mm, nominal 4 mm OD; validate the purchased insert's specified bore.
- Replaced metal-paperclip BOOT instructions with a blunt 1 mm nonconductive probe and clarified which firmware and mechanical claims require hardware testing.

## Evidence and scope

| Area | Check |
|---|---|
| PCB | Refilled-zone DRC, zero disconnected items, schematic parity and ERC; see `drc.json` and `erc.json` |
| USB | ESD input/output flow-through, C8 purchasing fields, complete track joins, via drill clearance and filled In2 ground under the main pair; `usb_layout.json`, `usb_reference.json` |
| Layout | All 82 key positions/widths match the saved Custom reference; `revision_geometry.json` |
| Components | 202 component assemblies, 31 bounding-box candidate pairs, no modeled overlap; `component_interference.json` |
| Case | PCB, plate, stabilisers, keycaps, gasket, foam, USB plug and BOOT approach checks; `mechanical.json` |
| Fasteners | CNC D5 M3 x 8 nominal insertion 4.5 mm; print version 3 mm into a 4 mm-long insert, 5 mm bore depth. Nominal paths checked; `print_fasteners.json` |
| Firmware | 34 static/host checks, including netlist-to-pin consistency, HID mappings and boot recovery; `firmware.json` |
| Manufacturing | Four copper Gerber layers, 198 bottom-side placements, ZIP integrity and matching packaged STEP files checked |

The separate strict DRC run enables categories normally suppressed by this project.
It reports 134 silkscreen overlaps, four missing stabiliser courtyards, one USB shield
PTH inside the opposing switch courtyard and one mixed SMT/PTH connector type warning.
These are retained as reviewed exceptions, not concealed as a globally warning-free
board. The overlap warnings involve silk graphics/footprint silk, not electrical copper.
The independent component-solid check includes J1 against SW2. See `strict_drc.json`.

The PCB is specified as **four layers, 1.6 mm, black solder mask, white silkscreen,
ENIG**, with JLC04161H-7628 and a 90 ohm differential target. In KiCad's 3D Viewer,
enable **Appearance → Use board stackup colors** and refresh. The viewer's default
green theme does not change the manufacturing order; select black on the order form.

## Required before a three-keyboard production order

1. Compile the QMK/VIA build with the intended QMK revision, or load the documented CircuitPython build. Neither target has been run on this hardware. Test all keys, modifiers, layers, BOOT/reset and repeated USB unplug/replug, suspend/resume and both cable orientations. BOOT is for firmware loading/recovery, not each normal connection.
2. Obtain JLCPCB's stackup/impedance acceptance and coupon report. Review BOM availability and every placement rotation in the manufacturer's preview. DRC and the local ground check do not measure impedance, ESD robustness or USB signal integrity.
3. Print/slice and assemble one case. Verify actual insert fit/retention, screw length and thread engagement, seam bonding, flatness, gasket compression, key travel, USB cable seating and BOOT travel. The modeled USB overmould is 12.35 x 6.5 mm; other cables need checking.
4. Keep conductive PC-CF away from exposed copper/solder. The specified component clearances and foam cut-outs must be preserved. Inspect the actual assembly and add suitable insulating film where required.
5. Slice with the actual printer/material settings and recalculate filament. Three 800 g spools is a geometric budget for three cases, not a measured slicer total.

CNC STEP files contain pilot bores, not modeled helical threads. Supply the D5 PDF/DXF
and requirements together with the STEP files. Use the separate insert-bore variants
for printing. Case geometry remains D5; Rev 1.7 identifies the PCB/release revision.

References: [QMK keyboard schema](https://github.com/qmk/qmk_firmware/blob/master/data/schemas/keyboard.jsonschema),
[QMK RP2040 documentation](https://docs.qmk.fm/platformdev_rp2040),
[CircuitPython microcontroller API](https://docs.circuitpython.org/en/stable/shared-bindings/microcontroller/index.html).
