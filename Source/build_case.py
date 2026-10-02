"""Vamora75 rev 1.1 case: two-piece tab-gasket case with a 6 degree typing angle.

    python Source/build_case.py <PCBA STEP from kicad-cli>     (CAD venv)

Everything is modelled in the plate frame of vamora_mech (Z = 0 on the PCB top), then
tilted about the front-bottom edge; the bottom case is trimmed flat on the desk plane.
Outputs (Mechanical/):
  Case/Vamora75_case_top|bottom.step/.stl     one-piece parts (CNC or >= 360 mm printers)
  Case/print_split/*_L|_R.step/.stl           staggered split for 250 x 210 mm beds
  Soft/*.dxf                                  gaskets, case foam, plate foam
  Vamora75_assembly.step                      case + gaskets + plate + PCBA + switches + keycaps
  build/*.stl                                 world-frame meshes for the renders
and validation/mechanical.json (interference / clearance report).
"""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import cadquery as cq
from shapely import affinity
from shapely.geometry import Point, box
from shapely.ops import unary_union

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import vamora_layout as L  # noqa: E402
import vamora_logo as V  # noqa: E402
import vamora_mech as M  # noqa: E402

ROOT = HERE.parent
OUT = ROOT / "Mechanical"
PCBA_STEP = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "Mechanical" / "Vamora75_PCBA.step"
T0 = time.time()
Z_DEEP = -80.0                 # bottom case is modelled this deep, then trimmed by the desk plane
TX = (M.MARGIN, M.MARGIN, -(M.FLOOR_Z - M.FLOOR_T))     # front-bottom edge -> origin
A = math.radians(M.TYPING_ANGLE)
REPORT = {}


def log(*a):
    print(f"[{time.time() - T0:6.1f}s]", *a, flush=True)


# ------------------------------------------------------------------ helpers
def rbox(x0, y0, x1, y1, z0, z1, r=0.0):
    w = cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))
    if r > 0:
        w = w.edges("|Z").fillet(r)
    return w


def cyl(x, y, d, z0, z1):
    return cq.Workplane("XY").circle(d / 2).extrude(z1 - z0).translate((x, y, z0))


def ext(g, z0, z1):
    """Extrude a shapely (multi)polygon with holes."""
    out = None
    for p in V.polygons(g):
        wp = cq.Workplane("XY").polyline(list(p.exterior.coords)[:-1]).close()
        for r in p.interiors:
            wp = wp.polyline(list(r.coords)[:-1]).close()
        s = wp.extrude(z1 - z0).translate((0, 0, z0))
        out = s if out is None else out.union(s)
    return out


def world(obj):
    return obj.translate(TX).rotate((0, 0, 0), (1, 0, 0), M.TYPING_ANGLE)


def world_loc():
    from OCP.gp import gp_Ax1, gp_Dir, gp_Pnt, gp_Trsf, gp_Vec
    t1, r = gp_Trsf(), gp_Trsf()
    t1.SetTranslation(gp_Vec(*TX))
    r.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(1, 0, 0)), A)
    return cq.Location(r.Multiplied(t1))


def world_moved(obj):
    """Same placement as world(), applied as a location: shared sub-shapes stay shared."""
    shape = obj.val() if hasattr(obj, "val") else obj
    return cq.Workplane("XY").add(shape.moved(world_loc()))


def wpt(x, y, z):
    x, y, z = x + TX[0], y + TX[1], z + TX[2]
    return (x, y * math.cos(A) - z * math.sin(A), y * math.sin(A) + z * math.cos(A))


def axis_exit(x, y):
    """Where a plate-frame vertical axis through (x, y) meets the desk plane (world z = 0)."""
    x, y = x + TX[0], y + TX[1]
    z = -y * math.tan(A)                 # translated-frame z where world Z = 0
    return (x, y * math.cos(A) - z * math.sin(A))


def comp(shapes):
    """One Workplane holding a single compound (robust for booleans and export)."""
    return cq.Workplane("XY").add(cq.Compound.makeCompound([getattr(s, "val", lambda: s)() for s in shapes]))


def vol(a, b):
    try:
        q = a.intersect(b)
        return sum(s.Volume() for s in q.solids().vals())
    except Exception as e:          # noqa: BLE001
        log("intersection failed", e)
        return -1.0


def pocket_rects():
    out = []
    for side, pos in M.TABS:
        x0, y0, x1, y1 = M.tab_rect(side, pos, extra=M.TAB_POCKET_CLEAR, inner=1.0).bounds
        out.append((x0, y0, x1, y1))
    return out


def write_step_assembly(parts, path):
    """Coloured STEP assembly that keeps shared instances (82 identical sockets/switches are
    written once). CadQuery's Assembly.export expands every instance (~20x larger files)."""
    from OCP.Interface import Interface_Static
    from OCP.Quantity import Quantity_Color, Quantity_TypeOfColor
    from OCP.STEPCAFControl import STEPCAFControl_Writer
    from OCP.STEPControl import STEPControl_AsIs
    from OCP.TCollection import TCollection_ExtendedString
    from OCP.TDataStd import TDataStd_Name
    from OCP.TDF import TDF_Label, TDF_LabelSequence
    from OCP.TDocStd import TDocStd_Document
    from OCP.TopLoc import TopLoc_Location
    from OCP.XCAFDoc import XCAFDoc_ColorType, XCAFDoc_DocumentTool

    doc = TDocStd_Document(TCollection_ExtendedString("XmlOcaf"))
    st = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    ct = XCAFDoc_DocumentTool.ColorTool_s(doc.Main())
    root = st.NewShape()
    TDataStd_Name.Set_s(root, TCollection_ExtendedString("Vamora75"))
    for item in parts:
        name, wp, rgb = item[:3]
        loc = item[3].wrapped if len(item) > 3 and item[3] is not None else TopLoc_Location()
        shape = wp.val().wrapped if hasattr(wp, "val") else wp.wrapped
        col = Quantity_Color(*rgb, Quantity_TypeOfColor.Quantity_TOC_RGB)
        lab = st.AddShape(shape, True)
        TDataStd_Name.Set_s(lab, TCollection_ExtendedString(name))
        if st.IsAssembly_s(lab):
            comps = TDF_LabelSequence()
            st.GetComponents_s(lab, comps, True)
            for i in range(1, comps.Length() + 1):
                ref = TDF_Label()
                if st.GetReferredShape_s(comps.Value(i), ref):
                    ct.SetColor(ref, col, XCAFDoc_ColorType.XCAFDoc_ColorGen)
        else:
            ct.SetColor(lab, col, XCAFDoc_ColorType.XCAFDoc_ColorGen)
        c = st.AddComponent(root, lab, loc)
        TDataStd_Name.Set_s(c, TCollection_ExtendedString(name))
    st.UpdateAssemblies()
    Interface_Static.SetIVal_s("write.surfacecurve.mode", 0)
    w = STEPCAFControl_Writer()
    w.SetColorMode(True)
    w.SetNameMode(True)
    w.Transfer(doc, STEPControl_AsIs)
    w.Write(str(path))


# ------------------------------------------------------------------ bottom case
def bottom_case():
    b = rbox(-M.MARGIN, -M.MARGIN, M.BW + M.MARGIN, M.BH + M.MARGIN, Z_DEEP, M.SPLIT_Z, M.CASE_R)
    b = b.cut(rbox(-M.CLEAR, -M.CLEAR, M.BW + M.CLEAR, M.BH + M.CLEAR, M.FLOOR_Z, M.SPLIT_Z + 1, M.BOARD_R + M.CLEAR))
    for x0, y0, x1, y1 in pocket_rects():
        b = b.cut(rbox(x0, y0, x1, y1, M.POCKET_LO, M.SPLIT_Z + 1, 0.5))
    u = M.USB_CUT
    ln = M.MARGIN + 3.0
    tunnel = (cq.Workplane("XY").box(u["w"], ln, u["h"]).edges("|Y").fillet(u["r"])
              .translate((M.USB_X, M.BH - 1.0 + ln / 2, M.USB_Z)))
    b = b.cut(tunnel)
    s = M.SCREW
    for x, y in M.SCREWS:
        b = b.cut(cyl(x, y, s["clear_d"], Z_DEEP, M.SPLIT_Z + 1)).cut(cyl(x, y, s["head_d"], Z_DEEP, s["head_seat_z"]))
    bx, by = M.BOOT_PIN
    b = b.cut(cyl(bx, by, 2.2, Z_DEEP, M.FLOOR_Z + 1))
    return b


NAME_W = 180.0          # engraved "Vamora75" on the case bottom, mm


def name_engraving():
    """The name for the case bottom in world XY, centred, rotated 180 deg so it reads from underneath."""
    g = affinity.rotate(V.name_text(NAME_W), 180, origin=(0, 0)).simplify(0.03)
    depth_y = (M.BH + 2 * M.MARGIN) / math.cos(A)
    return affinity.translate(g, M.CASE_W / 2, depth_y / 2)


def bottom_seam():
    """World X of the bottom-case print seam: the nominal seam, moved (within printer-bed and
    screw/dowel limits) into the nearest gap between two letters of the engraved name."""
    nominal = M.SPLIT_X_BOTTOM + M.MARGIN
    screw_x = M.SCREW_MID[1] + M.MARGIN
    hi = min(screw_x - M.SCREW["head_d"] / 2 - M.DOWEL["depth"] - 1.0, 250.0)   # dowel clear of the screw; L piece <= 250
    lo = nominal - 18.0
    polys = V.polygons(name_engraving())
    best = None
    for i in range(int((hi - lo) / 0.25) + 1):
        x = lo + i * 0.25
        clear = min(p.bounds[0] - x if p.bounds[0] > x else x - p.bounds[2] if p.bounds[2] < x else -1.0 for p in polys)
        if clear >= 1.0 and (best is None or abs(x - nominal) < abs(best - nominal)):
            best = x
    seam = best if best is not None else nominal
    REPORT["bottom_seam_world_x"] = round(seam, 2)
    return seam


def finish_bottom(bw):
    """World-frame: trim on the desk plane, chamfer, feet, engraved logo and BOOT label."""
    bw = bw.intersect(rbox(-50, -50, M.CASE_W + 50, 400, 0.0, 200))
    try:
        bw = bw.faces("<Z").edges().chamfer(0.6)
    except Exception as e:          # noqa: BLE001
        log("bottom chamfer skipped:", e)
    depth_y = (M.BH + 2 * M.MARGIN) / math.cos(A)
    f = M.FEET
    feet = [(f["inset"], f["inset"]), (M.CASE_W - f["inset"], f["inset"]),
            (f["inset"], depth_y - f["inset"]), (M.CASE_W - f["inset"], depth_y - f["inset"])]
    for x, y in feet:
        bw = bw.cut(cyl(x, y, f["d"], -1, f["depth"]))
    logo = name_engraving()
    bw = bw.cut(ext(logo, -1.0, 0.6))
    ex, ey = axis_exit(*M.BOOT_PIN)
    label, lw = V.shaped_text("BOOT", 4.0, V.SEGOE_BOLD)
    label = affinity.rotate(V.centre(label), 180, origin=(0, 0)).simplify(0.03)
    bw = bw.cut(ext(affinity.translate(label, ex, ey - 6.0), -1.0, 0.6))
    x0, y0, x1, y1 = logo.bounds
    REPORT["bottom_name"] = dict(text=V.NAME, width_mm=NAME_W, bounds_world_xy=[round(v, 1) for v in (x0, y0, x1, y1)],
                                 engrave_depth_mm=0.6)
    REPORT["feet_world_xy"] = [[round(v, 1) for v in p] for p in feet]
    REPORT["boot_pinhole_exit_world_xy"] = [round(ex, 1), round(ey, 1)]
    return bw


# ------------------------------------------------------------------ top case
def top_case():
    t = rbox(-M.MARGIN, -M.MARGIN, M.BW + M.MARGIN, M.BH + M.MARGIN, M.SPLIT_Z, M.CASE_TOP, M.CASE_R)
    x0, y0, x1, y1 = M.KEYFIELD
    c = M.OPENING_CLEAR
    t = t.cut(rbox(x0 - c, y0 - c, x1 + c, y1 + c, M.SPLIT_Z - 1, M.CASE_TOP + 1, 1.5))
    try:
        t = t.faces(">Z").edges().chamfer(0.8)
    except Exception as e:          # noqa: BLE001
        log("top chamfer skipped:", e)
    t = t.cut(rbox(-M.CLEAR, -M.CLEAR, M.BW + M.CLEAR, M.BH + M.CLEAR, M.SPLIT_Z - 1, M.LIP_Z, M.BOARD_R + M.CLEAR))
    for px0, py0, px1, py1 in pocket_rects():
        t = t.cut(rbox(px0, py0, px1, py1, M.SPLIT_Z - 1, M.POCKET_HI, 0.5))
    s = M.SCREW
    for x, y in M.SCREWS:
        t = t.cut(cyl(x, y, s["insert_d"], M.SPLIT_Z - 1, M.SPLIT_Z + s["insert_depth"]))
    return t


# ------------------------------------------------------------------ soft parts
def gaskets():
    out = []
    for side, pos in M.TABS:
        x0, y0, x1, y1 = M.gasket_rect(side, pos).bounds
        out.append(rbox(x0, y0, x1, y1, M.POCKET_LO, M.PLATE_BOT))           # lower, installed height
        out.append(rbox(x0, y0, x1, y1, M.PLATE_TOP, M.POCKET_HI))           # upper
    return out


def case_foam_poly():
    g = M.cavity_outline().buffer(-0.75)
    # clearance for the USB-C receptacle (the only bottom part taller than the foam gap) and the BOOT pin-hole
    jx, jy = M.USB_X, M.BH
    g = g.difference(box(jx - 8.5, jy - 10.0, jx + 8.5, jy + 5))
    g = g.difference(Point(M.BOOT_PIN).buffer(3.0))
    return g


def plate_foam_poly():
    g = box(0.5, 0.5, M.BW - 0.5, M.BH - 0.5)
    cuts = []
    for k, cut in M.key_cutouts():
        for q in V.polygons(cut):
            x0, y0, x1, y1 = q.bounds          # square cut-outs: die/laser friendly, 0.25 mm clearance
            cuts.append(box(x0 - 0.25, y0 - 0.25, x1 + 0.25, y1 + 0.25))
    return g.difference(unary_union(cuts))


def write_dxf(polys, path, layer="CUT"):
    import ezdxf
    doc = ezdxf.new("R2010")
    doc.units = 4
    msp = doc.modelspace()
    for g in polys:
        for p in V.polygons(g):
            msp.add_lwpolyline(list(p.exterior.coords)[:-1], close=True, dxfattribs={"layer": layer})
            for r in p.interiors:
                msp.add_lwpolyline(list(r.coords)[:-1], close=True, dxfattribs={"layer": layer})
    assert not doc.audit().has_errors
    doc.saveas(path)


# ------------------------------------------------------------------ switches, keycaps
SCOTTO_CAD = Path(__import__("os").environ.get("VAMORA_SCOTTO", r"A:\ScottoKicad")) / "3dmodels" / "ScottoKeebs_CAD.3dshapes"


def switch_shape():
    """Joe Scotto's MX switch model (ScottoKicad, copied to PCB/3dmodels): z = 0 on the PCB top."""
    return cq.importers.importStep(str(ROOT / "PCB" / "3dmodels" / "MX_PCB.step")).val()


def switch_envelope():
    """MX switch envelope (housing below/above the plate, stem) for interference checks."""
    base = cq.Workplane("XY").rect(14.0, 14.0).extrude(M.PLATE_TOP).edges("|Z").fillet(0.6)
    top = (cq.Workplane("XY").workplane(offset=M.PLATE_TOP).rect(15.6, 15.6)
           .workplane(offset=6.6).rect(11.0, 11.0).loft())
    stem = cq.Workplane("XY").workplane(offset=M.PLATE_TOP + 6.6).rect(4.1, 4.1).extrude(3.8)
    return base.union(top).union(stem).val()


_CAPS = {}


def keycap(k):
    """Joe Scotto's MX keycap model for the key width (ScottoKicad CAD library), flipped like his
    CAD footprints, with the skirt 6.9 mm above the plate (resting on the stem)."""
    size = L.fp_size_name(k["w"])
    if size not in _CAPS:
        f = SCOTTO_CAD / f"MX_{size}_CAD.step"
        cap = cq.importers.importStep(str(f)).val().rotate(cq.Vector(0, 0, 0), cq.Vector(0, 1, 0), 180)
        z0 = cap.BoundingBox().zmin
        _CAPS[size] = cap.translate(cq.Vector(0, 0, M.PLATE_TOP + 6.9 - z0))
    x, y = M.b2c(k["bx"], k["by"])
    return _CAPS[size].moved(cq.Location(cq.Vector(x, y, 0)))


# ------------------------------------------------------------------ splitting for printers
def split(shape_w, x_world, pins):
    """Cut a world-frame part at X = x_world; dowel holes (along X) at the given world (y, z)."""
    left = shape_w.intersect(rbox(-100, -100, x_world, 500, -100, 300))
    right = shape_w.intersect(rbox(x_world, -100, 600, 500, -100, 300))
    d, dep = M.DOWEL["d"], M.DOWEL["depth"]
    for y, z in pins:
        hole = (cq.Workplane("YZ").circle(d / 2).extrude(2 * dep).translate((x_world - dep, y, z)))
        left = left.cut(hole)
        right = right.cut(hole)
    return left, right


def export(wp, stem, folder, stl=True, tol=0.05):
    folder.mkdir(parents=True, exist_ok=True)
    cq.exporters.export(wp, str(folder / f"{stem}.step"))
    if stl:
        cq.exporters.export(wp, str(folder / f"{stem}.stl"), tolerance=tol, angularTolerance=0.15)


# ------------------------------------------------------------------ main
if __name__ == "__main__":
    case_dir, split_dir, soft_dir, build_dir = OUT / "Case", OUT / "Case" / "print_split", OUT / "Soft", OUT / "build"
    for d in (case_dir, split_dir, soft_dir, build_dir):
        d.mkdir(parents=True, exist_ok=True)

    log("bottom case (plate frame)")
    bottom_p = bottom_case()
    log("top case (plate frame)")
    top_p = top_case()
    plate_p = cq.importers.importStep(str(OUT / "Plate" / "Vamora75_plate_FR4.step"))
    log("PCBA", PCBA_STEP.name)
    pcba_raw = cq.importers.importStep(str(PCBA_STEP))          # KiCad frame: board bottom at z = 0
    pcba_p = pcba_raw.translate((0, 0, -M.PCB_T))                # plate frame (checks, meshes)
    gk = gaskets()

    # ---------------- checks in the plate frame
    log("interference checks")
    sols = pcba_p.val().Solids()
    board_body = max(sols, key=lambda s: s.Volume())
    bb = pcba_p.val().BoundingBox()
    REPORT["pcba_bbox_plate_frame"] = [round(v, 3) for v in (bb.xmin, bb.ymin, bb.zmin, bb.xmax, bb.ymax, bb.zmax)]
    REPORT["bottom_parts_to_floor_mm"] = round(bb.zmin - M.FLOOR_Z, 2)
    REPORT["pcba_to_wall_mm"] = round(min(bb.xmin + M.CLEAR, M.BW + M.CLEAR - bb.xmax,
                                          bb.ymin + M.CLEAR, M.BH + M.CLEAR - bb.ymax), 3)
    j1 = comp([s for s in sols if s.BoundingBox().xmin > 285 and s.BoundingBox().xmax < 308
               and s.BoundingBox().ymax > M.BH - 8.0])
    REPORT["overlap_mm3"] = {
        "bottom_case x board": vol(bottom_p, comp([board_body])),
        "top_case x board": vol(top_p, comp([board_body])),
        "bottom_case x J1 (USB-C)": vol(bottom_p, j1),
        "bottom_case x plate": vol(bottom_p, plate_p),
        "top_case x plate": vol(top_p, plate_p),
        "top_case x bottom_case": vol(top_p, bottom_p),
    }
    sw = switch_shape()
    keys = L.keys()
    sw_all = comp([sw.moved(cq.Location(cq.Vector(*M.b2c(k["bx"], k["by"]), 0))) for k in keys])
    caps = [keycap(k) for k in keys]
    caps_all = comp(caps)
    # interference uses envelopes: the detailed Scotto models make booleans very slow, and the
    # envelopes (MX housing outline, keycap bounding boxes) enclose them
    sw_env = switch_envelope()
    sw_env_all = comp([sw_env.moved(cq.Location(cq.Vector(*M.b2c(k["bx"], k["by"]), 0))) for k in keys])
    REPORT["overlap_mm3"]["top_case x switches"] = vol(top_p, sw_env_all)
    REPORT["overlap_mm3"]["top_case x keycaps (rest)"] = vol(top_p, caps_all)
    caps_down = comp([c.translate(cq.Vector(0, 0, -4.0)) for c in caps])
    REPORT["overlap_mm3"]["top_case x keycaps (bottomed out, 4 mm)"] = vol(top_p, caps_down)
    g_all = comp(gk)
    REPORT["overlap_mm3"]["gaskets x cases"] = vol(g_all, bottom_p) + vol(g_all, top_p)
    REPORT["overlap_mm3"]["gaskets x plate"] = vol(g_all, plate_p)
    # USB-C plug overmould through the tunnel (inserted plug: shell inside J1, overmould from the PCB edge out)
    u = M.USB_PLUG
    plug = (cq.Workplane("XY").box(u["w"], 25.0, u["h"]).edges("|Y").fillet(u["r"])
            .translate((M.USB_X, M.BH + 0.3 + 12.5, M.USB_Z)))
    REPORT["overlap_mm3"]["bottom_case x USB-C plug overmould"] = vol(bottom_p, plug)
    REPORT["usb_tunnel"] = dict(cut=M.USB_CUT, plug=u, centre_z_plate_frame=round(M.USB_Z, 2),
                                side_clearance_mm=round((M.USB_CUT["w"] - u["w"]) / 2, 3),
                                vertical_clearance_mm=round((M.USB_CUT["h"] - u["h"]) / 2, 3))
    log("overlaps", REPORT["overlap_mm3"])

    # ---------------- world frame
    log("world frame + bottom finishing")
    bottom_w = finish_bottom(world(bottom_p))
    top_w = world(top_p)
    plate_w = world_moved(plate_p)
    pcba_w = world_moved(pcba_p)
    gk_w = [world_moved(g) for g in gk]
    sw_w = world_moved(sw_all)
    caps_w = world_moved(caps_all)
    bbw = bottom_w.val().BoundingBox()
    tbw = top_w.val().BoundingBox()
    front_h = wpt(0, -M.MARGIN, M.CASE_TOP)[2]
    rear_h = wpt(0, M.BH + M.MARGIN, M.CASE_TOP)[2]
    REPORT["case"] = dict(
        mount="tab-gasket sandwich (8 plate tabs, 16 gaskets)",
        typing_angle_deg=M.TYPING_ANGLE,
        footprint_mm=[round(bbw.xlen, 2), round(max(bbw.ymax, tbw.ymax) - min(bbw.ymin, tbw.ymin), 2)],
        front_height_mm=round(front_h, 2), rear_height_mm=round(rear_h, 2),
        plate_top_above_desk_front_row_mm=round(wpt(0, M.b2c(0, L.MARGIN + 5.5 * L.U)[1], M.PLATE_TOP)[2], 2),
        z_stack_plate_frame=dict(floor=M.FLOOR_Z, pcb=[-M.PCB_T, 0], plate=[M.PLATE_BOT, M.PLATE_TOP],
                                 split=M.SPLIT_Z, gasket_seats=[M.POCKET_LO, M.POCKET_HI], lip=M.LIP_Z,
                                 case_top=M.CASE_TOP),
        gasket=dict(size_mm=[M.GASKET_W, M.GASKET_D, M.GASKET_T], installed_mm=M.GASKET_SET,
                    compression_pct=round(100 * (1 - M.GASKET_SET / M.GASKET_T), 1), count=2 * len(M.TABS)),
        screws=dict(count=len(M.SCREWS), spec=M.SCREW["name"], insert=M.SCREW["insert"]),
        feet=M.FEET["bumper"],
    )
    for name, part in (("bottom", bottom_w), ("top", top_w)):
        assert part.val().isValid(), name
        REPORT[f"case_{name}"] = dict(valid=True, solids=len(part.solids().vals()), volume_cm3=round(part.val().Volume() / 1000, 1))
    log("export case")
    export(top_w, "Vamora75_case_top", case_dir)
    export(bottom_w, "Vamora75_case_bottom", case_dir)

    log("print split")
    xt, xb = M.SPLIT_X_TOP + M.MARGIN, bottom_seam()
    pins_top = [wpt(0, -M.SCREW_INSET, (M.LIP_Z + M.CASE_TOP) / 2)[1:], wpt(0, M.BH + M.SCREW_INSET, (M.LIP_Z + M.CASE_TOP) / 2)[1:]]
    zb = (M.FLOOR_Z + M.SPLIT_Z) / 2
    pins_bot = [wpt(0, -M.SCREW_INSET, zb)[1:], wpt(0, M.BH + M.SCREW_INSET, zb)[1:],
                wpt(0, 0.75 * M.BH, M.FLOOR_Z - 7.0)[1:]]
    tl, tr = split(top_w, xt, pins_top)
    bl, br = split(bottom_w, xb, pins_bot)
    sizes = {}
    for stem, part in (("Vamora75_case_top_L", tl), ("Vamora75_case_top_R", tr),
                       ("Vamora75_case_bottom_L", bl), ("Vamora75_case_bottom_R", br)):
        assert part.val().isValid(), stem
        b = part.val().BoundingBox()
        sizes[stem] = [round(b.xlen, 1), round(b.ylen, 1), round(b.zlen, 1)]
        export(part, stem, split_dir)
    REPORT["print_split"] = dict(seams_world_x=[round(xt, 2), round(xb, 2)], piece_sizes_mm=sizes,
                                 dowels=M.DOWEL["pin"], fits_bed_mm=[250, 210])

    log("soft parts (DXF)")
    gpolys = []
    for i in range(2 * len(M.TABS)):
        gpolys.append(box((i % 4) * (M.GASKET_W + 4), (i // 4) * (M.GASKET_D + 4),
                          (i % 4) * (M.GASKET_W + 4) + M.GASKET_W, (i // 4) * (M.GASKET_D + 4) + M.GASKET_D))
    write_dxf(gpolys, soft_dir / "Vamora75_gaskets_16x_20x4.5x2mm.dxf")
    cf, pf = case_foam_poly(), plate_foam_poly()
    write_dxf([cf], soft_dir / "Vamora75_case_foam_3mm.dxf")
    write_dxf([pf], soft_dir / "Vamora75_plate_foam_3.5mm.dxf")
    cf_p = ext(cf, M.FLOOR_Z, M.FLOOR_Z + 3.0)
    foam_case_w = world_moved(cf_p)
    pf_body = rbox(0.5, 0.5, M.BW - 0.5, M.BH - 0.5, 0.0, M.PLATE_BOT)
    pf_cut = comp(M.cutter_solids(cq, grow=0.25, rounded=False, t=M.PLATE_BOT + 2))
    pf_p = pf_body.cut(pf_cut)
    foam_plate_w = world_moved(pf_p)
    REPORT["soft_parts"] = dict(gaskets="16 x 20 x 4.5 mm, 2.0 mm Poron 4701-50 or 40A silicone",
                                case_foam="3 mm PE/Poron, USB-C and BOOT cut-outs",
                                plate_foam="3.5 mm Poron/PE between PCB and plate, 14.5 mm switch cut-outs")

    log("assembly STEP")
    pal = V.PALETTE
    rgb = lambda h: (int(h[1:3], 16) / 255, int(h[3:5], 16) / 255, int(h[5:7], 16) / 255)
    WL = world_loc()          # plate-frame parts are placed by an assembly location (keeps instancing)
    write_step_assembly([
        ("case_bottom", bottom_w, rgb(pal["graphite"])), ("case_top", top_w, rgb(pal["graphite"])),
        ("gaskets", comp(gk), (0.55, 0.55, 0.58), WL), ("plate_FR4", plate_p, (0.08, 0.09, 0.10), WL),
        ("plate_foam", pf_p, (0.85, 0.85, 0.80), WL), ("PCBA", pcba_raw, (0.10, 0.30, 0.20), WL * cq.Location(cq.Vector(0, 0, -M.PCB_T))),
        ("case_foam", cf_p, (0.25, 0.25, 0.27), WL), ("switches_MX", sw_all, (0.12, 0.12, 0.14), WL),
        ("keycaps", caps_all, rgb(pal["paper"]), WL)], OUT / "Vamora75_assembly.step")

    log("render meshes")
    # renders use light meshes: switch envelopes (the detailed Scotto switch is in the STEP), coarse PCBA
    for name, part, tol in (("case_bottom", bottom_w, 0.08), ("case_top", top_w, 0.08), ("plate", plate_w, 0.08),
                            ("pcba", pcba_w, 0.3), ("switches", world_moved(sw_env_all), 0.1),
                            ("foam_case", foam_case_w, 0.1), ("foam_plate", foam_plate_w, 0.1)):
        cq.exporters.export(part, str(build_dir / f"{name}.stl"), tolerance=tol, angularTolerance=0.5 if tol > 0.1 else 0.2)
    cq.exporters.export(comp(gk_w[0::2]), str(build_dir / "gaskets_lower.stl"))
    cq.exporters.export(comp(gk_w[1::2]), str(build_dir / "gaskets_upper.stl"))
    # gold-filled logo (render only): a thin sheet on the floor of the 0.6 mm engraving
    inlay = name_engraving()
    cq.exporters.export(ext(inlay.buffer(-0.05), 0.45, 0.58), str(build_dir / "logo_inlay.stl"))
    # keycaps grouped by colour for the renders
    groups = {"esc": [], "enter": [], "mods": [], "alphas": []}
    mods = {"Tab", "Caps", "LShift", "RShift", "LCtrl", "Win", "LAlt", "RAlt", "Fn", "RCtrl", "Backspace", "\\",
            "Del", "Home", "PgUp", "PgDn", "End", "Up", "Down", "Left", "Right"} | {f"F{i}" for i in range(1, 13)}
    for k, c in zip(keys, caps):
        grp = "esc" if k["label"] == "Esc" else "enter" if k["label"] == "Enter" else "mods" if k["label"] in mods else "alphas"
        groups[grp].append(c)
    for grp, items in groups.items():
        cq.exporters.export(world_moved(comp(items)), str(build_dir / f"keycaps_{grp}.stl"),
                            tolerance=0.2, angularTolerance=0.4)
    (build_dir / "board_solids.json").write_text(json.dumps(
        {"board_body_volume": board_body.Volume()}), encoding="utf-8")

    bad = {k: v for k, v in REPORT["overlap_mm3"].items() if abs(v) > 0.01}
    REPORT["result"] = "PASS" if not bad else f"CHECK {bad}"
    (ROOT / "validation").mkdir(exist_ok=True)
    (ROOT / "validation" / "mechanical.json").write_text(json.dumps(REPORT, indent=2), encoding="utf-8")
    log("done", REPORT["result"])
    print(json.dumps(REPORT["case"], indent=2))
