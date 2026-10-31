"""One-shot PCB pipeline: schematic -> ERC -> netlist -> routing -> board -> zone refill -> DRC.

    python Source/build_pcb.py [output PCB dir] [--footprints]

Requires the CAD venv (CadQuery/Shapely/SciPy) for this script and KiCad 10 installed at
C:/Program Files/KiCad/10.0 (kicad-cli + KiCad's Python for pcbnew).
"""
from __future__ import annotations

import collections
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else ROOT / "PCB"
KICAD = Path(r"C:\Program Files\KiCad\10.0\bin")
CLI, KPY = str(KICAD / "kicad-cli.exe"), str(KICAD / "python.exe")
PY = sys.executable


def run(args, **kw):
    print(">", " ".join(str(a) for a in args[:4]), "...", flush=True)
    r = subprocess.run([str(a) for a in args], capture_output=True, text=True, encoding="utf-8", errors="replace", **kw)
    if r.returncode != 0:
        print(r.stdout[-3000:], r.stderr[-3000:])
        raise SystemExit(f"step failed: {args[:3]}")
    return r.stdout


def summary(path, keys):
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    out = {}
    for k in keys:
        v = d.get(k, [])
        if k == "sheets":
            v = [x for s in v for x in s["violations"]]
        out[k] = collections.Counter((x["type"], x["severity"]) for x in v)
    return d, out


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    B = OUT / "build"
    B.mkdir(exist_ok=True)
    if "--footprints" in sys.argv:
        run([PY, HERE / "gen_footprints.py"])
        run([KPY, HERE / "upgrade_footprints.py"])
    run([PY, HERE / "gen_schematic.py", OUT])
    run([PY, HERE / "gen_project.py", OUT])
    if OUT.resolve() != (ROOT / "PCB").resolve():
        for d in ("Vamora75.pretty", "3dmodels"):
            if (OUT / d).exists():
                shutil.rmtree(OUT / d)
            shutil.copytree(ROOT / "PCB" / d, OUT / d)
    run([CLI, "sch", "erc", "--format", "json", "--severity-all", "-o", B / "erc.json", OUT / "Vamora75.kicad_sch"])
    run([CLI, "sch", "export", "netlist", "--format", "kicadxml", "-o", B / "Vamora75.net.xml", OUT / "Vamora75.kicad_sch"])
    print(run([PY, HERE / "route_board.py", OUT])[-400:])
    print(run([PY, HERE / "check_connectivity.py", OUT, "--clearance"])[-1500:])
    print(run([PY, HERE / "make_board_plan.py", OUT]))
    print(run([KPY, HERE / "kicad_build.py", OUT]))
    # silkscreen artwork (front name, back poem and labels) is fitted around the finished board's pads, holes and legends
    print(run([KPY, HERE / "extract_obstacles.py", OUT]))
    print(run([PY, HERE / "gen_artwork.py", OUT], env={**os.environ, "PYTHONIOENCODING": "utf-8"}))
    print(run([PY, HERE / "make_board_plan.py", OUT]))
    print(run([KPY, HERE / "kicad_build.py", OUT]))
    run([CLI, "pcb", "drc", "--schematic-parity", "--severity-all", "--refill-zones", "--save-board",
         "--format", "json", "-o", B / "drc.json", OUT / "Vamora75.kicad_pcb"])
    _, erc = summary(B / "erc.json", ["sheets"])
    d, drc = summary(B / "drc.json", ["violations", "unconnected_items", "schematic_parity"])
    print("ERC:", dict(erc["sheets"]) or "clean")
    for k, v in drc.items():
        print(f"DRC {k}:", dict(v) or "clean")
    if OUT.resolve() == (ROOT / "PCB").resolve():          # publish the reports next to the other checks
        V = ROOT / "validation"
        V.mkdir(exist_ok=True)
        shutil.copy(B / "erc.json", V / "erc.json")
        shutil.copy(B / "drc.json", V / "drc.json")
        shutil.copy(B / "Vamora75.net.xml", V / "schematic.net.xml")
