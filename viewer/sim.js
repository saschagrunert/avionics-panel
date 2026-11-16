// The panel page: index.html loads this when python3 -m sim.page (sim/page.py) serves it with ?sim. The firmware
// runs in that program; this page sends it raw input events as they happen and shows what comes back: the lights,
// the buttons each joystick reports (with --family, a line of what the one pressed last does in that profile), a firmware
// error and a lost connection. The camera stays put. With ?play, as on GitHub Pages, the firmware's panel.py runs in
// the page itself instead (play.js: V.engine), which takes the same input events and gives back the same.
//   key cap: pointer down presses it, up (or cancel) lets go
//   knob: the inner knob, or the outer ring round it, by the pointer's distance from the knob's axis. The wheel
//     turns that ring, a detent per notch; a mouse button pushes the knob as long as it is down. A finger turns the
//     ring it touched by moving round the knob, a detent per 12 degrees as the real one. A finger that does not
//     move, not even a quarter detent round the knob, pushes it: a quick tap for a moment, one that stays longer
//     than HOLD_MS until it lifts, and turns the ring if it then moves round the knob, as a push and turn on the
//     panel. One finger per knob at a time: a second one takes the
//     knob over if the first has neither moved nor started to hold the push.
//   the pan arrows round RANGE: held, RANGE tilts that way
// A key or push clicks as it goes down and up, a ring ticks at each detent, unless "sound on" beside the lines at
// the bottom left is clicked to "sound off" (the browser remembers it).
// Over any of these the mouse pointer is a hand. Everything the page holds is let go when it is hidden or loses
// the focus; the program lets go of it when the page goes, also when the page stops telling it that it is still
// there (a tablet off the network).
window.playPanel = function playPanel(V) {
  const { G, camera, controls, canvas, assembly, go, invalidate } = V;
  const RANGE = V.knobs.range, KNOBS = Object.values(V.knobs);
  const MOVE_PX = 8;                   // a finger that moves this far from where it touched is no push
  const HOLD_MS = 1000;                // one that stays still longer than this holds the push until it lifts: longer
                                       // than a tap takes, so a finger that rests before it turns rarely pushes
  const AXIS_MM = 2.5;                 // closer to the axis than this the angle round it is a finger's jitter
  const AXIS_OUT_MM = 1;               // ... and a finger leaves that middle this much further out
  const WHEEL_GAP_MS = 300;            // a wheel event this long after the last starts a new spin: a notch at least
  const NOTCH_MIN_PX = 20;             // a spin whose first event is this large is a mouse's; a smaller one is a
                                       // touchpad's ...
  const WHEEL_PX = 100;                // ... which sums up to a notch this large (and Firefox's lines count as one)
  const LINE_PX = 18;                  // a line at the bottom left: 12 px type, 1.5 high ...
  const LINES_W_PX = 230;              // ... their width at most: two or three buttons a line ...
  const KEYS_W_PX = 412;               // ... in keyboard mode the longest shortcut's line. A longer line ends in an
                                       // ellipsis: they never wrap, so the panel does not move for them.
  const SPEAKER_PX = 84;               // the speaker button beside them, where there is sound, takes this more
  const SHORT_PX = 500;                // a window lower than this (a phone turned sideways) has them on one line
  const TOLD_SHORT = 48;               // ... where a legend line takes this many characters at most
  const FOV = 10;                      // degrees: from about straight above everywhere, so the knobs lean little
  const SPIN_TAU_MS = 25;              // a ring eases to its detent: most of the way in about 80 ms (3 of these)
  const SPIN_DONE = 0.001;             // radians from the target: there
  const TRAVEL = 1;                    // mm a pressed cap or pushed knob goes down ...
  const PRESS_TAU_MS = 8;              // ... at once, most of the way in a frame,
  const LIFT_TAU_MS = 20;              // ... and its spring brings it back a little slower
  const PRESS_DONE = 0.01;             // of the travel from where it goes: there
  const SHOWN_MS = 60;                 // a part pressed for less (a tap on a knob, at once) is shown down this long
  const PRESSED = 0.55;                // the light on a pressed cap, in the finger's shade ...
  const PRESSED_SIZE = 0.95;           // ... and its size: from above, going down is getting smaller
  const TILT = G.rkjxt.tilt * Math.PI / 180;   // RANGE leans this far towards an arrow, about the lever's fulcrum
  const FADE_MS = 1000;                // a button stays in the list, dimmed, this long after it went
  const ALERT_MS = 10000;              // a firmware error shows this long
  const Z = G.plate.z1, R_IN = G.inner_knob.d / 2 + 0.5;    // the inner knob, with its edge leaning out a little
  const R_OUT = 1.5 * G.outer_knob.d / 2;                    // the outer ring, and a margin round it as large again
  const TOP = { inner: Z + G.inner_knob.z1, outer: Z + G.outer_knob.z1, ring: Z + G.range_knob.z1 };
  const ARROWS = [G.plate_art.range.arrow_r - 1.5, G.plate_art.range.arrow_r + 5];   // the arrows' ring round RANGE
  const TICK_MS = 15;                  // the ticks of detents turned at once follow each other this far apart
  const QUIET = 'avionics-panel-quiet';   // the browser's storage key for the speaker off

  // ---------------- what the page shows ----------------
  const style = document.createElement('style');
  style.textContent = `
    body.play .bar, body.play .legend, body.play .hdr { display: none; }
    /* the lines can lie over the plate and the banner over the top keys: a ground of their own, and no taps taken */
    .sim { position: fixed; left: max(16px, env(safe-area-inset-left, 0px)); bottom: calc(16px + env(safe-area-inset-bottom, 0px));
           font: 12px var(--mono); color: var(--panel-fg); pointer-events: none; line-height: 1.5;
           max-width: min(calc(100% - 32px), ${LINES_W_PX}px);
           background: var(--panel); padding: 3px 7px; border-radius: 7px; box-sizing: border-box;
           display: flex; align-items: flex-start; }
    .sim .lines { min-width: 0; }
    .sim .lines > div { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .sim .gone, .sim .version { opacity: .45; }
    .sim .speaker { pointer-events: auto; cursor: pointer; font: inherit; color: inherit; background: none; border: 0;
                    padding: 0 4px; margin-left: 1ch; flex: none; line-height: inherit;
                    text-decoration: underline; text-decoration-style: dotted; text-underline-offset: 3px; }
    .sim .speaker.off { opacity: .45; }
    /* at the top, where the 3D view has its name */
    .sim-alert { position: fixed; top: calc(16px + env(safe-area-inset-top, 0px)); left: 50%; transform: translateX(-50%); max-width: calc(100% - 32px);
                 padding: 8px 14px; border-radius: 9px; background: var(--on); color: var(--on-fg); font: 500 14px var(--font);
                 pointer-events: none; }
    .sim.none, .sim-alert:empty { display: none; }`;
  document.head.appendChild(style);
  document.body.classList.add('play');
  const strip = document.createElement('div'), alert = document.createElement('div');
  const box = document.createElement('div');                    // the lines, beside the speaker button (sounds)
  strip.className = 'sim none'; box.className = 'lines'; alert.className = 'sim-alert'; alert.setAttribute('role', 'alert');
  strip.appendChild(box);
  document.body.append(strip, alert);
  for (const L of V.lights) if (L.name !== 'SHIFT') L.lens.color.setHex(0x1d1e21).convertSRGBToLinear();   // dark when off
  controls.enableRotate = controls.enableZoom = controls.enablePan = false;
  V.ground.visible = false;            // from above its shadow is a grey slab beside the panel
  canvas.addEventListener('contextmenu', e => e.preventDefault());
  camera.fov = FOV;                    // (the next frame updates the projection)
  controls.maxDistance = Infinity;     // the narrow view stands further off than the zoom limit of the others
  // The page shows neither name nor hint (docs/using/simulator.md says how to play it). The panel goes beside the
  // lines at the bottom left or with all it operates above them, whichever shows it larger; in a window lower than
  // SHORT_PX the lines are one line across it, with the panel above. The lines may lie over the plate's edge below
  // the RANGE arrows, the alert over the top keys. Again after a resize, and when the number of lines changes.
  let lines = 3, width = LINES_W_PX;   // the lines: UNIT (and the FREQ mode) and each joystick's buttons (with a
                                       // legend, and what the last one pressed does), or UNIT and the keyboard's
  let short = false;                   // all of them on one line, across the window
  const rows = () => short ? 1 : lines;
  const SIDES = 'max(16px, env(safe-area-inset-left, 0px)) - max(16px, env(safe-area-inset-right, 0px))';
  const fitStrip = () => { strip.style.maxWidth = `min(calc(100% - ${SIDES}), ${short ? 100000 : width}px)`; };
  // the screen's safe areas (a phone's notch and rounded corners), read through a hidden element: [top, right,
  // bottom, left] px
  const probe = document.createElement('div');
  probe.style.cssText = 'position: fixed; visibility: hidden; pointer-events: none; padding: env(safe-area-inset-top, 0px) '
    + 'env(safe-area-inset-right, 0px) env(safe-area-inset-bottom, 0px) env(safe-area-inset-left, 0px)';
  document.body.appendChild(probe);
  const insets = () => { const c = getComputedStyle(probe); return [c.paddingTop, c.paddingRight, c.paddingBottom, c.paddingLeft].map(parseFloat); };
  assembly.updateMatrixWorld();
  const operated = new THREE.Box3();   // round the caps, the knobs and the arrows round RANGE
  for (const m of [...V.keys.flatMap(k => k.meshes), ...KNOBS.flatMap(k => Object.values(k.rings).flat())]) operated.expandByObject(m);
  for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
    operated.expandByPoint(assembly.localToWorld(new THREE.Vector3(V.px(RANGE.x + dx * ARROWS[1]), Z, V.pz(RANGE.y + dy * ARROWS[1]))));
  }
  // the panel's footprint: its box, cut at the plate's top, as the knobs, seen from about straight above, stand
  // inside it (their tops, nearer the camera, would push the edges out); and the same with its side towards the
  // pilot (+z, the bottom) at the arrows
  const flat = V.view.box.clone();
  flat.max.y = assembly.localToWorld(new THREE.Vector3(0, Z, 0)).y;
  const above = flat.clone();
  above.max.z = operated.max.z;
  V.view.gap = 0.99;                   // fit() leaves 0.5 % free on each side inside the margins, at least 8 px
  V.view.margins = () => {             // [top, right, bottom, left] px kept free round a box, each way (fit() adds a gap)
    // clear of the safe areas, the same on both sides so the panel stays in the middle
    const css = getComputedStyle(strip), [top, right, , left] = insets(), side = Math.max(left, right);
    const bottom = parseFloat(css.bottom), beside = parseFloat(css.left) + width;
    const below = [top, side, bottom + rows() * LINE_PX + 6, side, above];                    // (6: their padding)
    return short ? [below] : [below, [top, side, bottom, beside, flat]];   // one line across the window: below only
  };
  // the lights and each device's buttons as the program last sent them (update()), and when each button went
  let lights = {}, unit = 1, freq = 'COM', buttons = {}, fadeTimer;
  let version = null;                  // the commit of the files the program serves (hello), the last line, dimmed
  let last = null;                     // [device, button] that went down last, for the legend
  let legend = null;                   // with --family: device: { button: what it does in that profile }
  let went = {};                       // device: { button: when it went }
  function place() {
    const was = short;
    short = window.innerHeight < SHORT_PX;
    if (short !== was) { fitStrip(); render(); }
    go('P', true);
  }
  window.addEventListener('resize', place);
  if (window.ResizeObserver) new ResizeObserver(place).observe(canvas);   // after index.html's: the camera's size first
  place();
  let alertTimer;
  const say = (text, ms) => { clearTimeout(alertTimer); alert.textContent = text; if (ms) alertTimer = setTimeout(() => say(''), ms); };

  // ---------------- sounds ----------------
  // a click: a few ms of noise through a band-pass filter, its pitch and loudness by what made it. The audio
  // starts with the first press (a browser lets it start only in a click or as a finger lifts off; a wheel does
  // not count before one) and takes a moment: a sound meanwhile waits for it, up to WAIT_MS. After IDLE_MS without a sound
  // it pauses, so a tablet left beside the sim saves its battery, and the next sound starts it again, as after
  // Safari interrupts it (a call). The ticks of a fast spin follow each other TICK_MS apart. The speaker button
  // turns the sounds off and on; without Web Audio, or where it fails to start, there is neither sound nor button.
  let AudioContext = window.AudioContext || window.webkitAudioContext;
  const SOUNDS = { down: [3200, 0.5, 0.012], up: [2400, 0.25, 0.010], detent: [4000, 0.6, 0.008] };   // Hz, gain, s
  const UP_AFTER_S = 0.04;             // a tap's release clicks at least this long after its press, not on top of it
  const WAIT_MS = 300, IDLE_MS = 120000;
  let audio = null, noise = null, quiet = false, downAt = -1, tickAt = 0, idleTimer;
  const waiting = [];                  // [kind, n, when] sounded while the audio starts
  try { quiet = localStorage.getItem(QUIET) === '1'; } catch (e) { /* no storage: sounds on */ }
  const speaker = document.createElement('button');
  speaker.className = 'speaker'; speaker.type = 'button';
  const showSpeaker = () => {
    speaker.textContent = quiet ? 'sound off' : 'sound on';
    speaker.classList.toggle('off', quiet);
    speaker.title = quiet ? 'Sounds off: click to turn them on' : 'Sounds on: click to turn them off';
  };
  showSpeaker();
  if (AudioContext) { strip.appendChild(speaker); width += SPEAKER_PX; }   // (not in the lines: render() makes those anew)
  fitStrip();
  speaker.addEventListener('click', () => {
    quiet = !quiet; showSpeaker();
    try { localStorage.setItem(QUIET, quiet ? '1' : '0'); } catch (e) { /* not remembered */ }
    if (quiet) pause(); else wake();
  });
  const settle = promise => { if (promise) promise.catch(() => {}); };   // (refused outside a gesture: the next tries)
  function pause() { clearTimeout(idleTimer); if (audio && audio.state === 'running' && audio.suspend) settle(audio.suspend()); }
  function wake() {                    // in a press or a click: a browser lets audio start there
    if (quiet || !AudioContext) return;
    try {
      if (!audio) {
        audio = new AudioContext();
        noise = audio.createBuffer(1, Math.ceil(audio.sampleRate * 0.02), audio.sampleRate);
        const data = noise.getChannelData(0);
        for (let i = 0; i < data.length; i++) data[i] = Math.random() * 2 - 1;
        audio.onstatechange = () => {  // running: what sounded while it started, unless that is long gone
          if (!audio || audio.state !== 'running') return;
          const now = performance.now();
          for (const [kind, n, at] of waiting.splice(0)) if (now - at < WAIT_MS) play(kind, n);
        };
      }
      if (audio.state !== 'running') settle(audio.resume());   // suspended, paused, or Safari's interrupted
    } catch (e) {                        // no audio device, too many contexts: the panel plays on without sound
      AudioContext = null; audio = null; waiting.length = 0;
      if (speaker.parentNode) { speaker.remove(); width -= SPEAKER_PX; fitStrip(); go('P', true); }
    }
  }
  function sound(kind, n = 1) {
    if (quiet || !audio) return;
    if (audio.state === 'running') return play(kind, n);
    waiting.push([kind, n, performance.now()]);
    if (waiting.length > 8) waiting.shift();
    wake();
  }
  function play(kind, n) {             // n of them, TICK_MS apart
    clearTimeout(idleTimer);
    idleTimer = setTimeout(pause, IDLE_MS);
    const [hz, gain, s] = SOUNDS[kind];
    for (let i = 0; i < n; i++) {
      let at = audio.currentTime;
      if (kind === 'down') downAt = at;
      else if (kind === 'up') at = Math.max(at, downAt + UP_AFTER_S);
      else { at = Math.max(at, tickAt); tickAt = at + TICK_MS / 1000; }
      const src = audio.createBufferSource(), filter = audio.createBiquadFilter(), level = audio.createGain();
      src.buffer = noise;
      filter.type = 'bandpass'; filter.frequency.value = hz; filter.Q.value = 4;
      level.gain.setValueAtTime(gain, at);
      level.gain.exponentialRampToValueAtTime(0.001, at + s);
      src.connect(filter); filter.connect(level); level.connect(audio.destination);   // (older Safari: no chaining)
      src.start(at); src.stop(at + s);
    }
  }

  // the lights in words, and each joystick's buttons (in keyboard mode the keyboard's function and shortcut); one
  // that went stays a while, dimmed. With a legend, one more line says what the button pressed last does, until
  // the next goes down.
  function render() {
    clearTimeout(fadeTimer);
    box.textContent = '';
    strip.classList.toggle('none', !Object.keys(buttons).length);
    if (!Object.keys(buttons).length) return;
    // a line each, or in a short window one line for all, the parts apart by a bar
    const one = short && document.createElement('div');
    if (one) box.appendChild(one);
    const line = (...parts) => {
      if (one) { if (parts.length) one.append(...(one.childNodes.length ? [' | '] : []), ...parts); return; }
      const d = document.createElement('div'); d.append(...(parts.length ? parts : ['\u00a0'])); box.appendChild(d);
    };
    line(`UNIT ${unit} · ${freq}${lights.SHIFT ? ' · SHIFT' : ''}`);   // the panel's unit and FREQ mode: the green
                                                                         // light blinks for ADF and counts too
    // what the button pressed last does: after the joysticks' lines, but in one line across a low window right
    // after UNIT, where the ellipsis cuts it last
    // ... in a short window cut to TOLD_SHORT characters, so the buttons down still show after it; all of it as the
    // line's title. (last may be a keyboard's, from before a reconnect to the same build in joystick mode.)
    const does = last && legend && legend[last[0]] && legend[last[0]][last[1]];
    const told = legend && !buttons.keyboard && [];
    if (told && does) {
      const full = `${last[1]}${last[0] === '2' ? ' (J2)' : ''}: ${does}`, t = document.createElement('span');
      t.textContent = short && full.length > TOLD_SHORT ? `${full.slice(0, TOLD_SHORT - 1)}…` : full;
      t.title = full;
      told.push(t);
    }
    if (told && short) line(...told);
    const now = performance.now();
    let next = Infinity;
    for (const [device, names] of Object.entries(buttons)) {
      const old = Object.entries(went[device] || {}).filter(([n, at]) => now - at < FADE_MS && !names.includes(n));
      for (const [, at] of old) next = Math.min(next, at + FADE_MS - now);
      const listed = [...names.map(n => [n, '']), ...old.map(([n]) => [n, 'gone'])];
      const spans = text => listed.flatMap(([n, cls], i) => {
        const s = document.createElement('span'); s.textContent = text(n); s.className = cls;
        return i ? [' · ', s] : [s];
      });
      const name = device === 'keyboard' ? 'keyboard' : `J${device}`;
      line(`${name}: `, ...(listed.length ? spans(n => n) : ['none']));
    }
    if (told && !short) line(...told);
    if (version) {
      const s = document.createElement('span'); s.textContent = `build ${version}`; s.className = 'version';
      line(s);
    }
    if (next < Infinity) fadeTimer = setTimeout(render, Math.ceil(next) + 1);
  }
  function update(state) {
    const now = performance.now();
    for (const [device, names] of Object.entries(state.buttons)) {
      for (const n of names) if (!(buttons[device] || []).includes(n)) last = [device, n];
    }
    for (const [device, names] of Object.entries(buttons)) {
      const still = state.buttons[device] || [];
      for (const n of names) if (!still.includes(n)) (went[device] = went[device] || {})[n] = now;
    }
    ({ lights, unit, freq, buttons } = state);
    const count = 1 + Object.keys(buttons).length + (legend && !buttons.keyboard ? 1 : 0) + (version ? 1 : 0);
    if (Object.keys(buttons).length && count !== lines) {   // the mode is known: the lines' number and width
      lines = count; width = (buttons.keyboard ? KEYS_W_PX : LINES_W_PX) + (speaker.parentNode ? SPEAKER_PX : 0);
      fitStrip(); go('P', true);
    }
    for (const L of V.lights) L.lens.emissiveIntensity = lights[L.name];
    render(); invalidate();
  }
  function clear() {
    went = {}; buttons = {};           // (last stays: a reconnect to the same build keeps its line)
    update({ lights: { SHIFT: 0, UNIT: 0, FREQ: 0 }, unit: 1, freq: 'COM', buttons: {} });
  }
  clear();

  // ---------------- the program ----------------
  // hello names this page (client), the build of the files the program serves and their commit (version, null in a
  // git checkout), the firmware's inputs under the caps and knobs, the legend (null without --family), and the
  // program's numbers: the angle of a detent, the detents one action takes and the actions one request takes at
  // most, and how often the page tells the program that it is still there. A page that reconnects to another build,
  // as after a newer simulator was unpacked and started, reloads: its files go with the old one.
  // The engine of play.js stands in for the program: the same hello (no build, no requests to count or pace), the
  // same states and faults, the same actions.
  const engine = V.engine || null;
  let events, client = null, build = null, inputs = null, busy = false, beat = false, beatTimer;
  let DETENT, TURN_MAX, ACTS_MAX, BEAT_MS;
  const queue = [];
  function hello(h) {
    if (build !== null && h.build !== build) { events.close(); location.reload(); return; }
    ({ client, build, version, inputs, legend, turn_max: TURN_MAX, acts_max: ACTS_MAX, beat_ms: BEAT_MS } = h);
    DETENT = 2 * Math.PI / h.detents;
    clearInterval(beatTimer);
    if (!engine) beatTimer = setInterval(() => { beat = true; flush(); }, BEAT_MS);
    say('');
  }
  const fault = f => say(`Firmware error, ${engine ? 'panel.py started again' : 'code.py reloaded'}: ${f.message}`, ALERT_MS);
  function connect() {
    if (engine) {
      say('loading the panel…');
      engine.open({ hello, state: update, fault, lost: message => { drop(); say(message); } });
      return;
    }
    say('connecting…');
    events = new EventSource('sim/events');
    events.addEventListener('hello', e => hello(JSON.parse(e.data)));
    events.addEventListener('state', e => update(JSON.parse(e.data)));
    events.addEventListener('fault', e => fault(JSON.parse(e.data)));
    events.onerror = () => { drop(); say('disconnected: start the simulator again'); };
  }
  // the program lets go of what this page held: forget it here too
  function drop() { letGo(); clearInterval(beatTimer); queue.length = 0; client = null; canvas.style.cursor = ''; clear(); }
  function disconnect() { if (engine) engine.close(); else if (events) events.close(); drop(); }
  if (!document.hidden) connect();     // (a page that loads hidden connects once it shows)
  // one request at a time, so the actions arrive in order; what comes up meanwhile goes in the next ones, ACTS_MAX
  // each. An empty one every BEAT_MS says that the page is still there. A request that is refused, lost or hangs
  // (given up after two of those) may have dropped a release, so the page starts again as a new client: closing
  // its stream makes the program let go of everything the old one held, and what still arrives for it is refused.
  // The engine takes the actions at once.
  function send(...lines) {
    if (engine) { if (client !== null) engine.act(lines); return; }
    queue.push(...lines); flush();
  }
  function restart(from) {
    if (from !== client) return;       // (already started again)
    disconnect();
    if (!document.hidden) connect();
  }
  async function flush() {
    if (busy || client === null || !(queue.length || beat)) return;
    busy = true; beat = false;
    const body = queue.splice(0, ACTS_MAX).join('\n'), from = client;
    // (not AbortSignal.timeout: the browsers of older tablets lack it)
    const abort = new AbortController(), timer = setTimeout(() => abort.abort(), 2 * BEAT_MS);
    try {
      const r = await fetch(`sim/act?client=${from}`, { method: 'POST', body, signal: abort.signal });
      if (!r.ok && r.status !== 409) console.warn('sim.page:', r.status, await r.text());
      if (!r.ok) restart(from);
    } catch (e) { restart(from); } finally { clearTimeout(timer); }
    busy = false; flush();
  }

  // ---------------- picking ----------------
  const ray = new THREE.Raycaster(), ndc = new THREE.Vector2(), inv = new THREE.Matrix4(), local = new THREE.Ray();
  const caps = [];
  for (const key of V.keys) for (const m of key.meshes) { m.userData.sim = { key }; caps.push(m); }
  const aim = e => {
    const r = canvas.getBoundingClientRect();
    ndc.set((e.clientX - r.left) / r.width * 2 - 1, (r.top - e.clientY) / r.height * 2 + 1);
    ray.setFromCamera(ndc, camera);
  };
  // where the pointer's ray meets the panel's plane at height h, from a knob's axis: [x, y] mm, y towards the user
  function onPlane(knob, h) {
    local.copy(ray.ray).applyMatrix4(inv.copy(assembly.matrixWorld).invert());
    const t = (h - local.origin.y) / local.direction.y;
    return [local.origin.x + t * local.direction.x - V.px(knob.x), local.origin.z + t * local.direction.z - V.pz(knob.y)];
  }
  // what is under the pointer: { key }, { knob, ring } or { knob: RANGE, tilt }
  function pick(e) {
    aim(e);
    for (const knob of KNOBS) {
      if (knob === RANGE) {            // the knob, or round it on the plate the arrows
        const [x, y] = onPlane(knob, Z), d = Math.hypot(x, y);
        if (d <= ARROWS[0]) return { knob, ring: 'ring' };
        if (d <= ARROWS[1]) return { knob, tilt: Math.abs(x) > Math.abs(y) ? (x > 0 ? 'RIGHT' : 'LEFT') : (y > 0 ? 'DN' : 'UP') };
      } else {                         // one plane, halfway up the inner knob: the same target from every side
        const d = Math.hypot(...onPlane(knob, (TOP.inner + TOP.outer) / 2));
        if (d <= R_OUT) return { knob, ring: d <= R_IN ? 'inner' : 'outer' };
      }
    }
    const hit = ray.intersectObjects(caps, false)[0];
    return hit && hit.object.userData.sim;
  }
  // a mouse pointer is a hand over what a click would operate. That is a hit test per move and no frame drawn; a
  // finger has no pointer to show.
  canvas.addEventListener('pointermove', e => {
    if (e.pointerType !== 'touch') canvas.style.cursor = client && pick(e) ? 'pointer' : '';
  });

  // ---------------- pressing, turning ----------------
  // a switch or a part held by two fingers at once goes down once and up when both have let go
  const downs = new Map(), shown = new Map();
  const count = (map, k, d) => { const n = (map.get(k) || 0) + d; map.set(k, n); return n; };
  const names = at => at.key ? [inputs.keys[at.key.label]] : at.tilt
    ? [inputs.knobs.RANGE.push, inputs.knobs.RANGE.tilt[at.tilt]] : [inputs.knobs[at.knob.name].push];
  // A cap or knob eases down and back up, shrinking a little round its middle and a cap darkening as it goes.
  // RANGE leans towards the arrow held instead, on a group round its parts at the lever's fulcrum (the RKJXT's,
  // over the PCB top as the panel's heights are), so it still turns and pushes in it. With reduced motion it jumps.
  const presses = new Map();           // a key or knob: its meshes, where they rest, how far down it is drawn
  const lean = new THREE.Group();
  {
    const [first] = RANGE.rings.ring;
    first.parent.add(lean);
    lean.position.set(V.px(RANGE.x), G.rkjxt.fulcrum, V.pz(RANGE.y));
    lean.updateMatrixWorld(true);
    for (const m of RANGE.rings.ring) lean.attach(m);
  }
  const LEAN = { RIGHT: [1, 0], LEFT: [-1, 0], DN: [0, 1], UP: [0, -1] };   // towards x, towards the user
  const leans = [];                    // the arrows held, in the order they went down: RANGE leans to the last one
  function tilt(at, d) {
    const n = count(shown, lean, d);
    if (d > 0) leans.push(at.tilt);
    else leans.splice(leans.lastIndexOf(at.tilt), 1);
    if (!presses.has(lean)) presses.set(lean, { lean: true, target: [0, 0], drawn: [0, 0] });
    const s = presses.get(lean);
    clearTimeout(s.upTimer);
    const move = () => { s.target = leans.length ? LEAN[leans.at(-1)] : [0, 0]; animate(); };
    if (d > 0) { s.downAt = performance.now(); move(); if (n === 1) sound('down'); }
    else if (n) move();
    else s.upTimer = setTimeout(() => { move(); sound('up'); }, V.reduce ? 0 : Math.max(s.downAt + SHOWN_MS - performance.now(), 0));
  }
  function show(at, d) {
    if (at.tilt) return tilt(at, d);
    const part = at.key || at.knob, n = count(shown, part, d);
    if (n !== (d > 0 ? 1 : 0)) return;
    if (!presses.has(part)) {
      const meshes = at.key ? at.key.meshes : Object.values(at.knob.rings).flat();
      // a cap's own materials, to darken it alone (its body's is shared by every cap)
      const lit = at.key ? meshes.map(m => (m.material = m.material.clone()).color.clone()) : [];
      presses.set(part, { meshes, rest: meshes.map(m => m.position.clone()), lit, face: at.key && meshes[1],
        target: 0, drawn: 0 });
    }
    const s = presses.get(part);
    clearTimeout(s.upTimer);
    const move = () => { s.target = d > 0 ? 1 : 0; sound(d > 0 ? 'down' : 'up'); animate(); };
    if (d > 0) { s.downAt = performance.now(); move(); }
    else s.upTimer = setTimeout(move, V.reduce ? 0 : Math.max(s.downAt + SHOWN_MS - performance.now(), 0));
  }
  function press(dt) {                 // the drawn travels dt ms on, closer to their targets; true while one moves
    let moving = false;
    for (const s of presses.values()) {
      if (s.lean) {                    // RANGE's lean, [towards x, towards the user], to the arrow or back up
        const k = Math.exp(-dt / (s.target[0] || s.target[1] ? PRESS_TAU_MS : LIFT_TAU_MS));
        s.drawn = s.drawn.map((v, i) => s.target[i] + (v - s.target[i]) * k);
        if (Math.hypot(s.drawn[0] - s.target[0], s.drawn[1] - s.target[1]) < PRESS_DONE) s.drawn = [...s.target];
        else moving = true;
        lean.rotation.set(TILT * s.drawn[1], 0, -TILT * s.drawn[0]);   // its top towards the arrow
        continue;
      }
      s.drawn = s.target + (s.drawn - s.target) * Math.exp(-dt / (s.target ? PRESS_TAU_MS : LIFT_TAU_MS));
      if (Math.abs(s.target - s.drawn) < PRESS_DONE) s.drawn = s.target;
      else moving = true;
      const size = 1 - (1 - PRESSED_SIZE) * s.drawn, light = 1 - (1 - PRESSED) * s.drawn, mid = s.rest[0];
      s.meshes.forEach((m, i) => {
        const r = s.rest[i];
        m.position.set(mid.x + (r.x - mid.x) * size, r.y - s.drawn * TRAVEL, mid.z + (r.z - mid.z) * size);
        if (m === s.face) m.scale.set(size, size, 1); else m.scale.set(size, 1, size);   // (the face lies turned)
        if (s.lit[i]) m.material.color.copy(s.lit[i]).multiplyScalar(light);
      });
    }
    invalidate();
    return moving;
  }
  function hold(g) {
    g.held = names(g);
    send(...g.held.filter(n => count(downs, n, 1) === 1).map(n => `press ${n}`)); show(g, 1);
  }
  function release(g) {
    if (!g.held) return;
    send(...g.held.reverse().filter(n => count(downs, n, -1) === 0).map(n => `release ${n}`)); show(g, -1);
    g.held = null;
  }
  // A ring turns smoothly to where its detents put it, as the eye would match each flute to the nearest one after
  // a jump of 12 degrees and see the ring step backwards. A fast spin moves the target on and the ring follows it.
  // With reduced motion it jumps.
  const spins = new Map();             // a ring's meshes: { target angle, angle drawn }
  function turn(knob, ring, n) {
    send(`turn ${inputs.knobs[knob.name][ring]} ${n}`);
    sound('detent', Math.abs(n));
    const meshes = knob.rings[ring];
    if (!spins.has(meshes)) spins.set(meshes, { target: meshes[0].rotation.y, drawn: meshes[0].rotation.y });
    spins.get(meshes).target -= n * DETENT;                          // clockwise seen from above
    animate();
  }
  function spin(dt) {                  // the drawn angles dt ms on, closer to their targets; true while one moves
    let moving = false;
    for (const [meshes, s] of spins) {
      s.drawn = s.target + (s.drawn - s.target) * Math.exp(-dt / SPIN_TAU_MS);
      if (Math.abs(s.target - s.drawn) < SPIN_DONE) s.drawn = s.target;
      else moving = true;
      for (const m of meshes) m.rotation.y = s.drawn;
    }
    invalidate();
    return moving;
  }
  // frames are drawn only while a ring turns or a part goes down or up
  let frameAt = null;
  const step = dt => [spin(dt), press(dt)].some(Boolean);
  function animate() {
    if (V.reduce) step(Infinity);
    else if (frameAt === null) { frameAt = performance.now(); requestAnimationFrame(frame); }
  }
  function frame(now) {
    const moving = step(Math.max(now - frameAt, 0));   // (a frame's time can be from before the press or turn)
    frameAt = moving ? now : null;
    if (moving) requestAnimationFrame(frame);
  }
  const gestures = new Map();          // pointer ID: what it holds or turns
  function letGo() {
    for (const g of gestures.values()) { clearTimeout(g.timer); release(g); }
    gestures.clear();
  }

  // the angle of the pointer round the knob's axis, on the touched ring's top; null in the middle, where it is a
  // finger's jitter (margin: to leave the middle, a finger goes this much further out, so it does not flicker)
  const angleOf = (g, margin) => {
    const [x, y] = onPlane(g.knob, TOP[g.ring]);
    return Math.hypot(x, y) < AXIS_MM + margin ? null : Math.atan2(y, x);
  };
  canvas.addEventListener('pointerdown', e => {
    if (e.button !== 0 || !client) return;
    wake();
    const at = pick(e);
    if (!at) return;
    // one finger per knob, and two on it are no tap: one that has not moved yet hands the knob to the next one
    const [id, first] = [...gestures].find(([, g]) => at.ring && g.knob === at.knob) || [];
    if (first && (first.moved || first.held)) { first.moved = true; return; }
    if (first) { clearTimeout(first.timer); gestures.delete(id); }
    canvas.setPointerCapture(e.pointerId);
    const g = { ...at, x: e.clientX, y: e.clientY, held: null, moved: !!first };
    gestures.set(e.pointerId, g);
    if (!g.ring || e.pointerType === 'mouse') return hold(g);
    // a finger on a knob: turns it if it moves round it, pushes it if it stays still: held from HOLD_MS on, or for
    // a moment when it lifts before (up())
    g.angle = angleOf(g, 0);
    g.sum = 0;
    g.timer = setTimeout(() => { if (gestures.get(e.pointerId) === g && !g.moved && !g.held) hold(g); }, HOLD_MS);
  });
  const still = (g, e) => !g.moved && Math.hypot(e.clientX - g.x, e.clientY - g.y) < MOVE_PX;
  canvas.addEventListener('pointermove', e => {
    const g = gestures.get(e.pointerId);
    // the left button let go while another is down: no pointerup comes until that one goes up too
    if (g && e.pointerType === 'mouse' && !(e.buttons & 1)) return up(e);
    if (!g || !g.ring || e.pointerType === 'mouse') return;     // (a mouse turns with the wheel)
    if (!still(g, e)) g.moved = true;
    aim(e);
    const a = angleOf(g, g.angle === null ? AXIS_OUT_MM : 0);
    if (a === null) { g.angle = null; return; }
    if (g.angle !== null) g.sum += Math.atan2(Math.sin(a - g.angle), Math.cos(a - g.angle));
    g.angle = a;
    if (Math.abs(g.sum) >= DETENT / 4) g.moved = true;      // a quarter detent round the axis: a turn, not a tap
    for (; Math.abs(g.sum) >= DETENT; g.sum -= Math.sign(g.sum) * DETENT) turn(g.knob, g.ring, Math.sign(g.sum));
  });
  const up = e => {
    const g = gestures.get(e.pointerId);
    if (!g) return;
    gestures.delete(e.pointerId);
    clearTimeout(g.timer);
    wake();                            // a finger lifting is a gesture, where audio may start (a touch going down is none)
    // a finger that did not move and is not holding the push yet: a quick tap, or one that lifts before its hold
    // came round (a busy page runs the timer late), pushes the knob for a moment
    if (g.ring && !g.held && e.type === 'pointerup' && still(g, e)) hold(g);
    release(g);
  };
  canvas.addEventListener('pointerup', up);
  canvas.addEventListener('pointercancel', up);
  // A detent per notch of the wheel, a spin's first event a notch at least. A mouse sends whole notches, of any
  // pixels (the page's zoom, the system's settings), one or several in an event: its notch is the smallest event
  // of the spin, and every event is a whole number of them. A spin whose first event is under NOTCH_MIN_PX, or
  // whose events stop being whole notches, is a touchpad's: a detent per WHEEL_PX, counting the first as one.
  const whole = (a, b) => a / b > 0.9 && Math.abs(a / b - Math.round(a / b)) < 0.1;   // a is a whole number of b
  let wheel = null;                    // the spin: { at: its last event, mouse, notch px, total px, sent detents }
  canvas.addEventListener('wheel', e => {
    e.preventDefault();                // no zoom, of the view or the page
    const at = client && pick(e);
    const dy = e.deltaMode ? Math.sign(e.deltaY) * WHEEL_PX : e.deltaY, size = Math.abs(dy);
    if (!at || !at.ring || !dy) return;
    wake();                            // (no gesture: audio starts here only once the page has had one)
    if (!wheel || e.timeStamp - wheel.at > WHEEL_GAP_MS) {
      const mouse = size >= NOTCH_MIN_PX;
      wheel = { mouse, notch: mouse ? size : WHEEL_PX, total: mouse ? dy : Math.sign(dy) * WHEEL_PX, sent: 0 };
    } else if (!wheel.mouse) wheel.total += dy;
    else if (size >= NOTCH_MIN_PX && whole(wheel.notch, size)) { wheel.notch = size; wheel.total += dy; }   // a smaller notch
    else if (whole(size, wheel.notch)) wheel.total += dy;
    else Object.assign(wheel, { mouse: false, notch: WHEEL_PX, total: wheel.sent * WHEEL_PX + dy });
    wheel.at = e.timeStamp;
    const notches = wheel.total / wheel.notch;                         // (a hair more: a sum of fractions is whole)
    const n = Math.max(-TURN_MAX, Math.min(TURN_MAX, Math.trunc(notches + Math.sign(notches) * 1e-9) - wheel.sent));
    if (n) { wheel.sent += n; turn(at.knob, at.ring, -n); }           // up: clockwise
  }, { passive: false });
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) disconnect();
    else if (engine || !events || events.readyState === EventSource.CLOSED) connect();
  });
  window.addEventListener('blur', letGo);
};
