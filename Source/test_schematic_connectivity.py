"""Compare KiCad XML netlists before/after schematic presentation changes.

Run: python Source/test_schematic_connectivity.py before.xml after.xml
Export each with: kicad-cli sch export netlist --format kicadxml -o file.xml file.kicad_sch
"""
import sys
import xml.etree.ElementTree as ET


def circuit(path):
    root = ET.parse(path).getroot()
    components = {
        c.get("ref"): (c.findtext("value"), c.findtext("footprint"))
        for c in root.findall("./components/comp")
        if not c.get("ref").startswith("#")
    }
    nets = {
        net.get("name"): frozenset((n.get("ref"), n.get("pin")) for n in net.findall("node")
                                  if not n.get("ref").startswith("#"))
        for net in root.findall("./nets/net")
    }
    nets = {name: pins for name, pins in nets.items() if pins}
    return components, nets


if __name__ == "__main__":
    before, after = map(circuit, sys.argv[1:])
    assert before[0] == after[0], "Components, values or footprints changed"
    assert before[1] == after[1], "Net names or electrical connections changed"
    print(f"PASS: {len(after[0])} components and {len(after[1])} pin groups unchanged")
