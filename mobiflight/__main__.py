"""py -m mobiflight --family g1000 [--vfr 7000] [--from guids.mfproj]   (python3 -m mobiflight ... on Linux and macOS)

Writes the MobiFlight project of one avionics family for both joysticks. Without --from or --serials, MobiFlight
asks for the two joysticks once when it opens the project (docs/using/mapping.md). With them, the project is
bound to your joysticks: read, names and all, from a project saved in MobiFlight with ENT bound in unit 1 and in
unit 2, or given by their serials, JS- and the DirectInput instance GUID, which names both "Avionics Panel". For
joysticks of another name, as the simulator's vJoy devices, use --from: MobiFlight asks again for two joysticks of
one name in a project that it does not find by name and serial (ControllerAutoBinder.cs)."""
import argparse
import sys

from mobiflight import profile
from mobiflight.families import FAMILIES, parts


def unmapped(family, device):
    """reason -> the buttons of the device that send nothing for it, in the table's order"""
    out = {}
    for button, reason in family.UNMAPPED[device].items():
        out.setdefault(reason, []).append(button)
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(prog="mobiflight", description=__doc__.split("\n\n")[1])
    parser.add_argument("--family", required=True, choices=sorted(FAMILIES))
    parser.add_argument("--vfr", metavar="CODE",
                        help=f"the squawk the VFR key sets (default: the family's, {parts.VFR}; 7000 in much of "
                             "Europe)")
    joysticks = parser.add_mutually_exclusive_group()
    joysticks.add_argument("--from", dest="saved", metavar="GUIDS.mfproj",
                           help="a project saved in MobiFlight with ENT bound in unit 1 and in unit 2")
    joysticks.add_argument("--serials", nargs=2, metavar=("DEVICE1", "DEVICE2"),
                           help="the serials of the panel's joysticks, JS-<guid>: device 1 (128 buttons), "
                                "device 2 (64)")
    parser.add_argument("-o", "--output", metavar="OUT.mfproj", help="default: FAMILY.mfproj")
    args = parser.parse_args(argv)
    family = FAMILIES[args.family]
    try:
        if args.saved:
            controllers = profile.controllers_from(args.saved)
        elif args.serials:
            controllers = {d: (profile.NAME, profile.serial(s)) for d, s in zip((1, 2), args.serials, strict=True)}
            if controllers[1] == controllers[2]:
                raise ValueError("device 1 and device 2 need different serials")
        else:
            controllers = profile.UNBOUND
        project = profile.build(family, controllers, args.vfr)
    except (OSError, ValueError) as e:
        parser.error(str(e))
    output = args.output or f"{args.family}.mfproj"
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
