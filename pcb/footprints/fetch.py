"""Download the JLCPCB / EasyEDA library footprint of every bottom-side (assembled) part into <LCSC>.json.

These are the footprints JLCPCB places the parts by (its placement preview draws them), so check.py fits each
one onto our pads, offline, from the files written here. Run it (needs the network) after adding a part type:
    cd pcb && python3 footprints/fetch.py
Each file keeps the pads only: number, centre x / y, size x / y in mm, top view, y down, from the
footprint's origin (the point JLCPCB puts on the CPL position).
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import board as B  # noqa: E402

URL = "https://easyeda.com/api/products/{}/components?version=6.4.19.5"
MIL10 = 0.254                       # EasyEDA units: 10 mil


def pads_of(data):
    """(number, x, y, w, h) of every pad of an EasyEDA footprint, mm, from its origin."""
    ds = data["packageDetail"]["dataStr"]
    ox, oy = float(ds["head"]["x"]), float(ds["head"]["y"])
    out = []
    for shape in ds["shape"]:
        if not shape.startswith("PAD~"):
            continue
        f = shape.split("~")
        kind, x, y, w, h, num, rot = f[1], float(f[2]), float(f[3]), float(f[4]), float(f[5]), f[8], f[11]
        if kind in ("RECT", "POLYGON"):             # the outline points give the size whatever the rotation
            pts = [float(v) for v in f[10].split()]
            xs, ys = pts[0::2], pts[1::2]
            w, h = max(xs) - min(xs), max(ys) - min(ys)
        elif rot and round(float(rot)) % 180 == 90:
            w, h = h, w
        out.append((num, round((x - ox) * MIL10, 3), round((y - oy) * MIL10, 3), round(w * MIL10, 3),
                    round(h * MIL10, 3)))
    return sorted(out, key=lambda p: (len(p[0]), p[0]))


def retry(error):
    """Worth another try: too many requests (429), a server error (5xx) or the network (no connection, a
    timeout, a reset). Any other HTTP error (404, 403) is the answer for this part and comes back the same."""
    if isinstance(error, urllib.error.HTTPError):       # a URLError too: check it first
        return error.code == 429 or error.code >= 500
    return True


def download(url):
    req = urllib.request.Request(url, headers={"User-Agent": "curl/8"})    # the default agent gets a 403
    for attempt in range(5):                    # the API refuses requests in quick succession for a while
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            if attempt == 4 or not retry(e):
                raise
            time.sleep(10 * (attempt + 1))


def main():
    """With a directory argument, reads the API answers saved there as <LCSC>.json instead of downloading."""
    B.build()
    here = os.path.dirname(os.path.abspath(__file__))
    for lcsc in sorted({p[2] for p in B.PARTS if p[6] == "bottom"}):
        url, answer = URL.format(lcsc), "no footprint in the answer"
        if len(sys.argv) > 1:
            with open(os.path.join(sys.argv[1], f"{lcsc}.json")) as f:
                data = json.load(f)["result"]
        else:
            try:
                data = download(url)["result"]
            except urllib.error.HTTPError as e:
                data, answer = None, f"HTTP {e.code}"
            time.sleep(1)
        if not data or not data.get("packageDetail"):
            sys.exit(f"{lcsc}: EasyEDA returned no footprint for this part ({url.split('?')[0]}, {answer}); check "
                     "the LCSC number in board.py (check.py needs JLC's footprint of every bottom-side part)")
        ref = {
            "lcsc": lcsc,
            "title": data["title"],
            "package": data["packageDetail"]["title"],
            "source": f"JLCPCB / EasyEDA library footprint, {url.split('?')[0]}, fetched {date.today()}",
            "frame": "top view, mm, x right, y down, from the footprint origin; pads: number, x, y, size x, size y",
        }
        head = ",\n".join(f" {json.dumps(k)}: {json.dumps(v)}" for k, v in ref.items())
        found = pads_of(data)
        pads = ",\n".join(f"  {json.dumps(list(p))}" for p in found)
        with open(os.path.join(here, f"{lcsc}.json"), "w") as f:
            f.write(f'{{\n{head},\n "pads": [\n{pads}\n ]\n}}\n')
        print(lcsc, ref["title"], ref["package"], len(found), "pads")


if __name__ == "__main__":
    main()
