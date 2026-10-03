"""Route the Vamora75 PCB.

Deterministic, regular routing for the 82-key matrix (B.Cu rows, F.Cu columns),
plus the design-rule-aware grid router (router.py) for the RP2040 / USB area.
Writes PCB/build/routes.json consumed by kicad_build.py.
    python Source/route_board.py <stage PCB dir>
"""
from __future__ import annotations

import json
import math
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import vamora_layout as L  # noqa: E402
import pcb_plan as P  # noqa: E402
from router import Router  # noqa: E402

STAGE = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE.parent / "PCB"
W_SIG, W_ROW, W_COL, W_PWR = 0.2, 0.25, 0.25, 0.4
CLR = 0.2
VIA = dict(d=0.6, drill=0.3)

tracks, vias = [], []


def T(net, layer, pts, w):
    for a, b in zip(pts, pts[1:]):
        if math.dist(a, b) > 1e-6:
            tracks.append(dict(net=net, layer=layer, a=[round(a[0], 4), round(a[1], 4)], b=[round(b[0], 4), round(b[1], 4)], w=w))


def V(net, at, d=0.6, drill=0.3):
    vias.append(dict(net=net, at=[round(at[0], 4), round(at[1], 4)], d=d, drill=drill))


# ======================================================================= inputs
nets, comps = P.netlist(STAGE / "build" / "Vamora75.net.xml")
pl = P.placement()
pads, keepouts, courts = P.all_pads(pl, nets)
pad_of = defaultdict(list)
for p in pads:
    pad_of[(p["ref"], p["num"])].append(p)
holes = [p["geom"] for p in pads if p["kind"] == "np_thru_hole"]
hole_union = unary_union(holes)
keys = L.keys()
by_ref = {k["ref"]: k for k in keys}


def padc(ref, num):
    p = pad_of[(ref, num)][0]
    return (p["x"], p["y"])


# ======================================================================= key matrix (deterministic)
colvia = {}
for k in keys:
    ref, d = k["ref"], k["diode"]
    col_net = nets[(ref, "1")]
    key_net = nets[(ref, "2")]
    row_net = nets[(d, "1")]
    assert nets[(d, "2")] == key_net
    x, y = k["bx"], k["by"]
    p1 = padc(ref, "1")
    p2 = padc(ref, "2")
    a = padc(d, "2")
    kk = padc(d, "1")
    assert abs(a[1] - (y + P.DIODE_DY - 1.65)) < 1e-6 and abs(kk[1] - (y + P.DIODE_DY + 1.65)) < 1e-6
    cv = (x + P.COLVIA_DX, y + P.COLVIA_DY)
    colvia[ref] = cv
    T(col_net, "B.Cu", [p1, cv], W_COL)
    V(col_net, cv)
    T(key_net, "B.Cu", [p2, (a[0] - 0.5, p2[1]), (a[0], p2[1] + 0.5), a], W_ROW)
    T(row_net, "B.Cu", [kk, (kk[0], y + P.ROWLINE_DY)], W_ROW)

# row lines (B.Cu) at y + ROWLINE_DY of each key; row 0 hops to F.Cu between HOP_W and HOP_E.
# Keys that sit lower (the arrow cluster, 0.25u down) are reached with a 45-degree jog centred
# in the key-free gap between the two keycaps.
rows = defaultdict(list)
for k in keys:
    rows[k["row"]].append(k)
row_y = {}


def row_polyline(ks):
    ks = sorted(ks, key=lambda k: k["bx"])
    pts = [(ks[0]["bx"] + P.DIODE_DX, ks[0]["by"] + P.ROWLINE_DY)]
    for k0, k1 in zip(ks, ks[1:]):
        x1, y1 = k1["bx"] + P.DIODE_DX, k1["by"] + P.ROWLINE_DY
        y0 = pts[-1][1]
        if abs(y1 - y0) > 1e-6:
            gap_l = L.MARGIN + (k0["x"] + k0["w"]) * L.U
            gap_r = L.MARGIN + k1["x"] * L.U
            xj, h = (gap_l + gap_r) / 2, abs(y1 - y0) / 2
            assert gap_r - gap_l >= 2 * h - 1e-6, "gap too narrow for the row jog"
            pts += [(xj - h, y0), (xj + h, y1)]
        pts.append((x1, y1))
    return pts


for r, ks in rows.items():
    yy = min(ks, key=lambda k: k["bx"])["by"] + P.ROWLINE_DY
    row_y[r] = yy
    net = f"/ROW{r}"
    if r == 0:
        xs = sorted(k["bx"] + P.DIODE_DX for k in ks)
        west = [x for x in xs if x < P.HOP_W]
        east = [x for x in xs if x > P.HOP_E]
        T(net, "B.Cu", [(x, yy) for x in west] + [(P.HOP_W, yy)], W_ROW)
        V(net, (P.HOP_W, yy))
        T(net, "F.Cu", [(P.HOP_W, yy), (P.HOP_E, yy)], W_ROW)
        V(net, (P.HOP_E, yy))
        T(net, "B.Cu", [(P.HOP_E, yy)] + [(x, yy) for x in east], W_ROW)
    else:
        T(net, "B.Cu", row_polyline(ks), W_ROW)

# ======================================================================= F.Cu column paths
fcu_items = []   # (net, geometry) already on F.Cu, for clearance checks


def fcu_ok(net, line, w=W_COL):
    g = line.buffer(w / 2)
    if g.distance(hole_union) < 0.25 + 1e-6:
        return False
    for n, geo in fcu_items:
        if n != net and g.distance(geo) < CLR + 1e-6:
            return False
    return True


def add_fcu(net, pts, w=W_COL):
    T(net, "F.Cu", pts, w)
    fcu_items.append((net, LineString(pts).buffer(w / 2)))


for v in vias:   # vias occupy F.Cu too
    fcu_items.append((v["net"], Point(v["at"]).buffer(v["d"] / 2)))
for t in tracks:
    if t["layer"] == "F.Cu":
        fcu_items.append((t["net"], LineString([t["a"], t["b"]]).buffer(t["w"] / 2)))
for p in pads:   # net-less plated rings (stabiliser reinforcement) are copper on F.Cu as well
    if p["kind"] == "thru_hole" and not p["net"] and "F.Cu" in p["layers"]:
        fcu_items.append((None, p["geom"]))

BUS_Y0, BUS_PITCH = 21.0, 0.65
COL13_Y, COL14_Y = 84.0, 88.0
ARROW_JOG_Y = 105.2            # column 15 turns west towards the Right arrow below this y
ROW5_JOG = (103.0, 306.0)      # ROW5 feed: leaves the bundle at this y and drops at this x to the arrow row line
BUS_LO = BUS_Y0 + BUS_PITCH * 13       # jogs between row 0 and row 1 must stay below the bus


def col_segment(net, a, b, ymin=None, prefer_mid=True):
    """F.Cu path from via a down to via b (b below a), vertical/45-degree/horizontal."""
    (xa, ya), (xb, yb) = a, b
    dx = xb - xa
    lo = (ymin if ymin is not None else ya + 1.0)
    cands = []
    if abs(dx) < 1e-6:
        cands.append([a, b])
    else:
        # vertical - 45 - vertical
        span = abs(dx)
        ys = np.arange(lo, yb - span - 0.6, 0.25)
        mid = (ya + yb - span) / 2
        for y0 in sorted(ys, key=lambda v: abs(v - mid) if prefer_mid else v):
            cands.append([a, (xa, y0), (xb, y0 + span), b])
        # vertical - 45 - horizontal - 45 - vertical
        for y0 in np.arange(lo, yb - 2.0, 0.25):
            for d in (1.0, 1.5, 2.0, 3.0):
                if y0 + d > yb - 0.8:
                    continue
                s = math.copysign(d, dx)
                if abs(dx) <= 2 * d:
                    continue
                cands.append([a, (xa, y0), (xa + s, y0 + d), (xb - s, y0 + d), (xb, y0 + 2 * d), b])
    for c in cands:
        c = [p for i, p in enumerate(c) if i == 0 or math.dist(p, c[i - 1]) > 1e-6]
        if fcu_ok(net, LineString(c)):
            return c
    raise RuntimeError(f"no F.Cu path for {net} {a}->{b}")


cols = defaultdict(list)
for k in keys:
    cols[k["col"]].append(k)
bus_via = {}
for c in range(L.MATRIX_COLS):
    ks = sorted(cols[c], key=lambda k: k["row"])
    net = f"/COL{c}"
    pts_chain = []
    if c <= 12:
        top = ks[0]
        bx = colvia[top["ref"]][0]
        by = BUS_Y0 + BUS_PITCH * c
        bus_via[c] = (bx, by)
        if top["row"] != 0:            # column without an F-row key: drop from the bus
            add_fcu(net, [(bx, by), colvia[top["ref"]]])
    for k0, k1 in zip(ks, ks[1:]):
        a, b = colvia[k0["ref"]], colvia[k1["ref"]]
        if c == 15 and k0["row"] == 4 and k1["row"] == 5:      # FORCED_COL15: End -> Right (arrow 0.25u left/down)
            # jog west late, so the ROW5 feed (which jogs west earlier, see the bundle) stays on its west side
            seg = [a, (a[0], ARROW_JOG_Y), (b[0], ARROW_JOG_Y + (a[0] - b[0])), b]
            assert fcu_ok(net, LineString(seg)), "column 15 jog collides"
            add_fcu(net, seg)
            continue
        if c == 13 and k0["row"] == 3 and k1["row"] == 5:      # FORCED_COL13: Enter -> Left
            xd = b[0] - 0.9          # stay clear of Enter's right stabiliser hole
            seg = [a, (a[0], COL13_Y - 0.8), (a[0] + 0.8, COL13_Y), (xd - 0.8, COL13_Y), (xd, COL13_Y + 0.8),
                   (xd, b[1] - 0.9), b]
            assert fcu_ok(net, LineString(seg)), "column 13 forced jog collides"
            add_fcu(net, seg)
            continue
        ymin = None
        if k0["row"] == 0 and c <= 12:
            ymin = BUS_LO + 0.2          # keep the jog below the bus via
        seg = col_segment(net, a, b, ymin)
        add_fcu(net, seg)

# bus vias + bus lines (B.Cu) from the controller area west to every column
BUS_X_EAST = 283.6
for c, (bx, by) in bus_via.items():
    V(f"/COL{c}", (bx, by))
    fcu_items.append((f"/COL{c}", Point(bx, by).buffer(0.3)))
    T(f"/COL{c}", "B.Cu", [(BUS_X_EAST, by), (bx, by)], W_SIG)

# ======================================================================= bundle down the nav gap (F.Cu)
BUNDLE = {"/COL13": 309.45, "/COL14": 310.25, "/ROW1": 311.05, "/ROW2": 311.85, "/ROW3": 312.65,
          "/ROW4": 313.45, "/ROW5": 314.25}
BUNDLE_VIA_Y = {"/ROW5": 24.65, "/ROW4": 25.3, "/ROW3": 25.95, "/ROW2": 26.6, "/ROW1": 27.25, "/COL14": 27.9, "/COL13": 29.4}
for net, x in BUNDLE.items():
    y0 = BUNDLE_VIA_Y[net]
    V(net, (x, y0))
    if net == "/ROW5":
        # the arrows sit 0.25u lower: meet their row line between Left/Down diodes and the Right socket
        jy, jx = ROW5_JOG
        right = [k for k in rows[5] if k["label"] == "Right"][0]
        y1 = right["by"] + P.ROWLINE_DY
        seg = [(x, y0), (x, jy), (jx, jy + (x - jx)), (jx, y1)]
        assert fcu_ok(net, LineString(seg)), "ROW5 feed collides"
        add_fcu(net, seg)
        V(net, (jx, y1))
    elif net.startswith("/ROW"):
        r = int(net[4:])
        y1 = row_y[r]
        add_fcu(net, [(x, y0), (x, y1)])
        V(net, (x, y1))
    elif net == "/COL14":
        up = [k for k in cols[14] if k["row"] == 4][0]
        cv = colvia[up["ref"]]
        add_fcu(net, [(x, y0), (x, COL14_Y - 0.8), (x - 0.8, COL14_Y), (cv[0] + 0.8, COL14_Y), (cv[0], COL14_Y + 0.8), cv])
    elif net == "/COL13":
        # meets the Enter -> Left jog of column 13, which runs along y = COL13_Y
        left = [k for k in cols[13] if k["row"] == 5][0]
        cv = colvia[left["ref"]]
        add_fcu(net, [(x, y0), (x, COL13_Y - 0.8), (x - 0.8, COL13_Y), (cv[0] - 0.9 - 0.8, COL13_Y)])

# ======================================================================= controller area router
WIN = box(272.5, -0.6, 320.5, 46.5)
R = Router(272.5, -0.6, 320.5, 46.5, 0.05, board=box(0, 0, L.BOARD_W, L.BOARD_H))
for p in pads:
    if not p["geom"].intersects(WIN.buffer(2)):
        continue
    if p["kind"] == "np_thru_hole":
        R.add_hole(p["geom"])
        continue
    R.add_copper(p["geom"], p["layers"], p["net"])
    if p["drill"] and p["net"]:
        R.ilayer.append((p["x"], p["y"], p["net"]))
    if p["drill"]:
        R.add_hole(p["geom"] if p["shape"] == "circle" else Point(p["x"], p["y"]).buffer(min(p["drill"]) / 2), p["net"])
for k in keepouts:
    if k["geom"].intersects(WIN):
        R.add_keepout(k["geom"], k["layers"])
for t in tracks:
    g = LineString([t["a"], t["b"]])
    if g.intersects(WIN.buffer(1)):
        R.add_copper(g.buffer(t["w"] / 2), [t["layer"]], t["net"])
for v in vias:
    if Point(v["at"]).intersects(WIN.buffer(1)):
        R.add_copper(Point(v["at"]).buffer(v["d"] / 2), ["F.Cu", "B.Cu"], v["net"])
        R.add_hole(Point(v["at"]).buffer(v["drill"] / 2), v["net"])
        R.ilayer.append((v["at"][0], v["at"][1], v["net"]))
J1_SHELL = box(pl["J1"]["x"] - 4.6, -1.0, pl["J1"]["x"] + 4.6, 6.75)
R.add_keepout(J1_SHELL, ["B.Cu"])
# bus terminals: tiny copper at the east end of each bus line
for c, (bx, by) in bus_via.items():
    R.add_copper(Point(BUS_X_EAST, by).buffer(0.1), ["B.Cu"], f"/COL{c}")

U1C = courts["U1"].buffer(0.15)
FAN = {k: box(*v) for k, v in P.FANOUT_AREAS.items()}
QFN_ZONE = (unary_union([U1C, FAN["FANOUT_QSPI"], FAN["FANOUT_QFN"]]), 0.15)   # = KiCad custom rule areas
USB_ZONE = (FAN["FANOUT_USB"], 0.15)
Z = QFN_ZONE


def pg(ref, num, layer="B.Cu"):
    return [(layer, p["geom"]) for p in pad_of[(ref, num)]]


routed, failed = [], []


def route(net, src, dst, w=W_SIG, zone=None, **kw):
    t0 = time.time()
    r = R.route(net, src, dst, w=w, clr=CLR, clr_map=zone, **kw)
    ok = r is not None
    (routed if ok else failed).append(net)
    info = "" if ok else f"  {getattr(R, 'last_info', {})} src={[(l, getattr(g, 'bounds', None)) for l, g in src][:1] if isinstance(src, list) else src}"
    print(f"  {'ok ' if ok else 'FAIL'} {net:14s} {time.time() - t0:5.1f}s{info}", flush=True)
    return r


def direct(net, layer, pts, w):
    """pre-planned copper (also registered with the router as an obstacle)"""
    T(net, layer, pts, w)
    n0 = len(R.tracks)
    R.add_track(net, layer, pts, w)
    del R.tracks[n0:]


def dvia(net, at, d=0.45, drill=0.3):
    V(net, at, d, drill)
    n0 = len(R.vias)
    R.add_via(net, at, d, drill)
    del R.vias[n0:]


def region_pads(net):
    return [p for p in pads if p["net"] == net and WIN.contains(Point(p["x"], p["y"])) and p["kind"] != "np_thru_hole"]


def connect_all(net, w, seed=None, skip=()):
    """Tree-route every pad of `net` inside the window (nearest to the seed first)."""
    ps = [p for p in region_pads(net) if (p["ref"], p["num"]) not in skip]
    if not ps:
        return
    if seed is None:
        seed = ps[0]
    order = sorted(ps, key=lambda p: math.dist((p["x"], p["y"]), (seed["x"], seed["y"])))
    for p in order:
        if p is seed:
            continue
        lay = "B.Cu" if "B.Cu" in p["layers"] else sorted(p["layers"])[0]
        r = R.route(net, [(lay, p["geom"])], "net", w=w, clr=CLR, clr_map=Z)
        tag = f"{p['ref']}.{p['num']}"
        if r is None and R.last_info.get("goal", 1) == 0:
            continue          # nothing left to connect to: already part of the tree
        (routed if r is not None else failed).append(f"{net}:{tag}")
        print(f"  {'ok ' if r is not None else 'FAIL'} {net}:{tag} {'' if r is not None else R.last_info}", flush=True)


print("routing controller area ...")
# F.Cu ground window over the RP2040 exposed pad + a corridor west to the main pour: the EP is
# the chip's only GND connection and must never be enclosed by F.Cu power traces.
EP_WINDOW = unary_union([box(P.MX - 2.1, P.MY - 2.1, P.MX + 2.1, P.MY + 2.1),
                         box(282.5, P.MY - 1.4, P.MX, P.MY - 0.0)])
R.add_keepout(EP_WINDOW, ["F.Cu"], tracks=True, vias=True)
J = pl["J1"]["x"]
U = {n: padc("U1", str(n)) for n in range(1, 57)}
TIP = 3.875                 # QFN pad tip distance from the package centre
MXc, MYc = pl["U1"]["x"], pl["U1"]["y"]

# ---- USB-C D+/D- crossover: D- pads (B7, A7) joined by a narrow U on B.Cu; D+ (A6) hops
#      through a 0.45 mm via inside the U to F.Cu and comes back down at B6.
pB7, pA6, pA7, pB6 = (padc("J1", n) for n in ("B7", "A6", "A7", "B6"))
direct("/USB_D-", "B.Cu", [pB7, (pB7[0], 9.75), (pA7[0], 9.75), pA7], 0.15)
direct("/USB_D+", "B.Cu", [pA6, (pA6[0], 9.2)], 0.2)
dvia("/USB_D+", (pA6[0], 9.2))
direct("/USB_D+", "B.Cu", [pB6, (pB6[0], 9.2)], 0.2)
dvia("/USB_D+", (pB6[0], 9.2))
direct("/USB_D+", "F.Cu", [(pA6[0], 9.2), (pB6[0], 9.2)], 0.2)
# J1 GND pads tie straight to the rear shell legs (just behind the shell edge)
for gnd_pad, side in (("A1", -1), ("A12", +1)):
    gp = pad_of[("J1", gnd_pad)][0]
    leg = [p for p in pad_of[("J1", "SH")] if p["y"] > 5 and (p["x"] - J) * side > 0][0]
    direct("GND", "B.Cu", [(gp["x"], gp["y"] + 0.35), (leg["x"], gp["y"] + 0.35)], 0.3)
# ESD: GND via above pin 2 (between the incoming D lines); VBUS via below pin 5
u2_2, u2_5 = padc("U2", "2"), padc("U2", "5")
direct("GND", "B.Cu", [u2_2, (u2_2[0], 10.45)], 0.25)
dvia("GND", (u2_2[0], 10.45))
direct("VBUS", "B.Cu", [u2_5, (u2_5[0], 14.95)], 0.25)
dvia("VBUS", (u2_5[0], 14.95))
# USB lines continue straight through the ESD array: flow-through under the package (pin 1-6, 3-4)
direct("/USB_D-", "B.Cu", [padc("U2", "1"), padc("U2", "6")], 0.25)
direct("/USB_D+", "B.Cu", [padc("U2", "3"), padc("U2", "4")], 0.25)

# ---- RP2040 power escapes that must exist before the signal fan-outs
# DVDD: pin 45 (VREG_VOUT) <-> pin 50 joined just inside the north pad row (under the package)
direct("+1V1", "B.Cu", [U[45], (U[45][0], MYc - 2.55), (U[50][0], MYc - 2.55), U[50]], 0.2)
# TESTEN to the exposed pad
direct("GND", "B.Cu", [U[19], (U[19][0], MYc + 1.4)], 0.2)
# IOVDD 33 (west, between bus lines): stub + via; IOVDD 22 (south): via + C5
direct("+3V3", "B.Cu", [U[33], (MXc - TIP - 0.75, U[33][1])], 0.2)
dvia("+3V3", (MXc - TIP - 0.75, U[33][1]))
c5 = padc("C5", "1")
direct("+3V3", "B.Cu", [U[22], (U[22][0], MYc + TIP + 0.75), c5], 0.2)
dvia("+3V3", (U[22][0], MYc + TIP + 0.75))
# C3 / C4 share one GND via between their facing GND pads
g3, g4 = padc("C3", "2"), padc("C4", "2")
direct("GND", "B.Cu", [g3, g4], 0.3)
dvia("GND", ((g3[0] + g4[0]) / 2, g3[1]))
# flash GND (U4 pin 4, SE corner) gets its via before the QSPI loops wrap around it
f4 = padc("U4", "4")
direct("GND", "B.Cu", [f4, (f4[0] + 0.55, f4[1] + 0.55)], 0.2)
dvia("GND", (f4[0] + 0.55, f4[1] + 0.55))

# ---- deterministic east fan-out: ROW0 (riser on F.Cu to the hop), COL15, rows/cols to the bundle
pin_of_net = {}
for num in range(1, 57):
    n = nets.get(("U1", str(num)))
    if n and (n.startswith("/COL") or n.startswith("/ROW")):
        pin_of_net[n] = num
xe = MXc + TIP                      # east pad tips
ROW0_X = 305.3
r0 = U[pin_of_net["/ROW0"]]
direct("/ROW0", "B.Cu", [r0, (xe + 0.5, r0[1]), (xe + 0.8, r0[1] - 0.3), (ROW0_X, r0[1] - 0.3)], 0.2)
dvia("/ROW0", (ROW0_X, r0[1] - 0.3), 0.6, 0.3)
direct("/ROW0", "F.Cu", [(ROW0_X, r0[1] - 0.3), (ROW0_X, P.ROW0_Y)], 0.25)
lanes = [("/COL15", 24.0, 315.0), ("/ROW5", 24.65, BUNDLE["/ROW5"]), ("/ROW4", 25.3, BUNDLE["/ROW4"]),
         ("/ROW3", 25.95, BUNDLE["/ROW3"]), ("/ROW2", 26.6, BUNDLE["/ROW2"]), ("/ROW1", 27.25, BUNDLE["/ROW1"]),
         ("/COL14", 27.9, BUNDLE["/COL14"]), ("+3V3", 28.55, 303.4), ("/COL13", 29.4, BUNDLE["/COL13"])]
n_l = len(lanes)
for i, (net, ylane, xend) in enumerate(lanes):
    pin = 10 if net == "+3V3" else pin_of_net[net]
    py = U[pin][1]
    xj = xe + 0.25 + (n_l - 1 - i) * 0.3
    d = ylane - py
    pts = [U[pin], (xj, py), (xj + d, ylane), (xend, ylane)]
    direct(net, "B.Cu", pts, 0.2)
    if net == "+3V3":
        dvia("+3V3", (xend, ylane))
    elif net == "/COL15":
        dvia(net, (xend, ylane), 0.6, 0.3)
    # bundle vias already exist at (x, BUNDLE_VIA_Y); lanes end exactly there

route("/USB_D-", pg("J1", "B7"), pg("U2", "1"), 0.2, USB_ZONE)
route("/USB_D+", pg("J1", "B6"), pg("U2", "3"), 0.2, USB_ZONE)
route("/USB_D-", pg("U2", "6"), pg("R4", "2"), 0.2, USB_ZONE)
route("/USB_D+", pg("U2", "4"), pg("R3", "2"), 0.2, USB_ZONE)
route("/RP_DM", pg("U1", "46"), pg("R4", "1"), 0.2, Z)
route("/RP_DP", pg("U1", "47"), pg("R3", "1"), 0.2, Z)
route("/CC1", pg("J1", "A5"), pg("R1", "1"), 0.2, USB_ZONE)
route("/CC2", pg("J1", "B5"), pg("R2", "1"), 0.2, USB_ZONE)
route("VBUS", pg("J1", "A4"), pg("F1", "1"), 0.4, USB_ZONE)
route("VBUS", pg("J1", "A9"), "net", 0.3, USB_ZONE)
route("VBUS", [("F.Cu", Point(u2_5[0], 14.95).buffer(0.2))], "net", 0.3, USB_ZONE)
# ---- QSPI
for a, b, net in [("53", "5", "/QSPI_SD0"), ("52", "6", "/QSPI_SCLK"), ("51", "7", "/QSPI_SD3"),
                  ("54", "3", "/QSPI_SD2"), ("55", "2", "/QSPI_SD1"), ("56", "1", "/QSPI_SS")]:
    route(net, pg("U1", a), pg("U4", b), 0.2, Z)
connect_all("/QSPI_SS", 0.2)
route("/BOOTSEL", pg("R6", "2"), pg("SW90", "1"), 0.2)
# ---- crystal
route("/XOUT", pg("U1", "21"), pg("R8", "1"), 0.2, Z)
route("/XTAL_OUT", pg("R8", "2"), pg("Y1", "3"), 0.2)
connect_all("/XTAL_OUT", 0.2)
route("/XIN", pg("U1", "20"), pg("Y1", "1"), 0.2, Z)
connect_all("/XIN", 0.2)
connect_all("/RUN", 0.2, seed=pad_of[("U1", "26")][0])
# ---- west matrix fan-out to the bus
print("matrix fan-out ...")
for c in range(13):
    net = f"/COL{c}"
    route(net, pg("U1", str(pin_of_net[net])), [("B.Cu", Point(BUS_X_EAST, bus_via[c][1]).buffer(0.1))], W_SIG, Z)
# ---- +5V / LDO input
connect_all("+5V", 0.4, seed=pad_of[("F1", "2")][0])
# ---- power rails (before GND escapes: they are the more constrained)
print("power ...")
connect_all("+3V3", 0.25, seed=pad_of[("U3", "2")][0])
connect_all("+1V1", 0.25, seed=pad_of[("U1", "45")][0])
# ---- GND escapes for every small GND pad in the area
print("GND escapes ...")
gnd_pads = [p for p in pads if p["net"] == "GND" and "B.Cu" in p["layers"] and not p["drill"]
            and WIN.contains(Point(p["x"], p["y"])) and p["ref"] not in ("U1", "J1", "U2")
            and not p["ref"].startswith("D") and not (p["ref"].startswith("SW") and p["ref"] not in ("SW90", "SW91"))
            and (p["ref"], p["num"]) not in (("U4", "4"), ("C3", "2"), ("C4", "2"))]
for p in gnd_pads:
    route("GND", [("B.Cu", p["geom"])], "via", 0.25)
print("done routing: ok", len(routed), "failed", len(failed), failed)

all_tracks = tracks + [dict(net=t["net"], layer=t["layer"], a=list(t["a"]), b=list(t["b"]), w=t["w"]) for t in R.tracks]
all_vias = vias + [dict(net=v["net"], at=list(v["at"]), d=v["d"], drill=v["drill"]) for v in R.vias]


def prune_dangling(trs, vs):
    """Drop vias that end up connected on one layer only (a later route found a better path),
    then the track stubs that led to them. GND is left alone (the pours connect it)."""
    def near(a, b):
        return math.dist(a, b) < 0.01

    def touches(net, layer, pt, skip=None, r=0.0):
        """copper of `net` on `layer` reaching the point (or a disc of radius r around it)"""
        n = 0
        for t in trs:
            if t is skip or t["net"] != net or t["layer"] != layer:
                continue
            if LineString([t["a"], t["b"]]).distance(Point(pt)) < t["w"] / 2 + r:
                n += 1
        n += sum(1 for v in vs if v["net"] == net and near(v["at"], pt))
        n += sum(1 for q in pads if q["net"] == net and layer in q["layers"] and q["geom"].distance(Point(pt)) < r + 0.01)
        return n
    removed = 0
    for v in list(vs):
        if v["net"] == "GND":
            continue
        conn = {lay: touches(v["net"], lay, v["at"], r=v["d"] / 2) - 1 for lay in ("F.Cu", "B.Cu")}   # -1: the via itself
        if min(conn.values()) > 0:
            continue
        vs.remove(v)
        removed += 1
        print(f"  pruned via {v['net']} at {v['at']} (connections F.Cu {conn['F.Cu']}, B.Cu {conn['B.Cu']})")
        free = [tuple(v["at"])]
        while free:                                    # walk the stub back from the removed via
            pt = free.pop()
            for t in list(trs):
                if t["net"] != v["net"] or not (near(t["a"], pt) or near(t["b"], pt)):
                    continue
                if touches(t["net"], t["layer"], pt, skip=t) == 0:
                    trs.remove(t)
                    other = t["b"] if near(t["a"], pt) else t["a"]
                    if touches(t["net"], t["layer"], other, skip=None) == 0:
                        free.append(tuple(other))
    return removed


n_pruned = prune_dangling(all_tracks, all_vias)
print("pruned dangling vias:", n_pruned)
out = dict(rule_areas={k: list(v) for k, v in P.FANOUT_AREAS.items()}, tracks=all_tracks, vias=all_vias, failed=failed)
(STAGE / "build").mkdir(exist_ok=True)
(STAGE / "build" / "routes.json").write_text(json.dumps(out), encoding="utf-8")
print("tracks", len(out["tracks"]), "vias", len(out["vias"]))
