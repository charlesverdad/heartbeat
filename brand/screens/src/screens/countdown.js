// Welcome countdown: logo and timer along one edge, messages in the middle, the last ten seconds big,
// and at zero the logo travels to the centre and stays.
(function () {
  const { clamp, lerp, ease, ep } = HB;

  // Messages take turns in the middle every 12 seconds. Each is a list of lines; long lines shrink to fit.
  const DEFAULT_MESSAGES = [
    ['Welcome to', 'Heartbeat Church'],
    ['Living Out The Gospel', 'Together Wholeheartedly'],
    ['Grab a coffee', 'and find a seat'],
    ['We’re glad', 'you’re here'],
  ];
  const SLOT = 12;   // seconds per message
  const FINALE = 10; // the last seconds count down big
  const LOGO_AR = 252.2 / 111.27;

  const schema = [
    ...HB.timerSchema,
    { key: 'bar', type: 'seg', label: 'Bar', options: [['top', 'Top'], ['bottom', 'Bottom']], default: 'top', param: 'bar' },
    HB.THEME,
    { key: 'big', type: 'check', label: 'Last 10 s', text: 'Count down in big numbers', default: true, param: 'big' },
    { key: 'messages', type: 'lines', label: 'Messages', default: DEFAULT_MESSAGES, param: 'm' },
  ];

  // ---------- DOM ----------
  const $ = id => document.getElementById(id);
  const stage = $('stage'), big = $('big'), fill = $('fill'), rule = $('rule'), row = $('row');
  const slotEl = $('slot'), logo = $('logo');
  logo.innerHTML = HB.lockupSVG();
  const setClock = HB.rollClock($('clock'));

  let msgEls = [];
  function setMessages(list) {
    $('msgs').innerHTML = '';
    msgEls = list.map(lines => {
      const d = document.createElement('div');
      d.className = 'msg';
      lines.forEach(l => {
        const r = d.appendChild(document.createElement('div'));
        r.appendChild(document.createElement('span')).textContent = l;
      });
      return $('msgs').appendChild(d);
    });
    if (geo) fitMessages();
  }
  // Shrink any message that is too wide or too tall for its space.
  function fitMessages() {
    const W = stage.clientWidth, H = stage.clientHeight;
    const maxW = W * (stage.classList.contains('portrait') ? 0.84 : 0.86);
    msgEls.forEach(m => HB.fitText(m, maxW, H * 0.62));
  }

  // Where the logo sits in the footer and where it lands at zero, in px. Measured on resize.
  let geo = null;
  function measure({ W, H, portrait }) {
    const r = slotEl.getBoundingClientRect();
    const h1 = Math.min(portrait ? (W * 0.3) : H * 0.26, (W * 0.72) / LOGO_AR);
    geo = {
      w: r.width, h: r.height,
      from: { cx: r.left + r.width / 2, cy: r.top + r.height / 2 },
      to: { cx: W / 2, cy: H / 2 },
      k1: h1 / r.height,
      H,
    };
    logo.style.width = `${r.width}px`;
    logo.style.height = `${r.height}px`;
    fitMessages();
  }

  // Draw the screen for t seconds into a COUNT-second countdown.
  function render(f, SET) {
    const { t, COUNT, n, phase, done, idle } = f;
    setClock(n, phase);
    // With the big final count off, messages run right up to zero.
    const finale = SET.big ? COUNT - FINALE : COUNT;
    const H = geo.H;

    // Messages: each slot fades and rises in, then fades out before the next. None in the final count,
    // and a slot that would only get a moment before them is skipped.
    const slot = Math.floor(t / SLOT);
    msgEls.forEach((m, i) => {
      let o = 0, dy = 0;
      if (idle) o = i === 0 ? 1 : 0;
      else {
        const t0 = slot * SLOT;
        const on = slot % msgEls.length === i && t < finale && t0 + 4 <= finale;
        const kin = on ? ep(t, t0, 0.7) : 0;
        const kout = on ? ep(t, Math.min(t0 + SLOT, finale) - 0.5, 0.5, ease.inCubic) : 0;
        o = kin * (1 - kout);
        dy = (1 - kin) * H * 0.02 - kout * H * 0.01;
      }
      m.style.opacity = o;
      m.style.transform = `translateY(calc(-50% + ${dy}px))`;
    });

    // The last ten seconds count down big, each number popping in on the tick.
    const showBig = SET.big && !idle && !done && n <= FINALE && t >= finale;
    big.textContent = String(n);
    const kp = ease.outCubic(clamp(phase / 0.35));
    big.style.opacity = showBig ? 0.25 + 0.75 * kp : 0;
    big.style.transform = `translateY(-50%) scale(${showBig ? 1.12 - 0.12 * kp : 1})`;

    // At zero the line and timer fade, and the logo travels to the centre and stays.
    const out = idle ? 0 : ep(t, COUNT, 0.5, ease.inCubic);
    fill.style.transform = `scaleX(${idle ? 0 : clamp(t / COUNT)})`;
    rule.style.opacity = 1 - out;
    row.style.opacity = 1 - out;
    const km = idle ? 0 : ep(t, COUNT + 0.3, 1.2, ease.inOutCubic);
    const k = lerp(1, geo.k1, km);
    const cx = lerp(geo.from.cx, geo.to.cx, km), cy = lerp(geo.from.cy, geo.to.cy, km);
    logo.style.transform = `translate(${cx - (geo.w * k) / 2}px, ${cy - (geo.h * k) / 2}px) scale(${k})`;
  }

  // ---------- wiring ----------
  let panel;
  const timer = HB.createTimer({
    values: () => panel.values,
    onChange: () => panel.setAction('go', timer.button()),
    keepAwake: () => panel.keepAwake(),
    badTime: () => document.querySelector('.controls input[type=time]')?.focus(),
  });
  const step = d => { if (timer.mode === 'idle' && panel.values.kind === 'minutes') panel.set('mins', clamp(panel.values.mins + d, 1, 180)); };

  panel = HB.panel({
    id: 'countdown',
    title: 'Countdown settings',
    schema,
    legacy: HB.timerLegacy,
    linkKeys: v => [...HB.timerLinkKeys(v), 'bar'],
    skipSave: ['messages'],
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
      else if (key === 'bar') { stage.classList.toggle('bar-bottom', v.bar === 'bottom'); measureNow(); }
      else if (key === 'messages') setMessages(v.messages);
    },
  });

  stage.classList.toggle('bar-bottom', panel.values.bar === 'bottom');
  setMessages(panel.values.messages);
  const measureNow = HB.watchStage(stage, measure);
  timer.reset();
  if (panel.autostart) timer.start();

  if (panel.demo) {
    // Homepage preview: a 22 s run that shows a message, the big final count and the logo landing, then loops.
    // ?t=N skips ahead N seconds (used by scripts/check.mjs to capture the final count and the landed logo).
    const DEMO = { COUNT: 22, LOOP: 32, SKIP: Number(new URLSearchParams(location.search).get('t')) || 0 };
    HB.loop(s => {
      const t = (s + DEMO.SKIP) % DEMO.LOOP;
      render({ idle: false, t, COUNT: DEMO.COUNT, ...HB.tick(t, DEMO.COUNT) }, panel.values);
    });
  } else {
    HB.loop(() => render(timer.frame(), panel.values));
  }
})();
