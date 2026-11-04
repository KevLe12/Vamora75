"""Check the complete Custom layout and the compact PCB geometry."""
import json
from pathlib import Path
from shapely.geometry import box, LineString, Point
from shapely.ops import unary_union
import vamora_layout as L
import vamora_mech as M
import pcb_plan as P

ROOT=Path(__file__).resolve().parents[1]
saved=json.loads((ROOT/'Reference/Custom_layout_2026-11-03.json').read_text())
custom={k['label']:k for k in saved['keys']}
L.check()
assert set(custom)=={k[0] for k in L.KEYS}
for label,x,y,w,kc,row,col in L.KEYS:
    expected=custom[label]
    assert all(abs(a-b)<1e-7 for a,b in zip((x,y,w),(expected['x'],expected['y'],expected['w']))),label
assert (L.BOARD_W,L.BOARD_H)==(315.5625,129.825)
keys=L.keys()
for i,a in enumerate(keys):
    ga=box(a['x'],a['y'],a['x']+a['w'],a['y']+1)
    for b in keys[i+1:]:
        assert ga.intersection(box(b['x'],b['y'],b['x']+b['w'],b['y']+1)).area<1e-7,(a['label'],b['label'])
pl=P.placement()
assert M.USB_X==pl['J1']['x']==25.0
assert M.BOOT_PIN==(pl['SW90']['x'],L.BOARD_H-pl['SW90']['y'])
nets,_=P.netlist(ROOT/'PCB/build/Vamora75.net.xml')
pads,_,_=P.all_pads(pl,nets)
for pad in pads:
    if pad['ref']=='J1' and pad['drill']:
        assert box(.4,.4,L.BOARD_W-.4,L.BOARD_H-.4).contains(pad['geom']),'USB anchor unsupported'
routes=json.loads((ROOT/'PCB/build/routes.json').read_text())
assert not routes['failed'],routes['failed']
return_plane=unary_union([box(.8,.8,3.7,L.BOARD_H-.8),box(.8,.8,15,3.7),
                          box(.8,L.BOARD_H-3.7,141,L.BOARD_H-.8)])
for t in routes['tracks']:
    if t['layer']=='B.Cu' and t['net']!='GND':
        assert not return_plane.intersects(LineString([t['a'],t['b']]).buffer(t['w']/2+.2)),t
for v in routes['vias']:
    if v['net']!='GND':
        assert not return_plane.intersects(Point(v['at']).buffer(v['d']/2+.2)),v
for p in pads:
    if p['net']!='GND' and 'B.Cu' in p['layers']:
        assert not return_plane.intersects(p['geom'].buffer(.2)),p['ref']
report=dict(result='PASS',custom_keys_matched=82,reference_sha256=saved['sha256'],
            pcb_mm=[L.BOARD_W,L.BOARD_H],usb_rear_left_x_mm=M.USB_X,
            controller_position_mm=[P.MX,P.MY],
            impedance='Fabricator must confirm 90 ohm differential against production stackup')
(ROOT/'validation/revision_geometry.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
