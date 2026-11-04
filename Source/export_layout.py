"""Layout data for people and other tools: layout.json, Mechanical/key_positions.csv, Previews/layout.png.

    python Source/export_layout.py
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import vamora_layout as L  # noqa: E402
import vamora_logo as V  # noqa: E402
import vamora_mech as M  # noqa: E402

ROOT = HERE.parent

if __name__ == "__main__":
    keys = []
    for k in L.keys():
        cx, cy = M.b2c(k["bx"], k["by"])
        keys.append(dict(n=k["n"], label=k["label"], keycode=k["kc"], x_u=k["x"], y_u=k["y"], w_u=k["w"],
                         row=k["row"], col=k["col"], switch_ref=k["ref"], diode_ref=k["diode"],
                         pcb_x_mm=round(k["bx"], 4), pcb_y_mm=round(k["by"], 4),
                         cad_x_mm=round(cx, 4), cad_y_mm=round(cy, 4),
                         stabilizer_mm=2 * L.STAB_SPACING[k["w"]] if k["w"] in L.STAB_SPACING else None))
    data = {
        "name": "Vamora75", "revision": L.REVISION, "units": "mm",
        "pcb_mm": [round(L.BOARD_W, 4), round(L.BOARD_H, 4)], "pitch_mm": L.U,
        "coordinates": {"pcb": "origin PCB rear-left corner, +y toward the user (KiCad)",
                        "cad": "origin PCB front-left corner, +Y toward the rear (STEP/case frame, plate-parallel)"},
        "matrix": {"rows": L.MATRIX_ROWS, "cols": L.MATRIX_COLS, "diode_direction": "COL2ROW",
                   "row_gpio": L.ROW_GPIO, "col_gpio": L.COL_GPIO},
        "keys": keys,
    }
    (ROOT / "layout.json").write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    with open(ROOT / "Mechanical" / "key_positions.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["n", "label", "width_u", "row", "col", "switch", "diode", "pcb_x_mm", "pcb_y_mm", "cad_x_mm", "cad_y_mm",
                    "stabilizer_mm"])
        for k in keys:
            w.writerow([k["n"], k["label"], k["w_u"], k["row"], k["col"], k["switch_ref"], k["diode_ref"], k["pcb_x_mm"],
                        k["pcb_y_mm"], k["cad_x_mm"], k["cad_y_mm"], k["stabilizer_mm"] or ""])

    # layout preview with matrix positions
    from PIL import Image, ImageDraw, ImageFont
    s = 6.0                                  # px per mm
    pad = 40
    Wpx, Hpx = int(L.BOARD_W * s + 2 * pad), int(L.BOARD_H * s + 2 * pad + 70)
    im = Image.new("RGB", (Wpx, Hpx), V.PALETTE["paper"])
    dr = ImageDraw.Draw(im)
    f_title = ImageFont.truetype(V.SEGOE_BOLD, 30)
    f_lab = ImageFont.truetype(V.SEGOE_BOLD, 17)
    f_rc = ImageFont.truetype(V.SEGOE, 13)
    dr.text((pad, 18), f"Vamora75 rev {L.REVISION} - 82 keys, 6 x 16 matrix (COL2ROW), labels = row,col", font=f_title,
            fill=V.PALETTE["ink"])
    oy = pad + 60
    dr.rounded_rectangle((pad, oy, pad + L.BOARD_W * s, oy + L.BOARD_H * s), radius=6, outline="#9aa0aa", width=2)
    for k in L.keys():
        x0 = pad + (L.MARGIN + k["x"] * L.U + 0.5) * s
        y0 = oy + (L.MARGIN + k["y"] * L.U + 0.5) * s
        x1 = x0 + (k["w"] * L.U - 1.0) * s
        y1 = y0 + (L.U - 1.0) * s
        fill = V.PALETTE["brass"] if k["label"] in ("Esc", "Enter") else "#ffffff"
        dr.rounded_rectangle((x0, y0, x1, y1), radius=8, fill=fill, outline="#3a3f4a", width=2)
        tc = V.PALETTE["ink"]
        dr.text(((x0 + x1) / 2, y0 + 30), k["label"], font=f_lab, fill=tc, anchor="mm")
        dr.text(((x0 + x1) / 2, y1 - 22), f"{k['row']},{k['col']}", font=f_rc, fill=tc if fill != "#ffffff" else "#6a6f79", anchor="mm")
    im.save(ROOT / "Previews" / "layout.png")
    print("layout.json, key_positions.csv, layout.png:", len(keys), "keys")
