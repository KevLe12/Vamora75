"""Rebuild every Vamora75 deliverable from source, then write validation/STATUS.md.

    python Source/build_all.py [--footprints] [--skip-pcb]

Order: footprints/3D models (optional) -> schematic, routing, board, DRC (build_pcb) ->
PCBA STEP -> plate (DXF/STEP + KiCad boards + DRC) -> case, assembly, checks (build_case) ->
renders -> manufacturing (Gerbers, BOM, CPL) -> firmware + tests -> artwork -> status report.
Needs the CAD venv (see requirements.txt) and KiCad 10 at C:/Program Files/KiCad/10.0.
"""
from __future__ import annotations

import collections
import datetime
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
KICAD = Path(r"C:\Program Files\KiCad\10.0\bin")
CLI, KPY, PY = str(KICAD / "kicad-cli.exe"), str(KICAD / "python.exe"), sys.executable
ENV = {**os.environ, "PYTHONIOENCODING": "utf-8"}


def run(args, quiet=False):
    print(">", " ".join(Path(str(a)).name if i < 2 else str(a) for i, a in enumerate(args[:4])), flush=True)
    r = subprocess.run([str(a) for a in args], capture_output=True, text=True, encoding="utf-8", errors="replace", env=ENV)
    if r.returncode != 0:
        print(r.stdout[-3000:], r.stderr[-3000:])
        raise SystemExit(f"FAILED: {args[:3]}")
    if not quiet:
        tail = [ln for ln in r.stdout.splitlines() if ln.strip() and not ln.startswith("  ok ")][-6:]
        print("\n".join("    " + ln for ln in tail))
    return r.stdout


def switchless_copy(src, dst):
    """A copy of the board with Scotto's MX switch model hidden (model paths made absolute)."""
    t = src.read_text(encoding="utf-8").replace("${KIPRJMOD}/3dmodels", (ROOT / "PCB" / "3dmodels").as_posix())
    t, n = re.subn(r'(\(model "[^"]*/MX_PCB\.step")', r"\1 (hide yes)", t)
    assert n == 82, f"expected 82 switch models, found {n}"
    dst.write_text(t, encoding="utf-8")
    return dst


def counts(path, key):
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    v = d.get(key, [])
    if key == "sheets":
        v = [x for s in v for x in s["violations"]]
    return dict(collections.Counter(x["type"] for x in v))


if __name__ == "__main__":
    pcb = ROOT / "PCB"
    if "--skip-pcb" not in sys.argv:
        run([PY, HERE / "build_pcb.py", pcb] + (["--footprints"] if "--footprints" in sys.argv else []))
    sys.path.insert(0, str(HERE))
    import vamora_layout as L
    origin = f"{L.PAGE_X0:g}x{L.PAGE_Y0 + L.BOARD_H:.4f}mm"       # PCB front-left corner = STEP origin
    # board with black solder mask, white silkscreen and pads, plus every 3D model (Scotto's switches too)
    step = [CLI, "pcb", "export", "step", "--force", "--user-origin", origin,
            "--include-silkscreen", "--include-soldermask", "--include-pads"]
    run(step + ["-o", ROOT / "Mechanical" / "Vamora75_PCBA.step", pcb / "Vamora75.kicad_pcb"], quiet=True)
    # the interference checks use a PCBA without Scotto's switch model (switch envelopes are checked instead)
    bare = switchless_copy(pcb / "Vamora75.kicad_pcb", pcb / "build" / "Vamora75_switchless.kicad_pcb")
    pcba_case = ROOT / "Mechanical" / "build" / "Vamora75_PCBA_switchless.step"
    pcba_case.parent.mkdir(exist_ok=True)
    run(step + ["-o", pcba_case, bare], quiet=True)
    run([PY, HERE / "build_plate.py"])
    run([KPY, HERE / "kicad_plate.py"])
    plate_drc = {}
    for f in ("Vamora75_Plate", "Vamora75_Plate_flexcut"):
        out = ROOT / "Plate" / "build" / f"{f}-drc.json"
        run([CLI, "pcb", "drc", "--severity-all", "--format", "json", "-o", out, ROOT / "Plate" / f"{f}.kicad_pcb"], quiet=True)
        plate_drc[f] = (counts(out, "violations"), counts(out, "unconnected_items"))
    run([PY, HERE / "build_case.py", pcba_case, ROOT / "Mechanical" / "Vamora75_PCBA.step"])
    run([PY, HERE / "render_previews.py"])
    build = ROOT / "Mechanical" / "build"                          # render meshes: rebuilt every run
    for f in [*build.glob("*.stl"), *build.glob("*.npz"), *build.glob("*.npy"), pcba_case]:
        f.unlink()
    # KiCad renders in the board's own colours (black mask, ENIG): pcb_top = bare front with the big
    # name, pcb_top_switches = as the 3D viewer shows it, with Scotto's switches
    render = [CLI, "pcb", "render", "--width", "2400", "--height", "1000", "--zoom", "2.3", "--quality", "high",
              "--background", "opaque", "--use-board-stackup-colors"]
    for name, side, board in (("pcb_top", "top", bare), ("pcb_top_switches", "top", pcb / "Vamora75.kicad_pcb"),
                              ("pcb_bottom", "bottom", pcb / "Vamora75.kicad_pcb"),
                              ("plate_top", "top", ROOT / "Plate" / "Vamora75_Plate.kicad_pcb")):
        run(render + ["--side", side, "-o", ROOT / "Previews" / f"{name}.png", board], quiet=True)
    for f in (bare, bare.with_suffix(".kicad_prl")):           # temporary board + the settings file kicad-cli adds
        f.unlink(missing_ok=True)
    run([PY, HERE / "export_manufacturing.py", pcb])
    run([PY, HERE / "gen_firmware.py"])
    run([PY, HERE / "export_layout.py"])
    fw = run([PY, HERE / "test_firmware.py", ROOT / "validation" / "schematic.net.xml"])
    run([PY, HERE / "export_artwork.py"])

    # ---------------------------------------------------------------- status report
    V = ROOT / "validation"
    erc = counts(V / "erc.json", "sheets")
    drc = {k: counts(V / "drc.json", k) for k in ("violations", "unconnected_items", "schematic_parity")}
    mech = json.loads((V / "mechanical.json").read_text(encoding="utf-8"))
    plate = json.loads((V / "plate.json").read_text(encoding="utf-8"))
    fwr = json.loads((V / "firmware.json").read_text(encoding="utf-8"))
    ok = lambda d: "clean" if not d else d
    lines = [
        f"# Vamora75 rev {L.REVISION} - validation status",
        "",
        f"Generated {datetime.date.today().isoformat()} by `Source/build_all.py`. These are digital checks of the",
        "design files; no board has been built or tested yet (see BUILD_GUIDE.md, bring-up).",
        "",
        "| Check | Result |",
        "|---|---|",
        f"| Schematic ERC (KiCad 10, all severities) | {ok(erc)} |",
        f"| PCB DRC violations (all severities, zones refilled) | {ok(drc['violations'])} |",
        f"| PCB unconnected items | {ok(drc['unconnected_items'])} |",
        f"| Schematic <-> PCB parity | {ok(drc['schematic_parity'])} |",
    ]
    for f, (v, u) in plate_drc.items():
        lines.append(f"| {f} DRC / unconnected | {ok(v)} / {ok(u)} |")
    lines += [
        f"| Plate min. FR4 web (switch-stab) | {plate['standard']['min_web_mm']} mm |",
        f"| Mechanical interference ({len(mech['overlap_mm3'])} pairs, incl. stabilisers through plate and foam, "
        f"keycaps bottomed out, USB-C plug) | {mech['result']} |",
        f"| PCBA bottom parts to case floor | {mech['bottom_parts_to_floor_mm']} mm |",
        f"| USB-C plug clearance in tunnel (side / vertical) | {mech['usb_tunnel']['side_clearance_mm']} / {mech['usb_tunnel']['vertical_clearance_mm']} mm |",
        f"| Firmware checks (QMK/VIA/KLE vs layout, netlist vs pins, CircuitPython HID) | "
        f"{sum(v == 'PASS' for v in fwr.values())}/{len(fwr)} pass |",
        "",
        "Not verified here: QMK compilation (no toolchain in the build environment), JLCPCB part stock and",
        "rotations in their placement preview, physical fit of printed parts, USB enumeration, typing feel.",
        "",
        "Raw reports: `erc.json`, `drc.json`, `mechanical.json`, `plate.json`, `firmware.json`, `schematic.net.xml`.",
    ]
    (V / "STATUS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    run([PY, HERE / "make_manifest.py"])
