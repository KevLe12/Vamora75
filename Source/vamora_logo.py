"""Vamora75 name and text geometry shared by the PCB silkscreen, the plate, the case
engraving and the artwork files.

The product carries no logo, only the name "Vamora75" (Segoe UI Black, `name_text`).
`shaped_text` turns any string into outlines (HarfBuzz shaping, so the stacked diacritics
in the poem on the PCB back are placed correctly). All geometry is Shapely, millimetres,
Y axis pointing DOWN (SVG/KiCad convention); every exporter derives from the same polygons,
so the PCB, plate, case and artwork always match.
"""
from __future__ import annotations

from shapely import affinity
from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union

# Product colourway (renders, artwork): black PCB and plate, graphite case, gold (ENIG) name
PALETTE = {
    "ink": "#15171c",        # text
    "graphite": "#2b2e33",   # case
    "slate": "#5b616b",      # modifier keycaps
    "bone": "#ece8df",       # alpha keycaps
    "brass": "#c9a14a",      # accent keycaps, ENIG gold name on the plate
    "mask": "#121315",       # PCB and plate solder mask
    "paper": "#f4f1ea",      # page background
}

SEGOE = r"C:\Windows\Fonts\segoeui.ttf"
SEGOE_BOLD = r"C:\Windows\Fonts\segoeuib.ttf"
SEGOE_BLACK = r"C:\Windows\Fonts\seguibl.ttf"   # the Vamora75 name on the PCB, plate and case
NAME = "Vamora75"


def name_text(width_mm: float, font: str = SEGOE_BLACK):
    """The plain "Vamora75" name (no emblem), centred at (0, 0), scaled to `width_mm`. Y down."""
    g, _ = shaped_text(NAME, 10.0, font)
    g = centre(g)
    x0, y0, x1, y1 = g.bounds
    k = width_mm / (x1 - x0)
    return affinity.scale(g, k, k, origin=(0, 0))


# ---------------------------------------------------------------- shaped text
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
    """Shape `text` with HarfBuzz (kerning, ligatures, stacked diacritics).

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


# --------------------------------------------------------------------------- helpers
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
