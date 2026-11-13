from pathlib import Path
import sys,json,re,itertools
r=Path(__file__).resolve().parents[1];sys.path.insert(0,str(r/'Source'))
import cadquery as cq, cad_mesh as C
from OCP.TDF import TDF_LabelSequence
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
doc,st,ct,roots=C.read_step(r/'Mechanical/Vamora75_PCBA.step')
parts={}
for root in roots:
 labs=TDF_LabelSequence();st.GetComponents_s(root,labs,False)
 for i in range(1,labs.Length()+1):
  l=labs.Value(i);name=C.label_name(l)
  if re.fullmatch(r'(?:SW|ST|U|J|R|C|D|F|Y)\d+',name):parts.setdefault(name,[]).append(cq.Shape.cast(st.GetShape_s(l)))
parts={n:cq.Compound.makeCompound(v) for n,v in parts.items()}
print('Selected parts',len(parts),flush=True);assert len(parts)>=200
boxes={}
for n,s in parts.items():
 b=Bnd_Box();BRepBndLib.Add_s(s.wrapped,b,False);boxes[n]=b.Get()
checks={}
for a,b in itertools.combinations(parts,2):
 x,y=boxes[a],boxes[b]
 if any(x[i+3]<=y[i]+.001 or y[i+3]<=x[i]+.001 for i in range(3)):continue
 vol=parts[a].intersect(parts[b]).Volume();checks[a+' x '+b]=round(vol,6)
report={'selected_parts':len(parts),'bounding_box_candidate_pairs':len(checks),'overlap_mm3':checks,'failures':{k:v for k,v in checks.items() if v>.01}}
report['result']='FAIL' if report['failures'] else 'PASS'
(r/'validation/component_interference.json').write_text(json.dumps(report,indent=2));print(report)

assert report["result"] == "PASS", report["failures"]
