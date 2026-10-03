"""Vamora75 case: two-piece tab-gasket case with a 6 degree typing angle.

    python Source/build_case.py <switch-free PCBA STEP> [<full PCBA STEP>]     (CAD venv)
    python Source/build_case.py --meshes-only      render meshes only, from the existing PCBA STEP

Everything is modelled in the plate frame of vamora_mech (Z = 0 on the PCB top), then
tilted about the front-bottom edge; the bottom case is trimmed flat on the desk plane.
Outputs (Mechanical/):
  Case/Vamora75_case_top|bottom.step/.stl     one-piece parts (CNC or >= 360 mm printers)
  Case/print_split/*_L|_R.step/.stl           staggered split for 250 x 210 mm beds
  Soft/*.dxf                                  gaskets, case foam, plate foam
  Vamora75_assembly.step                      case, gaskets, foams, plate, PCBA (KiCad colours, switches,
                                              stabilisers), keycaps
  Vamora75_PCB_plate.step / .glb              PCB + plate + every component (switches, stabilisers,
                                              sockets, SMD parts): the PCB/plate sandwich on its own
  build/*.npz                                 coloured world-frame meshes for the renders
and validation/mechanical.json (interference / clearance report).

The switch-free PCBA STEP (first argument) is used for the interference checks; the full one
(KiCad export with Joe Scotto's MX switch on every footprint) goes into the assemblies.
"""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import cadquery as cq
import numpy as np
from shapely import affinity
from shapely.geometry import Point, box
from shapely.ops import unary_union

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cad_mesh as C  # noqa: E402
import vamora_layout as L  # noqa: E402
import vamora_logo as V  # noqa: E402
import vamora_mech as M  # noqa: E402

ROOT = HERE.parent
OUT = ROOT / "Mechanical"
ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
MESHES_ONLY = "--meshes-only" in sys.argv    # only the render meshes (no checks, no exports): render tuning
PCBA_STEP = Path(ARGS[0]) if ARGS else ROOT / "Mechanical" / "Vamora75_PCBA.step"
PCBA_FULL = Path(ARGS[1]) if len(ARGS) > 1 else ROOT / "Mechanical" / "Vamora75_PCBA.step"
RGB = {k: tuple(int(v[i:i + 2], 16) / 255 for i in (1, 3, 5)) for k, v in V.PALETTE.items()}
GOLD = (0.85, 0.66, 0.30)                  # ENIG
PCB_COLOURS = {"Vamora75_pad": GOLD}       # KiCad exports the pads grey; the board is ENIG
MW = C.mat_rot_x(M.TYPING_ANGLE) @ C.mat_translate(M.MARGIN, M.MARGIN, -(M.FLOOR_Z - M.FLOOR_T))   # plate frame -> world
MK = MW @ C.mat_translate(0, 0, -M.PCB_T)  # KiCad PCBA frame (board bottom at z = 0) -> world
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
    try:
        t = t.faces(">Z").edges().chamfer(0.8)
    except Exception as e:          # noqa: BLE001
        log("top chamfer skipped:", e)
    # the opening follows the key clusters; the case bridges every gap between them
    opening = M.opening_outline()
    solid_top = M.case_outline().difference(opening)
    x0, y0, x1, y1 = M.KEYFIELD                                   # rev 1.1: one rectangle over the key field
    covered = box(x0 - 0.5, y0 - 0.5, x1 + 0.5, y1 + 0.5).difference(opening).area
    REPORT["top_case_opening"] = dict(follows="key clusters", clearance_to_key_cell_mm=M.OPENING_CLEAR,
                                      corner_r_mm=M.OPENING_R, gaps_covered_mm2=round(covered, 1))
    assert len(V.polygons(solid_top)) == 1, "a bridge of the top case is not connected to the rim"
    # cutter with true arcs (rectilinear clusters, vertical edges filleted) so the chamfer stays clean
    cutters = []
    for p in V.polygons(M.opening_cells()):
        c = (cq.Workplane("XY").polyline(list(p.exterior.coords)[:-1]).close()
             .extrude(M.CASE_TOP - M.SPLIT_Z + 2).translate((0, 0, M.SPLIT_Z - 1)))
        cutters.append(c.edges("|Z").fillet(M.OPENING_R))
    t = t.cut(comp(cutters))
    try:                            # small chamfer around the opening
        top = t.faces(">Z").val()
        outer = {e.hashCode() for e in top.outerWire().Edges()}
        inner = [e for e in top.Edges() if e.hashCode() not in outer]
        tc = t.newObject(inner).chamfer(0.5)
        if not tc.val().isValid():
            raise ValueError("invalid solid")
        t = tc
    except Exception as e:          # noqa: BLE001
        log("opening chamfer skipped:", e)
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
    """3.5 mm plate foam: square switch openings and stabiliser/wire windows (die/laser friendly)."""
    g = box(0.5, 0.5, M.BW - 0.5, M.BH - 0.5)
    return g.difference(unary_union(M.foam_cutouts()))


def write_dxf(polys, path, layer="CUT"):
    if MESHES_ONLY:
        return
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
def switch_envelope():
    """MX switch envelope (housing below/above the plate, stem) for interference checks."""
    base = cq.Workplane("XY").rect(14.0, 14.0).extrude(M.PLATE_TOP).edges("|Z").fillet(0.6)
    top = (cq.Workplane("XY").workplane(offset=M.PLATE_TOP).rect(15.6, 15.6)
           .workplane(offset=6.6).rect(11.0, 11.0).loft())
    stem = cq.Workplane("XY").workplane(offset=M.PLATE_TOP + 6.6).rect(4.1, 4.1).extrude(3.8)
    return base.union(top).union(stem).val()


# Sculpted keycaps (Cherry-like profile) for the assembly and the renders: per row a centre height
# and a top tilt (+ = the top faces the typist), a tapered body and a cylindrical dish.
KEYCAP_ROW = {0: (9.4, 7.0), 1: (9.4, 7.0), 2: (7.9, 3.0), 3: (7.6, 0.0), 4: (8.2, -6.0), 5: (8.2, -6.0)}
KEYCAP_Z0 = M.PLATE_TOP + 6.9              # skirt above the plate top, resting on the switch stem
ACCENT_KEYS = {"Esc", "Enter"}
MOD_KEYS = {"Tab", "Caps", "LShift", "RShift", "LCtrl", "Win", "LAlt", "RAlt", "Fn", "RCtrl", "Backspace", "\\",
            "Del", "Home", "PgUp", "PgDn", "End", "Up", "Down", "Left", "Right"} | {f"F{i}" for i in range(1, 13)}
_CAPS = {}


def _rr_wire(w, d, r, plane):
    f = cq.Face.makeFromWires(cq.Workplane(plane).rect(w, d).val())
    return f.fillet2D(r, f.Vertices()).outerWire()


def keycap_shape(w_u, row):
    """Keycap solid, skirt at z = 0, centred on the switch."""
    h, tilt = KEYCAP_ROW[row]
    bw, bd = w_u * L.U - 0.95, L.U - 0.95
    tw, td = bw - 5.7, bd - 4.9
    a = math.radians(tilt)
    n = cq.Vector(0, -math.sin(a), math.cos(a))
    yd = cq.Vector(0, math.cos(a), math.sin(a))
    c = cq.Vector(0, 0.5, h)
    body = cq.Solid.makeLoft([_rr_wire(bw, bd, 0.9, cq.Plane.XY()),
                              _rr_wire(tw, td, 2.0, cq.Plane(origin=c, xDir=(1, 0, 0), normal=n))], True)
    sag = 0.65 if w_u <= 2.25 else 0.3     # dish depth; the space bar is nearly flat
    r = (tw * tw / 4 + sag * sag) / (2 * sag)
    body = body.cut(cq.Solid.makeCylinder(r, 40, c + n * (r - sag) - yd * 20, yd))
    try:
        body = cq.Workplane().add(body).edges(cq.selectors.BoxSelector((-200, -30, h - 2.0), (200, 30, h + 5))).fillet(0.45).val()
    except Exception as e:          # noqa: BLE001
        log("keycap rim fillet skipped", w_u, row, e)
    return body


def keycap(k):
    key = (k["w"], k["row"])
    if key not in _CAPS:
        _CAPS[key] = keycap_shape(*key).translate(cq.Vector(0, 0, KEYCAP_Z0))
    x, y = M.b2c(k["bx"], k["by"])
    return _CAPS[key].moved(cq.Location(cq.Vector(x, y, 0)))


def keycap_group(k):
    return "accent" if k["label"] in ACCENT_KEYS else "mods" if k["label"] in MOD_KEYS else "alphas"


def plate_name_solid():
    """The ENIG name on the plate top (Plate/build/plate_plan.json, board coordinates) as a thin solid."""
    from shapely.geometry import Polygon
    plan = json.loads((ROOT / "Plate" / "build" / "plate_plan.json").read_text(encoding="utf-8"))
    g = unary_union([Polygon([M.b2c(x, y) for x, y in r["outer"]]) for r in plan["copper"]])
    return ext(g, M.PLATE_TOP, M.PLATE_TOP + 0.03)


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
    gk = gaskets()
    keys = L.keys()
    caps = [keycap(k) for k in keys]
    if not MESHES_ONLY:
        log("PCBA", PCBA_STEP.name)
        pcba_raw = cq.importers.importStep(str(PCBA_STEP))          # KiCad frame: board bottom at z = 0
        pcba_p = pcba_raw.translate((0, 0, -M.PCB_T))                # plate frame (checks)

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
        # top-side PCBA parts in the switch-free export are the four PCB-mount stabilisers
        stab_solids = [s for s in sols if s.BoundingBox().zmax > 1.0]
        stabs = comp(stab_solids)
        REPORT["stabilisers"] = dict(solids=len(stab_solids), plate_opening_mm=[M.STAB_W, M.STAB_TOP + M.STAB_BOT],
                                     foam_window_mm=[2 * M.FOAM_STAB_X, M.FOAM_STAB_FRONT + M.FOAM_STAB_REAR],
                                     pcb_holes="plated, copper reinforcement rings 4.6 / 6.0 mm")
        REPORT["overlap_mm3"]["plate x stabilisers"] = vol(plate_p, stabs)
        caps_all = comp(caps)
        # switches are checked as an envelope (the detailed Scotto model makes booleans very slow and the
        # envelope encloses it); keycaps are the real sculpted solids
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
    if not MESHES_ONLY:
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
    pf_p = ext(pf, 0.0, M.PLATE_BOT)
    REPORT["soft_parts"] = dict(gaskets="16 x 20 x 4.5 mm, 2.0 mm Poron 4701-50 or 40A silicone",
                                case_foam="3 mm PE/Poron, USB-C and BOOT cut-outs",
                                plate_foam="3.5 mm Poron/PE between PCB and plate, 14.5 mm switch cut-outs, stabiliser/wire windows")

    if not MESHES_ONLY:
        REPORT["overlap_mm3"]["plate_foam x stabilisers"] = vol(pf_p, stabs)

    groups = {"alphas": [], "mods": [], "accent": []}
    for k, c in zip(keys, caps):
        groups[keycap_group(k)].append(c)
    cap_rgb = {"alphas": RGB["bone"], "mods": RGB["slate"], "accent": RGB["brass"]}
    pname = plate_name_solid()
    gasket_rgb, foam_light, foam_dark = (0.55, 0.55, 0.58), (0.86, 0.85, 0.80), (0.22, 0.22, 0.24)
    if not MESHES_ONLY:
        log("assembly STEP")
        asm = C.Assembly("Vamora75")
        asm.add_shape("case_bottom", bottom_w, RGB["graphite"])
        asm.add_shape("case_top", top_w, RGB["graphite"])
        asm.add_shape("gaskets", comp(gk), gasket_rgb, MW)
        asm.add_shape("plate_FR4", plate_p, RGB["mask"], MW)
        asm.add_shape("plate_name_ENIG", pname, GOLD, MW)
        asm.add_shape("plate_foam", pf_p, foam_light, MW)
        asm.add_shape("case_foam", cf_p, foam_dark, MW)
        asm.add_step("PCBA", PCBA_FULL, MK, recolour=PCB_COLOURS)
        for grp, items in groups.items():
            asm.add_shape(f"keycaps_{grp}", comp(items), cap_rgb[grp], MW)
        asm.write_step(OUT / "Vamora75_assembly.step")

        log("PCB + plate STEP / GLB")
        stack = C.Assembly("Vamora75 PCB + plate")
        stack.add_step("PCBA", PCBA_FULL, recolour=PCB_COLOURS)          # KiCad frame: board bottom at z = 0
        MP = C.mat_translate(0, 0, M.PCB_T)                              # plate frame -> KiCad frame
        stack.add_shape("plate_FR4", plate_p, RGB["mask"], MP)
        stack.add_shape("plate_name_ENIG", pname, GOLD, MP)
        stack.write_step(OUT / "Vamora75_PCB_plate.step")
        glb = C.step_instances(PCBA_FULL, overrides=PCB_COLOURS, lin=0.1, ang=0.6)
        glb += [("plate_FR4", C.shape_buckets(plate_p, RGB["mask"]), [MP]),
                ("plate_name_ENIG", C.shape_buckets(pname, GOLD), [MP])]
        C.write_glb(glb, OUT / "Vamora75_PCB_plate.glb")

    log("render meshes")

    def save(name, buckets):
        C.save_buckets(buckets, build_dir / f"{name}.npz")
    save("case_bottom", C.shape_buckets(bottom_w, RGB["graphite"], lin=0.04, ang=0.2))
    save("case_top", C.shape_buckets(top_w, RGB["graphite"], lin=0.04, ang=0.2))
    inlay = name_engraving()          # gold-filled engraving (render only): a sheet on the engraving floor
    save("logo_inlay", C.shape_buckets(ext(inlay.buffer(-0.05), 0.45, 0.58), RGB["brass"]))
    save("plate", C.combine(C.shape_buckets(plate_p, RGB["mask"], MW), C.shape_buckets(pname, GOLD, MW)))
    save("foam_plate", C.shape_buckets(pf_p, foam_light, MW))
    save("foam_case", C.shape_buckets(cf_p, foam_dark, MW))
    save("gaskets_lower", C.shape_buckets(comp(gk[0::2]), gasket_rgb, MW))
    save("gaskets_upper", C.shape_buckets(comp(gk[1::2]), gasket_rgb, MW))
    save("pcba", C.step_buckets(PCBA_FULL, MK, overrides=PCB_COLOURS, lin=0.08, ang=0.5, skip=["SW_Cherry_MX_PCB"]))
    save("keycaps", C.combine(*[C.shape_buckets(comp(items), cap_rgb[g], MW, lin=0.02, ang=0.12)
                                for g, items in groups.items()]))
    # one switch (Joe Scotto's model, z = 0 on the PCB top) + where the 82 copies go
    save("switch", C.step_buckets(ROOT / "PCB" / "3dmodels" / "MX_PCB.step", lin=0.05, ang=0.4))
    np.save(build_dir / "switch_instances.npy",
            np.array([MW @ C.mat_translate(*M.b2c(k["bx"], k["by"]), 0) for k in keys]))
    if MESHES_ONLY:
        log("render meshes written")
        raise SystemExit(0)
    (build_dir / "board_solids.json").write_text(json.dumps(
        {"board_body_volume": board_body.Volume()}), encoding="utf-8")

    bad = {k: v for k, v in REPORT["overlap_mm3"].items() if abs(v) > 0.01}
    REPORT["result"] = "PASS" if not bad else f"CHECK {bad}"
    (ROOT / "validation").mkdir(exist_ok=True)
    (ROOT / "validation" / "mechanical.json").write_text(json.dumps(REPORT, indent=2), encoding="utf-8")
    log("done", REPORT["result"])
    print(json.dumps(REPORT["case"], indent=2))
