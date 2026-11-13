# Vamora75 rev 1.7 - validation status

Generated 2026-11-12 by `Source/build_all.py`. These are digital checks of the
design files; no board has been built or tested yet (see BUILD_GUIDE.md, bring-up).
Normal DRC uses reviewed project exclusions; see RELEASE_AUDIT.md and strict_drc.json for the separate audit.

| Check | Result |
|---|---|
| Schematic ERC (KiCad 10, all severities) | clean |
| PCB DRC violations (all severities, zones refilled) | clean |
| PCB unconnected items | clean |
| Schematic <-> PCB parity | clean |
| Print screw and insert paths | PASS (print_fasteners.json) |
| Component-to-component CAD interference | PASS (component_interference.json) |
| Custom key positions and widths | 82/82 match |
| ESD flow-through, C8 BOM and full USB junctions | PASS (usb_layout.json) |
| Four-layer USB filled-ground reference | PASS (validation/usb_reference.json) |
| PC-CF split prints | Four watertight parts fit CORE One L; see pccf_print.json |
| Vamora75_Plate DRC / unconnected | clean / clean |
| Vamora75_Plate_flexcut DRC / unconnected | clean / clean |
| Plate min. FR4 web (switch-stab) | 1.438 mm |
| Mechanical interference (21 pairs, incl. stabilisers through plate and foam, keycaps bottomed out, USB-C plug) | PASS |
| CNC case D5 screw heads, shafts, driver paths, BOOT access and bottom foam | Included in mechanical checks |
| CNC screw insertion (nominal / tolerance range) | 4.5 / [4.25, 4.75] mm |
| PCBA bottom parts to case floor | 2.1 mm |
| USB-C plug clearance in tunnel (side / vertical) | 0.825 / 0.75 mm |
| Firmware checks (QMK/VIA/KLE vs layout, netlist vs pins, CircuitPython HID) | 34/34 pass |

Not verified here: QMK compilation (no toolchain in the build environment), JLCPCB part stock and
rotations in their placement preview, physical fit of machined/printed parts, USB enumeration, typing feel.
CNC D5 requires first-article assembly and thread inspection; digital checks do not certify a machined part.
Request JLCPCB JLC04161H-7628, 90 ohm differential +/-10% and the impedance coupon report;
geometric DRC and the filled-ground check are not signal-integrity tests.

Raw reports: `erc.json`, `drc.json`, `usb_reference.json`, `usb_layout.json`, `revision_geometry.json`, `mechanical.json`, `plate.json`, `firmware.json`, `pccf_print.json`, `schematic.net.xml`.
