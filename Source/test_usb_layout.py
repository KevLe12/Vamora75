"""Check the professor's USB feedback against the generated netlist and routed copper."""
from pathlib import Path
import json,math
from shapely.geometry import Point,LineString
import pcb_plan as P

ROOT=Path(__file__).resolve().parents[1]
nets,components=P.netlist(ROOT/'PCB/build/Vamora75.net.xml')
pads,_,_=P.all_pads(P.placement(),nets)
r=json.loads((ROOT/'PCB/build/routes.json').read_text())
expected={('J1','A6'):'/USB_CONN_D+',('J1','B6'):'/USB_CONN_D+',
          ('J1','A7'):'/USB_CONN_D-',('J1','B7'):'/USB_CONN_D-',
          ('U2','3'):'/USB_CONN_D+',('U2','1'):'/USB_CONN_D-',
          ('U2','4'):'/USB_D+',('U2','6'):'/USB_D-',
          ('R3','2'):'/USB_D+',('R4','2'):'/USB_D-',
          ('C8','1'):'VBUS',('C8','2'):'GND'}
assert all(nets[k]==v for k,v in expected.items())
c=components['C8']
assert c['value']=='100nF' and c['footprint']=='Vamora75:Capacitor_0402'
assert c['fields']['LCSC']=='C1525' and c['fields']['MPN']=='CL05B104KO5NNNC'
assert components['R3']['value']==components['R4']['value']=='27R'
usb=[t for t in r['tracks'] if t['net'].startswith(('/USB','/RP_D'))]
vias=[v for v in r['vias'] if v['net'].startswith(('/USB','/RP_D'))]
for i,t in enumerate(usb):
    for end in (t['a'],t['b']):
        point=Point(end)
        connected=any(p['net']==t['net'] and t['layer'] in p['layers'] and math.dist(end,(p['x'],p['y']))<1e-5 for p in pads)
        connected |= any(v['net']==t['net'] and math.dist(end,v['at'])<1e-5 for v in vias)
        connected |= any(j!=i and q['net']==t['net'] and q['layer']==t['layer'] and LineString([q['a'],q['b']]).distance(point)<1e-5 for j,q in enumerate(usb))
        assert connected,('USB endpoint relies on partial copper overlap',t,end)
for v in vias:
    hole=Point(v['at']).buffer(v['drill']/2)
    assert not any(p['kind']=='smd' and hole.intersects(p['geom']) for p in pads),('USB via drill intersects SMD pad',v)
assert math.dist((P.placement()['C8']['x'],P.placement()['C8']['y']),(P.placement()['U2']['x'],P.placement()['U2']['y']))<4.5
report=dict(result='PASS',esd='J1 -> U2 pins 1/3 -> internal channels -> pins 6/4 -> R4/R3 -> RP2040',
            esd_bypass_capacitor='C8: 100 nF 0402, C1525',usb_track_segments=len(usb),
            junctions='Shared centrelines and pad/via centres; no partial-overlap-only USB endpoints',
            usb_via_drills_clear_of_smd_pads=True,source='ST USBLC6-2 DS4260 rev 7, Figure 17')
(ROOT/'validation/usb_layout.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
