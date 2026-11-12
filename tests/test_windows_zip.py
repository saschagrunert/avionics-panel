"""The simulator's zip for Windows (windows/make_zip.py), built from a stand-in for Python's embeddable package:
its layout, the ._pth line that makes the repository's packages importable, Windows' line ends, the hash check,
and that the simulator runs from the unpacked tree alone. The real package and Windows itself are tested on
Windows."""
import hashlib
import io
import shutil
import subprocess
import sys
import zipfile

import pytest

from conftest import load

make_zip = load("_make_zip", "windows/make_zip.py")
TOP = make_zip.TOP
if shutil.which("git") is None or subprocess.run(["git", "rev-parse", "HEAD"], cwd=make_zip.ROOT,
                                                 capture_output=True).returncode:
    pytest.skip("not a git checkout: the zip takes the files git tracks", allow_module_level=True)
PTH = b"python314.zip\r\n.\r\n\r\n# Uncomment to run site.main() automatically\r\n#import site\r\n"   # 3.14.10's


def embeddable():
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as z:
        z.writestr("python.exe", b"MZ")
        z.writestr("python314._pth", PTH)
    return out.getvalue()


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    path = tmp_path_factory.mktemp("zip") / "sim.zip"
    make_zip.build(embeddable(), path)
    return path


def test_the_layout(built):
    with zipfile.ZipFile(built) as z:
        names = set(z.namelist())
        assert {f"{TOP}/{n}" for n in ("start.bat", "vjoy-setup.bat", "README.txt", "LICENSE", "python/python.exe",
                                       "firmware/boot.py", "firmware/code.py", "firmware/BUTTONS.md",
                                       "sim/vjoy.py", "sim/page.py", "viewer/index.html")} <= names
        assert all(n.startswith(f"{TOP}/") for n in names)
        assert not [n for n in names if "/test_" in n or "__pycache__" in n]
        assert z.read(f"{TOP}/python/python314._pth").split(b"\r\n")[:3] == [b"python314.zip", b".", b".."]
        for name in make_zip.WINDOWS:
            text = z.read(f"{TOP}/{name}")
            assert text.count(b"\n") == text.count(b"\r\n") > 0


def test_the_same_commit_builds_the_same_zip(built, tmp_path):
    make_zip.build(embeddable(), tmp_path / "again.zip")
    assert (tmp_path / "again.zip").read_bytes() == built.read_bytes()


def test_a_package_with_another_hash_is_refused(tmp_path):
    path = tmp_path / "python.zip"
    path.write_bytes(embeddable())
    assert make_zip.fetch(path, hashlib.sha256(embeddable()).hexdigest()) == embeddable()
    with pytest.raises(ValueError, match="SHA-256"):
        make_zip.fetch(path)


def test_the_simulator_runs_from_the_unpacked_zip(built, tmp_path):
    # with only the zip's folder on sys.path, as the ._pth gives it: the page finds its viewer, the panel runs
    with zipfile.ZipFile(built) as z:
        z.extractall(tmp_path)
    code = ("import sys; sys.path.insert(0, sys.argv[1]); import sim.page, sim.vjoy; from sim import Sim; "
            "sim.page.inputs(); s = Sim(); s.tap('AP'); print(s.presses(1), sim.page.__file__)")
    out = subprocess.run([sys.executable, "-I", "-c", code, str(tmp_path / TOP)], cwd=tmp_path, check=True,
                         capture_output=True, text=True).stdout
    assert out.splitlines()[-1] == f"['AP'] {tmp_path / TOP / 'sim' / 'page.py'}"
