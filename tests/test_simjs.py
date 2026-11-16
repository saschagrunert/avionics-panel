"""The panel page's script (viewer/sim.js) in a browser, against the real `python3 -m sim.page`: what a wheel, a
finger and a refused request make the page send, and the page's alert when sim.js is missing (a server that
answers 404 for it) or its playPanel throws. And the page that plays the panel alone (?play, viewer/play.js), served
as plain files laid out as the Pages workflow lays them out, with the vendored MicroPython running the firmware's
panel.py in the browser: what the lights and lines show for keys and knobs, and that the plain view loads none of
it. The page's requests are read in the page (a wrapper round its fetch,
which can also refuse one), and the input is the browser's own (Chrome's DevTools protocol), at the screen point of
a knob or cap that the page's camera gives.

The browser comes from Playwright: Playwright for Python where it is installed, as in the firmware shell on Linux
(nix/shells.nix), else Playwright for Node through `node` (require('playwright')). Without either, or without its
Chromium, the tests skip; REQUIRE_BROWSER=1 turns that skip into a failure."""
import contextlib
import ctypes
import functools
import http.server
import json
import os
import re
import selectors
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TIMEOUT_S = 30       # a wait for the page: long, as build.sh runs the tests beside the solids, board checks and renders
CALL_S = 30          # a call to the browser (the start, an evaluate, an input event) answers within this, or fails
VIEWPORT = {"width": 480, "height": 360}       # small: software WebGL draws few pixels faster
ARGS = ["--enable-unsafe-swiftshader", "--use-angle=swiftshader"]     # WebGL in software, without a GPU
# without WAYLAND_DISPLAY: on a Wayland desktop SwiftShader asks Vulkan for a Wayland surface it lacks, and WebGL
# fails even headless
ENV = {k: v for k, v in os.environ.items() if k != "WAYLAND_DISPLAY"}
GAP_S = 0.4          # longer than sim.js's WHEEL_GAP_MS: the next wheel event starts a new spin
# before the page's scripts: the actions the page sends, by client ([client, line]; play.js's engine takes them as
# client "browser"), the states the engine gives, the intervals of the timers started, the WebAssembly modules
# started (a count), the statuses that refuse the next requests with actions, without the server (__refuse; an
# empty beat goes through), and the view index.html hands sim.js (V); __playThrows, set before it, makes playPanel
# throw, and __fail, a RegExp, fails the requests for the URLs it matches as a network error does
INIT = r"""
localStorage.setItem('avionics-panel-quiet', '1');      // the sound off: no audio device to start
window.__acts = []; window.__refuse = []; window.__states = []; window.__intervals = []; window.__wasm = 0;
for (const name of ['instantiate', 'instantiateStreaming']) {       // the WebAssembly modules started
  const start = WebAssembly[name].bind(WebAssembly);
  WebAssembly[name] = (...args) => { window.__wasm++; return start(...args); };
}
const fetched = window.fetch.bind(window), every = window.setInterval.bind(window);
window.setInterval = (f, ms) => { window.__intervals.push(ms); return every(f, ms); };
window.fetch = (url, options) => {
  // a request that fails as a network error does (__fail, a RegExp of URLs)
  if (window.__fail && window.__fail.test(String(url))) return Promise.reject(new TypeError('Failed to fetch'));
  const act = String(url).match(/sim\/act\?client=(.*)$/), body = String(options && options.body || '');
  if (act) {
    for (const line of body.split('\n')) if (line) window.__acts.push([act[1], line]);
    if (body && window.__refuse.length) return Promise.resolve(new Response('', { status: window.__refuse.shift() }));
  }
  return fetched(url, options);
};
let engine;
Object.defineProperty(window, 'playEngine', { configurable: true, get: () => engine,
  set: f => { engine = g => {
    const e = f(g), act = e.act, open = e.open;
    e.act = lines => { for (const l of lines) window.__acts.push(['browser', l]); act(lines); };
    e.open = h => open({ ...h, state: st => { window.__states.push(st); h.state(st); } });
    return e;
  }; } });
let play;
Object.defineProperty(window, 'playPanel', { configurable: true, get: () => play,
  set: f => { play = V => { window.__V = V; if (window.__playThrows) throw new Error('a test'); return f(V); }; } });
// the screen point [x, y] px of a point round a knob (V.knobs' key): r mm from its axis at deg degrees (0 to the
// right, 90 towards the user), at the height of its inner knob's top, its outer ring's top or halfway between
window.__knob = (knob, r, deg, top) => {
  const V = window.__V, G = V.G, k = V.knobs[knob], a = deg * Math.PI / 180;
  const h = G.plate.z1 + { inner: G.inner_knob.z1, outer: G.outer_knob.z1,
                           pick: (G.inner_knob.z1 + G.outer_knob.z1) / 2 }[top];
  return window.__screen(V.assembly.localToWorld(new THREE.Vector3(V.px(k.x) + r * Math.cos(a), h,
                                                                   V.pz(k.y) + r * Math.sin(a))));
};
window.__cap = label => {
  const top = window.__V.keys.find(k => k.label === label).meshes[1];
  return window.__screen(top.getWorldPosition(new THREE.Vector3()));
};
window.__screen = p => {
  const V = window.__V, box = V.canvas.getBoundingClientRect();
  p.project(V.camera);
  return [box.left + (p.x + 1) / 2 * box.width, box.top + (1 - p.y) / 2 * box.height];
};
"""
# `python3 -m sim.page`, but 404 for sim.js
NO_SIM_JS = r"""
from urllib.parse import urlsplit
import sim.page as page
get = page.Handler.do_GET
page.Handler.do_GET = lambda self, head=False: (self.send_error(404) if urlsplit(self.path).path == "/sim.js"
                                                else get(self, head))
page.main()
"""
# Playwright for Node, run by the tests as a server of their own: argv[1] the options, then one JSON command a
# line on stdin, ["evaluate", expression] or ["cdp", method, params], and its {result} or {error} on stdout; a page
# that crashes ends it with {crashed}
NODE = r"""
const { chromium } = require('playwright');
const readline = require('readline');
(async () => {
  const { url, init, viewport, args } = JSON.parse(process.argv[1]);
  let browser;
  try { browser = await chromium.launch({ args }); }
  catch (e) { console.log(JSON.stringify({ missing: String(e) })); return; }
  const context = await browser.newContext({ hasTouch: true, reducedMotion: 'reduce', viewport });
  await context.addInitScript(init);
  const page = await context.newPage(), cdp = await context.newCDPSession(page);
  page.on('crash', () => { console.log(JSON.stringify({ crashed: true })); process.exit(1); });
  await page.goto(url);
  console.log(JSON.stringify({ ready: true }));
  for await (const line of readline.createInterface({ input: process.stdin })) {
    const [op, ...rest] = JSON.parse(line);
    try {
      const result = op === 'evaluate' ? await page.evaluate(rest[0]) : await cdp.send(rest[0], rest[1]);
      console.log(JSON.stringify({ result: result === undefined ? null : result }));
    } catch (e) { console.log(JSON.stringify({ error: String(e) })); }
  }
  process.exit(0);                     // Playwright kills the browser as node exits: quicker than browser.close()
})();
"""


def missing(why):
    if os.environ.get("REQUIRE_BROWSER"):
        pytest.fail(f"{why}, and REQUIRE_BROWSER is set")
    pytest.skip(why)


class Browser:
    """What both kinds share: each call to the browser fails, rather than waits for ever, when the page crashes or
    the browser has not answered within CALL_S. Either kills the browser and Playwright, which fails the call:
    Playwright fails the calls a crashed page has on its own session, but not those on a CDP session (an input
    event the page crashed in waits for its answer for ever, even once the browser is gone), and an evaluate has no
    timeout."""
    crashed = killed = False

    def call(self, what, f, *args):
        watchdog = threading.Timer(CALL_S, self.hung)
        watchdog.start()
        try:
            return f(*args)
        except Exception:
            if self.crashed:
                pytest.fail(f"the page crashed: {what}")
            if self.killed:
                pytest.fail(f"the browser did not answer within {CALL_S} s: {what}")
            raise
        finally:
            watchdog.cancel()

    def hung(self):
        self.killed = True
        self.kill()

    def crash(self, *_):
        self.crashed = True
        self.kill()

    def evaluate(self, expression):
        return self.call(expression, self._evaluate, expression)

    def cdp(self, method, params):
        return self.call(method, self._cdp, method, params)


class PythonPlaywright(Browser):
    def __init__(self, url, init):
        from playwright.sync_api import Error, sync_playwright
        self.playwright = sync_playwright().start()
        try:
            self.browser = self.playwright.chromium.launch(args=ARGS, env=ENV, timeout=CALL_S * 1000)
        except Error as e:
            self.playwright.stop()
            missing(f"Playwright for Python has no Chromium: {str(e).splitlines()[0]}")
        info = self.browser.new_browser_cdp_session().send("SystemInfo.getProcessInfo")["processInfo"]
        self.pid = next(p["id"] for p in info if p["type"] == "browser")
        self.driver = self.playwright._impl_obj._connection._transport._proc.pid     # Playwright's node
        try:
            self.call(f"the page at {url}", self._open, url, init)
        except BaseException:
            self.close()
            raise

    def _open(self, url, init):
        context = self.browser.new_context(has_touch=True, reduced_motion="reduce", viewport=VIEWPORT)
        context.add_init_script(init)
        self.page = context.new_page()
        self.page.on("crash", self.crash)
        self.session = context.new_cdp_session(self.page)
        self.page.goto(url, timeout=CALL_S * 1000)

    def _evaluate(self, expression):
        return self.page.evaluate(expression)

    def _cdp(self, method, params):
        return self.session.send(method, params)

    def kill(self, *pids):
        for pid in pids or (self.pid, self.driver):     # the driver's end fails the calls waiting on the CDP session
            with contextlib.suppress(OSError):
                os.kill(pid, getattr(signal, "SIGKILL", signal.SIGTERM))

    def close(self):
        # ended at once: browser.close() waits seconds for the page to unload, as Playwright for Node's would
        self.kill(self.pid)
        self.playwright.stop()


class NodePlaywright(Browser):
    def __init__(self, url, node, init):
        options = {"url": url, "init": init, "viewport": VIEWPORT, "args": ARGS}
        self.process = subprocess.Popen([node, "-e", NODE, json.dumps(options)], stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE, text=True, cwd=ROOT, env=ENV)
        try:
            first = self.call(f"the page at {url}", self._answer)
        except BaseException:
            self.close()
            raise
        if "missing" in first:
            self.close()
            missing(f"Playwright for Node has no Chromium: {first['missing'].splitlines()[0]}")

    def _answer(self):
        answer = json.loads(self.process.stdout.readline() or '{"error": "node ended"}')
        if "crashed" in answer:
            self.crashed = True
        if "error" in answer or "crashed" in answer:
            raise RuntimeError(answer.get("error", "the page crashed"))
        return answer

    def _send(self, *command):
        self.process.stdin.write(json.dumps(command) + "\n")
        self.process.stdin.flush()
        return self._answer()["result"]

    def _evaluate(self, expression):
        return self._send("evaluate", expression)

    def _cdp(self, method, params):
        return self._send("cdp", method, params)

    def kill(self):
        self.process.kill()

    def close(self):
        with contextlib.suppress(OSError):
            self.process.stdin.close()
        try:
            self.process.wait(TIMEOUT_S)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait()


def browser(url, init):
    try:
        import playwright.sync_api  # noqa: F401
    except ImportError:
        pass
    else:
        return PythonPlaywright(url, init)
    node = shutil.which("node")
    if node and subprocess.run([node, "-e", "require('playwright')"], cwd=ROOT, capture_output=True).returncode == 0:
        return NodePlaywright(url, node, init)
    return missing("no Playwright: neither playwright for Python nor require('playwright') in node")


def _ends_with_pytest():
    """In the server, before it starts (Linux): a SIGTERM once pytest is gone, also when pytest was killed and
    stopped nothing (a CI job cancelled, timeout)"""
    ctypes.CDLL(None, use_errno=True).prctl(1, signal.SIGTERM)       # PR_SET_PDEATHSIG


# the view is up and the program has said which devices there are
READY = "window.__V && !document.querySelector('.fail') && !!document.querySelector('.sim:not(.none)')"


class Panel:
    """The page in a browser, served by `python3 -m sim.page` (or by server, python3 -c code), or the page at url of
    another server, once ready is true"""

    def __init__(self, init=INIT, server=None, ready=READY, url=None):
        self.server = None
        if url:
            self.url = url
        else:
            self.start(server)
        try:
            self.browser = browser(self.url, init)
            self.until(ready)
        except BaseException:
            self.stop()
            raise

    def start(self, server):
        self.errors = tempfile.TemporaryFile("w+")  # noqa: SIM115 (closed in stop(): the server writes it until then)
        run = ["-c", server] if server else ["-m", "sim.page"]
        self.server = subprocess.Popen([sys.executable, *run, "--port", "0"], cwd=ROOT, text=True,
                                       stdout=subprocess.PIPE, stderr=self.errors,
                                       preexec_fn=_ends_with_pytest if sys.platform.startswith("linux") else None)
        with selectors.DefaultSelector() as wait:                     # its first line, the URL, or a fail in time
            wait.register(self.server.stdout, selectors.EVENT_READ)
            line = self.server.stdout.readline() if wait.select(TIMEOUT_S) else ""
        found = re.search(r"http://\S+", line)
        if not found:
            self.server.kill()
            self.server.wait(TIMEOUT_S)
            self.errors.seek(0)
            pytest.fail(f"sim.page did not start: {line!r}\n{self.errors.read()}")
        self.url = found[0]

    def stop(self):
        if getattr(self, "browser", None):
            self.browser.close()
        if not self.server:
            return
        self.server.terminate()
        self.server.communicate(timeout=TIMEOUT_S)
        self.errors.close()

    def evaluate(self, expression):
        return self.browser.evaluate(expression)

    def until(self, expression):
        end = time.monotonic() + TIMEOUT_S
        while not (value := self.evaluate(expression)):
            assert time.monotonic() < end, f"not within {TIMEOUT_S} s: {expression}"
            time.sleep(0.02)
        return value

    def acts(self, since=0):
        """[client, line] of every action the page has sent since the since-th"""
        return self.evaluate(f"window.__acts.slice({since})")

    def mark(self):
        return self.evaluate("window.__acts.length")

    def lines(self, since):
        """The lines the page sent since a mark(), once it has been quiet for a moment and drawn what they changed
        (settle())"""
        end = time.monotonic() + TIMEOUT_S
        while True:
            before = self.acts(since)
            time.sleep(0.15)
            if self.acts(since) == before:
                self.settle()
                return [line for _, line in before]
            assert time.monotonic() < end, f"still sending after {TIMEOUT_S} s: {before}"

    def settle(self):
        """Waits until the page draws its frames at once again. Software WebGL takes its time over a frame, and
        Chrome hands the page a moving finger only with a frame: a finger that goes down while frames are behind
        moves late, after sim.js's HOLD_MS."""
        self.until("new Promise(done => { const start = performance.now(); requestAnimationFrame(() => "
                   "requestAnimationFrame(() => done(performance.now() - start < 100))); })")

    def wheel(self, at, *deltas):
        """Wheel events, deltaY px each (up is negative), all within one spin: each stamped 20 ms after the one
        before, so the page sees one spin however late a busy machine hands the events over (sim.js starts a new
        spin after WHEEL_GAP_MS between two events' times)"""
        start = time.time()
        for i, dy in enumerate(deltas):
            self.browser.cdp("Input.dispatchMouseEvent", {"type": "mouseWheel", "x": at[0], "y": at[1],
                                                          "deltaX": 0, "deltaY": dy, "timestamp": start + i * 0.02})

    def touch(self, kind, at=None):
        points = [{"x": at[0], "y": at[1], "id": 1}] if at else []
        self.browser.cdp("Input.dispatchTouchEvent", {"type": kind, "touchPoints": points})

    def mouse(self, kind, at):
        self.browser.cdp("Input.dispatchMouseEvent", {"type": kind, "x": at[0], "y": at[1], "button": "left",
                                                      "buttons": 1 if kind == "mousePressed" else 0, "clickCount": 1})

    def knob(self, name, r=0, deg=0, top="pick"):
        return self.evaluate(f"window.__knob({json.dumps(name)}, {r}, {deg}, {json.dumps(top)})")


@pytest.fixture(scope="module")
def panel():
    panel = Panel()
    try:
        yield panel
    finally:
        panel.stop()


@pytest.mark.parametrize("init, server", [(INIT, NO_SIM_JS), ("window.__playThrows = true;\n" + INIT, None)],
                         ids=["sim.js 404", "playPanel throws"])
def test_a_missing_or_failing_sim_js_shows_the_alert(init, server):
    # a sim.js the server does not have, and one whose playPanel throws: the page says so in its .fail alert.
    # Before the tests on the panel fixture: Playwright for Python runs one browser at a time in a thread
    panel = Panel(init, server, ready="document.querySelector('.fail[role=alert]')")
    try:
        assert "sim.js" in panel.evaluate("document.querySelector('.fail[role=alert]').textContent")
    finally:
        panel.stop()


VERSION = "2026-11-16, 1234abc"  # the commit the Pages workflow writes into firmware/version.py


@contextlib.contextmanager
def static_site(root, edits=(), layout="pages", requests=None):
    """viewer/ served as plain files, laid out as
    - "pages": GitHub Pages serves the artifact of the pages-pack job (build.yml), the firmware files play.js loads
      at firmware/ beside the page (at /);
    - "repository": a static server of a checkout, the page at /viewer/ and the firmware at /firmware/;
    - "project": a project site at /site/ that lacks its firmware/, with other files at the domain's /firmware/.
    version.py filled in. edits: (old, new) text of panel.py, each once. requests: a list that gets the path of
    every request. Gives the URL of the page."""
    page = {"pages": "viewer", "repository": "viewer", "project": "site"}[layout]
    shutil.copytree(os.path.join(ROOT, "viewer"), root / page)
    firmware = root / ("viewer/firmware" if layout == "pages" else "firmware")
    firmware.mkdir()
    for name in ("panel.py", "buttonmap.py"):
        shutil.copy(os.path.join(ROOT, "firmware", name), firmware)
    (firmware / "version.py").write_text(f'VERSION = "{VERSION}"\n')
    text = (firmware / "panel.py").read_text(encoding="utf-8")
    for old, new in edits:
        assert text.count(old) == 1, old
        text = text.replace(old, new)
    (firmware / "panel.py").write_text(text, encoding="utf-8")

    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def send_head(self):
            if requests is not None:
                requests.append(self.path)
            return super().send_head()
    served = root / "viewer" if layout == "pages" else root
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=served))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}/" + ("" if layout == "pages" else f"{page}/")
    finally:
        server.shutdown()
        server.server_close()


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    with static_site(tmp_path_factory.mktemp("site")) as url:
        yield url


# the plain view (no ?play) is up
VIEW = "document.readyState === 'complete' && !!document.querySelector('canvas')"


def test_the_plain_view_loads_nothing_of_the_panel(site):
    # the view for looking only: no sim.js, play.js, MicroPython or firmware, and a link to the panel
    page = Panel(url=site, ready=VIEW)
    try:
        time.sleep(0.5)
        loaded = page.evaluate("performance.getEntriesByType('resource').map(e => e.name)")
        assert any(name.endswith("/geometry.js") for name in loaded)
        assert not [name for name in loaded if re.search(r"sim\.js|play\.|micropython|firmware/", name)], loaded
        assert page.evaluate("document.querySelector('.hdr a').getAttribute('href')") == "?play"
    finally:
        page.stop()


def test_a_page_that_crashes_or_does_not_answer_fails_the_test(site, monkeypatch):
    # a page that crashes in an input event (Playwright leaves the CDP session's call waiting for ever), and an
    # evaluate that never ends, each fail the test at once and say so
    page = Panel(url=site, ready=VIEW)
    try:
        start = time.monotonic()
        with pytest.raises(pytest.fail.Exception, match="the page crashed: Page.crash"):
            page.browser.cdp("Page.crash", {})
        assert time.monotonic() - start < CALL_S
    finally:
        page.stop()
    page = Panel(url=site, ready=VIEW)
    try:
        monkeypatch.setitem(globals(), "CALL_S", 0.5)
        with pytest.raises(pytest.fail.Exception, match="did not answer within 0.5 s: new Promise"):
            page.evaluate("new Promise(() => {})")
    finally:
        page.stop()


def test_the_page_plays_the_panel_alone(site):
    # ?play, without the program: MicroPython runs panel.py in the page, and the page shows what it does as with the
    # program. A key held with the mouse, a wheel's detent and its pulse, the FREQ push's NAV and its light, a SHIFT
    # tap and its light, the shifted HOME's UNIT 2 and its light, a RANGE tilt, and the build from version.py
    page = Panel(url=site + "?play")
    light = "window.__V.lights.find(L => L.name === '{}').lens.emissiveIntensity"
    shown = "document.querySelector('.sim .lines').textContent"
    states = "window.__states.some(s => {})"
    try:
        assert f"build {VERSION}" in page.evaluate(shown) and page.evaluate(light.format("SHIFT")) == 0
        # idle: a step every IDLE_MS; an input steps at once, and every STEP_MS from then on
        page.until("window.__intervals.at(-1) === 250")
        cap = page.evaluate("window.__cap('AP')")
        since = page.mark()
        page.mouse("mousePressed", cap)
        assert page.evaluate("window.__intervals.at(-1)") == 10
        page.until(f"{shown}.includes('J1: AP')")
        page.mouse("mouseReleased", cap)
        page.until(f"{shown}.includes('J1: none')")
        time.sleep(GAP_S)
        page.wheel(page.knob("radio"), -100)
        page.until(states.format("s.buttons['1'].includes('COM_KHZ_UP')"))
        centre = page.knob("radio")
        page.mouse("mousePressed", centre)
        page.mouse("mouseReleased", centre)
        page.until(f"{shown}.includes('UNIT 1 · NAV') && {light.format('FREQ')} === 1")
        for label in ("SHIFT", "HOME"):
            cap = page.evaluate(f"window.__cap('{label}')")
            page.mouse("mousePressed", cap)
            page.mouse("mouseReleased", cap)
            if label == "SHIFT":
                page.until(f"{shown}.includes('SHIFT') && {light.format('SHIFT')} === 1")
        page.until(f"{shown}.includes('UNIT 2') && {light.format('UNIT')} === 1")
        arrow = page.knob("range", page.evaluate("window.__V.G.plate_art.range.arrow_r"), -90)
        page.mouse("mousePressed", arrow)
        page.until(states.format("s.buttons['1'].includes('PAN_UP')"))
        page.mouse("mouseReleased", arrow)
        assert page.lines(since) == [
            "press AP", "release AP", "turn FREQ_INNER 1", "press FREQ_PUSH", "release FREQ_PUSH", "press SHIFT",
            "release SHIFT", "press HOME", "release HOME", "press RANGE_COM", "press RANGE_A", "release RANGE_A",
            "release RANGE_COM"]
        assert {client for client, _ in page.acts(since)} == {"browser"}
    finally:
        page.stop()


# panel.py with an error in the FREQ light while the mode is NAV, which a new panel (COM) gets past
FREQ_FAULT = (("    def freq_lit(self, t):\n", "    def freq_lit(self, t):\n"
               "        if self.freq_mode == 1:\n            raise ZeroDivisionError('a test')\n"),)
# ... with an error in the SHIFT light that a new panel has too: from the start, or from a CDI press on
STUCK = (("import buttonmap as BM\n", "import buttonmap as BM\nSTUCK = []\n"),
         ("    def shift_level(self, t):\n",
          "    def shift_level(self, t):\n        if STUCK:\n            raise ZeroDivisionError('stuck')\n"),
         ("    def key(self, name, pressed, t, at=None):\n",
          "    def key(self, name, pressed, t, at=None):\n        if name == 'CDI':\n            STUCK.append(1)\n"))
ALERT = "document.querySelector('.sim-alert').textContent"
LINES = "document.querySelector('.sim .lines').textContent"


def test_an_error_in_the_panel_alone_starts_it_again_and_says_so(tmp_path):
    # as code.py's handler: the alert names the error, and the panel goes on anew (COM, not NAV)
    with static_site(tmp_path, FREQ_FAULT) as url:
        page = Panel(url=url + "?play")
        try:
            centre = page.knob("radio")
            page.mouse("mousePressed", centre)
            page.mouse("mouseReleased", centre)
            page.until(f"{ALERT}.includes('Firmware error, panel.py started again: ZeroDivisionError: a test')")
            page.until(f"{LINES}.startsWith('UNIT 1 · COM')")
            cap = page.evaluate("window.__cap('AP')")
            page.mouse("mousePressed", cap)
            page.until(f"{LINES}.includes('J1: AP')")
            page.mouse("mouseReleased", cap)
        finally:
            page.stop()


@pytest.mark.parametrize("start", (True, False), ids=["at the start", "in a step"])
def test_an_error_the_panel_alone_cannot_get_past_stops_it_and_says_so(tmp_path, start):
    # an error play.py hands on (the new panel has it too) stops the panel, in the start (hello and the first
    # step, where the page would say "loading the panel…" for ever) as in a later step, and the page says so
    edits = STUCK + ((("STUCK = []", "STUCK = [1]"),) if start else ())
    ready = f"!!document.querySelector('.sim-alert') && {ALERT}.startsWith('The panel stopped')" if start else READY
    with static_site(tmp_path, edits) as url:
        page = Panel(url=url + "?play", ready=ready)
        try:
            if not start:
                cap = page.evaluate("window.__cap('CDI')")
                page.mouse("mousePressed", cap)
                page.mouse("mouseReleased", cap)
                page.until(f"{ALERT}.startsWith('The panel stopped')")
            assert page.evaluate(ALERT) == ("The panel stopped: ZeroDivisionError: stuck. Switch to another tab and "
                                            "back, or reload the page, to start it again.")
            assert page.evaluate("document.querySelector('.sim').classList.contains('none')")
            if start:
                return
            # hidden and shown again: panel.py imported anew, without the error (STUCK empty), in the same
            # MicroPython (a second one in the page would share the first one's tables in globalThis)
            started = page.evaluate("window.__wasm")
            for hidden in ("true", "false"):
                page.evaluate("Object.defineProperty(document, 'hidden', { configurable: true, get: () => "
                              f"{hidden} }}); document.dispatchEvent(new Event('visibilitychange'))")
            page.until(READY)
            assert page.evaluate("window.__wasm") == started
            cap = page.evaluate("window.__cap('AP')")
            page.mouse("mousePressed", cap)
            page.until(f"{LINES}.includes('J1: AP')")
            page.mouse("mouseReleased", cap)
        finally:
            page.stop()


def test_a_checkout_s_page_takes_the_firmware_beside_viewer(tmp_path):
    # the page at .../viewer/ of a static server of the repository: firmware/ beside the page is not there, a
    # failed request (as a network error) no more than a missing file, and the repository's firmware/ is
    requests = []
    with static_site(tmp_path, layout="repository", requests=requests) as url:
        page = Panel("window.__fail = /^firmware\\/buttonmap/;\n" + INIT, url=url + "?play")
        try:
            assert "/firmware/panel.py" in requests and "/firmware/buttonmap.py" in requests
            assert "/viewer/firmware/panel.py" in requests and "/viewer/firmware/buttonmap.py" not in requests
        finally:
            page.stop()


def test_a_site_s_page_loads_no_firmware_from_above_it(tmp_path):
    # a project site on Pages (/site/) whose firmware/ went missing does not run the domain's /firmware/
    requests = []
    with static_site(tmp_path, layout="project", requests=requests) as url:
        page = Panel(url=url + "?play", ready="!!document.querySelector('.sim-alert') && "
                                              f"{ALERT}.endsWith('.py is missing')")
        try:
            # (whichever of panel.py and buttonmap.py the server answered first)
            assert re.fullmatch(r"The panel could not start in this browser: firmware/(panel|buttonmap)\.py is missing",
                                page.evaluate(ALERT))
            assert any(r.startswith("/site/firmware/") for r in requests)
            assert not [r for r in requests if r.startswith("/firmware/")]
        finally:
            page.stop()


def test_a_wheel_turns_a_detent_per_notch_and_a_touchpad_one_per_100_px(panel):
    # FREQ's inner knob: a mouse's notches of 100 px up (clockwise), one each; a notch and then three in one event
    # (a fast spin) down; a touchpad's 10 px steps, whose first counts as a detent and every 100 px more as one
    at = panel.knob("radio")
    for deltas, turns in (((-100, -100, -100), ["turn FREQ_INNER 1"] * 3),
                          ((100, 300), ["turn FREQ_INNER -1", "turn FREQ_INNER -3"]),
                          ((10,) * 11, ["turn FREQ_INNER -1"] * 2)):
        time.sleep(GAP_S)
        since = panel.mark()
        panel.wheel(at, *deltas)
        assert panel.lines(since) == turns, deltas


def test_a_finger_taps_holds_and_turns_a_knob(panel):
    # the ALT/HDG knob (its push lights nothing, so the page draws few frames): a tap pushes it for a moment; a
    # finger that stays still for HOLD_MS holds the push until it lifts; one that moves round the outer ring turns
    # it a detent per 12 degrees, clockwise and back, and pushes nothing
    centre = panel.knob("ap")
    since = panel.mark()
    panel.touch("touchStart", centre)
    panel.touch("touchEnd")
    assert panel.lines(since) == ["press ALTHDG_PUSH", "release ALTHDG_PUSH"]
    since = panel.mark()
    panel.touch("touchStart", centre)
    time.sleep(1.2)
    assert panel.lines(since) == ["press ALTHDG_PUSH"]
    panel.touch("touchEnd")
    assert panel.lines(since) == ["press ALTHDG_PUSH", "release ALTHDG_PUSH"]
    # 40 degrees round, then 50 back: a detent each 12 degrees, of the sum since the finger went down
    path = [panel.knob("ap", 9.5, deg, "outer") for deg in (0, 20, 40, 10, -10)]
    panel.settle()
    since = panel.mark()
    panel.touch("touchStart", path[0])
    for at in path[1:]:
        panel.touch("touchMove", at)
    panel.touch("touchEnd")
    assert panel.lines(since) == ["turn ALTHDG_OUTER 1"] * 3 + ["turn ALTHDG_OUTER -1"] * 3


def test_a_refused_request_starts_the_page_again_as_a_new_client(panel):
    # AP held with the mouse; a request the program refuses may have lost a release, so the page connects again
    # as a new client, and the program lets go of what the old one held: AP is up, and letting the mouse go
    # sends nothing more for it
    cap = panel.evaluate("window.__cap('AP')")
    since = panel.mark()
    panel.mouse("mousePressed", cap)
    panel.until("document.querySelector('.sim .lines').textContent.includes('J1: AP')")
    time.sleep(GAP_S)
    panel.evaluate("window.__refuse.push(409)")
    panel.wheel(panel.knob("radio"), -100)
    panel.until("document.querySelector('.sim .lines').textContent.includes('J1: none')")
    panel.mouse("mouseReleased", cap)
    time.sleep(GAP_S)
    panel.wheel(panel.knob("radio"), -100)
    panel.lines(since)
    sent = panel.acts(since)
    old, new = sent[0][0], sent[-1][0]
    assert sent == [[old, "press AP"], [old, "turn FREQ_INNER 1"], [new, "turn FREQ_INNER 1"]] and new != old
