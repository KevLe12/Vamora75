# Vamora75 sources

Deliverables are generated from the parameter files and the checked copper routing snapshot.
Rebuilds preserve the verified traces and vias. The revision is identified by the
containing folder and KiCad title blocks; matching project basenames remain stable. A layout, footprint-pad or netlist change
requires a new routed and DRC-checked snapshot; the build rejects stale routing.

```
python -m venv .venv && .venv\Scripts\pip install -r Source\requirements.txt
.venv\Scripts\python Source\build_all.py              # complete rebuild using checked copper routing
.venv\Scripts\python Source\build_all.py --skip-pcb   # keep the routed board, rebuild the rest
.venv\Scripts\python Source\build_all.py --footprints # also regenerate footprints + 3D models
```

KiCad 10.0.6 must be installed at `C:\Program Files\KiCad\10.0` (paths are at the top of
`build_pcb.py`, `build_all.py`, `export_manufacturing.py`). Joe Scotto's **ScottoKicad** library
is read from `A:\ScottoKicad` (set `VAMORA_SCOTTO` to move it). You only need it to regenerate
footprints (`--footprints`); the project already carries copies of everything it uses. The Segoe UI fonts ship with Windows; any TTF works
(constants in `vamora_logo.py`).

## Parameter files (edit these)

| File | Controls |
|---|---|
| `vamora_layout.py` | revision, date and designers; key positions and sizes, keycodes, matrix row/column of every key, RP2040 GPIO map, stabiliser spacing, PCB size |
| `pcb_plan.py` | placement of diodes and of every controller part (board coordinates), fan-out rule areas |
| `pcb_routes.json` | checked tracks and vias, with a fingerprint of the matching board dimensions, copper layers, placement, footprint geometry and netlist |
| `vamora_mech.py` | Z stack, plate tabs, gaskets, case margins, screws, USB tunnel, typing angle, plate cut-outs (incl. stabiliser openings), foam windows, print split |
| `vamora_logo.py` | the "Vamora75" name (`name_text`, Segoe UI Black), text shaping, the product colour palette |

## Pipeline

| Step | Script | Output |
|---|---|---|
| Footprints + 3D models | `gen_footprints.py`, `upgrade_footprints.py` (KiCad Python) | `PCB/Vamora75.pretty`, `PCB/3dmodels`: ScottoKicad hot-swap (with his MX switch model), stabiliser, diode, USB-C and passive footprints and models; KiCad stock RP2040, flash and crystal parts; a generated TS-1187A model. Re-saved in KiCad 10 format; stabiliser holes plated with copper reinforcement rings and keep-outs. |
| Schematic | `gen_schematic.py` | `PCB/Vamora75.kicad_sch` + project symbol library |
| Project / rules | `gen_project.py`, `make_board_plan.py` | `.kicad_pro` (net classes, JLCPCB limits), `.kicad_dru` (0.15 mm in fan-out areas and between the USB pair) |
| Routing | `route_board.py` | `PCB/build/routes.json` restored from `pcb_routes.json` only when its design fingerprint matches |
| Checks | `test_routing.py`, `check_connectivity.py`, `test_usb_layout.py` | Reject stale routing; check connectivity/clearance, ESD input/output nets, C8 BOM, centreline USB joins and via drills clear of SMD pads |
| Board | `kicad_build.py` (KiCad Python), `kicad_stackup.py` | `PCB/Vamora75.kicad_pcb` - footprints, nets, tracks, vias, GND pours, rule areas, artwork, black-mask ENIG stackup |
| Silkscreen art | `extract_obstacles.py` (KiCad Python), `gen_artwork.py` | front: a very large "Vamora75" across the middle (knocked out around holes and pads); back: *Nam Quốc Sơn Hà* centred under the F-row, the designers' names under the space bar, BOOT/RESET/rev labels, readable from below |
| DRC / ERC | `build_pcb.py` (orchestrates all of the above) | `validation/erc.json`, `validation/drc.json`; `check_usb_reference.py` verifies actual In2.Cu fill beneath the pair |
| Plate | `build_plate.py`, `kicad_plate.py` | `Mechanical/Plate/*` DXF/STEP/STL, `Plate/*.kicad_pcb` |
| Case | `build_case.py` (+ `cad_mesh.py`) | `Mechanical/Case/*`, `Mechanical/Soft/*`, `Mechanical/Vamora75_assembly.step`, `Mechanical/Vamora75_PCB_plate.step/.glb`, `validation/mechanical.json`, render meshes. Inputs: a switch-free PCBA STEP for the checks and the full PCBA STEP for the assemblies. Sculpted keycaps are generated here. |
| Component fit | `test_component_interference.py` | Exact intersections of neighboring component assemblies in the exported PCBA STEP |
| Print hardware | `test_print_fasteners.py` | Nominal screw, driver and insert bore envelopes checked against exported print-case STEP solids |
| PC-CF prints | `prepare_pccf.py` | Four oriented split-case STLs, insert coupon, print checks and ZIP; actual slicer and first-print validation required |
| Renders | `render_previews.py` | `Previews/*.png`: VTK product renders (PBR materials, studio lighting, ambient occlusion, soft shadows) + KiCad renders in the board's stackup colours (`pcb_top` bare, `pcb_top_switches`, `pcb_bottom`, `plate_top`) |
| Manufacturing | `export_manufacturing.py`, `assembly_plot_board.py` | Gerbers, drill, JLCPCB BOM/CPL, PDFs, plate Gerbers, kit BOM |
| Firmware | `gen_firmware.py`, `test_firmware.py` | QMK/VIA/CircuitPython/KLE + `validation/firmware.json` |
| Artwork | `export_artwork.py` | `Artwork/*`: "Vamora75" name SVG/PNG/DXF + overview sheet |
| Layout data | `export_layout.py` | `layout.json`, `Mechanical/key_positions.csv`, `Previews/layout.png` |
| Report | `build_all.py` | `validation/STATUS.md` |

Helpers: `sexp.py` (KiCad s-expressions), `kicad_fp.py` (footprint pad geometry in board
coordinates; bottom side = mirror then rotate, verified against pcbnew),
`cad_mesh.py` (coloured STEP reading, meshes, STEP/GLB assembly writer), `kicad_stackup.py`.

## Changing things safely

* CNC case revision D5 is independent of PCB revision 1.7. `check_cnc.py` adds screw, BOOT and
  bottom-foam checks to `build_case.py`. Main case exports are CNC pilots; `print_one_piece/`
  and `print_split/` retain the insert bores. `export_case_drawings.py` writes the three-sheet
  CNC drawing package and thread/tolerance requirements. Keep these together when ordering.

* **Moving keys, changing the matrix or moving controller parts**: update `vamora_layout.py`
  and/or `pcb_plan.py`, reroute the PCB, and replace `pcb_routes.json` with checked routing for
  that design. Do not change only its fingerprint to bypass the mismatch check. Run the full
  build and require zero DRC/unconnected items before exporting a new revision.
* **Different typing angle / case height**: `vamora_mech.py` (`TYPING_ANGLE`, `CASE_TOP`, `FLOOR_Z`) -
  `build_case.py` re-runs every interference check.
* The KiCad files are normal KiCad 10 files: you can also edit them by hand in KiCad. A later
  `build_pcb.py` run overwrites the schematic and board, so either keep working in KiCad from then
  on or port the change into the generators.

Earlier revisions are retained in the original working folder's local archive,
which is not included in the GitHub snapshot. Run the full build on a fresh clone
before using `--skip-pcb` or `test_revision_geometry.py`: they need generated PCB
intermediates.
