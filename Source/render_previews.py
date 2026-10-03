"""Product renders: Previews/*.png from the coloured meshes written by build_case.py (VTK, off-screen).

    python Source/render_previews.py [view ...]      (all views by default)

Geometry is the real case, plate, PCBA (KiCad STEP with solder mask, silkscreen and every
3D model), Joe Scotto's MX switch on all 82 positions, gaskets, foams and the sculpted
keycaps. Physically based materials, image-based studio lighting, ambient occlusion, a soft
floor shadow and 2x supersampling. Views:

  assembled   hero shot, front left            exploded   every layer along the plate normal
  top         from above                       side       profile (front / rear height)
  bottom      underside, engraved name         pcb_plate  PCB + plate + components, no case
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import vtk
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from vtk.util import numpy_support as ns

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cad_mesh as C  # noqa: E402
import vamora_layout as L  # noqa: E402
import vamora_logo as V  # noqa: E402
import vamora_mech as M  # noqa: E402

ROOT = HERE.parent
MESH = ROOT / "Mechanical" / "build"
OUT = ROOT / "Previews"
A = math.radians(M.TYPING_ANGLE)
NORMAL = np.array((0.0, -math.sin(A), math.cos(A)))       # plate normal in the world frame
SIZE = (1800, 1000)
SS = 2                                                      # supersampling
BG_TOP, BG_BOTTOM = (0.965, 0.962, 0.955), (0.885, 0.882, 0.875)
_MECH = json.loads((ROOT / "validation" / "mechanical.json").read_text(encoding="utf-8"))

# part, exploded offset along the plate normal (mm)
EXPLODE = {"case_bottom": 0, "logo_inlay": 0, "foam_case": 16, "pcba": 36, "foam_plate": 52, "gaskets_lower": 62,
           "plate": 72, "gaskets_upper": 82, "switch": 96, "case_top": 128, "keycaps": 158}
VIEWS = {
    "assembled": ["case_bottom", "case_top", "plate", "pcba", "switch", "keycaps"],
    "top": ["case_bottom", "case_top", "plate", "pcba", "switch", "keycaps"],
    "side": ["case_bottom", "case_top", "plate", "pcba", "switch", "keycaps"],
    "exploded": list(EXPLODE),
    "bottom": ["case_bottom", "logo_inlay"],
    "pcb_plate": ["pcba", "plate", "switch"],
}
CAPTIONS = {
    "assembled": "82-key 75 %, 6° typing angle, tab-gasket mount, hot-swap",
    "top": "Exploded 75 % Windows ANSI layout, separated arrow cluster",
    "exploded": "Case bottom · case foam · PCBA · plate foam · gaskets · FR4 plate · gaskets · switches · top case · keycaps",
    "bottom": "Underside: engraved Vamora75 (shown paint-filled), BOOT pin-hole, 4 bumpers",
    "side": "Profile: front {f:.1f} mm, rear {r:.1f} mm, {a:.0f}° typing angle".format(
        f=_MECH["case"]["front_height_mm"], r=_MECH["case"]["rear_height_mm"], a=M.TYPING_ANGLE),
    "pcb_plate": "PCB + FR4 plate + components: Joe Scotto's MX switches, PCB-mount stabilisers, Kailh sockets",
}


# ------------------------------------------------------------------ materials
def material(rgb, part):
    """(metallic, roughness) from the colour and the part."""
    r, g, b = rgb
    if r > 0.6 and 0.4 < g < 0.8 and b < 0.45 and r - b > 0.3:            # gold: ENIG, brass, plated pins
        return (0.0, 0.45) if part == "keycaps" else (1.0, 0.28)
    if part in ("case_bottom", "case_top"):
        return 0.55, 0.38                                               # bead-blasted anodised finish
    if part == "keycaps":
        return 0.0, 0.62                                                # PBT
    if part in ("foam_case", "foam_plate", "gaskets_lower", "gaskets_upper"):
        return 0.0, 0.95
    if max(rgb) - min(rgb) < 0.06 and 0.45 < r < 0.8:                   # bare metal (tin, steel)
        return 1.0, 0.35
    if max(rgb) < 0.12:                                                 # black solder mask: satin
        return 0.0, 0.75
    return 0.0, 0.42                                                    # plastics


def polydata(v, f):
    pts = vtk.vtkPoints()
    pts.SetData(ns.numpy_to_vtk(np.ascontiguousarray(v, np.float32), deep=True))
    cells = vtk.vtkCellArray()
    off = ns.numpy_to_vtkIdTypeArray(np.arange(0, 3 * len(f) + 1, 3, dtype=np.int64), deep=True)
    con = ns.numpy_to_vtkIdTypeArray(np.ascontiguousarray(f.reshape(-1), np.int64), deep=True)
    cells.SetData(off, con)
    pd = vtk.vtkPolyData()
    pd.SetPoints(pts)
    pd.SetPolys(cells)
    nrm = vtk.vtkPolyDataNormals()
    nrm.SetInputData(pd)
    nrm.SetFeatureAngle(32)
    nrm.SplittingOn()
    nrm.ConsistencyOff()
    nrm.Update()
    return nrm.GetOutput()


def vtk_matrix(m):
    vm = vtk.vtkMatrix4x4()
    for r in range(4):
        for c in range(4):
            vm.SetElement(r, c, float(m[r, c]))
    return vm


_CACHE = {}


def mappers(part):
    if part not in _CACHE:
        out = []
        for rgb, (v, f) in C.load_buckets(MESH / f"{part}.npz").items():
            mp = vtk.vtkPolyDataMapper()
            mp.SetInputData(polydata(v, f))
            mp.SetResolveCoincidentTopologyToPolygonOffset()
            out.append((tuple(float(c) for c in rgb), mp))
        _CACHE[part] = out
    return _CACHE[part]


def actors(part, shift=0.0, pre=None):
    """Actors of one part; `shift` along the plate normal; `pre` = extra 4x4 applied first (world)."""
    mats = [np.eye(4)]
    if part == "switch":
        mats = list(np.load(MESH / "switch_instances.npy"))
    out = []
    for rgb, mp in mappers(part):
        met, rough = material(rgb, part)
        for m in mats:
            a = vtk.vtkActor()
            a.SetMapper(mp)
            p = a.GetProperty()
            p.SetInterpolationToPBR()
            p.SetColor(*rgb)
            p.SetMetallic(met)
            p.SetRoughness(rough)
            mm = C.mat_translate(*(shift * NORMAL)) @ m
            if pre is not None:
                mm = pre @ mm
            a.SetUserMatrix(vtk_matrix(mm))
            out.append(a)
    return out


# ------------------------------------------------------------------ studio
def environment():
    """Equirectangular studio: grey cyclorama, two soft boxes and a top light."""
    h, w = 512, 1024
    y = np.linspace(0.0, 1.0, h)[:, None, None]
    img = (0.52 + 0.46 * (1 - y) ** 1.2) * np.ones((h, w, 3))
    img = Image.fromarray(np.clip(img * 255, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(img)
    d.rectangle((90, 90, 330, 230), fill=(255, 255, 255))      # key soft box (front left)
    d.rectangle((600, 120, 820, 220), fill=(232, 232, 232))     # fill soft box
    d.rectangle((0, 0, w, 36), fill=(250, 250, 250))            # ceiling light
    img = img.filter(ImageFilter.GaussianBlur(14))
    arr = np.asarray(img)[::-1].copy()
    vi = vtk.vtkImageData()
    vi.SetDimensions(w, h, 1)
    sc = ns.numpy_to_vtk(arr.reshape(-1, 3), deep=True, array_type=vtk.VTK_UNSIGNED_CHAR)
    sc.SetNumberOfComponents(3)
    vi.GetPointData().SetScalars(sc)
    tex = vtk.vtkTexture()
    tex.SetInputData(vi)
    tex.SetColorModeToDirectScalars()
    tex.MipmapOn()
    tex.InterpolateOn()
    return tex


def floor_shadow(bounds_xy, z=0.0, soft=14.0, strength=0.55):
    """A soft contact shadow under the model: a blurred rounded rectangle on a textured floor quad."""
    x0, y0, x1, y1 = bounds_xy
    pad = 3 * soft
    X0, Y0, X1, Y1 = x0 - pad, y0 - pad, x1 + pad, y1 + pad
    res = 3.0                                                   # px per mm
    W, H = int((X1 - X0) * res), int((Y1 - Y0) * res)
    im = Image.new("L", (W, H), 0)
    ImageDraw.Draw(im).rounded_rectangle(((x0 - X0) * res, (Y1 - y1) * res, (x1 - X0) * res, (Y1 - y0) * res),
                                         radius=8 * res, fill=255)
    im = im.filter(ImageFilter.GaussianBlur(soft * res / 2))
    a = (np.asarray(im)[::-1].astype(np.float32) / 255 * strength * 255).astype(np.uint8)
    rgba = np.zeros((H, W, 4), np.uint8)
    rgba[..., 3] = a
    vi = vtk.vtkImageData()
    vi.SetDimensions(W, H, 1)
    sc = ns.numpy_to_vtk(rgba.reshape(-1, 4), deep=True, array_type=vtk.VTK_UNSIGNED_CHAR)
    sc.SetNumberOfComponents(4)
    vi.GetPointData().SetScalars(sc)
    tex = vtk.vtkTexture()
    tex.SetInputData(vi)
    tex.SetColorModeToDirectScalars()
    tex.InterpolateOn()
    pl = vtk.vtkPlaneSource()
    pl.SetOrigin(X0, Y0, z)
    pl.SetPoint1(X1, Y0, z)
    pl.SetPoint2(X0, Y1, z)
    mp = vtk.vtkPolyDataMapper()
    mp.SetInputConnection(pl.GetOutputPort())
    act = vtk.vtkActor()
    act.SetMapper(mp)
    act.SetTexture(tex)
    act.GetProperty().SetLighting(False)
    act.ForceTranslucentOn()
    return act


def renderer(env, ao=True):
    ren = vtk.vtkRenderer()
    ren.GradientBackgroundOn()
    ren.SetBackground(*BG_BOTTOM)
    ren.SetBackground2(*BG_TOP)
    ren.UseImageBasedLightingOn()
    ren.SetEnvironmentTexture(env, False)
    ren.AutomaticLightCreationOff()
    for pos, inten in (((-350, -450, 650), 0.85), ((600, -150, 350), 0.35), ((180, 600, 300), 0.3)):
        lt = vtk.vtkLight()
        lt.SetLightTypeToSceneLight()
        lt.SetPosition(*pos)
        lt.SetFocalPoint(M.CASE_W / 2, 80, 0)
        lt.SetIntensity(inten)
        ren.AddLight(lt)
    if not ao:                                                  # flat views: AO only adds depth banding
        return ren
    basic = vtk.vtkRenderStepsPass()
    ssao = vtk.vtkSSAOPass()
    ssao.SetRadius(2.5)                                         # mm: contact shading between parts only
    ssao.SetBias(0.35)                                          # large enough to avoid banding on curved caps
    ssao.SetKernelSize(64)
    ssao.BlurOn()
    ssao.SetDelegatePass(basic)
    ren.SetPass(ssao)
    return ren


def pcb_plate_pre():
    """For the PCB + plate view: undo the case tilt and set the board on the floor."""
    inv = np.linalg.inv(C.mat_rot_x(M.TYPING_ANGLE) @ C.mat_translate(M.MARGIN, M.MARGIN, -(M.FLOOR_Z - M.FLOOR_T)))
    return C.mat_translate(0, 0, 4.2) @ inv     # sockets (~4 mm under the board) rest on the floor


def scene(view, env):
    ren = renderer(env, ao=view in ("assembled", "exploded", "pcb_plate"))
    explode = view == "exploded"
    pre = pcb_plate_pre() if view == "pcb_plate" else None
    for part in VIEWS[view]:
        for a in actors(part, EXPLODE[part] if explode else 0.0, pre):
            ren.AddActor(a)
    if view == "pcb_plate":
        ren.AddActor(floor_shadow((0, 0, M.BW, M.BH), z=0.0, soft=8.0, strength=0.35))
    elif view != "bottom":
        d = _MECH["case"]["footprint_mm"]
        ren.AddActor(floor_shadow((0, 0, d[0], d[1]), z=0.0, soft=12.0, strength=0.45))
    return ren


def camera(ren, view):
    cam = ren.GetActiveCamera()
    cx, cy = M.CASE_W / 2, 80.0
    cam.SetViewUp(0, 0, 1)
    if view == "assembled":
        cam.SetFocalPoint(cx + 10, cy - 6, 14)
        cam.SetPosition(cx - 300, cy - 560, 240)
        cam.SetViewAngle(23)
    elif view == "exploded":
        cam.SetFocalPoint(cx + 6, cy - 6, 88)
        cam.SetPosition(cx - 380, cy - 640, 470)
        cam.SetViewAngle(25)
    elif view == "top":
        cam.SetFocalPoint(cx, cy + 2, 20)
        cam.SetPosition(cx, cy - 60, 700)
        cam.SetViewUp(0, 1, 0)
        cam.SetViewAngle(24)
    elif view == "bottom":
        cam.SetFocalPoint(cx, cy, 0)
        cam.SetPosition(cx, cy, -620)
        cam.SetViewUp(0, 1, 0)
        cam.SetViewAngle(25)
    elif view == "side":
        cam.SetFocalPoint(cx, cy, 22)
        cam.SetPosition(cx - 1200, cy, 22)
        cam.ParallelProjectionOn()
        cam.SetParallelScale(56)
    elif view == "pcb_plate":
        cx, cy = M.BW / 2, M.BH / 2
        cam.SetFocalPoint(cx + 8, cy - 4, 6)
        cam.SetPosition(cx - 260, cy - 470, 280)
        cam.SetViewAngle(24)
    ren.ResetCameraClippingRange()


def shoot(view, path, env):
    ren = scene(view, env)
    camera(ren, view)
    win = vtk.vtkRenderWindow()
    win.SetOffScreenRendering(1)
    win.SetMultiSamples(0)
    win.SetSize(SIZE[0] * SS, SIZE[1] * SS)
    win.AddRenderer(ren)
    win.Render()
    w2i = vtk.vtkWindowToImageFilter()
    w2i.SetInput(win)
    w2i.ReadFrontBufferOff()
    w2i.Update()
    img = w2i.GetOutput()
    w, h, _ = img.GetDimensions()
    arr = ns.vtk_to_numpy(img.GetPointData().GetScalars()).reshape(h, w, -1)[::-1, :, :3]
    win.Finalize()
    im = Image.fromarray(np.ascontiguousarray(arr)).resize(SIZE, Image.LANCZOS)
    caption(im, view)
    im.save(path, optimize=True)


def caption(im, view):
    d = ImageDraw.Draw(im)
    f1 = ImageFont.truetype(V.SEGOE_BLACK, 30)
    f2 = ImageFont.truetype(V.SEGOE, 19)
    d.text((40, im.height - 78), "Vamora75", font=f1, fill="#1b1d22")
    d.text((40 + d.textlength("Vamora75", font=f1) + 14, im.height - 70), f"rev {L.REVISION}", font=f2, fill="#6b7079")
    d.text((40, im.height - 38), CAPTIONS[view], font=f2, fill="#4a4f58")


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    env = environment()
    for view in sys.argv[1:] or ("assembled", "exploded", "top", "side", "bottom", "pcb_plate"):
        shoot(view, OUT / f"{view}.png", env)
        print("rendered", f"{view}.png", flush=True)
