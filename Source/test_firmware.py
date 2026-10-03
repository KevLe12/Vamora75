"""Static + host-side tests for the generated firmware against the PCB netlist.

    python Source/test_firmware.py [netlist.xml]

1. QMK keyboard.json / keymaps / VIA / KLE agree with vamora_layout (82 keys, unique matrix slots,
   LAYOUT arity, KLE geometry round-trip).
2. The schematic netlist wires every switch exactly as the firmware expects: SWn -> COLc net,
   Dn cathode -> ROWr net, ROWr/COLc nets -> the RP2040 GPIO listed in keyboard.json.
3. The CircuitPython report builder produces the right HID usages for every key and Fn chord.
"""
from __future__ import annotations

import importlib.util
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gen_firmware as G  # noqa: E402
import vamora_layout as L  # noqa: E402

ROOT = HERE.parent
FW = ROOT / "Firmware"
NET = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "validation" / "schematic.net.xml"
results = {}


def check(name, cond, detail=""):
    results[name] = "PASS" if cond else f"FAIL {detail}"
    if not cond:
        print("FAIL", name, detail)


# ------------------------------------------------------------------ 1. QMK / VIA / KLE
kb = json.loads((G.QMK / "keyboard.json").read_text(encoding="utf-8"))
lay = kb["layouts"]["LAYOUT"]["layout"]
check("qmk.82 keys", len(lay) == 82, len(lay))
slots = [tuple(e["matrix"]) for e in lay]
check("qmk.unique matrix", len(set(slots)) == 82)
check("qmk.matrix in range", all(0 <= r < 6 and 0 <= c < 16 for r, c in slots))
check("qmk.pin counts", len(kb["matrix_pins"]["rows"]) == 6 and len(kb["matrix_pins"]["cols"]) == 16)
check("qmk.pins unique", len(set(kb["matrix_pins"]["rows"] + kb["matrix_pins"]["cols"])) == 22)
check("qmk.no QSPI/USB pins", not ({"GP30", "GP31"} & set(kb["matrix_pins"]["rows"] + kb["matrix_pins"]["cols"])))
for km_name, nlayers in (("default", 2), ("via", 4)):
    src = (G.QMK / "keymaps" / km_name / "keymap.c").read_text(encoding="utf-8")
    blocks = re.findall(r"LAYOUT\((.*?)\n    \)", src, re.S)
    check(f"keymap.{km_name}.layers", len(blocks) == nlayers, len(blocks))
    for i, b in enumerate(blocks):
        codes = [c.strip() for c in b.replace("\n", " ").split(",") if c.strip()]
        check(f"keymap.{km_name}.L{i}.arity", len(codes) == 82, len(codes))
    base = [c.strip() for c in blocks[0].replace("\n", " ").split(",") if c.strip()]
    check(f"keymap.{km_name}.base matches layout", base == [k["kc"] for k in L.keys()])
via = json.loads((FW / "via" / "vamora75.via.json").read_text(encoding="utf-8"))
labels = [x for row in via["layouts"]["keymap"] for x in row if isinstance(x, str)]
check("via.82 keys", len(labels) == 82 and len(set(labels)) == 82)
check("via.ids", via["vendorId"] == kb["usb"]["vid"] and via["productId"] == kb["usb"]["pid"])
check("via.matrix", via["matrix"] == {"rows": 6, "cols": 16})
# KLE round trip
kle = json.loads((FW / "layout" / "vamora75.kle.json").read_text(encoding="utf-8"))[1:]
pos, y = [], -1.0
for row in kle:
    y += 1.0
    x, w = 0.0, 1.0
    for item in row:
        if isinstance(item, dict):
            x += item.get("x", 0)
            y += item.get("y", 0)
            w = item.get("w", 1)
            continue
        pos.append((item, round(x, 4), round(y, 4), w))
        x += w
        w = 1.0
want = sorted((k["label"], k["x"], k["y"], k["w"]) for k in L.keys())
check("kle.geometry round-trip", sorted(pos) == want)

# ------------------------------------------------------------------ 2. netlist vs firmware
if NET.exists():
    root = ET.parse(NET).getroot()
    pin_of, gpio_of_net = {}, {}
    for n in root.findall("./nets/net"):
        for nd in n.findall("node"):
            pin_of[(nd.get("ref"), nd.get("pin"))] = n.get("name")
            if nd.get("ref") == "U1":
                m = re.match(r"GPIO(\d+)", nd.get("pinfunction") or "")
                if m:
                    gpio_of_net.setdefault(n.get("name"), set()).add(int(m.group(1)))
    bad = []
    for k in L.keys():
        if pin_of.get((k["ref"], "1")) != f"/COL{k['col']}":
            bad.append((k["ref"], "pad1", pin_of.get((k["ref"], "1"))))
        sw2 = pin_of.get((k["ref"], "2"))
        if sw2 != pin_of.get((k["diode"], "2")):
            bad.append((k["ref"], "pad2-anode", sw2))
        if pin_of.get((k["diode"], "1")) != f"/ROW{k['row']}":
            bad.append((k["diode"], "cathode", pin_of.get((k["diode"], "1"))))
    check("netlist.switch/diode wiring (COL2ROW)", not bad, bad[:5])
    pins_ok = all(gpio_of_net.get(f"/ROW{r}") == {g} for r, g in enumerate(L.ROW_GPIO)) and \
        all(gpio_of_net.get(f"/COL{c}") == {g} for c, g in enumerate(L.COL_GPIO))
    check("netlist.RP2040 GPIO == keyboard.json", pins_ok,
          {k: v for k, v in gpio_of_net.items() if k.startswith(("/ROW", "/COL"))})
    qmk_pins = [int(p[2:]) for p in kb["matrix_pins"]["rows"]], [int(p[2:]) for p in kb["matrix_pins"]["cols"]]
    check("keyboard.json pins == layout", qmk_pins == (L.ROW_GPIO, L.COL_GPIO))
else:
    results["netlist"] = f"SKIPPED ({NET} missing)"

# ------------------------------------------------------------------ 3. CircuitPython reports
cp = FW / "CircuitPython"
sys.path.insert(0, str(cp))
spec = importlib.util.spec_from_file_location("report", cp / "report.py")
rep = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rep)
import keymap as KM  # noqa: E402  (CircuitPython/keymap.py)

idx = {k["label"]: k["row"] * L.MATRIX_COLS + k["col"] for k in L.keys()}
errs = []
for k in L.keys():
    if k["kc"].startswith("MO("):
        continue
    kr, cr, boot = rep.reports({idx[k["label"]]})
    code = G.HID[k["kc"]]
    if 224 <= code <= 231:
        ok = kr[0] == 1 << (code - 224) and kr[2] == 0
    else:
        ok = kr[0] == 0 and kr[2] == code
    if not ok or boot:
        errs.append(k["label"])
check("circuitpython.every key", not errs, errs)
kr, cr, boot = rep.reports({idx["Fn"], idx["F3"]})
check("circuitpython.Fn+F3 volume up", cr == bytes([0xE9, 0]) and kr[2] == 0)
kr, cr, boot = rep.reports({idx["Fn"], idx["Esc"]})
check("circuitpython.Fn+Esc bootloader", boot)
kr, cr, boot = rep.reports({idx["Fn"], idx["Del"]})
check("circuitpython.Fn+Del insert", kr[2] == 73)
kr, cr, boot = rep.reports({idx[c] for c in "QWERTYU"})
check("circuitpython.7-key rollover error", list(kr[2:]) == [1] * 6)
kr, cr, boot = rep.reports({idx["LShift"], idx["A"]})
check("circuitpython.shift+A", kr[0] == 2 and kr[2] == 4)
check("circuitpython.keymap pins", KM.ROWS == L.ROW_GPIO and KM.COLS == L.COL_GPIO)

out = ROOT / "validation" / "firmware.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(results, indent=2), encoding="utf-8")
fails = [k for k, v in results.items() if v.startswith("FAIL")]
print(f"{len(results) - len(fails)}/{len(results)} checks passed" + (f"; FAILED: {fails}" if fails else ""))
sys.exit(1 if fails else 0)
