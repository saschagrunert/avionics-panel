"""Knobs and light pipes for the Avionics Panel rev 1, exact solids (OpenCascade) -> STEP.

Avionics style: matte black resin, fine vertical flutes, slight taper, chamfered flat top. All sizes
come from stack.py (datasheet shaft dimensions); each part has its bottom at z = 0.
  outer knob  dia 17, all three (Garmin proportions: 2.5 mm of ring each side of the inner knob): grips
              the slotted 6 mm outer shaft, with a key in the slot, and ends flush with the shaft top. The
              FMS ring has fewer, deeper flutes, so it feels different from FREQ above it.
  inner knob  dia 12, all three: D bore on the 3.5 mm inner shaft. The bore bottom sits on the shaft tip,
              so a push goes straight to the switch.
  RANGE knob  dia 13.6 with a 16.6 skirt over the 11.1 mm plate hole, D bore on the RKJXT lever.
  light pipes clear resin, stepped: a base that stands on the board over the LED's cutout, up to a shoulder
              under the plate back, and the rod through the plate hole; captive, no glue. Both are printed as
              one part on a snap-off bar under their bases (JLC3DP's minimum resin part is 10 x 2 x 2 mm), on
              1.0 mm necks (resin pillars 1.0 min.).
Fits get tested on the first print (stack.FIT): the knobs are held by friction only, so one outer ring, one FMS
ring, one inner and the RANGE knob also come with a bore 0.2 tighter and 0.2 looser (stack.FIT_VARIANTS); keep
whichever grips, or open a tight bore with a drill of the shaft size and file the D flat.
Needs pythonocc-core (see make_plate_step.py).
"""
import contextlib
import io
import os
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures.process import BrokenProcessPool

import stack as S
from occ_util import box, cut, cyl, dbore, export, fluted, fuse, move, revolve


def knurl(name, r, h, **kw):
    """a fluted knob body with the flutes stack.FLUTES[name]."""
    f = S.FLUTES[name]
    return fluted(r, h, f["n"], f["depth"], f["taper"], f["cham"], **kw)


def outer_key_z0():
    """key bottom above the outer knob's bottom: the key rests on the slot floor at the design height."""
    return S.OUTER_TOP - S.SLOT_LEN - S.PLATE_Z1 - S.OUTER_KNOB["z0"]


def outer_counterbore_top():
    """top of the counterbore round the fixed bushing, above the outer knob's bottom."""
    return S.SLEEVE_TOP - S.PLATE_Z1 - S.OUTER_KNOB["z0"] + S.SLEEVE_CLEAR


def outer_counterbore_d():
    """diameter of the counterbore round the fixed bushing."""
    return S.SLEEVE_D + 2 * S.SLEEVE_CLEAR


def outer_knob(flutes="outer", fit=S.FIT):
    ok = S.OUTER_KNOB
    h = ok["z1"] - ok["z0"]
    body = knurl(flutes, ok["d"] / 2, h)
    key_w = S.KEY_W / 2
    bore = cut(cyl((S.OUTER_D + fit) / 2, -1, h + 1), box(S.KEY_R, -key_w, outer_key_z0(), 4, key_w, h + 2))
    return cut(body, cyl(outer_counterbore_d() / 2, -1, outer_counterbore_top()), bore)


def inner_d_len():
    """length of the inner knob's D bore from the shaft tip down (stack.INNER_BORE_SHORT)."""
    return S.FLAT_LEN - S.INNER_BORE_SHORT


def inner_knob(fit=S.FIT):
    ik = S.INNER_KNOB
    h = ik["z1"] - ik["z0"]
    rec_top = ik["recess_top"] - ik["z0"]
    tip = S.INNER_TOP - S.PLATE_Z1 - ik["z0"]                                 # bore bottom on the shaft tip
    flat0 = tip - inner_d_len()
    body = knurl("inner", ik["d"] / 2, h)
    return cut(body, cyl(ik["recess_d"] / 2, -1, rec_top), cyl(S.INNER_D / 2 + S.INNER_BORE_RELIEF, -1, flat0 + 0.01),
               dbore(S.INNER_D + fit, S.INNER_FLAT + fit, flat0, tip))


def range_knob(fit=S.FIT):
    rk = S.RANGE_KNOB
    h = rk["z1"] - rk["z0"]
    sk = rk["skirt_d"] / 2
    body = fuse(knurl("range", rk["d"] / 2, h, bottom_cham=0.0),
                revolve([(0, 0), (sk, 0), (sk, rk["rim"]), (rk["d"] / 2 - 0.3, rk["rim"] + sk - rk["d"] / 2 + 0.3),
                         (0, rk["rim"] + sk - rk["d"] / 2 + 0.3)]))
    lever0 = S.LEVER_Z0 - S.PLATE_Z1 - rk["z0"]; lever1 = S.LEVER_Z1 - S.PLATE_Z1 - rk["z0"]
    relief_d, relief_min = S.RANGE_RELIEF
    return cut(body, cyl(relief_d / 2, -1, max(lever0, relief_min)),
               dbore(S.LEVER_D + fit, S.LEVER_FLAT + fit, -1, lever1))


def light_pipe():
    """the stepped light pipe (bottom at z = 0, on the board): the base up to the shoulder, then the rod, a slip
    fit in its plate hole (stack.PIPE)."""
    pp = S.PIPE
    base = cyl(pp["base_d"] / 2, 0, pp["base_len"] + 0.01)
    return fuse(base, cyl((S.LIGHT_HOLE - pp["clear"]) / 2, pp["base_len"], pp["len"]))


def light_pipe_pair(pitch=12.0):
    """Both light pipes on one snap-off bar: JLC3DP prints resin parts from 2 x 2 x 10 mm only. The bar runs
    under the bases on thin necks, so the visible tops stay as printed; sand the stubs flat after breaking off."""
    shift, unit = light_pipe(), move(light_pipe(), dx=pitch)
    pp = S.PIPE
    nr, neck = pp["neck_d"] / 2, pp["neck_len"]                          # neck: the stub left after breaking off
    necks = fuse(cyl(nr, -neck - 0.01, 0.01), cyl(nr, -neck - 0.01, 0.01, pitch, 0))
    bw, bh = pp["bar"]                                                    # at least 2 x 2: the part's minimum
    bar = box(-bw / 2, -bw / 2, -neck - bh, pitch + bw / 2, bw / 2, -neck)
    return fuse(fuse(shift, unit), fuse(necks, bar))


def parts():
    """(file name, solid function, its arguments) of every part, in the order they print."""
    out = [("avionics-panel-rev1-knob-outer", outer_knob, ()),                 # ALT/HDG and FREQ
           ("avionics-panel-rev1-knob-outer-fms", outer_knob, ("outer_fms",)),  # FMS: same fits, coarser grip
           ("avionics-panel-rev1-knob-inner", inner_knob, ()),
           ("avionics-panel-rev1-knob-range", range_knob, ())]
    for tag, fit in S.FIT_VARIANTS.items():
        out += [(f"avionics-panel-rev1-knob-outer-{tag}", outer_knob, ("outer", fit)),   # ALT/HDG and FREQ
                (f"avionics-panel-rev1-knob-outer-fms-{tag}", outer_knob, ("outer_fms", fit)),
                (f"avionics-panel-rev1-knob-inner-{tag}", inner_knob, (fit,)),
                (f"avionics-panel-rev1-knob-range-{tag}", range_knob, (fit,))]
    return out + [("avionics-panel-rev1-lightpipes", light_pipe_pair, ())]   # SHIFT left, UNIT right


def build(part):
    """one part's STEP, in a worker process: OpenCascade shapes do not pickle, so the worker builds its own
    solid. Returns what export() printed, which the main process prints in the order of parts()."""
    name, solid, args = part
    with contextlib.redirect_stdout(io.StringIO()) as out:
        export(solid(*args), name)
    return out.getvalue()


if __name__ == "__main__":
    # The parts are independent and take seconds each. Half the CPUs build them: build.sh runs the other
    # sections alongside. A worker that dies (a crash in OpenCascade, out of memory) breaks the pool, which then
    # fails instead of waiting for it forever.
    jobs = parts()
    workers = min(len(jobs), max(1, (os.process_cpu_count() or 1) // 2))
    try:
        with ProcessPoolExecutor(workers) as pool:
            for text in pool.map(build, jobs):
                print(text, end="", flush=True)
    except BrokenProcessPool as e:
        raise SystemExit(f"make_knobs.py: a worker process died ({e})") from e
