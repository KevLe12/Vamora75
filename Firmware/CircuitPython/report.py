"""USB boot-keyboard (6KRO) and consumer reports; no runtime library dependencies."""
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
