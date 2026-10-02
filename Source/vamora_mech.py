"""Vamora75 rev 1.1 mechanical parameters and 2D plate geometry (single source of truth).

CAD frame used by every mechanical script (millimetres, right-handed, Z up):
    X = PCB board-local x            (0 at the PCB's left edge)
    Y = BOARD_H - board-local y      (0 at the PCB's FRONT edge, +Y toward the rear)
    Z = 0 at the PCB TOP surface, measured perpendicular to the plate ("plate frame").
The finished case tilts this whole frame by TYPING_ANGLE about the front-bottom edge.

Mount: tab-gasket sandwich. The FR4 plate carries eight tabs; each tab is clamped
between a lower gasket (bottom case) and an upper gasket (top case). PCB and plate
float on the gaskets as one unit (held together by the switches); nothing is screwed
to the PCB.
"""
from __future__ import annotations

import math

from shapely import affinity
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

import vamora_layout as L

BW, BH = L.BOARD_W, L.BOARD_H          # 334.6125 x 129.825 (PCB = plate outline)
BOARD_R = 1.0                          # PCB / plate corner radius

# ------------------------------------------------------------------ Z stack (plate frame)
PCB_T = 1.6
PLATE_T = 1.5                          # MX spec; 1.6 mm FR4 also fits (see FABRICATION.md)
PLATE_TOP = 5.0                        # MX: plate top surface 5.0 mm above the PCB top
PLATE_BOT = PLATE_TOP - PLATE_T        # 3.5
GASKET_T = 2.0                         # free thickness (Poron / silicone 40A)
GASKET_SET = 1.6                       # installed thickness -> 20 % compression
SPLIT_Z = PLATE_BOT + PLATE_T / 2      # top / bottom case parting plane (mid-plate)
POCKET_LO = PLATE_BOT - GASKET_SET     # 1.9  lower gasket seat (bottom case)
POCKET_HI = PLATE_TOP + GASKET_SET     # 6.6  upper gasket seat (top case)
LIP_Z = PLATE_TOP + 1.0                # 6.0  underside of the top case lip over the plate
CASE_TOP = PLATE_TOP + 6.0             # 11.0 hides the switch top housings (6.6 above plate)
BOTTOM_PARTS = 3.26                    # tallest bottom-side part: USB-C receptacle (HRO TYPE-C-31-M-12)
SOCKET_H = 1.85                        # Kailh socket height below the PCB
FLOOR_Z = -PCB_T - 5.5                 # -7.1 case floor (room for 3 mm case foam under the sockets)
FLOOR_T = 3.0
TYPING_ANGLE = 6.0                     # degrees

# ------------------------------------------------------------------ XY envelope
CLEAR = 1.0                            # PCB/plate edge to case wall
MARGIN = 12.0                          # case outer edge beyond the PCB outline
CASE_R = 6.0
CASE_W, CASE_D = BW + 2 * MARGIN, BH + 2 * MARGIN          # 358.6 x 153.8
KEYFIELD = (L.MARGIN, L.MARGIN, BW - L.MARGIN, BH - L.MARGIN)   # key field (19.05 grid) in CAD XY
OPENING_CLEAR = 0.5                    # top-case opening beyond the key field (keycaps are 18 mm on 19.05)

# ------------------------------------------------------------------ gasket tabs
TAB_W, TAB_D = 20.0, 5.5               # along the edge / beyond the plate edge
TAB_POCKET_CLEAR = 0.5
TAB_X = (58.0, BW / 2, BW - 58.0)      # front and rear tabs (outer ones clear the USB-C tunnel)
TABS = ([("front", x) for x in TAB_X] + [("rear", x) for x in TAB_X] +
        [("left", BH / 2), ("right", BH / 2)])
GASKET_W, GASKET_D = TAB_W, TAB_D - CLEAR       # 20 x 4.5: the part of the tab over the pocket seat

# ------------------------------------------------------------------ fasteners / feet / USB
SCREW_INSET = 6.5                      # screw axis from the PCB outline (mid-wall)
SCREW_MID = (BW / 2 - 64.7, BW / 2 + 64.7)     # front/rear screws between the tabs, clear of the print seams
SCREWS = [(-SCREW_INSET, -SCREW_INSET), (BW + SCREW_INSET, -SCREW_INSET),
          (-SCREW_INSET, BH + SCREW_INSET), (BW + SCREW_INSET, BH + SCREW_INSET),
          (SCREW_MID[0], -SCREW_INSET), (SCREW_MID[1], -SCREW_INSET),
          (SCREW_MID[0], BH + SCREW_INSET), (SCREW_MID[1], BH + SCREW_INSET)]
# Optional split for 250 x 210 mm printer beds (staggered seams; 3 mm dowels across each seam)
SPLIT_X_TOP = BW / 2 - 30.0            # CAD X of the top-case seam
SPLIT_X_BOTTOM = 220.0                 # CAD X of the bottom-case seam (right of the engraved logo)
DOWEL = dict(d=3.1, depth=6.0, pin="3 x 12 mm steel dowel (or printed pin)")
SCREW = dict(name="M3 x 8 ISO 4762 socket head", clear_d=3.4, head_d=6.5, head_seat_z=SPLIT_Z - 5.0,
             insert="M3 x 4 x 4.0 mm heat-set insert", insert_d=4.0, insert_depth=5.0)
FEET = dict(d=10.5, depth=1.0, inset=22.0, bumper="10 x 3 mm silicone bumper")
USB_X = 296.5                          # J1 centre (PCB rear edge, bottom side)
USB_Z = -PCB_T - 0.08 - BOTTOM_PARTS / 2      # receptacle centre line (0.08 mm stand-off, from the PCBA STEP)
USB_CUT = dict(w=14.0, h=8.0, r=3.5)   # rear-wall tunnel: USB-IF overmould max 12.35 x 6.5 mm passes with margin
USB_PLUG = dict(w=12.35, h=6.5, r=3.0, shell=(8.25, 2.4, 6.65))
BOOT_PIN = (307.3, BH - 11.6)          # pin-hole under the BOOT button (SW90), CAD XY


def b2c(x, y):
    """Board-local (x, y-down) -> CAD (X, Y-rear)."""
    return x, BH - y


# ------------------------------------------------------------------ 2D helpers
def rrect(x0, y0, x1, y1, r):
    if r <= 0:
        return box(x0, y0, x1, y1)
    return box(x0 + r, y0 + r, x1 - r, y1 - r).buffer(r, resolution=24)


def fillet(g, r_concave=0.0, r_convex=0.0):
    if r_concave > 0:
        g = g.buffer(r_concave, resolution=24).buffer(-r_concave, resolution=24)
    if r_convex > 0:
        g = g.buffer(-r_convex, resolution=24).buffer(r_convex, resolution=24)
    return g


def tab_rect(side, pos, extra=0.0, depth=TAB_D, inner=0.0):
    """Rectangle of a tab (CAD XY). `inner` extends it into the plate, `extra` grows it."""
    w2 = TAB_W / 2 + extra
    if side == "front":
        return box(pos - w2, -depth - extra, pos + w2, inner)
    if side == "rear":
        return box(pos - w2, BH - inner, pos + w2, BH + depth + extra)
    if side == "left":
        return box(-depth - extra, pos - w2, inner, pos + w2)
    return box(BW - inner, pos - w2, BW + depth + extra, pos + w2)


def gasket_rect(side, pos):
    """Gasket footprint: the part of the tab that sits over the case pocket seat."""
    return tab_rect(side, pos, depth=TAB_D, inner=0.0).intersection(
        unary_union([box(-1e3, -1e3, 1e4, -CLEAR), box(-1e3, BH + CLEAR, 1e4, 1e3),
                     box(-1e3, -1e3, -CLEAR, 1e3), box(BW + CLEAR, -1e3, 1e4, 1e3)]))


def plate_outline():
    body = rrect(0, 0, BW, BH, BOARD_R)
    tabs = unary_union([tab_rect(s, p, inner=1.0) for s, p in TABS])
    g = fillet(unary_union([body, tabs]), r_concave=1.0, r_convex=1.0)
    return g


# ------------------------------------------------------------------ switch / stabiliser cutouts
SW_CUT = 14.0          # MX plate cutout
SW_CUT_R = 0.5         # FR4 routing (1.0 mm end mill); MX housing corners are chamfered
STAB_W, STAB_TOP, STAB_BOT = 6.75, 6.0, 8.0   # ai03 "MX simple": x +-3.375, 6 mm to the rear, 8 mm to the front
STAB_R = 0.5


def key_cutouts():
    """List of (key, shapely polygon) switch+stabiliser openings in CAD XY."""
    out = []
    for k in L.keys():
        cx, cy = b2c(k["bx"], k["by"])
        g = rrect(cx - SW_CUT / 2, cy - SW_CUT / 2, cx + SW_CUT / 2, cy + SW_CUT / 2, SW_CUT_R)
        sp = L.STAB_SPACING.get(k["w"])
        if sp:
            for sx in (cx - sp, cx + sp):
                g = g.union(rrect(sx - STAB_W / 2, cy - STAB_BOT, sx + STAB_W / 2, cy + STAB_TOP, STAB_R))
        out.append((k, g))
    return out


def flex_cuts(length_extra=4.0, inset=1.6, width=1.2):
    """Relief slots behind each gasket tab (flex-cut plate variant)."""
    cuts = []
    half = TAB_W / 2 + length_extra
    for side, pos in TABS:
        if side == "front":
            ln = LineString([(pos - half, inset + width / 2), (pos + half, inset + width / 2)])
        elif side == "rear":
            ln = LineString([(pos - half, BH - inset - width / 2), (pos + half, BH - inset - width / 2)])
        elif side == "left":
            ln = LineString([(inset + width / 2, pos - half), (inset + width / 2, pos + half)])
        else:
            ln = LineString([(BW - inset - width / 2, pos - half), (BW - inset - width / 2, pos + half)])
        cuts.append(ln.buffer(width / 2, resolution=16))
    return cuts


def plate_polygon(flex=False):
    holes = [g for _, g in key_cutouts()] + (flex_cuts() if flex else [])
    g = plate_outline().difference(unary_union(holes))
    return g


def min_web(flex=True):
    """Smallest FR4 web between any two openings / opening and edge (manufacturability)."""
    holes = [g for _, g in key_cutouts()] + (flex_cuts() if flex else [])
    holes = [q for g in holes for q in (getattr(g, "geoms", None) or [g])]
    outline = plate_outline()
    best = (1e9, None)
    edge = outline.exterior
    for i, a in enumerate(holes):
        d = a.exterior.distance(edge)
        if d < best[0]:
            best = (d, ("edge", i))
        for j in range(i + 1, len(holes)):
            b = holes[j]
            if a.distance(b) < best[0] and not a.intersects(b):
                best = (a.distance(b), (i, j))
    return best


def case_outline():
    return rrect(-MARGIN, -MARGIN, BW + MARGIN, BH + MARGIN, CASE_R)


def cavity_outline():
    return rrect(-CLEAR, -CLEAR, BW + CLEAR, BH + CLEAR, BOARD_R + CLEAR)


def opening_outline():
    x0, y0, x1, y1 = KEYFIELD
    c = OPENING_CLEAR
    return rrect(x0 - c, y0 - c, x1 + c, y1 + c, 1.5)


def tab_pockets():
    return [tab_rect(s, p, extra=TAB_POCKET_CLEAR, inner=1.0) for s, p in TABS]


def tilt_matrix():
    """Rotation about X by TYPING_ANGLE (rear goes up) - for reporting heights."""
    a = math.radians(TYPING_ANGLE)
    return math.cos(a), math.sin(a)


# ------------------------------------------------------------------ CadQuery solids (true arcs, compact STEP)
def _cq_rbox(cq, cx, cy, w, h, t, r, z0=-1.0):
    b = cq.Workplane("XY").box(w, h, t, centered=(True, True, False)).translate((cx, cy, z0))
    return b.edges("|Z").fillet(r) if r > 0 else b


def cutter_solids(cq, flex=False, grow=0.0, rounded=True, t=None):
    """Switch / stabiliser (/ flex) cutters as solids. grow > 0 enlarges them (foam clearance)."""
    t = (t or PLATE_T) + 2.0
    out = []
    for k, _ in key_cutouts():
        cx, cy = b2c(k["bx"], k["by"])
        r = SW_CUT_R if rounded else 0.0
        out.append(_cq_rbox(cq, cx, cy, SW_CUT + 2 * grow, SW_CUT + 2 * grow, t, r))
        sp = L.STAB_SPACING.get(k["w"])
        if sp:
            for sx in (cx - sp, cx + sp):
                out.append(_cq_rbox(cq, sx, cy + (STAB_TOP - STAB_BOT) / 2, STAB_W + 2 * grow,
                                    STAB_TOP + STAB_BOT + 2 * grow, t, STAB_R if rounded else 0.0))
    if flex:
        for g in flex_cuts():
            x0, y0, x1, y1 = g.bounds
            w, h = x1 - x0, y1 - y0
            sl = (cq.Workplane("XY").center((x0 + x1) / 2, (y0 + y1) / 2)
                  .slot2D(max(w, h), min(w, h), 0 if w > h else 90).extrude(t).translate((0, 0, -1.0)))
            out.append(sl)
    return out


def plate_solid(cq, flex=False):
    body = cq.Workplane("XY").box(BW, BH, PLATE_T, centered=False)
    for side, pos in TABS:
        x0, y0, x1, y1 = tab_rect(side, pos, inner=1.0).bounds
        body = body.union(cq.Workplane("XY").box(x1 - x0, y1 - y0, PLATE_T, centered=False).translate((x0, y0, 0)))
    body = body.edges("|Z").fillet(BOARD_R)
    cut = cq.Workplane("XY").add(cq.Compound.makeCompound([c.val() for c in cutter_solids(cq, flex)]))
    return body.cut(cut).translate((0, 0, PLATE_BOT))
