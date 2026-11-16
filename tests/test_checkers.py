"""The checkers fail on known-bad cases: pcb/check.py on a via whose annular ring is under JLCPCB's minimum, on drills
under its smallest, on swapped pin nets, on a pin table whose LCSC number no part has, on the exposed pad's paste
windows bunched in one corner, on a bottom legend that reads from the top, on a USB line too long or too skewed on
its path or too long in all with a stub, on a mask opening grown too far on one axis, on inner copper at the board
edge, on holes too close by their extent (a slot's end) and on a horizontal slot drilled along y or with a thin
ring, after reading one back as make.py drills it; its reader (gerber_io.py) on any number format, unit, command or
drill header make.py does not write; each of its checks of the files on a copy of them with one thing changed (a
short on F_Cu, a file's polarity, the zip against the files, copper in a mounting hole's keep-out or an LED cutout,
a pad flash or a paste opening deleted, a mounting hole or an LED cutout moved, legend on a pad or past the board
edge, a cathode bar or the pin 1 dots deleted, the CPL's Layer in lowercase, parts turned in the CPL); its fit of
JLC's through-hole footprints on the encoder lug slots as drawn (it passes), without their allowance and drawn as
JLC's; its checks of board.py's pads on a cathode pad renamed, swapped or on a part board.py does not have, a
decoupling capacitor or a fiducial gone; pcb/precheck.py on a pad on another one, at the board edge or in a mounting
hole's keep-out and on a body on another; mech/check_fit.py on a row whose margin is below zero or not a number (or
zero, unless the row is marked MEETS), and it prints a row's bounded worst case beside its RSS margin, passing on
the RSS one; on a tap drill of another depth than the stack's, on bare copper under a body boss, on a cap legend
missing or ink on a cap without one, a set's texture or a single cap off its set (its shape, UVs, zip, material or
tile), and its plate and body measures on a light hole moved and the walls raised; the read-backs of the plate's
STEP and DXF on a hole, a vertex, a polygon or a layer's order changed and on DXF groups the writer does not write;
occ_util.face_diff on a face of another type, area or centroid and on a face twice. They need the generators'
packages (numpy, shapely, OpenCascade), which the gen shell of nix/shells.nix has and the test shell does not, so
each case runs there, through nix-shell; without nix-shell these tests skip."""
import os
import re
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
    """a copy of pcb/ with Gerbers, BOM and CPL of its own, made by make.py and make_bom.py: pcb/gerbers may be
    missing (a fresh clone) or being rewritten (build.sh runs the tests and the board section at once). mech/ is
    linked, for board.py's stack.py"""
    root = tmp_path_factory.mktemp("made")
    pcb = root / "pcb"
    shutil.copytree(os.path.join(ROOT, "pcb"), pcb,
                    ignore=shutil.ignore_patterns("gerbers", "__pycache__", "avionics-panel-rev1-*"))
    os.symlink(os.path.join(ROOT, "mech"), root / "mech")
    gen(str(pcb), "import make, make_bom")
    return str(pcb)


# For the cases on made's files, in the gen shell: case() makes a scratch copy of the board's files (gerbers/, the
# zip, the BOM and CPL files) with some of them edited, works there and goes back; run() calls a check there
# without its printout and gives its count of problems, or "raises" for the ValueError of a file it cannot read.
# Each check reads only the files it needs, so each case copies the files and reruns one check, not the build.
BOARD = """
import contextlib, glob, io, json, os, re, shutil, tempfile
import board, check, gerber_io
HOME = os.getcwd()
pads = board.build()
by = {p.name: p for p in pads}
with open("routed.json") as f:
    rd = json.load(f)
segments, vias = rd["segments"], rd["vias"]


@contextlib.contextmanager
def case(edits=None):
    d = tempfile.mkdtemp()
    shutil.copytree("gerbers", os.path.join(d, "gerbers"))
    for f in glob.glob("avionics-panel-rev1-*"):
        shutil.copy(f, d)
    os.symlink(os.path.join(HOME, "footprints"), os.path.join(d, "footprints"))
    os.chdir(d)
    try:
        for fname, edit in (edits or {}).items():
            path = fname if os.path.exists(fname) else os.path.join("gerbers", fname)
            with open(path) as f:
                txt = f.read()
            new = edit(txt)
            assert new != txt, fname
            with open(path, "w") as f:
                f.write(new)
        yield
    finally:
        os.chdir(HOME)
        shutil.rmtree(d)


def run(f, *args):
    with contextlib.redirect_stdout(io.StringIO()):
        try:
            got = f(*args)
        except ValueError:
            return "raises"
    return got[1] if isinstance(got, tuple) else got


def sub(pattern, repl, count=1):
    return lambda txt: re.sub(pattern, repl, txt, count=count, flags=re.M)


def xy(x, y):
    return f"X{round(x * 1e6)}Y{round((board.H - y) * 1e6)}"       # board mm (y down) as Gerber coordinates


def drawn(*new):
    # new blocks at the end of a Gerber, dark, with its first aperture
    def edit(txt):
        n = re.search(r"%ADD(\\d+)", txt).group(1)
        return txt.replace("M02*", "\\n".join(["%LPD*%", f"D{n}*", *new, "M02*"]))
    return edit
"""


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
    code = """
import check_fit
for name, row in (("MEETS at zero", (0.0, check_fit.MEETS)), ("MEETS under zero", (-0.001, check_fit.MEETS)),
                  ("plain at zero", (0.0,))):
    try:
        check_fit.report([(f"a row, {name}", *row)])
        print("RESULT", name, "passes")
    except SystemExit:
        print("RESULT", name, "fails")
"""
    assert gen("mech", code) == ["MEETS at zero passes", "MEETS under zero fails", "plain at zero fails"]


def test_check_fit_py_prints_the_bounded_worst_case_of_an_rss_row_and_passes_on_the_rss_one():
    # 0.3, 0.4 and 1.2 add to 1.3 as a root sum square and to 1.9 linearly: a row with 1.4 of room passes on its
    # RSS margin (0.1) and prints its bounded worst case (-0.5) beside it; with 1.2 of room it fails, on RSS
    code = """
import contextlib, io, check_fit
rss, linear = check_fit.spread(0.3, 0.4, 1.2)
print("RESULT spread", f"{rss:.3f}", f"{linear:.3f}", linear == 0.3 + 0.4 + 1.2)
for name, room in (("room 1.4", 1.4), ("room 1.2", 1.2)):
    out = io.StringIO()
    try:
        with contextlib.redirect_stdout(out):
            rows = check_fit.report([(f"a row, {name}, RSS", room - rss, check_fit.Bounded(room - linear))])
        result = f"passes, bounded {rows[0][5]:.3f}"
    except SystemExit:
        result = "fails"
    line = out.getvalue().strip()
    print("RESULT", name, result, f"{room - rss:.3f}" in line, f"bounded worst case {room - linear:.3f}" in line)
"""
    assert gen("mech", code) == ["spread 1.300 1.900 True", "room 1.4 passes, bounded -0.500 True True",
                                 "room 1.2 fails True True"]


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


def test_gerber_io_reads_only_what_make_py_writes(made):
    # every file as made reads; each other format, unit, command or drill header raises
    code = BOARD + r"""
gerbers = sorted(f for f in os.listdir("gerbers") if not f.endswith(".drl"))
def read(fname):
    return run(gerber_io.drill_hits if fname.endswith(".drl") else gerber_io.gerber_ops, fname)
with case():
    print("RESULT as made", sorted({"raises" if read(f) == "raises" else "reads" for f in os.listdir("gerbers")}))
with case({f: sub(r"^%FSLAX46Y46\*%$", "%FSLAX45Y45*%") for f in gerbers}):
    print("RESULT FSLAX45Y45 everywhere", sorted({read(f) for f in gerbers}))
edge, cu, npth = "avionics-Edge_Cuts.gko", "avionics-F_Cu.gtl", "avionics-NPTH.drl"
zones = "avionics-In1_Cu.g2"                             # its regions come before its first aperture is selected
def unit_late(txt):                                      # %MOMM*% moved below the first coordinate
    txt = txt.replace("%MOMM*%\n", "", 1)
    return re.sub(r"^(X\d+Y\d+D0\d\*)$", r"\1\n%MOMM*%", txt, count=1, flags=re.M)
def comment_first(txt):                                  # the drill file's FileFunction comment right after M48
    ff = re.search(r"^; #@! TF\.FileFunction.*\n", txt, flags=re.M).group()
    return txt.replace(ff, "").replace("M48\n", "M48\n" + ff, 1)
for name, fname, edit in (
        ("Edge_Cuts in inches", edge, sub(r"^%MOMM\*%$", "%MOIN*%")),
        ("Edge_Cuts G03 for G01", edge, sub(r"^G01\*$", "G03*")),
        ("a G02 arc", cu, sub(r"^G01\*$", "G01*\nG02*")),
        ("G75", cu, sub(r"^G01\*$", "G01*\nG75*")),
        ("an aperture macro", cu, sub(r"^%MOMM\*%$", "%MOMM*%\n%AMOC8*5,1,8,0,0,1.08239X$1,22.5*%")),
        ("a polygon aperture", cu, sub(r"^%MOMM\*%$", "%MOMM*%\n%ADD99P,1.0X6*%")),
        ("a unit after the first coordinate", edge, unit_late),
        ("FS twice", edge, sub(r"^%MOMM\*%$", "%MOMM*%\n%FSLAX46Y46*%")),
        ("MO twice", edge, sub(r"^%MOMM\*%$", "%MOMM*%\n%MOMM*%")),
        ("an aperture's D code twice", cu, sub(r"^(%ADD10C,[^%]*%)$", r"\1\n\1")),
        ("an aperture's D code under 10", cu, sub(r"^%MOMM\*%$", "%MOMM*%\n%ADD9C,0.1000*%")),
        ("a circle aperture with a Y size", cu, sub(r"^%MOMM\*%$", "%MOMM*%\n%ADD99C,0.1000X0.2000*%")),
        ("a rectangle aperture without its X size", cu, sub(r"^%MOMM\*%$", "%MOMM*%\n%ADD99R,0.1000*%")),
        ("an obround aperture without its X size", cu, sub(r"^%MOMM\*%$", "%MOMM*%\n%ADD99O,0.1000*%")),
        ("a comment without the space after G04", cu, sub(r"^%MOMM\*%$", "%MOMM*%\nG04changed*")),
        ("an aperture attribute", cu, sub(r"^%MOMM\*%$", "%MOMM*%\n%TA.AperFunction,SMDPad,CuDef*%")),
        ("D01 before G01", cu, sub(r"^G01\*\n", "")),
        ("a flash before an aperture is selected", cu, sub(r"^G01\*$", "G01*\nX0Y0D03*")),
        ("a D01 before an aperture is selected", cu, sub(r"^G01\*$", "G01*\nX0Y0D01*")),
        ("a G36 in a region", zones, sub(r"^G36\*$", "G36*\nG36*")),
        ("a flash in a region", zones, sub(r"^G36\*$", "G36*\nX0Y0D03*")),
        ("Edge_Cuts without M02", edge, sub(r"^M02\*\n", "")),
        ("a region open at M02", zones, sub(r"^M02\*$", "G36*\nM02*")),
        ("a coordinate without Y", edge, sub(r"^(X\d+)Y\d+(D01\*)$", r"\1\2")),
        ("a D01 without a coordinate", cu, sub(r"^M02\*$", "D01*\nM02*")),
        ("an unknown command", cu, sub(r"^%MOMM\*%$", "%MOMM*%\n%LNTOP*%")),
        ("text outside a block", cu, sub(r"^M02\*$", "junk\nM02*")),
        ("a flash after M02", cu, lambda t: t + "X0Y0D03*\n"),
        ("text after M02", cu, lambda t: t + "junk\n"),
        ("NPTH in inches", npth, sub(r"^METRIC$", "INCH")),
        ("NPTH in another format", npth, sub(r"^FMAT,2$", "FMAT,1")),
        ("NPTH without a decimal point", npth, sub(r"^X(\d+)\.(\d+)Y(\d+)\.(\d+)$", r"X\1\2Y\3\4")),
        ("NPTH with an unknown line", npth, sub(r"^G05$", "G05\nG93")),
        ("NPTH with a hit before a tool", npth, sub(r"^G05$", "G05\nX1.000Y1.000")),
        ("NPTH with a tool twice", npth, sub(r"^(T1C[\d.]+)$", r"\1\n\1")),
        ("NPTH with a tool size without a decimal point", npth, sub(r"^T1C[\d.]+$", "T1C1")),
        ("NPTH selecting a tool it does not define", npth, sub(r"^G05$", "G05\nT9")),
        ("NPTH without its % line", npth, sub(r"^%\n", "")),
        ("NPTH with G05 before G90", npth, sub(r"^G90\nG05$", "G05\nG90")),
        ("NPTH cut short", npth, sub(r"^M30\n", "")),
        ("NPTH with a comment before M48", npth, lambda t: "; a comment\n" + t)):
    with case({fname: edit}):
        print("RESULT", name, "raises" if read(fname) == "raises" else "reads")
with case({npth: comment_first}):
    print("RESULT NPTH with its FileFunction right after M48", "raises" if read(npth) == "raises" else "reads")
"""
    assert gen(made, code) == ["as made ['reads']", "FSLAX45Y45 everywhere ['raises']"] + [
        f"{name} raises" for name in (
            "Edge_Cuts in inches", "Edge_Cuts G03 for G01", "a G02 arc", "G75", "an aperture macro",
            "a polygon aperture", "a unit after the first coordinate", "FS twice", "MO twice",
            "an aperture's D code twice", "an aperture's D code under 10", "a circle aperture with a Y size",
            "a rectangle aperture without its X size", "an obround aperture without its X size",
            "a comment without the space after G04", "an aperture attribute",
            "D01 before G01", "a flash before an aperture is selected", "a D01 before an aperture is selected",
            "a G36 in a region", "a flash in a region", "Edge_Cuts without M02", "a region open at M02",
            "a coordinate without Y", "a D01 without a coordinate", "an unknown command", "text outside a block",
            "a flash after M02", "text after M02",
            "NPTH in inches", "NPTH in another format", "NPTH without a decimal point", "NPTH with an unknown line",
            "NPTH with a hit before a tool", "NPTH with a tool twice", "NPTH with a tool size without a decimal point",
            "NPTH selecting a tool it does not define", "NPTH without its % line", "NPTH with G05 before G90",
            "NPTH cut short", "NPTH with a comment before M48")] + [
        "NPTH with its FileFunction right after M48 reads"]


def test_check_py_fails_on_a_board_file_changed(made):
    # each check on made's files (0 problems), then on a copy with one file changed as the generator would not
    code = BOARD + r"""
def copper():
    return {ly: gerber_io.vector_copper(f) for ly, f in check.LAYERS.items()}
def rasters():
    return {ly: gerber_io.raster(f) for ly, f in check.LAYERS.items()}
def drills():
    return gerber_io.read_drill("avionics-PTH.drl"), gerber_io.read_drill("avionics-NPTH.drl")
def assembly(fit):
    parts, bad = check.assembly_files()
    return bad + fit(pads, parts)
checks = {
    "copper_nets": lambda: check.copper_nets(copper(), pads, segments, vias, drills()[0]),
    "file_functions": check.file_functions,
    "mount_keepout": lambda: check.mount_keepout(rasters()),
    "led_cutouts": lambda: check.led_cutouts(rasters()),
    "copper_model": lambda: check.copper_model(pads, segments, vias),
    "drill_model": lambda: check.drill_model(pads, vias),
    "holes_and_paste": lambda: check.holes_and_paste(pads, vias, *drills()),
    "silk_clear": lambda: check.silk_clear(*drills()),
    "edge_cuts": check.edge_cuts,
    "silk_edge": check.silk_edge,
    "cathode_bars": lambda: check.cathode_bars(pads),
    "pin1_marks": lambda: check.pin1_marks(pads),
    "assembly_files": check.assembly_files,
    "footprints": lambda: assembly(check.footprints),
    "tht_footprints": lambda: assembly(check.tht_footprints),
}
with case():
    print("RESULT as made", {name: run(f) for name, f in checks.items()})
fp = [p for p in pads if "F" in p.layers and p.net]
a, b = min(((a, b) for i, a in enumerate(fp) for b in fp[i + 1:] if a.net != b.net),
           key=lambda ab: (ab[0].x - ab[1].x) ** 2 + (ab[0].y - ab[1].y) ** 2)
(mx, my), cut, pad = board.MOUNTS[0], board.CUTOUTS[0], by["DK00.A"]
def cutout_moved(txt):                      # the second contour (the first LED cutout) 0.3 mm along x
    lines = txt.split("\n")
    starts = [i for i, ln in enumerate(lines) if ln.endswith("D02*")]
    for i in range(starts[1], starts[2]):
        lines[i] = re.sub(r"^X(\d+)", lambda m: f"X{int(m.group(1)) + 300000}", lines[i])
    return "\n".join(lines)
for name, edits, check_name in (
        (f"F_Cu trace from {a.name} ({a.net}) to {b.name} ({b.net})",
         {"avionics-F_Cu.gtl": drawn(xy(a.x, a.y) + "D02*", xy(b.x, b.y) + "D01*")}, "copper_nets"),
        ("F_Mask's polarity Positive", {"avionics-F_Mask.gts": sub("Negative", "Positive")}, "file_functions"),
        ("a Gerber changed, not the zip", {"avionics-F_Cu.gtl": sub(r"^G01\*$", "G04 changed*\nG01*")},
         "file_functions"),
        ("F_Cu dot 2 mm from a mounting hole", {"avionics-F_Cu.gtl": drawn(xy(mx + 2.0, my) + "D03*")},
         "mount_keepout"),
        ("In1 dot in an LED cutout", {"avionics-In1_Cu.g2": drawn(xy(cut[0], cut[1]) + "D03*")}, "led_cutouts"),
        ("a B_Cu pad flash deleted", {"avionics-B_Cu.gbl": sub(r"^X\d+Y\d+D03\*\n", "")}, "copper_model"),
        ("a mounting hole 0.5 mm off", {"avionics-NPTH.drl": sub(r"^X3\.500Y56\.500$", "X4.000Y56.500")},
         "drill_model"),
        ("a paste opening deleted", {"avionics-B_Paste.gbp": sub(r"^X\d+Y\d+D03\*\n", "")}, "holes_and_paste"),
        (f"B legend across {pad.name}", {"avionics-B_Silkscreen.gbo": drawn(
            xy(pad.x - 0.2, pad.y) + "D02*", xy(pad.x + 0.2, pad.y) + "D01*")}, "silk_clear"),
        ("an LED cutout 0.3 mm off", {"avionics-Edge_Cuts.gko": cutout_moved}, "edge_cuts"),
        ("F legend past the board edge", {"avionics-F_Silkscreen.gto": drawn(
            xy(-0.2, 30.0) + "D02*", xy(1.0, 30.0) + "D01*")}, "silk_edge"),
        ("a cathode bar deleted", {"avionics-B_Silkscreen.gbo": lambda t: t.replace(
            next(m.group() for m in re.finditer(r"X(\d+)Y(\d+)D02\*\nX\d+Y\d+D01\*\n", t)
                 if abs(int(m.group(1)) / 1e6 - by["DK00.K"].x) < 1.5
                 and abs(board.H - int(m.group(2)) / 1e6 - by["DK00.K"].y) < 1.5), "")}, "cathode_bars"),
        ("the pin 1 dots deleted", {"avionics-B_Silkscreen.gbo": sub(r"^X\d+Y\d+D03\*\n", "", 0)}, "pin1_marks"),
        ("CPL Layer in lowercase", {"avionics-panel-rev1-CPL.csv": sub(",Bottom,", ",bottom,")}, "assembly_files"),
        ("DK00 turned 180", {f"avionics-panel-rev1-CPL{v}.csv": sub(r"^(DK00,.*,Bottom,)0$", r"\g<1>180")
                             for v in ("", "-full")}, "footprints"),
        ("K00 turned 90", {"avionics-panel-rev1-CPL-full.csv": sub(r"^(K00,.*,Top,)0$", r"\g<1>90")},
         "tht_footprints"),
        ("ENC_FMS turned 180", {"avionics-panel-rev1-CPL-full.csv": sub(r"^(ENC_FMS,.*,Top,)0$", r"\g<1>180")},
         "tht_footprints")):
    with case(edits):
        print("RESULT", name, check_name, run(checks[check_name]) > 0)
"""
    got = gen(made, code)
    names = ("copper_nets", "file_functions", "mount_keepout", "led_cutouts", "copper_model", "drill_model",
             "holes_and_paste", "silk_clear", "edge_cuts", "silk_edge", "cathode_bars", "pin1_marks",
             "assembly_files", "footprints", "tht_footprints")
    assert got[0] == "as made " + str(dict.fromkeys(names, 0))
    assert len(got) == 18 and all(ln.endswith(" True") for ln in got[1:]), got


def test_the_encoder_lug_slots_fit_jlcs_footprint_only_with_their_allowance(made):
    # the lug slots are drawn 1.5 x 3.0, 0.4 mm longer than JLC's own footprint of C19270361, for JLCPCB's 2:1 slot
    # rule: check.tht_footprints passes on the board as shipped, and fails without TH_SLOT_EXTRA or with the slots
    # drawn as JLC's 1.5 x 2.6 under it
    code = BOARD + r"""
sheet, slot0, extra0 = check.TH_SHEET["C19270361"], board.SLOT, check.TH_SLOT_EXTRA["C19270361"]
def footprints(slot, length, extra):
    board.SLOT, check.TH_SLOT_EXTRA["C19270361"] = slot, extra
    check.TH_SHEET["C19270361"] = (sheet[0], (sheet[1][0], length))
    parts, bad = check.assembly_files()             # CPL-full.csv: the slots' length leaves it as made
    return run(check.tht_footprints, board.build(), parts) + bad
with case():
    print("RESULT as shipped", slot0, extra0, footprints(slot0, sheet[1][1], extra0))
    print("RESULT without TH_SLOT_EXTRA", footprints(slot0, sheet[1][1], 0.0))
    print("RESULT JLC's 2.6 under it", footprints((1.5, 2.6), (2.6, 2.7), extra0))
"""
    assert gen(made, code) == ["as shipped (1.5, 3.0) 0.4 0", "without TH_SLOT_EXTRA 3", "JLC's 2.6 under it 3"]


def test_check_py_fails_on_a_part_changed_in_the_model(made):
    # the checks that take board.py's pads: a cathode pad renamed or on the other side, a decoupling capacitor
    # gone, a fiducial gone or at the edge
    code = BOARD + r"""
import copy
def changed(change):
    ps = copy.deepcopy(pads)
    change({p.name: p for p in ps}, ps)
    return ps
def rename(old, new):
    def change(by, ps):
        by[old].name = new
    return change
def swap(by, _ps):
    by["DK00.K"].name, by["DK00.A"].name = "DK00.A", "DK00.K"
def every_k(by, _ps):
    for p in by.values():
        if p.name.endswith(".K"):
            p.name = p.name[:-1] + "C"
def drop(prefix):
    def change(_by, ps):
        ps[:] = [p for p in ps if not p.name.startswith(prefix)]
    return change
def to_edge(by, _ps):
    by["FID.1"].x = 2.0
def stray(by, ps):                          # DK00's pads again as XX00's, a part board.PARTS does not have
    for end in ("K", "A"):
        p = copy.copy(by["DK00." + end]); p.name = "XX00." + end; ps.append(p)
for name, f, change in (
        ("as built", check.cathode_bars, None), ("DK00's K and A swapped", check.cathode_bars, swap),
        ("DK00.K named DK00.C", check.cathode_bars, rename("DK00.K", "DK00.C")),
        ("every K pad named C", check.cathode_bars, every_k),
        ("a K pad on a part not in PARTS", check.cathode_bars, stray),
        ("as built", lambda ps: check.decoupling(ps, segments, vias), None),
        ("C_IO1 gone", lambda ps: check.decoupling(ps, segments, vias), drop("C_IO1.")),
        ("as built", check.fiducials, None), ("FID.1 gone", check.fiducials, drop("FID.1")),
        ("FID.1 at the edge", check.fiducials, to_edge)):
    with case():
        print("RESULT", name, run(f, changed(change) if change else pads))
"""
    assert gen(made, code) == ["as built 0", "DK00's K and A swapped 1", "DK00.K named DK00.C 1",
                               "every K pad named C 38", "a K pad on a part not in PARTS 1", "as built 0",
                               "C_IO1 gone 2", "as built 0", "FID.1 gone 1", "FID.1 at the edge 1"]


def test_precheck_py_fails_on_a_part_placed_too_close():
    # precheck.py as a script, board.build() and board.bodies() changed under it: a pad on another net's pad, a
    # pad at the board edge, a body on another body, a pad in a mounting hole's keep-out. Its three counts:
    # placement (clearance and edge), bodies, keep-outs
    code = r"""
import contextlib, io, re, runpy, board
build, bodies = board.build, board.bodies
def moved(name, x, y):
    def f():
        pads = build()
        p = next(p for p in pads if p.name == name)
        q = {p.name: p for p in pads}
        p.x, p.y = x(q), y(q)
        return pads
    return f
def body_on_body():
    out = bodies()
    out["C_1V1"] = out["C_1V0"]
    return out
mx, my = board.MOUNTS[4]
for name, b, bs in (
        ("as built", build, bodies),
        ("R_UNIT.1 on R_UNIT.2", moved("R_UNIT.1", lambda q: q["R_UNIT.2"].x, lambda q: q["R_UNIT.2"].y + 0.3), bodies),
        ("FID.1 at the board edge", moved("FID.1", lambda q: 0.3, lambda q: 30.0), bodies),
        ("C_1V1 on C_1V0", build, body_on_body),
        ("FID.1 2 mm from a mounting hole", moved("FID.1", lambda q: mx + 2.0, lambda q: my), bodies)):
    board.build, board.bodies = b, bs
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        try:
            runpy.run_path("precheck.py", run_name="precheck")
        except SystemExit as e:
            status = e.code
    counts = [int(re.search(pat, out.getvalue()).group(1)) for pat in
              (r"placement problems: (\d+)", r"bodies: .*; (\d+) problems", r"mount keep-outs: .*; (\d+) problems")]
    print("RESULT", name, status, [n > 0 for n in counts])
"""
    assert gen("pcb", code) == ["as built 0 [False, False, False]", "R_UNIT.1 on R_UNIT.2 1 [True, False, False]",
                                "FID.1 at the board edge 1 [True, False, False]",
                                "C_1V1 on C_1V0 1 [False, True, False]",
                                "FID.1 2 mm from a mounting hole 1 [False, False, True]"]


def test_check_fit_py_fails_on_a_cap_legend_or_a_single_cap_off(tmp_path):
    # the cap zips as ordered (production/), copied: they pass; each case changes a copy and must fail
    for f in os.listdir(os.path.join(ROOT, "production")):
        if re.fullmatch(r"avionics-panel-rev1-caps-(single-)?[A-D]\.zip", f):
            shutil.copy(os.path.join(ROOT, "production", f), tmp_path / f)
    code = f"SRC = {str(tmp_path)!r}\n" + """
import io, os, re, shutil, tempfile, zipfile
from pathlib import Path
import numpy as np
from PIL import Image
import check_fit as C
SRC = Path(SRC)
def rezip(path, member, edit):
    with zipfile.ZipFile(path) as z:
        files = {i.filename: z.read(i) for i in z.infolist()}
    files[member] = edit(files[member])
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for n, data in files.items():
            z.writestr(n, data)
def png(arr):
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, "PNG")
    return buf.getvalue()
def caps(s):
    return f"avionics-panel-rev1-caps-{s}"
def blank_cell(d):                                 # cap 5's cell black, in every set's texture
    tex = np.array(C.cap_texture())
    tex[0:512, 4 * 512:5 * 512] = tex[-1, -1]
    data = png(tex)
    for s in C.S.CAP_SETS:
        rezip(d / f"{caps(s)}.zip", f"{caps(s)}.png", lambda _b: data)
def pixel_in_c(d):                                 # set C's texture one pixel off
    tex = np.array(C.cap_texture())
    tex[-1, -1] = 255
    rezip(d / f"{caps('C')}.zip", f"{caps('C')}.png", lambda _b: png(tex))
def single(s, k, edit):
    # set s's single cap k with one of its files changed, edit (its suffix, a function of its bytes and k), or with
    # its files changed together, edit a function of the dict of them
    def change(d):
        def inner(data):
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                files = {i.filename: z.read(i) for i in z.infolist()}
            if callable(edit):
                edit(files)
            else:
                name = next(n for n in files if n.endswith(edit[0]))
                files[name] = edit[1](files[name], k)
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w") as z:
                for n, b in files.items():
                    z.writestr(n, b)
            return buf.getvalue()
        with zipfile.ZipFile(d / f"{caps('single-' + s)}.zip") as z:
            name = z.namelist()[k]
        rezip(d / f"{caps('single-' + s)}.zip", name, inner)
    return change
def vertex_moved(b, _k):                           # the first vertex 0.3 um along x, past cap_singles' 0.2 um
    lines = b.decode().split("\\n")
    i = next(i for i, ln in enumerate(lines) if ln.startswith("v "))
    x, y, z = map(float, lines[i].split()[1:])
    lines[i] = f"v {x + 0.0003:.4f} {y:.4f} {z:.4f}"
    return "\\n".join(lines).encode()
def next_cell(_b, k):                              # the tile of the next cap
    return png(np.ascontiguousarray(C.cap_cell(k + 1)))
def uv_eighth(b, _k):                              # every UV an eighth: the tile's UVs as if on the texture
    lines = b.decode().split("\\n")
    for i, ln in enumerate(lines):
        if ln.startswith("vt "):
            u, v = map(float, ln.split()[1:])
            lines[i] = f"vt {u / 8:.6f} {v / 8:.6f}"
    return "\\n".join(lines).encode()
def uv_nudged(b, _k):                              # the top UVs 2e-4 off (the sides' last vt kept): 2.5e-5 on
    lines = b.decode().split("\\n")             # the texture
    vts = [i for i, ln in enumerate(lines) if ln.startswith("vt ")][:-1]
    for i in vts:
        u, v = map(float, lines[i].split()[1:])
        lines[i] = f"vt {u + 2e-4:.6f} {v:.6f}"
    return "\\n".join(lines).encode()
def missing_png(b, _k):                            # the MTL's texture another file
    return re.sub(r"map_Kd \\S+", "map_Kd missing.png", b.decode()).encode()
def stray_file(files):                             # a file more in the cap's zip
    files["readme.txt"] = b"stray"
def side_on_other_colour(files):                   # the sides' UV (the OBJ's last vt) on a pixel of another colour
    obj, tile = (next(n for n in files if n.endswith(ext)) for ext in (".obj", ".png"))
    tile = np.asarray(Image.open(io.BytesIO(files[tile])).convert("RGB"))
    lines = files[obj].decode().split("\\n")
    i = max(i for i, ln in enumerate(lines) if ln.startswith("vt "))
    u, v = map(float, lines[i].split()[1:])
    ys, xs = np.nonzero((tile != tile[int((1 - v) * C.CELL), int(u * C.CELL)]).any(axis=2))
    lines[i] = f"vt {(xs[0] + 0.5) / C.CELL:.6f} {1 - (ys[0] + 0.5) / C.CELL:.6f}"
    files[obj] = "\\n".join(lines).encode()
def other_mtllib(b, _k):                           # the OBJ on another MTL
    return re.sub(r"^mtllib \\S+", "mtllib caps.mtl", b.decode(), flags=re.M).encode()
def other_kd(b, _k):                               # the MTL's colour another
    return re.sub(r"^Kd .*", "Kd 0.5 0.5 0.5", b.decode(), flags=re.M).encode()
def no_label_5():                                  # cap 5 without a legend in stack.KEY_LEGENDS, its cell inked
    legends = C.S.KEY_LEGENDS
    flat = [cap for row in legends for cap in row]
    C.S.KEY_LEGENDS = [[("", "")] if k == 4 else [cap] for k, cap in enumerate(flat)]
    try:
        return C.legend_strokes()
    finally:
        C.S.KEY_LEGENDS = legends
def one_cap_less(d):
    path = d / f"{caps('single-D')}.zip"
    with zipfile.ZipFile(path) as z:
        files = {i.filename: z.read(i) for i in z.infolist()}
    with zipfile.ZipFile(path, "w") as z:
        for n, b in list(files.items())[:-1]:
            z.writestr(n, b)
for name, change, check in (
        ("as ordered", None, None),
        ("cap 5's legend missing", blank_cell, C.legend_strokes),
        ("set C's texture off", pixel_in_c, C.legend_strokes),
        ("a single cap B 3 moved", single("B", 2, (".obj", vertex_moved)), C.cap_singles),
        ("a single cap A 7 with cap 8's tile", single("A", 6, (".png", next_cell)), C.cap_singles),
        ("a single cap A 1 with its UVs an eighth", single("A", 0, (".obj", uv_eighth)), C.cap_singles),
        ("a single cap A 2 with its UVs nudged", single("A", 1, (".obj", uv_nudged)), C.cap_singles),
        ("a single cap B 1 on missing.png", single("B", 0, (".mtl", missing_png)), C.cap_singles),
        ("cap 5 without a legend, its cell inked", None, no_label_5),
        ("a single cap C 5 with a stray file", single("C", 4, stray_file), C.cap_singles),
        ("a single cap D 2 with its sides on another colour", single("D", 1, side_on_other_colour), C.cap_singles),
        ("a single cap A 3 on another MTL", single("A", 2, (".obj", other_mtllib)), C.cap_singles),
        ("a single cap B 4 with another colour in its MTL", single("B", 3, (".mtl", other_kd)), C.cap_singles),
        ("single-D one cap short", one_cap_less, C.cap_singles)):
    d = Path(tempfile.mkdtemp())
    for f in os.listdir(SRC):
        shutil.copy(SRC / f, d / f)
    C.HERE = SRC
    C.cap_texture.cache_clear(); C.set_cap_faces.cache_clear()
    if change:
        change(d)
    C.HERE = d
    C.cap_texture.cache_clear(); C.set_cap_faces.cache_clear()
    try:
        got = (C.cap_singles(), C.legend_strokes()[1]) if check is None else check()
        print("RESULT", name, got)
    except SystemExit as e:
        print("RESULT", name, "fails:", str(e).replace(str(d) + "/", ""))
"""
    got = gen("mech", code)
    assert got[:-1] == [
        "as ordered (112, 'NAV ⇆')",
        "cap 5's legend missing fails: check_fit.py: cap 5 ('COM 1') has no legend in its cell of the texture",
        "set C's texture off fails: check_fit.py: caps-C.zip's texture is not caps-A.zip's",
        "a single cap B 3 moved fails: check_fit.py: cap-B-03-HDG.obj is not cap 3 of caps-B.zip",
        "a single cap A 7 with cap 8's tile fails: check_fit.py: cap-A-07-COM-FLIP.png is not cap 7's cell of the "
        "texture",
        "a single cap A 1 with its UVs an eighth fails: check_fit.py: cap-A-01-AP.obj's UVs are not those of cap 1 "
        "of caps-A.zip",
        "a single cap A 2 with its UVs nudged fails: check_fit.py: cap-A-02-ALT.obj's UVs are not those of cap 2 of "
        "caps-A.zip",
        "a single cap B 1 on missing.png fails: check_fit.py: cap-B-01-AP.mtl is not caps-B.zip's material on "
        "cap-B-01-AP.png",
        "cap 5 without a legend, its cell inked fails: check_fit.py: cap 5 ('') has ink in its cell of the texture",
        "a single cap C 5 with a stray file fails: check_fit.py: cap-C-05-COM-1.zip holds ['cap-C-05-COM-1.obj', "
        "'cap-C-05-COM-1.mtl', 'cap-C-05-COM-1.png', 'readme.txt']",
        "a single cap D 2 with its sides on another colour fails: check_fit.py: cap-D-02-ALT.obj's UVs are not those "
        "of cap 2 of caps-D.zip",
        "a single cap A 3 on another MTL fails: check_fit.py: cap-A-03-HDG.mtl is not caps-A.zip's material on "
        "cap-A-03-HDG.png",
        "a single cap B 4 with another colour in its MTL fails: check_fit.py: cap-B-04-MIC-1.mtl is not caps-B.zip's "
        "material on cap-B-04-MIC-1.png"]
    assert got[-1].startswith("single-D one cap short fails: check_fit.py: avionics-panel-rev1-caps-single-D.zip "
                              "holds ['cap-D-01-AP.zip'")
    assert got[-1].endswith("'cap-D-27-CLR.zip'], not one zip per cap in order"), got[-1]


def test_check_fit_py_measures_a_light_hole_moved_and_a_wall_raised():
    # plate_measures() on the plate built with the SHIFT light hole 0.3 mm to the right (measured where board.py
    # has it), body_measures() on the mesh of the body as ordered (production/: mech/ may not have it yet, build.sh
    # runs the tests while it writes it) with its wall tops 0.2 mm higher: each reads its change and nothing else
    # there
    code = f"PROD = {os.path.join(ROOT, 'production')!r}" + '''
from pathlib import Path
import check_fit as C, make_plate_step as PS, board as B, stack as S
(lx, ly), g, c = B.LEDS["SHIFT"]
B.LEDS["SHIFT"] = ((lx + 0.3, ly), g, c)
plate, _ = PS.build()
B.LEDS["SHIFT"] = ((lx, ly), g, c)
pm = C.plate_measures(C.mesh_triangles(plate))
print("RESULT lights off", {k: round(v[0], 3) for k, v in pm["lights"].items()}, "CUT holes off",
      round(pm["cut"][0], 3))
C.HERE = Path(PROD)
tri = C.mesh_triangles(C.read_step("avionics-panel-rev1-body"))
tri[:, :, 1] *= -1                                  # to board y, as body_triangles()
top = S.PLATE_Z0 - S.WALL_GAP
tri[:, :, 2][tri[:, :, 2] > top - 1e-3] += 0.2
bm = C.body_measures(tri)
print("RESULT wall tops", [f"{v - top:.3f}" for v in bm["wall_top"]], "seats",
      [f"{abs(v - S.SEAT_Z):.3f}" for v in bm["seat_z"]])
'''
    assert gen("mech", code) == ["lights off {'SHIFT': 0.3, 'UNIT': 0.0, 'FREQ': 0.0} CUT holes off 0.3",
                                 "wall tops ['0.200', '0.200'] seats ['0.000', '0.000']"]


def test_the_read_backs_fail_on_a_written_file_changed(tmp_path):
    # the plate's STEP (make_plate_step.read_back) and DXF (make_plate_art.check_dxf) as ordered (production/: mech/
    # may not have them yet, build.sh runs the tests while it writes them) pass; each other case fails, with the
    # error of the check that should catch it. The STEP is read back against the plate built with the SHIFT light hole
    # 0.05 mm off: the same face count, volume and extent, only face_diff tells them apart
    code = f"PROD = {os.path.join(ROOT, 'production')!r}\nTMP = {str(tmp_path)!r}\n" + r'''
import contextlib, io, re, shutil
from pathlib import Path
import numpy as np
import check_fit as C, make_plate_art as PA, make_plate_step as PS, board as B
PROD, TMP = Path(PROD), Path(TMP)
def outcome(f):
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            f()
    except (RuntimeError, SystemExit, ValueError) as e:
        return f"fails: {type(e).__name__}"
    return "passes"
plate, _ = PS.build()
(lx, ly), g, c = B.LEDS["SHIFT"]
B.LEDS["SHIFT"] = ((lx + 0.05, ly), g, c)
moved, _ = PS.build()
B.LEDS["SHIFT"] = ((lx, ly), g, c)
for name, shape in (("STEP as ordered", plate), ("STEP with a light hole moved", moved)):
    print("RESULT", name, outcome(lambda: PS.read_back(shape, str(PROD / "avionics-panel-rev1-plate"))))
dxf = (PROD / "avionics-panel-rev1-plate.dxf").read_text()
def sub(pattern, repl):
    def edit(txt):
        new = re.sub(pattern, repl, txt, count=1, flags=re.M)
        assert new != txt, pattern
        return new
    return edit
END = "0\nENDSEC\n0\nEOF\n"
def polylines(txt):                                 # the DXF as its head and its POLYLINEs' texts, the end cut off
    head, *polys = txt.split("0\nPOLYLINE\n")
    assert polys[-1].endswith(END)
    return head, polys[:-1] + [polys[-1][:-len(END)]]
def last_layer_first(txt):                          # the last layer's polygons first, each layer's in their order
    head, polys = polylines(txt)
    last = polys[-1].split("\n")[1]
    moved = [p for p in polys if p.split("\n")[1] == last]
    return "0\nPOLYLINE\n".join([head, *moved, *(p for p in polys if p.split("\n")[1] != last)]) + END
def last_polygon_dropped(txt):
    head, polys = polylines(txt)
    return "0\nPOLYLINE\n".join([head, *polys[:-1]]) + END
for name, edit in (
        ("DXF as ordered", lambda t: t),
        ("DXF with its layers in another order", last_layer_first),
        ("DXF a polygon short", last_polygon_dropped),
        ("DXF with a vertex moved", sub(r"^10\n(\d+\.\d+)$", lambda m: f"10\n{float(m[1]) + 0.001:.4f}")),
        ("DXF with a bulge", sub(r"^(20\n\S+\n)(0\nVERTEX)$", r"\g<1>42\n1.0\n\2")),
        ("DXF with a Z", sub(r"^(20\n\S+\n)(0\nVERTEX)$", r"\g<1>30\n0.5\n\2")),
        ("DXF with a colour in a SEQEND", sub(r"^(0\nSEQEND\n8\n\S+\n)", r"\g<1>62\n1\n")),
        ("DXF with a VERTEX on another layer", sub(r"^(0\nVERTEX\n8\n)CUT$", r"\1LASER")),
        ("DXF with a SEQEND on another layer", sub(r"^(0\nSEQEND\n8\n)CUT$", r"\1LASER")),
        ("DXF with a POLYLINE before the SEQEND of the one before",
         sub(r"^0\nSEQEND\n8\n\S+\n(?=0\nPOLYLINE\n)", "")),
        ("DXF with a group before the first entity", sub(r"^(2\nENTITIES\n)", r"\g<1>5\n1F\n")),
        ("DXF with an open polyline", sub(r"^66\n1\n70\n1\n", "66\n1\n")),
        ("DXF with a POLYLINE without SEQEND", sub(r"^0\nSEQEND\n8\n\S+\n(0\nENDSEC\n0\nEOF\n)\Z", r"\1")),
        ("DXF with a LINE", sub(r"^(0\nENDSEC\n0\nEOF\n)\Z", r"0\nLINE\n8\nCUT\n\1")),
        ("DXF without EOF", sub(r"^0\nEOF\n\Z", "")),
        ("DXF cut short", sub(r"^0\nENDSEC\n0\nEOF\n\Z", ""))):
    (TMP / "plate.dxf").write_text(edit(dxf))
    print("RESULT", name, outcome(lambda: PA.check_dxf(str(TMP / "plate.dxf"))))
'''
    assert gen("mech", code) == [
        "STEP as ordered passes", "STEP with a light hole moved fails: RuntimeError",
        "DXF as ordered passes"] + [f"DXF {name} fails: SystemExit" for name in (
            "with its layers in another order", "a polygon short", "with a vertex moved")] + [
        f"DXF {name} fails: ValueError" for name in (
            "with a bulge", "with a Z", "with a colour in a SEQEND", "with a VERTEX on another layer",
            "with a SEQEND on another layer", "with a POLYLINE before the SEQEND of the one before",
            "with a group before the first entity", "with an open polyline",
            "with a POLYLINE without SEQEND", "with a LINE", "without EOF", "cut short")]


def test_face_diff_matches_faces_by_type_area_and_centroid_each_once():
    # occ_util.face_diff on solids given as their faces() rows (type, area, centroid x, y, z): a face of another
    # type, another area or another centroid is left over on both sides; a face twice in a and once in b, once
    code = """
import numpy as np
import occ_util as O
O.faces = lambda rows: np.array(rows, dtype=float).reshape(-1, 5)
f = (1, 10.0, 0.0, 0.0, 0.0)
for name, a, b in (("the same", [f], [f]), ("another type", [f], [(0, *f[1:])]),
                   ("another area", [f], [(1, 10.001, 0.0, 0.0, 0.0)]),
                   ("another centroid", [f], [(1, 10.0, 0.0, 0.001, 0.0)]),
                   ("another centroid in x", [f], [(1, 10.0, 0.001, 0.0, 0.0)]),
                   ("another centroid in z", [f], [(1, 10.0, 0.0, 0.0, 0.001)]), ("a face twice in a", [f, f], [f])):
    print("RESULT", name, [len(side) for side in O.face_diff(a, b)])
"""
    assert gen("mech", code) == ["the same [0, 0]", "another type [1, 1]", "another area [1, 1]",
                                 "another centroid [1, 1]", "another centroid in x [1, 1]",
                                 "another centroid in z [1, 1]", "a face twice in a [1, 0]"]
