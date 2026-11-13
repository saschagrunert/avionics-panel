"""Knobs and light pipes for the Avionics Panel rev 1, exact solids (OpenCascade) -> STEP.

Avionics style: matte black resin, fine vertical flutes, slight taper, chamfered flat top. All sizes
come from stack.py (datasheet shaft dimensions); each part has its bottom at z = 0.
  outer knob  dia 17, all three (Garmin proportions: 2.5 mm of ring each side of the inner knob): grips
              the slotted 6 mm outer shaft, with a key in the slot, and ends flush with the shaft top. The
              FMS ring has fewer, deeper flutes, so it feels different from FREQ above it.
  inner knob  dia 12, all three: D bore on the 3.5 mm inner shaft. The bore bottom sits on the shaft tip,
              so a push goes straight to the switch.
  RANGE knob  dia 13.6 with a 17.3 skirt over the 11.1 mm plate hole, D bore on the RKJXT lever; the underside
              is dished from the hub to the skirt's rim, so the rim clears the plate at full tilt, cocked on the
              lever by its play and pushed.
  light pipes translucent resin, stepped: a base that stands on the board over the LED's cutout, up to a
              shoulder under the plate back, and the rod through the plate hole; captive, no glue. Both are
              printed as one part on a snap-off bar under their bases (JLC3DP's minimum resin part is 10 x 2 x
              2 mm), on 1.0 mm necks (resin pillars 1.0 min.).
The knobs are held by friction only, so each of the four (outer ring, FMS ring, inner, RANGE) comes with five
bores, 0.1 mm apart (stack.FIT_VARIANTS): knob-<type>-1 has the tightest, knob-<type>-5 the loosest, and as many
dimples on its underside as its number, with a gap after the third (stack.KNOB_MARK). The one to keep goes on
by hand and holds.
Needs pythonocc-core (nix-shell nix/shells.nix -A gen, from the repository root).
"""
import contextlib
import io
import math
import os
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures.process import BrokenProcessPool

import stack as S
from occ_util import box, cut, cyl, dbore, export, fluted, fuse, move, revolve

# the bore drawn at the shaft size plus stack.FIT: the knob in the sections and the 3D view
NOMINAL = min(S.FIT_VARIANTS, key=lambda n: abs(S.FIT_VARIANTS[n]))


def knurl(name, r, h, **kw):
    """a fluted knob body with the flutes stack.FLUTES[name]."""
    f = S.FLUTES[name]
    return fluted(r, h, f["n"], f["depth"], f["taper"], f["cham"], **kw)


def place_xy(kind, place):
    """the axis of a place (from 0) on the dimples' circle of a knob of FLUTES name `kind` (stack.KNOB_MARK)."""
    m = S.KNOB_MARK
    a = math.radians(m["first"][kind] + place * m["pitch"][kind])
    return m["r"][kind] * math.cos(a), m["r"][kind] * math.sin(a)


def mark_xy(kind, k):
    """the axis of dimple k (from 0): the place after the first KNOB_MARK["group"] stays empty. None of the
    dimples lies on the knob's XZ section."""
    return place_xy(kind, k + (k >= S.KNOB_MARK["group"]))


def marks(kind, n, z0, z1):
    """the cutters of the n dimples that number a knob's bore, from z0 up to z1."""
    return [cyl(S.KNOB_MARK["d"] / 2, z0, z1, *mark_xy(kind, k)) for k in range(n)]


def outer_key_z0():
    """key bottom above the outer knob's bottom: the key rests on the slot floor at the design height."""
    return S.OUTER_TOP - S.SLOT_LEN - S.PLATE_Z1 - S.OUTER_KNOB["z0"]


def outer_counterbore_top():
    """top of the counterbore round the fixed bushing, above the outer knob's bottom."""
    return S.SLEEVE_TOP - S.PLATE_Z1 - S.OUTER_KNOB["z0"] + S.SLEEVE_CLEAR["above"]


def outer_counterbore_d():
    """diameter of the counterbore round the fixed bushing."""
    return S.SLEEVE_D + 2 * S.SLEEVE_CLEAR["radial"]


def outer_knob(flutes="outer", n=NOMINAL):
    """an outer ring with the flutes `flutes` and bore n, its dimples in the bottom face."""
    ok = S.OUTER_KNOB
    h = ok["z1"] - ok["z0"]
    body = knurl(flutes, ok["d"] / 2, h)
    key_w = S.KEY_W / 2
    fit = S.FIT + S.FIT_VARIANTS[n]
    bore = cut(cyl((S.OUTER_D + fit) / 2, -1, h + 1), box(S.KEY_R, -key_w, outer_key_z0(), 4, key_w, h + 2))
    return cut(body, cyl(outer_counterbore_d() / 2, -1, outer_counterbore_top()), bore,
               *marks(flutes, n, -1, S.KNOB_MARK["depth"]))


def inner_d_len():
    """length of the inner knob's D bore from the shaft tip down (stack.INNER_BORE_SHORT)."""
    return S.FLAT_LEN - S.INNER_BORE_SHORT


def inner_recess_top():
    """the ceiling of the inner knob's recess round the outer shaft top, above the knob's bottom."""
    return S.INNER_KNOB["recess_top"] - S.INNER_KNOB["z0"]


def relief_d(kind, n):
    """diameter of the round relief bore under the D bore n of the inner or the RANGE knob: the stack's, and never
    narrower than the D bore over it, so a shaft that fits the bore passes the relief."""
    base, shaft = {"inner": (S.INNER_D + 2 * S.INNER_BORE_RELIEF, S.INNER_D),
                   "range": (S.RANGE_RELIEF[0], S.LEVER_D)}[kind]
    return max(base, shaft + S.FIT + S.FIT_VARIANTS[n])


def inner_knob(n=NOMINAL):
    """an inner knob with bore n, its dimples in the ceiling of its recess."""
    ik = S.INNER_KNOB
    h = ik["z1"] - ik["z0"]
    rec_top = inner_recess_top()
    tip = S.INNER_TOP - S.PLATE_Z1 - ik["z0"]                                 # bore bottom on the shaft tip
    flat0 = tip - inner_d_len()
    fit = S.FIT + S.FIT_VARIANTS[n]
    body = knurl("inner", ik["d"] / 2, h)
    return cut(body, cyl(ik["recess_d"] / 2, -1, rec_top), cyl(relief_d("inner", n) / 2, -1, flat0 + 0.01),
               dbore(S.INNER_D + fit, S.INNER_FLAT + fit, flat0, tip),
               *marks("inner", n, rec_top - 0.01, rec_top + S.KNOB_MARK["depth"]))


def range_dish(r):
    """how far the RANGE knob's dished underside is over its bottom plane at radius r (outside the hub's flat)."""
    rk = S.RANGE_KNOB
    return rk["dish"] * (r - rk["hub_d"] / 2) / ((rk["skirt_d"] - rk["hub_d"]) / 2)


def range_mark_top():
    """the top of the RANGE knob's dimples above its bottom plane: `depth` over the dish at their far side."""
    m = S.KNOB_MARK
    return range_dish(m["r"]["range"] + m["d"] / 2) + m["depth"]


def range_knob(n=NOMINAL):
    """the RANGE knob with bore n: fluted body, the skirt with its 45 degree top, the underside dished from the
    flat hub (hub_d across) up by `dish` to the rim (stack.RANGE_KNOB), its dimples in the dish."""
    rk = S.RANGE_KNOB
    h = rk["z1"] - rk["z0"]
    sk, r0, u = rk["skirt_d"] / 2, rk["hub_d"] / 2, rk["dish"]
    top = u + rk["rim"] + sk - rk["d"] / 2 + rk["sink"]     # where the skirt's 45 degree top meets the body
    fit = S.FIT + S.FIT_VARIANTS[n]
    body = fuse(knurl("range", rk["d"] / 2, h, bottom_cham=0.0),
                revolve([(0, 0), (sk, 0), (sk, u + rk["rim"]), (rk["d"] / 2 - rk["sink"], top), (0, top)]))
    # the dish: everything under the cone from the hub's edge (r0, 0) to the rim's bottom edge (sk, u)
    body = cut(body, revolve([(r0, -1), (r0, 0), (sk + 1, range_dish(sk + 1)), (sk + 1, -1)]))
    lever0 = S.LEVER_Z0 - S.PLATE_Z1 - rk["z0"]; lever1 = S.LEVER_Z1 - S.PLATE_Z1 - rk["z0"]
    return cut(body, cyl(relief_d("range", n) / 2, -1, max(lever0, S.RANGE_RELIEF[1])),
               dbore(S.LEVER_D + fit, S.LEVER_FLAT + fit, -1, lever1), *marks("range", n, -1, range_mark_top()))


def light_pipe():
    """the stepped light pipe (bottom at z = 0, on the board): the base up to the shoulder, then the rod, a slip
    fit in its plate hole (stack.PIPE)."""
    pp = S.PIPE
    base = cyl(pp["base_d"] / 2, 0, pp["base_len"])
    return fuse(base, cyl((S.LIGHT_HOLE - pp["clear"]) / 2, pp["base_len"] - 0.01, pp["len"]))   # joined in the base


PIPE_PITCH = 12.0                 # the two light pipes on their bar, axis to axis


def light_pipe_pair(pitch=PIPE_PITCH):
    """Both light pipes on one snap-off bar: JLC3DP prints resin parts from 2 x 2 x 10 mm only. The bar runs
    under the bases on thin necks, so the visible tops stay as printed; sand the stubs flat after breaking off."""
    shift, unit = light_pipe(), move(light_pipe(), dx=pitch)
    pp = S.PIPE
    nr, neck = pp["neck_d"] / 2, pp["neck_len"]                          # neck: the stub left after breaking off
    necks = fuse(cyl(nr, -neck - 0.01, 0.01), cyl(nr, -neck - 0.01, 0.01, pitch, 0))
    bw, bh = pp["bar"]                                                    # at least 2 x 2: the part's minimum
    bar = box(-bw / 2, -bw / 2, -neck - bh, pitch + bw / 2, bw / 2, -neck)
    return fuse(fuse(shift, unit), fuse(necks, bar))


# the four knobs: (file name part, FLUTES name, solid function, its arguments before the bore's number), and how
# many of each the panel takes
KNOBS = (("outer", "outer", outer_knob, ("outer",)),            # ALT/HDG and FREQ
         ("outer-fms", "outer_fms", outer_knob, ("outer_fms",)),    # FMS: same fits, coarser grip
         ("inner", "inner", inner_knob, ()),
         ("range", "range", range_knob, ()))
QUANTITY = {"outer": 2, "outer-fms": 1, "inner": 3, "range": 1}


def parts():
    """(file name, solid function, its arguments) of every part, in the order they print: each knob with each of
    its bores (stack.FIT_VARIANTS), then the light pipes."""
    out = [(f"avionics-panel-rev1-knob-{name}-{n}", solid, (*args, n))
           for name, _kind, solid, args in KNOBS for n in S.FIT_VARIANTS]
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
    print(f"{len(jobs) - 1} knob files, bores {', '.join(f'{S.FIT + v:+.1f}' for v in S.FIT_VARIANTS.values())} "
          f"about the shaft size, to order {', '.join(f'{q} x {name}' for name, q in QUANTITY.items())} of each")
