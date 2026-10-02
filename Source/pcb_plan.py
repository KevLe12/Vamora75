"""Vamora75 PCB placement plan (board-local mm, origin = PCB rear-left corner, Y toward the user).

All components are on the BOTTOM side (single-sided assembly). The plan is consumed by
route_board.py (routing) and kicad_build.py (pcbnew board assembly).
"""
from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path

import vamora_layout as L
import kicad_fp

ROOT = Path(__file__).resolve().parents[1]

# ---------------------------------------------------------------- key matrix
DIODE_DX, DIODE_DY = 8.9, -0.9          # diode centre relative to switch centre (vertical, anode north)
COLVIA_DX, COLVIA_DY = -7.085, -0.85    # column via relative to switch centre (just south of Kailh pad 1)
ROWLINE_DY = 3.0                        # row trace y offset below the switch centre


def matrix_placement():
    pl = {}
    for k in L.keys():
        # ScottoKicad hot-swap footprint: placed on the TOP side (switch), Kailh socket pads on B.Cu
        pl[k["ref"]] = dict(fp=f"Hotswap_MX_{L.fp_size_name(k['w'])}", x=k["bx"], y=k["by"], phi=0, bottom=False)
        pl[k["diode"]] = dict(fp="Diode_SOD-123", x=k["bx"] + DIODE_DX, y=k["by"] + DIODE_DY, phi=270, bottom=True)
    return pl


def stab_placement():
    """PCB-mount stabilisers (ScottoKicad footprints, board-only: holes + keep-outs)."""
    pl, n = {}, 0
    for k in L.keys():
        if k["w"] in L.STAB_SPACING:
            n += 1
            fp = "Stabilizer_MX_6.25u" if k["w"] == 6.25 else "Stabilizer_MX_2.00u"
            pl[f"ST{n}"] = dict(fp=fp, x=k["bx"], y=k["by"], phi=0, bottom=False, key=k["label"])
    return pl


# ---------------------------------------------------------------- controller area (F12-Del gap)
MX, MY = 296.5, 25.6          # RP2040 centre
J1X = 296.5                   # USB-C centre (rear edge)
ROW0_Y = L.MARGIN + 0.5 * L.U + ROWLINE_DY      # 15.525
HOP_W, HOP_E = 280.7, 312.4                     # row-0 line hops to F.Cu between these x
# Rule areas where the KiCad custom DRC rule allows 0.15 mm clearance (fine-pitch fan-outs).
FANOUT_AREAS = {
    "FANOUT_USB": (292.6, 6.6, 300.6, 15.3),
    "FANOUT_QSPI": (296.4, 16.0, 305.0, 22.4),
    "FANOUT_QFN": (MX - 4.7, MY - 4.7, MX + 4.7, MY + 4.7),
}


def mcu_placement():
    p = {}
    def put(ref, fp, x, y, phi=0):
        p[ref] = dict(fp=fp, x=x, y=y, phi=phi, bottom=True)
    R0402, C0402, C0603 = "Resistor_0402", "Capacitor_0402", "C_0603_1608Metric"
    # USB-C, CC, ESD, fuse (north of the row-0 hop)
    put("J1", "USB_C_HRO_TYPE-C-31-M-12", J1X, 3.65, 180)
    put("U2", "ESD_SOT-23-6", 296.5, 12.7, 90)
    put("R1", R0402, 293.2, 11.6, 90)        # CC1 5k1
    put("R2", R0402, 299.9, 11.8, 90)        # CC2 5k1
    put("F1", "Fuse_0805_2012Metric", 290.6, 11.6, 90)
    put("TP4", "TestPoint_Pad_D1.0mm", 288.0, 11.6)        # +5V
    # USB series resistors (south of the hop), connector side north
    put("R4", R0402, 295.4, 17.3, 270)       # D- 27R
    put("R3", R0402, 296.6, 17.3, 270)       # D+ 27R
    # LDO + bulk caps next to the RP2040 +3V3 corner
    put("C1", C0603, 285.1, 17.9, 90)        # +5V in
    put("U3", "Voltage_SOT-23", 287.9, 17.9, 0)      # XC6206 LDO
    put("C2", C0603, 290.7, 17.9, 270)       # +3V3 out
    put("C13", C0402, 291.4, 20.6, 270)      # VREG_VIN 1u
    put("C10", C0402, 292.5, 20.6, 270)      # ADC_AVDD
    put("C7", C0402, 290.3, 20.6, 270)       # IOVDD 42
    put("C14", C0402, 294.35, 20.4, 270)     # VREG_VOUT 1u (+1V1)
    put("C9", C0402, 296.35, 20.4, 270)      # USB_VDD 48 / IOVDD 49
    # RP2040, flash
    put("U1", "QFN-56-1EP_7x7mm_P0.4mm_EP3.2x3.2mm_ThermalVias", MX, MY, 0)
    put("U4", "Winbond_USON-8-1EP_3x2mm_P0.5mm_EP0.2x1.6mm", 301.6, 18.7, 0)
    put("C15", C0402, 299.3, 16.6, 0)        # flash VCC
    put("R5", R0402, 306.4, 17.6, 0)         # SS pull-up (SS pad west)
    put("R6", R0402, 306.4, 18.9, 180)       # SS -> BOOTSEL 1k (SS pad west)
    put("SW90", "SW_Push_1P1T_XKB_TS-1187A", 307.3, 11.6, 180)   # BOOT
    put("C3", C0402, 301.7, 22.3, 180)       # IOVDD 1
    put("C4", C0402, 303.8, 22.3, 0)         # IOVDD 10 (fed through F.Cu); GND pads face C3
    put("C6", C0402, 289.9, 30.6, 0)         # IOVDD 33 (fed through F.Cu)
    # south: DVDD / IOVDD 22, crystal
    put("C12", C0402, 303.6, 31.4, 0)        # +1V1 bulk (fed through F.Cu)
    put("C11", C0402, 295.35, 31.6, 90)      # DVDD 23
    put("C5", C0402, 296.3, 31.45, 90)       # IOVDD 22
    put("R8", R0402, 297.4, 31.8, 90)        # XOUT series 1k
    put("Y1", "Crystal_SMD_3225-4Pin_3.2x2.5mm", 298.6, 34.8, 0)
    put("C17", C0402, 295.3, 33.9, 0)        # XTAL_OUT load
    put("C16", C0402, 301.8, 35.65, 180)     # XIN load
    # reset + test pads
    put("R7", R0402, 293.6, 33.4, 90)        # RUN pull-up
    put("TP1", "TestPoint_Pad_D1.0mm", 293.9, 35.9)        # RUN
    put("SW91", "SW_Push_1P1T_XKB_TS-1187A", 288.8, 39.8, 0)   # RESET
    put("TP2", "TestPoint_Pad_D1.0mm", 299.0, 40.8)        # +3V3
    put("TP3", "TestPoint_Pad_D1.0mm", 301.0, 40.8)        # GND
    return p


def placement():
    p = matrix_placement()
    p.update(mcu_placement())
    p.update(stab_placement())
    return p


def netlist(path):
    root = ET.parse(path).getroot()
    nets = {}
    for n in root.findall("./nets/net"):
        name = n.get("name")
        for node in n.findall("node"):
            nets[(node.get("ref"), node.get("pin"))] = name
    comps = {}
    for c in root.findall("./components/comp"):
        fields = {f.get("name"): (f.text or "") for f in c.findall("./fields/field")}
        comps[c.get("ref")] = dict(value=c.findtext("value"), footprint=c.findtext("footprint"),
                                   tstamp=(c.findtext("tstamps") or "").strip(), fields=fields)
    return nets, comps


def all_pads(pl, nets):
    pads, keepouts, courts = [], [], {}
    for ref, q in pl.items():
        pp, ko, court = kicad_fp.placed_pads(q["fp"], q["x"], q["y"], q["phi"], q["bottom"])
        for p in pp:
            p["ref"] = ref
            p["net"] = nets.get((ref, p["num"])) if p["num"] else None
            pads.append(p)
        for k in ko:
            k["ref"] = ref
            keepouts.append(k)
        courts[ref] = court
    return pads, keepouts, courts
