"""py -m mobiflight --family g1000 [--vfr 1200] [--from guids.mfproj]   (python3 -m mobiflight ... on Linux and macOS)
py -m mobiflight --autopilot kap140 --cockpit g1000 --navigator g1000 [...]
py -m mobiflight --autopilot kap140 --cockpit bendix-king --unit1 gns530 --unit2 gtn650-tds2 [...]
py -m mobiflight --parts-zip avionics-panel-parts.zip [...]
py -m mobiflight --ifr1 g1000 [--vfr 1200]
py -m mobiflight --cards avionics-panel-cards.zip
py -m mobiflight --sheets docs/using/aircraft
py -m mobiflight --joystick-definition avionics-panel.joystick.json
py -m mobiflight --list

Writes the MobiFlight project of a profile, or of the avionics parts given (one autopilot, one cockpit, and a
navigator of both units or one per unit), for both joysticks; or a zip with a project of each part, to add to a
project as its tabs; or the project of a profile for the Octavi IFR-1 instead (ifr1.py), which MobiFlight binds to
the one IFR-1 connected; or a zip with the quick-reference card and cheat sheet of each profile, for the panel and
for the IFR-1 (card.py, sheet.py, ifr1_card.py); or the cheat sheet of each profile as SVG (sheet.py); or
MobiFlight's joystick definition, which labels the buttons (joystick.py). Without --from or --serials, MobiFlight
asks for the two joysticks once when it opens the project (docs/using/mapping.md). With them, the project is bound to
your joysticks: read, names and all, from a project saved in MobiFlight with ENT bound in unit 1 and in unit 2, or
given by their serials, JS- and the DirectInput instance GUID, which names both "Avionics Panel". For joysticks of
another name, as the simulator's vJoy devices, use --from: MobiFlight asks again for two joysticks of one name in a
project that it does not find by name and serial (ControllerAutoBinder.cs). The project's name ends in the commit of
the files, in a release's files (profile.VERSION), or in what --stamp gives. --list lists the profiles and the parts."""
import argparse
import os
import sys
import zipfile

from mobiflight import card, cards, ifr1, joystick, profile
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


replacing = profile.replacing         # the CLI's every file goes through it (and sheet.write())


def unmapped(reasons):
    """reason -> the buttons that send nothing for it, in their order, of {button: reason}"""
    out = {}
    for button, reason in reasons.items():
        out.setdefault(reason, []).append(button)
    return out


UNITS = sorted(UNIT_NAVIGATORS) + ["none"]   # what --unit1 and --unit2 take (none: radios alone)


def listing():
    """The profiles and the parts, a line for each option that takes them"""
    return "\n".join(f"{option}: {' '.join(sorted(keys))}" for option, keys in (
        ("--family", FAMILIES), ("--ifr1", FAMILIES), ("--autopilot", AUTOPILOTS), ("--cockpit", COCKPITS),
        ("--navigator", NAVIGATORS), ("--unit1, --unit2", UNITS)))


def codes(part):
    """Every code a part sends, on every event of every button"""
    return {code for table in part.DEVICE.values() for entry in table.values()
            for code in profile.actions(entry).values()}


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
    units = (NAVIGATORS[args.navigator],) if args.navigator else navigators(args.unit1, args.unit2)
    if len(units) == 2 and codes(units[0]) & codes(units[1]):
        # the same navigator in both units, but one its maker names by unit (PMS50's GTN 750 in each, GTN750_ and
        # GTN750_2_): the two would work one navigator
        parser.error(f"{args.unit1} in both units: the two would work one navigator (none: radios alone)")
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
    what.add_argument("--ifr1", choices=sorted(FAMILIES), help="a whole profile for the Octavi IFR-1")
    what.add_argument("--cards", metavar="OUT.zip",
                      help="a zip with the quick-reference card and the cheat sheet of every profile, for the panel "
                           "and for the IFR-1")
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
                        help="default: avionics-panel-FAMILY.mfproj, avionics-panel-ifr1-FAMILY.mfproj for --ifr1, "
                             "or avionics-panel.mfproj for parts")
    parser.add_argument("--stamp", metavar="TEXT", default=profile.VERSION,
                        help="the text in brackets after the project's, the card's or the sheet's name, as the date "
                             f"and short hash of the commit (default: {profile.VERSION or 'none'}, from "
                             "firmware/version.py)")
    parser.add_argument("--tag", metavar="TAG",
                        help="with --cards: the release whose projects and docs the index links (default: the latest "
                             "build's and main's)")
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
    if args.cards and others("cards", "stamp", "tag"):
        parser.error("--cards takes no other option but --stamp and --tag")
    if args.tag and not args.cards:
        parser.error("--tag is for --cards alone")
    if args.sheets and others("sheets"):
        parser.error("--sheets takes no other option")
    if args.ifr1 and others("ifr1", "vfr", "output", "stamp"):
        parser.error("--ifr1 is a whole profile, bound to the IFR-1: it takes only --vfr, --output and --stamp")
    if args.joystick_definition and others("joystick_definition"):
        parser.error("--joystick-definition takes no other option")
    if args.joystick_definition and not args.joystick_definition.lower().endswith(".joystick.json"):
        parser.error("MobiFlight loads only files named *.joystick.json")
    try:
        if args.cards:
            # sheet reads viewer/geometry.js and mech/stack.py, which a profile does without, and ifr1_card reads sheet
            from mobiflight import ifr1_card, sheet
            with replacing(args.cards, binary=True) as f, zipfile.ZipFile(f, "w", zipfile.ZIP_DEFLATED) as z:
                for key, family in sorted(FAMILIES.items()):
                    panel_card, panel_sheet, one_card, one_sheet = cards.files(key)
                    z.writestr(entry(panel_card), card.page(family, key, args.stamp))
                    z.writestr(entry(panel_sheet), sheet.svg(key, sheet.TITLES[key], args.stamp))
                    one = ifr1.build(key)
                    z.writestr(entry(one_card), ifr1_card.page(one, args.stamp))
                    z.writestr(entry(one_sheet), ifr1_card.page(one, args.stamp, words=True))
                z.writestr(entry("index.html"),                       # and at cards/ beside the 3D view
                           cards.index(dict(sorted(FAMILIES.items())), args.stamp, args.tag))
            print(f"wrote {args.cards}: {len(FAMILIES)} cards and cheat sheets, as many for the IFR-1, and their index",
                  file=sys.stderr)
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
        if args.ifr1:
            one = ifr1.build(args.ifr1, args.vfr)
            output = args.output or ifr1.filename(args.ifr1)
            with replacing(output) as f:
                f.write(profile.dumps(ifr1.project(one, args.stamp)))
            print(f"IFR-1 ({ifr1.NAME}, {ifr1.SERIAL}): {len(one.DEVICE)} buttons mapped", file=sys.stderr)
            for reason, buttons in unmapped({b.removeprefix("Button_"): r for b, r in one.UNMAPPED.items()}).items():
                print(f"  unmapped {', '.join(buttons)}: {reason}", file=sys.stderr)
            print(f"wrote {output}", file=sys.stderr)
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
        for reason, buttons in unmapped(family.UNMAPPED[device]).items():
            print(f"  unmapped {', '.join(buttons)}: {reason}", file=sys.stderr)
    print(f"wrote {output}", file=sys.stderr)


if __name__ == "__main__":
    main()
