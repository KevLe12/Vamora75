"""Assemble PCB/Vamora75.kicad_pcb with KiCad's own Python (pcbnew).

    "C:/Program Files/KiCad/10.0/bin/python.exe" Source/kicad_build.py <stage PCB dir>

Input: build/board_plan.json written by make_board_plan.py (venv). Everything here is
mechanical: footprints, schematic links, nets, tracks, vias, zones, rule areas, graphics.
"""
import json
import sys
from pathlib import Path

import pcbnew

from kicad_stackup import set_stackup

STAGE = Path(sys.argv[1])
plan = json.loads((STAGE / "build" / "board_plan.json").read_text(encoding="utf-8"))
LIB = str(STAGE / "Vamora75.pretty")
OX, OY = plan["page_offset"]
MM = pcbnew.FromMM


def V(x, y):
    return pcbnew.VECTOR2I(MM(x + OX), MM(y + OY))


pcb_path = STAGE / "Vamora75.kicad_pcb"
if pcb_path.exists():
    pcb_path.unlink()
board = pcbnew.NewBoard(str(pcb_path))
board.SetCopperLayerCount(2)
ds = board.GetDesignSettings()
ds.SetBoardThickness(MM(1.6))
board.SetPageSettings(board.GetPageSettings())
tb = board.GetTitleBlock()
tb.SetTitle("Vamora75")
tb.SetRevision(plan["revision"])
tb.SetDate(plan["date"])
tb.SetCompany(plan["company"])
tb.SetComment(0, "75% hot-swap keyboard, RP2040, Kailh CPG151101S11 sockets (ScottoKicad footprints)")
tb.SetComment(1, "2-layer FR4 1.6 mm, 1 oz, black mask, ENIG, all SMT parts on the bottom side")
tb.SetComment(2, "Plated stabiliser holes with copper reinforcement rings")

# ---------------------------------------------------------------- nets
netinfo = {}
for name in plan["nets"]:
    ni = pcbnew.NETINFO_ITEM(board, name)
    board.Add(ni)
    netinfo[name] = ni

# ---------------------------------------------------------------- footprints
for c in plan["components"]:
    fp = pcbnew.FootprintLoad(LIB, c["fp"])
    if fp is None:
        raise SystemExit(f"footprint missing: {c['fp']}")
    fp.SetFPID(pcbnew.LIB_ID("Vamora75", c["fp"]))
    board.Add(fp)
    fp.SetReference(c["ref"])
    fp.SetValue(c["value"])
    for k, v in c["fields"].items():
        fp.SetField(k, v)
        fld = fp.GetField(k)
        if fld is not None:
            fld.SetVisible(False)
            fld.SetLayer(pcbnew.F_Fab)
    if c.get("path"):
        fp.SetPath(pcbnew.KIID_PATH(c["path"]))
        fp.SetSheetname("/")
        fp.SetSheetfile("Vamora75.kicad_sch")
    if c.get("board_only"):
        fp.SetBoardOnly(True)
        fp.SetExcludedFromBOM(True)
        fp.SetExcludedFromPosFiles(True)
    if c.get("exclude_bom"):
        fp.SetExcludedFromBOM(True)
    fp.SetPosition(V(c["x"], c["y"]))
    if c["bottom"]:
        fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        fp.SetOrientationDegrees((c["phi"] + 180) % 360)
    else:
        fp.SetOrientationDegrees(c["phi"])
    for pad in fp.Pads():
        n = c["pads"].get(pad.GetNumber())
        if n:
            pad.SetNet(netinfo[n])
        if c["ref"] == "U1" and pad.GetNumber() == "57":
            pad.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)   # exposed pad + its vias: solid to GND
    # reference text: small, on fab layer (assembly drawings); value (key legend) stays as designed
    fp.Reference().SetVisible(c.get("show_ref", False))

# ---------------------------------------------------------------- outline
W, H, r = plan["board"]["w"], plan["board"]["h"], plan["board"]["corner_r"]


def seg(a, b, layer=pcbnew.Edge_Cuts, w=0.1):
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(V(*a))
    s.SetEnd(V(*b))
    s.SetLayer(layer)
    s.SetWidth(MM(w))
    board.Add(s)


def arc3(a, m, b, layer=pcbnew.Edge_Cuts, w=0.1):
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_ARC)
    s.SetArcGeometry(V(*a), V(*m), V(*b))
    s.SetLayer(layer)
    s.SetWidth(MM(w))
    board.Add(s)


k = r * (1 - 0.5 ** 0.5)
seg((r, 0), (W - r, 0)); seg((W, r), (W, H - r)); seg((W - r, H), (r, H)); seg((0, H - r), (0, r))
arc3((W - r, 0), (W - k, k), (W, r)); arc3((W, H - r), (W - k, H - k), (W - r, H))
arc3((r, H), (k, H - k), (0, H - r)); arc3((0, r), (k, k), (r, 0))

# ---------------------------------------------------------------- tracks / vias
for t in plan["tracks"]:
    tr = pcbnew.PCB_TRACK(board)
    tr.SetStart(V(*t["a"]))
    tr.SetEnd(V(*t["b"]))
    tr.SetWidth(MM(t["w"]))
    tr.SetLayer(pcbnew.F_Cu if t["layer"] == "F.Cu" else pcbnew.B_Cu)
    tr.SetNet(netinfo[t["net"]])
    board.Add(tr)
for v in plan["vias"]:
    via = pcbnew.PCB_VIA(board)
    via.SetPosition(V(*v["at"]))
    via.SetWidth(MM(v["d"]))
    via.SetDrill(MM(v["drill"]))
    via.SetViaType(pcbnew.VIATYPE_THROUGH)
    via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    via.SetNet(netinfo[v["net"]])
    board.Add(via)


# ---------------------------------------------------------------- zones and rule areas
def poly_zone(pts, layers, net=None, name=None, rule_area=False, priority=0, clearance=0.25, min_w=0.25,
              thermal_gap=0.35, spoke=0.35):
    z = pcbnew.ZONE(board)
    ls = pcbnew.LSET()
    for l in layers:
        ls.AddLayer(l)
    z.SetLayerSet(ls)
    ol = z.Outline()
    ol.NewOutline()
    for x, y in pts:
        ol.Append(MM(x + OX), MM(y + OY))
    if rule_area:
        z.SetIsRuleArea(True)
        z.SetDoNotAllowTracks(False)
        z.SetDoNotAllowVias(False)
        z.SetDoNotAllowPads(False)
        z.SetDoNotAllowZoneFills(False)
        z.SetDoNotAllowFootprints(False)
    else:
        z.SetNet(netinfo[net])
        z.SetAssignedPriority(priority)
        z.SetLocalClearance(MM(clearance))
        z.SetMinThickness(MM(min_w))
        z.SetThermalReliefGap(MM(thermal_gap))
        z.SetThermalReliefSpokeWidth(MM(spoke))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THT_THERMAL)   # SMD pads solid, THT pads thermal
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    if name:
        z.SetZoneName(name)
    board.Add(z)
    return z


for zn in plan["zones"]:
    layers = [pcbnew.F_Cu if l == "F.Cu" else pcbnew.B_Cu for l in zn["layers"]]
    poly_zone(zn["pts"], layers, zn.get("net"), zn.get("name"), zn.get("rule_area", False), zn.get("priority", 0),
              zn.get("clearance", 0.25), zn.get("min_w", 0.25))

# ---------------------------------------------------------------- graphics (silkscreen polygons and text)
LAYERS = {"B.SilkS": pcbnew.B_SilkS, "F.SilkS": pcbnew.F_SilkS, "B.Fab": pcbnew.B_Fab, "F.Fab": pcbnew.F_Fab,
          "B.Mask": pcbnew.B_Mask, "F.Mask": pcbnew.F_Mask, "Cmts.User": pcbnew.Cmts_User}


def layer_id(name):
    lid = LAYERS.get(name, board.GetLayerID(name))
    if lid < 0:
        raise SystemExit(f"unknown layer {name}")
    return lid


for g in plan.get("polys", []):
    layer = layer_id(g["layer"])
    for ring in g["rings"]:
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_POLY)
        s.SetFilled(True)
        s.SetLayer(layer)
        s.SetWidth(0)
        sps = pcbnew.SHAPE_POLY_SET()
        sps.NewOutline()
        for x, y in ring["outer"]:
            sps.Append(MM(x + OX), MM(y + OY))
        for hi, h in enumerate(ring["holes"]):
            sps.NewHole()
            for x, y in h:
                sps.Append(MM(x + OX), MM(y + OY), -1, hi)
        s.SetPolyShape(sps)
        board.Add(s)
for t in plan.get("texts", []):
    tx = pcbnew.PCB_TEXT(board)
    tx.SetText(t["text"])
    tx.SetPosition(V(*t["at"]))
    tx.SetLayer(layer_id(t["layer"]))
    tx.SetTextSize(pcbnew.VECTOR2I(MM(t["size"]), MM(t["size"])))
    tx.SetTextThickness(MM(t.get("thick", t["size"] * 0.15)))
    if t["layer"].startswith("B."):
        tx.SetMirrored(True)
    tx.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_CENTER)
    if t.get("angle"):
        tx.SetTextAngleDegrees(t["angle"])
    board.Add(tx)

# aux origin at the board's lower-left (fabrication outputs)
ds.SetAuxOrigin(V(0, H))
ds.SetGridOrigin(V(0, 0))

filler = pcbnew.ZONE_FILLER(board)
filler.Fill(board.Zones())
board.Save(str(pcb_path))
set_stackup(pcb_path, 1.6)
print("saved", pcb_path, "footprints", len(board.GetFootprints()), "tracks", len(board.GetTracks()), "zones", board.GetAreaCount())
