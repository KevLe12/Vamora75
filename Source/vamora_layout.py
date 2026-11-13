"""Vamora75 — single source of truth for layout, matrix, board geometry and revision.

Units: millimetres. PCB coordinates are KiCad page coordinates (Y down).
Board-local coordinates ("b-coords") have their origin at the PCB's rear-left
corner, X to the right, Y toward the user (front).
"""
from __future__ import annotations

REVISION, REV_DATE = "1.7", "2026-11-12"
DESIGNERS = ("Kevin Le", "Sammy DeGraaff", "Mohammed-Mehdi Hamdaoui")
TEAM = "Vamora"

U = 19.05                    # key pitch
MARGIN = 3.0                 # PCB margin around the key field
COLS_U, ROWS_U = 16.25, 6.5  # key field size in units (arrows sit 0.25u lower)
BOARD_W = COLS_U * U + 2 * MARGIN      # 315.5625
BOARD_H = ROWS_U * U + 2 * MARGIN      # 129.825
PAGE_X0, PAGE_Y0 = 40.0, 80.0          # where the board sits on the KiCad A3 page

# (label, x[u], y[u], w[u], QMK keycode, matrix row, matrix col)
# Physical layout: all 82 positions and widths match the saved Custom PCB.
# End uses the previously empty row 0 / column 14 matrix position.
# Matrix: 6 physical rows x 16 columns (COL2ROW).
KEYS = [
    ('Esc', -0.0, -0.0, 1, 'KC_ESC', 0, 0),
    ('F1', 1.25, -0.0, 1, 'KC_F1', 0, 2),
    ('F2', 2.25, -0.0, 1, 'KC_F2', 0, 3),
    ('F3', 3.25, -0.0, 1, 'KC_F3', 0, 4),
    ('F4', 4.25, -0.0, 1, 'KC_F4', 0, 5),
    ('F5', 5.5, -0.0, 1, 'KC_F5', 0, 6),
    ('F6', 6.5, -0.0, 1, 'KC_F6', 0, 7),
    ('F7', 7.5, -0.0, 1, 'KC_F7', 0, 8),
    ('F8', 8.5, -0.0, 1, 'KC_F8', 0, 9),
    ('F9', 9.75, -0.0, 1, 'KC_F9', 0, 10),
    ('F10', 10.75, -0.0, 1, 'KC_F10', 0, 11),
    ('F11', 11.75, -0.0, 1, 'KC_F11', 0, 12),
    ('F12', 12.75, -0.0, 1, 'KC_F12', 0, 13),
    ('Del', 15.25, -0.0, 1, 'KC_DEL', 0, 15),
    ('`', -0.0, 1.25, 1, 'KC_GRV', 1, 0),
    ('1', 1.0, 1.25, 1, 'KC_1', 1, 1),
    ('2', 2.0, 1.25, 1, 'KC_2', 1, 2),
    ('3', 3.0, 1.25, 1, 'KC_3', 1, 3),
    ('4', 4.0, 1.25, 1, 'KC_4', 1, 4),
    ('5', 5.0, 1.25, 1, 'KC_5', 1, 5),
    ('6', 6.0, 1.25, 1, 'KC_6', 1, 6),
    ('7', 7.0, 1.25, 1, 'KC_7', 1, 7),
    ('8', 8.0, 1.25, 1, 'KC_8', 1, 8),
    ('9', 9.0, 1.25, 1, 'KC_9', 1, 9),
    ('0', 10.0, 1.25, 1, 'KC_0', 1, 10),
    ('-', 11.0, 1.25, 1, 'KC_MINS', 1, 11),
    ('=', 12.0, 1.25, 1, 'KC_EQL', 1, 12),
    ('Backspace', 13.0, 1.25, 2, 'KC_BSPC', 1, 13),
    ('Home', 15.25, 1.25, 1, 'KC_HOME', 1, 15),
    ('Tab', 0.0, 2.25, 1.5, 'KC_TAB', 2, 0),
    ('Q', 1.5, 2.25, 1, 'KC_Q', 2, 1),
    ('W', 2.5, 2.25, 1, 'KC_W', 2, 2),
    ('E', 3.5, 2.25, 1, 'KC_E', 2, 3),
    ('R', 4.5, 2.25, 1, 'KC_R', 2, 4),
    ('T', 5.5, 2.25, 1, 'KC_T', 2, 5),
    ('Y', 6.5, 2.25, 1, 'KC_Y', 2, 6),
    ('U', 7.5, 2.25, 1, 'KC_U', 2, 7),
    ('I', 8.5, 2.25, 1, 'KC_I', 2, 8),
    ('O', 9.5, 2.25, 1, 'KC_O', 2, 9),
    ('P', 10.5, 2.25, 1, 'KC_P', 2, 10),
    ('[', 11.5, 2.25, 1, 'KC_LBRC', 2, 11),
    (']', 12.5, 2.25, 1, 'KC_RBRC', 2, 12),
    ('\\', 13.5, 2.25, 1.5, 'KC_BSLS', 2, 13),
    ('PgUp', 15.25, 2.25, 1, 'KC_PGUP', 2, 15),
    ('Caps', 0.0, 3.25, 1.75, 'KC_CAPS', 3, 0),
    ('A', 1.75, 3.25, 1, 'KC_A', 3, 1),
    ('S', 2.75, 3.25, 1, 'KC_S', 3, 2),
    ('D', 3.75, 3.25, 1, 'KC_D', 3, 3),
    ('F', 4.75, 3.25, 1, 'KC_F', 3, 4),
    ('G', 5.75, 3.25, 1, 'KC_G', 3, 5),
    ('H', 6.75, 3.25, 1, 'KC_H', 3, 6),
    ('J', 7.75, 3.25, 1, 'KC_J', 3, 7),
    ('K', 8.75, 3.25, 1, 'KC_K', 3, 8),
    ('L', 9.75, 3.25, 1, 'KC_L', 3, 9),
    (';', 10.75, 3.25, 1, 'KC_SCLN', 3, 10),
    ("'", 11.75, 3.25, 1, 'KC_QUOT', 3, 11),
    ('Enter', 12.75, 3.25, 2.25, 'KC_ENT', 3, 13),
    ('PgDn', 15.25, 3.25, 1, 'KC_PGDN', 3, 15),
    ('LShift', -0.0, 4.25, 2.25, 'KC_LSFT', 4, 0),
    ('Z', 2.25, 4.25, 1, 'KC_Z', 4, 1),
    ('X', 3.25, 4.25, 1, 'KC_X', 4, 2),
    ('C', 4.25, 4.25, 1, 'KC_C', 4, 3),
    ('V', 5.25, 4.25, 1, 'KC_V', 4, 4),
    ('B', 6.25, 4.25, 1, 'KC_B', 4, 5),
    ('N', 7.25, 4.25, 1, 'KC_N', 4, 6),
    ('M', 8.25, 4.25, 1, 'KC_M', 4, 7),
    (',', 9.25, 4.25, 1, 'KC_COMM', 4, 8),
    ('.', 10.25, 4.25, 1, 'KC_DOT', 4, 9),
    ('/', 11.25, 4.25, 1, 'KC_SLSH', 4, 10),
    ('RShift', 12.25, 4.25, 1.75, 'KC_RSFT', 4, 12),
    ('Up', 14.25, 4.5, 1, 'KC_UP', 4, 14),
    ('End', 14.0, -0.0, 1, 'KC_END', 0, 14),
    ('LCtrl', 0.0, 5.25, 1.25, 'KC_LCTL', 5, 0),
    ('Win', 1.25, 5.25, 1.25, 'KC_LGUI', 5, 1),
    ('LAlt', 2.5, 5.25, 1.25, 'KC_LALT', 5, 2),
    ('Space', 3.75, 5.25, 6.25, 'KC_SPC', 5, 5),
    ('RAlt', 10.0, 5.25, 1, 'KC_RALT', 5, 9),
    ('Fn', 11.0, 5.25, 1, 'MO(1)', 5, 10),
    ('RCtrl', 12.0, 5.25, 1, 'KC_RCTL', 5, 11),
    ('Left', 13.25, 5.5, 1, 'KC_LEFT', 5, 13),
    ('Down', 14.25, 5.5, 1, 'KC_DOWN', 5, 14),
    ('Right', 15.25, 5.5, 1, 'KC_RGHT', 5, 15),
]
MATRIX_ROWS, MATRIX_COLS = 6, 16

# RP2040 GPIO assignment retained from rev 1.3; the bottom-mounted controller is
# near the rear-left USB connector; key functions and GPIO assignments are unchanged.
ROW_GPIO = [0, 6, 5, 4, 3, 2]
COL_GPIO = [29, 28, 27, 26, 24, 23, 22, 21, 20, 19, 18, 17, 16, 8, 7, 1]
# Free: GPIO9-15, GPIO25. GP25 stays free on purpose (status LED of the
# Raspberry Pi Pico CircuitPython build used as the no-compile firmware option).

STAB_SPACING = {2.0: 11.938, 2.25: 11.938, 2.75: 11.938, 6.25: 50.0, 7.0: 57.15}


def fp_size_name(w: float) -> str:
    return {1: "1.00u", 1.25: "1.25u", 1.5: "1.50u", 1.75: "1.75u", 2: "2.00u", 2.25: "2.25u", 6.25: "6.25u"}[w]


def switch_footprint(k):
    return f"Hotswap_MX_{fp_size_name(k['w'])}" + ("_USB" if k['label']=='F1' else "")


def keys():
    """List of dicts with computed centres (board-local b-coords and KiCad page coords)."""
    out = []
    for n, (label, x, y, w, kc, r, c) in enumerate(KEYS, start=1):
        bx = MARGIN + (x + w / 2) * U
        by = MARGIN + (y + 0.5) * U
        out.append(dict(n=n, ref=f"SW{n}", diode=f"D{n}", label=label, x=x, y=y, w=w, kc=kc,
                        row=r, col=c, bx=bx, by=by, px=PAGE_X0 + bx, py=PAGE_Y0 + by,
                        stab=STAB_SPACING.get(w)))
    return out


def check():
    ks = keys()
    assert len(ks) == 82
    cells = {(k["row"], k["col"]) for k in ks}
    assert len(cells) == 82, "duplicate matrix position"
    assert all(0 <= k["row"] < MATRIX_ROWS and 0 <= k["col"] < MATRIX_COLS for k in ks)
    gp = ROW_GPIO + COL_GPIO
    assert len(set(gp)) == len(gp) and 25 not in gp
    return True


if __name__ == "__main__":
    check()
    print(f"board {BOARD_W:.4f} x {BOARD_H:.4f} mm, {len(KEYS)} keys, matrix {MATRIX_ROWS}x{MATRIX_COLS}")
