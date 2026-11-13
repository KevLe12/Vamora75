# Revision 1.6 — friend and professor review

The input files are preserved in `../Reference/Friend_2026-11-12/`, with SHA-256
hashes. Their board is revision 1.4, two layers, with the controller under the
spacebar. The supplied schematic adds C8 (100 nF on VBUS); other component values,
pin/net assignments and key functions match the existing design. The new revision
retains the approved four-layer stackup, short USB route and compact Custom layout.

| Feedback | Revision 1.6 resolution | Evidence |
|---|---|---|
| USBLC6 input/output routing | J1 to U2 pins 1/3, protected outputs from 6/4; direct copper bypasses removed | `usb_layout.json`, schematic and PCB |
| Local VBUS bypass | C8 100 nF 0402 near U2; corrected friend BOM fields, which specified a 10 uF 0603 part | BOM/CPL and `usb_layout.json` |
| Tenuous wide/narrow USB joins | Short uniform main pair retained; USB centreline joins and pad/via-centre endpoints enforced, including connector and RP2040 escapes | `usb_layout.json` |
| Isolated ground copper | Dedicated In2.Cu plane, ground vias and zone refill; zero unconnected items required | `drc.json`, `usb_reference.json` |
| Clearance errors | Keep 0.20 mm general clearance and 0.15 mm fine-pitch exceptions; no blanket reduction to 0.10 mm | `.kicad_dru`, project rules and DRC |
| Black PCB | Black mask / white silk / ENIG in model and ordering notes; select black on the actual order | Fabrication guide and previews |

The USBLC6's two channels are internally connected across 1–6 and 3–4; the
separate external net names enforce flow-through board routing. This follows
[ST DS4260 Figure 17](https://www.st.com/resource/en/datasheet/usblc6-2.pdf).
The RP2040's required external 27-ohm resistors remain fitted.

Software verification does not establish USB/ESD compliance, manufacturing yield,
physical fit or a perfect product. Obtain the JLCPCB stackup/impedance coupon review,
review bottom-side assembly orientation and build one prototype. PC-CF prints,
insert fit, bonding and actual slicer consumption require first-article validation.
QMK compilation is not part of the available toolchain; firmware checks are source,
netlist and HID-behaviour checks. DRC uses the existing project rule configuration, with no per-item exclusions.
Disabled categories are silk overlap, footprint type/filter mismatch, missing
courtyard, PTH/NPTH inside courtyard, track not centred on via, and tuning-profile
track geometry. Copper clearance, shorts and connectivity remain enabled. The
new USB-specific test independently requires track/via/pad centre connections;
the impedance geometry is checked separately from KiCad tuning profiles.
