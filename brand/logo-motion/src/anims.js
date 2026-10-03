// The animation catalogue. Each entry:
//   id, title, kind ('mark' | 'lockup' | 'vision'), duration (s), loop?, blurb,
//   setup(s)        -> state, called once after the scene is built
//   frame(s, st, t) -> sets every animated attribute for time t (must be idempotent)
import {
  MARK_BOX, LOCKUP_BOX, VISION, clamp, lerp, prog, ep, ease, beat, el, set, tf, markSize, lockupSize,
} from './core.js';

const hideWord = s => s.word.setAttribute('display', 'none');

// Logo-space offset (in px on screen) -> logo units.
const px = (st, v) => v / st.k;

// An outlined copy of the mark, drawn behind it, for echo / sonar rings.
function echoes(s, n, { strokePx = 2 } = {}) {
  return Array.from({ length: n }, () => {
    const g = s.mark.cloneNode(true);
    g.removeAttribute('transform');
    set(g, { fill: 'none', stroke: s.th.fg, 'stroke-width': strokePx, opacity: 0 });
    g.querySelectorAll('polygon,path').forEach(p => p.setAttribute('vector-effect', 'non-scaling-stroke'));
    s.logo.insertBefore(g, s.mark);
    return g;
  });
}
const MARK_C = [(MARK_BOX[0] + MARK_BOX[2]) / 2, (MARK_BOX[1] + MARK_BOX[3]) / 2];

// The ECG trace, in screen px, with the R spike at (cx, cy).
function ecgPath(s, cx, cy, A) {
  const p = (dx, dy) => `${cx + dx * A} ${cy + dy * A}`;
  return [
    `M ${-20} ${cy}`, `L ${p(-1.5, 0)}`, `Q ${p(-1.3, -0.32)} ${p(-1.1, 0)}`, `L ${p(-0.42, 0)}`, `L ${p(-0.3, 0.16)}`,
    `L ${p(-0.08, -1.05)}`, `L ${p(0.12, 0.5)}`, `L ${p(0.26, 0)}`, `L ${p(0.75, 0)}`,
    `Q ${p(1.05, -0.42)} ${p(1.35, 0)}`, `L ${s.W + 20} ${cy}`,
  ].join(' ');
}

// Words of the vision, laid out per aspect.
function visionLines(s, mode = 'two') {
  if (mode === 'stack') return [['Living', 'Out'], ['The', 'Gospel'], ['Together'], ['Wholeheartedly']];
  if (s.portrait) return [['Living', 'Out', 'The'], ['Gospel', 'Together'], ['Wholeheartedly']];
  return [['Living', 'Out', 'The', 'Gospel'], ['Together', 'Wholeheartedly']];
}
const placeWord = (w, { dy = 0, o = 1, s = 1 } = {}) => {
  w.t.setAttribute('transform', `translate(${w.x} ${w.y + dy}) scale(${s})`);
  w.t.setAttribute('opacity', clamp(o));
};

export const ANIMS = [
  // ───────────────────────────── mark only ─────────────────────────────
  {
    id: 'mark-stack',
    title: 'Stack',
    kind: 'mark',
    duration: 3.2,
    blurb: 'H drops in from above, B slides in from the right, C rises from below. Each piece lands with a small overshoot.',
    setup(s) {
      hideWord(s);
      return s.place(MARK_BOX, { size: markSize(s) });
    },
    frame(s, st, t) {
      const far = px(st, s.H * 0.7);
      const { H, B, C } = s.parts;
      const k1 = ep(t, 0.15, 0.7, ease.outBack);
      const k2 = ep(t, 0.45, 0.7, ease.outBack);
      const k3 = ep(t, 0.75, 0.7, ease.outBack);
      tf(H.g, { y: lerp(-far, 0, k1), o: prog(t, 0.15, 0.15) });
      tf(B.g, { x: lerp(far, 0, k2), o: prog(t, 0.45, 0.15) });
      tf(C.g, { y: lerp(far, 0, k3), o: prog(t, 0.75, 0.15) });
      // Whole mark settles with a tiny push as the last piece lands.
      const push = Math.sin(clamp((t - 1.2) / 0.45) * Math.PI) * 0.025;
      tf(s.mark, { s: 1 + push, ox: MARK_C[0], oy: MARK_C[1] });
    },
  },
  {
    id: 'mark-pulse',
    title: 'Pulse',
    kind: 'mark',
    duration: 3.6,
    blurb: 'The mark springs in, then beats twice (lub-dub) and sends an outline echo outward on each beat.',
    setup(s) {
      hideWord(s);
      const st = s.place(MARK_BOX, { size: markSize(s) });
      st.echo = echoes(s, 4, { strokePx: Math.max(2, s.H / 500) });
      return st;
    },
    frame(s, st, t) {
      const pop = ep(t, 0.1, 0.9, ease.spring);
      const beats = [1.35, 2.35];
      const b = beats.reduce((a, bt) => a + beat(t, bt, 1, 0.55), 0);
      tf(s.mark, { s: pop * (1 + 0.07 * b), ox: MARK_C[0], oy: MARK_C[1], o: prog(t, 0.1, 0.2) });
      st.echo.forEach((g, i) => {
        const bt = beats[i >> 1] + (i & 1) * 0.22;
        const k = prog(t, bt, 1.1);
        tf(g, { s: 1 + ease.outCubic(k) * (i & 1 ? 0.45 : 0.7), ox: MARK_C[0], oy: MARK_C[1] });
        g.setAttribute('opacity', k > 0 && k < 1 ? (1 - k) * (i & 1 ? 0.35 : 0.6) : 0);
      });
    },
  },
  {
    id: 'mark-ecg',
    title: 'ECG',
    kind: 'mark',
    duration: 4,
    blurb: 'A heart-monitor line sweeps across the screen. The mark pops out of the spike as the line clears.',
    setup(s) {
      hideWord(s);
      const size = markSize(s);
      const st = s.place(MARK_BOX, { size });
      const cy = s.H / 2;
      const line = el('path', {
        d: ecgPath(s, s.W / 2, cy, size * 0.62), fill: 'none', stroke: s.th.fg,
        'stroke-width': Math.max(4, size / 45), 'stroke-linejoin': 'round', 'stroke-linecap': 'round',
      }, s.back);
      // Find where along the path the spike sits so the mark pops on cue.
      const L = line.getTotalLength();
      let lo = 0, hi = L;
      for (let i = 0; i < 30; i++) { const m = (lo + hi) / 2; line.getPointAtLength(m).x < s.W / 2 ? (lo = m) : (hi = m); }
      Object.assign(st, { line, L, spike: lo / L });
      return st;
    },
    frame(s, st, t) {
      const head = ep(t, 0, 1.9, ease.inOutCubic);
      const tail = ep(t, 0.7, 1.9, ease.inOutCubic);
      set(st.line, {
        'stroke-dasharray': `${(head - tail) * st.L} ${st.L * 2}`,
        'stroke-dashoffset': -tail * st.L,
        opacity: head - tail > 0.001 ? 1 : 0,
      });
      // Pop when the tail clears the spike.
      const tPop = 0.7 + 1.9 * 0.5;
      const k = ep(t, tPop - 0.15, 0.9, ease.spring);
      tf(s.mark, { s: k, ox: MARK_C[0], oy: MARK_C[1], o: prog(t, tPop - 0.15, 0.12) });
    },
  },
  {
    id: 'mark-draw',
    title: 'Draw',
    kind: 'mark',
    duration: 3.6,
    blurb: 'Each piece is traced as a thin outline, then fills in solid. Calm and precise.',
    setup(s) {
      hideWord(s);
      const st = s.place(MARK_BOX, { size: markSize(s) });
      for (const p of Object.values(s.parts)) {
        set(p.shape, { pathLength: 1, stroke: s.th.fg, 'stroke-width': px(st, Math.max(3, s.H / 260)), 'stroke-linejoin': 'round', 'stroke-dasharray': '1 1' });
      }
      return st;
    },
    frame(s, st, t) {
      ['H', 'B', 'C'].forEach((k, i) => {
        const { shape } = s.parts[k];
        const d = ep(t, 0.1 + i * 0.3, 1.2, ease.inOutCubic);
        const f = ep(t, 1.5 + i * 0.15, 0.6, ease.outCubic);
        set(shape, { 'stroke-dashoffset': 1 - d, 'fill-opacity': f, 'stroke-opacity': 1 - f * 0.999 });
      });
    },
  },
  {
    id: 'mark-flip',
    title: 'Flip',
    kind: 'mark',
    duration: 3,
    blurb: 'Each piece turns over like a card, one after another along the diagonal.',
    setup(s) {
      hideWord(s);
      return s.place(MARK_BOX, { size: markSize(s) });
    },
    frame(s, st, t) {
      ['H', 'B', 'C'].forEach((k, i) => {
        const p = s.parts[k];
        const q = prog(t, 0.2 + i * 0.28, 0.85);
        // Rotate about the vertical axis: scaleX follows cos, with a slight lift.
        const ang = (1 - ease.outBack(q, 1.4)) * Math.PI * 0.5;
        const sx = Math.max(0.0001, Math.cos(ang));
        tf(p.g, { sx, sy: 1, ox: p.c[0], oy: p.c[1], y: px(st, -12) * Math.sin(ang), o: q > 0 ? 1 : 0 });
      });
    },
  },
  {
    id: 'mark-wipe',
    title: 'Wipe',
    kind: 'mark',
    duration: 3,
    blurb: 'Each piece slides out from behind an invisible edge: H downward, B left to right, C right to left.',
    setup(s) {
      hideWord(s);
      const st = s.place(MARK_BOX, { size: markSize(s) });
      for (const [k, p] of Object.entries(s.parts)) {
        const id = s.uid(`clip-${k}`);
        const cp = el('clipPath', { id }, s.defs);
        const [x0, y0, x1, y1] = p.box;
        el('rect', { x: x0 - 0.5, y: y0 - 0.5, width: x1 - x0 + 1, height: y1 - y0 + 1 }, cp);
        p.g.setAttribute('clip-path', `url(#${id})`);
      }
      return st;
    },
    frame(s, st, t) {
      const dirs = { H: [0, -1], B: [-1, 0], C: [1, 0] };
      ['H', 'B', 'C'].forEach((k, i) => {
        const p = s.parts[k];
        const [x0, y0, x1, y1] = p.box;
        const k1 = 1 - ep(t, 0.15 + i * 0.32, 0.9, ease.outExpo);
        const [dx, dy] = dirs[k];
        set(p.shape, { transform: `translate(${dx * (x1 - x0 + 2) * k1} ${dy * (y1 - y0 + 2) * k1})` });
      });
    },
  },
  {
    id: 'mark-zoom',
    title: 'Zoom out',
    kind: 'mark',
    duration: 3,
    blurb: 'Starts inside the H, so the whole frame is solid colour, then pulls back fast to reveal the mark. Strong opener.',
    setup(s) {
      hideWord(s);
      return s.place(MARK_BOX, { size: markSize(s) });
    },
    frame(s, st, t) {
      const k = ep(t, 0, 1.5, ease.inOutCubic);
      // Interpolate zoom in log space so the pull-back feels even.
      const z = Math.pow(35, 1 - k);
      // Zoom about a point inside H's left leg, drifting to the mark centre.
      const ox = lerp(12, MARK_C[0], k);
      const oy = lerp(26, MARK_C[1], k);
      const r = lerp(-8, 0, k);
      s.mark.setAttribute('transform', `translate(${MARK_C[0]} ${MARK_C[1]}) rotate(${r}) scale(${z}) translate(${-ox} ${-oy})`);
    },
  },
  {
    id: 'mark-assemble',
    title: 'Assemble',
    kind: 'mark',
    duration: 3.2,
    blurb: 'The three pieces start scattered and rotated, then spring together into the mark.',
    setup(s) {
      hideWord(s);
      return s.place(MARK_BOX, { size: markSize(s) });
    },
    frame(s, st, t) {
      const from = { H: [-60, -45, -90], B: [70, -20, 120], C: [-30, 60, 75] };
      ['H', 'B', 'C'].forEach((k, i) => {
        const p = s.parts[k];
        const q = ep(t, 0.1 + i * 0.12, 1.5, ease.spring);
        const [fx, fy, fr] = from[k];
        tf(p.g, {
          x: lerp(fx, 0, q), y: lerp(fy, 0, q), r: lerp(fr, 0, q), s: lerp(0.4, 1, clamp(q)),
          ox: p.c[0], oy: p.c[1], o: prog(t, 0.1 + i * 0.12, 0.3),
        });
      });
    },
  },
  {
    id: 'mark-three-beats',
    title: 'Three beats',
    kind: 'mark',
    duration: 3.6,
    blurb: 'Each piece arrives on a heartbeat (H, B, C), then the whole mark beats once.',
    setup(s) {
      hideWord(s);
      const st = s.place(MARK_BOX, { size: markSize(s) });
      st.echo = echoes(s, 1, { strokePx: Math.max(2, s.H / 500) });
      return st;
    },
    frame(s, st, t) {
      const at = { H: 0.3, B: 0.55, C: 1.25 };
      for (const k of ['H', 'B', 'C']) {
        const p = s.parts[k];
        const q = prog(t, at[k], 0.45);
        tf(p.g, { s: ease.outBack(q, 3), ox: p.c[0], oy: p.c[1], o: q > 0 ? 1 : 0 });
      }
      const b = beat(t, 2.2, 1, 0.5);
      tf(s.mark, { s: 1 + 0.08 * b, ox: MARK_C[0], oy: MARK_C[1] });
      const e = prog(t, 2.2, 1.2);
      tf(st.echo[0], { s: 1 + ease.outCubic(e) * 0.6, ox: MARK_C[0], oy: MARK_C[1] });
      st.echo[0].setAttribute('opacity', e > 0 && e < 1 ? (1 - e) * 0.6 : 0);
    },
  },
  {
    id: 'mark-heartbeat-loop',
    title: 'Heartbeat loop',
    kind: 'mark',
    duration: 2.4,
    loop: true,
    blurb: 'A seamless loop of the mark beating. Good for livestream holding screens and as a background.',
    setup(s) {
      hideWord(s);
      const st = s.place(MARK_BOX, { size: markSize(s) });
      st.echo = echoes(s, 2, { strokePx: Math.max(2, s.H / 500) });
      return st;
    },
    frame(s, st, t) {
      const P = 1.2;
      const ph = ((t % P) + P) % P;
      // Envelope wraps so the loop has no seam.
      const b = beat(ph, 0.25, 1, 0.55) + beat(ph + P, 0.25, 1, 0.55) + beat(ph - P, 0.25, 1, 0.55);
      tf(s.mark, { s: 1 + 0.06 * b, ox: MARK_C[0], oy: MARK_C[1] });
      st.echo.forEach((g, i) => {
        const e = (((ph - 0.25 - i * 0.22) % P) + P) % P / 0.95;
        tf(g, { s: 1 + ease.outCubic(clamp(e)) * (i ? 0.35 : 0.55), ox: MARK_C[0], oy: MARK_C[1] });
        g.setAttribute('opacity', e < 1 ? (1 - e) * (i ? 0.25 : 0.45) : 0);
      });
    },
  },

  // ───────────────────────────── full lockup ─────────────────────────────
  {
    id: 'lockup-build',
    title: 'Build',
    kind: 'lockup',
    duration: 3.8,
    blurb: 'The mark stacks in, then each letter of Heartbeat Church rises from a hidden baseline.',
    setup(s) {
      const st = s.place(LOCKUP_BOX, { size: lockupSize(s) });
      // Clip each line of the wordmark at its baseline so letters rise from nothing.
      [[27, 52.05], [56.5, 81.65]].forEach(([y0, y1], i) => {
        const cp = el('clipPath', { id: s.uid(`line-${i}`) }, s.defs);
        el('rect', { x: 95, y: y0, width: 170, height: y1 - y0 }, cp);
      });
      const lines = [el('g', { 'clip-path': `url(#${s.uid('line-0')})` }, s.word), el('g', { 'clip-path': `url(#${s.uid('line-1')})` }, s.word)];
      s.letters.forEach(l => lines[l.line].appendChild(l.g));
      return st;
    },
    frame(s, st, t) {
      const { H, B, C } = s.parts;
      tf(H.g, { y: lerp(-30, 0, ep(t, 0.1, 0.6, ease.outBack)), o: prog(t, 0.1, 0.12) });
      tf(B.g, { x: lerp(30, 0, ep(t, 0.3, 0.6, ease.outBack)), o: prog(t, 0.3, 0.12) });
      tf(C.g, { y: lerp(30, 0, ep(t, 0.5, 0.6, ease.outBack)), o: prog(t, 0.5, 0.12) });
      let i0 = 0, i1 = 0;
      s.letters.forEach(l => {
        const i = l.line ? i1++ : i0++;
        const q = ep(t, 1.0 + l.line * 0.25 + i * 0.05, 0.7, ease.outQuint);
        tf(l.g, { y: lerp(30, 0, q) });
      });
    },
  },
  {
    id: 'lockup-slide',
    title: 'Slide reveal',
    kind: 'lockup',
    duration: 4,
    blurb: 'The mark appears alone in the centre, then slides left and pulls the wordmark out from behind it.',
    setup(s) {
      const st = s.place(LOCKUP_BOX, { size: lockupSize(s) });
      const cp = el('clipPath', { id: s.uid('word-clip') }, s.defs);
      st.clip = el('rect', { x: 95, y: 0, width: 170, height: 112 }, cp);
      // Clip in logo space (not word space) so the edge stays put while the word moves.
      const wrap = el('g', { 'clip-path': `url(#${s.uid('word-clip')})` });
      s.logo.insertBefore(wrap, s.word);
      wrap.appendChild(s.word);
      st.off = (LOCKUP_BOX[2] - MARK_BOX[2]) / 2; // shift that centres the mark alone
      return st;
    },
    frame(s, st, t) {
      const pop = ep(t, 0.1, 0.9, ease.spring);
      const k = ep(t, 1.3, 1.1, ease.inOutQuint);
      const mx = st.off * (1 - k);
      tf(s.mark, { x: mx, s: pop, ox: MARK_C[0], oy: MARK_C[1], o: prog(t, 0.1, 0.15) });
      // The clip's left edge rides on the mark's right edge; letters trail slightly.
      set(st.clip, { x: 95 + mx });
      tf(s.word, { x: -110 * (1 - ep(t, 1.3, 1.25, ease.inOutQuint)) });
    },
  },
  {
    id: 'lockup-focus',
    title: 'Focus + beat',
    kind: 'lockup',
    duration: 3.6,
    blurb: 'The lockup pulls into focus from a soft blur, then beats once with an echo. Quiet, good for endings.',
    setup(s) {
      const st = s.place(LOCKUP_BOX, { size: lockupSize(s) });
      const f = el('filter', { id: s.uid('soft'), x: '-30%', y: '-30%', width: '160%', height: '160%' }, s.defs);
      st.blur = el('feGaussianBlur', { stdDeviation: 0 }, f);
      s.logo.setAttribute('filter', `url(#${s.uid('soft')})`);
      st.echo = echoes(s, 1, { strokePx: Math.max(2, s.H / 500) });
      return st;
    },
    frame(s, st, t) {
      const k = ep(t, 0, 1.6, ease.outCubic);
      set(st.blur, { stdDeviation: lerp(12, 0, k) });
      const b = beat(t, 2.1, 1, 0.5);
      tf(s.mark, { s: lerp(0.94, 1, k) * (1 + 0.07 * b), ox: MARK_C[0], oy: MARK_C[1], o: k });
      tf(s.word, { x: lerp(6, 0, k), o: k });
      const e = prog(t, 2.1, 1.1);
      tf(st.echo[0], { s: 1 + ease.outCubic(e) * 0.5, ox: MARK_C[0], oy: MARK_C[1] });
      st.echo[0].setAttribute('opacity', e > 0 && e < 1 ? (1 - e) * 0.5 : 0);
    },
  },

  // ───────────────────────────── with the vision ─────────────────────────────
  {
    id: 'vision-endcard',
    title: 'End card',
    kind: 'vision',
    duration: 6,
    blurb: 'The lockup builds, then the vision fades up word by word underneath. Made for the end of a video.',
    setup(s) {
      const size = lockupSize(s) * (s.portrait ? 1.05 : 0.95);
      const cy = s.H * (s.portrait ? 0.42 : 0.4);
      const st = s.place(LOCKUP_BOX, { size, cy });
      const fs = s.portrait ? s.W * 0.066 : s.aspect === '1x1' ? s.W * 0.05 : s.H * 0.056;
      st.words = s.text(visionLines(s), { size: fs, weight: 500, cy: cy + size * 0.5 + fs * (s.portrait ? 3.1 : 2.4) });
      return st;
    },
    frame(s, st, t) {
      const { H, B, C } = s.parts;
      tf(H.g, { y: lerp(-24, 0, ep(t, 0.1, 0.6, ease.outBack)), o: prog(t, 0.1, 0.12) });
      tf(B.g, { x: lerp(24, 0, ep(t, 0.25, 0.6, ease.outBack)), o: prog(t, 0.25, 0.12) });
      tf(C.g, { y: lerp(24, 0, ep(t, 0.4, 0.6, ease.outBack)), o: prog(t, 0.4, 0.12) });
      const w = ep(t, 0.7, 0.9, ease.outQuint);
      tf(s.word, { x: lerp(-10, 0, w), o: w });
      st.words.forEach((wd, i) => {
        const q = ep(t, 1.6 + i * 0.22, 0.8, ease.outCubic);
        placeWord(wd, { dy: lerp(wd.size * 0.5, 0, q), o: q });
      });
    },
  },
  {
    id: 'vision-kinetic',
    title: 'Kinetic vision',
    kind: 'vision',
    duration: 8,
    blurb: 'Big type, one phrase at a time: Living Out, The Gospel, Together, Wholeheartedly. Then the lockup lands. For reels and openers.',
    setup(s) {
      const big = s.portrait ? s.W * 0.15 : s.aspect === '1x1' ? s.W * 0.13 : s.H * 0.17;
      const phrases = [['Living', 'Out'], ['The', 'Gospel'], ['Together'], ['Wholeheartedly']];
      const st = { phrases: [], big };
      for (const p of phrases) {
        // Shrink long phrases so they fit with margin.
        let ws = s.text([p], { size: big, weight: 700, cy: s.H / 2, tracking: -0.03 });
        const w = ws.at(-1).x + ws.at(-1).w - ws[0].x;
        if (w > s.W * 0.86) {
          ws.forEach(x => x.t.remove());
          ws = s.text([p], { size: (big * s.W * 0.86) / w, weight: 700, cy: s.H / 2, tracking: -0.03 });
        }
        st.phrases.push(ws);
      }
      // Phrases slide through a window that hugs one line of type.
      const cp = el('clipPath', { id: s.uid('kin') }, s.defs);
      el('rect', { x: 0, y: s.H / 2 - big * 0.55, width: s.W, height: big * 1.25 }, cp);
      s.top.setAttribute('clip-path', `url(#${s.uid('kin')})`);
      Object.assign(st, s.place(LOCKUP_BOX, { size: lockupSize(s) }));
      return st;
    },
    frame(s, st, t) {
      const slot = 1.3;
      const travel = st.big * 1.3;
      st.phrases.forEach((ws, i) => {
        const tin = 0.2 + i * slot;
        const tout = tin + slot - 0.32;
        ws.forEach((w, j) => {
          const d = ep(t, tin + j * 0.07, 0.6, ease.outExpo);
          const o = ep(t, tout + j * 0.03, 0.32, ease.inCubic);
          placeWord(w, { dy: lerp(travel, 0, d) - o * travel, o: t >= tin ? 1 : 0 });
        });
      });
      const tm = 0.2 + 4 * slot;
      const { H, B, C } = s.parts;
      tf(H.g, { y: lerp(-24, 0, ep(t, tm, 0.6, ease.outBack)), o: prog(t, tm, 0.1) });
      tf(B.g, { x: lerp(24, 0, ep(t, tm + 0.12, 0.6, ease.outBack)), o: prog(t, tm + 0.12, 0.1) });
      tf(C.g, { y: lerp(24, 0, ep(t, tm + 0.24, 0.6, ease.outBack)), o: prog(t, tm + 0.24, 0.1) });
      const w = ep(t, tm + 0.45, 0.8, ease.outQuint);
      tf(s.word, { x: lerp(-10, 0, w), o: w });
      const b = beat(t, tm + 1.6, 1, 0.5);
      tf(s.mark, { s: 1 + 0.06 * b, ox: MARK_C[0], oy: MARK_C[1] });
    },
  },
  {
    id: 'vision-heartbeat',
    title: 'Vision on the beat',
    kind: 'vision',
    duration: 7.5,
    blurb: 'The mark beats steadily. On each beat one word of the vision appears, ending on "Wholeheartedly".',
    setup(s) {
      hideWord(s);
      const size = markSize(s) * (s.portrait ? 0.85 : 0.72);
      const cy = s.H * (s.portrait ? 0.38 : 0.36);
      const st = s.place(MARK_BOX, { size, cy });
      const fs = s.portrait ? s.W * 0.074 : s.aspect === '1x1' ? s.W * 0.056 : s.H * 0.064;
      st.words = s.text(visionLines(s), { size: fs, weight: 500, cy: cy + size * 0.5 + fs * (s.portrait ? 3.2 : 2.3) });
      st.echo = echoes(s, 2, { strokePx: Math.max(2, s.H / 500) });
      st.mc = MARK_C;
      return st;
    },
    frame(s, st, t) {
      const beats = [0.9, 1.75, 2.6, 3.45, 4.3, 5.25];
      const pop = ep(t, 0.05, 0.8, ease.spring);
      let b = 0;
      beats.forEach((bt, i) => (b += beat(t, bt, i === 5 ? 1.4 : 1, 0.5)));
      tf(s.mark, { s: pop * (1 + 0.06 * b), ox: MARK_C[0], oy: MARK_C[1], o: prog(t, 0.05, 0.15) });
      st.words.forEach((w, i) => {
        const q = ep(t, beats[i] - 0.04, 0.5, ease.outBack);
        placeWord(w, { dy: lerp(w.size * 0.35, 0, clamp(q)), o: prog(t, beats[i] - 0.04, 0.12) });
      });
      st.echo.forEach((g, i) => {
        const e = prog(t, 5.25 + i * 0.22, 1.2);
        tf(g, { s: 1 + ease.outCubic(e) * (i ? 0.45 : 0.75), ox: MARK_C[0], oy: MARK_C[1] });
        g.setAttribute('opacity', e > 0 && e < 1 ? (1 - e) * (i ? 0.3 : 0.55) : 0);
      });
    },
  },
];

export const byId = id => ANIMS.find(a => a.id === id);
