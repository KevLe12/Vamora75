"""Assemble the Vamora75 project footprint library and 3D models.

    python Source/gen_footprints.py            (CAD venv)
    then "C:/Program Files/KiCad/10.0/bin/python.exe" Source/upgrade_footprints.py
         (re-saves every footprint in KiCad 10 format and adds stabiliser keep-outs)

Sources, copied into PCB/Vamora75.pretty and PCB/3dmodels so the project is self-contained:
  * Joe Scotto's ScottoKicad library (A:/ScottoKicad, override with VAMORA_SCOTTO):
    MX hot-swap switch footprints (Kailh CPG151101S11 socket on B.Cu, switch on top),
    PCB-mount stabiliser footprints, SOD-123 diode, HRO TYPE-C-31-M-12, 0402 R/C,
    SOT-23(-6), and their 3D models (socket, MX switch, stabilisers, USB-C, diode).
  * KiCad 10 stock libraries: RP2040 QFN-56, W25Q16 USON-8, 3225 crystal, 0603 C,
    0805 fuse, TS-1187A tact switch, test pad, fiducial.
  * One generated model (CadQuery): the TS-1187A tact switch (no stock model exists).
"""
from __future__ import annotations

import os
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "PCB" / "Vamora75.pretty"
M3D = ROOT / "PCB" / "3dmodels"
STOCK = Path(r"C:\Program Files\KiCad\10.0\share\kicad")
SCOTTO = Path(os.environ.get("VAMORA_SCOTTO", r"A:\ScottoKicad"))

SIZES = ["1.00u", "1.25u", "1.50u", "1.75u", "2.00u", "2.25u", "6.25u"]
SCOTTO_FPS = ([("ScottoKeebs_Hotswap", f"Hotswap_MX_{s}") for s in SIZES] +
              [("ScottoKeebs_Stabilizer", "Stabilizer_MX_2.00u"), ("ScottoKeebs_Stabilizer", "Stabilizer_MX_6.25u")] +
              [("ScottoKeebs_Components", n) for n in ("Diode_SOD-123", "USB_C_HRO_TYPE-C-31-M-12", "Resistor_0402",
                                                       "Capacitor_0402", "ESD_SOT-23-6", "Voltage_SOT-23")])
STOCK_FPS = {
    "Package_DFN_QFN": ["QFN-56-1EP_7x7mm_P0.4mm_EP3.2x3.2mm_ThermalVias"],
    "Package_SON": ["Winbond_USON-8-1EP_3x2mm_P0.5mm_EP0.2x1.6mm"],
    "Crystal": ["Crystal_SMD_3225-4Pin_3.2x2.5mm"],
    "Capacitor_SMD": ["C_0603_1608Metric"],
    "Fuse": ["Fuse_0805_2012Metric"],
    "Button_Switch_SMD": ["SW_Push_1P1T_XKB_TS-1187A"],
    "TestPoint": ["TestPoint_Pad_D1.0mm"],
    "Fiducial": ["Fiducial_1mm_Mask2mm"],
}
# footprints whose identically numbered pads are connected inside the part
JUMPER_FPS = {"SW_Push_1P1T_XKB_TS-1187A", "USB_C_HRO_TYPE-C-31-M-12"}
MX_SWITCH_MODEL = "MX_PCB.step"          # Scotto's 5-pin MX switch, added (visible) to every hot-swap footprint


def rewrite_models(t, wanted):
    """Point every model at ${KIPRJMOD}/3dmodels/<file> and remember which files to copy."""
    def scotto(m):
        rel = m.group(1)
        wanted.add(("scotto", rel))
        return f'(model "${{KIPRJMOD}}/3dmodels/{Path(rel).name}"'

    def stock(m):
        rel = re.sub(r"\.wrl$", ".step", m.group(2))
        wanted.add(("stock", rel))
        return f'(model "${{KIPRJMOD}}/3dmodels/{Path(rel).name}"'
    t = re.sub(r'\(model "?\$\{SCOTTOKEEBS_KICAD\}/3dmodels/([^"\s)]+)"?', scotto, t)
    t = re.sub(r'\(model "?\$\{KICAD(\d+)_3DMODEL_DIR\}/([^"\s)]+)"?', stock, t)
    return t


def copy_scotto(wanted):
    names = []
    for lib, nm in SCOTTO_FPS:
        src = SCOTTO / "footprints" / f"{lib}.pretty" / f"{nm}.kicad_mod"
        t = src.read_text(encoding="utf-8")
        t = rewrite_models(t, wanted)
        if nm == "USB_C_HRO_TYPE-C-31-M-12":
            # shield pads: S1 -> SH, the pin number used by KiCad's USB_C_Receptacle_USB2.0_16P symbol
            t = re.sub(r'\(pad "S1"', '(pad "SH"', t)
        if nm.startswith("Hotswap_MX_"):
            # also show Scotto's MX switch on the board (3D viewer, renders, PCBA STEP)
            t = t.rstrip()
            assert t.endswith(")")
            t = t[:-1] + (f'  (model "${{KIPRJMOD}}/3dmodels/{MX_SWITCH_MODEL}"\n'
                          '    (offset (xyz 0 0 0)) (scale (xyz 1 1 1)) (rotate (xyz 0 0 0)))\n)\n')
            wanted.add(("scotto", f"ScottoKeebs_MX.3dshapes/{MX_SWITCH_MODEL}"))
        (LIB / f"{nm}.kicad_mod").write_text(t, encoding="utf-8")
        names.append(nm)
    return names


def copy_stock(wanted):
    names = []
    for lib, fps in STOCK_FPS.items():
        for nm in fps:
            t = (STOCK / "footprints" / f"{lib}.pretty" / f"{nm}.kicad_mod").read_text(encoding="utf-8")
            t = rewrite_models(t, wanted)
            (LIB / f"{nm}.kicad_mod").write_text(t, encoding="utf-8")
            names.append(nm)
    return names


def copy_models(wanted):
    missing = []
    for kind, rel in sorted(wanted):
        dst = M3D / Path(rel).name
        src = (SCOTTO / "3dmodels" / rel) if kind == "scotto" else (STOCK / "3dmodels" / rel)
        if src.exists():
            shutil.copy2(src, dst)
        elif not dst.exists():
            missing.append(rel)
    return missing


def tact_switch_model():
    """XKB TS-1187A-B-A-B 5.1 x 5.1 x 1.5 mm (no model in the KiCad or Scotto libraries)."""
    import cadquery as cq

    def ky(w):          # drawn in footprint axes (Y down); model files are Y up
        return w.mirror("XZ")
    body = cq.Workplane("XY").rect(5.1, 5.1).extrude(0.95).edges("|Z").fillet(0.3)
    plate = cq.Workplane("XY").workplane(offset=0.95).rect(4.6, 4.6).extrude(0.15)
    act = cq.Workplane("XY").workplane(offset=1.1).circle(1.25).extrude(0.4)
    tl = None
    for x in (-3.0, 3.0):
        for y in (-1.875, 1.875):
            t = cq.Workplane("XY").box(1.0, 0.7, 0.2).translate((x, y, 0.1))
            tl = t if tl is None else tl.union(t)
    ts = cq.Assembly(name="TS-1187A")
    ts.add(ky(body), name="body", color=cq.Color(0.12, 0.12, 0.12))
    ts.add(ky(plate.union(tl)), name="metal", color=cq.Color(0.80, 0.80, 0.82))
    ts.add(ky(act), name="actuator", color=cq.Color(0.95, 0.95, 0.95))
    ts.export(str(M3D / "SW_Push_1P1T_XKB_TS-1187A.step"))


if __name__ == "__main__":
    if not SCOTTO.exists():
        raise SystemExit(f"ScottoKicad not found at {SCOTTO} (set VAMORA_SCOTTO)")
    LIB.mkdir(parents=True, exist_ok=True)
    M3D.mkdir(parents=True, exist_ok=True)
    for old in LIB.glob("*.kicad_mod"):
        old.unlink()
    for old in M3D.glob("*"):
        old.unlink()
    wanted = set()
    a = copy_scotto(wanted)
    b = copy_stock(wanted)
    tact_switch_model()
    missing = copy_models(wanted)
    t = (LIB / "SW_Push_1P1T_XKB_TS-1187A.kicad_mod").read_text(encoding="utf-8")
    t = re.sub(r'\(model "\$\{KIPRJMOD\}/3dmodels/[^"]+"', '(model "${KIPRJMOD}/3dmodels/SW_Push_1P1T_XKB_TS-1187A.step"', t)
    (LIB / "SW_Push_1P1T_XKB_TS-1187A.kicad_mod").write_text(t, encoding="utf-8")
    print("ScottoKicad footprints:", len(a), "| KiCad stock:", len(b), "| models:", len(list(M3D.glob("*"))))
    if missing:
        print("missing models:", missing)
