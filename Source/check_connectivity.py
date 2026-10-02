"""Exact (geometric) connectivity + clearance check of routes.json against the placed pads.

    python Source/check_connectivity.py <stage PCB dir> [--clearance]
Reports nets whose pads are split into several copper islands (ignoring zone fills,
except GND which is completed by the copper pours on both layers).
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

from shapely.geometry import LineString, Point
from shapely.strtree import STRtree

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pcb_plan as P  # noqa: E402

STAGE = Path(sys.argv[1])
nets, comps = P.netlist(STAGE / "build" / "Vamora75.net.xml")
pl = P.placement()
pads, keepouts, courts = P.all_pads(pl, nets)
R = json.loads((STAGE / "build" / "routes.json").read_text())

items = []   # (net, layerset, geom, label)
for p in pads:
    if p["net"] and p["kind"] != "np_thru_hole":
        items.append((p["net"], frozenset(p["layers"]), p["geom"], f"{p['ref']}.{p['num']}"))
for t in R["tracks"]:
    items.append((t["net"], frozenset([t["layer"]]), LineString([t["a"], t["b"]]).buffer(t["w"] / 2, cap_style=1), None))
for v in R["vias"]:
    items.append((v["net"], frozenset(["F.Cu", "B.Cu"]), Point(v["at"]).buffer(v["d"] / 2), None))

by_net = defaultdict(list)
for it in items:
    by_net[it[0]].append(it)

problems = {}
for net, its in by_net.items():
    parent = list(range(len(its)))

    def f(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    geoms = [g for _, _, g, _ in its]
    tree = STRtree(geoms)
    for i, (_, li, gi, _) in enumerate(its):
        for j in tree.query(gi):
            j = int(j)
            if j <= i:
                continue
            if li & its[j][1] and gi.intersects(geoms[j]):
                parent[f(i)] = f(j)
    groups = defaultdict(list)
    for i, (_, _, _, lab) in enumerate(its):
        if lab:
            groups[f(i)].append(lab)
    if len(groups) > 1:
        problems[net] = sorted(groups.values(), key=len, reverse=True)

skip_pour = {"GND"}
bad = {n: g for n, g in problems.items() if n not in skip_pour and not n.startswith("unconnected")}
print(f"nets: {len(by_net)}  split nets (excluding GND/pour): {len(bad)}")
for n, g in sorted(bad.items()):
    print(" ", n, "->", [grp[:6] for grp in g][:4])
gnd = problems.get("GND")
if gnd:
    print("  GND islands before pour:", len(gnd))

if "--clearance" in sys.argv:
    # pairwise clearance between different nets on the same layer (tracks/vias/pads)
    rules = R.get("rule_areas", {})
    from shapely.geometry import box
    relaxed = [box(*v) for v in rules.values()]
    U1 = courts["U1"].buffer(0.15)
    relaxed.append(U1)
    geoms = [g for _, _, g, _ in items]
    tree = STRtree(geoms)
    viol = []
    for i, (ni, li, gi, labi) in enumerate(items):
        for j in tree.query(gi.buffer(0.2)):
            j = int(j)
            if j <= i:
                continue
            nj, lj, gj, labj = items[j]
            if ni == nj or not (li & lj):
                continue
            d = gi.distance(gj)
            need = 0.15 if any(r.intersects(gi) or r.intersects(gj) for r in relaxed) else 0.2
            if d < need - 1e-4:
                c = gi.centroid
                viol.append((round(d, 3), need, ni, nj, labi, labj, round(c.x, 2), round(c.y, 2)))
    print("clearance violations:", len(viol))
    for v in sorted(viol)[:40]:
        print("  ", v)
