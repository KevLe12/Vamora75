"""Dimensioned review DXFs/PDF from the existing STEP solids; no model changes.

Run with the project's CAD Python: python Source/export_case_drawings.py
Requires cadquery, shapely, ezdxf, reportlab, pypdfium2.
"""
from pathlib import Path
import hashlib
import json
import math
import shutil
import zipfile

import cadquery as cq
import ezdxf
from OCP.HLRAlgo import HLRAlgo_Projector
from OCP.HLRBRep import HLRBRep_Algo, HLRBRep_HLRToShape
from OCP.gp import gp_Ax2, gp_Dir, gp_Pnt
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
import pypdfium2 as pdfium
import vamora_mech as M

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'Manufacturing' / 'Case_Drawings'
QA = ROOT / 'tmp' / 'case_drawings'
PDF = OUT / 'Vamora75_case_dimensioned_review.pdf'
W, H = 420, 297  # A3; orthographic views 1:2, dimensions in actual mm


def projected(shape, direction, xdir):
    algo = HLRBRep_Algo()
    algo.Add(shape.wrapped)
    algo.Projector(HLRAlgo_Projector(gp_Ax2(gp_Pnt(), gp_Dir(*direction), gp_Dir(*xdir))))
    algo.Update()
    algo.Hide()
    result = HLRBRep_HLRToShape(algo)
    for hidden, names in ((True, ('HCompound', 'OutLineHCompound')),
                          (False, ('VCompound', 'OutLineVCompound'))):
        for name in names:
            raw = getattr(result, name)()
            if not raw.IsNull():
                yield hidden, cq.Shape.cast(raw)


class BaseSheet:
    def line(self, points, layer='VISIBLE'):
        points = list(points)
        if len(points) < 2:
            return
        self.ms.add_lwpolyline(points, dxfattribs={'layer':layer})
        self.pdf.setStrokeColorRGB(*((0.63,0.66,0.69) if layer=='HIDDEN' else (0.08,0.12,0.17)))
        self.pdf.setLineWidth((0.10 if layer=='HIDDEN' else 0.18)*mm)
        self.pdf.setDash(1.5*mm,1*mm) if layer=='HIDDEN' else self.pdf.setDash()
        p=self.pdf.beginPath(); p.moveTo(points[0][0]*mm,points[0][1]*mm)
        for x,y in points[1:]: p.lineTo(x*mm,y*mm)
        self.pdf.drawPath(p)

    def text(self,x,y,txt,size=2.6):
        assert 3 <= x < W-3 and 3 <= y < H-3, (x,y,txt)
        self.ms.add_text(txt,dxfattribs={'height':size,'insert':(x,y),'layer':'NOTES','style':'OpenSans'})
        self.pdf.setFillColorRGB(0.08,0.12,0.17)
        self.pdf.setFont('Helvetica',size*mm)
        self.pdf.drawString(x*mm,y*mm,txt)

    def dim(self,p1,p2,offset,vertical=False):
        value=2*abs(p2[1]-p1[1] if vertical else p2[0]-p1[0])
        assert value > 0
        label=f'{value+1e-8:.3f}'.rstrip('0').rstrip('.')
        base=(offset,0) if vertical else (0,offset)
        d=self.ms.add_linear_dim(base=base,p1=p1,p2=p2,text=label,angle=90 if vertical else 0,
             override={'dimtxt':2.5,'dimasz':1.4,'dimexo':1,'dimexe':1.5,'dimdec':3,
                       'dimzin':8,'dimtad':1,'dimlfac':2},dxfattribs={'layer':'DIMENSIONS'})
        d.render()
        # PDF representation shares the same endpoints and measured value.
        if vertical:
            a,b=(offset,p1[1]),(offset,p2[1])
            for p,q in ((p1,a),(p2,b)): self.pdfline([p,q])
            self.pdfline([a,b]); self.pdf_arrow(a,b); self.pdf_arrow(b,a)
            self.pdf.saveState(); self.pdf.translate((offset-1.5)*mm,((a[1]+b[1])/2)*mm)
            self.pdf.rotate(90); self.pdf.setFont('Helvetica',2.5*mm)
            self.pdf.drawCentredString(0,0,label); self.pdf.restoreState()
        else:
            a,b=(p1[0],offset),(p2[0],offset)
            for p,q in ((p1,a),(p2,b)): self.pdfline([p,q])
            self.pdfline([a,b]); self.pdf_arrow(a,b); self.pdf_arrow(b,a)
            self.pdf.setFont('Helvetica',2.5*mm)
            self.pdf.drawCentredString((a[0]+b[0])/2*mm,(offset+1.5)*mm,label)

    def pdfline(self,pts):
        self.pdf.setDash(); self.pdf.setLineWidth(.12*mm); self.pdf.setStrokeColorRGB(.15,.25,.35)
        self.pdf.line(pts[0][0]*mm,pts[0][1]*mm,pts[1][0]*mm,pts[1][1]*mm)

    def pdf_arrow(self,tip,toward):
        dx,dy=toward[0]-tip[0],toward[1]-tip[1]
        length=math.hypot(dx,dy); dx,dy=dx/length,dy/length
        pts=[tip,(tip[0]+dx*1.6-dy*.3,tip[1]+dy*1.6+dx*.3),
             (tip[0]+dx*1.6+dy*.3,tip[1]+dy*1.6-dx*.3)]
        path=self.pdf.beginPath(); path.moveTo(pts[0][0]*mm,pts[0][1]*mm)
        for x,y in pts[1:]: path.lineTo(x*mm,y*mm)
        path.close(); self.pdf.setFillColorRGB(0,0,0); self.pdf.drawPath(path,stroke=0,fill=1)

    def shape(self,shape,origin,direction=(0,0,1),xdir=(1,0,0)):
        for hidden, wire in projected(shape,direction,xdir):
            for edge in wire.Edges():
                # Review drawing only: curved edges sampled to 0.01 mm deflection.
                pts,_=edge.sample(0.01)
                self.line([(p.x+origin[0],p.y+origin[1]) for p in pts], 'HIDDEN' if hidden else 'VISIBLE')

    def finish(self):
        path=OUT / f'Vamora75_case_{self.part}_dimensioned.dxf'
        self.doc.set_modelspace_vport(height=H,center=(W/2,H/2))
        self.doc.saveas(path)
        checked=ezdxf.readfile(path)
        assert not checked.audit().has_errors
        assert len(checked.modelspace().query('DIMENSION')) >= 4
        assert all(e.override().get('dimlfac')==2 for e in checked.modelspace().query('DIMENSION'))
        self.pdf.showPage()


class Sheet(BaseSheet):
    def __init__(self,pdf,part):
        self.pdf,self.part=pdf,part
        self.doc=ezdxf.new('R2010',setup=True); self.doc.units=ezdxf.units.MM
        self.doc.header['$MEASUREMENT']=1; self.ms=self.doc.modelspace()
        for name in ('VISIBLE','HIDDEN','DIMENSIONS','NOTES','SHADED','HATCH'):
            self.doc.layers.new(name,dxfattribs={'color':7})
        self.doc.layers.get('HIDDEN').dxf.linetype='DASHED'
        self.line([(15,10),(410,10),(410,287),(15,287),(15,10)])
        for i in range(8):
            x=15+(i+.5)*395/8
            self.text(x-1,290,str(i+1),2.5); self.text(x-1,5,str(i+1),2.5)
            if i:
                x=15+i*395/8
                self.line([(x,284),(x,290)]); self.line([(x,7),(x,13)])
        for i,letter in enumerate('ABCDEF'):
            y=287-(i+.5)*277/6
            self.text(9,y,letter,2.5); self.text(413,y,letter,2.5)
            if i:
                y=287-i*277/6
                self.line([(12,y),(18,y)]); self.line([(407,y),(413,y)])
        self.line([(230,10),(230,57),(410,57)])
        for y in (20,38,48): self.line([(230,y),(410,y)])
        for x in (260,318,365): self.line([(x,48),(x,57)])
        self.line([(330,10),(330,48)])
        for x in (348,385): self.line([(x,10),(x,20)])
        for x,t,v in [(232,'Units','mm'),(262,'Technical reference','Case STEP / rev 1.3'),
                      (320,'Prepared','2026-10-31'),(367,'Approved by','--')]:
            self.text(x,54,t,1.65); self.text(x,50,v,2.2)
        self.text(232,45,'Document type',1.65); self.text(232,40,'Part drawing / scale 1:2',2.3)
        self.text(332,45,'Document status',1.65); self.text(332,40,'REVIEW / QUOTATION',2.3)
        self.text(232,34,'Title',1.65); self.text(232,26,f'Vamora75 {part.title()} Case',4)
        self.text(332,34,'Drawing No.',1.65); self.text(332,26,'V75-CASE-'+part.upper(),2.5)
        self.text(232,16,'Material / finish',1.65); self.text(232,12,'6061-T6 proposed / finish TBD',2.1)
        for x,t,v in [(332,'Rev.','D3'),(350,'Date of issue','2026-10-31'),(387,'Sheet',f'{1 if part=="top" else 2}/2')]:
            self.text(x,16,t,1.6); self.text(x,12,v,2.1)

    def fill(self,pts,rgb=(0,0,0)):
        self.ms.add_solid(pts,dxfattribs={'layer':'SHADED','true_color':ezdxf.colors.rgb2int(tuple(int(c*255) for c in rgb))})
        self.pdf.setFillColorRGB(*rgb)
        self.pdf.setStrokeColorRGB(*rgb); self.pdf.setLineWidth(.025*mm); self.pdf.setDash()
        p=self.pdf.beginPath(); p.moveTo(pts[0][0]*mm,pts[0][1]*mm)
        for x,y in pts[1:]: p.lineTo(x*mm,y*mm)
        p.close(); self.pdf.drawPath(p,stroke=1,fill=1)

    def arrow(self,tip,toward):
        import numpy as np
        v=np.array(toward)-np.array(tip); v=v/np.linalg.norm(v); n=np.array([-v[1],v[0]])
        self.fill([tip,tuple(np.array(tip)+v*2+n*.35),tuple(np.array(tip)+v*2-n*.35)])

    def leader(self,point,knee,lines,size=2.5):
        self.line([point,knee,(knee[0]+5,knee[1])],'DIMENSIONS'); self.arrow(point,knee)
        for i,t in enumerate(lines): self.text(knee[0]+6,knee[1]-i*3.7,t,size)

    def view(self,shape,origin,direction=(0,0,1),xdir=(1,0,0),scale=.5,hidden=False):
        for is_hidden,wire in projected(shape,direction,xdir):
            if is_hidden and not hidden: continue
            for edge in wire.Edges():
                pts,_=edge.sample(.01)
                self.line([(p.x*scale+origin[0],p.y*scale+origin[1]) for p in pts],
                          'HIDDEN' if is_hidden else 'VISIBLE')

    def iso(self,shape,box,underside=False):
        import numpy as np
        import vtk
        from reportlab.lib.utils import ImageReader
        direction=np.array((1,1,-1) if underside else (1,-1,1),float); direction/=np.linalg.norm(direction)
        xdir=np.array((1,-1,0) if underside else (1,1,0),float); xdir/=np.linalg.norm(xdir)
        ydir=np.cross(direction,xdir); basis=np.array([xdir,ydir,direction])
        verts,tris=shape.tessellate(.08,.15)
        v=np.array([p.toTuple() for p in verts]); pv=v@basis.T
        lo=pv.min(axis=0); hi=pv.max(axis=0)
        scale=min(box[2]/(hi[0]-lo[0]),box[3]/(hi[1]-lo[1]))*.97
        origin=np.array(box[:2])+(np.array(box[2:])-(hi[:2]-lo[:2])*scale)/2-lo[:2]*scale
        points=vtk.vtkPoints()
        for p in verts: points.InsertNextPoint(*p.toTuple())
        cells=vtk.vtkCellArray()
        for ids in tris:
            cells.InsertNextCell(3)
            for i in ids: cells.InsertCellPoint(i)
        mesh=vtk.vtkPolyData(); mesh.SetPoints(points); mesh.SetPolys(cells)
        normals=vtk.vtkPolyDataNormals(); normals.SetInputData(mesh); normals.SetFeatureAngle(40); normals.Update()
        mapper=vtk.vtkPolyDataMapper(); mapper.SetInputConnection(normals.GetOutputPort())
        actor=vtk.vtkActor(); actor.SetMapper(mapper)
        actor.GetProperty().SetColor(.70,.68,.61); actor.GetProperty().SetAmbient(.45); actor.GetProperty().SetDiffuse(.55)
        renderer=vtk.vtkRenderer(); renderer.SetBackground(1,1,1); renderer.AddActor(actor)
        window=vtk.vtkRenderWindow(); window.SetOffScreenRendering(1); window.AddRenderer(renderer)
        window.SetSize(round(box[2]*10),round(box[3]*10)); window.SetMultiSamples(4)
        camera=renderer.GetActiveCamera(); centre=((lo+hi)/2)@basis
        camera.SetFocalPoint(*centre); camera.SetPosition(*(centre+direction*1000)); camera.SetViewUp(*ydir)
        camera.ParallelProjectionOn(); camera.SetParallelScale(box[3]/scale/2); renderer.ResetCameraClippingRange()
        window.Render()
        capture=vtk.vtkWindowToImageFilter(); capture.SetInput(window); capture.ReadFrontBufferOff(); capture.Update()
        path=QA/f'{self.part}_iso_{"inside" if underside else "outside"}.png'
        writer=vtk.vtkPNGWriter(); writer.SetFileName(str(path)); writer.SetInputConnection(capture.GetOutputPort()); writer.Write()
        window.Finalize()
        self.pdf.drawImage(ImageReader(str(path)),box[0]*mm,box[1]*mm,box[2]*mm,box[3]*mm)
        # DXF retains editable vector isometrics; PDF adds shaded z-buffered views.
        self.view(shape,origin,direction,xdir,scale)

    def section(self,section,origin):
        import numpy as np
        from shapely.geometry import Polygon,LineString
        from shapely.ops import unary_union
        verts,tris=section.tessellate(.03,.1)
        region=unary_union([Polygon([(origin[0]-verts[i].z*.5,origin[1]+verts[i].y*.5) for i in ids]) for ids in tris])
        assert not region.is_empty
        x0,y0,x1,y1=region.bounds
        for intercept in np.arange(y0-x1-5,y1-x0+5,1.5):
            clipped=region.intersection(LineString([(x0-2,x0-2+intercept),(x1+2,x1+2+intercept)]))
            for seg in getattr(clipped,'geoms',[clipped]):
                if seg.geom_type=='LineString': self.line(seg.coords,'HATCH')
        self.view(section,origin,direction=(1,0,0),xdir=(0,0,-1))

    def notes(self):
        texts=['NOTES:', '1. All dimensions in millimeters. Views 1:2; isometrics NTS.',
               '2. Tolerances, finish and CNC fastening revision: to be agreed.',
               '3. Existing STEP geometry shown; not released for machining.',
               '4. Undimensioned geometry per STEP. Quantity: 3 of each half.']
        texts.append('5. Key openings: R1, chamfer 0.5. Outer corners: R6.' if self.part=='top' else
                     '5. Outer corners R6; bottom chamfer 0.6; engraving depth 0.6.')
        for i,t in enumerate(texts): self.text(30,47-i*5,t,2.45)


def top_sheet(s,solid):
    w,d=M.CASE_W*.5,M.CASE_D*.5
    ox,oy=225,193
    s.view(solid,(ox,oy)); s.dim((ox,oy+d),(ox+w,oy+d),281)
    s.dim((ox+w,oy),(ox+w,oy+d),407,True); s.text(225,187,'EXTERIOR / TOP',2.2)
    s.view(solid,(35,249),direction=(0,-1,0),hidden=True)
    s.dim((35+w,249),(35+w,249+6.75*.5),220,True)
    s.leader((36,251.6),(29,265),['0.8 x 45 deg outer chamfer'],2.3); s.text(35,240,'FRONT ELEVATION',2.2)
    ox,oy=35,108
    s.view(solid,(ox+w,oy),direction=(0,0,-1),xdir=(-1,0,0)); s.text(35,101,'INTERIOR / UNDERSIDE',2.2)
    s.leader((ox+(M.CASE_W-244.00625)*.5,oy+153.0875*.5),(111,213),
             ['8x DIA 4 blind, depth 5','INSERT BORES AS MODELLED','CNC M3 revision required'],2.5)
    s.leader((ox+(M.CASE_W-70)*.5,oy+5*.5),(103,90),
             ['8x gasket recess, depth 2.35','21 along edge; R0.5 corners'],2.4)
    s.leader((ox+5.5,oy+40),(31,201),['Cavity depth 1.75','Outer corner R6'],2.4)
    x=M.MARGIN-M.SCREW_INSET
    sec=solid.intersect(cq.Face.makePlane(1000,1000,(x,M.CASE_D/2,0),(1,0,0))); assert sec.Faces()
    ax=ox+(M.CASE_W-x)*.5
    s.line([(ax,oy-3),(ax,oy+d+3)],'HIDDEN')
    for y in (oy-3,oy+d+3):
        s.line([(ax+4,y),(ax,y)],'DIMENSIONS'); s.arrow((ax,y),(ax+4,y)); s.text(ax+5,y-1,'A',3)
    s.section(sec,(250,95)); s.dim((250-6.75*.5,95+d),(250,95+d),181)
    s.text(236,87,'A-A (1:2)',3)
    s.iso(solid,(278,132,113,47)); s.iso(solid,(278,73,113,47),True)
    s.text(280,126,'EXTERIOR - NTS',2.1); s.text(280,67,'INTERIOR - NTS',2.1)
    s.notes(); return len(sec.Edges())


def bottom_sheet(s,solid):
    w,d=M.CASE_W*.5,M.CASE_D*.5
    ox,oy=35,158
    s.view(solid,(ox,oy)); s.dim((ox,oy+d),(ox+w,oy+d),279)
    s.dim((ox,oy),(ox,oy+d),25,True); s.text(35,151,'INTERIOR / TOP',2.2)
    s.leader((ox+5.5*.5,oy+153.0875*.5),(48,263),
             ['8x DIA 3.4 clearance','DIA 6.5 counterbore from underside','Head seat 5 below mating face'],2.45)
    s.leader((ox+179.30625*.5,oy+5*.5),(114,143),
             ['8x gasket recess, depth 2.35','Main cavity depth 11.35'],2.4)
    s.view(solid,(250,270),direction=(1,0,0),xdir=(0,1,0))
    s.dim((250+d,270-solid.BoundingBox().zlen*.5),(250+d,270),346,True)
    s.leader((289,259),(354,260),['6 deg','mating plane / desk'],2.4); s.text(250,245,'RIGHT SIDE (1:2)',2.2)
    s.iso(solid,(236,188,77,40)); s.iso(solid,(329,188,77,40),True)
    s.text(240,181,'INTERIOR - NTS',2.1); s.text(334,181,'UNDERSIDE - NTS',2.1)
    desk=solid.translate((0,0,M.SPLIT_Z-M.FLOOR_Z+M.FLOOR_T)).rotate((0,0,0),(1,0,0),M.TYPING_ANGLE)
    s.view(desk,(225+w,76),direction=(0,0,-1),xdir=(-1,0,0)); s.text(225,69,'UNDERSIDE - NORMAL TO DESK',2.2)
    s.leader((225+(M.CASE_W-22)*.5,76+22*.5),(300,63),['4x DIA 10.5 recess, depth 1'],2.25)
    s.view(solid,(35+w,89),direction=(0,1,0),xdir=(-1,0,0)); s.text(35,68,'REAR ELEVATION',2.2)
    usb=(35+(M.CASE_W-M.USB_X-M.MARGIN)*.5,89+(M.USB_Z-M.SPLIT_Z)*.5)
    s.leader(usb,(140,110),['USB-C opening 14 x 8, R3.5'],2.45)
    s.dim((usb[0],89),(35+w,89),117)
    s.dim((35,89),(35+w,89),123)
    s.leader((225+(M.CASE_W-319.3)*.5,76+135.7*.5),(238,164),['BOOT access DIA 2.2'],2.3)
    s.notes(); return 0


def main():
    OUT.mkdir(parents=True,exist_ok=True); QA.mkdir(parents=True,exist_ok=True)
    pdf=canvas.Canvas(str(PDF),pagesize=(W*mm,H*mm)); pdf.setTitle('Vamora75 case drawings - A3 / reference style')
    checks={}
    for part in ('top','bottom'):
        src=ROOT/'Mechanical'/'Case'/f'Vamora75_case_{part}.step'
        original=cq.importers.importStep(str(src)).val(); assert original.isValid() and len(original.Solids())==1
        solid=original.rotate((0,0,0),(1,0,0),-M.TYPING_ANGLE).translate((0,0,M.FLOOR_Z-M.FLOOR_T-M.SPLIT_Z))
        bb=solid.BoundingBox(); assert abs(bb.xlen-M.CASE_W)<.002 and abs(bb.ylen-M.CASE_D)<.002
        cylinders=[f._geomAdaptor().Cylinder() for f in solid.Faces() if f.geomType()=='CYLINDER']
        r=(M.SCREW['insert_d'] if part=='top' else M.SCREW['clear_d'])/2
        for x,y in M.SCREWS:
            assert any(abs(c.Radius()-r)<1e-5 and abs(c.Location().X()-x-M.MARGIN)<1e-5 and
                       abs(c.Location().Y()-y-M.MARGIN)<1e-5 for c in cylinders)
        s=Sheet(pdf,part); print('Drawing',part,flush=True)
        section_edges=(top_sheet if part=='top' else bottom_sheet)(s,solid)
        s.finish(); shutil.copy2(src,OUT/src.name)
        checks[part]={'source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'valid_solid':True,
                     'matched_fastener_cylinders':8,'drawing_frame_bbox_mm':[bb.xlen,bb.ylen,bb.zlen],
                     'section_edges':section_edges,'sheet':'A3','orthographic_scale':'1:2','dimension_factor':2}
    pdf.save()
    document=pdfium.PdfDocument(str(PDF)); assert len(document)==2
    for i,page in enumerate(document):
        assert abs(page.get_width()-W*mm)<.01
        page.render(scale=2).to_pil().save(QA/f'page_{i+1}.png')
    (OUT/'validation.json').write_text(json.dumps(checks,indent=2))
    (OUT/'READ_ME.txt').write_text(
        'Vamora75 case drawing package - revision D3 - 2026-10-31\n'
        'A3 drawings styled after supplied Manta75 references; dimensions belong to Vamora75.\n'
        'Two DXFs, two-page PDF, original STEP parts. All dimensional values in mm.\n'
        'Orthographic and section views are 1:2 on the sheet; DXF DIMLFAC=2. Isometrics NTS.\n'
        'Do not measure scaled sheet geometry as full-size part geometry. Use STEP for CAM.\n'
        'FOR REVIEW/QUOTATION. Tolerances, material, finish and CNC fastening revision not approved.\n'
        'Current top STEP has 4 mm heat-set insert bores, NOT M3 tapped holes.\n'
        'Proposed material: 6061-T6. Quantity: three of each half.\n'
        'Main views use plate-parallel axes; bottom underside view is normal to desk.\n'
        'Projection curves sampled to 0.01 mm deflection; PDF isometrics are shaded, DXF isometrics are vector lines.\n'
        'Reference Manta75 thread and tolerance specifications have NOT been copied.\n'
        'Source STEP SHA256 hashes and solid checks are recorded in validation.json.\n')
    with zipfile.ZipFile(OUT/'Vamora75_case_CAD_review_package.zip','w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(OUT.iterdir()):
            if p.suffix!='.zip': z.write(p,p.name)
    print(json.dumps(checks,indent=2),flush=True)


if __name__=='__main__': main()

