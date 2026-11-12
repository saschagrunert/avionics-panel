"""The live panel (sim/live.py) in the browser: serves the 3D view (viewer/) with the panel playable in it, and an
API for it. Python's standard library only.

    python3 -m sim.page [--uhid] [--port N] [--host ADDR]

prints the page's URL (http://127.0.0.1:8000/?sim): the ?sim makes the viewer play the panel (viewer/sim.js).
With --uhid the reports also go to a Linux HID device, as with `python3 -m sim.uhid`.

The API, under /sim/:

- GET events: one Server-Sent Events stream per page. `hello` first, with the page's client ID (a secret: only
  the page can read it) and the firmware names of the caps and knobs geometry.js draws (inputs()), then `state`
  whenever the lights or the buttons change (the lights are read every POLL_S, so the SHIFT light's 125 ms pulse
  keeps its rhythm), and `fault` for an error in code.py's loop, which then reloads (not `error`: EventSource has
  an event of that name).
- POST act?client=ID: actions, one per line, run at once and in order: `press NAME`, `release NAME` (a key, push
  or RANGE switch) and `turn RING DETENTS` (all in the same ms, sim.live.TURN_MAX at most). Nothing paces them: a
  fast wheel is a fast turn. An empty one only says that the page is still there. 204, or 400 with the reason
  (nothing runs), 409 for a client that has gone, 413 for a body over BODY_MAX.

A page that goes lets go of what it holds, unless another page holds it too: when its stream closes, and when it
has not posted for LEASE_S (a tablet that drops off the network closes nothing; the page posts every second).
Only this server's own page drives the panel: a request with a Host other than an IP address or localhost with
the server's port (DNS rebinding), from another Origin, or from another site (Sec-Fetch-Site) gets 403, except a
link to the page itself from another site; no other site may frame the page (clickjacking), and none can read a
client ID.

A fatal error of the live panel ends the program with its traceback; the page then says it is disconnected.
"""
import argparse
import contextlib
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
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from sim import BM, LIGHTS, TILT, key_name
from sim.live import USAGE, Live, parse
from sim.uhid import Uhid

VIEWER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "viewer")
GEOMETRY = os.path.join(VIEWER, "geometry.js")
POLL_S = 0.01        # the stream reads the lights and the reports this often
LEASE_S = 3          # a page that has not posted for this long has gone
BODY_MAX = 65536     # bytes of an act request at most
ACTS_MAX = 64        # actions in one request at most: a page sends a few, so none can queue minutes of changes
ACTS = {"press": USAGE["press"], "release": USAGE["release"], "turn": "turn RING DETENTS"}   # what act takes


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
        buttons by name"""
        live, lights = self.live, {}
        for i, name in enumerate(LIGHTS):
            duty = live.light(name)
            lights[name] = round(duty / live.code["LED_DUTY"][i], 3) if duty else 0
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
    def log_request(self, *args):
        pass

    def end_headers(self):
        self.send_header("X-Frame-Options", "DENY")              # no other site frames the page (clickjacking)
        self.send_header("Content-Security-Policy", "frame-ancestors 'none'")
        super().end_headers()

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
        self.send_error(403, explain="open the page by this computer's IP address or localhost, as sim.page prints it")
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
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        client, state, error = page.connect(), None, live.printed[-1] if live.printed else None
        try:
            self.wfile.write(b"retry: 1000\n\n")
            self.event("hello", {"client": client, "inputs": page.inputs})
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
    parser.add_argument("--port", type=int, default=8000, help="the port to serve on (default 8000)")
    parser.add_argument("--host", default="127.0.0.1",
                        help="the address to serve on (default 127.0.0.1; 0.0.0.0 for a tablet on the network)")
    parser.add_argument("--uhid", action="store_true", help="also feed a Linux HID device (sim.uhid)")
    args = parser.parse_args(argv)
    live, uhid = Live(), None
    try:
        if args.uhid:
            uhid = Uhid(live)
        page = Page(live, (args.host, args.port), uhid.send if uhid else None)
    except OSError as e:
        if uhid:
            uhid.close()
        sys.exit(f"sim.page: {e}")
    live.start(page.output)
    threading.Thread(target=page.serve_forever, name="page", daemon=True).start()
    print(f"The panel{f' ({uhid.name} on uhid)' if uhid else ''}: {page.url} (Ctrl-C ends it)", flush=True)
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
            if uhid:
                uhid.close()


if __name__ == "__main__":
    main()
