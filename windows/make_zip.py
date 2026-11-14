"""Builds the simulator for Windows (docs/using/simulator.md): one zip with Python's embeddable package for Windows
(amd64), the firmware, the simulator, the viewer and the MobiFlight profiles, and start.bat, profile.bat,
vjoy-setup.bat, firewall.bat and README.txt from here. Python's standard library only; runs on Linux.

    python3 windows/make_zip.py [--python ZIP] [--out ZIP]

downloads the embeddable package from PYTHON_URL (--python takes a copy downloaded before), checks its SHA-256
and writes --out (dist/avionics-panel-sim-windows.zip). In the zip, under avionics-panel-sim/:

    start.bat  profile.bat  vjoy-setup.bat  firewall.bat  README.txt  LICENSE
    python/  firmware/  sim/  viewer/  mobiflight/

The package's ._pth file gets the line `..`, the zip's folder: there `python -m sim.page` finds sim/ (a ._pth
replaces sys.path, without the current directory). LICENSE, firmware/, sim/, viewer/ and mobiflight/ are the
files git tracks, without the firmware's tests and the script for the renders, so it needs a git checkout. They
go in as they are in the working tree, with any change that is not committed. The batch files and README.txt get
Windows' line ends. firmware/version.py gets the commit's date and short hash, as git archive writes them
(SUBST, .gitattributes), which the page, the firmware's console and the profiles show; with -dirty after the hash
when a file that goes in differs from the commit. Every file has the time of the last commit, so a clean checkout
of a commit builds the same files (the compressed bytes can differ with another zlib).
"""
import argparse
import hashlib
import io
import os
import re
import subprocess
import sys
import time
import urllib.request
import zipfile

PYTHON_VERSION = "3.14.10"
PYTHON_URL = f"https://www.python.org/ftp/python/{PYTHON_VERSION}/python-{PYTHON_VERSION}-embed-amd64.zip"
PYTHON_SHA256 = "90905e64a840557d8c1bc4f5b74db3d7ee85e3ffb217611cac1c7813acea4159"   # as python.org lists it
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TOP = "avionics-panel-sim"
OUT = os.path.join(ROOT, "dist", f"{TOP}-windows.zip")
SOURCES = ("LICENSE", "firmware", "sim", "viewer", "mobiflight")
LEFT_OUT = ("firmware/test_", "viewer/shots.py")   # of SOURCES: not for the simulator's users
WINDOWS = ("start.bat", "profile.bat", "vjoy-setup.bat", "firewall.bat", "README.txt")   # text with CRLF line ends
SUBST = ("firmware/version.py",)          # of SOURCES: git archive fills in their placeholders (export-subst)
PLACEHOLDER = re.compile(r"\$Format:([^$]*)\$")


def fetch(path=None, sha256=PYTHON_SHA256):
    """The embeddable package's bytes, from path or PYTHON_URL; ValueError for another hash"""
    if path:
        with open(path, "rb") as f:
            data = f.read()
    else:
        with urllib.request.urlopen(PYTHON_URL, timeout=60) as r:
            data = r.read()
    if (got := hashlib.sha256(data).hexdigest()) != sha256:
        raise ValueError(f"{path or PYTHON_URL}: SHA-256 {got}, not {sha256}")
    return data


def sources():
    """The repository's files of SOURCES that go in, by their path from the root: the ones git tracks that the
    working tree has"""
    names = subprocess.run(["git", "ls-files", "-z", "--cached", "--", *SOURCES], cwd=ROOT, capture_output=True,
                           check=True, text=True).stdout.split("\0")
    return sorted({n for n in names if n and os.path.isfile(os.path.join(ROOT, n)) and not n.startswith(LEFT_OUT)})


def log(fmt):
    """The last commit by git log's --format"""
    command = ["git", "-c", "core.abbrev=7", "log", "-1", f"--format={fmt}"]      # 7 characters in every clone
    return subprocess.run(command, cwd=ROOT, capture_output=True, check=True, text=True).stdout.rstrip("\n")


def changed():
    """True when a file that goes in differs from the last commit"""
    return bool(subprocess.run(["git", "diff", "--name-only", "HEAD", "--", *sources()], cwd=ROOT,
                               capture_output=True, check=True, text=True).stdout)


def stamp(fmt):
    """What a $Format:fmt$ placeholder in the zip becomes: the last commit in that format, -dirty after it when
    a file that goes in differs from the commit"""
    return log(fmt) + ("-dirty" if changed() else "")


def commit_time():
    return time.gmtime(int(log("%ct")))[:6]


def substitute(data):
    """A file's bytes with each $Format:...$ replaced by stamp(), as git archive does for a clean commit"""
    return PLACEHOLDER.sub(lambda m: stamp(m[1]), data.decode()).encode()


def build(embeddable, out):
    """Writes the zip to out from the embeddable package's bytes"""
    stamp = commit_time()

    def add(z, name, data):
        info = zipfile.ZipInfo(f"{TOP}/{name}", stamp)
        info.compress_type, info.external_attr = zipfile.ZIP_DEFLATED, 0o644 << 16
        z.writestr(info, data)

    with zipfile.ZipFile(io.BytesIO(embeddable)) as python:
        pth = [n for n in python.namelist() if n.endswith("._pth")]
        if len(pth) != 1:
            raise ValueError(f"the embeddable package has {len(pth)} ._pth files, not 1")
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        with zipfile.ZipFile(out, "w") as z:
            for name in WINDOWS:
                with open(os.path.join(HERE, name), encoding="utf-8") as f:
                    add(z, name, f.read().replace("\n", "\r\n").encode())
            for info in python.infolist():
                data = python.read(info)
                if info.filename == pth[0]:
                    lines = data.decode().splitlines()
                    lines.insert(lines.index(".") + 1, "..")
                    data = "\r\n".join(lines + [""]).encode()
                add(z, f"python/{info.filename}", data)
            for name in sources():
                with open(os.path.join(ROOT, name), "rb") as f:
                    data = f.read()
                add(z, name, substitute(data) if name in SUBST else data)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python3 windows/make_zip.py", description=__doc__.split("\n\n")[0])
    parser.add_argument("--python", metavar="ZIP", help=f"the embeddable package, downloaded ({PYTHON_URL})")
    parser.add_argument("--out", metavar="ZIP", default=OUT, help=f"the zip to write ({os.path.relpath(OUT)})")
    args = parser.parse_args(argv)
    try:
        build(fetch(args.python), args.out)
    except subprocess.CalledProcessError as e:
        sys.exit(f"make_zip.py: needs a git checkout: {e.stderr.strip() or e}")
    except (OSError, ValueError, subprocess.SubprocessError) as e:
        sys.exit(f"make_zip.py: {e}")
    print(f"{args.out}: {os.path.getsize(args.out) / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
