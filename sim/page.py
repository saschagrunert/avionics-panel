"""The live panel (sim/live.py) in the browser: serves the 3D view (viewer/) with the panel playable in it, and an
API for it. Python's standard library only.

    python3 -m sim.page [--keyboard] [--uhid | --vjoy | --sendinput] [--port N] [--host ADDR] [--open]

prints the page's URL (http://127.0.0.1:8000/?sim): the ?sim makes the viewer play the panel (viewer/sim.js).
With --uhid the reports also go to a Linux HID device, as with `python3 -m sim.uhid`; with --vjoy to vJoy's
devices 1 and 2 on Windows, as with `python -m sim.vjoy`. --keyboard runs the keyboard mode (keys.py), whose
keystrokes --sendinput gives to the window in front on Windows (sim/sendinput.py). --open opens the page in the
default browser once it is served.

The API, under /sim/:

- GET events: one Server-Sent Events stream per page. `hello` first, with the page's client ID (a secret: only
  the page can read it), the firmware names of the caps and knobs geometry.js draws (inputs()) and the numbers the
  page keeps to (the detents of a knob's turn, TURN_MAX, ACTS_MAX and BEAT_S in ms), then `state` whenever the
  lights or the buttons change (the lights are read every POLL_S, so the SHIFT light's 125 ms pulse keeps its
  rhythm; in keyboard mode the buttons are the keyboard's, with the shortcut), and `fault` for an error in
  code.py's loop, which then reloads (not `error`: EventSource has an event of that name).
- POST act?client=ID: actions, one per line, run at once and in order: `press NAME`, `release NAME` (a key, push
  or RANGE switch) and `turn RING DETENTS` (all in the same ms, sim.live.TURN_MAX at most). Nothing paces them: a
  fast wheel is a fast turn. An empty one only says that the page is still there. 204, or 400 with the reason
  (nothing runs), 409 for a client that has gone, 413 for a body over BODY_MAX.

A page that goes lets go of what it holds, unless another page holds it too: when its stream closes, and when it
has not posted for LEASE_S (a tablet that drops off the network closes nothing; the page posts every BEAT_S).
A browser asks before it reuses a file it has kept (Cache-Control: no-cache) and always gets the file, never a
304, so the page it shows is the one this program serves. A connection that stalls for TIMEOUT_S is closed.
Only this server's own page drives the panel: a request with a Host other than an IP address or localhost with
the server's port (DNS rebinding), from another Origin, or from another site (Sec-Fetch-Site) gets 403, except a
link to the page itself from another site; no other site may frame the page (clickjacking), and none can read a
client ID.

A fatal error of the live panel ends the program with its traceback; the page then says it is disconnected.
"""
import argparse
import contextlib
import errno
import ipaddress
import json
import os
import re
import secrets
import select
import socket
import sys
import threading
import time
import webbrowser
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from sim import BM, FUNCTIONS, LIGHTS, TILT, key_name
from sim.hardware import make_keys
from sim.live import DETENTS, TURN_MAX, USAGE, Live, parse
from sim.sendinput import SendInput
from sim.uhid import Uhid
from sim.vjoy import VJoy

VIEWER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "viewer")
GEOMETRY = os.path.join(VIEWER, "geometry.js")
POLL_S = 0.01        # the stream reads the lights and the reports this often
LEASE_S = 3          # a page that has not posted for this long has gone ...
BEAT_S = 1           # ... so it posts this often, an empty request if it has nothing else
TIMEOUT_S = 10       # a request or a stream's event that takes longer ends its connection
BODY_MAX = 65536     # bytes of an act request at most
ACTS_MAX = 64        # actions in one request at most: a page sends a few, so none can queue minutes of changes
ACTS = {"press": USAGE["press"], "release": USAGE["release"], "turn": "turn RING DETENTS"}   # what act takes
WSAEACCES = 10013    # OSError.winerror (with errno 13) for a port Windows gives to no one: another program has it
                     # to itself, or it lies in a range that Windows keeps, as for Hyper-V and WSL
PORT_MAX = 65535


def port(text):
    """--port's value: 0, for any free port, to PORT_MAX"""
    number = int(text)
    if not 0 <= number <= PORT_MAX:
        raise ValueError(text)
    return number


def inputs(path=GEOMETRY):
    """The firmware's input names of the caps and knobs geometry.js draws: {"keys": {cap legend: switch},
    "knobs": {knob: {"outer", "inner" or "ring": its ring, "push": switch, RANGE's "tilt": {way: switch}}}}"""
    with open(path, encoding="utf-8") as f:
        text = f.read()
    geometry = json.loads(text[text.index("{"):text.rindex("}") + 1])
    keys = {label: key_name(label) for row in geometry["key_legends"] for label, _ in row}
    knobs = {}
    for knob in geometry["knobs"]:
        if knob == "RANGE":      # its centre push closes the tilt's "com" alone, a tilt closes it and a direction
            knobs[knob] = {"ring": "RANGE", "push": "RANGE_COM", "tilt": TILT}
        else:
            knobs[knob] = {"outer": f"{knob}_OUTER", "inner": f"{knob}_INNER", "push": f"{knob}_PUSH"}
    return {"keys": keys, "knobs": knobs}


def actions(body):
    """[(action, arguments)] of an act request's lines (ACTS), ACTS_MAX at most; ValueError for a wrong one"""
    lines = list(filter(None, (parse(line, ACTS) for line in body.splitlines())))
    if len(lines) > ACTS_MAX:
        raise ValueError(f"{ACTS_MAX} actions in one request at most")
    return [(action, args + [0] if action == "turn" else args) for action, args in lines]


def local(host, port):
    """Is a Host header this server's own: an IP address or localhost, with the server's port (a browser leaves
    out port 80)? Another name could be one that a site has pointed at this machine."""
    match = re.fullmatch(r"(\[[0-9A-Fa-f:.]+\]|[^:\[\]]+)(?::([0-9]+))?", host)
    if not match or int(match[2] or 80) != port:
        return False
    with contextlib.suppress(ValueError):
        ipaddress.ip_address(match[1].strip("[]"))
        return True
    return match[1] == "localhost"


def lan_address():
    """This computer's address on its network, as a tablet beside it reaches it (127.0.0.1 without one). Connecting
    a UDP socket only picks the route: nothing is sent."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.connect(("192.0.2.1", 9))        # TEST-NET-1, never routed anywhere
            return s.getsockname()[0]
        except OSError:
            return "127.0.0.1"


class Page(ThreadingHTTPServer):
    daemon_threads = True
    # Windows' SO_REUSEADDR lets a second server bind a port that another one listens on, and either then gets
    # the connections: there the port must be free
    allow_reuse_address = sys.platform != "win32"

    def __init__(self, live, address=("127.0.0.1", 0), forward=None):
        """Serves the page for a Live, not started yet: start it with output as its output. forward(device,
        report) gets every report too (Uhid.send)."""
        super().__init__(address, partial(Handler, directory=VIEWER))
        self.live, self.forward, self.inputs = live, forward, inputs()
        self.reports = {}                      # the last report of each device
        self.held, self.seen = {}, {}          # each client's switches held, and when it last posted
        self.lock, self.closing = threading.Lock(), threading.Event()

    @property
    def url(self):
        host, port = self.server_address[:2]
        if host == "0.0.0.0":                  # on every interface: the address a tablet opens
            host = lan_address()
        return f"http://{host}:{port}/?sim"

    def output(self, device, report):
        self.reports[device] = report
        if self.forward:
            self.forward(device, report)

    def state(self):
        """The lights (their duty as a share of full on: 1, or 0.25 for SHIFT's dim pulse) and each device's
        buttons by name; in keyboard mode the keyboard's ("keyboard") function with its shortcut and unit"""
        live, lights = self.live, {}
        for i, name in enumerate(LIGHTS):
            duty = live.light(name)
            lights[name] = round(duty / live.code["LED_DUTY"][i], 3) if duty else 0
        if live.keyboard:
            buttons = {}
            if 1 in self.reports:
                mods, key = self.reports[1][0], self.reports[1][2]
                dev, name = FUNCTIONS.get((mods, key), (None, None))
                unit = " (unit 2)" if dev == 2 else ""
                buttons["keyboard"] = [f"{name}{unit} {make_keys.shortcut_name(mods, key)}"] if dev else []
        else:
            buttons = {device: [n for b, n in enumerate(BM.DEVICE[device]) if report[1 + b // 8] >> b % 8 & 1]
                       for device, report in sorted(self.reports.items())}
        return {"lights": lights, "buttons": buttons}

    def connect(self):
        client = secrets.token_urlsafe(16)
        with self.lock:
            self.held[client], self.seen[client] = set(), time.monotonic()
        return client

    def act(self, client, actions):
        """Runs actions (actions()) for a client. KeyError for a client that has gone, RuntimeError once the panel
        has stopped."""
        with self.lock:                        # all or nothing against disconnect(): nothing stays held
            if client not in self.held:
                raise KeyError(client)
            self.seen[client] = time.monotonic()
            for action, args in actions:
                if action == "turn":
                    self.live.act(action, *args)
                    continue
                name, mine = args[0], self.held[client]
                if not self.elsewhere(client, name):      # a switch another page holds stays as it is
                    self.live.act(action, name)
                (mine.add if action == "press" else mine.discard)(name)

    def elsewhere(self, client, name):
        return any(name in held for other, held in self.held.items() if other != client)

    def gone(self, client):
        return time.monotonic() - self.seen[client] > LEASE_S

    def disconnect(self, client):
        """Lets go of what the client holds, but not of what another one holds too"""
        with self.lock:
            del self.seen[client]
            for name in sorted(self.held.pop(client)):
                if not self.elsewhere(client, name):
                    self.live.act("release", name)

    def stop(self):
        self.closing.set()
        self.shutdown()
        self.server_close()


class Handler(SimpleHTTPRequestHandler):
    timeout = TIMEOUT_S

    def log_request(self, *args):
        pass

    def log_error(self, format, *args):
        if not format.startswith("Request timed out"):           # a connection closed after TIMEOUT_S is no news
            super().log_error(format, *args)

    def end_headers(self):
        self.send_header("X-Frame-Options", "DENY")              # no other site frames the page (clickjacking)
        self.send_header("Content-Security-Policy", "frame-ancestors 'none'")
        # a browser asks before it reuses a file. Left to itself it reuses one for a tenth of its age, which is days
        # for the files of a zip (they have the commit's time): an older simulator's page against this program
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def send_head(self):
        # a browser that asks gets the file, never a 304: the copy it has kept can be another simulator's and
        # still be the newer one by its time (an older zip unpacked after a newer one, a zip after a checkout)
        del self.headers["If-Modified-Since"]
        return super().send_head()

    def foreign(self):
        """Sends 403 to a request that does not come from this server's own page. Another site may link to the
        page (a top-level navigation; framing it is refused by end_headers()), but not use the API or load the
        page's files into its own."""
        h = self.headers
        host, origin, path = h.get("Host", ""), h.get("Origin"), urlsplit(self.path).path
        link = h.get("Sec-Fetch-Mode") == "navigate" and h.get("Sec-Fetch-Dest") == "document" \
            and not path.startswith("/sim/")
        if (local(host, self.server.server_address[1]) and origin in (None, f"http://{host}")
                and (link or h.get("Sec-Fetch-Site") not in ("cross-site", "same-site"))):
            return False
        self.send_error(403, explain="open the page by this computer's IP address or localhost, as the simulator "
                                     "prints it")
        return True

    def do_HEAD(self):
        if not self.foreign():
            super().do_HEAD()

    def do_GET(self):
        path = urlsplit(self.path)
        if self.foreign():
            return
        if path.path == "/" and not path.query:            # the panel, not the plain 3D view
            self.send_response(302)
            self.send_header("Location", "/?sim")
            self.end_headers()
        elif path.path == "/sim/events":
            self.events()
        else:
            super().do_GET()

    def do_POST(self):
        path = urlsplit(self.path)
        if self.foreign():
            return
        if path.path != "/sim/act":
            return self.send_error(404)
        client, length = parse_qs(path.query).get("client", [None])[0], self.headers.get("Content-Length", "0")
        if client is None or not length.isdecimal():
            return self.send_error(400, explain="act?client=ID, with a Content-Length")
        if int(length) > BODY_MAX:
            return self.send_error(413)
        try:
            self.server.act(client, actions(self.rfile.read(int(length)).decode(errors="replace")))
        except ValueError as e:
            return self.send_error(400, explain=str(e))
        except KeyError:
            return self.send_error(409, explain="this page has gone: reload it")
        except RuntimeError as e:
            return self.send_error(503, explain=str(e))
        self.send_response(204)
        self.end_headers()

    def event(self, name, data):
        self.wfile.write(f"event: {name}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n".encode())

    def events(self):
        page, live = self.server, self.server.live
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.end_headers()
        client, state, error = page.connect(), None, live.printed[-1] if live.printed else None
        try:
            self.wfile.write(b"retry: 1000\n\n")
            self.event("hello", {"client": client, "inputs": page.inputs, "detents": DETENTS, "turn_max": TURN_MAX,
                                 "acts_max": ACTS_MAX, "beat_ms": 1000 * BEAT_S})
            while not page.closing.is_set() and live.thread.is_alive() and not page.gone(client):
                if (new := page.state()) != state:
                    self.event("state", state := new)
                if live.printed and live.printed[-1] is not error:
                    error = live.printed[-1]
                    self.event("fault", {"message": f"{type(error).__name__}: {error}"})
                # the page has gone when its end of the connection has closed (it sends nothing else)
                if select.select([self.connection], [], [], POLL_S)[0] and not self.connection.recv(4096):
                    break
        except OSError:                        # the page went while an event was on its way
            pass
        finally:
            with contextlib.suppress(RuntimeError):     # the panel has stopped: nothing is held any more
                page.disconnect(client)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python3 -m sim.page", description=__doc__.split("\n\n")[0])
    parser.add_argument("--port", type=port, default=8000, help="the port to serve on (default 8000)")
    parser.add_argument("--host", default="127.0.0.1",
                        help="the address to serve on (default 127.0.0.1; 0.0.0.0 for a tablet on the network)")
    parser.add_argument("--keyboard", action="store_true", help="the keyboard mode: a keyboard, no joysticks")
    outputs = parser.add_mutually_exclusive_group()
    outputs.add_argument("--uhid", action="store_true", help="also feed a Linux HID device (sim.uhid)")
    outputs.add_argument("--vjoy", action="store_true", help="also feed vJoy devices 1 and 2 on Windows (sim.vjoy)")
    outputs.add_argument("--sendinput", action="store_true",
                         help="with --keyboard: also type the keys into the window in front on Windows")
    parser.add_argument("--open", action="store_true", help="open the page in the default browser")
    args = parser.parse_args(argv)
    live, out = Live(keyboard=args.keyboard), None
    try:
        if args.uhid or args.vjoy or args.sendinput:
            out = Uhid(live) if args.uhid else VJoy(live) if args.vjoy else SendInput(live)
        page = Page(live, (args.host, args.port), out.send if out else None)
    except OSError as e:
        if out:
            out.close()
        if e.errno == errno.EADDRINUSE:
            other = args.port + 1 if args.port < PORT_MAX else args.port - 1
            sys.exit(f"sim.page: port {args.port} is in use: close the other simulator window, or add --port {other}")
        if getattr(e, "winerror", None) == WSAEACCES:
            sys.exit(f"sim.page: Windows gives port {args.port} to no one: another program has it to itself, or it "
                     "is in a range that Windows keeps, as for Hyper-V and WSL (netsh interface ipv4 show "
                     "excludedportrange protocol=tcp lists them). Close that program, or add --port with a port "
                     "outside those ranges")
        sys.exit(f"sim.page: {e}")
    live.start(page.output)
    threading.Thread(target=page.serve_forever, name="page", daemon=True).start()
    on = f" ({out.name}{' on uhid' if args.uhid else ''})" if out else ""
    print(f"The panel{' in keyboard mode' if args.keyboard else ''}{on}: {page.url} (Ctrl-C ends it)", flush=True)
    if args.open:
        webbrowser.open(page.url)
    try:
        while live.thread.is_alive():
            live.thread.join(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        page.stop()
        try:
            live.stop()                        # raises the live panel's fatal error, with its traceback
        finally:
            if out:
                out.close()


if __name__ == "__main__":
    main()
