"""The files to order agree with each other (tests/production_check.py, which reads production/ alone, with no
module of the repository): the board's and the plate's frames, the mounting holes of the drill file with the
plate's tapped bosses and the body's screw holes, the keys of the CPL with the plate's key holes in its STEP and its
DXF, the DXF's outline with the STEP's extent, and the encoders, RANGE and the LED cutouts with the plate's other
through holes in its STEP and those with the DXF's round holes. Each of these nine comparisons fails on a copy with
one thing changed, and only the ones that read it fail, so each fails alone on one copy at least: the board outline
moved in Edge_Cuts or made taller (the body's frame comes from the board's height), the plate STEP off its frame, a
mounting hole moved in the drill file (alone, and with the body's screw hole), a tap drill as wide as its boss in
the plate STEP, a screw hole wider in the body STEP, a key moved in the CPL (alone, and with its key hole in the
DXF), a key hole moved or dropped in the DXF, the DXF's outline scaled, an LED cutout moved in Edge_Cuts, an
encoder's lug slots moved in the drill file, a round hole moved or dropped in the DXF; and the script's result is
fail on each copy. It needs OpenCascade for the STEP files, which the gen shell of nix/shells.nix has; it runs
there through nix-shell, and without nix-shell this test skips."""
import csv
import io
import math
import os
import re
import shlex
import shutil
import subprocess
import zipfile

import pytest

from conftest import ROOT

pytestmark = pytest.mark.skipif(shutil.which("nix-shell") is None,
                                reason="nix-shell missing: the check runs in the gen shell of nix/shells.nix")

PROD = os.path.join(ROOT, "production")
NAME = "avionics-panel-rev1"
FILES = [f"{NAME}-{f}" for f in ("gerbers.zip", "CPL-full.csv", "plate.dxf", "plate.step", "body.step")]


def gerber_edit(path, member, edit):
    """the zip at path with one member's text changed by edit (a function of the text)"""
    with zipfile.ZipFile(path) as z:
        files = {i.filename: z.read(i) for i in z.infolist()}
    files[member] = edit(files[member].decode()).encode()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for n, data in files.items():
            z.writestr(n, data)
    with open(path, "wb") as f:
        f.write(buf.getvalue())


def text_edit(path, edit):
    with open(path) as f:
        txt = f.read()
    with open(path, "w") as f:
        f.write(edit(txt))


def is_round(pts):
    """whether a polygon's points lie on a circle round the middle of its extent (production_check.py's test)"""
    xs, ys = [x for x, _ in pts], [y for _, y in pts]
    r = [math.dist(q, ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2)) for q in pts]
    return max(r) - min(r) < 1e-3


def dxf_polygon(pick, edit):
    """a DXF text edit: the first polygon of the CUT layer that pick(its index on CUT, its points) takes, its text
    changed by edit (a function of the text, or None to drop the polygon); the outline is CUT's first"""
    def change(txt):
        head, *polys = txt.split("0\nPOLYLINE\n")
        cut = [i for i, p in enumerate(polys) if p.startswith("8\nCUT\n")]
        i = next(i for k, i in enumerate(cut)
                 if pick(k, [(float(x), float(y)) for x, y in re.findall(r"^10\n(\S+)\n20\n(\S+)$", polys[i], re.M)]))
        polys[i:i + 1] = [] if edit is None else [edit(polys[i])]
        return "0\nPOLYLINE\n".join([head, *polys])
    return change


def dxf_moved(dx):
    """a polygon text edit: dx mm to the right"""
    return lambda poly: re.sub(r"(\n10\n)(-?[\d.]+)", lambda m: f"{m.group(1)}{float(m.group(2)) + dx:.4f}", poly)


def dxf_scaled(poly):
    """a polygon's text 0.1 % larger, from the plate's corner"""
    return re.sub(r"(\n[12]0\n)(-?[\d.]+)", lambda m: f"{m.group(1)}{float(m.group(2)) * 1.001:.4f}", poly)


def key_hole(k, pts):
    return k > 0 and not is_round(pts)


def round_hole(k, pts):
    return k > 0 and is_round(pts)


def moved_coord(line_re, dx):
    """a text edit: on the first line matching line_re, the number of its group 1 (an x) moved by dx"""
    def edit(txt):
        m = re.search(line_re, txt, re.M)
        assert m, line_re
        return txt[:m.start(1)] + f"{float(m.group(1)) + dx:.3f}" + txt[m.end(1):]
    return edit


def contour_moved(k, dx, dy, above=-1.0):
    """an Edge_Cuts edit: every vertex of its contour k (0 the board outline, 1 the first LED cutout) above y =
    above mm moved by dx, dy mm"""
    def move(m):
        x, y = int(m.group(1)), int(m.group(2))
        return f"X{x + round(dx * 1e6)}Y{y + round(dy * 1e6)}" if y > above * 1e6 else m.group()
    def edit(txt):
        lines = txt.split("\n")
        starts = [i for i, ln in enumerate(lines) if ln.endswith("D02*")]
        for i in range(starts[k], starts[k + 1]):
            lines[i] = re.sub(r"^X(-?\d+)Y(-?\d+)", move, lines[i])
        return "\n".join(lines)
    return edit


def step_radius(old, new):
    """a STEP text edit: its first cylinder of radius old (as the file writes it) of radius new"""
    def edit(txt):
        out = re.sub(rf"(CYLINDRICAL_SURFACE\('',#\d+,){re.escape(old)}\);", rf"\g<1>{new});", txt, count=1)
        assert out != txt, old
        return out
    return edit


def step_axes_moved(xy, dx):
    """a STEP text edit: the axis of every cylinder on the axis at xy moved dx mm along x (the body's: its extent,
    which the faces' bounds give, is not read)"""
    def edit(txt):
        ent = dict(re.findall(r"^#(\d+) = (.*);$", txt, re.M))
        moved = set()
        for v in ent.values():
            if m := re.fullmatch(r"CYLINDRICAL_SURFACE\('',#(\d+),[^)]+\)", v):
                p = re.fullmatch(r"AXIS2_PLACEMENT_3D\('',#(\d+),.*", ent[m[1]])[1]
                if tuple(float(c) for c in ent[p].split("(")[2].split(",")[:2]) == xy:
                    moved.add(p)
        assert moved, xy
        return re.sub(r"^#(\d+) = CARTESIAN_POINT\('',\(([^,]+),", lambda m: m.group() if m[1] not in moved else
                      f"#{m[1]} = CARTESIAN_POINT('',({float(m[2]) + dx!r},", txt, flags=re.M)
    return edit


def step_moved(txt):
    """the plate STEP with every point 0.1 mm along x, its placement's origin too: the plate 0.2 mm off its frame"""
    return re.sub(r"CARTESIAN_POINT\('',\(([^,]+),", lambda m: f"CARTESIAN_POINT('',({float(m[1]) + 0.1!r},", txt)


def slots_moved(txt):
    """the PTH drill file with one encoder's two lug slots 0.2 mm along x: the first two slots drilled with the
    1.5 mm tool (J1's take 0.6) that start at the same y, whatever their length"""
    sizes, tool, lugs = {}, None, []
    for m in re.finditer(r"^(?:T(\d+)C([\d.]+)|T(\d+)|X([\d.]+)Y([\d.]+)G85X([\d.]+)Y([\d.]+))$", txt, re.M):
        if m[1]:
            sizes[m[1]] = float(m[2])
        elif m[3]:
            tool = sizes[m[3]]
        elif tool == 1.5:
            lugs.append(m)
    pair = [m for m in lugs if m[5] == lugs[0][5]][:2]
    assert len(pair) == 2, pair
    for m in reversed(pair):
        txt = txt[:m.start()] + f"X{float(m[4]) + 0.2:.3f}Y{m[5]}G85X{float(m[6]) + 0.2:.3f}Y{m[7]}" + txt[m.end():]
    return txt


OVH = 2.5                       # the plate's overhang (stack.OVH)
with open(os.path.join(PROD, f"{NAME}-CPL-full.csv"), newline="") as f:     # K00 in the plate's x, y
    K00 = next((float(r["Mid X"].removesuffix("mm")) + OVH, float(r["Mid Y"].removesuffix("mm")) + OVH)
               for r in csv.DictReader(f) if r["Designator"] == "K00")


def k00_hole(_k, pts):
    """K00's key hole in the DXF"""
    xs, ys = [x for x, _ in pts], [y for _, y in pts]
    return math.dist(((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2), K00) < 0.01


# each broken copy: its files and how each changes, and the comparisons that must fail, each by a part of its line
# no other line has
NPTH, EDGE, PTH = (("gerbers.zip", f) for f in ("avionics-NPTH.drl", "avionics-Edge_Cuts.gko", "avionics-PTH.drl"))
MOUNT_0 = moved_coord(r"^X([\d.]+)Y56\.500$", 0.5)                 # the mount at 3.5, 56.5 0.5 mm along x
MUTANTS = {
    "board outline 0.1 mm": ([(EDGE, contour_moved(0, 0.0, 0.1))], ["frames:"]),
    "board outline 0.1 mm taller": ([(EDGE, contour_moved(0, 0.0, 0.1, 30.0))],
                                    ["frames:", "the body STEP's screw holes"]),   # the body's frame from the height
    "plate STEP 0.2 mm off its frame": ([("plate.step", step_moved)], [
        "frames:", "the plate STEP's bosses:", "the plate STEP's key holes", "the DXF CUT outline",
        "round through holes:", "the DXF CUT layer's, centre and radius"]),
    "mounting hole 0.5 mm": ([(NPTH, MOUNT_0)], ["the plate STEP's bosses:", "the body STEP's screw holes"]),
    "mounting hole 0.5 mm, the body's screw hole with it": (
        [(NPTH, MOUNT_0), ("body.step", step_axes_moved((3.5, -3.5), 0.5))], ["the plate STEP's bosses:"]),
    "tap drill as wide as its boss": ([("plate.step", step_radius("1.25", "2.75"))], ["bosses are tapped"]),
    "body screw hole wider": ([("body.step", step_radius("2.1", "2.2"))], ["the body STEP's screw holes"]),
    "key 0.2 mm in the CPL": ([("CPL-full.csv", moved_coord(r"^K00,([\d.]+)mm", 0.2))],
                              ["the plate STEP's key holes", "the DXF CUT layer's key holes"]),
    "key 0.2 mm in the CPL and the DXF": (
        [("CPL-full.csv", moved_coord(r"^K00,([\d.]+)mm", 0.2)), ("plate.dxf", dxf_polygon(k00_hole, dxf_moved(0.2)))],
        ["the plate STEP's key holes"]),
    "key hole 0.1 mm in the DXF": ([("plate.dxf", dxf_polygon(k00_hole, dxf_moved(0.1)))],
                                   ["the DXF CUT layer's key holes"]),
    "key hole dropped from the DXF": ([("plate.dxf", dxf_polygon(key_hole, None))], ["the DXF CUT layer's key holes"]),
    "DXF outline 0.1 % larger": ([("plate.dxf", dxf_polygon(lambda k, _pts: k == 0, dxf_scaled))],
                                 ["the DXF CUT outline"]),
    "LED cutout 0.3 mm": ([(EDGE, contour_moved(1, 0.3, 0.0))], ["round through holes:"]),
    "encoder slots 0.2 mm": ([(PTH, slots_moved)], ["round through holes:"]),
    "round hole 0.1 mm in the DXF": ([("plate.dxf", dxf_polygon(round_hole, dxf_moved(0.1)))],
                                     ["the DXF CUT layer's, centre and radius"]),
    "round hole dropped from the DXF": ([("plate.dxf", dxf_polygon(round_hole, None))],
                                        ["the DXF CUT layer's, centre and radius"]),
}


def test_production_files_agree_and_each_comparison_fails_on_its_change(tmp_path):
    folders = {"production": PROD}
    for name, (edits, _fails) in MUTANTS.items():
        d = tmp_path / re.sub(r"\W+", "-", name)
        d.mkdir()
        for f in FILES:
            shutil.copy(os.path.join(PROD, f), d / f)
        for fname, edit in edits:
            if isinstance(fname, tuple):
                gerber_edit(d / f"{NAME}-{fname[0]}", fname[1], edit)
            else:
                text_edit(d / f"{NAME}-{fname}", edit)
        folders[name] = str(d)
    r = subprocess.run(["nix-shell", os.path.join(ROOT, "nix", "shells.nix"), "-A", "gen", "--run",
                        "python3 " + " ".join(shlex.quote(p) for p in
                                              [os.path.join(ROOT, "tests", "production_check.py"),
                                               *folders.values()])],
                       cwd=tmp_path, capture_output=True, text=True, timeout=600)
    runs = dict(zip(folders, r.stdout.split("== ")[1:], strict=True))
    good = runs.pop("production")
    assert "RESULT" in good and "FAIL" not in good, good
    lines = [ln for ln in good.splitlines() if ln.startswith("OK  ")]
    assert len(lines) == 9 and all(sum(f in ln for ln in lines) == 1 for _e, fs in MUTANTS.values() for f in fs), good
    assert all(any(f in ln for _e, fs in MUTANTS.values() for f in fs) for ln in lines), good   # each one pinned
    for name, out in runs.items():
        failed = [ln for ln in out.splitlines() if ln.startswith("FAIL")]
        assert failed and all(any(f in ln for f in MUTANTS[name][1]) for ln in failed), (name, out)
        assert all(any(f in ln for ln in failed) for f in MUTANTS[name][1]), (name, out)
        assert out.rstrip().endswith(" fail"), (name, out)
    assert r.returncode == 1, r.stderr
