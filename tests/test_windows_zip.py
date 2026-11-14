"""The simulator's zip for Windows (windows/make_zip.py), built from a stand-in for Python's embeddable package:
its layout, the ._pth line that makes the repository's packages importable, Windows' line ends, the hash check,
the commit it names, and that the simulator and the profiles run from the unpacked tree alone. The real package
and Windows itself are tested on a Windows PC."""
import hashlib
import io
import json
import os
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
        assert {f"{TOP}/{n}" for n in ("start.bat", "profile.bat", "vjoy-setup.bat", "firewall.bat", "README.txt",
                                       "LICENSE", "python/python.exe", "firmware/boot.py", "firmware/code.py",
                                       "firmware/keys.py", "firmware/version.py", "firmware/BUTTONS.md",
                                       "firmware/KEYS.md", "sim/vjoy.py", "sim/sendinput.py", "sim/page.py",
                                       "viewer/index.html", "mobiflight/__main__.py", "mobiflight/profile.py",
                                       "mobiflight/families/g1000.py")} <= names
        assert all(n.startswith(f"{TOP}/") for n in names)
        assert not [n for n in names if "/test_" in n or "__pycache__" in n or n.endswith("shots.py")]
        assert z.read(f"{TOP}/python/python314._pth").split(b"\r\n")[:3] == [b"python314.zip", b".", b".."]
        for name in make_zip.WINDOWS:
            text = z.read(f"{TOP}/{name}")
            assert text.count(b"\n") == text.count(b"\r\n") > 0
        # start.bat passes its arguments on, as the docs use it: start.bat --host 0.0.0.0
        assert b"python\\python.exe -m sim.page --vjoy --open %*\r\n" in z.read(f"{TOP}/start.bat")
        # profile.bat too, to the zip's Python from any folder; without any it lists the profiles and parts
        bat = z.read(f"{TOP}/profile.bat").decode()
        assert '\r\n"%~dp0python\\python.exe" -m mobiflight %*\r\n' in bat
        usage = bat.index('if not "%~1"=="" goto run\r\n')
        assert usage < bat.index("-m mobiflight --list\r\n") < bat.index("pause\r\n", usage) < bat.index(":run\r\n")
        assert "--from guids.mfproj" in bat and "--unit1" in bat and "--family g1000" in bat
        # the usage it echoes holds nothing cmd reads as its own: no redirection, pipe, command separator or variable
        echoed = [line for line in bat.splitlines() if line.lstrip().startswith("echo")]
        assert len(echoed) > 10 and not [line for line in echoed if set(line) & set("<>|&%^")]
        # firewall.bat allows the zip's own python.exe, on private networks only, after the rules from before
        firewall = z.read(f"{TOP}/firewall.bat").decode()
        assert 'set "PYTHON=%~dp0python\\python.exe"' in firewall
        add = firewall.index("add rule")
        assert firewall.index("delete rule name=all program=") < add < firewall.index("profile=private")
        assert firewall.index('delete rule name="%RULE%"') < add          # its own, also for a folder moved since


def test_the_zips_python_is_the_one_the_tests_run_on():
    # the same minor version: the simulator is tested on the Python it ships with. nixpkgs moves the one of the
    # tests, PYTHON_VERSION (with PYTHON_SHA256 and PTH here) the zip's, by hand. The firmware shell
    # (nix/shells.nix) and CI's Windows job ask for it with REQUIRE_ZIP_PYTHON=1; elsewhere any Python may run
    # the tests.
    if not os.environ.get("REQUIRE_ZIP_PYTHON"):
        pytest.skip("REQUIRE_ZIP_PYTHON is not set (nix/shells.nix sets it)")
    assert make_zip.PYTHON_VERSION.split(".")[:2] == [str(n) for n in sys.version_info[:2]]
    assert PTH.startswith(b"python%d%d.zip" % sys.version_info[:2])


def test_the_same_commit_builds_the_same_zip(built, tmp_path):
    make_zip.build(embeddable(), tmp_path / "again.zip")
    assert (tmp_path / "again.zip").read_bytes() == built.read_bytes()


def test_the_zip_names_its_commit(built):
    # firmware/version.py gets the date and short hash of the last commit, as git archive writes them (a release's
    # source code), and every other file stays as it is
    stamp = make_zip.stamp("%cs, %h")                                  # the hash of 7 characters it pins
    with zipfile.ZipFile(built) as z:
        version = z.read(f"{TOP}/firmware/version.py").decode()
        with open(os.path.join(make_zip.ROOT, "firmware", "version.py"), encoding="utf-8", newline="") as f:
            assert version == f.read().replace('"$Format:%cs, %h$"', f'"{stamp}"')
        assert f'VERSION = "{stamp}"' in version.splitlines()   # CRLF in a Windows checkout
        for name in make_zip.sources():
            if name not in make_zip.SUBST:
                with open(os.path.join(make_zip.ROOT, name), "rb") as f:
                    assert z.read(f"{TOP}/{name}") == f.read(), name
    for name in make_zip.SUBST:              # git archive fills in the same files
        attr = subprocess.run(["git", "check-attr", "export-subst", "--", name], cwd=make_zip.ROOT,
                              capture_output=True, check=True, text=True).stdout
        assert attr == f"{name}: export-subst: set\n"


def test_files_not_committed_mark_the_stamp_dirty(monkeypatch):
    # the zip packs the working tree: a change not committed is not the commit the stamp names
    monkeypatch.setattr(make_zip, "changed", lambda: True)
    assert make_zip.substitute(b'V = "$Format:%cs, %h$"') == f'V = "{make_zip.log("%cs, %h")}-dirty"'.encode()


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
            "sim.page.inputs(); s = Sim(); s.tap('AP'); print(s.presses(1), sim.page.legend('g1000')[1]['AP'], "
            "sim.page.__file__); print(sim.page.version())")
    out = subprocess.run([sys.executable, "-I", "-c", code, str(tmp_path / TOP)], cwd=tmp_path, check=True,
                         capture_output=True, text=True).stdout
    assert out.splitlines()[-2:] == [f"['AP'] AP_MASTER {tmp_path / TOP / 'sim' / 'page.py'}",
                                     make_zip.stamp("%cs, %h")]
    assert f"Avionics Panel rev 1 ready ({make_zip.stamp('%cs, %h')})\n" in out       # the firmware's console


def test_the_profiles_are_made_from_the_unpacked_zip(built, tmp_path):
    # as profile.bat runs python -m mobiflight, from another folder: the profile goes there, named with the commit
    with zipfile.ZipFile(built) as z:
        z.extractall(tmp_path)
    out = tmp_path / "out"
    out.mkdir()
    code = ("import runpy, sys; sys.path.insert(0, sys.argv.pop(1)); "
            "runpy.run_module('mobiflight', run_name='__main__', alter_sys=True)")

    def mobiflight(*args):
        return subprocess.run([sys.executable, "-I", "-c", code, str(tmp_path / TOP), *args], cwd=out, check=True,
                              capture_output=True, text=True).stdout
    listed = mobiflight("--list")
    assert "--family: " in listed and " g1000 " in listed and "--unit1, --unit2: " in listed
    mobiflight("--family", "g1000", "-o", "x.mfproj")
    project = json.loads((out / "x.mfproj").read_text(encoding="utf-8"))
    assert project["Name"] == f"Avionics Panel: G1000 NXi ({make_zip.stamp('%cs, %h')})"
    assert os.listdir(out) == ["x.mfproj"]
