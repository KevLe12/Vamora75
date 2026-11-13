"""Prepare a disposable board with legible assembly references; never edit production copper."""
import sys
from pathlib import Path
import pcbnew

source, target = map(Path, sys.argv[1:3])
assert source.resolve() != target.resolve() and target.parent.name == 'build'
board = pcbnew.LoadBoard(str(source))
refs = set()
for fp in board.GetFootprints():
    ref = fp.GetReference()
    assert ref not in refs
    refs.add(ref)
    if ref.startswith('D'):
        fp.Reference().SetVisible(False)
        fp.Value().SetVisible(False)
        continue  # Diode library references already sit clearly outside their polarity symbols.
    for item in list(fp.GraphicalItems()):
        if isinstance(item, pcbnew.PCB_TEXT) and item.GetText() in ('${REFERENCE}', '${VALUE}'):
            item.SetLayer(pcbnew.Dwgs_User)
    field = fp.Reference()
    field.SetVisible(True)
    field.SetLayer(pcbnew.B_Fab)
    field.SetMirrored(True)
    field.SetTextAngle(pcbnew.EDA_ANGLE(0, pcbnew.DEGREES_T))
    size = .7 if ref.startswith(('SW', 'U', 'J', 'Y')) else .3
    field.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(size), pcbnew.FromMM(size)))
    field.SetTextThickness(pcbnew.FromMM(.045))
    at = fp.GetPosition()
    if ref.startswith('SW') and ref not in ('SW90', 'SW91'):
        # Socket body is offset from the switch centre and its large through-hole.
        at = at + pcbnew.VECTOR2I(pcbnew.FromMM(-.62), pcbnew.FromMM(-3.81))
    field.SetPosition(at)
    fp.Value().SetVisible(False)
assert len(refs) == 209, len(refs)
pcbnew.SaveBoard(str(target), board)
