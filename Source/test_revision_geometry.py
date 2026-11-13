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
nets,components=P.netlist(ROOT/'PCB/build/Vamora75.net.xml')
pads,_,_=P.all_pads(pl,nets)
for pad in pads:
    if pad['ref']=='J1' and pad['drill']:
        assert box(.4,.4,L.BOARD_W-.4,L.BOARD_H-.4).contains(pad['geom']),'USB anchor unsupported'
routes=json.loads((ROOT/'PCB/build/routes.json').read_text())
assert not routes['failed'],routes['failed']
assert P.COPPER_LAYERS==('F.Cu','In1.Cu','In2.Cu','B.Cu')
assert components['R3']['value']==components['R4']['value']=='27R'
assert (P.MX,P.MY)==(40.0,23.0)
return_plane=box(26.45,15.2862,38.9,16.2915)
for t in routes['tracks']:
    assert not(t['layer']=='In2.Cu' and t['net']!='GND'),'Signal routed on USB reference plane'
for v in routes['vias']:
    if v['net']!='GND':
        assert not return_plane.intersects(Point(v['at']).buffer(v['d']/2+.2)),v
for p in pads:
    if p['net']!='GND' and ('In2.Cu' in p['layers'] or p['kind']=='np_thru_hole'):
        assert not return_plane.intersects(p['geom'].buffer(.2)),p['ref']
import math
lengths={suffix:sum(math.dist(t['a'],t['b']) for t in routes['tracks'] if t['net'] in nets_for_signal)
         for suffix,nets_for_signal in (('plus',{'/USB_CONN_D+','/USB_D+','/RP_DP'}),('minus',{'/USB_CONN_D-','/USB_D-','/RP_DM'}))}
assert max(lengths.values())<60,lengths
main={net:[t for t in routes['tracks'] if t['net']==net and t['layer']=='B.Cu' and abs(t['w']-.2276)<1e-6
           and abs(t['a'][1]-t['b'][1])<1e-6 and abs(t['a'][0]-t['b'][0])>10] for net in ('/USB_D+','/USB_D-')}
assert all(len(ts)==1 for ts in main.values()),main
gap=abs(main['/USB_D+'][0]['a'][1]-main['/USB_D-'][0]['a'][1])-.2276
assert abs(gap-.1501)<1e-5,gap
report=dict(result='PASS',custom_keys_matched=82,reference_sha256=saved['sha256'],
            pcb_mm=[L.BOARD_W,L.BOARD_H],usb_rear_left_x_mm=M.USB_X,
            controller_position_mm=[P.MX,P.MY],
            usb_aggregate_copper_length_mm=lengths,
            copper_layers=list(P.COPPER_LAYERS),
            impedance='JLC04161H-7628, 90 ohm differential +/-10%; calculator geometry checked, supplier coupon and prototype checks required')
(ROOT/'validation/revision_geometry.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
