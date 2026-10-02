"""Vamora75 rev 1.1 - 6 x 16 COL2ROW matrix on a bare RP2040 (CircuitPython, Raspberry Pi Pico build)."""
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
