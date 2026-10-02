"""Build the FR4 plate boards (KiCad) from Plate/build/plate_plan.json.

    "C:/Program Files/KiCad/10.0/bin/python.exe" Source/kicad_plate.py

Writes Plate/Vamora75_Plate.kicad_pcb and Plate/Vamora75_Plate_flexcut.kicad_pcb:
Edge.Cuts = plate outline + every switch / stabiliser / flex opening; artwork on the
top: copper emblem and wordmark exposed through the solder mask, tagline in silkscreen.
"""
import json
import shutil
from pathlib import Path

import pcbnew

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "Plate"
plan = json.loads((OUT / "build" / "plate_plan.json").read_text(encoding="utf-8"))
OX, OY = 40.0, 80.0                     # same page position as the main PCB
MM = pcbnew.FromMM


def poly(board, pts, layer, filled, width=0.0):
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_POLY)
    s.SetFilled(filled)
    s.SetLayer(layer)
    s.SetWidth(MM(width))
    sps = pcbnew.SHAPE_POLY_SET()
    sps.NewOutline()
    for x, y in pts:
        sps.Append(MM(x + OX), MM(y + OY))
    s.SetPolyShape(sps)
    board.Add(s)


for key, title in (("standard", "Vamora75 FR4 plate"), ("flexcut", "Vamora75 FR4 plate (flex cuts)")):
    v = plan["variants"][key]
    fname = "Vamora75_Plate" + ("_flexcut" if key == "flexcut" else "")
    path = OUT / f"{fname}.kicad_pcb"
    if path.exists():
        path.unlink()
    board = pcbnew.NewBoard(str(path))
    board.SetCopperLayerCount(2)
    ds = board.GetDesignSettings()
    ds.SetBoardThickness(MM(plan["board"]["t"]))
    tb = board.GetTitleBlock()
    tb.SetTitle(title)
    tb.SetRevision("1.1")
    tb.SetDate("2026-10-02")
    tb.SetCompany("Vamora - Viet Nam / USA / Morocco")
    tb.SetComment(0, "FR4 1.5 mm (1.6 mm also fits), black mask both sides, ENIG for the gold Vamora75 name")
    tb.SetComment(1, "Non-electrical part: no nets; route every Edge.Cuts opening")
    for r in v["edge"]:
        poly(board, r["outer"], pcbnew.Edge_Cuts, False, 0.05)
        for h in r["holes"]:
            poly(board, h, pcbnew.Edge_Cuts, False, 0.05)
    for r in plan["copper"]:
        poly(board, r["outer"], pcbnew.F_Cu, True)
        poly(board, r["outer"], pcbnew.F_Mask, True)        # mask opening = exposed copper (gold with ENIG)
    for r in plan["silk"]:
        poly(board, r["outer"], pcbnew.F_SilkS, True)
    ds.SetAuxOrigin(pcbnew.VECTOR2I(MM(OX), MM(OY + plan["board"]["h"])))
    board.Save(str(path))
    pro = OUT / f"{fname}.kicad_pro"
    if not pro.exists():
        pro.write_text(json.dumps({"meta": {"filename": f"{fname}.kicad_pro", "version": 3},
                                   "board": {"design_settings": {"rules": {"min_copper_edge_clearance": 0.3}}}},
                                  indent=2), encoding="utf-8")
    print("saved", path.name, "edge rings", sum(1 + len(r["holes"]) for r in v["edge"]))
