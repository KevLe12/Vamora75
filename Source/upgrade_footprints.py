"""Normalise the project footprint library with KiCad's own I/O (KiCad Python).

    "C:/Program Files/KiCad/10.0/bin/python.exe" Source/upgrade_footprints.py

* re-saves every footprint in KiCad 10 format (the ScottoKicad stabiliser footprints are
  KiCad 5 "module" files);
* stabiliser holes become plated holes with copper reinforcement rings on both sides
  (4.6 mm rings on the 3.05 mm holes, 6.0 mm on the 3.99 mm screw holes), and get B.Cu
  keep-outs 0.5 mm beyond the ring so no trace runs under a screw head or washer;
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


# Stabiliser holes are plated and carry a copper ring on both sides (exposed, gold with ENIG):
# the barrel and rings stiffen the FR4 where the screw-in stabiliser is clamped (screw head and
# washer on the back, housing on the front). Finished hole sizes stay at the Cherry values.
STAB_RING = {3.048: 4.6, 3.988: 6.0}      # finished hole (mm) -> ring diameter (mm)
KEEPOUT_EXTRA = 0.5                        # B.Cu track/via keep-out beyond the ring (screw head)


def reinforce(pad):
    """Turn a stabiliser NPTH into a plated hole with a copper ring; returns the ring diameter."""
    d = round(pcbnew.ToMM(pad.GetDrillSize().x), 3)
    ring = next(v for k, v in STAB_RING.items() if abs(k - d) < 0.01)
    pad.SetAttribute(pcbnew.PAD_ATTRIB_PTH)
    pad.SetLayerSet(pcbnew.PAD.PTHMask())
    try:
        pad.SetSize(pcbnew.F_Cu, pcbnew.VECTOR2I(MM(ring), MM(ring)))
    except TypeError:                      # older API without padstack layers
        pad.SetSize(pcbnew.VECTOR2I(MM(ring), MM(ring)))
    return ring


names = sorted(p.stem for p in Path(LIB).glob("*.kicad_mod"))
for name in names:
    fp = pcbnew.FootprintLoad(LIB, name)
    if name.startswith("Stabilizer_MX") and not any(z.GetZoneName() == "stab_screw_keepout" for z in fp.Zones()):
        for pad in list(fp.Pads()):
            c = pad.GetFPRelativePosition() if hasattr(pad, "GetFPRelativePosition") else pad.GetPos0()
            ring = reinforce(pad)
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
            r = ring / 2 + KEEPOUT_EXTRA
            for i in range(24):
                a = 2 * math.pi * i / 24
                ol.Append(c.x + MM(r * math.cos(a)), c.y + MM(r * math.sin(a)))
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
