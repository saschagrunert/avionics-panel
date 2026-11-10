"""Knobs and light pipes for the Avionics Panel rev 1, exact solids (OpenCascade) -> STEP + STL.

Avionics style: matte black resin, fine vertical flutes, slight taper, chamfered flat top. All sizes
come from stack.py (datasheet shaft dimensions); each part has its bottom at z = 0.
  outer knob  dia 17, all three (Garmin proportions: 2.5 mm of ring each side of the inner knob): grips
              the slotted 6 mm outer shaft, with a key in the slot; a hidden neck carries it up into the
              inner knob's skirt.
  inner knob  dia 12, all three: D bore on the 3.5 mm inner shaft. The bore bottom sits on the shaft tip,
              so a push goes straight to the switch.
  RANGE knob  dia 13.6 with a 15.6 skirt over the 12 mm plate hole, D bore on the RKJXT lever.
  light pipes clear resin rods, glued flush into the plate, the bottom clear of the LED. Both are printed as
              one part on a snap-off bar over their tops (JLC3DP's minimum resin part is 2 x 2 x 10 mm).
Fits get tested on the first print (stack.FIT): the knobs are held by friction only, so one outer, one inner
and the RANGE knob also come with a tighter and a looser bore (stack.FIT_VARIANTS); keep whichever grips.
Needs pythonocc-core (see make_plate_step.py).
"""
import stack as S
from occ_util import box, cut, cyl, dbore, export, fluted, fuse, revolve

# flutes: coarse on the outer rings (count per mm of radius), fine on the inner knobs; depth, taper, top chamfer
OUTER_FLUTES = dict(per_r=3.3, depth=0.45, taper=0.05, cham=0.8)
INNER_FLUTES = dict(n=24, depth=0.32, taper=0.06, cham=0.6)


def outer_counterbore_top():
    """counterbore top above the outer knob's bottom: it clears the fixed sleeve."""
    return S.SLEEVE_TOP - S.PLATE_Z1 - S.OUTER_KNOB["z0"] + S.SLEEVE_CLEAR


def outer_knob(D, fit=S.FIT):
    ok = S.OUTER_KNOB
    h = ok["z1"] - ok["z0"]; top = ok["neck_top"] - ok["z0"]
    f = OUTER_FLUTES
    body = fuse(fluted(D / 2, h, round(D / 2 * f["per_r"]), f["depth"], f["taper"], f["cham"]),
                cyl(ok["neck_d"] / 2, h - 0.3, top))
    sleeve_top = outer_counterbore_top()
    slot0 = S.OUTER_TOP - S.SLOT_LEN - S.PLATE_Z1 - ok["z0"] + 0.4
    key_w = (S.SLOT_W - 0.2) / 2
    bore = cut(cyl((S.OUTER_D + fit) / 2, -1, top + 1), box(2.2, -key_w, slot0, 4, key_w, top + 2))
    return cut(body, cyl(S.SLEEVE_D / 2 + S.SLEEVE_CLEAR, -1, sleeve_top), bore)


def inner_knob(fit=S.FIT):
    ik = S.INNER_KNOB
    h = ik["z1"] - ik["z0"]
    rec_top = ik["recess_top"] - ik["z0"]
    tip = S.INNER_TOP - S.PLATE_Z1 - ik["z0"]                                 # bore bottom on the shaft tip
    flat0 = tip - S.FLAT_LEN + 0.2
    f = INNER_FLUTES
    body = fluted(ik["d"] / 2, h, f["n"], f["depth"], f["taper"], f["cham"])
    return cut(body, cyl(ik["recess_d"] / 2, -1, rec_top), cyl(S.INNER_D / 2 + 0.1, -1, flat0 + 0.01),
               dbore(S.INNER_D + fit, S.INNER_FLAT + fit, flat0, tip))


def range_knob(fit=S.FIT):
    rk = S.RANGE_KNOB
    h = rk["z1"] - rk["z0"]
    sk = rk["skirt_d"] / 2
    body = fuse(fluted(rk["d"] / 2, h, 22, 0.32, 0.05, 0.6, bottom_cham=0.0),
                revolve([(0, 0), (sk, 0), (sk, 0.25), (rk["d"] / 2 - 0.3, 0.25 + sk - rk["d"] / 2 + 0.3), (0, 1.5)]))
    lever0 = S.LEVER_Z0 - S.PLATE_Z1 - rk["z0"]; lever1 = S.LEVER_Z1 - S.PLATE_Z1 - rk["z0"]
    return cut(body, cyl(2.0, -1, max(lever0, 0.3)), dbore(S.LEVER_D + fit, S.LEVER_FLAT + fit, -1, lever1))


def light_pipe(name):
    """a plain rod in the plate hole, glued flush with the face (bottom at z = 0)."""
    pp = S.PIPE
    return cyl((S.LIGHT_HOLES[name] - pp["clear"]) / 2, 0, pp["len"])  # slip fit: anodising shrinks the hole


NECK = 0.6                          # neck length above the pipe top: the stub left after breaking off


def light_pipe_pair(pitch=12.0):
    """Both light pipes on one snap-off bar: JLC3DP prints resin parts from 2 x 2 x 10 mm only. The bar runs
    over the pipe tops on thin necks; sand the stub off with the top before gluing the pipes in."""
    from occ_util import move
    shift, unit = light_pipe("SHIFT"), move(light_pipe("UNIT"), dx=pitch)
    top, nr = S.PIPE["len"], S.PIPE["neck_d"] / 2
    necks = fuse(cyl(nr, top - 0.01, top + NECK + 0.01), cyl(nr, top - 0.01, top + NECK + 0.01, pitch, 0))
    bar = box(-1.1, -1.1, top + NECK, pitch + 1.1, 1.1, top + NECK + 1.2)     # 2.2 wide: the part is 2 mm thick
    return fuse(fuse(shift, unit), fuse(necks, bar))


if __name__ == "__main__":
    assert len(set(S.KNOB_D.values())) == 1, "one outer knob file serves all three dual knobs"
    export(outer_knob(S.KNOB_D["ALTHDG"]), "avionics-panel-rev1-knob-outer")
    export(inner_knob(), "avionics-panel-rev1-knob-inner")
    export(range_knob(), "avionics-panel-rev1-knob-range")
    for tag, fit in S.FIT_VARIANTS.items():
        export(outer_knob(S.KNOB_D["ALTHDG"], fit), f"avionics-panel-rev1-knob-outer-{tag}")
        export(inner_knob(fit), f"avionics-panel-rev1-knob-inner-{tag}")
        export(range_knob(fit), f"avionics-panel-rev1-knob-range-{tag}")
    export(light_pipe_pair(), "avionics-panel-rev1-lightpipes", deflection=0.005)   # SHIFT left, UNIT right
