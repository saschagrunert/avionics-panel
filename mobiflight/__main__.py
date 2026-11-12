"""py -m mobiflight --family g1000 --from guids.mfproj   (python3 -m mobiflight ... on Linux and macOS)

Writes the MobiFlight project of one avionics family for both joysticks, with the presets of HubHop's database
(py -m mobiflight.hubhop downloads it). The joysticks are read from a project saved in MobiFlight with ENT
bound in unit 1 and in unit 2 (docs/using/mapping.md), or given by their serials, JS- and the DirectInput
instance GUID (named "Avionics Panel": MobiFlight rebinds a joystick of another name with the same serial)."""
import argparse
import sys

from mobiflight import hubhop, profile
from mobiflight.families import FAMILIES


def main(argv=None):
    parser = argparse.ArgumentParser(prog="mobiflight", description=__doc__.split("\n\n")[1])
    parser.add_argument("--family", required=True, choices=sorted(FAMILIES))
    joysticks = parser.add_mutually_exclusive_group(required=True)
    joysticks.add_argument("--from", dest="saved", metavar="GUIDS.mfproj",
                           help="a project saved in MobiFlight with ENT bound in unit 1 and in unit 2")
    joysticks.add_argument("--serials", nargs=2, metavar=("DEVICE1", "DEVICE2"),
                           help="the joysticks' serials, JS-<guid>: device 1 (128 buttons), device 2 (64)")
    parser.add_argument("--hubhop", default=hubhop.FILE, metavar="PRESETS.json",
                        help=f"HubHop's preset database (default {hubhop.FILE})")
    parser.add_argument("-o", "--output", metavar="OUT.mfproj", help="default: FAMILY.mfproj")
    args = parser.parse_args(argv)
    family = FAMILIES[args.family]
    try:
        if args.saved:
            controllers = profile.controllers_from(args.saved)
        else:
            controllers = {d: (profile.NAME, profile.serial(s)) for d, s in zip((1, 2), args.serials, strict=True)}
            if controllers[1] == controllers[2]:
                raise ValueError("device 1 and device 2 need different serials")
        presets = hubhop.lookup(hubhop.load(args.hubhop), hubhop.names([family]))
    except (OSError, ValueError) as e:
        parser.error(str(e))
    output = args.output or f"{args.family}.mfproj"
    with open(output, "w", encoding="utf-8", newline="\n") as f:
        f.write(profile.dumps(profile.build(family, controllers, presets)))
    for device in (1, 2):
        name, serial = controllers[device]
        print(f"device {device} ({name}, {serial}): {len(family.DEVICE[device])} buttons mapped, unmapped "
              f"(the reasons are in mobiflight/families/{args.family}.py): "
              f"{', '.join(family.UNMAPPED[device]) or 'none'}", file=sys.stderr)
    print(f"wrote {output}", file=sys.stderr)


if __name__ == "__main__":
    main()
