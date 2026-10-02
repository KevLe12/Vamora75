"""Normalise the project footprint library with KiCad's own I/O (KiCad Python).

    "C:/Program Files/KiCad/10.0/bin/python.exe" Source/upgrade_footprints.py

* re-saves every footprint in KiCad 10 format (the ScottoKicad stabiliser footprints are
  KiCad 5 "module" files);
* stabiliser footprints get B.Cu keep-outs (r = 3 mm) around their holes so no trace runs
  under a stabiliser screw head or housing peg (same rule as rev 1.0);
* Joe Scotto's MX switch model stays visible on the hot-swap footprints (3D viewer, renders,
  PCBA STEP); build_all.py exports a switch-free copy of the board for the case checks;
* footprints whose same-numbered pads are internally connected are flagged as such.
"""
import math
from pathlib import Path

import pcbnew

ROOT = Path(__file__).resolve().parents[1]
LIB = str(ROOT / "PCB" / "Vamora75.pretty")
JUMPER_FPS = {"SW_Push_1P1T_XKB_TS-1187A", "USB_C_HRO_TYPE-C-31-M-12"}
MM = pcbnew.FromMM


names = sorted(p.stem for p in Path(LIB).glob("*.kicad_mod"))
for name in names:
    fp = pcbnew.FootprintLoad(LIB, name)
    if name.startswith("Stabilizer_MX"):
        for pad in list(fp.Pads()):
            c = pad.GetFPRelativePosition() if hasattr(pad, "GetFPRelativePosition") else pad.GetPos0()
            z = pcbnew.ZONE(fp)
            z.SetIsRuleArea(True)
            z.SetDoNotAllowTracks(True)
            z.SetDoNotAllowVias(True)
            z.SetDoNotAllowPads(False)
            z.SetDoNotAllowZoneFills(False)
            z.SetDoNotAllowFootprints(False)
            ls = pcbnew.LSET()
            ls.AddLayer(pcbnew.B_Cu)
            z.SetLayerSet(ls)
            z.SetZoneName("stab_screw_keepout")
            ol = z.Outline()
            ol.NewOutline()
            for i in range(24):
                a = 2 * math.pi * i / 24
                ol.Append(c.x + MM(3.0 * math.cos(a)), c.y + MM(3.0 * math.sin(a)))
            fp.Add(z)
    if name in JUMPER_FPS:
        fp.SetDuplicatePadNumbersAreJumpers(True)
    pcbnew.FootprintSave(LIB, fp)
    f = Path(LIB) / f"{name}.kicad_mod"
    t = f.read_text(encoding="utf-8")
    key = '(model "${KIPRJMOD}/3dmodels/MX_PCB.step"\n'
    hidden = key + '\t\t(hide yes)\n'
    if hidden in t:                       # early rev 1.1 hid the switch; Models() is a copy in Python
        f.write_text(t.replace(hidden, key), encoding="utf-8")
print("normalised", len(names), "footprints")
