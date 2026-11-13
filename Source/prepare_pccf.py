"""Orient the checked insert-bore split case for printing; no geometry scaling."""
from pathlib import Path
import hashlib, json, math, zipfile
import trimesh
import cadquery as cq

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'Mechanical/Case/print_pccf'
OUT.mkdir(exist_ok=True)
rows=[]
for path in sorted((OUT.parent/'print_split').glob('*.stl')):
    mesh=trimesh.load(path)
    assert mesh.is_watertight and mesh.volume>0,path
    original_volume=mesh.volume
    if '_top_' in path.name:
        mesh.apply_transform(trimesh.transformations.rotation_matrix(math.radians(174),[1,0,0]))
    mesh.apply_translation(-mesh.bounds[0])
    assert abs(mesh.volume-original_volume)/original_volume<1e-6
    assert all(mesh.extents < [280,280,330]),mesh.extents
    mesh.export(OUT/path.name)
    rows.append(dict(file=path.name,bounds_mm=mesh.extents.tolist(),watertight=True,
                     source_sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
assert len(rows)==4
# Test the case's blind insert depth in the chosen material.
coupon=cq.Workplane('XY').box(42,14,8,centered=(False,False,False))
for x,d in ((7,3.9),(21,4.0),(35,4.1)):
    cutter=cq.Workplane('XY').workplane(offset=3).center(x,7).circle(d/2).extrude(5)
    coupon=coupon.cut(cutter)
assert coupon.val().isValid() and len(coupon.val().Solids())==1
cq.exporters.export(coupon,str(OUT/'insert_fit_3.9_4.0_4.1mm.stl'))
report=dict(printer='Prusa CORE One L',build_volume_mm=[300,300,330],parts=rows,
            fit_coupon='Left to right along 42 mm edge: 3.9, 4.0, 4.1 mm blind bores; 5 mm depth',
            status='Geometry fit checked; not sliced or physically printed')
(OUT/'print_checks.json').write_text(json.dumps(report,indent=2))
(ROOT/'validation/pccf_print.json').write_text(json.dumps(report,indent=2))
with zipfile.ZipFile(ROOT/'Manufacturing/Vamora75_PCCF_print.zip','w',zipfile.ZIP_DEFLATED) as z:
    for path in sorted(OUT.iterdir()):
        if path.is_file():z.write(path,path.name)
    z.write(ROOT/'Manufacturing/PCCF_PRINT.md','PCCF_PRINT.md')
print(json.dumps(report,indent=2))
