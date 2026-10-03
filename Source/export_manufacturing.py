"""Fabrication and assembly outputs (JLCPCB-ready) for the main PCB and the FR4 plates.

    python Source/export_manufacturing.py [PCB project dir]      (default: PCB/)

Manufacturing/PCB/    Gerbers + Excellon (zip), JLCPCB BOM + CPL, drill map, schematic PDF,
                      bottom assembly drawing PDF, PCBA STEP
Manufacturing/Plate/  Gerber zips for the standard and flex-cut FR4 plates
Manufacturing/Vamora75_kit_BOM.csv   everything needed to build one keyboard
"""
from __future__ import annotations

import csv
import io
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pcb_plan as P  # noqa: E402
import vamora_layout as L  # noqa: E402
import vamora_mech as M  # noqa: E402

ROOT = HERE.parent
PCB = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "PCB"
OUT = ROOT / "Manufacturing"
CLI = r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe"
LAYERS = "F.Cu,B.Cu,F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts"
SOCKET_CENTROID = (-0.62, -3.81)      # Kailh body centre vs. switch centre (board view, y down)


def run(*args):
    r = subprocess.run([CLI, *map(str, args)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise SystemExit(f"kicad-cli failed: {args[:3]}\n{r.stdout[-2000:]}\n{r.stderr[-2000:]}")
    return r.stdout


def gerbers(board, outdir, zip_path, layers=LAYERS):
    if outdir.exists():
        shutil.rmtree(outdir)
    outdir.mkdir(parents=True)
    run("pcb", "export", "gerbers", "--layers", layers, "--subtract-soldermask", "-o", outdir, board)
    run("pcb", "export", "drill", "--format", "excellon", "--excellon-units", "mm", "--excellon-separate-th",
        "--generate-map", "--map-format", "gerberx2", "-o", outdir, board)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(outdir.iterdir()):
            z.write(f, f.name)
    return sorted(f.name for f in outdir.iterdir())


def main_pcb():
    board = PCB / "Vamora75.kicad_pcb"
    sch = PCB / "Vamora75.kicad_sch"
    out = OUT / "PCB"
    out.mkdir(parents=True, exist_ok=True)
    files = gerbers(board, out / "gerbers", out / "Vamora75_gerbers_JLCPCB.zip")
    print("gerbers:", len(files), "files")
    run("sch", "export", "pdf", "-o", out / "Vamora75_schematic.pdf", sch)
    run("pcb", "export", "pdf", "--layers", "B.Fab,B.SilkS,Edge.Cuts", "--mirror", "--include-border-title",
        "--mode-single", "-o", out / "Vamora75_assembly_bottom.pdf", board)
    # ---------------- BOM (JLCPCB format) from the netlist written by the schematic
    netxml = PCB / "build" / "Vamora75.net.xml"
    if not netxml.exists():
        run("sch", "export", "netlist", "--format", "kicadxml", "-o", netxml, sch)
    _, comps = P.netlist(netxml)
    groups = {}
    for ref, c in comps.items():
        f = c["fields"]
        lcsc = f.get("LCSC", "")
        if not lcsc:                     # test pads, not assembled
            continue
        fp = c["footprint"].split(":", 1)[1]
        if fp.startswith("Hotswap_MX"):
            comment, fp = "Kailh CPG151101S11 MX hot-swap socket", "Kailh_CPG151101S11"
        else:
            comment = f"{c['value']} {f.get('MPN', '')}".strip() if c["value"] not in f.get("MPN", "") else f.get("MPN", c["value"])
        groups.setdefault((comment, fp, lcsc), []).append(ref)
    key = lambda r: (''.join(ch for ch in r if ch.isalpha()), int(''.join(ch for ch in r if ch.isdigit()) or 0))
    with open(out / "Vamora75_BOM_JLCPCB.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #", "Quantity"])
        for (comment, fp, lcsc), refs in sorted(groups.items(), key=lambda kv: key(sorted(kv[1], key=key)[0])):
            refs = sorted(refs, key=key)
            w.writerow([comment, ",".join(refs), fp, lcsc, len(refs)])
    n_parts = sum(len(v) for v in groups.values())
    print("BOM:", len(groups), "lines,", n_parts, "placements")
    # ---------------- CPL from KiCad's own position export (drill/aux origin = board lower-left)
    raw = run("pcb", "export", "pos", "--side", "both", "--format", "csv", "--units", "mm",
              "--use-drill-file-origin", "--exclude-dnp", "-o", out / "_pos_raw.csv", board)
    rows = list(csv.DictReader(open(out / "_pos_raw.csv", encoding="utf-8")))
    (out / "_pos_raw.csv").unlink()
    with open(out / "Vamora75_CPL_JLCPCB.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        placed = 0
        for r in sorted(rows, key=lambda r: key(r["Ref"])):
            ref = r["Ref"]
            if ref.startswith(("TP", "FID")) or not any(ref in g for g in groups.values()):
                continue
            x, y, rot = float(r["PosX"]), float(r["PosY"]), float(r["Rot"])
            side = "Bottom" if r["Side"].lower().startswith("b") else "Top"
            if r["Package"].startswith("Hotswap_MX"):
                # ScottoKicad switch footprints sit on the top layer, but the Kailh socket they carry is a
                # bottom-side part: report it at the socket body centre, bottom side, as a flipped part (180)
                x, y = x + SOCKET_CENTROID[0], y - SOCKET_CENTROID[1]     # pos file is Y-up
                side, rot = "Bottom", (rot + 180) % 360
            w.writerow([ref, f"{x:.4f}mm", f"{y:.4f}mm", side, f"{rot:g}"])
            placed += 1
    print("CPL:", placed, "placements")
    assert placed == n_parts, (placed, n_parts)
    return n_parts


def plates():
    out = OUT / "Plate"
    out.mkdir(parents=True, exist_ok=True)
    for name in ("Vamora75_Plate", "Vamora75_Plate_flexcut"):
        board = ROOT / "Plate" / f"{name}.kicad_pcb"
        gerbers(board, out / f"{name}_gerbers", out / f"{name}_gerbers.zip",
                layers="F.Cu,B.Cu,F.SilkS,F.Mask,B.Mask,Edge.Cuts")
        shutil.rmtree(out / f"{name}_gerbers")
        print("plate gerbers:", name)


KIT = [  # item, qty, spec, source / notes
    ("PCBA (this design)", 1, "2-layer FR4 1.6 mm, black mask, ENIG, bottom-side SMT assembled", "Manufacturing/PCB - JLCPCB/PCBWay"),
    ("FR4 plate", 1, "1.5 mm (1.6 mm fits), black mask, ENIG for the gold name", "Manufacturing/Plate - any PCB fab"),
    ("Case top", 1, "PETG/ASA print or CNC 6061", "Mechanical/Case"),
    ("Case bottom", 1, "PETG/ASA print or CNC 6061 (solid wedge, 6 deg)", "Mechanical/Case"),
    ("MX-compatible switches", 82, "3-pin or 5-pin", "user choice"),
    ("Keycaps", 82, "1u x 71, 1.25u x 3, 1.5u x 2, 1.75u x 2, 2u x 1, 2.25u x 2, 6.25u x 1", "any MX set with 75 % kit"),
    ("PCB-mount screw-in stabilisers", 4, "3 x 2u (Backspace, Enter, LShift) + 1 x 6.25u (Space)", "Durock/Cherry/TX"),
    ("Gaskets", 16, f"{M.GASKET_W:g} x {M.GASKET_D:g} x {M.GASKET_T:g} mm Poron 4701-50 or 40A silicone", "Mechanical/Soft DXF"),
    ("Case foam", 1, "3 mm PE / Poron", "Mechanical/Soft DXF"),
    ("Plate foam (optional)", 1, "3.5 mm Poron / PE, with stabiliser/wire windows", "Mechanical/Soft DXF"),
    ("Screws", 8, M.SCREW["name"], ""),
    ("Heat-set inserts", 8, M.SCREW["insert"] + " (printed top case; tap M3 if CNC)", ""),
    ("Dowel pins (split print only)", 5, M.DOWEL["pin"], "only for the 4-piece printed case"),
    ("Bumpers", 4, M.FEET["bumper"], ""),
    ("USB-C cable", 1, "overmould <= 12.3 x 6.5 mm", ""),
]


def kit_bom(n_smt):
    with open(OUT / "Vamora75_kit_BOM.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Item", "Qty", "Specification", "Source / file"])
        for row in KIT:
            w.writerow(row)
    print("kit BOM:", len(KIT), "lines (PCBA has", n_smt, "SMT placements)")


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    n = main_pcb()
    plates()
    kit_bom(n)
