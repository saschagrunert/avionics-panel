"""The live panel (sim/live.py) as a Linux HID device, through uhid: the kernel gets the report descriptor boot.py
builds (both joysticks, report IDs 4 and 5, as on the panel's one HID interface; in keyboard mode the keyboard of
keys.py), the name and IDs the panel has on USB, and every report code.py sends. The USB layer itself
(enumeration, interfaces, update mode's drive and console) is not there.

    python3 -m sim.uhid [--keyboard]

reads actions from stdin, one per line (sim.live.LINES), such as `tap AP`, `tap AP 500` (held 500 ms),
`turn FREQ_INNER 3`, `tilt UP 500`, `press SHIFT`, `release SHIFT` or `wait 1000`; a turn is 30 detents at most
(sim.live.TURN_MAX, a turn of the knob). `lights` prints the duty of both lights once the actions before it have
taken effect. The end of the input ends it, after the actions have run. --keyboard runs the keyboard mode: the
desktop then takes its shortcuts like those of any keyboard, in the window that has the focus.

It needs write access to /dev/uhid: run it as root, or give your user access with a udev rule, which lets it
create any HID device, keyboards included.
"""
import argparse
import errno
import os
import select
import struct
import sys
import threading

from sim.live import Live, from_stdin

# <linux/uhid.h>
UHID_START, UHID_GET_REPORT, UHID_GET_REPORT_REPLY, UHID_CREATE2, UHID_INPUT2 = 2, 9, 10, 11, 12
UHID_SET_REPORT, UHID_SET_REPORT_REPLY, UHID_INPUT_REPORT = 13, 14, 2
EVENT_SIZE = 4376          # sizeof(struct uhid_event)
BUS_USB = 3
VID, PID = 0x239A, 0x80F4  # CircuitPython's Raspberry Pi Pico build (docs/using/mapping.md): boot.py keeps them
VERSION = 0x0100           # bcdDevice


class Uhid:
    """One uhid device with both joysticks, or the keyboard. send(device, report) is Live's output. A thread
    answers the kernel's requests: GET_REPORT of an input report with the last one sent, any other with EIO, as
    SET_REPORT (the descriptor has no feature reports; the keyboard's LED output reports come as UHID_OUTPUT,
    which goes unanswered)."""

    def __init__(self, board, phys="avionics-panel-sim", path="/dev/uhid"):
        descriptor = b"".join(d.report_descriptor for d in board.devices)
        manufacturer, product, *ids = next(c[1:] for c in board.calls if c[0] == "set_usb_identification")
        vid, pid = ids[:2] if ids else (VID, PID)
        self.name = f"{manufacturer} {product}"    # as Linux names a USB HID device
        self.numbered = any(d.report_ids[0] for d in board.devices)   # the joysticks' reports start with their ID
        self.last, self.closing = {}, threading.Event()   # the last report sent, by report ID (0: none)
        try:
            self.fd = os.open(path, os.O_RDWR | os.O_CLOEXEC)
        except PermissionError as e:
            raise PermissionError(e.errno, f"{e.strerror}: {path} needs write access (root, or a udev rule)") from e
        try:
            self.write(UHID_CREATE2, struct.pack("<128s64s64sHHIIII", self.name.encode(), phys.encode(), b"",
                                                 len(descriptor), BUS_USB, vid, pid, VERSION, 0) + descriptor)
            if not select.select([self.fd], [], [], 2)[0] or self.read()[0] != UHID_START:
                raise OSError(f"{path}: the kernel did not start the device (see dmesg)")
        except BaseException:
            os.close(self.fd)
            raise
        self.thread = threading.Thread(target=self.answer, name="uhid", daemon=True)
        self.thread.start()

    def write(self, kind, data):
        os.write(self.fd, struct.pack("<I", kind) + data.ljust(EVENT_SIZE - 4, b"\0"))

    def read(self):
        """The next event from the kernel: (type, its data)"""
        event = os.read(self.fd, EVENT_SIZE)
        return struct.unpack_from("<I", event)[0], event[4:]

    def answer(self):
        while not self.closing.is_set():
            if not select.select([self.fd], [], [], 0.05)[0]:
                continue
            kind, data = self.read()                   # start, open, close: nothing to do
            if kind == UHID_GET_REPORT:
                request, number, report_type = struct.unpack_from("<IBB", data)
                report = self.last.get(number, b"") if report_type == UHID_INPUT_REPORT else b""
                self.write(UHID_GET_REPORT_REPLY,
                           struct.pack("<IHH", request, 0 if report else errno.EIO, len(report)) + report)
            elif kind == UHID_SET_REPORT:
                self.write(UHID_SET_REPORT_REPLY, struct.pack("<IH", struct.unpack_from("<I", data)[0], errno.EIO))

    def send(self, device, report):
        self.last[report[0] if self.numbered else 0] = report
        self.write(UHID_INPUT2, struct.pack("<H", len(report)) + report)

    def close(self):
        self.closing.set()
        self.thread.join()
        os.close(self.fd)                              # the kernel removes the device


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python3 -m sim.uhid", description=__doc__.split("\n\n")[0])
    parser.add_argument("--keyboard", action="store_true", help="the keyboard mode: a keyboard, no joysticks")
    live = Live(keyboard=parser.parse_args(argv).keyboard)
    try:
        uhid = Uhid(live)
    except OSError as e:
        sys.exit(f"sim.uhid: {e}")
    print(f"{uhid.name} on uhid; actions, one per line:", file=sys.stderr)
    from_stdin(live, uhid, "sim.uhid")


if __name__ == "__main__":
    main()
