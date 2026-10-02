"""Vamora75 name artwork (rev 1.1: the name only, no logo): SVG / PNG / DXF + an overview sheet.

    python Source/export_artwork.py

The same geometry (vamora_logo.name_text, Segoe UI Black) is used on the PCB bottom
silkscreen, the FR4 plate and the engraved case bottom.
"""
from __future__ import annotations

import sys
from pathlib import Path

from shapely import affinity

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import vamora_logo as V  # noqa: E402

ROOT = HERE.parent
OUT = ROOT / "Artwork"
P = V.PALETTE


def svg(g, path, color, title, pad=2.0, bg=None):
    x0, y0, x1, y1 = g.bounds
    x0, y0, x1, y1 = x0 - pad, y0 - pad, x1 + pad, y1 + pad
    w, h = x1 - x0, y1 - y0
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x0:.3f} {y0:.3f} {w:.3f} {h:.3f}" '
           f'width="{w:.2f}mm" height="{h:.2f}mm">', f"<title>{title}</title>"]
    if bg:
        out.append(f'<rect x="{x0:.3f}" y="{y0:.3f}" width="{w:.3f}" height="{h:.3f}" fill="{bg}"/>')
    out.append(f'<path fill="{color}" fill-rule="evenodd" d="{V.to_svg_path(g)}"/>')
    out.append("</svg>")
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


def png(g, path, color, px=2400, pad=2.0, bg=None):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import PathPatch
    from matplotlib.path import Path as MPath
    x0, y0, x1, y1 = g.bounds
    x0, y0, x1, y1 = x0 - pad, y0 - pad, x1 + pad, y1 + pad
    w, h = x1 - x0, y1 - y0
    dpi = 200
    fig = plt.figure(figsize=(px / dpi, px * h / w / dpi), dpi=dpi)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_axis_off()
    verts, codes = [], []
    for p in V.polygons(g):
        for r in [p.exterior] + list(p.interiors):
            c = list(r.coords)
            verts += c
            codes += [MPath.MOVETO] + [MPath.LINETO] * (len(c) - 2) + [MPath.CLOSEPOLY]
    ax.add_patch(PathPatch(MPath(verts, codes), facecolor=color, edgecolor="none"))
    ax.set_xlim(x0, x1)
    ax.set_ylim(y1, y0)
    ax.set_aspect("equal")
    fig.savefig(path, dpi=dpi, transparent=bg is None, facecolor=bg or "none")
    plt.close(fig)


def dxf(g, path):
    import ezdxf
    doc = ezdxf.new("R2010")
    doc.units = 4
    msp = doc.modelspace()
    for p in V.polygons(affinity.scale(g, 1, -1, origin=(0, 0))):     # DXF is Y-up
        msp.add_lwpolyline(list(p.exterior.coords)[:-1], close=True, dxfattribs={"layer": "NAME"})
        for r in p.interiors:
            msp.add_lwpolyline(list(r.coords)[:-1], close=True, dxfattribs={"layer": "NAME"})
    assert not doc.audit().has_errors
    doc.saveas(path)


def sheet(g, path):
    """Where the name goes, in the colours of each surface."""
    from PIL import Image, ImageDraw, ImageFont
    W, Hh = 1800, 1150
    im = Image.new("RGB", (W, Hh), P["paper"])
    dr = ImageDraw.Draw(im)
    f1, f2 = ImageFont.truetype(V.SEGOE_BOLD, 40), ImageFont.truetype(V.SEGOE, 24)
    dr.text((60, 40), "Vamora75 - name artwork (rev 1.1)", font=f1, fill=P["ink"])
    dr.text((60, 100), "No logo: the name alone, set in Segoe UI Black, on the PCB, the plate and the case.", font=f2,
            fill="#4a4f5a")
    panels = [("PCB bottom - white silkscreen, 240 mm wide", "#1d3b2a", "#ffffff"),
              ("FR4 plate - gold ENIG in the F12-Del gap, 26 mm", "#16181d", P["brass"]),
              ("Case bottom - 0.6 mm engraving, 180 mm wide", "#1d2f4f", "#c9d3e3")]
    for i, (cap, bg, fg) in enumerate(panels):
        y = 170 + i * 320
        dr.rounded_rectangle((60, y, W - 60, y + 290), radius=18, fill=bg)
        tmp = ROOT / "Artwork" / "_tmp.png"
        png(g, tmp, fg, px=1300, pad=1.0)
        logo = Image.open(tmp).convert("RGBA")
        k = 200 / logo.height
        logo = logo.resize((int(logo.width * k), 200))
        im.paste(logo, ((W - logo.width) // 2, y + 30), logo)
        tmp.unlink()
        dr.text((90, y + 245), cap, font=ImageFont.truetype(V.SEGOE, 22), fill="#d7dbe2")
    im.save(path)


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    g = V.name_text(100.0)
    for stem, color, bg in (("Vamora75_name_black", P["ink"], None), ("Vamora75_name_white", "#ffffff", None),
                            ("Vamora75_name_on_navy", "#ffffff", P["navy"])):
        svg(g, OUT / f"{stem}.svg", color, "Vamora75", bg=bg)
        png(g, OUT / f"{stem}.png", color, bg=bg)
    dxf(g, OUT / "Vamora75_name_engrave.dxf")
    sheet(g, OUT / "Vamora75_name_sheet.png")
    print("artwork: name SVG/PNG (black, white, on navy), DXF, sheet")
