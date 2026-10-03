"""Coloured meshes and coloured assemblies from STEP data (OpenCASCADE XCAF, CAD venv).

* `step_buckets(path)`: triangles of a coloured STEP assembly (e.g. KiCad's PCBA export),
  grouped by colour, in the STEP frame. Instanced parts are triangulated once and copied.
* `shape_buckets(shape, rgb)`: the same for one CadQuery/OCCT shape in a single colour.
* `save_buckets` / `load_buckets`: compressed .npz files the VTK renders read.
* `Assembly`: a coloured STEP writer that can embed another STEP file *with its own colours
  and instances* (the KiCad PCBA) next to CadQuery parts.
* `step_instances` + `write_glb`: a light, instanced, coloured glTF for viewers.

Matrices are 4x4 numpy arrays (millimetres); `xf` applies one to an (N, 3) vertex array.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from OCP.BRep import BRep_Tool
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.IFSelect import IFSelect_RetDone
from OCP.Interface import Interface_Static
from OCP.Quantity import Quantity_Color, Quantity_TypeOfColor
from OCP.STEPCAFControl import STEPCAFControl_Reader, STEPCAFControl_Writer
from OCP.STEPControl import STEPControl_AsIs
from OCP.TCollection import TCollection_AsciiString, TCollection_ExtendedString
from OCP.TDataStd import TDataStd_Name
from OCP.TDF import TDF_Label, TDF_LabelSequence, TDF_Tool
from OCP.TDocStd import TDocStd_Document
from OCP.TopAbs import TopAbs_FACE, TopAbs_REVERSED
from OCP.TopExp import TopExp
from OCP.TopLoc import TopLoc_Location
from OCP.TopoDS import TopoDS
from OCP.TopTools import TopTools_IndexedMapOfShape
from OCP.XCAFDoc import XCAFDoc_ColorType, XCAFDoc_DocumentTool

LIN, ANG = 0.05, 0.35            # default tessellation: 0.05 mm chordal deviation, 0.35 rad


# ------------------------------------------------------------------ matrices
def mat_translate(x, y, z):
    m = np.eye(4)
    m[:3, 3] = (x, y, z)
    return m


def mat_rot_x(deg):
    a = np.radians(deg)
    m = np.eye(4)
    m[1:3, 1:3] = [[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]]
    return m


def xf(m, v):
    return v @ m[:3, :3].T + m[:3, 3]


def _loc_mat(loc):
    t = loc.Transformation()
    m = np.eye(4)
    for r in range(3):
        for c in range(4):
            m[r, c] = t.Value(r + 1, c + 1)
    return m


# ------------------------------------------------------------------ triangles
def _mesh(shape, lin=LIN, ang=ANG):
    BRepMesh_IncrementalMesh(shape, lin, False, ang, True)


def _face_tris(face):
    loc = TopLoc_Location()
    tri = BRep_Tool.Triangulation_s(face, loc)
    if tri is None:
        return None
    t = loc.Transformation()
    pts = [tri.Node(i).Transformed(t) for i in range(1, tri.NbNodes() + 1)]
    v = np.array([(p.X(), p.Y(), p.Z()) for p in pts], float)
    f = np.array([tri.Triangle(i).Get() for i in range(1, tri.NbTriangles() + 1)], np.int64) - 1
    if face.Orientation() == TopAbs_REVERSED:
        f = f[:, ::-1]
    return v, f


def _faces(shape):
    m = TopTools_IndexedMapOfShape()
    TopExp.MapShapes_s(shape, TopAbs_FACE, m)
    return m


def _add(buckets, rgb, v, f):
    buckets.setdefault(rgb, []).append((v, f))


def merge(buckets):
    """{rgb: [(V, F), ...]} -> {rgb: (V, F)} with one vertex/face array per colour."""
    out = {}
    for rgb, parts in buckets.items():
        if isinstance(parts, tuple):
            out[rgb] = parts
            continue
        vs, fs, n = [], [], 0
        for v, f in parts:
            vs.append(v)
            fs.append(f + n)
            n += len(v)
        out[rgb] = (np.concatenate(vs), np.concatenate(fs))
    return out


def shape_buckets(shape, rgb, matrix=None, lin=LIN, ang=ANG):
    """One shape (CadQuery object or TopoDS_Shape), one colour."""
    s = shape.val() if hasattr(shape, "val") else shape
    s = s.wrapped if hasattr(s, "wrapped") else s
    _mesh(s, lin, ang)
    out = {}
    fm = _faces(s)
    for i in range(1, fm.Extent() + 1):
        r = _face_tris(TopoDS.Face_s(fm.FindKey(i)))
        if r is not None:
            v, f = r
            _add(out, rgb, v if matrix is None else xf(matrix, v), f)
    return merge(out)


def combine(*bucket_dicts):
    out = {}
    for d in bucket_dicts:
        for rgb, vf in d.items():
            _add(out, rgb, *vf)
    return merge(out)


def save_buckets(buckets, path):
    b = merge(buckets)
    arrays = {"colors": np.array([list(c) for c in b], float).reshape(-1, 3)}
    for i, (v, f) in enumerate(b.values()):
        arrays[f"v{i}"] = v.astype(np.float32)
        arrays[f"f{i}"] = f.astype(np.int32)
    np.savez_compressed(path, **arrays)


def load_buckets(path):
    z = np.load(path)
    return {tuple(c): (z[f"v{i}"], z[f"f{i}"]) for i, c in enumerate(z["colors"])}


# ------------------------------------------------------------------ XCAF documents
def new_doc():
    doc = TDocStd_Document(TCollection_ExtendedString("XmlOcaf"))
    return doc, XCAFDoc_DocumentTool.ShapeTool_s(doc.Main()), XCAFDoc_DocumentTool.ColorTool_s(doc.Main())


def read_step(path, doc=None):
    """Read a STEP file with colours and names; returns (doc, shape tool, colour tool, free labels)."""
    doc, st, ct = new_doc() if doc is None else doc
    before = TDF_LabelSequence()
    st.GetFreeShapes(before)
    known = {_entry(before.Value(i)) for i in range(1, before.Length() + 1)}
    r = STEPCAFControl_Reader()
    r.SetColorMode(True)
    r.SetNameMode(True)
    if r.ReadFile(str(path)) != IFSelect_RetDone:
        raise IOError(f"cannot read {path}")
    r.Transfer(doc)
    free = TDF_LabelSequence()
    st.GetFreeShapes(free)
    new = [free.Value(i) for i in range(1, free.Length() + 1) if _entry(free.Value(i)) not in known]
    return doc, st, ct, new


def _entry(lab):
    s = TCollection_AsciiString()
    TDF_Tool.Entry_s(lab, s)
    return s.ToCString()


def label_name(lab):
    n = TDataStd_Name()
    return n.Get().ToExtString() if lab.FindAttribute(TDataStd_Name.GetID_s(), n) else ""


def label_color(lab):
    from OCP.XCAFDoc import XCAFDoc_ColorTool
    c = Quantity_Color()
    for t in (XCAFDoc_ColorType.XCAFDoc_ColorSurf, XCAFDoc_ColorType.XCAFDoc_ColorGen):
        if XCAFDoc_ColorTool.GetColor_s(lab, t, c):
            return (round(c.Red(), 4), round(c.Green(), 4), round(c.Blue(), 4))
    return None


def _leaves(st, lab, m, inherited, out):
    col = label_color(lab) or inherited
    if st.IsReference_s(lab):
        ref = TDF_Label()
        st.GetReferredShape_s(lab, ref)
        _leaves(st, ref, m @ _loc_mat(st.GetLocation_s(lab)), label_color(lab) or label_color(ref) or inherited, out)
    elif st.IsAssembly_s(lab):
        comps = TDF_LabelSequence()
        st.GetComponents_s(lab, comps, False)
        for i in range(1, comps.Length() + 1):
            _leaves(st, comps.Value(i), m, col, out)
    else:
        out.append((lab, m, col))


def _proto(st, lab, default, lin, ang, force=False):
    """Triangles of one simple-shape label in its own frame, by colour (face > solid > label colour;
    `force` paints every face in `default`)."""
    shape = st.GetShape_s(lab)
    _mesh(shape, lin, ang)
    fm = _faces(shape)
    face_col = {}
    subs = TDF_LabelSequence()
    if not force:
        st.GetSubShapes_s(lab, subs)
    for j in range(1, subs.Length() + 1):
        sl = subs.Value(j)
        c = label_color(sl)
        if not c:
            continue
        s = st.GetShape_s(sl)
        if s.ShapeType() == TopAbs_FACE:
            face_col[fm.FindIndex(s)] = (2, c)
        else:
            sm = _faces(s)
            for k in range(1, sm.Extent() + 1):
                idx = fm.FindIndex(sm.FindKey(k))
                if face_col.get(idx, (0, None))[0] < 2:
                    face_col[idx] = (1, c)
    out = {}
    for i in range(1, fm.Extent() + 1):
        r = _face_tris(TopoDS.Face_s(fm.FindKey(i)))
        if r is not None:
            _add(out, face_col.get(i, (0, default))[1], *r)
    return merge(out)


def step_instances(path, matrix=None, overrides=None, default=(0.6, 0.6, 0.6), lin=LIN, ang=ANG, skip=None):
    """A STEP assembly as [(name, {rgb: (V, F)} in the part's own frame, [4x4 placement, ...])]: every
    part is triangulated once, however often it is placed. `overrides`: {label name: rgb} repaints
    those parts completely (e.g. KiCad's pads in ENIG gold); `skip`: name substrings to leave out."""
    doc, st, ct, free = read_step(path)
    leaves = []
    for lab in free:
        _leaves(st, lab, np.eye(4) if matrix is None else matrix, None, leaves)
    protos = {}
    for lab, m, col in leaves:
        name = label_name(lab)
        if skip and any(s in name for s in skip):
            continue
        force = name in (overrides or {})
        col = overrides[name] if force else (col or default)
        k = (_entry(lab), col)
        if k not in protos:
            protos[k] = (name, _proto(st, lab, col, lin, ang, force), [])
        protos[k][2].append(m)
    return list(protos.values())


def step_buckets(path, matrix=None, overrides=None, default=(0.6, 0.6, 0.6), lin=LIN, ang=ANG, skip=None):
    """Coloured triangles of a STEP assembly, all placements merged (see step_instances)."""
    out = {}
    for _, buckets, mats in step_instances(path, matrix, overrides, default, lin, ang, skip):
        for m in mats:
            for rgb, (v, f) in buckets.items():
                _add(out, rgb, xf(m, v), f)
    return merge(out)


def pbr(rgb):
    """(metallic, roughness) for a colour: gold and bare metal shine, everything else is plastic."""
    r, g, b = rgb
    if r > 0.6 and 0.4 < g < 0.8 and b < 0.45 and r - b > 0.3:
        return 1.0, 0.3
    if max(rgb) - min(rgb) < 0.06 and 0.45 < r < 0.8:
        return 1.0, 0.35
    return 0.0, 0.55


def write_glb(parts, path):
    """Binary glTF (metres, Y up) from [(name, {rgb: (V, F)}, [4x4 placement in mm, ...])]. Each part's
    mesh is stored once and placed by nodes, so repeated parts (switches, sockets, diodes) cost
    nothing; opens in Windows 3D Viewer, Blender or any web glTF viewer."""
    import trimesh
    conv = np.diag([0.001, 0.001, 0.001, 1.0]) @ np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, -1, 0, 0], [0, 0, 0, 1.0]])
    sc = trimesh.Scene()
    for p, (name, buckets, mats) in enumerate(parts):
        for c, (rgb, (v, f)) in enumerate(merge(buckets).items()):
            met, rough = pbr(rgb)
            mesh = trimesh.Trimesh(vertices=v, faces=f, process=False)
            mesh.visual = trimesh.visual.TextureVisuals(material=trimesh.visual.material.PBRMaterial(
                baseColorFactor=[int(255 * x) for x in rgb] + [255], metallicFactor=met, roughnessFactor=rough))
            geom = f"{p:03d}_{name}_{c}"
            for i, m in enumerate(mats):
                if i == 0:
                    sc.add_geometry(mesh, geom_name=geom, node_name=f"{geom}_{i}", transform=conv @ m)
                else:
                    sc.graph.update(frame_to=f"{geom}_{i}", frame_from=sc.graph.base_frame, matrix=conv @ m,
                                    geometry=geom)
    Path(path).write_bytes(trimesh.exchange.gltf.export_glb(sc, include_normals=True))


# ------------------------------------------------------------------ coloured STEP / GLB writer
class Assembly:
    """Root assembly in an XCAF document. Parts keep shared instances; embedded STEP files keep
    their own colours, names and instances (only the colours named in `recolour` change)."""

    def __init__(self, name):
        self.doc, self.st, self.ct = new_doc()
        self.root = self.st.NewShape()
        TDataStd_Name.Set_s(self.root, TCollection_ExtendedString(name))

    @staticmethod
    def _loc(m):
        from OCP.gp import gp_Trsf
        t = gp_Trsf()
        t.SetValues(*[float(m[r, c]) for r in range(3) for c in range(4)])
        return TopLoc_Location(t)

    def _color(self, lab, rgb):
        col = Quantity_Color(*rgb, Quantity_TypeOfColor.Quantity_TOC_RGB)
        self.ct.SetColor(lab, col, XCAFDoc_ColorType.XCAFDoc_ColorGen)
        self.ct.SetColor(lab, col, XCAFDoc_ColorType.XCAFDoc_ColorSurf)

    def add_shape(self, name, shape, rgb, matrix=None):
        s = shape.val() if hasattr(shape, "val") else shape
        s = s.wrapped if hasattr(s, "wrapped") else s
        lab = self.st.AddShape(s, True)
        TDataStd_Name.Set_s(lab, TCollection_ExtendedString(name))
        if self.st.IsAssembly_s(lab):
            comps = TDF_LabelSequence()
            self.st.GetComponents_s(lab, comps, True)
            for i in range(1, comps.Length() + 1):
                ref = TDF_Label()
                if self.st.GetReferredShape_s(comps.Value(i), ref):
                    self._color(ref, rgb)
        else:
            self._color(lab, rgb)
        c = self.st.AddComponent(self.root, lab, self._loc(np.eye(4) if matrix is None else matrix))
        TDataStd_Name.Set_s(c, TCollection_ExtendedString(name))

    def add_step(self, name, path, matrix=None, recolour=None):
        _, st, _, free = read_step(path, (self.doc, self.st, self.ct))
        if recolour:                       # {label name: rgb}: the label and all its coloured sub-shapes
            labs = TDF_LabelSequence()
            st.GetShapes(labs)
            for i in range(1, labs.Length() + 1):
                lab = labs.Value(i)
                rgb = recolour.get(label_name(lab))
                if rgb:
                    self._color(lab, rgb)
                    subs = TDF_LabelSequence()
                    st.GetSubShapes_s(lab, subs)
                    for j in range(1, subs.Length() + 1):
                        if label_color(subs.Value(j)):
                            self._color(subs.Value(j), rgb)
        for lab in free:
            c = self.st.AddComponent(self.root, lab, self._loc(np.eye(4) if matrix is None else matrix))
            TDataStd_Name.Set_s(c, TCollection_ExtendedString(name))

    def write_step(self, path):
        self.st.UpdateAssemblies()
        Interface_Static.SetIVal_s("write.surfacecurve.mode", 0)
        w = STEPCAFControl_Writer()
        w.SetColorMode(True)
        w.SetNameMode(True)
        w.Transfer(self.doc, STEPControl_AsIs)
        w.Write(str(path))
