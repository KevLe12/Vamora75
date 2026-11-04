"""Generate all Vamora75 firmware sources from vamora_layout (same data as the PCB).

    python Source/gen_firmware.py

Firmware/qmk/keyboards/vamora75/   QMK (data-driven keyboard.json, default + VIA keymaps)
Firmware/via/vamora75.via.json     VIA "Design" definition (load in usevia.app -> Settings -> Design)
Firmware/CircuitPython/            no-compile option (CircuitPython for Raspberry Pi Pico + 4 files)
Firmware/layout/                   keyboard-layout-editor JSON
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import vamora_layout as L  # noqa: E402

ROOT = HERE.parent
FW = ROOT / "Firmware"
QMK = FW / "qmk" / "keyboards" / "vamora75"
VID, PID = "0x564D", "0x0075"          # "VM" / 75 - DIY ids, change before any commercial run
ROWS = [f"GP{g}" for g in L.ROW_GPIO]
COLS = [f"GP{g}" for g in L.COL_GPIO]
KEYS = L.keys()

# Fn layer (layer 1). Everything else transparent.
FN = {"Esc": "QK_BOOT", "F1": "KC_MUTE", "F2": "KC_VOLD", "F3": "KC_VOLU", "F4": "KC_MPLY", "F5": "KC_MPRV",
      "F6": "KC_MNXT", "F7": "KC_BRID", "F8": "KC_BRIU", "F9": "KC_CALC", "F10": "KC_PAUS", "F11": "KC_SCRL",
      "F12": "KC_PSCR", "Del": "KC_INS", "Win": "GU_TOGG", "N": "NK_TOGG"}

# USB HID usage ids for the CircuitPython build (keyboard page 0x07 / consumer page 0x0C)
HID = {"KC_ESC": 41, "KC_GRV": 53, "KC_MINS": 45, "KC_EQL": 46, "KC_BSPC": 42, "KC_TAB": 43, "KC_LBRC": 47,
       "KC_RBRC": 48, "KC_BSLS": 49, "KC_CAPS": 57, "KC_SCLN": 51, "KC_QUOT": 52, "KC_ENT": 40, "KC_LSFT": 225,
       "KC_COMM": 54, "KC_DOT": 55, "KC_SLSH": 56, "KC_RSFT": 229, "KC_UP": 82, "KC_LCTL": 224, "KC_LGUI": 227,
       "KC_LALT": 226, "KC_SPC": 44, "KC_RALT": 230, "KC_RCTL": 228, "KC_LEFT": 80, "KC_DOWN": 81,
       "KC_RGHT": 79, "KC_DEL": 76, "KC_HOME": 74, "KC_PGUP": 75, "KC_PGDN": 78, "KC_END": 77,
       "KC_INS": 73, "KC_PSCR": 70, "KC_SCRL": 71, "KC_PAUS": 72, "KC_CALC": 0}
for i, ch in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ"):
    HID[f"KC_{ch}"] = 4 + i
for i, ch in enumerate("1234567890"):
    HID[f"KC_{ch}"] = 30 + i
for i in range(1, 13):
    HID[f"KC_F{i}"] = 57 + i
CONSUMER = {"KC_MUTE": 0xE2, "KC_VOLD": 0xEA, "KC_VOLU": 0xE9, "KC_MPLY": 0xCD, "KC_MPRV": 0xB6,
            "KC_MNXT": 0xB5, "KC_BRID": 0x70, "KC_BRIU": 0x6F, "KC_CALC": 0x192}


def check_matrix():
    seen = {}
    for k in KEYS:
        rc = (k["row"], k["col"])
        assert rc not in seen, f"matrix collision {rc}: {seen.get(rc)} / {k['label']}"
        assert 0 <= k["row"] < L.MATRIX_ROWS and 0 <= k["col"] < L.MATRIX_COLS
        seen[rc] = k["label"]
    assert len(seen) == 82


def keyboard_json():
    layout = []
    for k in KEYS:
        e = {"label": k["label"], "matrix": [k["row"], k["col"]], "x": k["x"], "y": k["y"]}
        if k["w"] != 1:
            e["w"] = k["w"]
        layout.append(e)
    esc = next(k for k in KEYS if k["label"] == "Esc")
    return {
        "manufacturer": "Vamora",
        "keyboard_name": "Vamora75",
        "maintainer": "vamora",
        "url": "",
        "processor": "RP2040",
        "bootloader": "rp2040",
        "usb": {"vid": VID, "pid": PID, "device_version": "1.0.0"},
        "diode_direction": "COL2ROW",
        "matrix_pins": {"rows": ROWS, "cols": COLS},
        "debounce": 5,
        "features": {"bootmagic": True, "extrakey": True, "mousekey": True, "nkro": True},
        "bootmagic": {"matrix": [esc["row"], esc["col"]]},
        "layouts": {"LAYOUT": {"layout": layout}},
    }


CONFIG_H = """// Copyright 2026 Kevin Le, Sammy DeGraaff, Mohammed-Mehdi Hamdaoui (Vamora)
// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once

// Bare RP2040 + Winbond W25Q16JV (2 MB, QSPI) + 12 MHz crystal.
// The generic 03h boot stage works with every W25Qxx part (and with substitutes).
#define RP2040_FLASH_GENERIC_03H

// Double-tap the RESET button (SW91) to enter the UF2 bootloader without opening the case;
// Fn+Esc (QK_BOOT), holding Esc while plugging in (bootmagic) or BOOT+plug also work.
#define RP2040_BOOTLOADER_DOUBLE_TAP_RESET
#define RP2040_BOOTLOADER_DOUBLE_TAP_RESET_TIMEOUT 500U
"""

QMK_README = """# Vamora75

82-key 75 % (exploded Windows ANSI) hot-swap keyboard with an on-board RP2040.
Designed by Kevin Le, Sammy DeGraaff and Mohammed-Mehdi Hamdaoui (team Vamora).

* Keyboard maintainer: vamora
* Hardware supported: Vamora75 PCB (RP2040, W25Q16JV, USB-C, Kailh hot-swap)
* Hardware availability: open-source design files

Make example for this keyboard (after setting up your build environment):

    qmk compile -kb vamora75 -km default
    qmk compile -kb vamora75 -km via

Flashing example: copy the `.uf2` file to the `RPI-RP2` drive.

See the [build environment setup](https://docs.qmk.fm/#/getting_started_build_tools) and the
[make instructions](https://docs.qmk.fm/#/getting_started_make_guide) for more information.

## Bootloader

Enter the bootloader in 4 ways:

* **Bootmagic reset**: hold Esc (top-left key) and plug in the keyboard
* **Keycode in layout**: Fn+Esc (`QK_BOOT`)
* **Double-tap reset**: double-tap the RESET button on the PCB
* **Physical**: hold BOOT (pin-hole in the case bottom) while plugging in
"""


def c_layout(name, codes, per_row):
    rows, i = [], 0
    for n in per_row:
        rows.append("        " + ", ".join(codes[i:i + n]))
        i += n
    return f"    [{name}] = LAYOUT(\n" + ",\n".join(rows) + "\n    )"


def keymap_c(layers):
    per_row = []
    for r in sorted({k["y"] for k in KEYS}):
        per_row.append(sum(1 for k in KEYS if k["y"] == r))
    body = ",\n".join(c_layout(i, codes, per_row) for i, codes in enumerate(layers))
    return ("// Copyright 2026 Kevin Le, Sammy DeGraaff, Mohammed-Mehdi Hamdaoui (Vamora)\n// SPDX-License-Identifier: GPL-2.0-or-later\n"
            "#include QMK_KEYBOARD_H\n\n"
            "const uint16_t PROGMEM keymaps[][MATRIX_ROWS][MATRIX_COLS] = {\n" + body + "\n};\n")


def layers(n):
    base = [k["kc"] for k in KEYS]
    fn = [FN.get(k["label"], "_______") for k in KEYS]
    out = [base, fn]
    while len(out) < n:
        out.append(["_______"] * len(KEYS))
    return out


def kle_rows(label_fn):
    rows = []
    prev_y = None
    for y in sorted({k["y"] for k in KEYS}):
        row, cursor = [], 0.0
        for n, k in enumerate(sorted([k for k in KEYS if k["y"] == y], key=lambda k: k["x"])):
            props = {}
            if n == 0 and prev_y is not None and y - prev_y != 1:
                props["y"] = round(y - prev_y - 1, 4)
            if abs(k["x"] - cursor) > 1e-9:
                props["x"] = round(k["x"] - cursor, 4)
            if k["w"] != 1:
                props["w"] = k["w"]
            if props:
                row.append(props)
            row.append(label_fn(k))
            cursor = k["x"] + k["w"]
        rows.append(row)
        prev_y = y
    return rows


def via_json():
    return {"name": "Vamora75", "vendorId": VID, "productId": PID,
            "matrix": {"rows": L.MATRIX_ROWS, "cols": L.MATRIX_COLS},
            "layouts": {"keymap": kle_rows(lambda k: f"{k['row']},{k['col']}")}}


# ------------------------------------------------------------------ CircuitPython
CP_BOOT = '''"""Vamora75 boot.py - hold Esc while plugging in for the writable CIRCUITPY drive + serial REPL."""
import time
import digitalio
import microcontroller
import storage
import usb_cdc
import usb_hid
import usb_midi

ESC_COL, ESC_ROW = microcontroller.pin.GPIO{esc_col}, microcontroller.pin.GPIO{esc_row}
c = digitalio.DigitalInOut(ESC_COL)
r = digitalio.DigitalInOut(ESC_ROW)
r.switch_to_input(pull=digitalio.Pull.DOWN)
c.switch_to_output(value=True)
time.sleep(0.01)
maintenance = r.value
c.deinit()
r.deinit()
usb_midi.disable()
if not maintenance:
    storage.disable_usb_drive()
    usb_cdc.disable()
usb_hid.set_interface_name("Vamora75")
usb_hid.enable((usb_hid.Device.KEYBOARD, usb_hid.Device.CONSUMER_CONTROL), boot_device=0 if maintenance else 1)
'''

CP_CODE = '''"""Vamora75 - 6 x 16 COL2ROW matrix on a bare RP2040 (CircuitPython, Raspberry Pi Pico build)."""
import time
import digitalio
import microcontroller
import usb_hid
from keymap import COLS, ROWS, NCOLS
from report import reports

keyboard = next(d for d in usb_hid.devices if d.usage_page == 1 and d.usage == 6)
consumer = next((d for d in usb_hid.devices if d.usage_page == 12 and d.usage == 1), None)


def pin(gp):
    return digitalio.DigitalInOut(getattr(microcontroller.pin, "GPIO" + str(gp)))


rows, cols = [], []
for gp in ROWS:                      # rows: inputs with pull-downs (diode cathodes)
    p = pin(gp)
    p.switch_to_input(pull=digitalio.Pull.DOWN)
    rows.append(p)
for gp in COLS:                      # columns: driven high one at a time (diode anodes via the switches)
    p = pin(gp)
    p.switch_to_output(value=False)
    cols.append(p)
N = len(ROWS) * NCOLS
raw, stable, changed = [False] * N, [False] * N, [0.0] * N
last_k = last_c = None
while True:
    now = time.monotonic()
    for c, col in enumerate(cols):
        col.value = True
        time.sleep(0.00002)
        for r, row in enumerate(rows):
            i = r * NCOLS + c
            v = row.value
            if v != raw[i]:
                raw[i] = v
                changed[i] = now
            elif now - changed[i] >= 0.005:
                stable[i] = v
        col.value = False
    k, cc, boot = reports({i for i, v in enumerate(stable) if v})
    if boot:
        keyboard.send_report(bytes(8))
        if consumer:
            consumer.send_report(bytes(2))
        microcontroller.on_next_reset(microcontroller.RunMode.UF2)
        microcontroller.reset()
    try:
        if k != last_k:
            keyboard.send_report(k)
            last_k = k
        if consumer and cc != last_c:
            consumer.send_report(cc)
            last_c = cc
    except OSError:                  # USB suspended / re-enumerating: resend the full state later
        last_k = last_c = None
    time.sleep(0.001)
'''

CP_REPORT = '''"""USB boot-keyboard (6KRO) and consumer reports; no runtime library dependencies."""
from keymap import KEYMAP, FN_INDEX, FN_ACTIONS


def reports(held):
    fn = FN_INDEX in held
    mods, codes, consumer, boot = 0, [], 0, False
    for index in sorted(held):
        code = KEYMAP[index]
        if fn and index in FN_ACTIONS:
            kind, code = FN_ACTIONS[index]
            if kind == "boot":
                boot = True
                continue
            if kind == "consumer":
                consumer = code
                continue
        if not code:
            continue
        if 224 <= code <= 231:
            mods |= 1 << (code - 224)
        elif code not in codes:
            codes.append(code)
    if len(codes) > 6:
        codes = [1] * 6              # ErrorRollOver until the chord drops to <= 6 keys
    return bytes([mods, 0] + codes + [0] * (6 - len(codes))), bytes([consumer & 255, consumer >> 8]), boot
'''


def cp_keymap():
    n = L.MATRIX_ROWS * L.MATRIX_COLS
    km = [0] * n
    fn_actions = {}
    fn_index = None
    for k in KEYS:
        i = k["row"] * L.MATRIX_COLS + k["col"]
        if k["kc"].startswith("MO("):
            fn_index = i
            continue
        km[i] = HID[k["kc"]]
        a = FN.get(k["label"])
        if a == "QK_BOOT":
            fn_actions[i] = ("boot", 0)
        elif a in CONSUMER:
            fn_actions[i] = ("consumer", CONSUMER[a])
        elif a and a in HID and HID[a]:
            fn_actions[i] = ("key", HID[a])
    lines = ["# Generated by Source/gen_firmware.py from vamora_layout.py. Index = row * NCOLS + col.",
             f"ROWS = {L.ROW_GPIO}          # GPIO numbers, matrix rows 0..5",
             f"COLS = {L.COL_GPIO}",
             f"NCOLS = {L.MATRIX_COLS}",
             f"KEYMAP = {km}",
             f"FN_INDEX = {fn_index}",
             f"FN_ACTIONS = {fn_actions}"]
    return "\n".join(lines) + "\n", km, fn_index, fn_actions


FW_README = """# Vamora75 firmware

The PCB carries a bare **RP2040** with a **W25Q16JV 2 MB flash** and a **12 MHz crystal** - the same
core circuit as a Raspberry Pi Pico - so both options below run on it unchanged.

| | Matrix | Pins |
|---|---|---|
| Rows 0-5 (diode cathodes) | 6 | {rows} |
| Columns 0-15 | 16 | {cols} |
| Diodes | COL2ROW | 1N4148W (SOD-123), one per switch |

Free GPIO: GP9-GP15 and GP25 (GP25 is the Pico's status-LED pin, deliberately left unconnected).

## Entering the bootloader (UF2 drive `RPI-RP2`)

* Brand-new board (blank flash): it enumerates as `RPI-RP2` by itself.
* Hold **Esc** while plugging in (QMK bootmagic), or press **Fn+Esc**.
* Double-tap the **RESET** button (QMK build).
* Hold the **BOOT** button - reachable with a paper clip through the pin-hole in the case bottom - while plugging in.

## Option A - QMK + VIA (recommended)

1. Copy `qmk/keyboards/vamora75` into `qmk_firmware/keyboards/`.
2. `qmk compile -kb vamora75 -km via` (or `-km default`).
3. Copy the resulting `vamora75_via.uf2` to the `RPI-RP2` drive.
4. Remap live in https://usevia.app : Settings -> enable *Show Design tab* -> Design -> load
   `via/vamora75.via.json` (needed until the board is merged into the VIA repository).

`keyboard.json` is data-driven (QMK 0.22+). These sources were generated and statically checked
here (layout/matrix consistency, keymap arity) but **not compiled** - no QMK toolchain in this
environment. Do the first compile before ordering boards.

Default layers: 0 = base, 1 = Fn (hold the Fn key):

| Fn + | Action | Fn + | Action |
|---|---|---|---|
| Esc | bootloader (QK_BOOT) | F7 / F8 | brightness - / + |
| F1 | mute | F9 | calculator |
| F2 / F3 | volume - / + | F10 | Pause |
| F4 | play / pause | F11 | Scroll Lock |
| F5 / F6 | previous / next track | F12 | Print Screen |
| Del | Insert | Win | Windows-key lock (gaming) |
| N | NKRO on/off | | |

## Option B - CircuitPython (no compiler needed)

1. Download the **Raspberry Pi Pico** UF2 from https://circuitpython.org/board/raspberry_pi_pico/
   (10.x). Do *not* use the rev 0.1 Waveshare RP2040-Zero UF2: that build drives GP16 (a matrix
   column on this board) as its NeoPixel.
2. Copy it to `RPI-RP2`; the `CIRCUITPY` drive appears.
3. Copy `CircuitPython/boot.py`, `code.py`, `keymap.py`, `report.py` to `CIRCUITPY`, then replug.
4. Normal use hides the drive and serial port and offers a BIOS-compatible boot keyboard.
   Hold **Esc** while plugging in to get `CIRCUITPY` back for edits.

CircuitPython sends 6 keys + modifiers (6KRO), 5 ms debounce, same Fn layer except Win-lock and NKRO.

## Layout files

* `layout/vamora75.kle.json` - paste into http://www.keyboard-layout-editor.com (Raw data).
* `via/vamora75.via.json` - VIA definition (rows,cols labels).

Generated by `Source/gen_firmware.py`; tests: `Source/test_firmware.py`.
"""


if __name__ == "__main__":
    check_matrix()
    (QMK / "keymaps" / "default").mkdir(parents=True, exist_ok=True)
    (QMK / "keymaps" / "via").mkdir(parents=True, exist_ok=True)
    (FW / "via").mkdir(parents=True, exist_ok=True)
    (FW / "layout").mkdir(parents=True, exist_ok=True)
    (FW / "CircuitPython").mkdir(parents=True, exist_ok=True)
    (QMK / "keyboard.json").write_text(json.dumps(keyboard_json(), indent=4) + "\n", encoding="utf-8")
    (QMK / "config.h").write_text(CONFIG_H, encoding="utf-8")
    (QMK / "readme.md").write_text(QMK_README, encoding="utf-8")
    (QMK / "keymaps" / "default" / "keymap.c").write_text(keymap_c(layers(2)), encoding="utf-8")
    (QMK / "keymaps" / "via" / "keymap.c").write_text(keymap_c(layers(4)), encoding="utf-8")
    (QMK / "keymaps" / "via" / "rules.mk").write_text("VIA_ENABLE = yes\n", encoding="utf-8")
    (FW / "via" / "vamora75.via.json").write_text(json.dumps(via_json(), indent=2) + "\n", encoding="utf-8")
    kle = [{"name": "Vamora75", "author": "Kevin Le, Sammy DeGraaff, Mohammed-Mehdi Hamdaoui (Vamora)"}] + kle_rows(lambda k: k["label"])
    (FW / "layout" / "vamora75.kle.json").write_text(json.dumps(kle, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    esc = next(k for k in KEYS if k["label"] == "Esc")
    (FW / "CircuitPython" / "boot.py").write_text(
        CP_BOOT.replace("{esc_col}", str(L.COL_GPIO[esc["col"]])).replace("{esc_row}", str(L.ROW_GPIO[esc["row"]])),
        encoding="utf-8")
    (FW / "CircuitPython" / "code.py").write_text(CP_CODE, encoding="utf-8")
    (FW / "CircuitPython" / "report.py").write_text(CP_REPORT, encoding="utf-8")
    txt, *_ = cp_keymap()
    (FW / "CircuitPython" / "keymap.py").write_text(txt, encoding="utf-8")
    (FW / "README.md").write_text(FW_README.format(rows=", ".join(ROWS), cols=", ".join(COLS)), encoding="utf-8")
    print("firmware sources written:", QMK.relative_to(ROOT), "| via | CircuitPython | layout")
