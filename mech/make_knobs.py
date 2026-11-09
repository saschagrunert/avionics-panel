"""Knobs and light pipes for the Avionics Panel rev 1, exact solids (OpenCascade) -> STEP + STL.

Avionics style: matte black resin, fine vertical flutes, slight taper, chamfered flat top. All sizes
come from stack.py (datasheet shaft dimensions); each part has its bottom at z = 0.
  outer knob  ALT/HDG and FREQ dia 22, FMS dia 24: grips the slotted 6 mm outer shaft, with a key in
              the slot; a hidden neck carries it up into the inner knob's skirt.
  inner knob  dia 13, all three: D bore on the 3.5 mm inner shaft. The bore bottom sits on the shaft tip,
              so a push goes straight to the switch.
  RANGE knob  dia 13.6 with a 15.6 skirt over the 12 mm plate hole, D bore on the RKJXT lever.
  light pipes clear resin, captive: collar under the plate, flat on the collar towards the key cap. Both
              are printed as one part on a snap-off bar (JLC3DP's minimum resin part is 2 x 2 x 10 mm).
Fits get tested on the first print (stack.FIT): the knobs are held by friction only, so one inner and one
outer knob also come with a tighter and a looser bore (stack.FIT_VARIANTS); keep whichever grips. Needs pythonocc-core (see make_plate_step.py).
"""
import sys

sys.path.insert(0, "../pcb")
import board as B  # noqa: E402
import stack as S  # noqa: E402
from occ_util import box, cut, cyl, dbore, export, fluted, fuse, revolve  # noqa: E402


def outer_knob(D, fit=S.FIT):
    ok = S.OUTER_KNOB
    h = ok["z1"] - ok["z0"]; top = ok["neck_top"] - ok["z0"]
    body = fuse(fluted(D / 2, h, round(D / 2 * 3.3), 0.45, 0.05, 0.8), cyl(ok["neck_d"] / 2, h - 0.3, top))
    sleeve_top = S.SLEEVE_TOP - S.PLATE_Z1 - ok["z0"] + S.SLEEVE_CLEAR       # clears the fixed sleeve
    slot0 = S.OUTER_TOP - S.SLOT_LEN - S.PLATE_Z1 - ok["z0"] + 0.4
    bore = cut(cyl((S.OUTER_D + fit) / 2, -1, top + 1), box(2.2, -(S.SLOT_W - 0.2) / 2, slot0, 4, (S.SLOT_W - 0.2) / 2, top + 2))
    return cut(body, cyl(S.SLEEVE_D / 2 + S.SLEEVE_CLEAR, -1, sleeve_top), bore)


def inner_knob(fit=S.FIT):
    ik = S.INNER_KNOB
    h = ik["z1"] - ik["z0"]
    rec_top = ik["recess_top"] - ik["z0"]
    tip = S.INNER_TOP - S.PLATE_Z1 - ik["z0"]                                 # bore bottom on the shaft tip
    flat0 = tip - S.FLAT_LEN + 0.2
    body = fluted(ik["d"] / 2, h, 24, 0.32, 0.06, 0.6)
    return cut(body, cyl(ik["recess_d"] / 2, -1, rec_top), cyl(S.INNER_D / 2 + 0.1, -1, flat0 + 0.01),
               dbore(S.INNER_D + fit, S.INNER_FLAT + fit, flat0, tip))


def range_knob():
    rk = S.RANGE_KNOB
    h = rk["z1"] - rk["z0"]
    sk = rk["skirt_d"] / 2
    body = fuse(fluted(rk["d"] / 2, h, 22, 0.32, 0.05, 0.6, bottom_cham=0.0),
                revolve([(0, 0), (sk, 0), (sk, 0.25), (rk["d"] / 2 - 0.3, 0.25 + sk - rk["d"] / 2 + 0.3), (0, 1.5)]))
    lever0 = S.LEVER_Z0 - S.PLATE_Z1 - rk["z0"]; lever1 = S.LEVER_Z1 - S.PLATE_Z1 - rk["z0"]
    return cut(body, cyl(2.0, -1, max(lever0, 0.3)), dbore(S.LEVER_D + S.FIT, S.LEVER_FLAT + S.FIT, -1, lever1))


def light_pipe(name):
    d = S.LIGHT_HOLES[name]
    (lx, ly), _, _ = B.LEDS[name]
    cap_edge = min(abs(ly - y) for y in B.ROWS) - 3.2                       # LED to the key cap above it
    z0 = S.PIPE["z0"]; cd, ct = S.PIPE["collar"]
    h = S.PLATE_Z1 - 0.05 - z0
    collar = cut(cyl(cd / 2, 0, S.PLATE_Z0 - z0), box(-cd, cap_edge - 0.3, -1, cd, cd, 5))   # flat faces +y = the key
    return fuse(cyl((d - S.PIPE["clear"]) / 2, 0, h), collar)          # slip fit: anodising shrinks the hole a little


def light_pipe_pair(pitch=12.0):
    """Both light pipes on one snap-off bar: JLC3DP prints resin parts from 2 x 2 x 10 mm only. The bar runs
    at collar height on the side away from the D flats, with thin necks to break and sand off."""
    from occ_util import move
    shift, unit = light_pipe("SHIFT"), move(light_pipe("UNIT"), dx=pitch)
    cd, ct = S.PIPE["collar"]
    h = S.PLATE_Z0 - S.PIPE["z0"]                                  # collar height
    r = cd / 2
    bar = box(r - 0.3, -1.6, 0, pitch - r + 0.3, -0.4, h)          # 1.2 wide, collar height
    necks = cut(bar, box(r - 0.3, -1.6, -1, r + 0.5, -1.4, h + 1), box(r - 0.3, -0.6, -1, r + 0.5, -0.4, h + 1),
                box(pitch - r - 0.5, -1.6, -1, pitch - r + 0.3, -1.4, h + 1), box(pitch - r - 0.5, -0.6, -1, pitch - r + 0.3, -0.4, h + 1))
    return fuse(fuse(shift, unit), necks)


if __name__ == "__main__":
    export(outer_knob(S.KNOB_D["ALTHDG"]), "avionics-panel-rev1-knob-outer-22")
    export(outer_knob(S.KNOB_D["FMS"]), "avionics-panel-rev1-knob-outer-24")
    export(inner_knob(), "avionics-panel-rev1-knob-inner")
    export(range_knob(), "avionics-panel-rev1-knob-range")
    for tag, fit in S.FIT_VARIANTS.items():
        export(outer_knob(S.KNOB_D["ALTHDG"], fit), f"avionics-panel-rev1-knob-outer-22-{tag}")
        export(inner_knob(fit), f"avionics-panel-rev1-knob-inner-{tag}")
    export(light_pipe_pair(), "avionics-panel-rev1-lightpipes", deflection=0.005)   # SHIFT left, UNIT right
