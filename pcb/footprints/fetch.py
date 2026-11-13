"""Download the JLCPCB / EasyEDA library footprint of every part with an LCSC number into <LCSC>.json.

The bottom-side parts are placed by JLCPCB by these footprints (its placement preview draws them), so check.py
fits each one onto our pads, offline, from the files written here; the through-hole parts on the top are
soldered by hand or, in full assembly, placed by JLCPCB from the top-side CPL, and check.py fits their hole
patterns at that CPL position and rotation. Run it (needs the network) after adding a part type; it asks for
one part every PACE seconds, so a run takes about ten minutes:
    cd pcb && python3 footprints/fetch.py
Each file keeps the pads (number, centre x / y, size x / y in mm, top view, y down, from the footprint's
origin, the point JLCPCB puts on the CPL position) and the name JLC's symbol of the part gives each pad's pin:
check.py reads from it which pad of a diode or an LED is the cathode. Through-hole parts also keep their holes:
plated (number, x, y, drill, slot length or 0) and unplated (x, y, diameter).
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import board as B

URL = "https://easyeda.com/api/products/{}/components?version=6.4.19.5"
MIL10 = 0.254                       # EasyEDA units: 10 mil
# Seconds between two parts. The API blocks an address for some minutes after 15 to 19 requests at one every 10 s
# or faster, and its answer then is HTTP 403, which is final here (retry()). At one every 20 s the 28 parts of
# this board come through in one run.
PACE = 20


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


def pins_of(data):
    """(pad number, pin name) of every pin of an EasyEDA symbol: a pin is "P~..." in sections joined by "^^", the
    fourth holding its name and the fifth its number, the number of its pad in the footprint."""
    out = []
    for shape in data["dataStr"]["shape"]:
        if shape.startswith("P~"):
            sections = shape.split("^^")
            out.append((sections[4].split("~")[4], sections[3].split("~")[4]))
    return sorted(out, key=lambda p: (len(p[0]), p[0]))


def holes_of(data):
    """(plated, unplated) holes of an EasyEDA footprint, mm, from its origin: plated (number, x, y, drill, slot
    length or 0) from the multi-layer pads, unplated (x, y, diameter) from the HOLE shapes."""
    ds = data["packageDetail"]["dataStr"]
    ox, oy = float(ds["head"]["x"]), float(ds["head"]["y"])
    plated, unplated = [], []
    for shape in ds["shape"]:
        f = shape.split("~")
        if f[0] == "PAD" and f[6] == "11" and float(f[9] or 0) > 0:      # layer 11: all layers, a hole
            slot = float(f[13] or 0) * MIL10
            plated.append((f[8], round((float(f[2]) - ox) * MIL10, 3), round((float(f[3]) - oy) * MIL10, 3),
                           round(2 * float(f[9]) * MIL10, 3), round(slot, 3)))
        elif f[0] == "HOLE":
            unplated.append((round((float(f[1]) - ox) * MIL10, 3), round((float(f[2]) - oy) * MIL10, 3),
                             round(2 * float(f[3]) * MIL10, 3)))
    return sorted(plated, key=lambda p: (len(p[0]), p[0])), sorted(unplated)


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
    B.build()
    here = os.path.dirname(os.path.abspath(__file__))
    top = {p[2] for p in B.PARTS if p[6] == "top"}
    for k, lcsc in enumerate(sorted({p[2] for p in B.PARTS})):
        url, answer = URL.format(lcsc), "no footprint in the answer"
        if k:
            time.sleep(PACE)                        # between two parts only: none after the last or a failed one
        try:
            data = download(url)["result"]
        except urllib.error.HTTPError as e:
            data, answer = None, f"HTTP {e.code}"
        if not data or not data.get("packageDetail"):
            sys.exit(f"{lcsc}: EasyEDA returned no footprint for this part ({url.split('?')[0]}, {answer}); check "
                     "the LCSC number in board.py (check.py needs JLC's footprint of every part)")
        ref = {
            "lcsc": lcsc,
            "title": data["title"],
            "package": data["packageDetail"]["title"],
            "source": f"JLCPCB / EasyEDA library footprint, {url.split('?')[0]}, fetched {date.today()}",
            "frame": "top view, mm, x right, y down, from the footprint origin; pads: number, x, y, size x, size y; "
                     "pins: pad number, the pin's name in JLC's symbol",
        }
        found = pads_of(data)
        lists = {"pads": found, "pins": pins_of(data)}
        stray = sorted({n for n, _name in lists["pins"]} - {p[0] for p in found})
        if stray:
            sys.exit(f"{lcsc}: pins {stray} of JLC's symbol have no pad in its footprint ({url.split('?')[0]})")
        if lcsc in top:                             # through-hole part: its holes too
            lists["holes"], lists["npth"] = holes_of(data)
            ref["frame"] += "; holes: number, x, y, drill, slot length (0: round); npth: x, y, diameter"
        head = ",\n".join(f" {json.dumps(k)}: {json.dumps(v)}" for k, v in ref.items())
        body = ",\n".join(f' "{k}": [\n' + ",\n".join(f"  {json.dumps(list(p))}" for p in v) + "\n ]" if v
                           else f' "{k}": []' for k, v in lists.items())
        with open(os.path.join(here, f"{lcsc}.json"), "w") as f:
            f.write(f"{{\n{head},\n{body}\n}}\n")
        print(lcsc, ref["title"], ref["package"], len(found), "pads")


if __name__ == "__main__":
    main()
