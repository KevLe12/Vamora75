"""Vamora75 FR4 gasket plate: DXF, STEP/STL and the KiCad board used to order it as a PCB.

    python Source/build_plate.py            (CAD venv: shapely, ezdxf, cadquery)
    -> Mechanical/Plate/*.dxf|.step|.stl, Plate/build/plate_plan.json
    then "C:/Program Files/KiCad/10.0/bin/python.exe" Source/kicad_plate.py builds Plate/*.kicad_pcb

Two variants: standard, and "flexcut" (relief slots behind every gasket tab).
The name "Vamora75" sits in the key-free F12-Del gap of the exploded layout, as bare copper
under an opening in the black solder mask (ENIG = gold).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from shapely import affinity
from shapely.ops import unary_union

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import vamora_layout as L  # noqa: E402
import vamora_logo as V  # noqa: E402
import vamora_mech as M  # noqa: E402

ROOT = HERE.parent
OUT_MECH = ROOT / "Mechanical" / "Plate"
OUT_PCB = ROOT / "Plate"


def c2b(g):
    """CAD (Y rear) -> board (y down) for KiCad."""
    return affinity.scale(g, 1, -1, origin=(0, M.BH / 2))


def rings(g):
    out = []
    for p in V.polygons(g):
        out.append(dict(outer=[[round(x, 4), round(y, 4)] for x, y in p.exterior.coords[:-1]],
                        holes=[[[round(x, 4), round(y, 4)] for x, y in h.coords[:-1]] for h in p.interiors]))
    return out


def artwork():
    """Plate artwork in BOARD coordinates (y down), seen from the top: the name only (rev 1.1),
    in the F12-Del gap (F12 ends at 14.5u, Del starts at 16.25u), bare copper (gold with ENIG)."""
    gx, gy = L.MARGIN + (14.5 + 16.25) / 2 * L.U, L.MARGIN + 0.5 * L.U
    copper = affinity.translate(V.name_text(26.0), gx, gy)
    from shapely.geometry import GeometryCollection
    return V.clean(copper), GeometryCollection()


def write_dxf(g, path, flex_cuts=()):
    import ezdxf
    doc = ezdxf.new("R2010")
    doc.units = 4                      # millimetres
    for name, color in (("OUTLINE", 7), ("CUTOUTS", 1), ("FLEX", 3)):
        doc.layers.add(name, color=color)
    msp = doc.modelspace()
    p = V.polygons(g)[0]
    msp.add_lwpolyline(list(p.exterior.coords)[:-1], close=True, dxfattribs={"layer": "OUTLINE"})
    flex = unary_union(list(flex_cuts)) if flex_cuts else None
    for h in p.interiors:
        layer = "FLEX" if flex is not None and flex.buffer(0.01).contains(h.centroid) else "CUTOUTS"
        msp.add_lwpolyline(list(h.coords)[:-1], close=True, dxfattribs={"layer": layer})
    assert not doc.audit().has_errors
    doc.saveas(path)


def solid(g, z0, h):
    import cadquery as cq
    p = V.polygons(g)[0]
    wp = cq.Workplane("XY").polyline(list(p.exterior.coords)[:-1]).close()
    for r in p.interiors:
        wp = wp.polyline(list(r.coords)[:-1]).close()
    return wp.extrude(h).translate((0, 0, z0))


if __name__ == "__main__":
    import cadquery as cq
    OUT_MECH.mkdir(parents=True, exist_ok=True)
    (OUT_PCB / "build").mkdir(parents=True, exist_ok=True)
    copper, silk = artwork()
    plan = dict(board=dict(w=M.BW, h=M.BH, t=M.PLATE_T), variants={})
    report = {}
    for variant, flex in (("standard", False), ("flexcut", True)):
        g = M.plate_polygon(flex)
        assert g.geom_type == "Polygon" and g.is_valid
        name = "Vamora75_plate_FR4" + ("_flexcut" if flex else "")
        write_dxf(g, OUT_MECH / f"{name}.dxf", M.flex_cuts() if flex else ())
        s = M.plate_solid(cq, flex)
        assert s.val().isValid()
        assert abs(s.val().Volume() - g.area * M.PLATE_T) < 0.002 * g.area * M.PLATE_T, "STEP and DXF disagree"
        cq.exporters.export(s, str(OUT_MECH / f"{name}.step"))
        cq.exporters.export(s, str(OUT_MECH / f"{name}.stl"), tolerance=0.05, angularTolerance=0.15)
        web, where = M.min_web(flex)
        report[variant] = dict(openings=len(g.interiors), area_mm2=round(g.area, 1), min_web_mm=round(web, 3),
                               volume_mm3=round(s.val().Volume(), 1))
        plan["variants"][variant] = dict(name=name, edge=rings(c2b(g)))
        print(f"{name}: {len(g.interiors)} openings, min web {web:.2f} mm")
    # artwork must stay clear of every opening (1 mm) - checked in board coordinates
    holes_b = c2b(unary_union([gg for _, gg in M.key_cutouts()] + M.flex_cuts()))
    for nm, art in (("copper", copper), ("silk", silk)):
        if art.is_empty:
            continue
        d = art.distance(holes_b)
        assert d > 1.0, (nm, d)
        report[f"{nm}_to_cutout_mm"] = round(d, 2)
    loss = V.min_feature_check(copper, 0.2)
    report["copper_area_below_0p2mm_pct"] = round(100 * loss, 2)
    plan["copper"] = [r for q in V.hole_free(copper) for r in rings(q)]
    plan["silk"] = [r for q in V.hole_free(silk) for r in rings(q)]
    (OUT_PCB / "build" / "plate_plan.json").write_text(json.dumps(plan), encoding="utf-8")
    (ROOT / "validation").mkdir(exist_ok=True)
    (ROOT / "validation" / "plate.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
