"""py -m mobiflight --family g1000 [--vfr 1200] [--from guids.mfproj]   (python3 -m mobiflight ... on Linux and macOS)
py -m mobiflight --autopilot kap140 --cockpit g1000 --navigator g1000 [...]
py -m mobiflight --autopilot kap140 --cockpit bendix-king --unit1 gns530 --unit2 gtn650-tds2 [...]
py -m mobiflight --parts-zip avionics-panel-parts.zip [...]
py -m mobiflight --cards avionics-panel-cards.zip
py -m mobiflight --sheets docs/using/aircraft
py -m mobiflight --joystick-definition avionics-panel.joystick.json
py -m mobiflight --list

Writes the MobiFlight project of a profile, or of the avionics parts given (one autopilot, one cockpit, and a
navigator of both units or one per unit), for both joysticks; or a zip with a project of each part, to add to a
project as its tabs; or a zip with the quick-reference card of each profile (card.py); or the cheat sheet of each
profile as SVG (sheet.py); or MobiFlight's joystick definition, which labels the buttons (joystick.py). Without
--from or --serials, MobiFlight asks for the two joysticks once when it opens the project (docs/using/mapping.md).
With them, the project is bound to your joysticks: read, names and all, from a project saved in MobiFlight with ENT
bound in unit 1 and in unit 2, or given by their serials, JS- and the DirectInput instance GUID, which names both
"Avionics Panel". For joysticks of another name, as the simulator's vJoy devices, use --from: MobiFlight asks again
for two joysticks of one name in a project that it does not find by name and serial (ControllerAutoBinder.cs). The
project's name ends in the commit of the files, in a release's files (profile.VERSION), or in what --stamp gives.
--list lists the profiles and the parts."""
import argparse
import contextlib
import errno
import os
import shutil
import sys
import tempfile
import zipfile

from mobiflight import card, joystick, profile
from mobiflight.families import (
    AUTOPILOTS,
    COCKPITS,
    FAMILIES,
    NAVIGATORS,
    UNIT_NAVIGATORS,
    every_part,
    navigators,
    parts,
)
from mobiflight.families.part import compose

STAMP = (2024, 1, 1, 0, 0, 0)    # the zip's entries' time, so the same parts make the same zip


def entry(name):
    """A zip entry of this name, with the time, mode (rw-r--r--, not the 600 of no mode) and compression of every zip
    the generator writes"""
    info = zipfile.ZipInfo(name, STAMP)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    return info


@contextlib.contextmanager
def replacing(path, binary=False):
    """A file to write path through: a new file in its folder, which takes path's place once the block ends without
    an error and is removed after any other end, so nothing half written stays and a file already there is left as
    it was. A file there that may not be written is refused before, as opening it would be. A symbolic link is
    followed, so the file it points to is replaced, and a file there keeps its mode. (The new file needs the right
    to make files in the folder, which writing over a file there alone did not.)"""
    path = os.path.realpath(path)
    if os.path.exists(path) and not os.access(path, os.W_OK):
        raise PermissionError(errno.EACCES, os.strerror(errno.EACCES), path)
    fd, new = tempfile.mkstemp(dir=os.path.dirname(path), prefix=f".{os.path.basename(path)}.")
    try:
        with os.fdopen(fd, "wb") if binary else os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            yield f
        if os.path.exists(path):
            shutil.copymode(path, new)
        else:                                        # as open() makes it, not mkstemp()'s rw-------
            mask = os.umask(0o22)
            os.umask(mask)
            os.chmod(new, 0o666 & ~mask)
        os.replace(new, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.remove(new)
        raise


def unmapped(family, device):
    """reason -> the buttons of the device that send nothing for it, in the table's order"""
    out = {}
    for button, reason in family.UNMAPPED[device].items():
        out.setdefault(reason, []).append(button)
    return out


UNITS = sorted(UNIT_NAVIGATORS) + ["none"]   # what --unit1 and --unit2 take (none: radios alone)


def listing():
    """The profiles and the parts, a line for each option that takes them"""
    return "\n".join(f"{option}: {' '.join(sorted(keys))}" for option, keys in (
        ("--family", FAMILIES), ("--autopilot", AUTOPILOTS), ("--cockpit", COCKPITS), ("--navigator", NAVIGATORS),
        ("--unit1, --unit2", UNITS)))


def chosen(parser, args):
    """The profile of --family, or of the parts given, and its key (None for parts: profile.filename)"""
    if args.family:
        if args.cockpit or args.navigator or args.unit1 or args.unit2:      # (--autopilot: its own group)
            parser.error("--family is a whole profile: give it or the parts, not both")
        return FAMILIES[args.family], args.family
    if not (args.autopilot and args.cockpit and (args.navigator or (args.unit1 and args.unit2))) \
            or args.navigator and (args.unit1 or args.unit2):
        parser.error("give --family, or --autopilot, --cockpit and --navigator, or --autopilot, --cockpit, --unit1 "
                     "and --unit2")
    if args.unit1 and args.unit1 == args.unit2 != "none":
        parser.error(f"{args.unit1} in both units: the two would work one navigator (none: radios alone)")
    units = (NAVIGATORS[args.navigator],) if args.navigator else navigators(args.unit1, args.unit2)
    picked = (AUTOPILOTS[args.autopilot], COCKPITS[args.cockpit], *units)
    return compose(", ".join(p.TITLE for p in picked), *picked), None


def unclobbered(parser, args, output):
    """A usage error where output is the project --from reads: writing it would lose that project's own bindings"""
    if args.saved and os.path.exists(output) and os.path.samefile(output, args.saved):
        parser.error(f"{output} is the project --from reads: give another file to write")


def main(argv=None):
    parser = argparse.ArgumentParser(prog="mobiflight", description=__doc__.split("\n\n")[1])
    what = parser.add_mutually_exclusive_group(required=True)
    what.add_argument("--family", choices=sorted(FAMILIES), help="a whole profile")
    what.add_argument("--autopilot", choices=sorted(AUTOPILOTS), help="the autopilot part")
    what.add_argument("--parts-zip", metavar="OUT.zip", help="a zip with a project of every part")
    what.add_argument("--cards", metavar="OUT.zip", help="a zip with the quick-reference card of every profile")
    what.add_argument("--sheets", metavar="DIR", help="the cheat sheet of every profile, as DIR/<profile>.svg")
    what.add_argument("--joystick-definition", metavar="OUT.joystick.json",
                      help="MobiFlight's joystick definition, with a label for every button")
    what.add_argument("--list", action="store_true", help="list the profiles and the parts, and write nothing")
    parser.add_argument("--cockpit", choices=sorted(COCKPITS), help="the cockpit part")
    parser.add_argument("--navigator", choices=sorted(NAVIGATORS), help="the navigator of both units")
    parser.add_argument("--unit1", choices=UNITS, help="the navigator of unit 1 (none: radios alone)")
    parser.add_argument("--unit2", choices=UNITS, help="the navigator of unit 2 (none: radios alone)")
    parser.add_argument("--vfr", metavar="CODE",
                        help=f"the squawk the VFR key sets (default: {parts.VFR} as in EASA's airspace; 1200 in the "
                             "US)")
    joysticks = parser.add_mutually_exclusive_group()
    joysticks.add_argument("--from", dest="saved", metavar="GUIDS.mfproj",
                           help="a project saved in MobiFlight with ENT bound in unit 1 and in unit 2")
    joysticks.add_argument("--serials", nargs=2, metavar=("DEVICE1", "DEVICE2"),
                           help="the serials of the panel's joysticks, JS-<guid>: device 1 (128 buttons), "
                                "device 2 (64)")
    parser.add_argument("-o", "--output", metavar="OUT.mfproj",
                        help="default: avionics-panel-FAMILY.mfproj, or avionics-panel.mfproj for parts")
    parser.add_argument("--stamp", metavar="TEXT", default=profile.VERSION,
                        help="the text in brackets after the project's or the card's name, as the date and short "
                             f"hash of the commit (default: {profile.VERSION or 'none'}, from firmware/version.py)")
    args = parser.parse_args(argv)
    def others(*own):                   # an option given (not its default) but these
        return any(value != parser.get_default(name) for name, value in vars(args).items() if name not in own)

    if args.list:
        if others("list"):
            parser.error("--list lists the profiles and parts: it takes no other option")
        print(listing())
        return
    if args.parts_zip and (args.cockpit or args.navigator or args.unit1 or args.unit2 or args.output):
        parser.error("--parts-zip writes every part: it takes no parts and no --output")
    if args.cards and others("cards", "stamp"):
        parser.error("--cards takes no other option but --stamp")
    if args.sheets and others("sheets"):
        parser.error("--sheets takes no other option")
    if args.joystick_definition and others("joystick_definition"):
        parser.error("--joystick-definition takes no other option")
    if args.joystick_definition and not args.joystick_definition.lower().endswith(".joystick.json"):
        parser.error("MobiFlight loads only files named *.joystick.json")
    try:
        if args.cards:
            with replacing(args.cards, binary=True) as f, zipfile.ZipFile(f, "w", zipfile.ZIP_DEFLATED) as z:
                for key, family in sorted(FAMILIES.items()):
                    z.writestr(entry(f"avionics-panel-{key}-card.html"), card.page(family, key, args.stamp))
            print(f"wrote {args.cards}: {len(FAMILIES)} cards", file=sys.stderr)
            return
        if args.sheets:
            from mobiflight import sheet  # reads mech/stack.py's legends, which a profile does without
            paths = sheet.write(args.sheets)
            print(f"wrote {len(paths)} sheets to {args.sheets}", file=sys.stderr)
            return
        if args.joystick_definition:
            with replacing(args.joystick_definition) as f:
                f.write(joystick.dumps(joystick.definition()))
            print(f"wrote {args.joystick_definition}", file=sys.stderr)
            return
        if args.saved:
            controllers = profile.controllers_from(args.saved)
        elif args.serials:
            controllers = {d: (profile.NAME, profile.serial(s)) for d, s in zip((1, 2), args.serials, strict=True)}
            if controllers[1] == controllers[2]:
                raise ValueError("device 1 and device 2 need different serials")
        else:
            controllers = profile.UNBOUND
        if args.parts_zip:
            unclobbered(parser, args, args.parts_zip)
            if args.vfr is not None:
                parts.vfr(args.vfr)                                      # (a wrong code fails before the zip)
            every = every_part()
            with replacing(args.parts_zip, binary=True) as f, zipfile.ZipFile(f, "w", zipfile.ZIP_DEFLATED) as z:
                for key, part in sorted(every.items()):
                    vfr = args.vfr if part.KIND == "cockpit" else None
                    project = profile.build(part, controllers, vfr, args.stamp)
                    z.writestr(entry(profile.filename(key)), profile.dumps(project))
            print(f"wrote {args.parts_zip}: {len(every)} parts", file=sys.stderr)
            return
        family, key = chosen(parser, args)
        project = profile.build(family, controllers, args.vfr, args.stamp)
    except (OSError, ValueError) as e:
        parser.error(str(e))
    output = args.output or profile.filename(key)
    unclobbered(parser, args, output)
    try:
        with replacing(output) as f:                     # no part of a project, which MobiFlight could not load
            f.write(profile.dumps(project))
    except OSError as e:
        parser.error(str(e))
    for device in (1, 2):
        name, serial = controllers[device]
        print(f"device {device} ({name}, {serial}): {len(family.DEVICE[device])} buttons mapped", file=sys.stderr)
        for reason, buttons in unmapped(family, device).items():
            print(f"  unmapped {', '.join(buttons)}: {reason}", file=sys.stderr)
    print(f"wrote {output}", file=sys.stderr)


if __name__ == "__main__":
    main()
