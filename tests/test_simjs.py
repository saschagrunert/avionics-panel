"""The panel page's script (viewer/sim.js) in a browser, against the real `python3 -m sim.page`: what a wheel, a
finger and a refused request make the page send. The page's requests are read in the page (a wrapper round its
fetch, which can also refuse one), and the input is the browser's own (Chrome's DevTools protocol), at the screen
point of a knob or cap that the page's camera gives.

The browser comes from Playwright: Playwright for Python where it is installed, as in the firmware shell on Linux
(nix/shells.nix), else Playwright for Node through `node` (require('playwright')). Without either, or without its
Chromium, the tests skip; REQUIRE_BROWSER=1 turns that skip into a failure."""
import contextlib
import ctypes
import json
import os
import re
import selectors
import shutil
import signal
import subprocess
import sys
import tempfile
import time

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TIMEOUT_S = 10
VIEWPORT = {"width": 480, "height": 360}       # small: software WebGL draws few pixels faster
ARGS = ["--enable-unsafe-swiftshader", "--use-angle=swiftshader"]     # WebGL in software, without a GPU
# without WAYLAND_DISPLAY: on a Wayland desktop SwiftShader asks Vulkan for a Wayland surface it lacks, and WebGL
# fails even headless
ENV = {k: v for k, v in os.environ.items() if k != "WAYLAND_DISPLAY"}
GAP_S = 0.4          # longer than sim.js's WHEEL_GAP_MS: the next wheel event starts a new spin
# before the page's scripts: the actions the page sends, by client ([client, line]), the statuses that refuse the
# next requests with actions, without the server (__refuse; an empty beat goes through), and the view index.html
# hands sim.js (V)
INIT = r"""
localStorage.setItem('avionics-panel-quiet', '1');      // the sound off: no audio device to start
window.__acts = []; window.__refuse = [];
const fetched = window.fetch.bind(window);
window.fetch = (url, options) => {
  const act = String(url).match(/sim\/act\?client=(.*)$/), body = String(options && options.body || '');
  if (act) {
    for (const line of body.split('\n')) if (line) window.__acts.push([act[1], line]);
    if (body && window.__refuse.length) return Promise.resolve(new Response('', { status: window.__refuse.shift() }));
  }
  return fetched(url, options);
};
let play;
Object.defineProperty(window, 'playPanel', { configurable: true, get: () => play,
  set: f => { play = V => { window.__V = V; return f(V); }; } });
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
# Playwright for Node, run by the tests as a server of their own: argv[1] the options, then one JSON command a
# line on stdin, ["evaluate", expression] or ["cdp", method, params], and its {result} or {error} on stdout
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


class PythonPlaywright:
    def __init__(self, url):
        from playwright.sync_api import Error, sync_playwright
        self.playwright = sync_playwright().start()
        try:
            self.browser = self.playwright.chromium.launch(args=ARGS, env=ENV)
        except Error as e:
            self.playwright.stop()
            missing(f"Playwright for Python has no Chromium: {str(e).splitlines()[0]}")
        context = self.browser.new_context(has_touch=True, reduced_motion="reduce", viewport=VIEWPORT)
        context.add_init_script(INIT)
        self.page = context.new_page()
        self.session = context.new_cdp_session(self.page)
        info = self.browser.new_browser_cdp_session().send("SystemInfo.getProcessInfo")["processInfo"]
        self.pid = next(p["id"] for p in info if p["type"] == "browser")
        self.page.goto(url)

    def evaluate(self, expression):
        return self.page.evaluate(expression)

    def cdp(self, method, params):
        return self.session.send(method, params)

    def close(self):
        # ended at once: browser.close() waits seconds for the page to unload, as Playwright for Node's would
        with contextlib.suppress(OSError):
            os.kill(self.pid, getattr(signal, "SIGKILL", signal.SIGTERM))
        self.playwright.stop()


class NodePlaywright:
    def __init__(self, url, node):
        options = {"url": url, "init": INIT, "viewport": VIEWPORT, "args": ARGS}
        self.process = subprocess.Popen([node, "-e", NODE, json.dumps(options)], stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE, text=True, cwd=ROOT, env=ENV)
        first = json.loads(self.process.stdout.readline() or '{"missing": "node ended"}')
        if "missing" in first:
            self.close()
            missing(f"Playwright for Node has no Chromium: {first['missing'].splitlines()[0]}")

    def call(self, *command):
        self.process.stdin.write(json.dumps(command) + "\n")
        self.process.stdin.flush()
        answer = json.loads(self.process.stdout.readline())
        if "error" in answer:
            raise RuntimeError(answer["error"])
        return answer["result"]

    def evaluate(self, expression):
        return self.call("evaluate", expression)

    def cdp(self, method, params):
        return self.call("cdp", method, params)

    def close(self):
        self.process.stdin.close()
        try:
            self.process.wait(TIMEOUT_S)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait()


def browser(url):
    try:
        import playwright.sync_api  # noqa: F401
    except ImportError:
        pass
    else:
        return PythonPlaywright(url)
    node = shutil.which("node")
    if node and subprocess.run([node, "-e", "require('playwright')"], cwd=ROOT, capture_output=True).returncode == 0:
        return NodePlaywright(url, node)
    return missing("no Playwright: neither playwright for Python nor require('playwright') in node")


def _ends_with_pytest():
    """In the server, before it starts (Linux): a SIGTERM once pytest is gone, also when pytest was killed and
    stopped nothing (a CI job cancelled, timeout)"""
    ctypes.CDLL(None, use_errno=True).prctl(1, signal.SIGTERM)       # PR_SET_PDEATHSIG


class Panel:
    """The page in a browser, served by `python3 -m sim.page`"""

    def __init__(self):
        self.errors = tempfile.TemporaryFile("w+")  # noqa: SIM115 (closed in stop(): the server writes it until then)
        self.server = subprocess.Popen([sys.executable, "-m", "sim.page", "--port", "0"], cwd=ROOT, text=True,
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
        try:
            self.browser = browser(self.url)
            # the view is up and the program has said which devices there are
            self.until("window.__V && !document.querySelector('.fail') && !!document.querySelector('.sim:not(.none)')")
        except BaseException:
            self.stop()
            raise

    def stop(self):
        if getattr(self, "browser", None):
            self.browser.close()
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
        while True:
            before = self.acts(since)
            time.sleep(0.15)
            if self.acts(since) == before:
                self.settle()
                return [line for _, line in before]

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
