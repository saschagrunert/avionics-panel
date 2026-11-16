"""The two checkers fail on known-bad cases: pcb/check.py on a via whose annular ring is under JLCPCB's minimum,
on drills under its smallest, on swapped pin nets, on a pin table whose LCSC number no part has, on the exposed
pad's paste windows bunched in one corner, on a bottom legend that reads from the top, on a USB line too long or
too skewed on its path or too long in all with a stub, on a mask opening grown too far on one axis, on inner copper
at the board edge, on holes too close by their extent (a slot's end) and on a horizontal slot drilled along y or
with a thin ring, after reading one back as make.py drills it; mech/check_fit.py on a row whose margin is below zero
or not a number, on a tap drill of another depth than the stack's and on bare copper under a body boss. Both need
the generators' packages (numpy, shapely, OpenCascade), which the gen shell of nix/shells.nix has and the
test shell does not, so each case runs there, through nix-shell; without nix-shell these tests skip."""
import os
import shlex
import shutil
import subprocess

import pytest

from conftest import ROOT

pytestmark = pytest.mark.skipif(shutil.which("nix-shell") is None,
                                reason="nix-shell missing: the checkers run in the gen shell of nix/shells.nix")


def gen(where, code):
    """the lines starting with RESULT that code prints, run by the gen shell's python3 in where (pcb or mech, or
    a folder)"""
    r = subprocess.run(["nix-shell", os.path.join(ROOT, "nix", "shells.nix"), "-A", "gen", "--run",
                        "python3 -c " + shlex.quote(code)],
                       cwd=os.path.join(ROOT, where), capture_output=True, text=True, timeout=600)
    assert r.returncode == 0, r.stdout + r.stderr
    return [ln.split(None, 1)[1] for ln in r.stdout.splitlines() if ln.startswith("RESULT ")]


@pytest.fixture(scope="module")
def made(tmp_path_factory):
    """a copy of pcb/ with Gerbers of its own, made by make.py: pcb/gerbers may be missing (a fresh clone) or
    being rewritten (build.sh runs the tests and the board section at once). mech/ is linked, for board.py's
    stack.py"""
    root = tmp_path_factory.mktemp("made")
    pcb = root / "pcb"
    shutil.copytree(os.path.join(ROOT, "pcb"), pcb,
                    ignore=shutil.ignore_patterns("gerbers", "__pycache__", "avionics-panel-rev1-*"))
    os.symlink(os.path.join(ROOT, "mech"), root / "mech")
    gen(str(pcb), "import make")
    return str(pcb)


def test_check_py_fails_on_a_thin_annular_ring_and_on_small_drills():
    # vias as routed.json has them (x, y, net, pad diameter, drill), holes as the drill files give them
    code = """
import check
cases = {
    "good": ([(10.0, 10.0, "N", 0.45, 0.3)], [(10.0, 10.0, 0.3)], [(20.0, 20.0, 0.5)]),
    "thin ring": ([(10.0, 10.0, "N", 0.40, 0.3)], [(10.0, 10.0, 0.3)], []),
    "small drill": ([(10.0, 10.0, "N", 0.45, 0.25)], [(10.0, 10.0, 0.25)], []),
    "small unplated hole": ([], [], [(20.0, 20.0, 0.4)]),
}
for name, (vias, pth, npth) in cases.items():
    print("RESULT", name, check.drill_rings([], vias, pth, npth)[0])
"""
    assert gen("pcb", code) == ["good 0", "thin ring 1", "small drill 1", "small unplated hole 1"]


def test_check_py_measures_the_area_the_exposed_pads_paste_covers():
    # the windows as make.py places them, and all four moved into one corner (overlapping)
    code = """
import board, check
from shapely.geometry import box
ep = next(p for p in board.build() if p.name == "U1.EP")
def windows(spots):
    return [box(ep.x + dx - s / 2, ep.y + dy - s / 2, ep.x + dx + s / 2, ep.y + dy + s / 2) for dx, dy, s in spots]
spread = [(sx * 0.95, sy * 0.95, 1.1) for sx in (-1, 1) for sy in (-1, 1)]
for name, spots in (("spread", spread), ("one corner", [(0.95, 0.95, 1.1)] * 4), ("none", [])):
    share = check.paste_share(ep, windows(spots))
    print("RESULT", name, check.EP_PASTE[0] <= share <= check.EP_PASTE[1])
"""
    assert gen("pcb", code) == ["spread True", "one corner False", "none False"]


def test_check_py_tells_a_mirrored_title_from_one_that_reads_from_the_top():
    code = """
import functools, board, check
from shapely import make_valid
from shapely.affinity import scale, translate
from shapely.geometry import Polygon
from matplotlib.textpath import TextPath
text, x, y = board.TITLE
tp = TextPath((0, 0), text, size=1.4, prop=check.LEGEND_FONT)
drawn = functools.reduce(lambda a, b: a.symmetric_difference(b),
                         (make_valid(Polygon(p)) for p in tp.to_polygons(closed_only=True)), Polygon())
for name, sx in (("mirrored", -1.0), ("read from the top", 1.0)):
    legend = translate(scale(drawn, sx, -1.0, origin=(0, 0)), x, y + 0.5)     # board y down
    match = check.mirror_match(legend)
    print("RESULT", name, match[True] >= check.MIRROR_MATCH > match[False])
"""
    assert gen("pcb", code) == ["mirrored True", "read from the top False"]


def test_check_py_fails_on_swapped_pins():
    # two pins' nets swapped at the flash, the regulator, the LED switch and the USB-C socket, and a pad missing
    code = """
import board, check
for name, change in (("as built", None), ("U2 SD1 / SD2", ("U2.2", "U2.3")), ("U3 in / out", ("U3.2", "U3.3")),
                     ("Q gate / drain", ("Q_UNIT.1", "Q_UNIT.3")), ("J1 D+ / D-", ("J1.A6", "J1.A7")),
                     ("U2 pad 8 missing", ("U2.8",))):
    pads = board.build()
    by = {p.name: p for p in pads}
    if change and len(change) == 2:
        by[change[0]].net, by[change[1]].net = by[change[1]].net, by[change[0]].net
    elif change:
        pads.remove(by[change[0]])
    print("RESULT", name, check.symbol_pins(pads))
"""
    assert gen("pcb", code) == ["as built 0", "U2 SD1 / SD2 2", "U3 in / out 2", "Q gate / drain 2",
                                "J1 D+ / D- 2", "U2 pad 8 missing 2"]


def test_check_fit_py_fails_on_a_tap_drill_of_another_depth():
    code = '''
import check_fit, stack
tp = stack.TAP
pm = dict(boss_h=(stack.BOSS["h"],) * 2, boss_d=(stack.BOSS["d"],) * 2, boss_off=0.0,
          drill=(tp["drill"],) * 2, sink=(tp["drill"],) * 2)
for name, tap in (("as drawn", tp["depth"] + tp["point"]), ("2 mm shallower", tp["depth"] + tp["point"] - 2.0)):
    print("RESULT", name, check_fit.boss_build_row(dict(pm, tap=tap))[1] > 0)
'''
    assert gen("mech", code) == ["as drawn True", "2 mm shallower False"]


def test_check_fit_py_fails_on_a_margin_under_zero():
    code = """
import check_fit
for name, margin in (("holds", 0.1), ("under zero", -0.01), ("not a number", float("nan"))):
    try:
        check_fit.report([(f"a row that {name}", margin)])
        print("RESULT", name, "passes")
    except SystemExit:
        print("RESULT", name, "fails")
"""
    assert gen("mech", code) == ["holds passes", "under zero fails", "not a number fails"]


def test_check_py_fails_on_a_long_or_skewed_usb_line_and_on_a_long_stub():
    # each change sized from the margins as routed, so a re-route keeps it: D- 1 mm per side past USB_MAX, on its
    # path and in all (2); D+ 1 mm per side past USB_SKEW under a USB_MAX raised clear of it: skew alone (1); a
    # dead-end stub on USB_DP_C 1 mm past USB_MAX in all: the paths as routed, the total over USB_MAX (1)
    code = """
import json, board, check, geom
rd = json.load(open("routed.json"))
pads, segs, vias = board.build(), rd["segments"], rd["vias"]
paths, _ok = geom.usb_paths(pads, segs, vias)
total = geom.usb_totals(geom.net_lengths(segs))
def flat(net):              # net's longest segment along x
    return max((s for s in segs if s[5] == net and s[1] == s[3]), key=lambda s: abs(s[2] - s[0]))
def detour(net, up):        # flat(net) replaced by a U up mm off it: 2 x up longer
    s = flat(net)
    (x0, y), x1 = s[:2], s[2]
    return [t for t in segs if t is not s] + [[*a, *b, *s[4:]] for a, b in (
        ((x0, y), (x0, y + up)), ((x0, y + up), (x1, y + up)), ((x1, y + up), (x1, y)))]
long = (geom.USB_MAX - min(max(r["D-"] for r in paths.values()), total["D-"])) / 2 + 1
skew = (geom.USB_SKEW - min(r["D+"] - r["D-"] for r in paths.values())) / 2 + 1
most = max([*total.values()] + [v for r in paths.values() for v in r.values()]) + 2 * skew + 1
x, y, *_x, ly, _n, w = flat("USB_DP_C")
stub = [x, y, x, y - (geom.USB_MAX - total["D+"] + 1), ly, "USB_DP_C", w]
for name, segs_, most_ in (("as routed", segs, geom.USB_MAX), ("D- long", detour("USB_DM", long), geom.USB_MAX),
                           ("skewed", detour("USB_DP", skew), most), ("stub", segs + [stub], geom.USB_MAX)):
    geom.USB_MAX = check.USB_MAX = most_
    got, ok = geom.usb_paths(pads, segs_, vias)
    print("RESULT", name, ok, got == paths, check.lengths(pads, segs_, vias))
"""
    assert gen("pcb", code) == ["as routed True True 0", "D- long False False 2", "skewed False False 1",
                                "stub True True 1"]


def test_check_py_fails_on_a_pin_table_whose_lcsc_no_part_has():
    # also once the old number's footprint file is gone: a problem counted, not a crash
    code = """
import board, check
pads = board.build()
print("RESULT as built", check.symbol_pins(pads))
old = next(lc for ref, _v, lc, *_r in board.PARTS if ref == "U3")
board.PARTS[:] = [(ref, v, "C0" if ref == "U3" else lc, *r) for ref, v, lc, *r in board.PARTS]
print("RESULT U3 on another LCSC", check.symbol_pins(pads))
read = check.jlc_footprint
def gone(lcsc):
    if lcsc == old:
        raise FileNotFoundError(f"footprints/{lcsc}.json")
    return read(lcsc)
check.jlc_footprint = gone
print("RESULT its footprint file gone", check.symbol_pins(pads))
"""
    assert gen("pcb", code) == ["as built 0", "U3 on another LCSC 1", "its footprint file gone 1"]


def test_check_py_fails_on_a_mask_opening_grown_on_one_axis(made):
    # F1.1's opening 0.05 mm longer at each end: its narrowest margin as before, its widest past MASK_MAX_GROW
    code = """
import contextlib, io, board, check, gerber_io
pads, p = board.build(), next(p for p in board.build() if p.name == "F1.1")
def grown(fname):
    return [("rect", g[1], g[2] - 0.05, g[3], g[4] + 0.05, g[5])
            if g[0] == "rect" and abs((g[1] + g[3]) / 2 - p.x) < 1e-3 and abs((g[2] + g[4]) / 2 - p.y) < 1e-3 else g
            for g in gerber_io.flashes(fname)]
for name, read in (("as made", gerber_io.flashes), ("grown", grown)):
    check.flashes, out = read, io.StringIO()
    with contextlib.redirect_stdout(out):
        check.mask_dams(pads, [])
    print("RESULT", name, "OVER F1.1 " in out.getvalue())
"""
    assert gen(made, code) == ["as made False", "grown True"]


def test_check_py_fails_on_inner_copper_at_the_board_edge(made):
    code = """
import board, check, gerber_io
from shapely.geometry import box
copper = {ly: gerber_io.vector_copper(check.LAYERS[ly]) for ly in board.PLANES}
print("RESULT as made", check.inner_edge(copper))
copper["In1"] = copper["In1"].union(box(0.2, board.H / 2 - 1, 1.0, board.H / 2 + 1))
print("RESULT In1 0.2 mm from the edge", check.inner_edge(copper))
"""
    assert gen(made, code) == ["as made 0", "In1 0.2 mm from the edge 1"]


def test_check_py_pairs_holes_by_their_extent():
    # a 6 mm slot and a round hole of another net 3.6 mm from its centre: 0.1 mm from its end, and 1 mm at 4.5
    code = """
import board, check
x, y = 80.0, 30.0
board.build()
for name, dy in (("1 mm apart", 4.5), ("0.1 mm apart", 3.6)):
    pads = [board.Pad("S.1", "A", x, y, "obround", 2.0, 7.0, "FB", drill=1.0, slot=(1.0, 6.0)),
            board.Pad("H.1", "B", x, y + dy, "circle", 1.6, 1.6, "FB", drill=1.0)]
    print("RESULT", name, check.hole_spacing(pads, []))
"""
    assert gen("pcb", code) == ["1 mm apart 0", "0.1 mm apart 1"]


def test_check_py_reads_back_a_horizontal_slot_as_make_py_drills_it():
    # make.py's drill() and its slots line run on one pad with a slot along x, written to a scratch gerbers/: as
    # made it matches the model and its ring holds; drilled along y it does not match; in a pad 0.8 mm shorter its
    # ring along x is too thin
    code = """
import ast, os, tempfile, board, check, gerber_io
tree = ast.parse(open("make.py").read())
made = ast.Module([n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "drill" or
                   isinstance(n, ast.Assign) and getattr(n.targets[0], "id", None) == "slots"], [])
board.build()                                   # board.NPTH
os.chdir(tempfile.mkdtemp())
os.mkdir("gerbers")
for name, w, tall in (("as made", 3.6, None), ("along y", 3.6, True), ("short pad", 2.8, None)):
    pad = board.Pad("ENC.MP1", "GND", 80.0, 30.0, "obround", w, 2.5, "FB", drill=1.5, slot=(1.5, 2.6))
    ns = {"B": board, "os": os, "OUT": "gerbers", "pads": [pad]}
    exec(compile(made, "make.py", "exec"), ns)
    slots = [(*s[:4], tall) for s in ns["slots"]] if tall else ns["slots"]
    ns["drill"]("avionics-PTH.drl", [], True, slots)
    ns["drill"]("avionics-NPTH.drl", [(x, y, board.MOUNT_HOLE) for x, y in board.MOUNTS] + board.NPTH, False)
    rings = check.drill_rings([pad], [], gerber_io.read_drill("avionics-PTH.drl"), [])[0]
    print("RESULT", name, ns["slots"][0][4], check.drill_model([pad], []) > 0, rings > 0)
"""
    assert gen("pcb", code) == ["as made False False False", "along y False True False", "short pad False False True"]


def test_check_fit_py_fails_on_bare_copper_under_a_body_boss():
    # the row of boss_fits(), the fit values as fit_values() works them out (the reach and the bare copper by
    # boss_bare(), as there); a fiducial moved next to a mount
    code = '''
import types, check_fit, board as B, make_mech as MM, stack as S
pt, sc, bo, tp = S.POS_TOL, S.SCREW, S.BOSS, S.TAP
hole = B.MOUNT_HOLE
hole_lo, hole_hi = (hole - pt["npth_d"]) / 2, (hole + pt["npth_d"]) / 2
off = hole_hi - sc["d_min"] / 2 + pt["thread"]
fv = dict(hole=hole, pt=pt, need=0.0, hole_lo=hole_lo, hole_hi=hole_hi, bo=bo, off=off, keepout=B.MOUNT_KEEPOUT,
          boss_lo=(bo["d"] - bo["d_tol"]) / 2, boss_hi=(bo["d"] + bo["d_tol"]) / 2, offset=MM.SCREW_OFFSET,
          pm=dict(boss_h=(bo["h"],) * 2, boss_d=(bo["d"],) * 2, boss_off=0.0, drill=(tp["drill"],) * 2,
                  sink=(tp["drill"],) * 2, tap=tp["depth"] + tp["point"]))
pads = B.build()
reach = check_fit.boss_bare(pads, fv["offset"], off)[0]
for name, move in (("as placed", False), ("fiducial at a mount", True)):
    if move:
        fid = next(p for p in pads if p.name == "FID.1")
        fid.x, fid.y = B.MOUNTS[0][0] + reach, B.MOUNTS[0][1]
    boss_reach, bare, bare_pad = check_fit.boss_bare(pads, fv["offset"], off)
    rows = check_fit.boss_fits(types.SimpleNamespace(**fv, boss_reach=boss_reach, bare=bare, bare_pad=bare_pad))
    print("RESULT", name, next(r for r in rows if r[0].startswith("body boss tops (R"))[1] > 0)
'''
    assert gen("mech", code) == ["as placed True", "fiducial at a mount False"]
