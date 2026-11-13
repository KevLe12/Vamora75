"""Use KiCad's filled copper polygons to check the USB ground reference."""
from pathlib import Path
import json,sys,collections
import pcbnew

stage=Path(sys.argv[1])
board=pcbnew.LoadBoard(str(stage/'Vamora75.kicad_pcb'))
assert board.GetCopperLayerCount()==4
reference=board.GetLayerID('In2.Cu')
counts=collections.Counter(board.GetLayerName(t.GetLayer()) for t in board.GetTracks() if not isinstance(t,pcbnew.PCB_VIA))
assert counts['In1.Cu']>0 and counts['In2.Cu']==0,counts
ground=pcbnew.SHAPE_POLY_SET()
for z in board.Zones():
    if z.GetNetname()=='GND' and z.IsOnLayer(reference) and not z.GetIsRuleArea():
        ground.BooleanAdd(z.GetFilledPolysList(reference))
assert ground.Area()/1e12>315.5625*129.825*.8,'Ground plane unexpectedly fragmented or missing'
window=pcbnew.SHAPE_POLY_SET();window.NewOutline()
for x,y in ((26.45,15.2862),(38.9,15.2862),(38.9,16.2915),(26.45,16.2915)):
    window.Append(pcbnew.FromMM(x+40),pcbnew.FromMM(y+80))
window.BooleanSubtract(ground)
missing=window.Area()/1e12
assert missing<1e-8,('USB reference copper missing',missing)
result=dict(result='PASS',layers=4,track_counts=dict(counts),reference_layer='In2.Cu',
            reference_window_missing_mm2=missing,reference_margin_beyond_trace_edge_mm=.2,
            scope='Uniform coupled section only; short connector/resistor pad escapes are discontinuities')
(stage/'build/usb_reference_check.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
