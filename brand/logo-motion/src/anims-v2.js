// Round two of the catalogue, from feedback on the first report:
//   - heartbeat loop without the echo outlines, alone and with the church name
//   - kinetic vision with "Living Out The Gospel" as one phrase, in several treatments
//   - slide reveal that returns to the mark
// Same contract as anims.js: setup(s) -> state, frame(s, st, t) sets everything for time t.
import { MARK_BOX, LOCKUP_BOX, clamp, lerp, prog, ep, ease, beat, el, set, tf, markSize, lockupSize } from './core.js';

const MARK_C = [(MARK_BOX[0] + MARK_BOX[2]) / 2, (MARK_BOX[1] + MARK_BOX[3]) / 2];
const OFF = (LOCKUP_BOX[2] - MARK_BOX[2]) / 2; // shift that centres the mark alone inside the lockup box
const hideWord = s => s.word.setAttribute('display', 'none');

// Seamless lub-dub envelope with period P, beat at phase b.
const loopBeat = (t, P, b = 0.25) => {
  const ph = ((t % P) + P) % P;
  return beat(ph, b, 1, 0.55) + beat(ph + P, b, 1, 0.55) + beat(ph - P, b, 1, 0.55);
};

// ---------- the slide reveal, shared ----------
// Wrap the wordmark in a clip whose left edge rides the mark's right edge.
function slideSetup(s) {
  const cp = el('clipPath', { id: s.uid('word-clip') }, s.defs);
  const clip = el('rect', { x: 95, y: 0, width: 170, height: 112 }, cp);
  const wrap = el('g', { 'clip-path': `url(#${s.uid('word-clip')})` });
  s.logo.insertBefore(wrap, s.word);
  wrap.appendChild(s.word);
  return clip;
}
// k = how far the wordmark is out (0 hidden, 1 fully revealed). Same easing as Slide reveal.
function slidePose(s, clip, k, kw, extra = {}) {
  const mx = OFF * (1 - k);
  tf(s.mark, { x: mx, ox: MARK_C[0], oy: MARK_C[1], ...extra });
  set(clip, { x: 95 + mx });
  tf(s.word, { x: -110 * (1 - kw) });
}

// The lockup builds in: H, B, C stack, then the wordmark slides out of the mark.
function lockupBuild(s, t, t0) {
  const { H, B, C } = s.parts;
  tf(H.g, { y: lerp(-24, 0, ep(t, t0, 0.6, ease.outBack)), o: prog(t, t0, 0.1) });
  tf(B.g, { x: lerp(24, 0, ep(t, t0 + 0.12, 0.6, ease.outBack)), o: prog(t, t0 + 0.12, 0.1) });
  tf(C.g, { y: lerp(24, 0, ep(t, t0 + 0.24, 0.6, ease.outBack)), o: prog(t, t0 + 0.24, 0.1) });
  const w = ep(t, t0 + 0.45, 0.8, ease.outQuint);
  tf(s.word, { x: lerp(-10, 0, w), o: w });
}

// ---------- kinetic type helpers ----------
// A phrase as its own group of words, scaled down to fit maxW. Returns its box in screen px.
function phrase(s, lines, { size, cy, maxW = s.W * 0.86, weight = 700, parent = s.top, tracking = -0.03 }) {
  const g = el('g', {}, parent);
  let words = s.text(lines, { size, weight, cy, tracking, parent: g });
  const widest = () => Math.max(...lines.map((_, li) => {
    const ws = words.filter(w => w.line === li);
    return ws.at(-1).x + ws.at(-1).w - ws[0].x;
  }));
  const w0 = widest();
  if (w0 > maxW) {
    words.forEach(w => w.t.remove());
    size = (size * maxW) / w0;
    words = s.text(lines, { size, weight, cy, tracking, parent: g });
  }
  const x0 = Math.min(...words.map(w => w.x));
  const x1 = Math.max(...words.map(w => w.x + w.w));
  const y0 = Math.min(...words.map(w => w.y)) - size * 0.82;
  const y1 = Math.max(...words.map(w => w.y)) + size * 0.3;
  return { g, words, size, box: [x0, y0, x1, y1] };
}
// Give a phrase a clip window: its own box, padded. Returns the clip rect.
function windowClip(s, p, name, pad = 0.08) {
  const [x0, y0, x1, y1] = p.box;
  const px = (x1 - x0) * pad;
  const cp = el('clipPath', { id: s.uid(name) }, s.defs);
  const r = el('rect', { x: x0 - px, y: y0, width: x1 - x0 + 2 * px, height: y1 - y0 }, cp);
  p.g.setAttribute('clip-path', `url(#${s.uid(name)})`);
  p.clip = { r, x: x0 - px, w: x1 - x0 + 2 * px };
  return r;
}
const placeWords = (p, { dx = 0, dy = 0, o = 1 } = {}) => p.words.forEach(w => {
  w.t.setAttribute('transform', `translate(${w.x + dx} ${w.y + dy})`);
  w.t.setAttribute('opacity', clamp(o));
});
// Left-to-right wipe of a whole phrase, line by line, as one continuous sweep.
function wipeLR(p, k) {
  const lines = [...new Set(p.words.map(w => w.line))];
  if (lines.length === 1) {
    set(p.clip.r, { width: p.clip.w * k });
    placeWords(p, { dx: (1 - k) * -p.size * 0.15 });
    return;
  }
  // Multi-line (portrait): sweep each line in turn, using per-word opacity masks.
  const n = lines.length;
  set(p.clip.r, { width: p.clip.w });
  p.words.forEach(w => {
    const lk = clamp(k * n - w.line);
    const ws = p.words.filter(x => x.line === w.line);
    const lx0 = ws[0].x;
    const lx1 = ws.at(-1).x + ws.at(-1).w;
    const edge = lx0 + (lx1 - lx0) * lk;
    // Word is shown once the sweep passes its left edge; it eases in over its own width.
    const wk = clamp((edge - w.x) / Math.max(1, w.w));
    w.t.setAttribute('transform', `translate(${w.x - (1 - wk) * p.size * 0.15} ${w.y})`);
    w.t.setAttribute('opacity', wk);
  });
}
const visionSize = s => (s.portrait ? s.W * 0.16 : s.aspect === '1x1' ? s.W * 0.13 : s.H * 0.17);
const gospelLines = s => (s.portrait ? [['Living', 'Out'], ['The', 'Gospel']] : [['Living', 'Out', 'The', 'Gospel']]);

export const ANIMS_V2 = [
  // ─────────────── heartbeat loops, no echo ───────────────
  {
    id: 'mark-heartbeat-loop-clean',
    title: 'Heartbeat loop (clean)',
    kind: 'mark',
    duration: 2.4,
    loop: true,
    blurb: 'The heartbeat loop with the echo outlines removed. Just the mark beating, twice per loop.',
    setup(s) {
      hideWord(s);
      return s.place(MARK_BOX, { size: markSize(s) });
    },
    frame(s, st, t) {
      tf(s.mark, { s: 1 + 0.07 * loopBeat(t, 1.2), ox: MARK_C[0], oy: MARK_C[1] });
    },
  },
  {
    id: 'lockup-heartbeat-loop',
    title: 'Heartbeat loop with name',
    kind: 'lockup',
    duration: 2.4,
    loop: true,
    blurb: 'The full lockup. Only the mark beats; the name holds still beside it.',
    setup(s) {
      return s.place(LOCKUP_BOX, { size: lockupSize(s) });
    },
    frame(s, st, t) {
      tf(s.mark, { s: 1 + 0.07 * loopBeat(t, 1.2), ox: MARK_C[0], oy: MARK_C[1] });
    },
  },
  {
    id: 'lockup-heartbeat-loop-whole',
    title: 'Heartbeat loop, whole lockup',
    kind: 'lockup',
    duration: 2.4,
    loop: true,
    blurb: 'A variation where the whole lockup beats together, a little softer.',
    setup(s) {
      return s.place(LOCKUP_BOX, { size: lockupSize(s) });
    },
    frame(s, st, t) {
      const k = 1 + 0.045 * loopBeat(t, 1.2);
      // Scale the wordmark about the same centre as the whole lockup so it stays attached.
      tf(s.word, { s: k, ox: 126.1, oy: MARK_C[1] });
      tf(s.mark, { s: k, ox: 126.1, oy: MARK_C[1] });
    },
  },

  // ─────────────── slide reveal and return ───────────────
  {
    id: 'lockup-slide-return',
    title: 'Slide reveal and return',
    kind: 'lockup',
    duration: 6,
    blurb: 'Slide reveal, then the name slides back behind the mark and the mark settles in the centre with one beat.',
    setup(s) {
      const st = s.place(LOCKUP_BOX, { size: lockupSize(s) });
      st.clip = slideSetup(s);
      return st;
    },
    frame(s, st, t) {
      const pop = ep(t, 0.1, 0.9, ease.spring);
      const out = ep(t, 1.3, 1.1, ease.inOutQuint);
      const back = ep(t, 3.6, 0.9, ease.inOutQuint);
      const k = out * (1 - back);
      const kw = ep(t, 1.3, 1.25, ease.inOutQuint) * (1 - ep(t, 3.55, 0.85, ease.inOutQuint));
      const b = beat(t, 4.9, 1, 0.5);
      slidePose(s, st.clip, k, kw, { s: pop * (1 + 0.07 * b), o: prog(t, 0.1, 0.15) });
    },
  },

  // ─────────────── kinetic vision, round two ───────────────
  {
    id: 'kinetic-sweep',
    title: 'Kinetic: sweep and rise',
    kind: 'vision',
    duration: 8,
    blurb: '“Living Out The Gospel” sweeps in left to right in one go. “Together” rises from below, then “Wholeheartedly”. Ends on the lockup.',
    setup(s) {
      const big = visionSize(s);
      const st = s.place(LOCKUP_BOX, { size: lockupSize(s) });
      st.p1 = phrase(s, gospelLines(s), { size: big, cy: s.H / 2 });
      st.p2 = phrase(s, [['Together']], { size: big, cy: s.H / 2 });
      st.p3 = phrase(s, [['Wholeheartedly']], { size: big, cy: s.H / 2 });
      windowClip(s, st.p1, 'k1'); windowClip(s, st.p2, 'k2'); windowClip(s, st.p3, 'k3');
      return st;
    },
    frame(s, st, t) {
      const { p1, p2, p3 } = st;
      const lift = p => (p.box[3] - p.box[1]) * 1.2;
      // 1. sweep in, hold, lift out
      wipeLR(p1, ep(t, 0.2, 0.9, ease.inOutCubic));
      const o1 = ep(t, 2.0, 0.4, ease.inCubic);
      if (o1 > 0) placeWords(p1, { dy: -o1 * lift(p1) });
      // 2. rise, hold, lift out
      placeWords(p2, { dy: lift(p2) * (1 - ep(t, 2.45, 0.6, ease.outExpo)) - lift(p2) * ep(t, 3.65, 0.4, ease.inCubic) });
      // 3. rise, hold, lift out
      placeWords(p3, { dy: lift(p3) * (1 - ep(t, 4.1, 0.6, ease.outExpo)) - lift(p3) * ep(t, 5.4, 0.4, ease.inCubic) });
      lockupBuild(s, t, 5.75);
    },
  },
  {
    id: 'kinetic-stack',
    title: 'Kinetic: build and stay',
    kind: 'vision',
    duration: 7.5,
    blurb: 'The three parts stack up and stay: the first line sweeps in, “Together” and “Wholeheartedly” rise in under it. Then the text lifts away for the lockup.',
    setup(s) {
      const size = visionSize(s) * (s.portrait ? 0.78 : 0.72);
      const st = s.place(LOCKUP_BOX, { size: lockupSize(s) });
      const lines = s.portrait ? 4 : 3;
      const lh = size * 1.08;
      const top = s.H / 2 - (lines * lh) / 2 + lh / 2;
      st.stack = el('g', {}, s.top);
      st.p1 = phrase(s, gospelLines(s), { size, cy: top + (s.portrait ? lh / 2 : 0), parent: st.stack });
      // Every part shares the first part's fitted size so the stack reads as one block.
      const sz = st.p1.size;
      const y2 = top + lh * (s.portrait ? 2 : 1);
      st.p2 = phrase(s, [['Together']], { size: sz, cy: y2, parent: st.stack });
      st.p3 = phrase(s, [['Wholeheartedly']], { size: sz, cy: y2 + lh, parent: st.stack });
      windowClip(s, st.p1, 's1'); windowClip(s, st.p2, 's2'); windowClip(s, st.p3, 's3');
      return st;
    },
    frame(s, st, t) {
      const { p1, p2, p3 } = st;
      const h = p => (p.box[3] - p.box[1]) * 1.2;
      wipeLR(p1, ep(t, 0.2, 0.9, ease.inOutCubic));
      placeWords(p2, { dy: h(p2) * (1 - ep(t, 1.35, 0.6, ease.outExpo)) });
      placeWords(p3, { dy: h(p3) * (1 - ep(t, 2.15, 0.6, ease.outExpo)) });
      const away = ep(t, 3.9, 0.6, ease.inCubic);
      set(st.stack, { transform: `translate(0 ${-away * s.H * 0.12})`, opacity: 1 - away });
      lockupBuild(s, t, 4.4);
    },
  },
  {
    id: 'kinetic-beat',
    title: 'Kinetic: on the heartbeat',
    kind: 'vision',
    duration: 8,
    blurb: 'Each part lands on a heartbeat: the first line pulses in whole, “Together” slides in from the right, “Wholeheartedly” lands on a strong beat. The mark beats in to finish.',
    setup(s) {
      const big = visionSize(s);
      const st = s.place(LOCKUP_BOX, { size: lockupSize(s) });
      st.p1 = phrase(s, gospelLines(s), { size: big, cy: s.H / 2 });
      st.p2 = phrase(s, [['Together']], { size: big, cy: s.H / 2 });
      st.p3 = phrase(s, [['Wholeheartedly']], { size: big, cy: s.H / 2 });
      windowClip(s, st.p2, 'b2', 0.02);
      st.clip = slideSetup(s);
      return st;
    },
    frame(s, st, t) {
      const { p1, p2, p3 } = st;
      const pulse = (p, tb, out, strong = 1) => {
        const inK = ep(t, tb - 0.12, 0.35, ease.outBack);
        const b = beat(t, tb + 0.25, strong, 0.55 * strong);
        const k = (0.86 + 0.14 * inK) * (1 + 0.05 * b) * (1 - 0.1 * ep(t, out, 0.3, ease.inCubic));
        const o = prog(t, tb - 0.12, 0.12) * (1 - prog(t, out, 0.3));
        const [x0, y0, x1, y1] = p.box;
        set(p.g, { transform: `translate(${(x0 + x1) / 2} ${(y0 + y1) / 2}) scale(${k}) translate(${-(x0 + x1) / 2} ${-(y0 + y1) / 2})`, opacity: o });
      };
      placeWords(p1); pulse(p1, 0.4, 1.95);
      // Together slides in from the right through its own window.
      const k2 = ep(t, 2.3, 0.55, ease.outExpo);
      placeWords(p2, { dx: (1 - k2) * (p2.box[2] - p2.box[0]) * 1.1 - ep(t, 3.4, 0.35, ease.inCubic) * (p2.box[2] - p2.box[0]) * 1.1 });
      p2.g.setAttribute('opacity', t >= 2.3 ? 1 : 0);
      placeWords(p3); pulse(p3, 4.1, 5.5, 1.6);
      // The mark beats in on its own, then the name slides out (slide reveal).
      const tm = 5.95;
      const pop = ep(t, tm, 0.8, ease.spring);
      const k = ep(t, tm + 1.0, 0.9, ease.inOutQuint);
      const kw = ep(t, tm + 1.0, 1.0, ease.inOutQuint);
      slidePose(s, st.clip, k, kw, { s: pop * (1 + 0.07 * beat(t, tm + 0.55, 1, 0.5)), o: prog(t, tm, 0.12) });
    },
  },
  {
    id: 'kinetic-scroll',
    title: 'Kinetic: scroll into slide reveal',
    kind: 'vision',
    duration: 8.5,
    blurb: 'Lines scroll up like credits: each new part pushes the last one up. Then the mark appears and the name slides out of it, as in Slide reveal.',
    setup(s) {
      const size = visionSize(s) * (s.portrait ? 0.8 : 0.78);
      const st = s.place(LOCKUP_BOX, { size: lockupSize(s) });
      st.lh = size * 1.12 * (s.portrait ? 2 : 1);
      st.stack = el('g', {}, s.top);
      st.p1 = phrase(s, gospelLines(s), { size, cy: s.H / 2, parent: st.stack });
      const sz = st.p1.size;
      st.p2 = phrase(s, [['Together']], { size: sz, cy: s.H / 2 + st.lh, parent: st.stack });
      st.p3 = phrase(s, [['Wholeheartedly']], { size: sz, cy: s.H / 2 + st.lh * (s.portrait ? 1.5 : 2), parent: st.stack });
      st.step3 = s.portrait ? 1.5 : 2;
      windowClip(s, st.p1, 'c1');
      st.clip = slideSetup(s);
      return st;
    },
    frame(s, st, t) {
      const { p1, p2, p3 } = st;
      wipeLR(p1, ep(t, 0.2, 0.9, ease.inOutCubic));
      // Each arrival pushes the whole stack up by one line.
      const s1 = ep(t, 1.7, 0.7, ease.inOutCubic);
      const s2 = ep(t, 2.9, 0.7, ease.inOutCubic);
      const scroll = s1 * st.lh + s2 * (st.step3 - 1) * st.lh;
      const away = ep(t, 4.4, 0.6, ease.inCubic);
      set(st.stack, { transform: `translate(0 ${-scroll - away * s.H * 0.15})`, opacity: 1 - away });
      // Older lines dim as they move up.
      p1.g.setAttribute('opacity', 1 - 0.65 * s1);
      placeWords(p2, { o: prog(t, 1.75, 0.3) * (1 - 0.65 * s2) });
      placeWords(p3, { o: prog(t, 2.95, 0.3) });
      // Then: Slide reveal.
      const tm = 5.0;
      const pop = ep(t, tm, 0.9, ease.spring);
      const k = ep(t, tm + 1.2, 1.1, ease.inOutQuint);
      const kw = ep(t, tm + 1.2, 1.25, ease.inOutQuint);
      slidePose(s, st.clip, k, kw, { s: pop, o: prog(t, tm, 0.15) });
    },
  },
];
