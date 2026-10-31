"""Check the requested arrow-only change and rear-left USB geometry."""
import json
from pathlib import Path

from shapely.geometry import LineString, Point, box

import pcb_plan as P
import vamora_layout as L
import vamora_mech as M

ROOT = Path(__file__).resolve().parents[1]
original = json.loads((ROOT / "Reference/rev1.2_key_positions.json").read_text())
custom = json.loads((ROOT / "Reference/Custom_layout_2026-10-31.json").read_text())["keys"]
current = {k[0]: k for k in L.KEYS}
saved = {k["label"]: k for k in custom}
arrows = {"Up", "Left", "Down", "Right"}
L.check()
for old in original:
    new = current[old[0]]
    assert list(new[3:]) == old[3:], f"function, width or matrix changed: {old[0]}"
    if old[0] not in arrows:
        assert list(new) == old, f"non-arrow key moved: {old[0]}"
for label in arrows:
    new = current[label]
    for index, axis in ((1, "x"), (2, "y")):
        assert abs((new[index] - current["RShift"][index]) -
                   (saved[label][axis] - saved["RShift"][axis])) < 1e-8, label

pl = P.placement()
assert M.USB_X == pl["J1"]["x"] == 31.5
assert (pl["U1"]["x"], pl["U1"]["y"]) == (296.5, 25.6)
nets, _ = P.netlist(ROOT / "PCB/build/Vamora75.net.xml")
pads, _, courts = P.all_pads(pl, nets)
for ref in ("J1", "U2", "R1", "R2", "F1"):
    assert all(c is None or name == ref or courts[ref].intersection(c).area < 1e-6
               for name, c in courts.items()), f"USB courtyard collision: {ref}"
for pad in pads:
    if pad["ref"] == "J1" and pad["drill"]:
        assert box(.4, .4, L.BOARD_W-.4, L.BOARD_H-.4).contains(pad["geom"]), "USB anchor lacks PCB support"

routes = json.loads((ROOT / "PCB/build/routes.json").read_text())
for net, y in (("/USB_D-", 1.5), ("/USB_D+", 2.95)):
    assert any(t["net"] == net and t["layer"] == "F.Cu" and t["w"] == 1.25 and
               list(t["a"]) == [44., y] and list(t["b"]) == [282., y] for t in routes["tracks"])
return_area = box(46, .875, 280, 3.575)
for t in routes["tracks"]:
    if t["layer"] == "B.Cu" and t["net"] != "GND":
        assert not LineString([t["a"], t["b"]]).buffer(t["w"]/2+.2).intersects(return_area), "USB return plane interrupted"
for v in routes["vias"]:
    assert not return_area.buffer(v["d"]/2+.2).contains(Point(v["at"])), "via in USB return area"
report = dict(result="PASS", unchanged_non_arrow_keys=78, arrow_positions="Custom relative to Right Shift",
              usb_rear_left_x_mm=M.USB_X, straight_usb_pair_length_mm=238,
              impedance="Not measured: fabricator must confirm 90 ohm differential against production stackup")
(ROOT / "validation/revision_geometry.json").write_text(json.dumps(report, indent=2)+"\n")
print(json.dumps(report, indent=2))
