# Attribution and sources

## Manta75 hardware and firmware

Controller circuitry and the key arrangement are derived from **The Manta75**, by **Eric Becourt (Rico / mymakercorner)**.

- Hardware source: https://github.com/mymakercorner/the_manta75
- Supplied local reference: the_manta75 directory provided by the user.
- Hardware license: Creative Commons Attribution 4.0 International, copied in Licenses/Manta75-CC-BY-4.0.md.
- Firmware source: https://github.com/mymakercorner/qmk_firmware/tree/the_manta75
- QMK source and binary retain their original GPL licensing and notices; see Firmware/QMK-LICENSE.txt.

Changes made for this package: fixed 83-key ANSI layout; Kailh MX socket footprints; fresh matrix routing; removal of personal copper/mask artwork; new ISP access pads and service markings; local libraries; a rebuilt modern schematic; a new two-piece gasket-mounted case, plate, gasket pattern, and optional risers. Original source-author credit is retained here instead of decorative PCB artwork. The supplied VIA firmware binary is unmodified.

## USB daughterboard

**Unified Daughterboard Project — UDB-C-JSH**, revision C5, downloaded source commit prefix **2b6c52a**.

- Source: https://github.com/Unified-Daughterboard/UDB-C-JSH
- Documentation: https://unified-daughterboard.github.io/
- License: MIT; complete notice in USB_daughterboard/LICENSE.
- Original contributors are credited in USB_daughterboard/README.md.
- Changes and remaining assembly review item are recorded in USB_daughterboard/MODIFICATIONS.md.

## Library symbols and manufacturer drawing

- Local schematic symbol subset: KiCad community libraries from the installed KiCad 10 distribution. They retain the KiCad library CC-BY-SA 4.0 license with design-use exception; see Licenses/KiCad-library-license.md and https://www.kicad.org/libraries/license/ . The symbol subsets were expanded from inherited symbols and packaged locally for portability.
- Kailh socket geometry reference: manufacturer drawing **CPG151101S11-16 / KHA-PG1511-388EN**, 2022-06-01, in the manufacturer's product specification: https://www.kailhswitch.com/Content/upload/pdf/202215927/CPG151101S11-16.pdf . Manufacturer documents and marks remain the property of their owners; the original PDF is not redistributed in this package.

The new files are provided as a prototype derivative with these provenance notices. No endorsement by the original designers, KiCad, or component manufacturers is claimed.
