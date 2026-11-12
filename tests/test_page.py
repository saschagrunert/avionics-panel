"""The panel page's server (sim/page.py), in this process: the live panel SPEED times faster than the wall clock, the
server on a free port, actions posted and the event stream read as the page does. The tests wait for events, not
for times. The stream reads the panel every 10 ms, which at SPEED can miss a 56 ms pulse: the tests read the pulses
from every report (page.sent) and from the stream only states that last."""
import contextlib
import json
import os
import queue
import re
import socket
import threading
import urllib.error
import urllib.request

import pytest

import sim.page
from sim import BM, TILT, key_name
from sim.hardware import RINGS, SWITCHES, keys, make_keys
from sim.live import Live
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
        name, hello = self.next()
        assert name == "hello"
        self.client = hello["client"]

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
def serve(speed=SPEED, keyboard=False):
    live = Live(speed=speed, keyboard=keyboard)
    page = Page(live, forward=lambda device, report: page.sent.append(
        (device, report if keyboard else names(device, report))))
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


def names(device, report):
    return [n for b, n in enumerate(BM.DEVICE[device]) if report[1 + b // 8] >> b % 8 & 1]


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


def test_the_page_and_its_files_are_served(page):
    base = f"http://127.0.0.1:{page.server_address[1]}"
    with urllib.request.urlopen(base + "/", timeout=TIMEOUT_S) as r:     # follows the redirect
        assert r.url == base + "/?sim" and b"sim.js" in r.read()
    for path in ("/geometry.js", "/sim.js"):
        with urllib.request.urlopen(base + path, timeout=TIMEOUT_S) as r:
            assert r.status == 200


def test_keys_and_knobs_reach_the_reports_and_the_lights(page):
    stream = Stream(page)
    first = stream.until(lambda s: s["buttons"].keys() == {"1", "2"})
    assert first["lights"] == {"SHIFT": 0, "UNIT": 0}
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
    stream.until(lambda s: s["lights"] == {"SHIFT": 0, "UNIT": 1})
    # unit 2's COM ⇆ is on device 2
    post(page, "press COM_SWAP", stream.client)
    stream.until(pressed(2, "COM_SWAP"))
    stream.close()


def test_keyboard_mode_shows_the_lights_taking_turns_and_the_shortcut_down():
    with serve(speed=4, keyboard=True) as page:
        stream = Stream(page)
        stream.until(lambda s: s["lights"] == {"SHIFT": 1, "UNIT": 0})             # the start pattern
        stream.until(lambda s: s["lights"] == {"SHIFT": 0, "UNIT": 1})
        stream.until(lambda s: s["buttons"] == {"keyboard": []})                  # the loop's first report
        post(page, "press SHIFT\nrelease SHIFT", stream.client)
        stream.until(lambda s: s["lights"]["SHIFT"] == 1)
        post(page, "press HOME\nrelease HOME", stream.client)
        stream.until(lambda s: s["lights"] == {"SHIFT": 0, "UNIT": 1})
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
