"""Changed placement or electrical connections must reject the checked routing."""
from pathlib import Path
import sys
import route_board as R

stage=Path(sys.argv[1]) if len(sys.argv)>1 else R.ROOT/'PCB'
assert R.checked_routes(stage)['tracks']
placement,netlist=R.P.placement,R.P.netlist
layers=R.P.COPPER_LAYERS
def must_reject():
    try:R.checked_routes(stage)
    except SystemExit:return
    raise AssertionError('Changed design accepted stale routing')
try:
    moved=placement();moved['J1']['x']+=1
    R.P.placement=lambda:moved
    must_reject()
    R.P.placement=placement
    nets,components=netlist(stage/'build/Vamora75.net.xml')
    nets['U1','2']='changed-net'
    R.P.netlist=lambda path:(nets,components)
    must_reject()
    R.P.netlist=netlist
    R.P.COPPER_LAYERS=('F.Cu','B.Cu')
    must_reject()
finally:
    R.P.placement,R.P.netlist=placement,netlist
    R.P.COPPER_LAYERS=layers
print('Routing snapshot: matching design accepted; moved USB, changed net and changed layer count rejected')
