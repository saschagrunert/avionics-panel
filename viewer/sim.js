// The panel page: index.html loads this when python3 -m sim.page (sim/page.py) serves it with ?sim. The firmware
// runs in that program; this page sends it raw input events as they happen and shows what comes back: the lights,
// the buttons each joystick reports, a firmware error and a lost connection. The camera stays put.
//   key cap: pointer down presses it, up (or cancel) lets go
//   knob: the inner knob, or the outer ring round it, by the pointer's distance from the knob's axis. The wheel
//     turns that ring, a detent per notch; a mouse button pushes the knob as long as it is down. A finger turns the
//     ring it touched by moving round the knob, a detent per 12 degrees as the real one, and a quick tap that does
//     not move, not even a quarter detent round the knob, pushes it; anything else a finger does on a knob does
//     nothing. One finger per knob at a time: a second one takes the knob over if the first has not moved.
//   the pan arrows round RANGE: held, RANGE tilts that way
// Over any of these the mouse pointer is a hand. Everything the page holds is let go when it is hidden or loses
// the focus; the program lets go of it when the page goes, also when the page stops telling it that it is still
// there (a tablet off the network).
window.playPanel = function playPanel(V) {
  const { G, camera, controls, canvas, assembly, go, invalidate } = V;
  const RANGE = V.knobs.range, KNOBS = Object.values(V.knobs);
  const MOVE_PX = 8;                   // a finger that moves this far from where it touched is no tap
  const TAP_MS = 400;                  // ... nor one that stays longer than this
  const AXIS_MM = 2.5;                 // closer to the axis than this the angle round it is a finger's jitter
  const AXIS_OUT_MM = 1;               // ... and a finger leaves that middle this much further out
  const WHEEL_GAP_MS = 300;            // a wheel event this long after the last starts a new spin: a notch at least
  const NOTCH_MIN_PX = 20;             // a spin whose first event is this large is a mouse's; a smaller one is a
                                       // touchpad's ...
  const WHEEL_PX = 100;                // ... which sums up to a notch this large (and Firefox's lines count as one)
  const LINE_PX = 21;                  // a line at the bottom left: 14 px type, 1.5 high ...
  const LINES_W_PX = 324;              // ... their width at most: three buttons a line ...
  const KEYS_W_PX = 480;               // ... in keyboard mode the longest shortcut's line. A longer line ends in an
                                       // ellipsis: they never wrap, so the panel does not move for them.
  const FOV = 10;                      // degrees: from about straight above everywhere, so the knobs lean little
  const SPIN_TAU_MS = 25;              // a ring eases to its detent: most of the way in about 80 ms (3 of these)
  const SPIN_DONE = 0.001;             // radians from the target: there
  const TRAVEL = 1;                    // mm a pressed cap or pushed knob goes down
  const PRESSED = 0x505050;            // the glow of a pressed cap's legend face
  const FADE_MS = 1000;                // a button stays in the list, dimmed, this long after it went
  const ALERT_MS = 10000;              // a firmware error shows this long
  const Z = G.plate.z1, R_IN = G.inner_knob.d / 2 + 0.5;    // the inner knob, with its edge leaning out a little
  const R_OUT = 1.5 * G.outer_knob.d / 2;                    // the outer ring, and a margin round it as large again
  const TOP = { inner: Z + G.inner_knob.z1, outer: Z + G.outer_knob.z1, ring: Z + G.range_knob.z1 };
  const ARROWS = [G.plate_art.range.arrow_r - 1.5, G.plate_art.range.arrow_r + 5];   // the arrows' ring round RANGE

  // ---------------- what the page shows ----------------
  const style = document.createElement('style');
  style.textContent = `
    body.play .bar, body.play .legend, body.play #dims, body.play .links { display: none; }
    /* the lines can lie over the plate and the banner over the top keys: a ground of their own, and no taps taken */
    .sim { position: fixed; left: max(16px, env(safe-area-inset-left, 0px)); bottom: calc(16px + env(safe-area-inset-bottom, 0px));
           font: 14px var(--mono); color: var(--panel-fg); pointer-events: none; line-height: 1.5;
           max-width: min(calc(100% - 32px), ${LINES_W_PX}px);
           background: var(--panel); padding: 4px 8px; border-radius: 8px; box-sizing: border-box; }
    .sim > div { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .sim .gone { opacity: .45; }
    /* under the name and the hint line (place() sets its top) */
    .sim-alert { position: fixed; top: 76px; left: 50%; transform: translateX(-50%); max-width: calc(100% - 32px);
                 padding: 8px 14px; border-radius: 9px; background: var(--on); color: var(--on-fg); font: 500 14px var(--font);
                 pointer-events: none; }
    .sim:empty, .sim-alert:empty { display: none; }`;
  document.head.appendChild(style);
  document.body.classList.add('play');
  const strip = document.createElement('div'), alert = document.createElement('div');
  strip.className = 'sim'; alert.className = 'sim-alert'; alert.setAttribute('role', 'alert');
  document.body.append(strip, alert);
  document.querySelector('.mouse').textContent =
    'click a key or knob · the wheel on a knob turns the ring under the pointer · hold an arrow round RANGE to tilt';
  document.querySelector('.touch').textContent =
    'tap a key · move round a knob to turn the ring you touched · tap a knob to push · hold an arrow round RANGE to tilt';
  for (const L of V.lights) if (L.name === 'UNIT') L.lens.color.setHex(0x1d1e21).convertSRGBToLinear();   // dark when off
  controls.enableRotate = controls.enableZoom = controls.enablePan = false;
  V.ground.visible = false;            // from above its shadow is a grey slab beside the panel
  canvas.addEventListener('contextmenu', e => e.preventDefault());
  camera.fov = FOV;                    // (the next frame updates the projection)
  controls.maxDistance = Infinity;     // the narrow view stands further off than the zoom limit of the others
  // The panel goes under the name and the hint, and beside the lines at the bottom left or with all it operates
  // above them, whichever shows it larger (beside them in a wide, short window); the lines may lie over the plate's
  // edge below the RANGE arrows. The alert goes under the name and the hint. Again after a resize, and when the
  // number of lines changes.
  const header = document.querySelector('.hdr');
  let lines = 3, width = LINES_W_PX;   // the lines: UNIT and each joystick's buttons, or UNIT and the keyboard's
  assembly.updateMatrixWorld();
  const operated = new THREE.Box3();   // round the caps, the knobs and the arrows round RANGE
  for (const m of [...V.keys.flatMap(k => k.meshes), ...KNOBS.flatMap(k => Object.values(k.rings).flat())]) operated.expandByObject(m);
  for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
    operated.expandByPoint(assembly.localToWorld(new THREE.Vector3(V.px(RANGE.x + dx * ARROWS[1]), Z, V.pz(RANGE.y + dy * ARROWS[1]))));
  }
  const above = V.view.box.clone();    // the panel's box, its side towards the pilot (+z, the bottom) at the arrows
  above.max.z = operated.max.z;
  V.view.margins = () => {             // [top, right, bottom, left] px kept free round a box, each way (fit() adds a gap)
    const css = getComputedStyle(strip), top = header.getBoundingClientRect().bottom;
    const bottom = parseFloat(css.bottom), left = parseFloat(css.left) + width;
    return [[top, 0, bottom + lines * LINE_PX + 8, 0, above], [top, 0, bottom, left, V.view.box]];   // (8: their padding)
  };
  function place() { alert.style.top = `${header.getBoundingClientRect().bottom + 8}px`; go('P', true); }
  window.addEventListener('resize', place);
  place();
  let alertTimer;
  const say = (text, ms) => { clearTimeout(alertTimer); alert.textContent = text; if (ms) alertTimer = setTimeout(() => say(''), ms); };

  // the lights in words, and each joystick's buttons (in keyboard mode the keyboard's function and shortcut); one
  // that went stays a while, dimmed
  let lights = {}, buttons = {}, fadeTimer;
  let went = {};                       // device: { button: when it went }
  function render() {
    clearTimeout(fadeTimer);
    strip.textContent = '';
    if (!Object.keys(buttons).length) return;
    const line = (...parts) => { const d = document.createElement('div'); d.append(...parts); strip.appendChild(d); };
    line(`UNIT ${lights.UNIT ? 2 : 1}${lights.SHIFT ? ' · SHIFT' : ''}`);
    const now = performance.now();
    let next = Infinity;
    for (const [device, names] of Object.entries(buttons)) {
      const old = Object.entries(went[device] || {}).filter(([n, at]) => now - at < FADE_MS && !names.includes(n));
      for (const [, at] of old) next = Math.min(next, at + FADE_MS - now);
      const parts = [...names.map(n => [n, '']), ...old.map(([n]) => [n, 'gone'])].flatMap(([n, cls], i) => {
        const s = document.createElement('span'); s.textContent = n; s.className = cls;
        return i ? [' · ', s] : [s];
      });
      line(device === 'keyboard' ? 'keyboard: ' : `joystick ${device}: `, ...(parts.length ? parts : ['none']));
    }
    if (next < Infinity) fadeTimer = setTimeout(render, Math.ceil(next) + 1);
  }
  function update(state) {
    const now = performance.now();
    for (const [device, names] of Object.entries(buttons)) {
      const still = state.buttons[device] || [];
      for (const n of names) if (!still.includes(n)) (went[device] = went[device] || {})[n] = now;
    }
    ({ lights, buttons } = state);
    const count = 1 + Object.keys(buttons).length;
    if (count > 1 && count !== lines) {          // the mode is known: the lines' number and width
      lines = count; width = buttons.keyboard ? KEYS_W_PX : LINES_W_PX;
      strip.style.maxWidth = `min(calc(100% - 32px), ${width}px)`; go('P', true);
    }
    for (const L of V.lights) L.lens.emissiveIntensity = lights[L.name];
    render(); invalidate();
  }
  function clear() {
    went = {}; buttons = {};
    update({ lights: { SHIFT: 0, UNIT: 0 }, buttons: {} });
  }
  clear();

  // ---------------- the program ----------------
  // hello names this page (client), the build of the files the program serves, the firmware's inputs under the caps
  // and knobs, and the program's numbers: the angle of a detent, the detents one action takes and the actions one
  // request takes at most, and how often the page tells the program that it is still there. A page that reconnects
  // to another build, as after a newer simulator was unpacked and started, reloads: its files go with the old one.
  let events, client = null, build = null, inputs = null, busy = false, beat = false, beatTimer;
  let DETENT, TURN_MAX, ACTS_MAX, BEAT_MS;
  const queue = [];
  function connect() {
    say('connecting…');
    events = new EventSource('sim/events');
    events.addEventListener('hello', e => {
      const hello = JSON.parse(e.data);
      if (build !== null && hello.build !== build) { events.close(); location.reload(); return; }
      ({ client, build, inputs, turn_max: TURN_MAX, acts_max: ACTS_MAX, beat_ms: BEAT_MS } = hello);
      DETENT = 2 * Math.PI / hello.detents;
      clearInterval(beatTimer);
      beatTimer = setInterval(() => { beat = true; flush(); }, BEAT_MS);
      say('');
    });
    events.addEventListener('state', e => update(JSON.parse(e.data)));
    events.addEventListener('fault', e => say(`Firmware error, code.py reloaded: ${JSON.parse(e.data).message}`, ALERT_MS));
    events.onerror = () => { drop(); say('disconnected: start the simulator again'); };
  }
  // the program lets go of what this page held: forget it here too
  function drop() { letGo(); clearInterval(beatTimer); queue.length = 0; client = null; canvas.style.cursor = ''; clear(); }
  function disconnect() { if (events) events.close(); drop(); }
  if (!document.hidden) connect();     // (a page that loads hidden connects once it shows)
  // one request at a time, so the actions arrive in order; what comes up meanwhile goes in the next ones, ACTS_MAX
  // each. An empty one every BEAT_MS says that the page is still there. A request that is refused, lost or hangs
  // (given up after two of those) may have dropped a release, so the page starts again as a new client: closing
  // its stream makes the program let go of everything the old one held, and what still arrives for it is refused.
  function send(...lines) { queue.push(...lines); flush(); }
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
  function show(at, d) {
    const part = at.key || at.knob, n = count(shown, part, d);
    if (n !== (d > 0 ? 1 : 0)) return;
    const meshes = at.key ? at.key.meshes : Object.values(at.knob.rings).flat();
    for (const m of meshes) m.position.y -= d * TRAVEL;
    if (at.key) { const [, legend] = at.key.meshes; legend.material.emissive.setHex(d > 0 ? PRESSED : 0); }
    invalidate();
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
  // Frames are drawn only while a ring moves; with reduced motion it jumps.
  const spins = new Map();             // a ring's meshes: { target angle, angle drawn }
  let spinAt = null;
  function turn(knob, ring, n) {
    send(`turn ${inputs.knobs[knob.name][ring]} ${n}`);
    const meshes = knob.rings[ring];
    if (!spins.has(meshes)) spins.set(meshes, { target: meshes[0].rotation.y, drawn: meshes[0].rotation.y });
    spins.get(meshes).target -= n * DETENT;                          // clockwise seen from above
    if (V.reduce) spin(Infinity);
    else if (spinAt === null) { spinAt = performance.now(); requestAnimationFrame(spinFrame); }
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
  function spinFrame(now) {
    const moving = spin(Math.max(now - spinAt, 0));   // (a frame's time can be from before the turn)
    spinAt = moving ? now : null;
    if (moving) requestAnimationFrame(spinFrame);
  }
  const gestures = new Map();          // pointer ID: what it holds or turns
  function letGo() {
    for (const g of gestures.values()) release(g);
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
    const at = pick(e);
    if (!at) return;
    // one finger per knob, and two on it are no tap: one that has not moved yet hands the knob to the next one
    const [id, first] = [...gestures].find(([, g]) => at.ring && g.knob === at.knob) || [];
    if (first && (first.moved || first.held)) { first.moved = true; return; }
    if (first) gestures.delete(id);
    canvas.setPointerCapture(e.pointerId);
    const g = { ...at, x: e.clientX, y: e.clientY, t: e.timeStamp, held: null, moved: !!first };
    gestures.set(e.pointerId, g);
    if (!g.ring || e.pointerType === 'mouse') return hold(g);
    // a finger on a knob: turns it if it moves round it, pushes it on a quick tap (up())
    g.angle = angleOf(g, 0);
    g.sum = 0;
  });
  const still = (g, e) => !g.moved && Math.hypot(e.clientX - g.x, e.clientY - g.y) < MOVE_PX;
  canvas.addEventListener('pointermove', e => {
    const g = gestures.get(e.pointerId);
    // the left button let go while another is down: no pointerup comes until that one goes up too
    if (g && e.pointerType === 'mouse' && !(e.buttons & 1)) return up(e);
    if (!g || !g.ring || g.held) return;
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
    // a quick tap that did not move, judged by the events' own times: the knob's push
    if (g.ring && !g.held && e.type === 'pointerup' && still(g, e) && e.timeStamp - g.t < TAP_MS) hold(g);
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
    else if (!events || events.readyState === EventSource.CLOSED) connect();
  });
  window.addEventListener('blur', letGo);
};
