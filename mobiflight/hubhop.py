"""py -m mobiflight.hubhop [-o hubhop-presets.json]   (python3 -m mobiflight.hubhop on Linux and macOS)

Downloads HubHop's preset database, the one MobiFlight itself downloads (SimConnectMSFS/WasmModuleUpdater.cs),
and checks that it holds every preset the family tables name, once. The generator takes the presets' codes and
IDs from that file. HubHop's presets are HubHop's data, written by its authors: they are not part of this
repository and not covered by its licence.

The tables name a preset vendor.aircraft.label, as HubHop's editor lists it. The database holds the presets
for MSFS 2020 and 2024 alike; those made for MSFS 2024 only name it in their aircraft, as in "G1000 (2024)".
"""
import argparse
import http.client
import json
import sys
import urllib.request

from mobiflight import profile
from mobiflight.families import FAMILIES

SOURCE = "https://hubhop-api-mgtm.azure-api.net/api/v1/msfs2020/presets?type=json"
FILE = "hubhop-presets.json"
DOWNLOAD = "`py -m mobiflight.hubhop` (`python3` on Linux and macOS)"
FIELDS = ("id", "vendor", "aircraft", "label", "code", "presetType")    # what every preset holds, as text


def names(families=None):
    """The name of every preset these family tables use (default: all)"""
    families = FAMILIES.values() if families is None else families
    return {name for family in families for buttons in family.DEVICE.values()
            for entry in buttons.values() for name in profile.actions(entry).values()}


def parse(data, source):
    """HubHop's database (a list of presets) from the bytes of its JSON, checked for the fields used here"""
    try:
        database = json.loads(data.decode("utf-8-sig"))
    except ValueError as e:                      # UnicodeDecodeError and JSONDecodeError too
        raise ValueError(f"{source} is not HubHop's preset database: {e}") from e
    if not isinstance(database, list) or not all(
            isinstance(p, dict) and all(isinstance(p.get(f), str) for f in FIELDS) for p in database):
        raise ValueError(f"{source} is not HubHop's preset database: not a JSON list of presets that each hold "
                         f"{', '.join(FIELDS)}")
    return database


def load(path):
    """HubHop's database from a downloaded file"""
    try:
        with open(path, "rb") as f:
            data = f.read()
    except OSError as e:
        raise ValueError(f"cannot read HubHop's presets from {path} ({e}): download them with {DOWNLOAD}") from e
    return parse(data, path)


def lookup(database, wanted):
    """name -> preset, for these names; each must name exactly one input preset of the database"""
    found = {}
    for preset in database:
        if preset["presetType"] == "Input" and profile.key(preset) in wanted:
            found.setdefault(profile.key(preset), []).append(preset)
    errors = [f"  {name}: {len(found.get(name, []))} presets" for name in sorted(wanted)
              if len(found.get(name, [])) != 1]
    if errors:
        raise ValueError("these names do not name exactly one HubHop input preset:\n" + "\n".join(errors)
                         + "\nHubHop changed; the family table needs an update, please report it.")
    return {name: presets[0] for name, presets in found.items()}


def main(argv=None):
    parser = argparse.ArgumentParser(prog="mobiflight.hubhop", description=__doc__.split("\n\n")[1])
    parser.add_argument("-o", "--output", default=FILE, help=f"where to save it (default {FILE})")
    parser.add_argument("--url", default=SOURCE, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    try:
        with urllib.request.urlopen(args.url, timeout=120) as response:
            data = response.read()
    except (OSError, http.client.HTTPException) as e:    # IncompleteRead is no OSError
        sys.exit(f"cannot download HubHop's presets from {args.url}: {str(e) or type(e).__name__}\n"
                 f"{args.output} is unchanged")
    try:
        database = parse(data, args.url)                 # before writing: a bad reply keeps a good file
    except ValueError as e:
        sys.exit(f"{e}\n{args.output} is unchanged")
    try:
        with open(args.output, "wb") as f:
            f.write(data)
    except OSError as e:
        sys.exit(f"cannot save HubHop's presets to {args.output}: {e}")
    errors = []                  # per family: one that HubHop broke leaves the others usable
    for key, family in sorted(FAMILIES.items()):
        try:
            lookup(database, names([family]))
        except ValueError as e:
            errors.append(f"--family {key} cannot be generated: {e}")
    if errors:                   # still an error, for CI
        sys.exit(f"saved {args.output}, but " + "\n".join(errors))
    print(f"saved {args.output}: every preset of the family tables found", file=sys.stderr)


if __name__ == "__main__":
    main()
