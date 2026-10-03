"""Board stackup with colours (black solder mask, white silkscreen) for a saved .kicad_pcb.

KiCad's Python API does not expose the stackup, so the block is written into the saved file.
KiCad keeps it on every later save (DRC --save-board, opening and saving in the editor);
the 3D viewer, `kicad-cli pcb render --use-board-stackup-colors` and the fab notes follow it.
"""
from pathlib import Path

_STACKUP = """\t\t(stackup
\t\t\t(layer "F.SilkS"
\t\t\t\t(type "Top Silk Screen")
\t\t\t\t(color "White")
\t\t\t)
\t\t\t(layer "F.Paste"
\t\t\t\t(type "Top Solder Paste")
\t\t\t)
\t\t\t(layer "F.Mask"
\t\t\t\t(type "Top Solder Mask")
\t\t\t\t(color "{mask}")
\t\t\t\t(thickness 0.01)
\t\t\t)
\t\t\t(layer "F.Cu"
\t\t\t\t(type "copper")
\t\t\t\t(thickness 0.035)
\t\t\t)
\t\t\t(layer "dielectric 1"
\t\t\t\t(type "core")
\t\t\t\t(thickness {core})
\t\t\t\t(material "FR4")
\t\t\t\t(epsilon_r 4.5)
\t\t\t\t(loss_tangent 0.02)
\t\t\t)
\t\t\t(layer "B.Cu"
\t\t\t\t(type "copper")
\t\t\t\t(thickness 0.035)
\t\t\t)
\t\t\t(layer "B.Mask"
\t\t\t\t(type "Bottom Solder Mask")
\t\t\t\t(color "{mask}")
\t\t\t\t(thickness 0.01)
\t\t\t)
\t\t\t(layer "B.Paste"
\t\t\t\t(type "Bottom Solder Paste")
\t\t\t)
\t\t\t(layer "B.SilkS"
\t\t\t\t(type "Bottom Silk Screen")
\t\t\t\t(color "White")
\t\t\t)
\t\t\t(copper_finish "{finish}")
\t\t\t(dielectric_constraints no)
\t\t)
"""


def set_stackup(path, thickness=1.6, mask="#101114F2", finish="ENIG"):
    """Insert a 2-layer stackup (FR4 core, coloured mask, white silk) into a saved board file.
    The mask is a near-opaque black: KiCad's "Black" preset is translucent and renders brown."""
    p = Path(path)
    t = p.read_text(encoding="utf-8")
    if "(stackup" in t:
        raise ValueError(f"{p.name} already has a stackup")
    core = round(thickness - 2 * 0.035 - 2 * 0.01, 4)
    block = _STACKUP.format(mask=mask, finish=finish, core=core)
    assert t.count("\t(setup\n") == 1, "board file without a (setup) section"
    p.write_text(t.replace("\t(setup\n", "\t(setup\n" + block, 1), encoding="utf-8")
