"""Restore checked copper routing only when its layout, pads and netlist still match."""
import hashlib
import json
import sys
from pathlib import Path
import pcb_plan as P
import kicad_fp
import vamora_layout as L

ROOT=Path(__file__).resolve().parents[1]

def input_fingerprint(stage):
    nets,_=P.netlist(stage/'build/Vamora75.net.xml')
    placement=P.placement()
    data=dict(board=[L.BOARD_W,L.BOARD_H],placement=placement,nets=sorted((ref,pin,net) for (ref,pin),net in nets.items()),
              footprints={name:kicad_fp.load(name) for name in sorted({p['fp'] for p in placement.values()})})
    return hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def checked_routes(stage):
    saved=json.loads((ROOT/'Source/pcb_routes.json').read_text())
    if saved['revision']!=L.REVISION or saved['input_sha256']!=input_fingerprint(stage):
        raise SystemExit('Checked routing does not match this design. Reroute the changed PCB, pass DRC, and update Source/pcb_routes.json before rebuilding.')
    assert not saved['routing']['failed'],'Routing snapshot contains unresolved connections'
    return saved['routing']

if __name__=='__main__':
    stage=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'PCB'
    routes=checked_routes(stage)
    (stage/'build/routes.json').write_text(json.dumps(routes))
    print('Restored verified routing:',len(routes['tracks']),'tracks,',len(routes['vias']),'vias; design fingerprint matches')
