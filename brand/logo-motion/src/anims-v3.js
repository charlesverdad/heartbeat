// Round three: loaders, pre-service countdowns and livestream holding screens.
// Same contract as anims.js: setup(s) -> state, frame(s, st, t) sets everything for time t.
//
// Countdowns are real timers: a 5-minute one is 5:00 of video plus a short outro that
// lands on the logo, so it can be started exactly five minutes before the service.
// To make another length, add e.g. countdownPulse(10) to ANIMS_V3 below.
import { MARK_BOX, LOCKUP_BOX, LOGO, clamp, lerp, prog, ep, ease, beat, el, set, tf, markSize, lockupSize } from './core.js';

const MARK_C = [(MARK_BOX[0] + MARK_BOX[2]) / 2, (MARK_BOX[1] + MARK_BOX[3]) / 2];
const LOCKUP_AR = (LOCKUP_BOX[2] - LOCKUP_BOX[0]) / (LOCKUP_BOX[3] - LOCKUP_BOX[1]);
const PARTS = ['H', 'B', 'C'];
const hideWord = s => s.word.setAttribute('display', 'none');
const mod = (a, n) => ((a % n) + n) % n;
const G = (x, c, w) => Math.exp(-(((x - c) / w) ** 2));

// Seamless lub-dub envelope with period P, beat at phase b.
const loopBeat = (t, P, b = 0.25) => {
  const ph = mod(t, P);
  return beat(ph, b, 1, 0.55) + beat(ph + P, b, 1, 0.55) + beat(ph - P, b, 1, 0.55);
};
const beatMark = (s, k) => tf(s.mark, { s: k, ox: MARK_C[0], oy: MARK_C[1] });

// One heart-monitor complex; x is seconds (or any unit) after the beat.
const ecg = x => -0.12 * G(x, 0.02, 0.012) + G(x, 0.045, 0.011) - 0.32 * G(x, 0.07, 0.012) + 0.2 * G(x, 0.32, 0.05) + 0.09 * G(x, 0.88, 0.035);

// ---------- screen-space type ----------
function txt(s, str, { x = s.W / 2, y, size, weight = 700, anchor = 'middle', tracking = -0.01, fill = s.th.fg, parent = s.top }) {
  const t = el('text', { x, y, 'font-family': 'Inter Tight', 'font-weight': weight, 'font-size': size, 'text-anchor': anchor, 'letter-spacing': `${tracking}em`, fill }, parent);
  t.textContent = str;
  return t;
}
const label = (s, str, o) => txt(s, str.toUpperCase(), { weight: 700, tracking: 0.14, fill: s.th.muted, ...o });

// A M:SS clock drawn in fixed-width cells, so the digits never shift as they change.
// y is the baseline; digits are about 0.72 × size tall.
function clock(s, { size, x = s.W / 2, y, anchor = 'middle', parent = s.top, digits = 1 }) {
  const g = el('g', {}, parent);
  const cw = size * 0.6;
  const widths = [...Array(digits).fill(cw), size * 0.3, cw, cw];
  const total = widths.reduce((a, b) => a + b, 0);
  let cx = anchor === 'middle' ? -total / 2 : anchor === 'end' ? -total : 0;
  const cells = widths.map(w => {
    const t = el('text', { x: cx + w / 2, y: 0, 'text-anchor': 'middle', 'font-family': 'Inter Tight', 'font-weight': 700, 'font-size': size, fill: s.th.fg }, g);
    cx += w;
    return t;
  });
  const c = { g, cells, size, digits, x, y, total };
  posClock(c);
  return c;
}
// Scale about the middle of the digits, not the baseline.
function posClock(c, { k = 1, o = 1, dy = 0 } = {}) {
  const m = c.size * 0.36;
  c.g.setAttribute('transform', `translate(${c.x} ${c.y - m + dy}) scale(${k}) translate(0 ${m})`);
  c.g.setAttribute('opacity', clamp(o));
}
const fmt = (n, d) => `${String(Math.floor(n / 60)).padStart(d, '0')}:${String(n % 60).padStart(2, '0')}`;
// n = whole seconds showing; phase = seconds since the display last changed.
function setClock(c, n, phase) {
  const str = fmt(n, c.digits);
  const prev = fmt(n + 1, c.digits);
  const k = ease.outCubic(clamp(phase / 0.3));
  c.cells.forEach((t, i) => {
    t.textContent = str[i];
    const rolling = str[i] !== prev[i];
    t.setAttribute('transform', rolling ? `translate(0 ${(1 - k) * -c.size * 0.1})` : '');
    t.setAttribute('opacity', rolling ? 0.15 + 0.85 * k : 1);
  });
}
// Where the countdown is at time t.
function tick(t, COUNT) {
  const R = COUNT - t;
  if (R <= 0) return { n: 0, phase: -R, done: true };
  const n = Math.ceil(R - 1e-6);
  return { n, phase: n - R, done: false };
}
const tickBeat = phase => beat(phase, 0.15, 1, 0.55);

// Lockup placed by its left edge or centre in screen px.
const lockupW = size => size * LOCKUP_AR;

// ---------- countdown factory ----------
const OUTRO = 5;
function countdown(def) {
  return minutes => {
    const COUNT = minutes * 60;
    return {
      id: `${def.id}-${minutes}m`,
      title: `${def.title} (${minutes}:00)`,
      kind: 'countdown',
      duration: COUNT + OUTRO,
      count: COUNT,
      // The report opens these near the end so the landing is visible straight away.
      previewFrom: COUNT - 12,
      aspects: ['16x9'],
      blurb: def.blurb,
      setup: s => def.setup(s, COUNT),
      frame: (s, st, t) => def.frame(s, st, t, COUNT),
    };
  };
}

// A. Big clock, mark beating once a second underneath.
const countdownPulse = countdown({
  id: 'countdown-pulse',
  title: 'Countdown: pulse',
  blurb: 'A big clock with the mark beneath it, beating once a second. The beat gets stronger in the last ten seconds; at zero the clock clears and the mark comes to the centre.',
  setup(s) {
    hideWord(s);
    const P = s.portrait;
    const size = P ? s.W * 0.3 : s.H * 0.27;
    const cy = P ? s.H * 0.45 : s.H * 0.47;
    const c = clock(s, { size, y: cy + size * 0.36 });
    const lab = label(s, 'Service begins in', { y: cy - size * 0.36 - size * 0.3, size: size * 0.12 });
    const m0 = { cy: P ? s.H * 0.8 : s.H * 0.83, size: P ? s.W * 0.13 : s.H * 0.09 };
    return { c, lab, m0, m1: { cy: s.H / 2, size: markSize(s) } };
  },
  frame(s, st, t, COUNT) {
    const { n, phase, done } = tick(t, COUNT);
    setClock(st.c, n, phase);
    const last = !done && n <= 10;
    const b = done ? 0 : tickBeat(phase);
    const out = ep(t, COUNT, 0.5, ease.inCubic);
    posClock(st.c, { k: 1 + (last ? 0.035 * b : 0), o: 1 - out });
    st.lab.setAttribute('opacity', 1 - out);
    const km = ep(t, COUNT + 0.25, 1.2, ease.inOutCubic);
    s.place(MARK_BOX, { cy: lerp(st.m0.cy, st.m1.cy, km), size: lerp(st.m0.size, st.m1.size, km) });
    beatMark(s, 1 + (last ? 0.14 : 0.07) * b + 0.08 * beat(t, COUNT + 1.8));
  },
});

// B. A ring drains around the mark over the whole countdown.
const countdownRing = countdown({
  id: 'countdown-ring',
  title: 'Countdown: ring',
  blurb: 'The mark inside a thin ring that drains over the five minutes, with the time underneath. At zero the ring refills, the mark beats, and the ring ripples away.',
  setup(s) {
    hideWord(s);
    const P = s.portrait;
    const r = P ? s.W * 0.3 : s.H * 0.22;
    const cy = s.H * 0.42;
    const sw = r * 0.035;
    const g = el('g', {}, s.back);
    const track = el('circle', { cx: 0, cy: 0, r, fill: 'none', stroke: s.th.fg, 'stroke-opacity': 0.16, 'stroke-width': sw }, g);
    const C = 2 * Math.PI * r;
    const arc = el('circle', { cx: 0, cy: 0, r, fill: 'none', stroke: s.th.fg, 'stroke-width': sw, 'stroke-dasharray': C, transform: 'rotate(-90)' }, g);
    const dot = el('circle', { r: sw * 1.1, fill: s.th.fg }, g);
    const ripple = el('circle', { cx: 0, cy: 0, r, fill: 'none', stroke: s.th.fg, 'stroke-width': sw, opacity: 0 }, g);
    const ls = P ? s.W * 0.035 : s.H * 0.026;
    const cs = P ? s.W * 0.14 : s.H * 0.1;
    const lab = label(s, 'Service begins in', { y: cy + r + ls * 2.6, size: ls });
    const c = clock(s, { size: cs, y: cy + r + ls * 3.6 + cs * 0.72 });
    return { g, track, arc, dot, ripple, r, C, cy, sw, lab, c, m0: r * 0.95 };
  },
  frame(s, st, t, COUNT) {
    const { n, phase, done } = tick(t, COUNT);
    setClock(st.c, n, phase);
    const b = done ? 0 : tickBeat(phase);
    const out = ep(t, COUNT, 0.5, ease.inCubic);
    posClock(st.c, { o: 1 - out });
    st.lab.setAttribute('opacity', 1 - out);
    // Remaining fraction drains; after zero it refills fast.
    const fill = done ? ep(t, COUNT + 0.15, 0.8, ease.outCubic) : clamp((COUNT - t) / COUNT);
    // Mark and ring travel to the centre together.
    const km = ep(t, COUNT + 0.3, 1.1, ease.inOutCubic);
    const size = lerp(st.m0, markSize(s), km);
    const cy = lerp(st.cy, s.H / 2, km);
    const rr = st.r * (size / st.m0);
    s.place(MARK_BOX, { cy, size });
    set(st.g, { transform: `translate(${s.W / 2} ${cy}) scale(${rr / st.r})` });
    set(st.arc, { 'stroke-dashoffset': st.C * (1 - fill) });
    const a = (-90 + 360 * fill) * (Math.PI / 180);
    set(st.dot, { cx: st.r * Math.cos(a), cy: st.r * Math.sin(a), r: st.sw * (1.1 + 0.9 * b), opacity: done ? 1 - prog(t, COUNT + 0.9, 0.2) : 1 });
    // After landing: one strong beat, the ring ripples out and the track goes with it.
    const kr = ep(t, COUNT + 1.6, 1.3, ease.outCubic);
    set(st.ripple, { r: st.r * (1 + 0.42 * kr), opacity: kr > 0 ? 1 - kr : 0 });
    const gone = prog(t, COUNT + 1.6, 0.25);
    set(st.arc, { opacity: 1 - gone });
    set(st.track, { 'stroke-opacity': 0.16 * (1 - gone) });
    beatMark(s, 1 + 0.05 * b + 0.09 * beat(t, COUNT + 1.6));
  },
});

// C. Editorial layout with a heart-monitor trace that blips every second.
const countdownTrace = countdown({
  id: 'countdown-trace',
  title: 'Countdown: heart monitor',
  blurb: 'A heart-monitor line sweeps across the bottom and blips on every second. At zero the line goes flat and the lockup moves to the centre.',
  setup(s) {
    const P = s.portrait;
    const mx = s.W * 0.1;
    const lk = P ? s.W * 0.12 : s.H * 0.075;
    const l0 = P ? { cx: s.W / 2, cy: s.H * 0.14, size: lk } : { cx: mx + lockupW(lk) / 2, cy: s.H * 0.14, size: lk };
    const cs = P ? s.W * 0.3 : s.H * 0.3;
    const ls = P ? s.W * 0.036 : s.H * 0.03;
    const anchor = P ? 'middle' : 'start';
    const x = P ? s.W / 2 : mx;
    const ly = P ? s.H * 0.36 : s.H * 0.33;
    const lab = label(s, 'Service begins in', { x, y: ly, size: ls, anchor });
    const c = clock(s, { size: cs, x, y: ly + ls * 1.3 + cs * 0.72, anchor });
    const base = P ? s.H * 0.68 : s.H * 0.8;
    const amp = P ? s.W * 0.11 : s.H * 0.1;
    const sw = P ? s.W * 0.006 : s.H * 0.005;
    const line = el('path', { fill: 'none', stroke: s.th.fg, 'stroke-width': sw, 'stroke-linejoin': 'round', 'stroke-linecap': 'round' }, s.back);
    const dot = el('circle', { r: sw * 1.8, fill: s.th.fg }, s.back);
    return { l0, l1: { cx: s.W / 2, cy: s.H / 2, size: lockupSize(s) }, lab, c, line, dot, base, amp, speed: s.W / 3, gap: s.W * 0.06 };
  },
  frame(s, st, t, COUNT) {
    const { n, phase, done } = tick(t, COUNT);
    setClock(st.c, n, phase);
    const b = done ? 0 : tickBeat(phase);
    const out = ep(t, COUNT, 0.5, ease.inCubic);
    posClock(st.c, { o: 1 - out });
    st.lab.setAttribute('opacity', 1 - out);
    // Beats sit on the seconds; after zero the line flattens and fades.
    const flat = 1 - ep(t, COUNT + 0.1, 0.6);
    const yAt = tau => st.base - st.amp * flat * (tau < COUNT + 0.1 ? ecg(mod(tau - 0.1, 1)) : 0);
    const xh = mod(t * st.speed, s.W);
    const step = s.W / 480;
    let d = '';
    let pen = false;
    for (let x = 0; x <= s.W + 0.1; x += step) {
      const behind = mod(xh - x, s.W);
      if (behind > s.W - st.gap) { pen = false; continue; }
      const y = yAt(t - behind / st.speed);
      d += `${pen ? 'L' : 'M'}${x.toFixed(1)},${y.toFixed(1)}`;
      pen = true;
    }
    const fade = 1 - ep(t, COUNT + 0.6, 0.6);
    set(st.line, { d, opacity: fade });
    set(st.dot, { cx: xh, cy: yAt(t), opacity: fade });
    const km = ep(t, COUNT + 0.4, 1.2, ease.inOutCubic);
    s.place(LOCKUP_BOX, { cx: lerp(st.l0.cx, st.l1.cx, km), cy: lerp(st.l0.cy, st.l1.cy, km), size: lerp(st.l0.size, st.l1.size, km) });
    beatMark(s, 1 + 0.06 * b + 0.08 * beat(t, COUNT + 1.9));
  },
});

// D. Welcome messages rotate above a quiet timer bar; the last ten seconds count big.
const MESSAGES = [
  { land: [['Welcome', 'to'], ['Heartbeat', 'Church']], port: [['Welcome', 'to'], ['Heartbeat'], ['Church']] },
  { land: [['Living', 'Out', 'The', 'Gospel'], ['Together', 'Wholeheartedly']], port: [['Living', 'Out'], ['The', 'Gospel'], ['Together'], ['Wholeheartedly']] },
  { land: [['Grab', 'a', 'coffee'], ['and', 'find', 'a', 'seat']], port: [['Grab', 'a', 'coffee'], ['and', 'find'], ['a', 'seat']] },
  { land: [['We’re', 'glad'], ['you’re', 'here']], port: [['We’re', 'glad'], ['you’re', 'here']] },
];
const SLOT = 12;
const countdownWelcome = countdown({
  id: 'countdown-welcome',
  title: 'Countdown: welcome',
  blurb: 'Welcome lines and the vision take turns in the middle every 12 seconds, with the time and a progress line along the bottom. The last ten seconds count down big.',
  setup(s) {
    const P = s.portrait;
    const cy = P ? s.H * 0.4 : s.H * 0.4;
    const ms = P ? s.W * 0.11 : s.H * 0.1;
    const msgs = MESSAGES.map(m => {
      const g = el('g', { opacity: 0 }, s.top);
      const words = s.text(P ? m.port : m.land, { size: ms, cy, lh: 1.08, parent: g, tracking: -0.025 });
      words.forEach(w => w.t.setAttribute('transform', `translate(${w.x} ${w.y})`));
      return g;
    });
    const big = txt(s, '10', { y: cy + (P ? s.W * 0.5 : s.H * 0.42) * 0.36, size: P ? s.W * 0.5 : s.H * 0.42, tracking: -0.04 });
    const mx = P ? s.W * 0.1 : s.W * 0.07;
    const ly = P ? s.H * 0.74 : s.H * 0.79;
    const sw = P ? s.W * 0.004 : s.H * 0.003;
    const track = el('line', { x1: mx, x2: s.W - mx, y1: ly, y2: ly, stroke: s.th.fg, 'stroke-opacity': 0.18, 'stroke-width': sw }, s.back);
    const bar = el('line', { x1: mx, x2: mx, y1: ly, y2: ly, stroke: s.th.fg, 'stroke-width': sw }, s.back);
    let c, lab, l0;
    if (P) {
      const cs = s.W * 0.09;
      lab = label(s, 'Service begins in', { y: ly + s.W * 0.1, size: s.W * 0.03 });
      c = clock(s, { size: cs, y: ly + s.W * 0.1 + s.W * 0.035 + cs * 0.72 });
      l0 = { cx: s.W / 2, cy: s.H * 0.9, size: s.W * 0.1 };
    } else {
      const cs = s.H * 0.065;
      const by = s.H * 0.9;
      c = clock(s, { size: cs, x: s.W - mx, y: by, anchor: 'end' });
      lab = label(s, 'Service begins in', { x: s.W - mx - c.total - cs * 0.4, y: by, size: s.H * 0.022, anchor: 'end' });
      l0 = { cx: mx + lockupW(s.H * 0.065) / 2, cy: by - cs * 0.36, size: s.H * 0.065 };
    }
    return { msgs, big, track, bar, mx, c, lab, l0, l1: { cx: s.W / 2, cy: s.H / 2, size: lockupSize(s) } };
  },
  frame(s, st, t, COUNT) {
    const { n, phase, done } = tick(t, COUNT);
    setClock(st.c, n, phase);
    const finale = COUNT - 10;
    // Messages: each slot fades and rises in, then fades out before the next. They stop before the last ten seconds.
    const slot = Math.floor(t / SLOT);
    st.msgs.forEach((g, i) => {
      const t0 = slot * SLOT;
      // Skip a slot that would only get a moment before the final count.
      const on = slot % st.msgs.length === i && t < finale && t0 + 4 <= finale;
      const kin = on ? ep(t, t0, 0.7) : 0;
      const kout = on ? ep(t, Math.min(t0 + SLOT, finale) - 0.5, 0.5, ease.inCubic) : 0;
      g.setAttribute('opacity', kin * (1 - kout));
      g.setAttribute('transform', `translate(0 ${(1 - kin) * s.H * 0.02 - kout * s.H * 0.01})`);
    });
    // The last ten seconds count down big, each number popping in on the tick.
    const showBig = !done && n <= 10 && t >= finale;
    st.big.textContent = String(n);
    const kp = ease.outCubic(clamp(phase / 0.35));
    const cx = s.W / 2;
    const cyb = Number(st.big.getAttribute('y'));
    st.big.setAttribute('transform', `translate(${cx} ${cyb}) scale(${showBig ? 1.12 - 0.12 * kp : 1}) translate(${-cx} ${-cyb})`);
    st.big.setAttribute('opacity', showBig ? 0.25 + 0.75 * kp : 0);
    const out = ep(t, COUNT, 0.5, ease.inCubic);
    posClock(st.c, { o: 1 - out });
    st.lab.setAttribute('opacity', 1 - out);
    const elapsed = clamp(t / COUNT);
    set(st.bar, { x2: st.mx + (s.W - 2 * st.mx) * elapsed, opacity: 1 - out });
    set(st.track, { opacity: 1 - out });
    const km = ep(t, COUNT + 0.3, 1.2, ease.inOutCubic);
    s.place(LOCKUP_BOX, { cx: lerp(st.l0.cx, st.l1.cx, km), cy: lerp(st.l0.cy, st.l1.cy, km), size: lerp(st.l0.size, st.l1.size, km) });
    beatMark(s, 1 + 0.08 * beat(t, COUNT + 1.8));
  },
});

// ---------- loaders (mark only, seamless) ----------
const loaderSize = s => markSize(s) * 0.62;
const loaderSetup = s => {
  hideWord(s);
  s.place(MARK_BOX, { size: loaderSize(s) });
};
const ENTRY = { H: { y: -24 }, B: { x: 24 }, C: { x: -24 } };

const LOADERS = [
  {
    id: 'load-stack',
    title: 'Loader: build',
    duration: 2.4,
    blurb: 'H, B and C drop into place one after another, hold, then shrink away in the same order.',
    setup: loaderSetup,
    frame(s, st, t) {
      PARTS.forEach((k, i) => {
        const p = s.parts[k];
        const kin = ep(t, 0.05 + 0.18 * i, 0.5, ease.outBack);
        const kout = ep(t, 1.45 + 0.16 * i, 0.4, ease.inCubic);
        const e = ENTRY[k];
        tf(p.g, { x: (e.x || 0) * (1 - kin), y: (e.y || 0) * (1 - kin), s: 1 - 0.5 * kout, ox: p.c[0], oy: p.c[1], o: prog(t, 0.05 + 0.18 * i, 0.12) * (1 - kout) });
      });
    },
  },
  {
    id: 'load-hop',
    title: 'Loader: hop',
    duration: 1.2,
    blurb: 'The three letters hop in turn, like a typing indicator.',
    setup: loaderSetup,
    frame(s, st, t) {
      PARTS.forEach((k, i) => {
        const ph = mod(t - 0.14 * i, 1.2);
        const h = ph < 0.42 ? Math.sin((Math.PI * ph) / 0.42) : 0;
        const p = s.parts[k];
        tf(p.g, { y: -20 * h, sy: 1 + 0.05 * h, sx: 1 - 0.04 * h, ox: p.c[0], oy: p.box[3] });
      });
    },
  },
  {
    id: 'load-blink',
    title: 'Loader: blink',
    duration: 1.2,
    blurb: 'The letters light up in turn, H to B to C, like a spinner made from the mark.',
    setup: loaderSetup,
    frame(s, st, t) {
      PARTS.forEach((k, i) => {
        const ph = mod(t - 0.4 * i + 0.6, 1.2) - 0.6;
        s.parts[k].g.setAttribute('opacity', 0.16 + 0.84 * G(ph, 0, 0.24));
      });
    },
  },
  {
    id: 'load-fill',
    title: 'Loader: fill',
    duration: 2.2,
    blurb: 'The mark in outline fills from the bottom up, then the fill drains out of the top.',
    setup(s) {
      loaderSetup(s);
      const outline = el('g', { fill: 'none', stroke: s.th.fg, 'stroke-width': 1.1, opacity: 0.4 });
      for (const k of PARTS) el(LOGO[k].tag, LOGO[k].attrs, outline);
      s.logo.insertBefore(outline, s.mark);
      const cp = el('clipPath', { id: s.uid('fill'), clipPathUnits: 'userSpaceOnUse' }, s.defs);
      const rect = el('rect', { x: -2, width: 98, y: 112, height: 0 }, cp);
      s.mark.setAttribute('clip-path', `url(#${s.uid('fill')})`);
      return { rect };
    },
    frame(s, st, t) {
      const H = 112;
      const up = ep(t, 0.1, 1.1, ease.inOutCubic);
      const drain = ep(t, 1.45, 0.65, ease.inOutCubic);
      const top = H * (1 - up);
      const bottom = H * (1 - drain);
      set(st.rect, { y: top - 0.5, height: Math.max(0, bottom - top + 1) });
    },
  },
  {
    id: 'load-trace',
    title: 'Loader: heart monitor',
    duration: 2,
    blurb: 'A short heart-monitor trace runs under the mark; the mark beats as the blip passes beneath it.',
    setup(s) {
      hideWord(s);
      const size = loaderSize(s);
      const cy = s.H / 2 - size * 0.18;
      s.place(MARK_BOX, { cy, size });
      const span = size * 2.4;
      const base = cy + size * 0.5 + size * 0.58;
      const sw = size * 0.022;
      const gid = s.uid('trail');
      const grad = el('linearGradient', { id: gid, gradientUnits: 'userSpaceOnUse' }, s.defs);
      el('stop', { offset: 0, 'stop-color': s.th.fg, 'stop-opacity': 0 }, grad);
      el('stop', { offset: 1, 'stop-color': s.th.fg, 'stop-opacity': 1 }, grad);
      const line = el('path', { fill: 'none', stroke: `url(#${gid})`, 'stroke-width': sw, 'stroke-linejoin': 'round', 'stroke-linecap': 'round' }, s.back);
      const dot = el('circle', { r: sw * 1.6, fill: s.th.fg }, s.back);
      return { grad, line, dot, span, base, amp: size * 0.3, trail: span * 0.55, x0: s.W / 2 - span / 2 };
    },
    frame(s, st, t) {
      // The head runs from one trail-length left of the span to one trail-length right of it,
      // so nothing is visible at the loop point.
      const P = 2;
      const from = st.x0 - st.trail;
      const to = st.x0 + st.span + st.trail;
      const xh = lerp(from, to, mod(t, P) / P);
      const xc = s.W / 2;
      const yAt = x => st.base - st.amp * ecg(((x - xc) / st.span) * 0.9 + 0.045);
      const a = Math.max(st.x0, xh - st.trail);
      const b = Math.min(st.x0 + st.span, xh);
      let d = '';
      for (let x = a; x <= b; x += 2) d += `${d ? 'L' : 'M'}${x.toFixed(1)},${yAt(x).toFixed(1)}`;
      set(st.line, { d: b > a ? d : '' });
      set(st.grad, { x1: xh - st.trail, x2: xh, y1: 0, y2: 0 });
      const inSpan = xh >= st.x0 && xh <= st.x0 + st.span;
      set(st.dot, { cx: xh, cy: yAt(xh), opacity: inSpan ? 1 : 0 });
      // The head passes the blip at the centre at this phase.
      const tb = ((xc - from) / (to - from)) * P + 0.04;
      beatMark(s, 1 + 0.08 * (beat(mod(t, P), tb, 1, 0.55) + beat(mod(t, P) + P, tb, 1, 0.55)));
    },
  },
  {
    id: 'load-bar',
    title: 'Loader: lockup with bar',
    duration: 1.8,
    blurb: 'The full lockup with a thin progress line under it that keeps sweeping across.',
    setup(s) {
      const size = lockupSize(s) * 0.8;
      const cy = s.H / 2 - size * 0.12;
      s.place(LOCKUP_BOX, { cy, size });
      const w = lockupW(size);
      const x0 = s.W / 2 - w / 2;
      const y = cy + size * 0.5 + size * 0.32;
      const sw = Math.max(3, size * 0.035);
      el('line', { x1: x0, x2: x0 + w, y1: y, y2: y, stroke: s.th.fg, 'stroke-opacity': 0.15, 'stroke-width': sw }, s.back);
      const cp = el('clipPath', { id: s.uid('bar') }, s.defs);
      el('rect', { x: x0, y: y - sw, width: w, height: sw * 2 }, cp);
      const g = el('g', { 'clip-path': `url(#${s.uid('bar')})` }, s.back);
      const seg = el('line', { y1: y, y2: y, stroke: s.th.fg, 'stroke-width': sw }, g);
      return { seg, x0, w };
    },
    frame(s, st, t) {
      const k = ease.inOutCubic(mod(t, 1.8) / 1.8);
      const len = st.w * (0.18 + 0.22 * Math.sin(Math.PI * k));
      const x = lerp(st.x0 - len, st.x0 + st.w, k);
      set(st.seg, { x1: x, x2: x + len });
    },
  },
].map(a => ({ ...a, kind: 'loader', loop: true, gif: true }));

// ---------- livestream & holding screens (seamless) ----------
function streamCard(s, words) {
  const P = s.portrait;
  const size = lockupSize(s);
  const cy = s.H / 2 - size * 0.35;
  s.place(LOCKUP_BOX, { cy, size });
  const ts = P ? s.W * 0.055 : s.H * 0.052;
  const y = cy + size * 0.5 + ts * 2.3;
  const t = txt(s, words, { y, size: ts, weight: 500, fill: s.th.fg });
  const w = t.getComputedTextLength();
  const dots = [0, 1, 2].map(i => el('circle', { cx: s.W / 2 + w / 2 + ts * (0.2 + 0.26 * i), cy: y - ts * 0.06, r: ts * 0.075, fill: s.th.fg }, s.top));
  // Re-centre text plus dots as one line.
  const shift = -(ts * (0.2 + 0.52 + 0.075)) / 2;
  t.setAttribute('transform', `translate(${shift} 0)`);
  dots.forEach(d => d.setAttribute('transform', `translate(${shift} 0)`));
  return { dots };
}
function streamFrame(s, st, t) {
  beatMark(s, 1 + 0.06 * loopBeat(t, 2.4, 0.3));
  st.dots.forEach((d, i) => {
    const ph = mod(t - 0.25 * i + 0.6, 1.2) - 0.6;
    d.setAttribute('opacity', 0.2 + 0.8 * G(ph, 0, 0.22));
  });
}

const STREAM = [
  {
    id: 'stream-starting-soon',
    title: 'Starting soon',
    duration: 4.8,
    blurb: 'For the livestream before it goes live: the lockup beating slowly over “Starting soon” and three dots.',
    setup: s => streamCard(s, 'Starting soon'),
    frame: streamFrame,
  },
  {
    id: 'stream-be-right-back',
    title: 'Be right back',
    duration: 4.8,
    blurb: 'Same layout for a break or a technical hold: “We’ll be right back”.',
    setup: s => streamCard(s, 'We’ll be right back'),
    frame: streamFrame,
  },
  {
    id: 'hold-backdrop',
    title: 'Holding backdrop',
    duration: 9.6,
    blurb: 'A giant, faint mark cropped off the edge, breathing slowly. Leaves the other side clear for a ProPresenter timer or announcement.',
    setup(s) {
      hideWord(s);
      const P = s.portrait;
      const size = P ? s.H * 0.62 : s.H * 1.0;
      s.place(MARK_BOX, P ? { cx: s.W * 0.62, cy: s.H * 0.86, size } : { cx: s.W * 0.8, cy: s.H * 0.6, size });
      s.logo.setAttribute('opacity', 0.11);
    },
    frame(s, st, t) {
      const breathe = 0.012 * Math.sin((2 * Math.PI * t) / 9.6);
      beatMark(s, 1 + breathe + 0.018 * loopBeat(t, 2.4, 0.3));
    },
  },
].map(a => ({ ...a, kind: 'stream', loop: true }));

export const ANIMS_V3 = [
  ...LOADERS,
  countdownPulse(5),
  countdownRing(5),
  countdownTrace(5),
  countdownWelcome(5),
  ...STREAM,
];
