"""Collect placement, netlist, routes, zones and artwork into build/board_plan.json
for kicad_build.py, and write the custom DRC rules file.

    python Source/make_board_plan.py <stage PCB dir>
"""
from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import vamora_layout as L  # noqa: E402
import pcb_plan as P  # noqa: E402

STAGE = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE.parent / "PCB"
SCH_UUID = str(uuid.uuid5(uuid.UUID("0f6b4a2c-3a1e-4f39-9a6e-7a3c5d75a075"), "schematic-root"))
REV = "1.1"

nets, comps = P.netlist(STAGE / "build" / "Vamora75.net.xml")
pl = P.placement()
routes = json.loads((STAGE / "build" / "routes.json").read_text())

# fiducials (board-only, bottom side) at three asymmetric corners
FIDS = {"FID1": (2.7, 2.7), "FID2": (L.BOARD_W - 2.7, 2.7), "FID3": (2.7, L.BOARD_H - 2.7)}

components = []
pads_by_ref = {}
for (ref, pin), n in nets.items():
    pads_by_ref.setdefault(ref, {})[pin] = n
for ref, c in sorted(comps.items()):
    q = pl.get(ref)
    if q is None:
        raise SystemExit(f"no placement for {ref}")
    fpname = c["footprint"].split(":", 1)[1]
    assert fpname == q["fp"], (ref, fpname, q["fp"])
    fields = {k: v for k, v in c["fields"].items() if k in ("LCSC", "MPN", "Description", "Datasheet", "Key", "Matrix") and v}
    components.append(dict(ref=ref, fp=fpname, value=c["value"], fields=fields, path=f"/{SCH_UUID}/{c['tstamp']}",
                           x=q["x"], y=q["y"], phi=q["phi"], bottom=q["bottom"], pads=pads_by_ref.get(ref, {}),
                           exclude_bom=ref.startswith("TP")))
for ref, (x, y) in FIDS.items():
    components.append(dict(ref=ref, fp="Fiducial_1mm_Mask2mm", value="Fiducial", fields={}, path=None, x=x, y=y,
                           phi=0, bottom=True, pads={}, board_only=True))
for ref, q in P.stab_placement().items():          # PCB-mount stabilisers: holes only, board-only
    components.append(dict(ref=ref, fp=q["fp"], value=f"Stabilizer {q['key']}", fields={}, path=None, x=q["x"], y=q["y"],
                           phi=0, bottom=False, pads={}, board_only=True))

W, H = L.BOARD_W, L.BOARD_H
board_rect = [(0, 0), (W, 0), (W, H), (0, H)]
zones = [
    dict(name="GND_B", net="GND", layers=["B.Cu"], pts=board_rect, priority=0, clearance=0.25, min_w=0.25),
    dict(name="GND_F", net="GND", layers=["F.Cu"], pts=board_rect, priority=0, clearance=0.25, min_w=0.25),
]
for name, (x0, y0, x1, y1) in P.FANOUT_AREAS.items():
    zones.append(dict(name=name, layers=["F.Cu", "B.Cu"], pts=[(x0, y0), (x1, y0), (x1, y1), (x0, y1)], rule_area=True))

netnames = sorted({n for n in nets.values()})
plan = dict(revision=REV, date="2026-10-02", page_offset=[L.PAGE_X0, L.PAGE_Y0],
            board=dict(w=W, h=H, corner_r=1.0), nets=netnames, components=components,
            tracks=routes["tracks"], vias=routes["vias"], zones=zones, polys=[], texts=[])

art = STAGE / "build" / "artwork.json"
if art.exists():
    a = json.loads(art.read_text(encoding="utf-8"))
    plan["polys"] = a.get("polys", [])
    plan["texts"] = a.get("texts", [])

(STAGE / "build" / "board_plan.json").write_text(json.dumps(plan), encoding="utf-8")

dru = '''(version 1)
# Vamora75 custom design rules (KiCad 10)
# Fine-pitch fan-outs (RP2040 QFN-56 0.4 mm, USON-8 flash, USB-C 0.5 mm pads) use 0.15 mm
# clearance inside named rule areas; JLCPCB's 2-layer minimum is 0.10 mm.
(rule "fanout clearance"
	(condition "A.intersectsArea('FANOUT_USB') || B.intersectsArea('FANOUT_USB') || A.intersectsArea('FANOUT_QSPI') || B.intersectsArea('FANOUT_QSPI') || A.intersectsArea('FANOUT_QFN') || B.intersectsArea('FANOUT_QFN')")
	(constraint clearance (min 0.15mm)))
# 0.45 mm / 0.3 mm vias are standard-price at JLCPCB (diameter >= hole + 0.15 mm)
(rule "small vias"
	(condition "A.Type == 'Via'")
	(constraint via_diameter (min 0.45mm))
	(constraint hole_size (min 0.2mm)))
'''
(STAGE / "Vamora75.kicad_dru").write_text(dru, encoding="utf-8")
print(f"plan: {len(components)} components, {len(routes['tracks'])} tracks, {len(routes['vias'])} vias, {len(zones)} zones")
