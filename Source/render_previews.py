"""Render Previews/*.png from the world-frame meshes written by build_case.py (VTK, off-screen).

    python Source/render_previews.py

Geometry is the real case / plate / PCBA (KiCad STEP) / gaskets / foams; switches and
keycaps are simplified envelopes. The engraved logo is shown gold-filled.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import vtk
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import vamora_logo as V  # noqa: E402
import vamora_mech as M  # noqa: E402

ROOT = HERE.parent
MESH = ROOT / "Mechanical" / "build"
OUT = ROOT / "Previews"
A = math.radians(M.TYPING_ANGLE)
NORMAL = (0.0, -math.sin(A), math.cos(A))       # plate normal in the world frame


def hex2rgb(h):
    return tuple(int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))


PAL = {k: hex2rgb(v) for k, v in V.PALETTE.items()}
CASE = hex2rgb("#1d2f4f")                         # anodised navy
PARTS = [  # name, colour, exploded offset along the plate normal (mm), specular
    ("case_bottom", CASE, 0, 0.35),
    ("logo_inlay", PAL["gold"], 0, 0.6),
    ("foam_case", (0.20, 0.20, 0.22), 14, 0.0),
    ("pcba", None, 32, 0.25),
    ("foam_plate", (0.86, 0.85, 0.80), 46, 0.0),
    ("gaskets_lower", (0.62, 0.62, 0.66), 56, 0.0),
    ("plate", (0.07, 0.08, 0.09), 64, 0.4),
    ("gaskets_upper", (0.62, 0.62, 0.66), 72, 0.0),
    ("switches", (0.10, 0.10, 0.12), 84, 0.3),
    ("case_top", CASE, 112, 0.35),
    ("keycaps_alphas", PAL["paper"], 140, 0.15),
    ("keycaps_mods", hex2rgb("#3a3f4a"), 140, 0.15),
    ("keycaps_esc", PAL["red"], 140, 0.15),
    ("keycaps_enter", PAL["green"], 140, 0.15),
]


def actor(name, color, shift, spec):
    rd = vtk.vtkSTLReader()
    rd.SetFileName(str(MESH / f"{name}.stl"))
    rd.Update()
    nrm = vtk.vtkPolyDataNormals()
    nrm.SetInputConnection(rd.GetOutputPort())
    nrm.SetFeatureAngle(35)
    nrm.SplittingOn()
    mp = vtk.vtkPolyDataMapper()
    mp.SetInputConnection(nrm.GetOutputPort())
    a = vtk.vtkActor()
    a.SetMapper(mp)
    p = a.GetProperty()
    p.SetColor(*(color or (0.09, 0.28, 0.19)))
    p.SetSpecular(spec)
    p.SetSpecularPower(40)
    p.SetDiffuse(0.85)
    p.SetAmbient(0.12)
    a.SetPosition(*(shift * c for c in NORMAL))
    return a


def scene(mode):
    ren = vtk.vtkRenderer()
    ren.GradientBackgroundOn()
    ren.SetBackground(0.93, 0.93, 0.91)
    ren.SetBackground2(0.80, 0.81, 0.80)
    explode = mode == "exploded"
    for name, color, off, spec in PARTS:
        if mode in ("bottom",) and not name.startswith(("case_bottom", "logo")):
            continue
        if mode == "assembled" and name.startswith(("foam", "gaskets")):
            continue
        ren.AddActor(actor(name, color, off if explode else 0.0, spec))
    ren.UseFXAAOn()
    lk = vtk.vtkLightKit()
    lk.SetKeyLightIntensity(0.95)
    lk.AddLightsToRenderer(ren)
    return ren


def shoot(mode, path, size=(1800, 920)):
    ren = scene(mode)
    cam = ren.GetActiveCamera()
    cx, cy = M.CASE_W / 2, 78.0
    if mode == "assembled":
        cam.SetFocalPoint(cx, cy, 18)
        cam.SetPosition(cx + 250, cy - 430, 330)
        cam.SetViewUp(0, 0, 1)
        cam.SetViewAngle(24)
    elif mode == "exploded":
        cam.SetFocalPoint(cx, cy - 20, 80)
        cam.SetPosition(cx + 330, cy - 560, 420)
        cam.SetViewUp(0, 0, 1)
        cam.SetViewAngle(27)
    elif mode == "bottom":
        cam.SetFocalPoint(cx, cy, 0)
        cam.SetPosition(cx, cy, -600)
        cam.SetViewUp(0, 1, 0)
        cam.ParallelProjectionOn()
        cam.SetParallelScale(108)
    elif mode == "side":
        cam.SetFocalPoint(cx, cy, 24)
        cam.SetPosition(cx - 900, cy, 24)
        cam.SetViewUp(0, 0, 1)
        cam.ParallelProjectionOn()
        cam.SetParallelScale(50)
    elif mode == "top":
        cam.SetFocalPoint(cx, cy, 20)
        cam.SetPosition(cx, cy - 63, 600)     # looking down the plate normal
        cam.SetViewUp(0, 1, 0)
        cam.ParallelProjectionOn()
        cam.SetParallelScale(92)
    ren.ResetCameraClippingRange()
    win = vtk.vtkRenderWindow()
    win.SetOffScreenRendering(1)
    win.SetSize(*size)
    win.AddRenderer(ren)
    win.Render()
    w2i = vtk.vtkWindowToImageFilter()
    w2i.SetInput(win)
    w2i.SetScale(1)
    w2i.ReadFrontBufferOff()
    w2i.Update()
    wr = vtk.vtkPNGWriter()
    wr.SetFileName(str(path))
    wr.SetInputConnection(w2i.GetOutputPort())
    wr.Write()
    win.Finalize()


_MECH = __import__("json").loads((ROOT / "validation" / "mechanical.json").read_text(encoding="utf-8"))
FOOTER = "Việt Nam · USA · Morocco    |    CAD render - keycaps: ScottoKicad models, switches shown as envelopes"
CAPTIONS = {
    "assembled": "Vamora75 rev 1.1 - 82-key 75 %, 6 deg typing angle, tab-gasket mount, hot-swap",
    "exploded": "Case bottom | case foam | PCBA | plate foam | gaskets | FR4 plate | gaskets | switches | top case | keycaps",
    "bottom": "Underside - engraved Vamora75 (shown paint-filled), BOOT pin-hole, 4 bumpers",
    "side": "Profile - front {front:.1f} mm, rear {rear:.1f} mm, {M.TYPING_ANGLE:.0f} deg".format(
        front=_MECH["case"]["front_height_mm"], rear=_MECH["case"]["rear_height_mm"], M=M),
    "top": "Top view",
}


def annotate(path, mode):
    """Header band (title, caption) + render + footer band."""
    r = Image.open(path).convert("RGB")
    im = Image.new("RGB", (r.width, r.height + 160), "#f4f1ea")
    im.paste(r, (0, 110))
    dr = ImageDraw.Draw(im)
    f1 = ImageFont.truetype(V.SEGOE_BOLD, 34)
    f2 = ImageFont.truetype(V.SEGOE, 22)
    dr.text((40, 18), "VAMORA75", font=f1, fill="#15171c")
    dr.text((40, 64), CAPTIONS[mode], font=f2, fill="#3a3f4a")
    dr.text((40, im.height - 40), FOOTER,
            font=ImageFont.truetype(V.SEGOE, 18), fill="#5a606b")
    im.save(path)


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    for mode in ("assembled", "exploded", "bottom", "side"):
        p = OUT / f"{mode}.png"
        shoot(mode, p)
        annotate(p, mode)
        print("rendered", p.name, flush=True)
