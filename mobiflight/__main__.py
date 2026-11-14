"""py -m mobiflight --family g1000 [--vfr 1200] [--from guids.mfproj]   (python3 -m mobiflight ... on Linux and macOS)
py -m mobiflight --autopilot kap140 --cockpit g1000 --navigator g1000 [...]
py -m mobiflight --autopilot kap140 --cockpit bendix-king --unit1 gns530 --unit2 gtn650-tds2 [...]
py -m mobiflight --parts-zip avionics-panel-parts.zip [...]

Writes the MobiFlight project of a profile, or of the avionics parts given (one autopilot, one cockpit, and a
navigator of both units or one per unit), for both joysticks; or a zip with a project of each part, to add to a
project as its tabs. Without --from or --serials, MobiFlight asks for the two joysticks once when it opens the
project (docs/using/mapping.md). With them, the project is bound to your joysticks: read, names and all, from a
project saved in MobiFlight with ENT bound in unit 1 and in unit 2, or given by their serials, JS- and the
DirectInput instance GUID, which names both "Avionics Panel". For joysticks of another name, as the simulator's
vJoy devices, use --from: MobiFlight asks again for two joysticks of one name in a project that it does not find
by name and serial (ControllerAutoBinder.cs)."""
import argparse
import sys
import zipfile

from mobiflight import profile
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


def unmapped(family, device):
    """reason -> the buttons of the device that send nothing for it, in the table's order"""
    out = {}
    for button, reason in family.UNMAPPED[device].items():
        out.setdefault(reason, []).append(button)
    return out


def chosen(parser, args):
    """The profile of --family, or of the parts given"""
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
    return compose(", ".join(p.TITLE for p in picked), *picked), "avionics"


def main(argv=None):
    parser = argparse.ArgumentParser(prog="mobiflight", description=__doc__.split("\n\n")[1])
    what = parser.add_mutually_exclusive_group(required=True)
    what.add_argument("--family", choices=sorted(FAMILIES), help="a whole profile")
    what.add_argument("--autopilot", choices=sorted(AUTOPILOTS), help="the autopilot part")
    what.add_argument("--parts-zip", metavar="OUT.zip", help="a zip with a project of every part")
    parser.add_argument("--cockpit", choices=sorted(COCKPITS), help="the cockpit part")
    parser.add_argument("--navigator", choices=sorted(NAVIGATORS), help="the navigator of both units")
    units = sorted(UNIT_NAVIGATORS) + ["none"]
    parser.add_argument("--unit1", choices=units, help="the navigator of unit 1 (none: radios alone)")
    parser.add_argument("--unit2", choices=units, help="the navigator of unit 2 (none: radios alone)")
    parser.add_argument("--vfr", metavar="CODE",
                        help=f"the squawk the VFR key sets (default: {parts.VFR} as in EASA's airspace; 1200 in the "
                             "US)")
    joysticks = parser.add_mutually_exclusive_group()
    joysticks.add_argument("--from", dest="saved", metavar="GUIDS.mfproj",
                           help="a project saved in MobiFlight with ENT bound in unit 1 and in unit 2")
    joysticks.add_argument("--serials", nargs=2, metavar=("DEVICE1", "DEVICE2"),
                           help="the serials of the panel's joysticks, JS-<guid>: device 1 (128 buttons), "
                                "device 2 (64)")
    parser.add_argument("-o", "--output", metavar="OUT.mfproj", help="default: FAMILY.mfproj, or avionics.mfproj")
    args = parser.parse_args(argv)
    if args.parts_zip and (args.cockpit or args.navigator or args.unit1 or args.unit2 or args.output):
        parser.error("--parts-zip writes every part: it takes no parts and no --output")
    try:
        if args.saved:
            controllers = profile.controllers_from(args.saved)
        elif args.serials:
            controllers = {d: (profile.NAME, profile.serial(s)) for d, s in zip((1, 2), args.serials, strict=True)}
            if controllers[1] == controllers[2]:
                raise ValueError("device 1 and device 2 need different serials")
        else:
            controllers = profile.UNBOUND
        if args.parts_zip:
            if args.vfr is not None:
                parts.vfr(args.vfr)                                      # (a wrong code fails before the zip)
            every = every_part()
            with zipfile.ZipFile(args.parts_zip, "w", zipfile.ZIP_DEFLATED) as z:
                for key, part in sorted(every.items()):
                    vfr = args.vfr if part.KIND == "cockpit" else None
                    info = zipfile.ZipInfo(f"avionics-panel-{key}.mfproj", STAMP)
                    info.compress_type = zipfile.ZIP_DEFLATED
                    z.writestr(info, profile.dumps(profile.build(part, controllers, vfr)))
            print(f"wrote {args.parts_zip}: {len(every)} parts", file=sys.stderr)
            return
        family, key = chosen(parser, args)
        project = profile.build(family, controllers, args.vfr)
    except (OSError, ValueError) as e:
        parser.error(str(e))
    output = args.output or f"{key}.mfproj"
    with open(output, "w", encoding="utf-8", newline="\n") as f:
        f.write(profile.dumps(project))
    for device in (1, 2):
        name, serial = controllers[device]
        print(f"device {device} ({name}, {serial}): {len(family.DEVICE[device])} buttons mapped", file=sys.stderr)
        for reason, buttons in unmapped(family, device).items():
            print(f"  unmapped {', '.join(buttons)}: {reason}", file=sys.stderr)
    print(f"wrote {output}", file=sys.stderr)


if __name__ == "__main__":
    main()
