"""Parse KiCad footprints (.kicad_mod) and place their pads in board coordinates.

Placement convention (matches pcbnew): a BOTTOM footprint is flipped left/right
(x -> -x) and then rotated by phi (counter-clockwise as seen from the top, Y down).
In pcbnew this is Flip(LEFT_RIGHT) followed by SetOrientationDegrees(phi + 180).
"""
from __future__ import annotations

import math
from functools import lru_cache
from pathlib import Path

from shapely import affinity
from shapely.geometry import Point, Polygon, box
from shapely.ops import unary_union

import sexp

LIB = Path(__file__).resolve().parents[1] / "PCB" / "Vamora75.pretty"


def rot(x, y, deg):
    """CCW (visual, Y-down) rotation."""
    a = math.radians(deg)
    return x * math.cos(a) + y * math.sin(a), -x * math.sin(a) + y * math.cos(a)


@lru_cache(None)
def load(name):
    e = sexp.loads((LIB / f"{name}.kicad_mod").read_text(encoding="utf-8"))
    pads = []
    for p in sexp.findall(e, "pad"):
        num, kind, shape = p[1], str(p[2]), str(p[3])
        at = sexp.find(p, "at")
        size = sexp.find(p, "size")
        drill = sexp.find(p, "drill")
        layers = [str(x) for x in sexp.find(p, "layers")[1:]]
        rr = sexp.find(p, "roundrect_rratio")
        dr = None
        if drill:
            vals = [x for x in drill[1:] if isinstance(x, (int, float))]
            dr = (vals[0], vals[1] if len(vals) > 1 else vals[0])
        pads.append(dict(num=str(num), kind=kind, shape=shape, x=at[1], y=at[2], rot=at[3] if len(at) > 3 else 0,
                         w=size[1], h=size[2], drill=dr, layers=layers, rr=rr[1] if rr else 0))
    zones = []
    for z in sexp.findall(e, "zone"):
        if sexp.find(z, "keepout"):
            pts = [(q[1], q[2]) for q in sexp.find(sexp.find(z, "polygon"), "pts")[1:]]
            lay = sexp.find(z, "layers") or sexp.find(z, "layer")      # KiCad writes (layer ..) for one layer
            zones.append(dict(layers=[str(x) for x in lay[1:]], pts=pts))
    crt = []
    for g in sexp.findall(e, "fp_line"):
        if str(sexp.find(g, "layer")[1]).endswith("CrtYd"):
            s, t = sexp.find(g, "start"), sexp.find(g, "end")
            crt.append(((s[1], s[2]), (t[1], t[2])))
    for g in sexp.findall(e, "fp_rect"):
        if str(sexp.find(g, "layer")[1]).endswith("CrtYd"):
            s, t = sexp.find(g, "start"), sexp.find(g, "end")
            crt += [((s[1], s[2]), (t[1], s[2])), ((t[1], s[2]), (t[1], t[2])), ((t[1], t[2]), (s[1], t[2])), ((s[1], t[2]), (s[1], s[2]))]
    return dict(pads=pads, zones=zones, courtyard=crt)


def _side_layer(l, bottom):
    if not bottom:
        return l
    return l.replace("F.", "@").replace("B.", "F.").replace("@", "B.")


def xform(x, y, X, Y, phi, bottom):
    if bottom:
        x = -x
    dx, dy = rot(x, y, phi)
    return X + dx, Y + dy


def placed_pads(name, X, Y, phi, bottom):
    fp = load(name)
    out = []
    for p in fp["pads"]:
        cx, cy = xform(p["x"], p["y"], X, Y, phi, bottom)
        prot = (p["rot"] if not bottom else -p["rot"]) + phi
        if p["shape"] == "circle":
            geom = Point(cx, cy).buffer(p["w"] / 2, resolution=16)
        else:
            w, h = p["w"], p["h"]
            r = min(w, h) * p["rr"] if p["shape"] == "roundrect" else (min(w, h) / 2 if p["shape"] == "oval" else 0)
            g = box(-w / 2 + r, -h / 2 + r, w / 2 - r, h / 2 - r).buffer(r, resolution=8) if r > 0 else box(-w / 2, -h / 2, w / 2, h / 2)
            g = affinity.rotate(g, -prot, origin=(0, 0))   # shapely rotate is CCW in Y-up == CW visual in Y-down
            geom = affinity.translate(g, cx, cy)
        layers = set()
        for l in p["layers"]:
            if l in ("*.Cu",):
                layers |= {"F.Cu", "B.Cu"}
            elif l.endswith(".Cu"):
                layers.add(_side_layer(l, bottom))
        out.append(dict(num=p["num"], kind=p["kind"], x=cx, y=cy, geom=geom, layers=layers,
                        drill=p["drill"], shape=p["shape"]))
    keepouts = []
    for z in fp["zones"]:
        pts = [xform(x, y, X, Y, phi, bottom) for x, y in z["pts"]]
        keepouts.append(dict(layers={_side_layer(l, bottom) for l in z["layers"]}, geom=Polygon(pts)))
    crt = []
    for a, b in fp["courtyard"]:
        crt.append((xform(*a, X, Y, phi, bottom), xform(*b, X, Y, phi, bottom)))
    court = None
    if crt:
        xs = [p[0] for s in crt for p in s]
        ys = [p[1] for s in crt for p in s]
        court = box(min(xs), min(ys), max(xs), max(ys))
    return out, keepouts, court
