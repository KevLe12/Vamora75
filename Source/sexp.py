"""Tiny S-expression reader/writer for KiCad files (keeps KiCad's tab formatting)."""
from __future__ import annotations

import re


class Sym(str):
    """Unquoted atom."""


_tok = re.compile(r'\s*(?:(\()|(\))|"((?:[^"\\]|\\.)*)"|([^\s()"]+))', re.S)


def loads(text: str):
    stack, cur = [], []
    pos = 0
    while True:
        m = _tok.match(text, pos)
        if not m:
            break
        pos = m.end()
        if m.group(1):
            stack.append(cur)
            cur = []
        elif m.group(2):
            done = cur
            cur = stack.pop()
            cur.append(done)
        elif m.group(3) is not None:
            cur.append(m.group(3).replace('\\"', '"').replace("\\\\", "\\"))
        else:
            a = m.group(4)
            try:
                cur.append(int(a)) if re.fullmatch(r"-?\d+", a) else cur.append(float(a)) if re.fullmatch(r"-?\d*\.\d+(e-?\d+)?|-?\d+e-?\d+", a) else cur.append(Sym(a))
            except ValueError:
                cur.append(Sym(a))
    return cur[0]


def num(v):
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, int):
        return str(v)
    s = f"{v:.6f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def atom(a):
    if isinstance(a, Sym):
        return str(a)
    if isinstance(a, str):
        return '"' + a.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'
    return num(a)


def dumps(e, indent=0):
    if not isinstance(e, list):
        return atom(e)
    if e and isinstance(e[0], str) and not isinstance(e[0], Sym):
        e = [Sym(e[0])] + list(e[1:])          # list heads are always bare keywords
    if all(not isinstance(x, list) for x in e):
        return "(" + " ".join(atom(x) for x in e) + ")"
    if e and e[0] == "pts":
        return "(" + " ".join(dumps(x, indent + 1) for x in e) + ")"
    s = "("
    first = True
    for x in e:
        if isinstance(x, list):
            s += NL + TAB * (indent + 1) + dumps(x, indent + 1)
        else:
            s += ("" if first else " ") + atom(x)
        first = False
    return s + NL + TAB * indent + ")"


NL, TAB = chr(10), chr(9)


def find(e, key):
    for x in e:
        if isinstance(x, list) and x and x[0] == key:
            return x
    return None


def findall(e, key):
    return [x for x in e if isinstance(x, list) and x and x[0] == key]
