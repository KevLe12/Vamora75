"""Write PCB/Vamora75.kicad_pro (KiCad 10) with Vamora75 design rules and net classes.

    python Source/gen_project.py [output_dir]
Design rules follow JLCPCB standard 2-layer capabilities with margin.
"""
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "PCB"
TEMPLATE = ROOT / "Archive" / "rev0.1" / "PCB" / "Vamora75.kicad_pro"
if not TEMPLATE.exists():
    TEMPLATE = ROOT / "PCB" / "Vamora75.kicad_pro"

p = json.loads(TEMPLATE.read_text(encoding="utf-8"))
ds = p["board"]["design_settings"]
ds["rules"].update({
    "min_clearance": 0.15, "min_copper_edge_clearance": 0.4, "min_hole_clearance": 0.25,
    "min_hole_to_hole": 0.25, "min_through_hole_diameter": 0.2, "min_track_width": 0.15,
    "min_via_annular_width": 0.07, "min_via_diameter": 0.45, "min_text_height": 0.8,
    "min_text_thickness": 0.12, "min_silk_clearance": 0.0, "solder_mask_to_copper_clearance": 0.0,
})
ds["track_widths"] = [0.0, 0.2, 0.25, 0.3, 0.4, 0.5]
ds["via_dimensions"] = [{"diameter": 0.0, "drill": 0.0}, {"diameter": 0.6, "drill": 0.3}, {"diameter": 0.8, "drill": 0.4}]
# Severities: keep KiCad defaults but treat these as errors so they can never slip through
sev = ds.setdefault("rule_severities", {})
for k in ["clearance", "copper_edge_clearance", "hole_clearance", "hole_to_hole", "shorting_items", "tracks_crossing",
          "unconnected_items", "items_not_allowed", "malformed_courtyard", "courtyards_overlap", "solder_mask_bridge"]:
    sev[k] = "error"
sev["lib_footprint_issues"] = "warning"
sev["lib_footprint_mismatch"] = "warning"
sev["silk_over_copper"] = "warning"
sev["silk_overlap"] = "ignore"
sev["text_height"] = "warning"
sev["track_dangling"] = "warning"
sev["via_dangling"] = "warning"
sev["footprint_type_mismatch"] = "ignore"
sev["npth_inside_courtyard"] = "ignore"
sev["pth_inside_courtyard"] = "ignore"
sev["missing_courtyard"] = "ignore"
sev["footprint_filters_mismatch"] = "ignore"

base = p["net_settings"]["classes"][0]
base.update({"name": "Default", "track_width": 0.2, "clearance": 0.2, "via_diameter": 0.6, "via_drill": 0.3})


def cls(name, track, clear, via, drill, prio):
    c = copy.deepcopy(base)
    c.update({"name": name, "track_width": track, "clearance": clear, "via_diameter": via, "via_drill": drill,
              "priority": prio})
    return c


p["net_settings"]["classes"] = [base, cls("Power", 0.4, 0.2, 0.8, 0.4, 1), cls("USB", 0.3, 0.2, 0.6, 0.3, 2)]
p["net_settings"]["netclass_patterns"] = [
    {"netclass": "Power", "pattern": "GND"}, {"netclass": "Power", "pattern": "+3V3"},
    {"netclass": "Power", "pattern": "+5V"}, {"netclass": "Power", "pattern": "+1V1"},
    {"netclass": "Power", "pattern": "VBUS"},
    {"netclass": "USB", "pattern": "/USB_D*"}, {"netclass": "USB", "pattern": "/RP_D*"},
]
p["net_settings"]["netclass_assignments"] = None
p["text_variables"] = {"REV": "1.1", "PROJECT_NAME": "Vamora75"}
p["meta"]["filename"] = "Vamora75.kicad_pro"
p["libraries"] = {"pinned_footprint_libs": [], "pinned_symbol_libs": []}
import uuid as _u
SCH_UUID = str(_u.uuid5(_u.UUID("0f6b4a2c-3a1e-4f39-9a6e-7a3c5d75a075"), "schematic-root"))
p["sheets"] = [[SCH_UUID, "Root"]]
p["boards"] = []
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "Vamora75.kicad_pro").write_text(json.dumps(p, indent=2), encoding="utf-8")
print("project written", OUT / "Vamora75.kicad_pro")
