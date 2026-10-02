"""Dump everything the silkscreen artwork must avoid, for both sides (KiCad's own geometry).

    "C:/Program Files/KiCad/10.0/bin/python.exe" Source/extract_obstacles.py <stage PCB dir>

Writes build/silk_obstacles.json in board-local mm (origin = PCB rear-left corner):
per side ("F", "B") the footprint silkscreen (outlines and visible texts) and the pads that
reach that side (SMD pads on that copper layer, every through-hole/NPTH), plus the drilled
holes and vias shared by both sides. gen_artwork.py reads it so the name, the poem and the
labels never touch pads, holes or legends.
"""
import json
import sys
from pathlib import Path

import pcbnew

STAGE = Path(sys.argv[1])
plan = json.loads((STAGE / "build" / "board_plan.json").read_text(encoding="utf-8"))
OX, OY = plan["page_offset"]
board = pcbnew.LoadBoard(str(STAGE / "Vamora75.kicad_pcb"))
ERR = pcbnew.FromMM(0.01)
SIDES = {"F": (pcbnew.F_SilkS, pcbnew.F_Cu, pcbnew.F_Mask), "B": (pcbnew.B_SilkS, pcbnew.B_Cu, pcbnew.B_Mask)}


def mm(p):
    return [round(pcbnew.ToMM(p.x) - OX, 4), round(pcbnew.ToMM(p.y) - OY, 4)]


def rings(ps):
    out = []
    ps.Simplify()
    for i in range(ps.OutlineCount()):
        ol = ps.Outline(i)
        out.append([mm(ol.CPoint(j)) for j in range(ol.PointCount())])
    return out


side_obs = {s: dict(silk=[], pads=[]) for s in SIDES}
holes, vias = [], []
for fp in board.GetFootprints():
    items = list(fp.GraphicalItems()) + [fp.Reference(), fp.Value()]
    for s, (silk_l, cu_l, mask_l) in SIDES.items():
        for it in items:
            if it.GetLayer() != silk_l:
                continue
            if hasattr(it, "IsVisible") and not it.IsVisible():
                continue
            ps = pcbnew.SHAPE_POLY_SET()
            it.TransformShapeToPolygon(ps, silk_l, 0, ERR, pcbnew.ERROR_OUTSIDE)
            side_obs[s]["silk"] += [dict(ref=fp.GetReference(), pts=r) for r in rings(ps)]
        for pad in fp.Pads():
            if pad.IsOnLayer(cu_l) or pad.IsOnLayer(mask_l):
                ps = pcbnew.SHAPE_POLY_SET()
                lay = mask_l if pad.IsOnLayer(mask_l) else cu_l
                pad.TransformShapeToPolygon(ps, lay, 0, ERR, pcbnew.ERROR_OUTSIDE)
                side_obs[s]["pads"] += [dict(ref=fp.GetReference(), pad=pad.GetNumber(), pts=r) for r in rings(ps)]
    for pad in fp.Pads():
        if pad.HasHole():
            ps = pcbnew.SHAPE_POLY_SET()
            pad.TransformHoleToPolygon(ps, 0, ERR, pcbnew.ERROR_OUTSIDE)
            holes += [dict(ref=fp.GetReference(), pts=r) for r in rings(ps)]
for t in board.GetTracks():
    if t.Type() == pcbnew.PCB_VIA_T:
        vias.append(dict(at=mm(t.GetPosition()), d=round(pcbnew.ToMM(t.GetWidth(pcbnew.F_Cu)), 3)))

out = dict(F=side_obs["F"], B=side_obs["B"], holes=holes, vias=vias, board=plan["board"])
(STAGE / "build" / "silk_obstacles.json").write_text(json.dumps(out), encoding="utf-8")
old = STAGE / "build" / "bottom_obstacles.json"          # rev 1.1 draft name
if old.exists():
    old.unlink()
print("obstacles: " + ", ".join(f"{s}: {len(o['silk'])} silk, {len(o['pads'])} pads" for s, o in side_obs.items())
      + f"; {len(holes)} holes, {len(vias)} vias")
