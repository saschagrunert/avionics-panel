"""The two checkers fail on known-bad cases: pcb/check.py on a via whose annular ring is under JLCPCB's minimum,
on drills under its smallest, on the exposed pad's paste windows bunched in one corner and on a bottom legend
that reads from the top; mech/check_fit.py on a row whose margin is below zero or not a number and on a tap
drill of another depth than the stack's. Both
need the generators' packages (numpy, shapely, OpenCascade), which the gen shell of nix/shells.nix has and the
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
    """the lines starting with RESULT that code prints, run by the gen shell's python3 in where (pcb or mech)"""
    r = subprocess.run(["nix-shell", os.path.join(ROOT, "nix", "shells.nix"), "-A", "gen", "--run",
                        "python3 -c " + shlex.quote(code)],
                       cwd=os.path.join(ROOT, where), capture_output=True, text=True, timeout=600)
    assert r.returncode == 0, r.stdout + r.stderr
    return [ln.split(None, 1)[1] for ln in r.stdout.splitlines() if ln.startswith("RESULT ")]


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
