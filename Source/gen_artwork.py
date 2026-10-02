"""Silkscreen artwork for the Vamora75 PCB (rev 1.1).

    python Source/gen_artwork.py <stage PCB dir>

Front (F.SilkS): a very large "Vamora75" across the middle of the board, readable from
above. Joe Scotto's switch outlines run straight through the letters (silk on silk, which the
project rules ignore), and the letters are knocked out around every hole and exposed pad with
clearance, so nothing solderable or drilled is covered.

Back (B.SilkS): the poem "Nam quoc son ha" centred in the free band under the F-row, plus the
BOOT, RESET and revision labels. These are composed in BOTTOM-VIEW coordinates (u = W - x, the
board turned over) so they read from below, then mirrored into board coordinates. The poem sits
clear of pads, holes, legends and the labels.

The name and the poem may cross vias: every via is tented (covered by solder mask on both
sides), so the silkscreen prints over it and no letter or diacritic has to be cut. The small
labels still keep 0.35 mm from vias.

Obstacles come from build/silk_obstacles.json (extract_obstacles.py). Output:
build/artwork.json (hole-free polygons per layer) and the previews build/artwork_front_view.png
and build/artwork_bottom_view.png.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from shapely import affinity
from shapely.geometry import Point, Polygon, box
from shapely.ops import unary_union
from shapely.prepared import prep

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import vamora_logo as V  # noqa: E402

STAGE = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE.parent / "PCB"
BOLD = V.SEGOE_BOLD
MIN_SILK = 0.18          # JLCPCB silkscreen minimum line width is 0.153 mm
NAME_WIDTH = 240.0       # mm, about 72 % of the board width
REV = "rev 1.1"
POEM = ["NAM QUỐC SƠN HÀ",
        "Nam quốc sơn hà Nam đế cư,",
        "Tiệt nhiên định phận tại thiên thư.",
        "Như hà nghịch lỗ lai xâm phạm,",
        "Nhữ đẳng hành khan thủ bại hư."]

obs = json.loads((STAGE / "build" / "silk_obstacles.json").read_text(encoding="utf-8"))
W, H = obs["board"]["w"], obs["board"]["h"]


def _poly(pts):
    g = Polygon(pts)
    return g if g.is_valid else g.buffer(0)


def _union(items):
    return unary_union([_poly(s["pts"]) for s in items if len(s["pts"]) >= 3])


def to_board(g):
    """bottom view (u, v) -> board (x, y): mirror about the board's vertical centre line."""
    return affinity.translate(affinity.scale(g, -1, 1, origin=(0, 0)), W, 0)


SILK = {s: _union(obs[s]["silk"]) for s in "FB"}
PADS = {s: _union(obs[s]["pads"]) for s in "FB"}
HOLES = _union(obs["holes"])
VIA_KEEP = unary_union([Point(v["at"]).buffer(v["d"] / 2 + 0.35) for v in obs["vias"]])
EDGE = box(-5, -5, W + 5, H + 5).difference(box(1.2, 1.2, W - 1.2, H - 1.2))
COMMON = unary_union([HOLES.buffer(0.6), EDGE])
FRONT_KEEP = unary_union([COMMON, PADS["F"].buffer(0.35)])      # front silk and tented vias are not avoided
BACK_HARD = unary_union([COMMON, PADS["B"].buffer(0.35), SILK["B"].buffer(0.3)])
placed = []          # envelopes of back-side blocks already placed (board coords)


def offsets(du, dv, step):
    return sorted(((i * step, j * step) for i in range(-int(du / step), int(du / step) + 1)
                   for j in range(-int(dv / step), int(dv / step) + 1)),
                  key=lambda o: (o[0] ** 2 + (2 * o[1]) ** 2))


def fit(name, make, sizes, centre_uv, du, dv, step=0.25, pad=0.4, vias=True):
    """Back-side block: largest size first, then the free position nearest to centre_uv (bottom view).
    vias=False lets the block cross (tented) vias."""
    blocked = prep(unary_union([BACK_HARD] + ([VIA_KEEP] if vias else []) + placed))
    offs = offsets(du, dv, step)
    for s in sizes:
        g = V.centre(make(s))
        x0, y0, x1, y1 = g.bounds
        env = box(x0 - pad, y0 - pad, x1 + pad, y1 + pad)
        for ou, ov in offs:
            e = to_board(affinity.translate(env, centre_uv[0] + ou, centre_uv[1] + ov))
            if not blocked.intersects(e):
                placed.append(e.buffer(0.3))
                gb = to_board(affinity.translate(g, centre_uv[0] + ou, centre_uv[1] + ov))
                print(f"  {name:8s} size {s:5.2f}  at u={centre_uv[0] + ou:7.2f} v={centre_uv[1] + ov:6.2f}")
                return gb
    print(f"  {name:8s} NOT PLACED (no free spot)")
    return None


def frange(a, b, st):
    out, v = [], a
    while v >= b - 1e-9:
        out.append(round(v, 3))
        v -= st
    return out


def label(text, font=BOLD):
    return lambda c: V.shaped_text(text, c, font)[0]


def poem_block(c):
    """Title over the two couplets side by side (lines 1-2 left, 3-4 right), Y down."""
    g0, w0 = V.shaped_text(POEM[0], c * 1.25, BOLD)
    out = [affinity.translate(g0, -w0 / 2, 0)]
    lines = [V.shaped_text(t, c, BOLD) for t in POEM[1:]]
    colw = [max(lines[0][1], lines[1][1]), max(lines[2][1], lines[3][1])]
    gap = c * 4.0
    x0 = -(colw[0] + gap + colw[1]) / 2
    for i, (g, _) in enumerate(lines):
        col, row = divmod(i, 2)
        out.append(affinity.translate(g, x0 + col * (colw[0] + gap), c * 2.9 + row * c * 2.3))
    return unary_union(out)


def front_name():
    """The name, centred on the board front, knocked out around holes and exposed pads."""
    g = affinity.translate(V.name_text(NAME_WIDTH), W / 2, H / 2)
    g = g.difference(FRONT_KEEP)
    r = MIN_SILK / 2
    g = g.buffer(-r, join_style=2).buffer(r, join_style=2)          # drop slivers thinner than 0.18 mm
    g = unary_union([p for p in V.polygons(g) if p.area > 0.6])     # and specks
    x0, y0, x1, y1 = g.bounds
    print(f"  name     {V.NAME!r} {x1 - x0:.1f} x {y1 - y0:.1f} mm on F.SilkS, {len(V.polygons(g))} pieces after knock-outs")
    return g


def view_png(side, blocks, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import PathPatch
    from matplotlib.path import Path as MPath

    def patch(g, color):
        verts, codes = [], []
        for p in V.polygons(g):
            for r in [p.exterior] + list(p.interiors):
                c = list(r.coords)
                verts += c
                codes += [MPath.MOVETO] + [MPath.LINETO] * (len(c) - 2) + [MPath.CLOSEPOLY]
        return PathPatch(MPath(verts, codes), facecolor=color, edgecolor="none")

    view = to_board if side == "B" else (lambda g: g)      # the same mirror maps board -> bottom view
    fig, ax = plt.subplots(figsize=(26, 26 * H / W))
    ax.add_patch(plt.Rectangle((0, 0), W, H, facecolor="#1d3b2a"))
    ax.add_patch(patch(view(PADS[side]), "#d4a640"))
    ax.add_patch(patch(view(SILK[side]), "#e8e8e8"))
    ax.add_patch(patch(view(HOLES), "#0b0b0b"))
    if blocks:
        ax.add_patch(patch(view(unary_union(blocks)), "#ffffff"))
    ax.set_xlim(0, W); ax.set_ylim(H, 0); ax.set_aspect("equal"); ax.set_axis_off()
    fig.tight_layout(pad=0.2); fig.savefig(path, dpi=110); plt.close(fig)


if __name__ == "__main__":
    print("artwork:")
    U = lambda x: W - x                     # board x -> bottom-view u
    blocks, layer = {}, {}
    blocks["name"], layer["name"] = front_name(), "F.SilkS"
    blocks["boot"] = fit("BOOT", label("BOOT"), frange(1.3, 1.0, 0.1), (U(307.3), 16.0), 8, 6)
    blocks["reset"] = fit("RESET", label("RESET"), frange(1.3, 1.0, 0.1), (U(288.8), 44.5), 8, 6)
    blocks["rev"] = fit("rev", label(REV), frange(1.4, 1.0, 0.1), (U(264.5), 24.5), 8, 4)
    blocks["poem"] = fit("poem", poem_block, frange(3.0, 1.6, 0.05), (W / 2, 24.0), 30, 4, pad=0.6, vias=False)
    ok = {k: v for k, v in blocks.items() if v is not None}
    polys = []
    for k, g in ok.items():
        loss = V.min_feature_check(g, MIN_SILK * 0.9)
        pieces = V.hole_free(V.clean(g))
        lay = layer.get(k, "B.SilkS")
        print(f"  {k:8s} {lay}  {len(pieces):4d} polygons, area below {MIN_SILK * 0.9:.2f} mm features: {100 * loss:.2f} %")
        polys.append(dict(name=k, layer=lay,
                          rings=[dict(outer=[[round(x, 4), round(y, 4)] for x, y in p.exterior.coords[:-1]], holes=[])
                                 for p in pieces]))
    (STAGE / "build" / "artwork.json").write_text(json.dumps(dict(polys=polys, texts=[])), encoding="utf-8")
    view_png("F", [g for k, g in ok.items() if layer.get(k) == "F.SilkS"], STAGE / "build" / "artwork_front_view.png")
    view_png("B", [g for k, g in ok.items() if layer.get(k) != "F.SilkS"], STAGE / "build" / "artwork_bottom_view.png")
    missing = [k for k, v in blocks.items() if v is None]
    print("artwork:", ", ".join(ok), "| missing:", ", ".join(missing) or "none")
