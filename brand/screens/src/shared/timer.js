// The countdown engine shared by every screen that counts down (countdown, ring, ...):
// schema rows for Timer / Until, the Start / Pause / Reset state machine, and the rolling digit clock.
// Needs core.js. A classic script, like the rest.
(function () {
  const HB = (globalThis.HB = globalThis.HB || {});
  const { clamp, ease, tick, fmt, secondsUntil } = HB;

  // Schema rows. Spread them into a screen's schema: [...HB.timerSchema, ...].
  // `mins` and `at` sit on the same panel row as `kind`.
  HB.timerSchema = [
    { key: 'kind', type: 'seg', label: 'Count', options: [['minutes', 'Timer'], ['until', 'Until']], default: 'minutes', param: 'kind' },
    { key: 'mins', type: 'number', label: 'Minutes', min: 1, max: 180, unit: 'min', default: 5, param: 'min', inline: true, when: v => v.kind === 'minutes' },
    { key: 'at', type: 'time', label: 'Start time', default: '11:00', param: 'at', inline: true, when: v => v.kind === 'until' },
  ];
  // Old links: ?at=11:00 means Until, ?min=5 means Timer. Pass as the `legacy` arg of HB.fromParams.
  HB.timerLegacy = (out, params) => {
    if (params.get('at')) out.kind = 'until';
    else if (params.get('min')) out.kind = 'minutes';
    return out;
  };
  // Link keys the countdown always writes, so shared links stay readable.
  HB.timerLinkKeys = v => ['kind', v.kind === 'until' ? 'at' : 'mins'];

  // State machine. mode: 'idle' waiting, 'run' a minutes timer (pausable), 'until' counting to a time of day.
  // opts: { values: () => current settings, onChange(): buttons need re-labelling, keepAwake(), badTime() }
  HB.createTimer = function (opts) {
    const S = { mode: 'idle', COUNT: 300, start: 0, pausedAt: 0, paused: 0 };
    const now = () => Date.now() / 1000;
    const elapsed = () => (S.pausedAt || now()) - S.start - S.paused;
    const changed = () => opts.onChange?.();

    // While idle the clock shows the full count: minutes, or the time left until the chosen start.
    function refresh() {
      if (S.mode !== 'idle') return;
      const v = opts.values();
      S.COUNT = v.kind === 'until' ? Math.max(1, Math.ceil(secondsUntil(v.at) ?? 0)) : clamp(Math.round(Number(v.mins) || 5), 1, 180) * 60;
    }
    function start() {
      const v = opts.values();
      if (S.mode === 'idle') {
        if (v.kind === 'until') {
          const left = secondsUntil(v.at);
          if (left == null) { opts.badTime?.(); return; }
          Object.assign(S, { mode: 'until', start: now(), COUNT: left, pausedAt: 0, paused: 0 });
        } else {
          refresh();
          Object.assign(S, { mode: 'run', start: now(), pausedAt: 0, paused: 0 });
        }
        opts.keepAwake?.();
      } else if (S.mode === 'run' && elapsed() < S.COUNT) {
        if (S.pausedAt) { S.paused += now() - S.pausedAt; S.pausedAt = 0; } else S.pausedAt = now();
      }
      changed();
    }
    function reset() {
      Object.assign(S, { mode: 'idle', pausedAt: 0, paused: 0 });
      opts.letSleep?.();
      refresh();
      changed();
    }
    // Changing the time while counting to it re-aims the countdown.
    function retarget() { if (S.mode === 'until') { S.mode = 'idle'; start(); } }
    // The Start button's face for the current state.
    const button = () => ({
      text: S.mode === 'idle' ? 'Start' : S.mode === 'until' ? 'Running' : S.pausedAt ? 'Resume' : 'Pause',
      disabled: S.mode === 'until',
    });
    // What to draw right now: { idle, t, COUNT, n, phase, done }.
    function frame() {
      refresh();
      if (S.mode === 'idle') return { idle: true, t: 0, COUNT: S.COUNT, n: S.COUNT, phase: 1, done: false };
      const t = elapsed();
      return { idle: false, t, COUNT: S.COUNT, ...tick(t, S.COUNT) };
    }
    return { S, start, reset, retarget, button, frame, refresh, get mode() { return S.mode; } };
  };

  // Everything a countdown screen shares: the timer, its panel rows wired to it, Start/Reset, keys,
  // autostart and the homepage demo loop. The screen supplies its own rows (`schema`, after the timer
  // rows), what to do when they change (`onChange`), and `render(frame, values)`.
  //   HB.countdownScreen({ id, title, schema, linkKeys, skipSave, onChange, render })
  HB.countdownScreen = function (o) {
    let panel;
    const timer = HB.createTimer({
      values: () => panel.values,
      onChange: () => panel.setAction('go', timer.button()),
      keepAwake: () => panel.keepAwake(),
      letSleep: () => panel.letSleep(),
      badTime: () => document.querySelector('.controls input[type=time]')?.focus(),
    });
    const step = d => { if (timer.mode === 'idle' && panel.values.kind === 'minutes') panel.set('mins', clamp(panel.values.mins + d, 1, 180)); };
    panel = HB.panel({
      id: o.id,
      title: o.title,
      schema: o.schema,
      legacy: HB.timerLegacy,
      linkKeys: v => [...HB.timerLinkKeys(v), ...(o.linkKeys || [])],
      skipSave: o.skipSave,
      startable: true,
      actions: [
        { id: 'reset', label: 'Reset', onclick: () => timer.reset() },
        { id: 'go', label: 'Start', primary: true, onclick: () => timer.start() },
      ],
      keyHelp: [['Space', 'start / pause'], ['R', 'reset']],
      keys: { ' ': () => timer.start(), r: () => timer.reset(), arrowup: () => step(1), arrowdown: () => step(-1) },
      enter: () => timer.start(),
      onChange(key, v) {
        if (key === 'kind') timer.reset();
        else if (key === 'mins') timer.refresh();
        else if (key === 'at') timer.retarget();
        else o.onChange?.(key, v);
      },
    });
    // Let the screen set itself up from the settings before the first frame.
    o.ready?.(panel.values);
    timer.reset();
    if (panel.autostart) timer.start();

    if (panel.demo) {
      // Homepage preview: a 32 s loop that starts 22 s from zero, so it shows the last stretch, the final
      // count and the landing. ?t=N skips ahead N seconds (scripts/check.mjs uses it for the late moments).
      const COUNT = 22, LOOP = 32, SKIP = Number(new URLSearchParams(location.search).get('t')) || 0;
      HB.loop(s => {
        const t = (s + SKIP) % LOOP;
        o.render({ idle: false, t, COUNT, ...HB.tick(t, COUNT) }, panel.values);
      });
    } else {
      HB.loop(() => o.render(timer.frame(), panel.values));
    }
    return { panel, timer };
  };

  // The clock: one span per character so digits that change can roll in (rise 0.1em and fade up over 0.3 s).
  HB.rollClock = function (el) {
    let cells = [], shown = null;
    return function set(n, phase) {
      const str = fmt(n), prev = fmt(n + 1);
      if (cells.length !== str.length) {
        el.innerHTML = '';
        cells = [...str].map(() => el.appendChild(document.createElement('span')));
      }
      const k = ease.outCubic(clamp(phase / 0.3));
      cells.forEach((c, i) => {
        // Only touch the DOM when something changed, so a settled clock costs no layout.
        if (c.textContent !== str[i]) c.textContent = str[i];
        const rolling = phase < 0.3 && prev.length === str.length && str[i] !== prev[i];
        const tf = rolling ? `translateY(${(k - 1) * 0.1}em)` : '', op = rolling ? String(0.15 + 0.85 * k) : '1';
        if (c.style.transform !== tf) c.style.transform = tf;
        if (c.style.opacity !== op) c.style.opacity = op;
      });
      if (n !== shown) { shown = n; el.setAttribute('aria-label', `${Math.floor(n / 60)} minutes ${n % 60} seconds`); }
    };
  };
})();
