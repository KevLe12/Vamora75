"""Vamora brand mark: geometry shared by the artwork, PCB silkscreen and case engraving.

The mark is a keycap seen from above carrying a "seal star":
  * a solid five-pointed star - the star found on the flags of Viet Nam (gold star),
    the United States (fifty stars) and Morocco (green pentagram);
  * incised with an alternating over/under pentagram weave - the interlaced
    "Seal of Solomon" drawn on the Moroccan flag and common in zellige strapwork;
  * the wordmark uses crossbar-less A's (VΛMORΛ) that repeat the star's tips.

All geometry is Shapely, millimetres, Y axis pointing DOWN (SVG/KiCad convention).
Every exporter derives from the same polygons, so PCB, case and artwork always match.
"""
from __future__ import annotations

import math
from pathlib import Path

from shapely import affinity
from shapely.geometry import LineString, MultiPolygon, Point, Polygon, box
from shapely.ops import unary_union

# Brand palette (shared red of all three flags, VN gold, MA green, US navy)
PALETTE = {
    "ink": "#15171c",
    "graphite": "#2a2d34",
    "brass": "#d4a640",
    "red": "#c1272d",
    "gold": "#f2c230",
    "green": "#006233",
    "navy": "#0f2340",
    "paper": "#f4f1ea",
}

SEGOE = r"C:\Windows\Fonts\segoeui.ttf"
SEGOE_BOLD = r"C:\Windows\Fonts\segoeuib.ttf"
SEGOE_BLACK = r"C:\Windows\Fonts\seguibl.ttf"   # the Vamora75 name on the PCB, plate and case (rev 1.1)
NAME = "Vamora75"


def name_text(width_mm: float, font: str = SEGOE_BLACK):
    """The plain "Vamora75" name (no emblem), centred at (0, 0), scaled to `width_mm`. Y down."""
    g, _ = shaped_text(NAME, 10.0, font)
    g = centre(g)
    x0, y0, x1, y1 = g.bounds
    k = width_mm / (x1 - x0)
    return affinity.scale(g, k, k, origin=(0, 0))


# ----------------------------------------------------------------------------- star
def _tips(cx, cy, R):
    return [(cx + R * math.cos(math.radians(-90 + 72 * k)),
             cy + R * math.sin(math.radians(-90 + 72 * k))) for k in range(5)]


def _wedge(cx, cy, a0, a1, big=4000.0, n=48):
    return Polygon([(cx, cy)] + [(cx + big * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
                                  cy + big * math.sin(math.radians(a0 + (a1 - a0) * i / n)))
                                 for i in range(n + 1)])


def _bands(cx, cy, R, w):
    """Five mitred pentagram bands; band k joins tip k to tip k+2."""
    P = _tips(cx, cy, R)
    out = []
    for k in range(5):
        a, b = P[k], P[(k + 2) % 5]
        L = math.dist(a, b)
        ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        strip = LineString([(a[0] - ux * 4 * w, a[1] - uy * 4 * w),
                            (b[0] + ux * 4 * w, b[1] + uy * 4 * w)]).buffer(w / 2, cap_style=2)
        ta = -90 + 72 * k
        out.append(strip.intersection(_wedge(cx, cy, ta, ta + 144)))
    return P, out


def seal_star(cx: float, cy: float, R: float, band: float, gap: float):
    """Solid star; the cinquefoil weave is shown by incised lines of width `gap`.

    R is the circumradius of the pentagram band centre-lines; the silhouette tips
    reach slightly further because the band edges are mitred.
    Returns (geometry, silhouette).
    """
    P, B = _bands(cx, cy, R, band)
    crossings = []
    for i in range(5):
        j = (i + 1) % 5                      # bands k and k+1 cross inside the star
        crossings.append((i, j, B[i].intersection(B[j]).centroid))

    def t(k, c):
        a, b = P[k], P[(k + 2) % 5]
        return ((c.x - a[0]) * (b[0] - a[0]) + (c.y - a[1]) * (b[1] - a[1])) / math.dist(a, b) ** 2

    path = [0, 2, 4, 1, 3]                  # unicursal path P0->P2->P4->P1->P3->P0
    events = sorted([(path.index(i), t(i, c), n, i) for n, (i, j, c) in enumerate(crossings)] +
                    [(path.index(j), t(j, c), n, j) for n, (i, j, c) in enumerate(crossings)])
    over = {}
    for k, (_, _, n, band_id) in enumerate(events):
        if k % 2 == 0:                       # strictly alternating over / under
            assert n not in over
            over[n] = band_id
    assert len(over) == 5
    woven = list(B)
    for n, (i, j, c) in enumerate(crossings):
        top = over[n]
        under = j if top == i else i
        local = Point(c.x, c.y).buffer(band * 2.5)
        woven[under] = woven[under].difference(B[top].buffer(gap, join_style=2).intersection(local))
    allb = unary_union(B)
    if not isinstance(allb, Polygon):        # float slivers at some scales: keep the star body
        allb = max(polygons(allb), key=lambda p: p.area)
    silhouette = Polygon(allb.exterior)
    tiles = silhouette.difference(allb.buffer(gap, join_style=2))
    return unary_union(woven + [tiles]), silhouette


def star_bbox_offset(R, band):
    """Vertical offset from circumcentre to the visual (bbox) centre of the silhouette."""
    _, sil = seal_star(0, 0, R, band, band * 0.1)
    x0, y0, x1, y1 = sil.bounds
    return (y0 + y1) / 2, (x1 - x0), (y1 - y0)


# --------------------------------------------------------------------------- keycap
def rrect(x0, y0, x1, y1, r):
    return box(x0 + r, y0 + r, x1 - r, y1 - r).buffer(r, resolution=32)


def emblem(size: float = 40.0, min_feature: float = 0.2, filled: bool = False):
    """Keycap emblem centred on (0,0), `size` = outer keycap width in mm.

    min_feature: smallest line/gap the process can make (silkscreen ~0.15-0.2,
    FDM engraving ~0.6-0.8, CNC/laser ~0.3). Stroke and weave gaps never go below it.
    Returns dict of named geometries.
    """
    s = size
    stroke = max(s * 0.034, min_feature * 1.25)
    outer = rrect(-s / 2, -s / 2, s / 2, s / 2, s * 0.17)
    ts = s * 0.74
    ty = -s * 0.05
    top = rrect(-ts / 2, ty - ts / 2, ts / 2, ty + ts / 2, s * 0.13)
    R = ts * 0.345
    bandw = R * 0.235
    gap = max(R * 0.034, min_feature)
    dy, _, _ = star_bbox_offset(R, bandw)
    star, sil = seal_star(0, ty - dy + s * 0.004, R, bandw, gap)
    ring = outer.difference(outer.buffer(-stroke)).union(top.difference(top.buffer(-stroke)))
    mono = unary_union([ring, star])
    return {"outer": outer, "top": top, "ring": ring, "star": star, "star_silhouette": sil,
            "mono": mono, "stroke": stroke}


# ------------------------------------------------------------------------- wordmark
def _seg(a, b, t):
    return LineString([a, b]).buffer(t / 2, cap_style=2, join_style=2)


def _arc(cx, cy, r, t, a0, a1, n=72):
    pts = [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * k / n)),
            cy + r * math.sin(math.radians(a0 + (a1 - a0) * k / n))) for k in range(n + 1)]
    return LineString(pts).buffer(t / 2, cap_style=2, join_style=1)


def _clip(g, H):
    return g.intersection(box(-1e4, 0, 1e4, H))


def _glyph(ch, H, t):
    """Geometric monoline capitals. Origin top-left, Y down, cap height H."""
    if ch == "V":
        w = H * 0.94
        a, b, c = (t * 0.55, 0.0), (w / 2, H), (w - t * 0.55, 0.0)
        g = unary_union([LineString([(a[0] - (b[0] - a[0]) * .3, -H * .3), b]).buffer(t / 2, cap_style=2, join_style=2),
                         LineString([(c[0] + (c[0] - b[0]) * .3, -H * .3), b]).buffer(t / 2, cap_style=2, join_style=2)])
        return _clip(g, H), w
    if ch == "A":                            # crossbar-less: the star's tip
        g, w = _glyph("V", H, t)
        return affinity.scale(g, 1, -1, origin=(0, H / 2)), w
    if ch == "M":
        w = H * 1.06
        g = unary_union([box(0, 0, t, H), box(w - t, 0, w, H),
                         _seg((t / 2, 0), (w / 2, H * 0.64), t), _seg((w - t / 2, 0), (w / 2, H * 0.64), t)])
        return _clip(g, H), w
    if ch == "O":
        w = H * 1.02
        o = Point(w / 2, H / 2).buffer(H / 2, resolution=72)
        o = affinity.scale(o, w / H, 1)
        return o.difference(o.buffer(-t)), w
    if ch == "R":
        w = H * 0.80
        bh = H * 0.56
        r = bh / 2 - t / 2
        x1 = w - r - t / 2
        g = unary_union([box(0, 0, t, H), box(0, 0, x1, t), box(0, bh - t, x1, bh),
                         _arc(x1, bh / 2, r, t, -90, 90),
                         LineString([(w * 0.40, bh - t / 2), (w * 1.02, H + t)]).buffer(t / 2, cap_style=2, join_style=2)])
        return _clip(g.intersection(box(0, -1, w, H + 1)), H), w
    if ch == "7":
        w = H * 0.70
        g = unary_union([box(0, 0, w, t), LineString([(w - t * .45, t * .5), (w * .26, H + t)]).buffer(t / 2, cap_style=2, join_style=2)])
        return _clip(g.intersection(box(0, 0, w, H)), H), w
    if ch == "5":
        w = H * 0.72
        r = H * 0.285
        cy = H - r - t / 2
        x1 = w - r - t / 2
        g = unary_union([box(t * .1, 0, w, t), box(t * .1, 0, t * 1.1, H * .46),
                         box(t * .1, H * .46 - t, x1, H * .46), _arc(x1, cy, r, t, -90, 90), box(0, H - t, x1, H)])
        return _clip(g, H), w
    raise KeyError(ch)


def wordmark(text="VAMORA", H=10.0, weight=0.165, tracking=0.17):
    """Return (geometry, width). Origin top-left of the cap line, Y down."""
    t = H * weight
    x, parts = 0.0, []
    for ch in text:
        if ch == " ":
            x += H * 0.45
            continue
        g, w = _glyph(ch, H, t)
        parts.append(affinity.translate(g, x, 0))
        x += w + H * tracking
    return unary_union(parts), x - H * tracking


# ---------------------------------------------------------------- shaped text (Arabic etc.)
class _FlatPen:
    """fontTools pen that flattens curves into polylines (font units, Y up)."""

    def __init__(self, glyphset, steps=8):
        self.glyphSet, self.steps, self.contours, self.cur = glyphset, steps, [], []

    def moveTo(self, p):
        self.cur = [p]

    def lineTo(self, p):
        self.cur.append(p)

    def qCurveTo(self, *pts):
        # TrueType implied on-curve points between consecutive off-curve points
        if pts[-1] is None:                  # closed contour of only off-curve points
            pts = pts[:-1]
            start = ((pts[-1][0] + pts[0][0]) / 2, (pts[-1][1] + pts[0][1]) / 2)
            self.cur = [start]
            pts = pts + (start,)
        p0 = self.cur[-1]
        offs, end = pts[:-1], pts[-1]
        for i, c in enumerate(offs):
            nxt = end if i == len(offs) - 1 else ((c[0] + offs[i + 1][0]) / 2, (c[1] + offs[i + 1][1]) / 2)
            for s in range(1, self.steps + 1):
                u = s / self.steps
                self.cur.append(((1 - u) ** 2 * p0[0] + 2 * (1 - u) * u * c[0] + u * u * nxt[0],
                                 (1 - u) ** 2 * p0[1] + 2 * (1 - u) * u * c[1] + u * u * nxt[1]))
            p0 = nxt

    def curveTo(self, *pts):
        p0 = self.cur[-1]
        c1, c2, e = pts[-3], pts[-2], pts[-1]
        for s in range(1, self.steps + 1):
            u = s / self.steps
            self.cur.append(tuple((1 - u) ** 3 * a + 3 * (1 - u) ** 2 * u * b + 3 * (1 - u) * u * u * c + u ** 3 * d
                                  for a, b, c, d in zip(p0, c1, c2, e)))

    def closePath(self):
        if len(self.cur) >= 3:
            self.contours.append(self.cur)
        self.cur = []

    endPath = closePath

    def addComponent(self, name, transform):
        sub = _FlatPen(self.glyphSet, self.steps)
        self.glyphSet[name].draw(sub)
        a, b, c, d, e, f = transform
        for con in sub.contours:
            self.contours.append([(a * x + c * y + e, b * x + d * y + f) for x, y in con])


def shaped_text(text: str, cap_mm: float, font_path: str = SEGOE, features=None):
    """Shape `text` with HarfBuzz (handles Arabic joining/RTL and Vietnamese marks).

    Returns (geometry, width) with origin at the left end of the baseline, Y down,
    scaled so that capital 'H' height == cap_mm.
    """
    import uharfbuzz as hb
    from fontTools.ttLib import TTFont

    blob = hb.Blob.from_file_path(font_path)
    face = hb.Face(blob)
    font = hb.Font(face)
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(font, buf, features or {"kern": True, "liga": True})
    tt = TTFont(font_path)
    gs = tt.getGlyphSet()
    order = tt.getGlyphOrder()
    capH = tt["OS/2"].sCapHeight or 0.7 * tt["head"].unitsPerEm
    k = cap_mm / capH
    x = 0
    polys = []
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        pen = _FlatPen(gs)
        gs[order[info.codepoint]].draw(pen)
        fills, holes = [], []
        for con in pen.contours:
            pts = [((x + pos.x_offset + px) * k, -(pos.y_offset + py) * k) for px, py in con]
            if len(pts) < 3:
                continue
            p = Polygon(pts).buffer(0)
            area = sum(pts[i][0] * pts[i - 1][1] - pts[i - 1][0] * pts[i][1] for i in range(len(pts))) / 2
            # TrueType outer contours are clockwise in Y-up; after Y flip -> signed area < 0 here
            (fills if area < 0 else holes).append(p)
        if fills:
            polys.append(unary_union(fills).difference(unary_union(holes)) if holes else unary_union(fills))
        x += pos.x_advance
    return unary_union(polys), x * k


# --------------------------------------------------------------------------- lockups
def tagline_parts(cap=2.2, sep_gap=None):
    """'VIỆT NAM · USA · المغرب' as separate geometries: vn, us, ma, dots (origin baseline-left)."""
    sep_gap = sep_gap or cap * 1.0
    segs = [("vn", shaped_text("VIỆT NAM", cap, SEGOE_BOLD)), ("us", shaped_text("USA", cap, SEGOE_BOLD)),
            ("ma", shaped_text("المغرب", cap * 1.12, SEGOE_BOLD))]
    x, out, dots = 0.0, {}, []
    dot_r = cap * 0.13
    for i, (name, (g, w)) in enumerate(segs):
        out[name] = affinity.translate(g, x, 0)
        x += w
        if i < len(segs) - 1:
            dots.append(Point(x + sep_gap, -cap * 0.42).buffer(dot_r, resolution=16))
            x += sep_gap * 2
    out["dots"] = unary_union(dots)
    return out


def tagline(cap=2.2, sep_gap=None):
    """'VIỆT NAM · USA · المغرب' — each name in its own script."""
    geom = clean(unary_union(list(tagline_parts(cap, sep_gap).values())))
    x0, y0, x1, y1 = geom.bounds
    return geom, (x0, y0, x1, y1)


def clean(g, grid=0.0005):
    """Valid, noded geometry snapped to a 0.5 um grid (robust boolean ops later)."""
    import shapely
    g = shapely.make_valid(g)
    g = shapely.set_precision(g, grid)
    return unary_union([p for p in polygons(g) if p.area > grid * grid * 10])


def centre(g):
    g = clean(g)
    x0, y0, x1, y1 = g.bounds
    return affinity.translate(g, -(x0 + x1) / 2, -(y0 + y1) / 2)


def stacked_lockup(width_mm: float, min_feature: float, with_tagline=True, with_75=True):
    """Emblem above wordmark (and optional tagline); centred at (0,0)."""
    # build at a nominal scale then scale to width
    e = emblem(40, min_feature=min_feature * (40 / max(width_mm, 1)) * 1.0)
    parts = [e["mono"]]
    wm, ww = wordmark("VAMORA75" if with_75 else "VAMORA", H=8.0)
    parts.append(affinity.translate(wm, -ww / 2, 40 / 2 + 6.0))
    if with_tagline:
        tg, (x0, y0, x1, y1) = tagline(cap=2.6)
        parts.append(affinity.translate(tg, -(x0 + x1) / 2, 40 / 2 + 6 + 8 + 6.5))
    g = unary_union(parts)
    x0, y0, x1, y1 = g.bounds
    k = width_mm / (x1 - x0)
    return centre(affinity.scale(g, k, k, origin=(0, 0)))


def badge_lockup(E: float, min_feature: float = 0.2):
    """Compact stacked lockup for the PCB and the case bottom: keycap emblem, then the
    VAMORA75 wordmark, then the trilingual tagline set to the wordmark's width.
    E = emblem size in mm; total height ~1.73 E, width ~1.95 E. Centred at (0, 0)."""
    e = emblem(E, min_feature=min_feature)
    H = E * 0.235
    wm, ww = wordmark("VAMORA75", H=H)
    y = E / 2 + 0.17 * E
    parts = [e["mono"], affinity.translate(wm, -ww / 2, y)]
    tg, (x0, y0, x1, y1) = tagline(cap=1.0)
    k = ww / (x1 - x0)
    tg = affinity.scale(tg, k, k, origin=(0, 0))
    x0, y0, x1, y1 = tg.bounds
    parts.append(affinity.translate(tg, -(x0 + x1) / 2, y + H + 0.14 * E - y0))
    return centre(unary_union(parts))


def badge_parts(E: float, min_feature: float = 0.2):
    """badge_lockup() split into colourable parts (same geometry and placement).

    Keys: outer, top, ring, star, weave (gaps of the interlace), wordmark,
    tag_vn, tag_us, tag_ma, tag_dots, mono (= badge_lockup)."""
    e = emblem(E, min_feature=min_feature)
    H = E * 0.235
    wm, ww = wordmark("VAMORA75", H=H)
    y = E / 2 + 0.17 * E
    parts = {"outer": e["outer"], "top": e["top"], "ring": e["ring"], "star": e["star"],
             "weave": e["star_silhouette"].difference(e["star"]), "wordmark": affinity.translate(wm, -ww / 2, y)}
    tp = tagline_parts(cap=1.0)
    tall = clean(unary_union(list(tp.values())))
    x0, y0, x1, y1 = tall.bounds
    k = ww / (x1 - x0)
    dx, dy = -(x0 + x1) / 2 * k, y + H + 0.14 * E - y0 * k
    for name, g in tp.items():
        parts["tag_" + name] = affinity.translate(affinity.scale(g, k, k, origin=(0, 0)), dx, dy)
    mono = clean(unary_union([e["mono"], parts["wordmark"]] + [parts["tag_" + n] for n in tp]))
    mx0, my0, mx1, my1 = mono.bounds
    cx, cy = (mx0 + mx1) / 2, (my0 + my1) / 2
    out = {n: affinity.translate(g, -cx, -cy) for n, g in parts.items()}
    out["mono"] = affinity.translate(mono, -cx, -cy)
    return out


def horizontal_lockup(height_mm: float, min_feature: float, with_75=True):
    e = emblem(40, min_feature=min_feature * 40 / height_mm)
    wm, ww = wordmark("VAMORA75" if with_75 else "VAMORA", H=14.0)
    g = unary_union([e["mono"], affinity.translate(wm, 40 / 2 + 8, -7)])
    x0, y0, x1, y1 = g.bounds
    k = height_mm / (y1 - y0)
    return centre(affinity.scale(g, k, k, origin=(0, 0)))


def min_feature_check(g, feature):
    """True if every positive part survives an opening by feature/2 (no slivers thinner than feature)."""
    g = clean(g)
    r = feature / 2 * 0.98
    lost = 0.0
    for p in polygons(g):                    # per polygon: GEOS buffers of big multipolygons can misbehave
        lost += max(p.area - p.buffer(-r).buffer(r).area, 0.0)
    return lost / max(g.area, 1e-9)


# --------------------------------------------------------------------------- export
def hole_free(g):
    """Split polygons with holes into hole-free pieces (KiCad gr_poly cannot store holes)."""
    from shapely.ops import split
    todo, out = list(polygons(g)), []
    while todo:
        p = todo.pop()
        if not p.interiors:
            out.append(p)
            continue
        hx = Polygon(p.interiors[0]).representative_point().x
        x0, y0, x1, y1 = p.bounds
        todo += [q for q in polygons(split(p, LineString([(hx, y0 - 1), (hx, y1 + 1)]))) if q.area > 1e-6]
    return out


def to_svg_path(g, fmt="{:.3f}"):
    def ring(r):
        c = list(r.coords)
        return "M" + " L".join(f"{fmt.format(x)},{fmt.format(y)}" for x, y in c[:-1]) + "Z"
    polys = [g] if isinstance(g, Polygon) else [p for p in getattr(g, "geoms", []) if isinstance(p, Polygon)]
    return " ".join(ring(p.exterior) + "".join(ring(h) for h in p.interiors) for p in polys)


def polygons(g):
    if g.is_empty:
        return []
    if isinstance(g, Polygon):
        return [g]
    out = []
    for p in getattr(g, "geoms", []):
        out += polygons(p)
    return out
