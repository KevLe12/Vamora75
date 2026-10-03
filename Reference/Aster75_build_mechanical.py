from pathlib import Path
import json, math
import cadquery as cq
from shapely.geometry import box
from shapely.ops import unary_union
import ezdxf
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'Mechanical';OUT.mkdir(exist_ok=True)
keys=json.loads((ROOT/'layout.json').read_text())
components=json.loads((ROOT/'validation/pcb-components.json').read_text())
def rect(x0,y0,x1,y1,z0,z1):
    return cq.Workplane('XY').box(x1-x0,y1-y0,z1-z0,centered=(False,False,False)).translate((x0,y0,z0))
def cyl(x,y,r,z0,z1):return cq.Workplane('XY').center(x,y).circle(r).extrude(z1-z0).translate((0,0,z0))
def blank(z0,z1):
    return rect(0,0,352,170,z0,z1).edges('|Z').fillet(6)
def pocket(x0,y0,x1,y1,z0,z1,r=1.5):return rect(x0,y0,x1,y1,z0,z1).edges('|Z').fillet(r)
def xy(k):return k['x']+28,137-k['y']
tabs=[(x,y) for x in [60,176,292] for y in [17,152]]
screws=[(8,8),(176,8),(344,8),(8,85),(344,85),(8,162),(176,162),(344,162)]
platepoly=unary_union([box(16,20,336,149)]+[box(x-15,y-3,x+15,y+3) for x,y in tabs])
cuts=[]
for key in keys:
    x,y=xy(key);cuts.append(box(x-7,y-7,x+7,y+7))
    if key['w']>=2:
        spacing=50 if key['w']==6.25 else 11.938
        yc=y+(.635 if key['w']==6.25 else -.635)
        for sx in [x-spacing,x+spacing]:cuts.append(box(sx-3.75,yc-8.75,sx+3.75,yc+8.75))
platepoly=platepoly.difference(unary_union(cuts))
assert platepoly.is_valid and platepoly.geom_type=='Polygon'
def solid_from_poly(p,z0,h):
    wp=cq.Workplane('XY').polyline(list(p.exterior.coords)[:-1]).close()
    for ring in p.interiors:wp=wp.polyline(list(ring.coords)[:-1]).close()
    return wp.extrude(h).translate((0,0,z0))
plate=solid_from_poly(platepoly,16.5,1.5)
base=blank(0,16.4)
# Main floating cavity and tab seats. The underside floor is 4 mm thick.
base=base.cut(pocket(14.5,19.5,337.5,150.5,4,17))
for x,y in tabs:base=base.cut(pocket(x-15.5,y-3.5,x+15.5,y+3.5,14.9,17))
# Separate USB bay, with open access for installing the daughterboard.
base=base.cut(pocket(225.5,149.5,246.5,168.5,4,17))
usbmount=[(229,153),(243,153),(229,165.5),(243,165.5)]
for x,y in usbmount:base=base.union(cyl(x,y,2.4,4,6)).cut(cyl(x,y,.8,2,7))
# USB plug opening: width 12 mm, height 6 mm, 2.5 mm connector-face recess.
base=base.cut(rect(230,167,242,171,6.6,12.6))
for x,y in screws:base=base.cut(cyl(x,y,1.7,-1,17)).cut(cyl(x,y,3.25,-1,3.5))
top=blank(16.4,25)
top=top.cut(pocket(14.5,19.5,337.5,150.5,16,19.6))
top=top.cut(pocket(16,21,336,149,19.6,26))
for x,y in tabs:top=top.cut(pocket(x-15.5,y-3.5,x+15.5,y+3.5,16,19.6))
# Cover the daughterboard pocket without disturbing plate suspension.
top=top.cut(pocket(225.5,149.5,246.5,168.5,16,19.6))
for x,y in screws:top=top.cut(cyl(x,y,1.25,16,23.4))
# Small cosmetic external chamfer; internal gasket seats retain sharp dimensions.
try:top=top.faces('>Z').edges().chamfer(.6)
except Exception:pass
pcb=rect(17,21,335,148,11.4,13)
for c in components:
    for p in c['pads']:
        if p['drill']>0:
            pcb=pcb.cut(cyl(p['x']+28,137-p['y'],p['drill']/2,11,13.5))
# Conservative socket envelope, including plastic and solder underneath PCB.
sockets=[]
for key in keys:
    x,y=xy(key)
    sockets.append(rect(x-8.6,y+.2,x+7.2,y+7.4,8.3,11.4))
gaskets=[rect(x-15,y-2.75,x+15,y+2.75,z,z+1.6) for x,y in tabs for z in [14.9,18]]
checks={}
for name,shape in [('case_bottom',base),('case_top',top),('plate',plate),('pcb_envelope',pcb)]:
    assert shape.val().isValid(),name
    checks[name]={'valid_solid':True,'solid_count':len(shape.solids().vals()),'volume_mm3':shape.val().Volume()}
    cq.exporters.export(shape,str(OUT/(name+'.step')))
    cq.exporters.export(shape,str(OUT/(name+'.stl')),tolerance=.06,angularTolerance=.1)
def overlap(a,b):return a.intersect(b).val().Volume() if a.intersect(b).vals() else 0
checks['case_halves_overlap_mm3']=overlap(base,top)
checks['plate_case_overlap_mm3']=overlap(plate,base)+overlap(plate,top)
checks['pcb_case_overlap_mm3']=overlap(pcb,base)+overlap(pcb,top)
checks['nominal_socket_floor_clearance_mm']=8.3-4
checks['socket_floor_clearance_at_1mm_travel_mm']=8.3-1-4
checks['gaskets']={'count':12,'free_size_mm':[30,5.5,2],'installed_thickness_mm':1.6,'precompression_percent':20,'positions_xy_mm':tabs}
checks['case_size_mm']=[352,170,25]
assert checks['case_halves_overlap_mm3']<.001
assert checks['plate_case_overlap_mm3']<.001
assert checks['pcb_case_overlap_mm3']<.001
# CAD assembly uses one coordinate system for every exported solid.
assy=cq.Assembly(name='Aster75')
assy.add(base,name='Case_bottom',color=cq.Color(.13,.16,.18));assy.add(top,name='Case_top',color=cq.Color(.13,.16,.18))
assy.add(plate,name='Plate_1p5mm',color=cq.Color(.7,.72,.74));assy.add(pcb,name='PCB_1p6mm',color=cq.Color(.08,.3,.22))
for i,g in enumerate(gaskets):assy.add(g,name=f'Gasket_{i+1}',color=cq.Color(.25,.25,.25))
assy.export(str(OUT/'assembly.step'))
# Clean 1:1 millimetre DXF, one outer contour and closed switch/stabilizer contours.
doc=ezdxf.new('R2010');doc.units=4;m=doc.modelspace()
m.add_lwpolyline(list(platepoly.exterior.coords)[:-1],close=True)
for ring in platepoly.interiors:m.add_lwpolyline(list(ring.coords)[:-1],close=True)
doc.saveas(OUT/'plate_1p5mm.dxf')
gd=ezdxf.new('R2010');gd.units=4;gm=gd.modelspace()
for i in range(12):
    x=(i%3)*35;y=(i//3)*10;gm.add_lwpolyline([(x,y),(x+30,y),(x+30,y+5.5),(x,y+5.5)],close=True)
gd.saveas(OUT/'gaskets_2mm_12pieces.dxf')
# Flat rear risers provide an optional ~6 degree typing slope over 140 mm foot span.
riser=cq.Workplane('YZ').polyline([(0,8*math.tan(math.radians(6))),(16,-8*math.tan(math.radians(6))),(16,14.7),(0,14.7)]).close().extrude(24)
cq.exporters.export(riser,str(OUT/'optional_rear_riser_print_two.stl'))
cq.exporters.export(riser,str(OUT/'optional_rear_riser_print_two.step'))
(ROOT/'validation/mechanical-checks.json').write_text(json.dumps(checks,indent=2))
(ROOT/'validation/plate-polygon.json').write_text(json.dumps({'outer':list(platepoly.exterior.coords),'holes':[list(r.coords) for r in platepoly.interiors]}))
print(json.dumps(checks,indent=2))
