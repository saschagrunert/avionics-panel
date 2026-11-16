"""The panel page's server (sim/page.py), in this process: the live panel SPEED times faster than the wall clock, the
server on a free port, actions posted and the event stream read as the page does. The tests wait for events, not
for times. The stream reads the panel every 10 ms, which at SPEED can miss a 56 ms pulse: the tests read the pulses
from every report (page.sent) and from the stream only states that last."""
import contextlib
import errno
import http.client
import json
import os
import queue
import re
import socket
import threading
import urllib.error
import urllib.request
from types import SimpleNamespace

import pytest

import sim.page
from conftest import load
from mobiflight import profile
from mobiflight.families import FAMILIES
from sim import BM, TILT, buttons_in, key_name
from sim.hardware import RINGS, SWITCHES, keys, make_keys
from sim.live import DETENTS, TURN_MAX, Live
from sim.page import VIEWER, Page, inputs

SPEED = 25
TIMEOUT_S = 5


class Stream:
    """An event stream, read in a thread of its own: next() gives (event, data) in order"""

    def __init__(self, page):
        self.sock = socket.create_connection(page.server_address[:2], TIMEOUT_S)
        self.sock.settimeout(None)             # a quiet stream is no error
        self.sock.sendall(f"GET /sim/events HTTP/1.1\r\nHost: 127.0.0.1:{page.server_address[1]}\r\n\r\n".encode())
        self.events, self.file = queue.Queue(), self.sock.makefile("rb")
        assert self.file.readline().split()[1] == b"200"
        threading.Thread(target=self.read, daemon=True).start()
        name, self.hello = self.next()
        assert name == "hello"
        self.client = self.hello["client"]

    def read(self):
        name = None
        try:
            for line in self.file:
                if line.startswith(b"event: "):
                    name = line[7:].strip().decode()
                elif line.startswith(b"data: "):
                    self.events.put((name, json.loads(line[6:])))
        except OSError:
            pass
        self.events.put(None)                  # the stream has ended

    def next(self):
        return self.events.get(timeout=TIMEOUT_S)

    def until(self, check):
        """The first state event check() accepts"""
        while True:
            event = self.next()
            assert event, "the stream ended"
            if event[0] == "state" and check(event[1]):
                return event[1]

    def close(self):
        self.sock.shutdown(socket.SHUT_RDWR)
        self.sock.close()


@contextlib.contextmanager
def serve(speed=SPEED, keyboard=False, family=None):
    live = Live(speed=speed, keyboard=keyboard)
    page = Page(live, forward=lambda device, report: page.sent.append(
        (device, report if keyboard else buttons_in(device, report))), family=family)
    page.sent = []                             # every report: (device, buttons by name; the keyboard's as sent)
    live.start(page.output)
    threading.Thread(target=page.serve_forever, args=(0.02,), daemon=True).start()
    try:
        yield page
    finally:
        page.stop()
        if live.thread.is_alive():
            live.stop()


@pytest.fixture
def page():
    with serve() as page:
        yield page


def post(page, body, client=None, headers=None, path="/sim/act"):
    """The status of a request: a POST of body, or a GET for None"""
    url = f"http://127.0.0.1:{page.server_address[1]}{path}" + (f"?client={client}" if client else "")
    data = None if body is None else body.encode()
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data, headers or {}), timeout=TIMEOUT_S) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code


def pressed(device, name):
    return lambda state: name in state["buttons"].get(str(device), [])


def test_the_table_names_every_input_once():
    table = inputs()
    names = list(table["keys"].values())
    for knob in table["knobs"].values():
        names += [v for k, v in knob.items() if k != "tilt"] + list(knob.get("tilt", {}).values())
    assert sorted(names) == sorted(SWITCHES + list(RINGS))
    assert table["knobs"]["RANGE"]["tilt"] == TILT and table["keys"]["D→"] == key_name("D→") == "DIRECT"


def test_the_viewer_names_the_rings_as_the_table():
    # sim.js looks a knob's rings up in the table by the names index.html gives them (k.rings)
    with open(os.path.join(VIEWER, "index.html"), encoding="utf-8") as f:
        rings = set(re.findall(r"\b(\w+): \[(?:knob|skirt)\b", f.read()))
    assert rings == {ring for knob in inputs()["knobs"].values() for ring in knob if ring not in ("push", "tilt")}


def viewer(name):
    with open(os.path.join(VIEWER, name), encoding="utf-8") as f:
        return f.read()


def test_the_page_gets_the_programs_numbers_with_hello(page):
    # sim.js copies none of them: it reads each by its name
    hello = Stream(page).hello
    assert {k: v for k, v in hello.items() if k not in ("client", "inputs")} == {
        "build": sim.page.build(), "version": sim.page.version(), "legend": None, "detents": DETENTS,
        "turn_max": TURN_MAX, "acts_max": sim.page.ACTS_MAX, "beat_ms": 1000}
    assert all(re.search(rf"\b{key}\b", viewer("sim.js")) for key in hello)
    assert DETENTS == load("_page_stack", "mech/stack.py").ENC_DETENTS     # a turn of the knob, as built
    assert 2 * sim.page.BEAT_S < sim.page.LEASE_S                          # a beat may be lost


@pytest.mark.parametrize("family", FAMILIES)
def test_the_legend_says_what_every_button_does_in_the_profile(family):
    # every button of both joysticks, once: the label MobiFlight's list shows for its codes, or "nothing" and why
    legend, table = sim.page.legend(family), FAMILIES[family]
    for device in (1, 2):
        assert sorted(legend[device]) == sorted(BM.DEVICE[device]), device
        for button, what in legend[device].items():
            entry = table.DEVICE[device].get(button)
            if entry is None:
                assert what == f"{sim.page.NOTHING} ({table.UNMAPPED[device][button]})", button
            else:
                assert what == profile.label(" ".join(profile.actions(entry).values())) and what, button
    if family == "g1000":
        assert legend[1]["HDG_SYNC"] == "HEADING_BUG_SET" and legend[1]["FREQ_PUSH"] == (
            "nothing (the FREQ knob's mode is the panel's: each mode sends buttons of its own)")


def test_the_page_gets_the_legend_with_hello():
    # by device and button, as the page looks up the button pressed last; sim.js shows it in a line of its own,
    # for the joysticks only
    with serve(family="g1000") as page:
        hello = Stream(page).hello
    assert hello["legend"] == {str(d): what for d, what in sim.page.legend("g1000").items()}
    assert "legend[last[0]][last[1]]" in viewer("sim.js") and "!buttons.keyboard" in viewer("sim.js")


def test_family_takes_a_profile_and_goes_to_the_page(monkeypatch, capsys):
    # a family FAMILIES has, not with the keyboard mode, whose lines show shortcuts, not joystick buttons
    for args in (["--family", "g1001"], ["--keyboard", "--family", "g1000"]):
        with pytest.raises(SystemExit) as refused:
            sim.page.main([*args, "--port", "0"])
        assert refused.value.code == 2 and "argument --family" in capsys.readouterr().err
    families = []

    def page(live, address, forward, family):
        families.append(family)
        raise OSError("stop here")
    monkeypatch.setattr(sim.page, "Page", page)
    for args in ([], ["--family", "cows-da40"]):
        with pytest.raises(SystemExit, match="sim.page: stop here"):
            sim.page.main([*args, "--port", "0"])
    assert families == [None, "cows-da40"]


def test_the_build_names_the_files_the_page_gets(tmp_path):
    # an open page that reconnects to a program serving other files, as after a newer zip was unpacked, reloads
    # when hello names another build (sim.js); the same files are the same build
    (tmp_path / "sim.js").write_text("a")
    builds = [sim.page.build(tmp_path), sim.page.build(tmp_path)]
    (tmp_path / "sim.js").write_text("b")
    builds.append(sim.page.build(tmp_path))
    (tmp_path / "vendor").mkdir()
    (tmp_path / "vendor" / "three.min.js").write_text("")
    builds.append(sim.page.build(tmp_path))
    assert builds[0] == builds[1] and len(set(builds)) == 3


def test_the_version_names_the_commit_of_a_releases_files(tmp_path):
    # firmware/version.py as git archive and the zip fill it in, which the page shows in its last line; a git
    # checkout keeps the placeholder, and the page shows none
    path = tmp_path / "version.py"
    path.write_text('VERSION = "$Format:%cs, %h$"\n')
    assert sim.page.version(path) is None and sim.page.version(tmp_path / "missing.py") is None
    path.write_text('VERSION = "2026-11-14, 5d1c305"\n')
    assert sim.page.version(path) == "2026-11-14, 5d1c305"
    assert "s.textContent = `build ${version}`" in viewer("sim.js")


def test_the_page_asks_for_nothing_that_older_tablets_lack():
    # the newest a script of the page could take for granted: AbortSignal.timeout (Safari 16, Chrome 103), without
    # which no request of the page leaves, and the operators ||=, &&= and ??= (Safari 14, Chrome 85) and ?. and ??
    # (Safari 13.1, Chrome 80), each a syntax error there that stops the whole script
    scripts = viewer("sim.js") + viewer("index.html") + viewer("play.js")
    assert not re.findall(r"AbortSignal\.timeout\(|\?\.(?!\d)|\?\?|\|\|=|&&=", scripts)


def test_the_focus_ring_stands_out_and_the_view_has_a_name():
    # WCAG 2.2 asks 3:1 between a focus indicator and what it lies on, here the view buttons' bar and the page
    # behind it, in the light and in the dark colours
    def luminance(colour):
        linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in (v / 255 for v in colour)]
        return sum(w * c for w, c in zip((0.2126, 0.7152, 0.0722), linear, strict=True))

    def rgb(colour):
        return [int(colour[i:i + 2], 16) for i in (1, 3, 5)]
    page = viewer("index.html")
    schemes = re.findall(r"--bg: (#\w{6});.*?--panel: rgba\((\d+),(\d+),(\d+),([.\d]+)\);.*?--accent: (#\w{6});", page,
                         re.S)
    assert len(schemes) == 2
    for bg, r, g, b, alpha, accent in schemes:
        bar = [float(alpha) * int(c) + (1 - float(alpha)) * under for c, under in zip((r, g, b), rgb(bg), strict=True)]
        for ground in (rgb(bg), bar):
            lighter, darker = sorted((luminance(rgb(accent)), luminance(ground)), reverse=True)
            assert (lighter + 0.05) / (darker + 0.05) >= 3, (accent, ground)
    assert '<canvas id="c" role="img" aria-label="3D model of the Avionics Panel">' in page


def test_the_view_links_to_the_repository_and_to_the_zip_the_docs_give():
    with open(os.path.join(os.path.dirname(VIEWER), "docs", "using", "simulator.md"), encoding="utf-8") as f:
        [zip_link] = re.findall(r"^\[sim-zip\]: (\S+)$", f.read(), re.M)
    # and to the panel that plays in the browser alone (viewer/play.js)
    assert re.findall(r'<a href="([^"]+)"', viewer("index.html")) == ["?play", zip_link.split("/releases/")[0],
                                                                       zip_link]


def test_the_page_and_its_files_are_served(page):
    base = f"http://127.0.0.1:{page.server_address[1]}"
    with urllib.request.urlopen(base + "/", timeout=TIMEOUT_S) as r:     # follows the redirect
        assert r.url == base + "/?sim" and b"sim.js" in r.read()
    for path in ("/geometry.js", "/sim.js"):
        with urllib.request.urlopen(base + path, timeout=TIMEOUT_S) as r:
            assert r.status == 200


def test_head_answers_as_get_does_without_the_body(page):
    # the same status and headers: / goes to the panel, the stream's head opens no stream
    def ask(method, path):
        connection = http.client.HTTPConnection(*page.server_address[:2], timeout=TIMEOUT_S)
        try:
            connection.request(method, path)
            r = connection.getresponse()
            return r.status, r.getheader("Location"), r.getheader("Content-Type"), r.read() if method == "HEAD" else b""
        finally:
            connection.close()
    for path in ("/", "/?play", "/?sim", "/sim.js", "/nothing", "/vendor/"):
        assert ask("HEAD", path) == ask("GET", path), path
    assert ask("HEAD", "/")[:2] == (302, "/?sim")
    # the view's link to the panel that plays in the browser alone, from / or /index.html, plays it here, with the
    # program
    for path in ("/?play", "/index.html?play", "/?play=1&x", "/index.html?x&play"):
        assert ask("HEAD", path)[:2] == (302, "/?sim"), path
    for path in ("/?other", "/index.html", "/?sim&play", "/index.html?sim", "/?player"):
        assert ask("HEAD", path)[0] == 200, path
    assert ask("HEAD", "/sim/events") == (200, None, "text/event-stream; charset=utf-8", b"") and not page.held


def test_a_browser_asks_before_it_reuses_a_file_and_gets_it(page):
    # without Cache-Control it reuses a file for a tenth of its age: days for a zip's files, so the page of an
    # older zip would run against this program. Asked, it gets the file, also when the copy it has kept is the
    # newer one by its time, as after an older zip was unpacked over a newer one's page
    base = f"http://127.0.0.1:{page.server_address[1]}"
    for path in ("/?sim", "/index.html", "/geometry.js", "/sim.js", "/vendor/three.min.js"):
        for kept in ({}, {"If-Modified-Since": "Fri, 01 Jan 2100 00:00:00 GMT"}):
            with urllib.request.urlopen(urllib.request.Request(base + path, headers=kept), timeout=TIMEOUT_S) as r:
                assert r.status == 200 and r.headers.get_all("Cache-Control") == ["no-cache"] and r.read(), path


def test_the_files_go_with_fixed_types_and_the_folders_without_a_listing(page, monkeypatch):
    # the types do not depend on the PC's registry, and nosniff holds the browser to them; a folder is no page. The
    # registry here says text/plain for everything, as Windows' can for .js
    import http.server
    for name in ("guess_file_type", "guess_type"):                  # (guess_file_type from Python 3.13)
        monkeypatch.setattr(http.server.mimetypes, name, lambda *a, **k: ("text/plain", None), raising=False)
    base = f"http://127.0.0.1:{page.server_address[1]}"
    for path, kind in (("/?sim", "text/html"), ("/sim.js", "text/javascript"),
                       ("/vendor/three.min.js", "text/javascript"), ("/fonts/OFL.txt", "text/plain"),
                       ("/fonts/BarlowSemiCondensed-Bold.ttf", "font/ttf")):
        with urllib.request.urlopen(base + path, timeout=TIMEOUT_S) as r:
            assert r.headers.get_content_type() == kind and r.headers["X-Content-Type-Options"] == "nosniff", path
    for path in ("/vendor/", "/fonts/"):
        with pytest.raises(urllib.error.HTTPError) as refused:
            urllib.request.urlopen(base + path, timeout=TIMEOUT_S)
        assert refused.value.code == 404, path


def test_a_page_that_has_gone_is_told_without_a_word_on_the_console(page, capsys):
    # a tablet back from its sleep posts for the page it had: 409, which the page shows, and nothing on the console
    assert post(page, "press AP", "nobody") == 409
    assert capsys.readouterr().err == ""


def test_a_request_that_stalls_is_closed_without_a_word(page, monkeypatch, capsys):
    # half a request would hold its thread of the server for good; a browser's spare connection is one of these
    assert sim.page.Handler.timeout == sim.page.TIMEOUT_S == 10
    monkeypatch.setattr(sim.page.Handler, "timeout", 0.2)      # sooner, for the test
    host = f"Host: 127.0.0.1:{page.server_address[1]}\r\n"
    for request in ("", "GET /sim.js HTTP/1.1\r\n",
                    f"POST /sim/act?client=x HTTP/1.1\r\n{host}Content-Length: 9\r\n\r\npress"):
        with socket.create_connection(page.server_address[:2], TIMEOUT_S) as sock:
            sock.sendall(request.encode())
            assert sock.recv(4096) == b""                  # closed, with no answer
    assert capsys.readouterr().err == ""


def test_keys_and_knobs_reach_the_reports_and_the_lights(page):
    stream = Stream(page)
    first = stream.until(lambda s: s["buttons"].keys() == {"1", "2"})
    assert first["lights"] == {"SHIFT": 0, "UNIT": 0, "FREQ": 0} and first["unit"] == 1 and first["freq"] == "COM"
    # held and let go
    assert post(page, "press AP", stream.client) == 204
    stream.until(pressed(1, "AP"))
    assert post(page, "release AP", stream.client) == 204
    stream.until(lambda s: not s["buttons"].get("1", []))
    # a click with press and release in one request still reaches a key scan (sim.live.PRESS_MIN_MS), and a wheel
    # notch on the ALT/HDG outer ring is one step
    del page.sent[:]
    for body in ("press VS\nrelease VS", "turn ALTHDG_OUTER 1"):
        assert post(page, body, stream.client) == 204
        assert page.live.idle(TIMEOUT_S)
    assert page.sent == [(1, ["VS"]), (1, []), (1, ["ALT_100_UP"]), (1, [])]
    # SHIFT lights up; SHIFT then HOME selects unit 2: the UNIT light on, SHIFT off
    post(page, "press SHIFT\nrelease SHIFT", stream.client)
    stream.until(lambda s: s["lights"]["SHIFT"] == 1)
    post(page, "press HOME\nrelease HOME", stream.client)
    stream.until(lambda s: s["lights"] == {"SHIFT": 0, "UNIT": 1, "FREQ": 0} and s["unit"] == 2)
    # a FREQ push: NAV, the green light on once its count is over; the mode comes from the panel, not from the
    # light, which blinks for ADF and is dark for a count
    post(page, "press FREQ_PUSH\nrelease FREQ_PUSH", stream.client)
    stream.until(lambda s: s["lights"]["FREQ"] == 1 and s["freq"] == "NAV")
    light = page.live.light
    page.live.light = lambda name: 0 if name == "FREQ" else light(name)
    try:
        assert page.state()["lights"]["FREQ"] == 0 and page.state()["freq"] == "NAV"
    finally:
        page.live.light = light
    # unit 2's COM ⇆ is on device 2
    post(page, "press COM_SWAP", stream.client)
    stream.until(pressed(2, "COM_SWAP"))
    stream.close()


def test_a_light_that_is_on_as_code_py_reloads_reads_as_off():
    # a reload starts code.py's globals anew, without LED_DUTY until code.py has set it, while the stream may
    # still read the duty of a light the run before left on: off, not a KeyError that would end the stream
    live = Live()
    page = Page(live)
    try:
        live.leds = [SimpleNamespace(duty_cycle=0x4800), SimpleNamespace(duty_cycle=0), SimpleNamespace(duty_cycle=0)]
        assert "LED_DUTY" not in live.code                     # boot.py's globals, as before code.py starts
        assert page.state() == {"lights": {"SHIFT": 0, "UNIT": 0, "FREQ": 0}, "unit": 1, "freq": "COM",
                                "buttons": {}}
        live.code = {**live.code, "LED_DUTY": (0x4800, 0x5500, 0x7B00)}
        assert page.state()["lights"] == {"SHIFT": 1, "UNIT": 0, "FREQ": 0}
    finally:
        page.server_close()


def test_the_keyboard_line_reads_one_report_as_the_next_replaces_it():
    # output() replaces the last report while the stream reads it: the shortcut and its function come from one
    class Replaced(dict):
        def __getitem__(self, device):
            report = super().__getitem__(device)
            self[device] = later                               # the next report arrives
            return report

    def report(name):
        mods, key = keys.shortcut(1, BM.BUTTON[1][name])
        return bytes((mods, 0, key)) + bytes(5)

    page = Page(Live(keyboard=True))
    try:
        first, later = report("AP"), report("YD")
        page.reports = Replaced({1: first})
        assert page.state()["buttons"] == {"keyboard": [f"AP {make_keys.shortcut_name(first[0], first[2])}"]}
    finally:
        page.server_close()


def test_keyboard_mode_shows_the_lights_taking_turns_and_the_shortcut_down():
    with serve(speed=4, keyboard=True) as page:
        stream = Stream(page)
        stream.until(lambda s: s["lights"] == {"SHIFT": 1, "UNIT": 0, "FREQ": 0})   # the start pattern
        stream.until(lambda s: s["lights"] == {"SHIFT": 0, "UNIT": 1, "FREQ": 0})
        stream.until(lambda s: s["lights"] == {"SHIFT": 0, "UNIT": 0, "FREQ": 1})
        stream.until(lambda s: s["buttons"] == {"keyboard": []})                  # the loop's first report
        post(page, "press SHIFT\nrelease SHIFT", stream.client)
        stream.until(lambda s: s["lights"]["SHIFT"] == 1)
        post(page, "press HOME\nrelease HOME", stream.client)
        stream.until(lambda s: s["lights"] == {"SHIFT": 0, "UNIT": 1, "FREQ": 0})
        # held, so the stream's reads see it (a knob's pulse can fall between them)
        assert post(page, "press COM_SWAP", stream.client) == 204
        name = make_keys.shortcut_name(*keys.shortcut(2, BM.BUTTON[2]["COM_SWAP"]))
        stream.until(lambda s: s["buttons"] == {"keyboard": [f"COM_SWAP (unit 2) {name}"]})
        assert post(page, "release COM_SWAP", stream.client) == 204
        stream.until(lambda s: s["buttons"] == {"keyboard": []})
        stream.close()
        assert page.live.idle(TIMEOUT_S) and page.sent[-1] == (1, bytes(keys.REPORT))


@pytest.mark.parametrize("args, message", [
    (["--sendinput"], "SendInput takes the keyboard mode's keys: add --keyboard"),
    (["--keyboard", "--vjoy"], "vJoy takes the joysticks: the keyboard mode goes to Windows through --sendinput"),
])
def test_an_output_the_mode_has_not_is_refused(args, message):
    with pytest.raises(SystemExit, match=f"sim.page: {message}"):
        sim.page.main([*args, "--port", "0"])


def test_a_port_that_is_taken_is_named_with_the_ways_out(page, monkeypatch):
    # another program listens on it, or a simulator that feeds no vJoy device (a second one stops at vJoy first)
    port = page.server_address[1]
    with pytest.raises(SystemExit, match=f"sim.page: port {port} is in use: close the other simulator window, or "
                                         f"add --port {port + 1}$"):
        sim.page.main(["--port", str(port)])

    def refuse(error, winerror=None):
        def page(*args):
            if winerror:
                error.winerror = winerror
            raise error
        monkeypatch.setattr(sim.page, "Page", page)
    refuse(OSError(errno.EADDRINUSE, "Address already in use"))    # no port follows 65535
    with pytest.raises(SystemExit, match="sim.page: port 65535 is in use: .*, or add --port 65534$"):
        sim.page.main(["--port", "65535"])
    # Windows' errno 13 with winerror 10013: a port that a program has to itself, or one in a range Windows keeps,
    # where the next port is no way out
    refuse(PermissionError(13, "An attempt was made to access a socket in a way forbidden"), 10013)
    with pytest.raises(SystemExit, match="sim.page: Windows gives port 8000 to no one: another program has it to "
                                         "itself, or it is in a range that Windows keeps, .* add --port with a port "
                                         "outside those ranges$"):
        sim.page.main([])
    refuse(PermissionError(13, "Permission denied"))               # a port under 1024 on Linux
    with pytest.raises(SystemExit, match=r"sim.page: \[Errno 13\] Permission denied$"):
        sim.page.main(["--port", "80"])


def test_a_second_ctrl_c_while_it_ends_still_lets_go_of_the_output(monkeypatch):
    # the first Ctrl-C ends the wait, a second one comes while the page stops: the panel stops all the same, and
    # then the output lets go, so nothing is sent to it after that
    lives, closed = [], []

    class Output:
        name = "an output"

        def __init__(self, live):
            pass

        def send(self, device, report):
            pass

        def close(self):
            closed.append(lives[0].thread.is_alive())          # whether the panel still runs

    class Interrupted(Live):
        def start(self, output):
            super().start(output)
            lives.append(self)
            join = self.thread.join

            def ctrl_c(*_):                    # the first, while main() waits
                self.thread.join = join
                raise KeyboardInterrupt
            self.thread.join = ctrl_c

    stop = Page.stop

    def stopping(page):                        # the second
        stop(page)
        raise KeyboardInterrupt
    monkeypatch.setattr(sim.page, "VJoy", Output)
    monkeypatch.setattr(sim.page, "Live", Interrupted)
    monkeypatch.setattr(Page, "stop", stopping)
    try:
        with pytest.raises(KeyboardInterrupt):
            sim.page.main(["--vjoy", "--port", "0"])
    finally:
        lives[0].stop()
    assert closed == [False]


def test_an_answer_the_page_gave_up_on_goes_without_a_traceback(page, capsys):
    # a request the page gave up on while this program stalled: its answer finds the connection closed
    def fail(error):
        try:
            raise error
        except Exception:
            page.handle_error(None, ("127.0.0.1", 1))
    fail(BrokenPipeError(errno.EPIPE, "Broken pipe"))
    fail(ConnectionResetError(errno.ECONNRESET, "Connection reset by peer"))
    assert capsys.readouterr().err == ""
    for error in (OSError(errno.EBADF, "Bad file descriptor"), ValueError("a bug")):     # anything else is one
        fail(error)
        assert f"{type(error).__name__}: " in capsys.readouterr().err


@pytest.mark.parametrize("port", ["65536", "70000", "-1", "8000.5", "http"])
def test_a_port_that_is_none_is_refused_before_anything_starts(port, capsys):
    # by argparse (exit status 2), with its usage: no output is acquired yet
    with pytest.raises(SystemExit) as refused:
        sim.page.main(["--vjoy", "--port", port])
    assert refused.value.code == 2 and f"argument --port: invalid port value: '{port}'" in capsys.readouterr().err


def test_the_shift_light_pulses_in_its_last_second():
    # slower than the others: the pulse's 125 ms dim and bright phases stay longer than the stream's 10 ms reads
    with serve(speed=4) as page:
        stream = Stream(page)
        post(page, "press SHIFT\nrelease SHIFT", stream.client)
        seen = [stream.until(lambda s: s["lights"]["SHIFT"] == 1)["lights"]["SHIFT"]]
        while seen[-1]:
            seen.append(stream.until(lambda s, last=seen[-1]: s["lights"]["SHIFT"] != last)["lights"]["SHIFT"])
        stream.close()
    assert seen[:2] == [1, 0.25] and set(seen) == {1, 0.25, 0}


def test_wrong_actions_are_refused_and_none_runs(page):
    stream = Stream(page)
    for body in ("press AP\ntap AP", "press AP1", "turn FREQ_INNER 1 0", "turn FREQ_INNER x", "release",
                 "turn FREQ_INNER 31", "press AP\nturn FREQ_INNER -31", "turn FREQ_INNER --3",
                 "turn FREQ_INNER 1\n" * (sim.page.ACTS_MAX + 1)):
        assert post(page, body, stream.client) == 400
    assert post(page, "press AP") == 400                       # no client
    with socket.create_connection(page.server_address[:2], TIMEOUT_S) as sock:   # chunked: not an empty heartbeat
        sock.sendall(f"POST /sim/act?client={stream.client} HTTP/1.1\r\nHost: 127.0.0.1:{page.server_address[1]}"
                     "\r\nTransfer-Encoding: chunked\r\n\r\n8\r\npress AP\r\n0\r\n\r\n".encode())
        assert sock.recv(4096).startswith(b"HTTP/1.0 411 ")
    assert post(page, "press AP", "nobody") == 409
    assert post(page, "turn FREQ_INNER -30", stream.client) == 204
    assert not page.held[stream.client]
    stream.close()


def test_only_its_own_page_drives_the_panel(page):
    stream, port = Stream(page), page.server_address[1]
    assert stream.client != Stream(page).client and len(stream.client) >= 20     # not to be guessed
    for host, status in ((f"rebound.example:{port}", 403), (f"127.0.0.1:{port}", 200)):     # HEAD too
        head = urllib.request.Request(f"http://127.0.0.1:{port}/?sim", headers={"Host": host}, method="HEAD")
        try:
            with urllib.request.urlopen(head, timeout=TIMEOUT_S) as r:
                assert r.status == status
        except urllib.error.HTTPError as e:
            assert e.code == status
    # another site's page (Origin, Sec-Fetch-Site: also the page framed by it), or one under a name that site
    # points at this machine (DNS rebinding)
    for headers in ({"Host": f"rebound.example:{port}"}, {"Host": "127.0.0.1:1"}, {"Origin": "http://evil.example"},
                    {"Origin": "null"}, {"Sec-Fetch-Site": "cross-site"}, {"Sec-Fetch-Site": "same-site"}):
        assert post(page, "press AP", stream.client, headers) == 403
        assert post(page, None, None, headers, "/sim/events") == 403
    # the page itself, also from a tablet on the network
    lan = f"192.168.1.20:{port}"
    for headers in ({"Origin": f"http://127.0.0.1:{port}", "Sec-Fetch-Site": "same-origin"},
                    {"Host": f"localhost:{port}"}, {"Host": lan, "Origin": f"http://{lan}"}, {"Host": f"[::1]:{port}"}):
        assert post(page, "", stream.client, headers) == 204
    assert not page.held[stream.client] and not any(page.state()["buttons"].values())
    # and no other site may frame it, nor its error pages
    for path in ("/", "/?sim", "/nothing"):
        try:
            response = urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=TIMEOUT_S)
        except urllib.error.HTTPError as e:
            response = e
        with response:
            assert response.headers["X-Frame-Options"] == "DENY"
            assert response.headers["Content-Security-Policy"] == "frame-ancestors 'none'"
    stream.close()


def test_another_site_may_link_to_the_page_but_not_frame_or_use_it(page):
    stream = Stream(page)
    link = {"Sec-Fetch-Site": "cross-site", "Sec-Fetch-Mode": "navigate", "Sec-Fetch-Dest": "document"}
    for site in ("cross-site", "same-site"):
        assert post(page, None, None, {**link, "Sec-Fetch-Site": site}, "/") == 200   # via /?sim
        # framed, or the page's files loaded into another site's page
        for mode, dest in (("navigate", "iframe"), ("no-cors", "script"), ("cors", "empty")):
            headers = {"Sec-Fetch-Site": site, "Sec-Fetch-Mode": mode, "Sec-Fetch-Dest": dest}
            assert post(page, None, None, headers, "/?sim") == 403
        # the API, also as a navigation
        assert post(page, None, None, {**link, "Sec-Fetch-Site": site}, "/sim/events") == 403
        assert post(page, "press AP", stream.client, {**link, "Sec-Fetch-Site": site}) == 403
        assert post(page, "press AP", stream.client, {"Sec-Fetch-Site": site, "Sec-Fetch-Mode": "cors"}) == 403
    assert not page.held[stream.client]
    stream.close()


def test_the_host_is_an_address_or_localhost_with_the_port():
    assert all(sim.page.local(host, 8000) for host in ("127.0.0.1:8000", "localhost:8000", "[::1]:8000",
                                                       "192.168.1.20:8000"))
    assert sim.page.local("10.0.0.2", 80) and sim.page.local("[fe80::1]", 80)    # a browser leaves port 80 out
    assert not any(sim.page.local(host, 8000) for host in ("127.0.0.1", "localhost:80", "mypc.local:8000",
                                                           "localhost.evil.example:8000", "127.0.0.1.nip.io:8000",
                                                           "[::1]", "", ":8000"))


def test_served_to_the_network_on_windows_it_names_firewall_bat(tmp_path):
    # Windows' firewall keeps a tablet out until firewall.bat lets the zip's python.exe in (windows/firewall.bat):
    # the hint is for the zip's Python, with firewall.bat beside its folder
    zipped = tmp_path / "python" / "python.exe"
    zipped.parent.mkdir()
    (tmp_path / "firewall.bat").write_text("")
    assert "run the zip's firewall.bat as administrator" in sim.page.firewall("0.0.0.0", "win32", zipped)
    assert "firewall.bat" in sim.page.firewall("192.168.1.20", "win32", zipped)
    assert sim.page.firewall("127.0.0.1", "win32", zipped) is None
    assert sim.page.firewall("0.0.0.0", "linux", zipped) is None
    assert sim.page.firewall("0.0.0.0", "win32", tmp_path / "py" / "bin" / "python.exe") is None   # a Python of its own


def test_a_switch_two_pages_hold_stays_held_until_both_let_go(page):
    a, b = Stream(page), Stream(page)
    post(page, "press AP", a.client)
    post(page, "press AP", b.client)
    a.close()
    b.until(pressed(1, "AP"))
    assert page.live.idle(TIMEOUT_S) and "AP" in page.state()["buttons"][1]        # B still holds it
    post(page, "release AP", b.client)
    b.until(lambda s: not s["buttons"].get("1", []))
    b.close()


@pytest.mark.parametrize("length, status", [("abc", 400), ("-1", 400), ("70000", 413)])
def test_a_wrong_length_is_refused(page, length, status):
    stream = Stream(page)
    with socket.create_connection(page.server_address[:2], TIMEOUT_S) as sock:
        sock.sendall(f"POST /sim/act?client={stream.client} HTTP/1.1\r\nHost: 127.0.0.1:{page.server_address[1]}\r\n"
                     f"Content-Length: {length}\r\n\r\npress AP".encode())
        with sock.makefile("rb") as response:              # all of it: the server closes the connection after
            assert response.read().split()[1] == str(status).encode()
    assert not page.held[stream.client]
    stream.close()


def test_a_page_that_goes_lets_go_of_what_it_holds(page):
    watch, gone = Stream(page), Stream(page)
    post(page, "press AP\npress RANGE_COM\npress " + TILT["UP"], gone.client)
    watch.until(lambda s: {"AP", "PAN_UP"} <= set(s["buttons"].get("1", [])))
    assert page.held[gone.client] == {"AP", "RANGE_COM", "RANGE_A"}
    gone.close()
    watch.until(lambda s: not s["buttons"].get("1", []))
    assert gone.client not in page.held
    assert post(page, "press AP", gone.client) == 409
    watch.close()


def test_a_page_that_stops_posting_lets_go_too(page, monkeypatch):
    # a tablet that drops off the network closes nothing: its lease runs out
    monkeypatch.setattr(sim.page, "LEASE_S", 0.3)
    stream = Stream(page)
    post(page, "press AP", stream.client)
    assert page.live.idle(TIMEOUT_S) and "AP" in page.state()["buttons"][1]
    while stream.next():                       # the server ends the stream
        pass
    assert page.live.idle(TIMEOUT_S) and not page.state()["buttons"][1]
    assert stream.client not in page.held


def test_a_firmware_error_is_reported_and_code_py_reloads(page):
    stream = Stream(page)
    # code.py's loop runs, so its panel is there: on a busy PC the stream can be up before code.py has made it
    stream.until(lambda s: s["buttons"].keys() == {"1", "2"})

    def bug(board):                            # this run's panel fails on the next detent
        def turn(*_):
            raise ValueError("bug")
        board.code["panel"].turn = turn
        board.turn("ALTHDG_OUTER", 1)
    page.live.do(bug)
    page.live.act("wait", 2100)                # code.py waits 2 s and reloads: a key held then stays silent
    while (event := stream.next())[0] != "fault":
        pass
    assert event[1] == {"message": "ValueError: bug"}
    # after the reload, a key works again
    post(page, "press AP", stream.client)
    stream.until(pressed(1, "AP"))
    assert len(page.live.reloads) == 1
    stream.close()


def test_a_stream_on_a_socket_numbered_past_1023_works(page):
    # select.select() takes no socket numbered 1024 or more on Linux, which a program with many files open gives
    # out: the stream still tells the page what changes, and sees it go
    resource = pytest.importorskip("resource")
    soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    if hard != resource.RLIM_INFINITY and hard < 2048:
        pytest.skip(f"{hard} files open at most")
    if soft != resource.RLIM_INFINITY and soft < 2048:
        resource.setrlimit(resource.RLIMIT_NOFILE, (2048, hard))
    taken = []                                 # every number below 1024, so the stream's sockets get higher ones
    try:
        while (fd := os.open(os.devnull, os.O_RDONLY)) < 1024:
            taken.append(fd)
        os.close(fd)
        stream = Stream(page)
        assert stream.sock.fileno() >= 1024
        assert post(page, "press AP", stream.client) == 204
        stream.until(pressed(1, "AP"))
        stream.close()
        assert page.live.idle(TIMEOUT_S)
        for _ in range(500):                   # the server sees the page go, and lets go of what it held
            if stream.client not in page.held:
                break
            page.closing.wait(0.01)
        assert stream.client not in page.held and not page.state()["buttons"][1]
    finally:
        for fd in taken:
            os.close(fd)
        resource.setrlimit(resource.RLIMIT_NOFILE, (soft, hard))


def test_the_stream_ends_when_the_panel_stops(page):
    stream, client = Stream(page), page.connect()      # the second without a stream, which would end now

    def fail(board):
        raise OSError("gone")
    page.live.do(fail)
    while stream.next():
        pass
    assert post(page, "press AP", client) == 503
    with pytest.raises(OSError, match="gone"):
        page.live.stop()
