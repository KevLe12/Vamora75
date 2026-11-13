"""Additional CNC checks run by build_case, using the actual PCBA and case solids."""
import math
import cadquery as cq
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
import vamora_mech as M


def bounds(shape):
    box = Bnd_Box()
    BRepBndLib.Add_s(shape.wrapped, box, False)
    return cq.BoundBox(box)


def check_cnc(bottom, top, bottom_world, parts, pcba, foam, report):
    from build_case import cyl, comp, vol, world, wpt
    overlaps = report["overlap_mm3"]
    s = M.SCREW
    grip = M.SPLIT_Z - s["head_seat_z"]
    engagement = s["length"] - grip
    # Purchased screw length +/-0.2; machined grip +/-0.05. Entry and screw tip consume 0.9 mm.
    low, high = engagement - .25, engagement + .25
    assert low - .9 >= 3.0 and high < s["thread_depth"]
    assert M.CASE_TOP - M.SPLIT_Z - s["pilot_depth"] - .05 >= 1.0 - 1e-9
    shanks, heads, drivers = [], [], []
    for x, y in M.SCREWS:
        shanks.append(cyl(x, y, 3.0, s["head_seat_z"], M.SPLIT_Z))
        heads.append(cyl(x, y, 5.5, s["head_seat_z"] - 3.0, s["head_seat_z"]))
        drivers.append(cyl(x, y, 3.0, -80, s["head_seat_z"] - 1.0))
        pilot = cyl(x, y, s["pilot_d"] - .002, M.SPLIT_Z, M.SPLIT_Z + s["pilot_depth"] - .001)
        assert abs(vol(top, pilot)) < .001, "Pilot bore is blocked"
        assert wpt(x, y, s["head_seat_z"] - 3.0)[2] > 0, "Screw head protrudes below case"
    overlaps["bottom_case x screw shanks"] = vol(bottom, comp(shanks))
    overlaps["bottom_case x screw heads"] = vol(bottom, comp(heads))
    overlaps["finished_bottom x hex driver paths"] = vol(bottom_world, world(comp(drivers)))
    report["cnc_fasteners"] = dict(thread=s["thread"], count=8, grip_mm=grip,
        nominal_engagement_mm=engagement, insertion_range_mm=[low, high],
        minimum_effective_engagement_mm=round(low-.9, 3), minimum_tip_to_full_thread_end_mm=s["thread_depth"]-high,
        pilot_diameter_mm=s["pilot_d"], flat_bottom_pilot_depth_mm=s["pilot_depth"],
        minimum_roof_mm=round(M.CASE_TOP-M.SPLIT_Z-s["pilot_depth"]-.05, 3),
        screw_length_acceptance_mm=[7.8, 8.2], thread_geometry="Drawing callout; STEP has pilot bores, not helical threads")

    # Conservative bounding-box rejection avoids slow booleans on parts entirely above the foam.
    candidates = [q for q in pcba.val().Solids() if bounds(q).zmin < M.FLOOR_Z + 3.0]
    overlaps["case_foam x bottom PCBA components"] = vol(foam, comp(candidates)) if candidates else 0
    boot = bounds(parts["SW90"])
    bx, by = M.BOOT_PIN
    error = math.hypot((boot.xmin+boot.xmax)/2-bx, (boot.ymin+boot.ymax)/2-by)
    assert error < .01, "BOOT actuator not centered on access hole"
    # A 1 mm blunt probe plus +/-0.65 mm PCB float/position allowance stays on the 2.5 mm actuator.
    probe_d = 1.0 + 2*.65
    assert probe_d < 2.5 and probe_d < M.BOOT_HOLE_D
    probe = cyl(bx, by, probe_d, -80, boot.zmin-.001)
    overlaps["finished_bottom x BOOT probe envelope"] = vol(bottom_world, world(probe))
    overlaps["case_foam x BOOT probe envelope"] = vol(foam, probe)
    nearby = [q for q in pcba.val().Solids() if bounds(q).zmin < boot.zmin-.001]
    overlaps["PCBA x BOOT approach envelope"] = vol(comp(nearby), probe) if nearby else 0
    report["boot_access"] = dict(hole_mm=M.BOOT_HOLE_D, probe_mm=1.0, lateral_allowance_mm=.65,
        center_error_mm=round(error, 6), button_face_z_mm=round(boot.zmin, 3),
        instruction="Insert a blunt nonconductive probe along the hole axis (normal to PCB), gently press; actual travel needs first-article test")
    report["layer_allowances"] = dict(pcb_mm=M.PCB_T, plate_mm=M.PLATE_T,
        plate_foam_mm=3.5, bottom_foam_mm=3.0,
        socket_to_bottom_foam_nominal_mm=round(-M.PCB_T-M.SOCKET_H-(M.FLOOR_Z+3), 3),
        pcb_to_floor_mm=round(-M.PCB_T-M.FLOOR_Z, 3),
        gasket_free_mm=M.GASKET_T, gasket_installed_mm=M.GASKET_SET)
    assert all(abs(value) <= .01 for value in overlaps.values()), overlaps
