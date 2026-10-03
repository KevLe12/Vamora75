# Vamora75 rev 1.2 - validation status

Generated 2026-10-03 by `Source/build_all.py`. These are digital checks of the
design files; no board has been built or tested yet (see BUILD_GUIDE.md, bring-up).

| Check | Result |
|---|---|
| Schematic ERC (KiCad 10, all severities) | clean |
| PCB DRC violations (all severities, zones refilled) | clean |
| PCB unconnected items | clean |
| Schematic <-> PCB parity | clean |
| Vamora75_Plate DRC / unconnected | clean / clean |
| Vamora75_Plate_flexcut DRC / unconnected | clean / clean |
| Plate min. FR4 web (switch-stab) | 1.438 mm |
| Mechanical interference (14 pairs, incl. stabilisers through plate and foam, keycaps bottomed out, USB-C plug) | PASS |
| PCBA bottom parts to case floor | 2.1 mm |
| USB-C plug clearance in tunnel (side / vertical) | 0.825 / 0.75 mm |
| Firmware checks (QMK/VIA/KLE vs layout, netlist vs pins, CircuitPython HID) | 30/30 pass |

Not verified here: QMK compilation (no toolchain in the build environment), JLCPCB part stock and
rotations in their placement preview, physical fit of printed parts, USB enumeration, typing feel.

Raw reports: `erc.json`, `drc.json`, `mechanical.json`, `plate.json`, `firmware.json`, `schematic.net.xml`.
