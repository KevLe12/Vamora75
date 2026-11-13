"""Check nominal print-variant screw and insert paths in the exported STEP solids."""
from pathlib import Path
import json
import cadquery as cq
import vamora_mech as M
from build_case import cyl, world, vol, wpt

root = Path(__file__).resolve().parents[1]
folder = root / 'Mechanical/Case/print_one_piece'
bottom = cq.importers.importStep(str(folder / 'Vamora75_case_bottom_print.step'))
top = cq.importers.importStep(str(folder / 'Vamora75_case_top_print.step'))
s = M.SCREW
seat = M.PRINT_HEAD_SEAT_Z
checks = {}
for i, (x, y) in enumerate(M.SCREWS, 1):
    envelopes = {
        'shaft': (bottom, cyl(x, y, 3, seat, M.SPLIT_Z)),
        'head': (bottom, cyl(x, y, 5.5, seat - 3, seat)),
        'driver': (bottom, cyl(x, y, 3, -80, seat - 1)),
        'insert bore': (top, cyl(x, y, s['insert_d'] - .002, M.SPLIT_Z, M.SPLIT_Z + s['insert_depth'] - .001)),
    }
    for name, (part, tool) in envelopes.items():
        checks[f'{i}: {name}'] = round(vol(part, world(tool)), 6)
    assert wpt(x, y, seat - 3)[2] > 0, 'Head below desk plane'
grip = M.SPLIT_Z - seat
insertion = s['length'] - grip
assert 0 < insertion < 4 <= s['insert_depth']
report = dict(result='PASS' if all(v < .001 for v in checks.values()) else 'FAIL',
              screw_count=len(M.SCREWS), grip_mm=grip, nominal_insertion_mm=insertion,
              insert_bore_depth_mm=s['insert_depth'], overlap_mm3=checks,
              scope='Nominal CAD only; insert fit, thread engagement and retention require physical testing')
(root / 'validation/print_fasteners.json').write_text(json.dumps(report, indent=2))
assert report['result'] == 'PASS', report
print(json.dumps(report, indent=2))
