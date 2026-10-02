"""Generate the Vamora75 rev 1.1 schematic and project symbol library (KiCad 10).

    python Source/gen_schematic.py [output_dir]

Circuit: RP2040 minimal design (Raspberry Pi "Hardware design with RP2040"),
USB-C (HRO TYPE-C-31-M-12) with CC pull-downs, USBLC6-2SC6 ESD, 500 mA PTC,
XC6206 3.3 V LDO, W25Q128JV QSPI flash, ABM8-272-T3 12 MHz crystal (15 pF, 1 k
series on XOUT), BOOT/RESET buttons, SWD test pads, and an 82-key 6x16 COL2ROW
matrix of Kailh CPG151101S11 hot-swap sockets with 1N4148W diodes.
"""
from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import sexp  # noqa: E402
from sexp import Sym as S  # noqa: E402
import vamora_layout as L  # noqa: E402

ROOT = HERE.parent
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "PCB"
STOCK = Path(r"C:\Program Files\KiCad\10.0\share\kicad\symbols")
LIBNAME = "Vamora75"
NS = uuid.UUID("0f6b4a2c-3a1e-4f39-9a6e-7a3c5d75a075")
SCH_UUID = str(uuid.uuid5(NS, "schematic-root"))
VERSION = 20251024


def uid(*p):
    return str(uuid.uuid5(NS, "/".join(map(str, p))))


# ------------------------------------------------------------------ symbol library
NEEDED = {
    "Device": ["R", "C", "D", "Polyfuse", "Crystal_GND24"],
    "Switch": ["SW_Push"],
    "Connector": ["USB_C_Receptacle_USB2.0_16P", "TestPoint"],
    "MCU_RaspberryPi": ["RP2040"],
    "Memory_Flash": ["W25Q32JVZP"],
    "Power_Protection": ["USBLC6-2SC6"],
    "Regulator_Linear": ["XC6206PxxxMR"],
    "power": ["GND", "+3V3", "+5V", "+1V1", "VBUS", "PWR_FLAG"],
}


def load_lib(name):
    return sexp.loads((STOCK / f"{name}.kicad_sym").read_text(encoding="utf-8"))


def flatten(lib, name):
    sym = next(x for x in sexp.findall(lib, "symbol") if x[1] == name)
    ext = sexp.find(sym, "extends")
    if not ext:
        return [x if not (isinstance(x, list) and x and x[0] == "symbol") else x for x in sym]
    parent = flatten(lib, ext[1])
    pname = parent[1]
    out = ["symbol", name]
    child_props = {p[1]: p for p in sexp.findall(sym, "property")}
    for x in parent[2:]:
        if isinstance(x, list) and x and x[0] == "property":
            out.append(child_props.pop(x[1], x))
        elif isinstance(x, list) and x and x[0] == "symbol":
            unit = list(x)
            unit[1] = unit[1].replace(pname, name, 1)
            out.append(unit)
        else:
            out.append(x)
    for p in child_props.values():
        out.insert(len([y for y in out if not (isinstance(y, list) and y[0] == "symbol")]), p)
    return out


SYMS = {}
for libname, names in NEEDED.items():
    lib = load_lib(libname)
    for nm in names:
        SYMS[nm] = flatten(lib, nm)
# W25Q16JVUXIQ (USON-8 2x3, as on the Raspberry Pi Pico) shares the W25Q32JVZP pinout incl. EP
_f = [x for x in SYMS.pop("W25Q32JVZP")]
_f[1] = "W25Q16JVUXIQ"
for _x in _f:
    if isinstance(_x, list) and _x and _x[0] == "symbol":
        _x[1] = _x[1].replace("W25Q32JVZP", "W25Q16JVUXIQ")
    if isinstance(_x, list) and _x and _x[0] == "property":
        if _x[1] == "Value":
            _x[2] = "W25Q16JVUXIQ"
        elif _x[1] == "Footprint":
            _x[2] = "Package_SON:Winbond_USON-8-1EP_3x2mm_P0.5mm_EP0.2x1.6mm"
        elif _x[1] == "Datasheet":
            _x[2] = "https://www.winbond.com/resource-files/w25q16jv%20spi%20revh%2005182017%20sfdp.pdf"
SYMS["W25Q16JVUXIQ"] = _f


def pins_of(sym):
    """{number: (x, y, angle, name, type)} in symbol (Y-up) coordinates."""
    out = {}

    def walk(o):
        if isinstance(o, list):
            if o and o[0] == "pin":
                at = sexp.find(o, "at")
                nm = sexp.find(o, "name")[1]
                num = sexp.find(o, "number")[1]
                out.setdefault(num, (at[1], at[2], at[3], nm, str(o[1])))
            for z in o:
                walk(z)
    walk(sym)
    return out


PINS = {k: pins_of(v) for k, v in SYMS.items()}


def xform(px, py, ang):
    return {0: (px, -py), 90: (-py, -px), 180: (-px, py), 270: (py, px)}[ang]


# ------------------------------------------------------------------ schematic model
class Sch:
    def __init__(self):
        self.items = []
        self.symbols_used = set()
        self.pwr = 0
        self.comps = []      # for BOM/netplan
        self.done = set()
        self.netplan = {}    # (ref, pin) -> net

    def place(self, sym, ref, value, x, y, ang=0, fp="", lcsc="", mpn="", desc="", extra=None, hide_value=False,
              datasheet="", in_bom=True):
        self.symbols_used.add(sym)
        pins = PINS[sym]
        props = [("Reference", ref, (x + 2.54, y - 3.0), False), ("Value", value, (x + 2.54, y + 3.0), hide_value),
                 ("Footprint", fp, (x, y), True), ("Datasheet", datasheet, (x, y), True), ("Description", desc, (x, y), True)]
        if lcsc:
            props.append(("LCSC", lcsc, (x, y), True))
        if mpn:
            props.append(("MPN", mpn, (x, y), True))
        for k, v in (extra or {}).items():
            props.append((k, v, (x, y), True))
        e = ["symbol", ["lib_id", f"{LIBNAME}:{sym}"], ["at", x, y, ang], ["unit", 1], ["body_style", 1],
             ["exclude_from_sim", S("no")], ["in_bom", S("no" if (ref.startswith("#") or not in_bom) else "yes")],
             ["on_board", S("no" if ref.startswith("#") else "yes")], ["dnp", S("no")], ["uuid", uid("sym", ref)]]
        for k, v, (tx, ty), hide in props:
            pe = ["property", k, v, ["at", tx, ty, 0]]
            if hide:
                pe.append(["hide", S("yes")])
            pe.append(["effects", ["font", ["size", 1.27, 1.27]], ["justify", S("left")]])
            e.append(pe)
        for num in pins:
            e.append(["pin", num, ["uuid", uid("pin", ref, num)]])
        e.append(["instances", ["project", LIBNAME, ["path", "/" + SCH_UUID, ["reference", ref], ["unit", 1]]]])
        self.items.append(e)
        if not ref.startswith("#"):
            self.comps.append(dict(ref=ref, value=value, footprint=fp, lcsc=lcsc, mpn=mpn, symbol=sym, desc=desc))
        return {num: (x + xform(p[0], p[1], ang)[0], y + xform(p[0], p[1], ang)[1], p) for num, p in pins.items()}

    def pin_dir(self, p, ang):
        """Outward direction (angle where a label should point) for a pin."""
        pa = (p[2] + ang) % 360
        # pin angle = direction from connection point toward body; label goes opposite
        return {0: 180, 90: 270, 180: 0, 270: 90}[pa]

    def label(self, name, xy, direction=0, ref=None, pin=None):
        x, y = xy
        just = {0: "left", 180: "right", 90: "left", 270: "right"}[direction]
        ang = {0: 0, 180: 0, 90: 90, 270: 90}[direction]
        self.items.append(["label", name, ["at", x, y, ang], ["fields_autoplaced", S("yes")],
                           ["effects", ["font", ["size", 1.27, 1.27]], ["justify", S(just), S("bottom")]],
                           ["uuid", uid("lbl", name, round(x, 3), round(y, 3))]])
        if ref:
            self.netplan[(ref, pin)] = name

    def pinlabel(self, placed, ref, num, name, ang=0):
        x, y, p = placed[num]
        d = self.pin_dir(p, ang)
        self.netplan[(ref, num)] = name
        key = (name, round(x, 3), round(y, 3))
        if key in self.done:
            return
        self.done.add(key)
        if name in POWER_NETS:
            # GND-style symbols draw downward at rotation 0, supply symbols upward
            rot = (d + 90) % 360 if name == "GND" else (d - 90) % 360
            self.power(name, (x, y), rot=rot)
        else:
            self.label(name, (x, y), d)

    def power(self, kind, xy, ref_for=None, pin=None, rot=0):
        self.pwr += 1
        sym = kind
        r = f"#{'FLG' if kind == 'PWR_FLAG' else 'PWR'}{self.pwr:03d}"
        self.place(sym, r, kind, xy[0], xy[1], rot, hide_value=(kind == "PWR_FLAG"))
        if ref_for:
            self.netplan[(ref_for, pin)] = kind

    def nc(self, xy):
        self.items.append(["no_connect", ["at", xy[0], xy[1]], ["uuid", uid("nc", round(xy[0], 3), round(xy[1], 3))]])

    def wire(self, a, b):
        self.items.append(["wire", ["pts", ["xy", a[0], a[1]], ["xy", b[0], b[1]]],
                           ["stroke", ["width", 0], ["type", S("default")]], ["uuid", uid("w", a, b)]])

    def text(self, t, x, y, size=1.8, bold=False):
        fnt = ["font", ["size", size, size]] + ([["bold", S("yes")]] if bold else [])
        self.items.append(["text", t, ["exclude_from_sim", S("no")], ["at", x, y, 0],
                           ["effects", fnt, ["justify", S("left"), S("bottom")]], ["uuid", uid("txt", t[:40], x, y)]])

    def box(self, x0, y0, x1, y1):
        self.items.append(["rectangle", ["start", x0, y0], ["end", x1, y1],
                           ["stroke", ["width", 0.3], ["type", S("dash")]], ["fill", ["type", S("none")]],
                           ["uuid", uid("rect", x0, y0)]])


POWER_NETS = {"GND", "+3V3", "+5V", "+1V1", "VBUS"}


def g(v):
    """snap to 1.27 mm grid"""
    return round(v / 1.27) * 1.27


FP = {
    "R0402": f"{LIBNAME}:Resistor_0402", "C0402": f"{LIBNAME}:Capacitor_0402",
    "C0603": f"{LIBNAME}:C_0603_1608Metric", "D": f"{LIBNAME}:Diode_SOD-123",
    "QFN": f"{LIBNAME}:QFN-56-1EP_7x7mm_P0.4mm_EP3.2x3.2mm_ThermalVias",
    "USON8": f"{LIBNAME}:Winbond_USON-8-1EP_3x2mm_P0.5mm_EP0.2x1.6mm",
    "USBC": f"{LIBNAME}:USB_C_HRO_TYPE-C-31-M-12", "SOIC8": f"{LIBNAME}:SOIC-8_5.3x5.3mm_P1.27mm",
    "XTAL": f"{LIBNAME}:Crystal_SMD_3225-4Pin_3.2x2.5mm", "SOT23": f"{LIBNAME}:Voltage_SOT-23", "SOT23-6": f"{LIBNAME}:ESD_SOT-23-6",
    "FUSE": f"{LIBNAME}:Fuse_0805_2012Metric", "BTN": f"{LIBNAME}:SW_Push_1P1T_XKB_TS-1187A",
    "TP": f"{LIBNAME}:TestPoint_Pad_D1.0mm",
}


def build():
    s = Sch()
    # ---------------------------------------------------------------- titles / frames
    s.box(25, 25, 245, 225)
    s.text("USB-C · protection · 3.3 V supply", 30, 33, 3, True)
    s.box(255, 25, 815, 270)
    s.text("RP2040 · 2 MB QSPI flash · 12 MHz crystal · boot/reset · SWD", 260, 33, 3, True)
    s.box(25, 280, 815, 575)
    s.text("Key matrix · 82 × Kailh CPG151101S11 hot-swap sockets · 1N4148W · 6 rows × 16 columns · COL2ROW", 30, 288, 3, True)

    # ---------------------------------------------------------------- USB-C
    j1 = s.place("USB_C_Receptacle_USB2.0_16P", "J1", "TYPE-C-31-M-12", g(60), g(110), 0, FP["USBC"], "C165948",
                 "HRO TYPE-C-31-M-12", "USB-C receptacle, USB 2.0, 16 pin, bottom-side mounted at rear edge")
    for num in ("A4", "A9", "B4", "B9"):
        s.pinlabel(j1, "J1", num, "VBUS")
    s.pinlabel(j1, "J1", "A5", "CC1")
    s.pinlabel(j1, "J1", "B5", "CC2")
    s.pinlabel(j1, "J1", "A6", "USB_D+")
    s.pinlabel(j1, "J1", "B6", "USB_D+")
    s.pinlabel(j1, "J1", "A7", "USB_D-")
    s.pinlabel(j1, "J1", "B7", "USB_D-")
    s.nc(j1["A8"][:2])
    s.nc(j1["B8"][:2])
    for num in ("A1", "A12", "B1", "B12"):
        s.pinlabel(j1, "J1", num, "GND")
    s.pinlabel(j1, "J1", "SH", "GND")

    r1 = s.place("R", "R1", "5.1k", g(110), g(100), 0, FP["R0402"], "C25905", "0402WGF5101TCE", "USB-C CC1 pull-down (sink)")
    s.pinlabel(r1, "R1", "1", "CC1")
    s.pinlabel(r1, "R1", "2", "GND")
    r2 = s.place("R", "R2", "5.1k", g(125), g(100), 0, FP["R0402"], "C25905", "0402WGF5101TCE", "USB-C CC2 pull-down (sink)")
    s.pinlabel(r2, "R2", "1", "CC2")
    s.pinlabel(r2, "R2", "2", "GND")

    u2 = s.place("USBLC6-2SC6", "U2", "USBLC6-2SC6", g(175), g(100), 0, FP["SOT23-6"], "C7519", "USBLC6-2SC6",
                 "USB D+/D- and VBUS ESD protection")
    # bottom-side mounting mirrors the SOT-23-6, so D+ uses channel I/O2 and D- uses I/O1
    s.pinlabel(u2, "U2", "3", "USB_D+")
    s.pinlabel(u2, "U2", "4", "USB_D+")
    s.pinlabel(u2, "U2", "1", "USB_D-")
    s.pinlabel(u2, "U2", "6", "USB_D-")
    s.pinlabel(u2, "U2", "5", "VBUS")
    s.pinlabel(u2, "U2", "2", "GND")

    f1 = s.place("Polyfuse", "F1", "500mA", g(110), g(160), 0, FP["FUSE"], "C66452", "SMD0805-050", "Resettable PTC fuse, 0.5 A hold")
    s.pinlabel(f1, "F1", "1", "VBUS")
    s.pinlabel(f1, "F1", "2", "+5V")
    c1 = s.place("C", "C1", "10uF", g(135), g(160), 0, FP["C0603"], "C19702", "CL10A106KP8NNNC", "LDO input")
    s.pinlabel(c1, "C1", "1", "+5V")
    s.pinlabel(c1, "C1", "2", "GND")
    u3 = s.place("XC6206PxxxMR", "U3", "XC6206P332MR", g(175), g(160), 0, FP["SOT23"], "C5446", "XC6206P332MR",
                 "3.3 V 200 mA LDO")
    s.pinlabel(u3, "U3", "3", "+5V")
    s.pinlabel(u3, "U3", "2", "+3V3")
    s.pinlabel(u3, "U3", "1", "GND")
    c2 = s.place("C", "C2", "10uF", g(210), g(160), 0, FP["C0603"], "C19702", "CL10A106KP8NNNC", "LDO output")
    s.pinlabel(c2, "C2", "1", "+3V3")
    s.pinlabel(c2, "C2", "2", "GND")
    # power flags
    for i, net in enumerate(["+5V", "GND", "VBUS"]):
        x, y = g(60 + 45 * i), g(205)
        s.power("PWR_FLAG", (x, y))
        s.power(net, (x, y), rot=0 if net == "GND" else 180)
    s.text("CC1/CC2 5.1 kΩ = USB-C sink (works with C-to-C cables). PTC limits faults to 0.5 A.", 30, 218, 1.5)

    # ---------------------------------------------------------------- RP2040
    ux, uy = g(400), g(140)
    u1 = s.place("RP2040", "U1", "RP2040", ux, uy, 0, FP["QFN"], "C2040", "RP2040",
                 "Raspberry Pi RP2040 MCU, QFN-56, exposed pad = GND")
    gpio_net = {}
    for r, gp in enumerate(L.ROW_GPIO):
        gpio_net[gp] = f"ROW{r}"
    for c, gp in enumerate(L.COL_GPIO):
        gpio_net[gp] = f"COL{c}"
    for num, p in PINS["RP2040"].items():
        name = p[3]
        if name.startswith("GPIO"):
            gp = int(name[4:].split("/")[0])
            if gp in gpio_net:
                s.pinlabel(u1, "U1", num, gpio_net[gp])
            else:
                s.nc(u1[num][:2])
    for num in ("1", "10", "22", "33", "42", "49", "43", "44", "48"):
        s.pinlabel(u1, "U1", num, "+3V3")
    for num in ("45", "23", "50"):
        s.pinlabel(u1, "U1", num, "+1V1")
    s.pinlabel(u1, "U1", "57", "GND")
    s.pinlabel(u1, "U1", "19", "GND")          # TESTEN
    s.pinlabel(u1, "U1", "26", "RUN")
    s.pinlabel(u1, "U1", "46", "RP_DM")
    s.pinlabel(u1, "U1", "47", "RP_DP")
    for num, net in (("56", "QSPI_SS"), ("52", "QSPI_SCLK"), ("53", "QSPI_SD0"), ("55", "QSPI_SD1"),
                     ("54", "QSPI_SD2"), ("51", "QSPI_SD3")):
        s.pinlabel(u1, "U1", num, net)
    s.pinlabel(u1, "U1", "20", "XIN")
    s.pinlabel(u1, "U1", "21", "XOUT")
    s.nc(u1["24"][:2])          # SWCLK - not needed: ROM USB bootloader + BOOT/RESET buttons
    s.nc(u1["25"][:2])          # SWDIO

    # USB series resistors
    for i, (ref, a, b) in enumerate((("R3", "RP_DP", "USB_D+"), ("R4", "RP_DM", "USB_D-"))):
        r = s.place("R", ref, "27R", g(300 + 14 * i), g(80), 0, FP["R0402"], "C25100", "0402WGF270JTCE", "USB series termination")
        s.pinlabel(r, ref, "1", a)
        s.pinlabel(r, ref, "2", b)

    # QSPI flash
    u4 = s.place("W25Q16JVUXIQ", "U4", "W25Q16JVUXIQ", g(300), g(190), 0, FP["USON8"], "C2843335", "W25Q16JVUXIQ",
                 "2 MB QSPI NOR flash (same part as Raspberry Pi Pico)")
    for num, net in (("1", "QSPI_SS"), ("6", "QSPI_SCLK"), ("5", "QSPI_SD0"), ("2", "QSPI_SD1"), ("3", "QSPI_SD2"),
                     ("7", "QSPI_SD3"), ("8", "+3V3"), ("4", "GND")):
        s.pinlabel(u4, "U4", num, net)
    s.nc(u4["9"][:2])
    r5 = s.place("R", "R5", "10k", g(330), g(240), 0, FP["R0402"], "C25744", "0402WGF1002TCE", "Flash CS pull-up")
    s.pinlabel(r5, "R5", "1", "+3V3")
    s.pinlabel(r5, "R5", "2", "QSPI_SS")
    r6 = s.place("R", "R6", "1k", g(345), g(240), 0, FP["R0402"], "C11702", "0402WGF1001TCE", "BOOTSEL series resistor")
    s.pinlabel(r6, "R6", "1", "QSPI_SS")
    s.pinlabel(r6, "R6", "2", "BOOTSEL")
    sw_boot = s.place("SW_Push", "SW90", "BOOT", g(375), g(255), 0, FP["BTN"], "C318884", "TS-1187A-B-A-B",
                      "Hold while plugging in to enter the RP2040 USB bootloader")
    s.pinlabel(sw_boot, "SW90", "1", "BOOTSEL")
    s.pinlabel(sw_boot, "SW90", "2", "GND")
    r7 = s.place("R", "R7", "10k", g(420), g(240), 0, FP["R0402"], "C25744", "0402WGF1002TCE", "RUN pull-up")
    s.pinlabel(r7, "R7", "1", "+3V3")
    s.pinlabel(r7, "R7", "2", "RUN")
    sw_rst = s.place("SW_Push", "SW91", "RESET", g(450), g(255), 0, FP["BTN"], "C318884", "TS-1187A-B-A-B", "Reset")
    s.pinlabel(sw_rst, "SW91", "1", "RUN")
    s.pinlabel(sw_rst, "SW91", "2", "GND")

    # crystal
    y1 = s.place("Crystal_GND24", "Y1", "12MHz", g(520), g(200), 0, FP["XTAL"], "C20625731", "ABM8-272-T3",
                 "12 MHz, CL 10 pF (Raspberry Pi approved for RP2040)")
    s.pinlabel(y1, "Y1", "1", "XIN")
    s.pinlabel(y1, "Y1", "3", "XTAL_OUT")
    s.pinlabel(y1, "Y1", "2", "GND")
    s.pinlabel(y1, "Y1", "4", "GND")
    r8 = s.place("R", "R8", "1k", g(555), g(185), 0, FP["R0402"], "C11702", "0402WGF1001TCE", "XOUT drive limit")
    s.pinlabel(r8, "R8", "1", "XOUT")
    s.pinlabel(r8, "R8", "2", "XTAL_OUT")
    for i, (ref, net) in enumerate((("C16", "XIN"), ("C17", "XTAL_OUT"))):
        c = s.place("C", ref, "15pF", g(500 + 40 * i), g(235), 0, FP["C0402"], "C1548", "0402CG150J500NT", "Crystal load")
        s.pinlabel(c, ref, "1", net)
        s.pinlabel(c, ref, "2", "GND")

    # decoupling
    caps = [("C3", "100nF", "+3V3", "IOVDD 1"), ("C4", "100nF", "+3V3", "IOVDD 10"), ("C5", "100nF", "+3V3", "IOVDD 22"),
            ("C6", "100nF", "+3V3", "IOVDD 33"), ("C7", "100nF", "+3V3", "IOVDD 42"),
            ("C9", "100nF", "+3V3", "USB_VDD 48 / IOVDD 49"), ("C10", "100nF", "+3V3", "ADC_AVDD 43"),
            ("C11", "100nF", "+1V1", "DVDD 23"), ("C12", "100nF", "+1V1", "DVDD (pins 23/50)"),
            ("C13", "1uF", "+3V3", "VREG_VIN 44"), ("C14", "1uF", "+1V1", "VREG_VOUT 45"),
            ("C15", "100nF", "+3V3", "Flash VCC")]
    for i, (ref, val, net, why) in enumerate(caps):
        lc, mp = ("C1525", "CL05B104KO5NNNC") if val == "100nF" else ("C52923", "CL05A105KA5NQNC")
        c = s.place("C", ref, val, g(600 + 16 * (i % 7)), g(90 + 55 * (i // 7)), 0, FP["C0402"], lc, mp, f"Decoupling {why}")
        s.pinlabel(c, ref, "1", net)
        s.pinlabel(c, ref, "2", "GND")

    # test points (SWD, power)
    for i, (ref, net) in enumerate((("TP1", "RUN"), ("TP2", "+3V3"), ("TP3", "GND"), ("TP4", "+5V"))):
        t = s.place("TestPoint", ref, net, g(600 + 25 * i), g(225), 0, FP["TP"], "", "", "Test pad (not assembled)",
                    in_bom=False)
        s.pinlabel(t, ref, "1", net)
    s.text("Hold BOOT while connecting USB (or press RESET while holding BOOT) to get the RPI-RP2 UF2 drive.\n"
           "A blank board enumerates as RPI-RP2 automatically. Test pads: RUN, +3V3, GND, +5V.", 600, 255, 1.5)

    # ---------------------------------------------------------------- key matrix
    keys = L.keys()
    x0, y0, dx, dy = 45, 315, 48.26, 43.18
    for k in keys:
        cx = g(x0 + dx * k["col"])
        cy = g(y0 + dy * k["row"])
        sw = s.place("SW_Push", k["ref"], k["label"], cx, cy, 0, f"{LIBNAME}:Hotswap_MX_{L.fp_size_name(k['w'])}",
                     "C5156480", "Kailh CPG151101S11", "MX hot-swap socket (switch is user-installed)",
                     extra={"Key": k["label"], "Matrix": f"R{k['row']}C{k['col']}"},
                     datasheet="https://www.kailhswitch.com/mechanical-keyboard-switches/box-switches/mechanical-keyboard-switches-kailh-pcb-socket.html")
        s.pinlabel(sw, k["ref"], "1", f"COL{k['col']}")
        # diode vertical, anode on the switch pin 2, cathode down to the row label
        ax, ay, _ = sw["2"]
        d = s.place("D", k["diode"], "1N4148W", ax, ay + 3.81, 90, FP["D"], "C81598", "1N4148W", "Matrix diode")
        s.netplan[(k["ref"], "2")] = f"K{k['n']}"
        s.netplan[(k["diode"], "2")] = f"K{k['n']}"
        s.pinlabel(d, k["diode"], "1", f"ROW{k['row']}")
    for c in range(L.MATRIX_COLS):
        s.text(f"COL{c}  GPIO{L.COL_GPIO[c]}", g(x0 + dx * c) - 8, y0 - 12, 1.6, True)
    for r in range(L.MATRIX_ROWS):
        s.text(f"ROW{r}\nGPIO{L.ROW_GPIO[r]}", 28, g(y0 + dy * r) + 6, 1.6, True)
    return s


def write(s: Sch):
    OUT.mkdir(parents=True, exist_ok=True)
    libsyms = []
    for nm in sorted(s.symbols_used):
        e = [x for x in SYMS[nm]]
        e[1] = f"{LIBNAME}:{nm}"
        libsyms.append(e)
    doc = ["kicad_sch", ["version", VERSION], ["generator", "eeschema"], ["generator_version", "10.0"],
           ["uuid", SCH_UUID], ["paper", "A1"],
           ["title_block", ["title", "Vamora75 — 75% hot-swap keyboard, Windows ANSI"], ["date", "2026-10-02"],
            ["rev", "1.1"], ["company", "Vamora · Việt Nam · USA · Morocco"],
            ["comment", 1, "RP2040 + USB-C, 82 Kailh CPG151101S11 hot-swap sockets, 6x16 COL2ROW matrix"],
            ["comment", 2, "All SMD parts on the bottom side (single-sided JLCPCB assembly)"]],
           ["lib_symbols"] + libsyms]
    doc += s.items
    doc += [["sheet_instances", ["path", "/", ["page", "1"]]], ["embedded_fonts", S("no")]]
    (OUT / "Vamora75.kicad_sch").write_text(sexp.dumps(doc) + "\n", encoding="utf-8")
    # project symbol library
    lib = ["kicad_symbol_lib", ["version", VERSION], ["generator", "kicad_symbol_editor"], ["generator_version", "10.0"]]
    for nm in sorted(SYMS):
        lib.append(SYMS[nm])
    (OUT / "Vamora75.kicad_sym").write_text(sexp.dumps(lib) + "\n", encoding="utf-8")
    (OUT / "sym-lib-table").write_text('(sym_lib_table\n\t(version 7)\n\t(lib (name "Vamora75")(type "KiCad")(uri "${KIPRJMOD}/Vamora75.kicad_sym")(options "")(descr "Vamora75 project symbols"))\n)\n', encoding="utf-8")
    (OUT / "fp-lib-table").write_text('(fp_lib_table\n\t(version 7)\n\t(lib (name "Vamora75")(type "KiCad")(uri "${KIPRJMOD}/Vamora75.pretty")(options "")(descr "Vamora75 project footprints"))\n)\n', encoding="utf-8")
    plan = {"components": s.comps, "netplan": {f"{r}|{p}": n for (r, p), n in s.netplan.items()}}
    (OUT / "build").mkdir(exist_ok=True)
    (OUT / "build" / "schematic_plan.json").write_text(json.dumps(plan, indent=1), encoding="utf-8")
    print(f"schematic: {len(s.comps)} components, {len(s.items)} items -> {OUT}")


if __name__ == "__main__":
    L.check()
    write(build())
