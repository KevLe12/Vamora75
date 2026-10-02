# Vamora75 rev 1.1 - build guide

## 1. Parts

The complete list is [Manufacturing/Vamora75_kit_BOM.csv](Manufacturing/Vamora75_kit_BOM.csv), and
how to order each item is in [Manufacturing/FABRICATION.md](Manufacturing/FABRICATION.md). In short:

* The PCBA. All parts are on the bottom: 82 sockets, 82 diodes, RP2040, flash, crystal, USB-C,
  ESD protection, LDO and buttons. It is assembled by the fab in one pass.
* The FR4 plate (standard or flex-cut) and 16 gaskets (20 x 4.5 x 2 mm).
* Case top and bottom, printed or machined, with 8 M3 x 8 socket-head screws and 8 M3 heat-set
  inserts. A split print also needs 5 dowels (3 x 12 mm).
* 4 PCB-mount screw-in stabilisers: three 2u (Backspace, Enter, LShift) and one 6.25u (Space).
* 82 MX-compatible switches (3- or 5-pin) and a 75 % keycap set (RShift 1.75u, Space 6.25u).
* Optional: 3 mm case foam, 3.5 mm plate foam and 4 bumpers (10 x 3 mm).

Tools: a multimeter, a soldering iron with a heat-set insert tip, a 2.5 mm hex key (long), tweezers
or a bent paper clip, and a USB-C cable whose plug overmould is 12.35 x 6.5 mm or smaller.

## 2. Bring up the bare PCBA (before any mechanical work)

1. **Look it over.** Check the bottom side for bridges at U1 (QFN-56) and U4, and check that every
   socket is flat. Diode cathode bars face pad 1, which is the ROW side.
2. **Check for shorts** with a meter, using the test pads near the controller:
   TP4 (+5V), TP2 (+3V3), TP1 (RUN), TP3 (GND). Neither +5V nor +3V3 may read as a short to GND
   (more than about 100 Ω, rising as the capacitors charge).
3. **Plug in USB.** With blank flash, the RP2040 enumerates as the drive `RPI-RP2`. Measure
   3.3 V (±3 %) between TP2 and TP3.
4. **Flash the firmware**: copy the QMK `.uf2`, or the CircuitPython UF2 plus its 4 files (see
   [Firmware/README.md](Firmware/README.md)).
5. **Test the matrix.** Open the VIA key tester (usevia.app -> Key Tester) or
   https://config.qmk.fm/#/test. Short each socket by touching both of its contacts through the two
   3 mm switch-pin holes from the top, using tweezers. All 82 keys must register, and each must
   register only once. Rev 1.1 has no key legends on the silkscreen (the front carries the big
   "Vamora75", the back the poem); use `Previews/layout.png` or
   `Manufacturing/PCB/Vamora75_assembly_bottom.pdf` to find a key.

## 3. Stabilisers, switches, plate

6. **Stabilisers.** Clip and lube them if you like, then fit the four screw-in stabilisers on the
   PCB top (ScottoKicad `Stabilizer_MX` footprints, marked ST1-ST4 on the fabrication layer). The
   screw heads go on the bottom. All four are in the standard orientation (wire toward the rear).
7. **Plate foam (optional).** Lay the 3.5 mm foam on the PCB top.
8. **Switches.** Clip four switches into the plate corners (Esc, Del, LCtrl, Right), line up the
   plate with the PCB, and press those switches into their sockets. Then fit the rest.
   **Support the sockets from below** as you press. The USB-C receptacle stands 3.3 mm below the
   PCB, taller than the sockets (1.85 mm), so let that corner hang over the edge of the table, or
   rest the PCB on the case foam. Straighten any bent switch pin rather than forcing it.

## 4. Case

9. **Heat-set inserts.** Press the 8 M3 inserts into the underside of the top case (the parting
   face) with an iron at about 220-240 °C for PETG/ASA. Keep them straight and flush.
   For a machined case, tap M3 instead (2.5 mm pilot).
10. **Split print only.** Glue each pair of halves with 3 x 12 mm dowels: 2 in the top seam, 3 in the
    bottom seam. Use epoxy or CA, and clamp the halves on a flat surface.
11. **Case foam.** Lay the 3 mm foam in the bottom case. It has cut-outs for the USB-C receptacle and
    the BOOT pin-hole.
12. **Gaskets.** Stick 8 gaskets onto the floors of the 8 pockets in the bottom case. Stick the other
    8 either on top of the plate tabs or onto the pocket ceilings of the top case.
13. **Drop in the PCB and plate as one unit.** The USB-C goes to the rear right, in line with the
    tunnel, and each tab rests on its lower gasket. The PCB and plate must not touch the case walls
    anywhere (there is 1 mm of clearance all round).
14. **Close the case.** Put the top case on, then drive the 8 M3 x 8 screws in from below. The rear
    counterbores are deep, so use a long hex key. Tighten in a cross pattern only until the two halves
    meet: the pockets already set the gasket compression (1.6 mm, 20 %), so overtightening only
    strains the inserts.
15. **Finish.** Fit the keycaps and the 4 bumpers in their recesses, then test every key again.
    Also test Fn+F1-F12, NKRO (Fn+N), sleep/wake and replugging the cable.

## 5. Reference data

Z stack, measured perpendicular to the plate, from the PCB top surface (0):

| Item | Z (mm) |
|---|---:|
| Case floor | -7.1 |
| Case foam (3 mm) | -7.1 to -4.1 |
| Lowest bottom-side part (USB-C) | -4.9 |
| Sockets (bottom of body) | -3.45 |
| PCB | -1.6 to 0 |
| Plate foam (optional) | 0 to 3.5 |
| Lower gasket seat / plate / upper gasket seat | 1.9 / 3.5-5.0 / 6.6 |
| Case parting plane | 4.25 |
| Top-case lip underside | 6.0 |
| Top of case | 11.0 |

The whole frame is tilted 6° about the front-bottom edge. The front edge of the case is 21.0 mm
high and the rear is 37.6 mm.

**Entering the bootloader later:** press Fn+Esc, hold Esc while plugging in, or double-tap RESET
(QMK). Last resort: push a paper clip through the pin-hole marked BOOT on the case bottom (rear
left as you look at the bottom) while plugging in.

**Hand-assembly alternative:** if your fab cannot source the Kailh sockets, order the PCBA without
them and hand-solder the 82 sockets (two large pads each). The controller parts (0.4 mm-pitch QFN)
should still be machine-assembled.
