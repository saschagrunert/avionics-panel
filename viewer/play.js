// The panel in the browser alone, for the page served as plain files (GitHub Pages, or any static server): index.html
// loads this with ?play, before sim.js, and hands sim.js the engine it makes in place of python3 -m sim.page.
// MicroPython in WebAssembly (vendor/micropython.mjs and micropython.wasm, MIT, vendor/micropython-LICENSE: served
// with the page, no request leaves the site) runs the firmware's own panel.py and buttonmap.py with play.py, which
// does what code.py's loop does round them. The engine gives sim.js what sim.page's stream gives it and takes the
// actions sim.js posts to it, so sim.js plays the panel the same way:
//   open({ hello, state, fault, lost }): loads MicroPython and the files the first time (the files again after the
//     panel stopped), then calls hello(...) and state(...) as the stream's events would; lost(message) if they
//     cannot load, or if the panel stops
//   act(lines): press NAME, release NAME, turn RING DETENTS, as sim.js posts them
//   close(): lets go of everything held; the panel's clock stops until the next open
// Nothing loads before the first open. The firmware's files are beside the page in firmware/, where the Pages
// workflow puts them, or, for the page at .../viewer/ (a static server of the repository), in the repository's
// firmware/ beside viewer/; never above another page, as on Pages, where that would be outside the site.
window.playEngine = function playEngine(geometry) {
  const STEP_MS = 10;                  // play.py runs the loop passes up to now this often (sim.page reads the panel
                                       // as often) ...
  const IDLE_MS = 250;                 // ... and this often while it is idle (play.py's idle()): the passes are the
                                       // same, run in larger batches, and an input steps at once
  const BEHIND_MS = 1000;              // a step later than this (a busy or throttled page) moves the panel's clock on
                                       // this far only
  const FIRMWARE = ['panel.py', 'buttonmap.py', 'version.py'];
  const REPOSITORY = /\/viewer\/(index\.html)?$/.test(location.pathname);   // the page of a checkout's viewer/
  let loading = null, play = null, on = null, timer = null, pace = 0;
  // The page's one MicroPython: micropython.mjs keeps its tables of the objects that cross to JS and back, and
  // the Module that frees them, in globalThis, so a second one in the page takes over the first one's, and the
  // first one's JS objects, collected, free the second one's Python objects.
  let python = null;
  // The Play of each panel that stopped, kept to the end of the page: collected, its JS object has MicroPython free
  // it, which crashed Chrome's renderer now and then after a stop (under load, a read out of bounds in the
  // WebAssembly)
  const stopped = [];
  let clock = 0, last = 0;             // the panel's ms at the last step, and performance.now() then
  const now = () => Math.floor(clock + Math.min(performance.now() - last, BEHIND_MS));
  async function text(...urls) {       // the first of urls that the server has: an error or a failed request is none
    for (const url of urls) {
      try {
        const r = await fetch(url);
        if (r.ok) return await r.text();
      } catch (e) { /* the next one */ }
    }
    throw new Error(`${urls[0]} is missing`);
  }
  const OPTIONAL = new Set(['version.py']);   // without it the page only lacks the version line, as code.py's console
  const fetched = (name, urls) => OPTIONAL.has(name) ? text(...urls).catch(() => '') : text(...urls);
  async function load() {             // the files fetched and imported anew, into the page's MicroPython
    const files = [...FIRMWARE.map(name => [name, [`firmware/${name}`, ...(REPOSITORY ? [`../firmware/${name}`] : [])]]),
      ['play.py', ['play.py']]];
    if (!python) {                     // (one that fails to load is tried again at the next open)
      const loaded = python = import(new URL('vendor/micropython.mjs', document.baseURI).href).then(({ loadMicroPython }) =>
        loadMicroPython({ linebuffer: true, stdout: line => console.log(line), stderr: line => console.error(line) }));
      loaded.catch(() => { if (python === loaded) python = null; });
    }
    const [texts, mp] = await Promise.all([Promise.all(files.map(([name, urls]) => fetched(name, urls))), python]);
    files.forEach(([name], i) => mp.FS.writeFile(`/${name}`, texts[i]));   // (before the import)
    const modules = files.map(([name]) => name.replace(/\.py$/, ''));      // imported anew: after a stop, the
                                                                            // modules start as in a new MicroPython
    mp.runPython(`import sys\nfor m in ${JSON.stringify(modules)}:\n    sys.modules.pop(m, None)`);
    // (in an object: a promise would take the Python object's then for a thenable's)
    return { play: mp.pyimport('play').Play(JSON.stringify(geometry.key_legends), JSON.stringify(Object.keys(geometry.knobs))) };
  }
  // what failed: an error's message, of a Python one (a traceback) its last line
  const reason = e => String((e && e.message) || e).trim().split('\n').pop();
  // an error play.py does not take itself (it restarts the panel for one in the panel), in a step or in the start:
  // the panel stops, and the page says so, as when the program stops. The next open (the page shown again after it
  // was hidden, or reloaded) imports the files anew.
  function stop(e) {
    console.error(e);
    clearInterval(timer);
    timer = null;
    pace = 0;
    if (play) stopped.push(play);
    const lost = on && on.lost;
    loading = play = on = null;        // (what the panel held goes with it: sim.js lets go too)
    if (lost) lost(`The panel stopped: ${reason(e)}. Switch to another tab and back, or reload the page, to start it again.`);
  }
  function every(ms) {                 // steps every ms from now on
    if (ms === pace) return;
    clearInterval(timer);
    timer = setInterval(step, ms);
    pace = ms;
  }
  function step() {
    try {
      const t = performance.now();
      clock += Math.min(t - last, BEHIND_MS);
      last = t;
      const out = play.step(Math.floor(clock));
      every(play.idle() ? IDLE_MS : STEP_MS);
      if (!out) return;
      const state = JSON.parse(out);
      if (state.fault) on.fault({ message: state.fault });
      on.state(state);
    } catch (e) { stop(e); }
  }
  return {
    open(handlers) {
      on = handlers;
      if (!loading) loading = load();
      loading.then(loaded => {
        if (on !== handlers) return;   // closed, or opened again, meanwhile
        try {
          play = loaded.play;
          last = performance.now();
          on.hello(JSON.parse(play.hello()));
          pace = 0;                    // (an open after an open without a close: one clock)
          every(STEP_MS);
          step();
        } catch (e) { stop(e); }
      }, e => {
        console.error(e);
        loading = null;                // the next open tries again
        if (on === handlers) on.lost(`The panel could not start in this browser: ${reason(e)}`);
      });
    },
    act(lines) {                       // taken at once: a step now, and STEP_MS from then on (play.py is busy now)
      if (!play || !on) return;
      for (const line of lines) {
        try { play.act(line, now()); } catch (e) { console.warn('play.py:', line, e); }
      }
      step();
    },
    close() {
      clearInterval(timer);
      timer = null;
      pace = 0;
      if (play && on) play.close(now());
      on = null;
    },
  };
};
