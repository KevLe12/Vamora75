# PC-CF case — CORE One L

Use `Vamora75_PCCF_print.zip` or `Mechanical/Case/print_pccf/`. These are the
insert-bore print variants, already oriented with their bed faces at Z=0. Keep
100% scale. Do not print the CNC STEP pilots and try to force inserts into them.
The four parts retain the compact Custom layout, rear-left USB tunnel, BOOT hole,
gasket seats and foam clearances. No keyboard dimensions were reduced.

The assumed printer is the [Prusa CORE One L](https://www.prusa3d.com/p/core-one-l/),
with a 300 x 300 x 330 mm envelope. Each part fits individually with room for a
brim. Print one part per plate until a complete first case has been checked.
Top halves are face down; bottom halves sit on their flat underside.

## Material and starting settings

Assumption: **Prusament PC Blend Carbon Fiber, 800 g spools**. Other brands need
their own material profile. Use the printer/nozzle-specific PrusaSlicer profile
and a hardened nozzle suitable for abrasive filament. Start with approximately
2.6 mm shell thickness, at least 1.2 mm top/bottom skins, and 20–30% gyroid infill.
Check the sliced preview around screw seats, inserts, seams and gasket pockets;
make those small regions solid if the toolpaths leave inadequate support.

The [manufacturer's TDS](https://prusament.com/wp-content/uploads/2023/04/TDS_Prusament-PCCF_2023_EN.pdf)
specifies 285 +/-10 C nozzle, 110 +/-10 C bed and density 1.22 g/cm3. Use its
material profile for cooling and the sheet-specific adhesion/release instructions.
This package contains geometry, not G-code or a validated slicer preset.

## Quantity for three cases

| Part | Estimated grams at 20–30% core infill |
|---|---:|
| Bottom left | 232–268 |
| Bottom right | 143–164 |
| Top left | 38–40 |
| Top right | 55–58 |
| One complete case | 468–530 |
| Three cases plus 25% allowance | 1,756–1,989 |

Budget **three 800 g spools (2.4 kg total)**. These are geometric estimates using
2.6 mm walls and 1.2 mm skins, not slicer measurements. Recalculate from actual
sliced filament totals before ordering. Extensive supports, failed prints, or
solid infill can exceed this budget; three solid cases alone would use about 2.89 kg.

## Fit and assembly

1. Print the included insert coupon first with the case settings. Along its
   42 mm length, bores are 3.9, 4.0, 4.1 mm left to right, each 5 mm deep.
   The actual case uses 4.0 mm bores for M3 x 4 mm inserts with nominal 4 mm OD.
   Verify the exact insert manufacturer's recommended hole size. This coupon
   screens fit; check insertion and pullout on a first case before repeating.
2. Calibrate insertion temperature on the coupon for this material and insert.
   The old PETG/ASA 220–240 C guidance is not a validated PC-CF setting. Seat
   inserts straight and flush without forcing or deforming the shell.
3. Dry-fit each seam with 3 x 12 mm dowels (two top, three bottom per case).
   Printed dowel holes are nominal 3.1 mm diameter, 6 mm deep per side. Clear
   debris and verify the two faces close fully; fit by hand without splitting them.
4. Bond top halves together and bottom halves together separately. Use a
   polycarbonate-compatible structural adhesive, following its preparation and
   cure instructions. Verify adhesion on a PC-CF scrap first; PC-CF bond strength
   has not been tested. Keep adhesive out of gasket seats, screw holes and USB tunnel.
5. Clamp on a flat reference while curing. Do not glue top to bottom: those remain
   removable with eight M3 x 8 screws. For three cases buy 24 inserts, 24 screws
   and 15 dowels, plus spares.
6. Check case flatness, USB plug seating, BOOT probe access and screw fit before
   fitting the PCB. Carbon-filled plastic must not be relied on as electrical
   insulation. Retain the specified foam/clearance and verify no exposed PCB
   copper or solder touches the case; add a suitable insulating film if needed.

Physical print, bond, insert retention and complete keyboard assembly remain
first-article checks. Do not use uniform scaling to correct fit: it also changes
key spacing, gasket seats and the USB/BOOT alignment.
