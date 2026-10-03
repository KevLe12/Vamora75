# Vamora75 mechanical files

All parts share one coordinate system (STEP/STL, mm): X runs left to right along the front edge,
Y runs toward the rear, and Z points up from the desk. The case sits at its 6° typing angle.
The internal design frame (plate-parallel) is described in `Source/vamora_mech.py`.

| File | Contents |
|---|---|
| `Vamora75_assembly.step` | The whole keyboard: case, gaskets, plate (with its gold name), plate foam, case foam, the PCBA in KiCad's colours (black mask, white silkscreen, gold pads, Joe Scotto's switches, stabilisers, sockets and SMD parts) and sculpted keycaps. Coloured and instanced. |
| `Vamora75_PCB_plate.step` | **PCB + plate + every component**, without the case: the PCBA as above with the FR4 plate fitted 3.5 mm above the PCB (where it sits in the keyboard). Same frame as the PCBA STEP. |
| `Vamora75_PCB_plate.glb` | The same as a coloured glTF file: opens in Windows 3D Viewer, Blender or any web glTF viewer (no CAD software needed). |
| `Vamora75_PCBA.step` | The PCB with solder mask, silkscreen, pads and every component, including Joe Scotto's MX switch on every footprint, exported by KiCad. Origin is the PCB's front-left corner, board bottom at z = 0. |
| `Case/Vamora75_case_top.*`, `Case/Vamora75_case_bottom.*` | One-piece case parts. The top-case opening follows the key clusters (0.25 mm beyond each key's 19.05 mm cell, R1 corners, 0.5 mm chamfer); bridges of 4.3 mm and wider cover every gap between clusters, 1 mm above the plate |
| `Case/print_split/*_L/_R.*` | The same parts split for 250 x 210 mm beds (staggered seams, dowel holes) |
| `Plate/Vamora75_plate_FR4[_flexcut].dxf/.step/.stl` | Plate outline and openings (the DXF has OUTLINE, CUTOUTS and FLEX layers). Stabiliser openings 7.0 x 14 mm for PCB-mount stabilisers. |
| `Soft/*.dxf` | Gaskets (16), case foam (3 mm), plate foam (3.5 mm, with stabiliser/wire windows) |
| `key_positions.csv` | Every key: label, size, matrix, switch/diode refs, PCB and CAD coordinates, stabiliser spacing |
| `build/` | Intermediate files. The switch-free PCBA STEP used by `build_case.py` and the coloured render meshes (`*.npz`) are written here and deleted again by `build_all.py` after rendering. |

Key numbers (from `validation/mechanical.json`):

* Footprint 358.6 x 161.5 mm. Height 21.0 mm at the front and 37.6 mm at the rear. Typing angle 6°.
* Mount: 8 plate tabs (20 x 5.5 mm), 16 gaskets (20 x 4.5 x 2.0 mm) set to 1.6 mm (20 %).
  Tab pockets have 0.5 mm clearance. The PCB and plate have 1.0 mm clearance to every wall.
* Fasteners: 8 M3 x 8 ISO 4762 screws from below, into M3 x 4 heat-set inserts (4.0 mm holes) in the top case.
* USB-C tunnel: 14.0 x 8.0 mm, R3.5, centred on J1. It passes a USB-IF maximum overmould (12.35 x 6.5 mm)
  with 0.8 mm to spare.
* BOOT pin-hole: 2.2 mm, through the floor under SW90.
* 14 interference checks run on every rebuild. Every overlap volume is 0 mm³, including the PCB-mount
  stabilisers through the plate and the plate foam, keycaps pressed fully down (4 mm), the switches
  against the top case, and the gaskets against the plate and case.
* Keycaps in the models are generated sculpted (Cherry-like) caps for looks and clearance checks;
  any MX keycap set fits.
