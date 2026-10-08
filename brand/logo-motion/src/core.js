// Scene engine for the Heartbeat logo animations.
// Every animation is a pure function of time: frame(scene, t) sets attributes,
// so the same code plays live in the browser and renders frame-exact to video.

const NS = 'http://www.w3.org/2000/svg';

// Geometry lifted verbatim from Heartbeat_Brandmark_Main_Black.svg (viewBox 0 0 252.2 111.27).
export const LOGO = {
  H: { tag: 'polygon', attrs: { points: '49.83 0 25.59 0 25.59 8.98 24.1 8.98 24.1 0 0 0 0 53.82 24.1 53.82 24.1 44.84 25.59 44.84 25.59 53.82 49.83 53.82 49.83 0' }, box: [0, 0, 49.83, 53.82] },
  B: { tag: 'path', attrs: { d: 'M51.87,82.7V28.87h20.96c6.21,0,15.08,1.6,15.08,12.73,0,10.46-7.43,12.48-10.54,12.48v1.5c6.8,0,16.03,1.74,16.03,13.48s-9.23,13.63-14.2,13.63h-27.34Z' }, box: [51.87, 28.87, 93.43, 82.7] },
  C: { tag: 'path', attrs: { d: 'M14.56,82.05c0-13.8,9.31-26.44,35.38-26.44v27.09h-8.98v1.5h8.98v27.06c-26.22,0-35.38-11.39-35.38-25.94v-3.28Z' }, box: [14.56, 55.61, 49.94, 111.27] },
  heartbeat: 'M117.24,51.98v-9.45h-8.95v9.45h-5.11v-22.31h5.11v8.78h8.95v-8.78h5.08v22.31h-5.08ZM132.87,49.46c2.14,0,2.99-1.2,3.35-3.43l4.11,1.2c-.76,3.08-3.35,5.17-7.63,5.17-4.87,0-7.93-3.23-7.93-8.22s3.2-8.22,7.87-8.22c4.96,0,7.54,3.14,7.57,8.86h-10.51c.12,3.17,1.23,4.64,3.17,4.64ZM132.66,39.01c-1.61,0-2.55,1.29-2.88,3.58h5.64c-.15-2.44-.97-3.58-2.76-3.58ZM147.36,42.3l-4.2-.76c-.06-.24-.09-.62-.09-.88,0-3.49,3.52-4.7,6.6-4.7,4.17,0,6.46,1.41,6.46,4.64v7.31c0,1.06.41,1.47,1.2,1.47.44,0,.79-.12,1.06-.21v2.38c-.47.44-1.61.85-2.96.85-1.56,0-2.85-.62-3.38-1.64-.12-.23-.18-.47-.21-.73h-.21c-.56,1.06-2.17,2.38-4.73,2.38s-4.7-1.47-4.7-4.29,1.85-3.7,5.22-4.58c2.14-.53,3.2-.85,3.87-1.38v-1.17c0-1.41-.53-2-2-2-1.38,0-2.14.68-2.14,2.05,0,.41.06.85.18,1.26ZM148.62,49.61c1.12,0,2.32-.76,2.7-1.79v-3.2c-.38.29-1.29.59-2.47.97-1.38.41-2.14.82-2.14,2.14,0,1.12.62,1.88,1.91,1.88ZM160.39,51.98v-15.62h4.49v3.02h.21c.68-2.03,2.35-3.43,4.17-3.43,1.94,0,3.58.97,3.58,3.79,0,.91-.21,1.76-.56,2.52l-3.85.09c.18-.56.29-1.09.29-1.91s-.35-1.23-1.14-1.23c-1.67,0-2.41,1.88-2.41,5.28v7.48h-4.78ZM176.01,48.28v-8.69h-2.41v-3.23h2.41v-5.46h4.78v5.46h4.34v3.23h-4.34v8.19c0,.91.38,1.29,1.23,1.29,1.14,0,1.32-.62,1.32-1.88,0-.56-.09-1.12-.15-1.41l2.47.32c.18.35.38,1.5.38,2.2,0,2.14-1.12,4.08-5.05,4.08-2.79,0-4.99-.91-4.99-4.11ZM191.51,51.98h-3.35v-22.31h4.64v9.22h.26c.79-1.94,2.61-2.94,4.78-2.94,3.43,0,6.43,2.41,6.43,8.22s-3.61,8.22-6.87,8.22c-2.26,0-4.02-1.03-4.96-2.82h-.29l-.65,2.41ZM192.95,44.15c0,3.35,1.17,5.14,3.23,5.14s3.2-1.64,3.2-5.11-1.09-5.11-3.23-5.11c-1.88,0-3.2,1.61-3.2,5.08ZM214.19,49.46c2.14,0,2.99-1.2,3.35-3.43l4.11,1.2c-.76,3.08-3.35,5.17-7.63,5.17-4.87,0-7.93-3.23-7.93-8.22s3.2-8.22,7.87-8.22c4.96,0,7.54,3.14,7.57,8.86h-10.51c.12,3.17,1.23,4.64,3.17,4.64ZM213.99,39.01c-1.61,0-2.55,1.29-2.88,3.58h5.64c-.15-2.44-.97-3.58-2.76-3.58ZM228.68,42.3l-4.2-.76c-.06-.24-.09-.62-.09-.88,0-3.49,3.52-4.7,6.6-4.7,4.17,0,6.46,1.41,6.46,4.64v7.31c0,1.06.41,1.47,1.2,1.47.44,0,.79-.12,1.06-.21v2.38c-.47.44-1.61.85-2.96.85-1.56,0-2.85-.62-3.38-1.64-.12-.23-.18-.47-.21-.73h-.21c-.56,1.06-2.17,2.38-4.73,2.38s-4.7-1.47-4.7-4.29,1.85-3.7,5.22-4.58c2.14-.53,3.2-.85,3.87-1.38v-1.17c0-1.41-.53-2-2-2-1.38,0-2.14.68-2.14,2.05,0,.41.06.85.18,1.26ZM229.94,49.61c1.12,0,2.32-.76,2.7-1.79v-3.2c-.38.29-1.29.59-2.47.97-1.38.41-2.14.82-2.14,2.14,0,1.12.62,1.88,1.91,1.88ZM242.17,48.28v-8.69h-2.41v-3.23h2.41v-5.46h4.78v5.46h4.34v3.23h-4.34v8.19c0,.91.38,1.29,1.23,1.29,1.14,0,1.32-.62,1.32-1.88,0-.56-.09-1.12-.15-1.41l2.47.32c.18.35.38,1.5.38,2.2,0,2.14-1.12,4.08-5.05,4.08-2.79,0-4.99-.91-4.99-4.11Z',
  church: 'M112.43,58.83c5.34,0,8.42,2.91,9.36,7.07l-4.52,1.85c-.5-3.43-2.08-5.08-4.81-5.08-3.52,0-5.43,3.02-5.43,7.75s1.91,7.75,5.69,7.75,5.02-2.82,5.28-5.9l4.64,1.82c-.85,4.02-3.9,7.9-9.98,7.9-7.16,0-11.04-5.17-11.04-11.56s3.93-11.59,10.8-11.59ZM124.41,81.58v-22.31h4.49v9.69h.21c.82-2.44,2.76-3.4,4.99-3.4,3.58,0,5.08,1.91,5.08,5.05v10.98h-4.78v-10.48c0-1.53-.7-2.29-2.14-2.29-1.97,0-3.05,1.44-3.05,4.26v8.51h-4.78ZM156.21,65.97v15.62h-4.26v-2.67h-.26c-.88,2.2-2.88,3.08-5.02,3.08-3.52,0-5.22-1.79-5.22-5.19v-10.83h4.78v10.39c0,1.59.85,2.38,2.23,2.38,1.85,0,2.96-1.2,2.96-4.05v-8.72h4.78ZM158.61,81.58v-15.62h4.49v3.02h.21c.67-2.03,2.35-3.43,4.17-3.43,1.94,0,3.58.97,3.58,3.79,0,.91-.21,1.76-.56,2.52l-3.85.09c.18-.56.29-1.09.29-1.91s-.35-1.23-1.14-1.23c-1.67,0-2.41,1.88-2.41,5.28v7.48h-4.78ZM171.95,73.78c0-5.02,3.08-8.22,7.9-8.22,4.2,0,6.11,2.38,6.69,5.49l-3.73,1.38c-.29-2.38-1.09-3.61-2.88-3.61-1.97,0-3.08,1.53-3.08,4.96s1.09,5.02,3.17,5.02,2.91-1.47,3.23-3.85l3.73,1.59c-.65,3.2-3.02,5.46-7.13,5.46-4.78,0-7.9-3.23-7.9-8.22ZM188.52,81.58v-22.31h4.49v9.69h.21c.82-2.44,2.76-3.4,4.99-3.4,3.58,0,5.08,1.91,5.08,5.05v10.98h-4.78v-10.48c0-1.53-.7-2.29-2.14-2.29-1.97,0-3.05,1.44-3.05,4.26v8.51h-4.78Z',
};

export const MARK_BOX = [0, 0, 93.43, 111.27];
export const LOCKUP_BOX = [0, 0, 252.2, 111.27];
export const VISION = ['Living', 'Out', 'The', 'Gospel', 'Together', 'Wholeheartedly'];

export const THEMES = {
  dark: { bg: '#000000', fg: '#ffffff', muted: 'rgba(255,255,255,0.55)' },
  light: { bg: '#ffffff', fg: '#000000', muted: 'rgba(0,0,0,0.55)' },
  alpha: { bg: 'none', fg: '#ffffff', muted: 'rgba(255,255,255,0.7)' },
};

export const ASPECTS = {
  '16x9': [1920, 1080],
  '1x1': [1080, 1080],
  '9x16': [1080, 1920],
};

// ---------- maths ----------
export const clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v));
export const lerp = (a, b, k) => a + (b - a) * k;
export const prog = (t, start, dur) => clamp((t - start) / dur);
export const ease = {
  linear: k => k,
  inCubic: k => k * k * k,
  outCubic: k => 1 - Math.pow(1 - k, 3),
  outQuart: k => 1 - Math.pow(1 - k, 4),
  outQuint: k => 1 - Math.pow(1 - k, 5),
  outExpo: k => (k >= 1 ? 1 : 1 - Math.pow(2, -10 * k)),
  inOutCubic: k => (k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2),
  inOutQuint: k => (k < 0.5 ? 16 * k ** 5 : 1 - Math.pow(-2 * k + 2, 5) / 2),
  inExpo: k => (k <= 0 ? 0 : Math.pow(2, 10 * k - 10)),
  inOutExpo: k => (k <= 0 ? 0 : k >= 1 ? 1 : k < 0.5 ? Math.pow(2, 20 * k - 10) / 2 : (2 - Math.pow(2, -20 * k + 10)) / 2),
  outBack: (k, s = 1.70158) => 1 + (s + 1) * Math.pow(k - 1, 3) + s * Math.pow(k - 1, 2),
  // Damped spring that settles at 1 by k=1.
  spring: (k, damp = 7, freq = 3.2) => (k >= 1 ? 1 : 1 - Math.exp(-damp * k) * Math.cos(freq * Math.PI * 2 * k * (1 - k * 0.15))),
};
// Eased progress in one call.
export const ep = (t, start, dur, fn = ease.outCubic) => fn(prog(t, start, dur));

// A "lub-dub" heartbeat envelope: two bumps, returns 0..1 around a beat at time b.
export function beat(t, b, strong = 1, weak = 0.6) {
  const bump = (c, w) => Math.exp(-Math.pow((t - c) / w, 2));
  return strong * bump(b, 0.07) + weak * bump(b + 0.22, 0.07);
}

// ---------- DOM ----------
export function el(tag, attrs = {}, parent) {
  const e = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  if (parent) parent.appendChild(e);
  return e;
}

export function set(e, attrs) {
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
}

// transform about a pivot (ox, oy) in the element's own coordinates.
export function tf(e, { x = 0, y = 0, s = 1, sx = s, sy = s, r = 0, ox = 0, oy = 0, o } = {}) {
  e.setAttribute('transform', `translate(${x + ox} ${y + oy}) rotate(${r}) scale(${sx} ${sy}) translate(${-ox} ${-oy})`);
  if (o !== undefined) e.setAttribute('opacity', clamp(o));
}

const centre = b => [(b[0] + b[2]) / 2, (b[1] + b[3]) / 2];

// Split a multi-subpath glyph run into one path per letter, keeping counters
// (the holes in e, a, b) with the letter whose box contains them.
function splitLetters(d, parent) {
  const subs = d.split(/(?=M)/).filter(Boolean);
  const probe = el('g', {}, parent);
  const items = subs.map(s => {
    const p = el('path', { d: s }, probe);
    const b = p.getBBox();
    return { d: s, box: [b.x, b.y, b.x + b.width, b.y + b.height] };
  });
  probe.remove();
  const inside = (a, b) => a[0] >= b[0] - 0.01 && a[2] <= b[2] + 0.01 && a[1] >= b[1] - 0.01 && a[3] <= b[3] + 0.01;
  const letters = [];
  for (const it of items) {
    const host = letters.find(l => inside(it.box, l.box));
    if (host) host.d += it.d;
    else letters.push({ ...it });
  }
  return letters.sort((a, b) => a.box[0] - b.box[0]);
}

let sceneCount = 0;

// Build the stage. Returns a scene object the animations drive.
export function buildScene(svg, { aspect = '16x9', theme = 'dark' } = {}) {
  const [W, H] = ASPECTS[aspect];
  const th = THEMES[theme];
  svg.innerHTML = '';
  set(svg, { viewBox: `0 0 ${W} ${H}`, width: W, height: H });
  const bg = el('rect', { x: 0, y: 0, width: W, height: H, fill: th.bg === 'none' ? 'transparent' : th.bg }, svg);
  const defs = el('defs', {}, svg);
  const back = el('g', { class: 'fx-back' }, svg);
  const logo = el('g', { class: 'logo', fill: th.fg }, svg);
  const mark = el('g', { class: 'mark' }, logo);
  const parts = {};
  for (const k of ['H', 'B', 'C']) {
    const g = el('g', { class: `part-${k}` }, mark);
    const shape = el(LOGO[k].tag, LOGO[k].attrs, g);
    parts[k] = { g, shape, box: LOGO[k].box, c: centre(LOGO[k].box) };
  }
  const word = el('g', { class: 'word' }, logo);
  const mk = (d, line) =>
    splitLetters(d, word).map(l => {
      const g = el('g', {}, word);
      const p = el('path', { d: l.d }, g);
      return { g, p, box: l.box, c: centre(l.box), line };
    });
  const letters = [...mk(LOGO.heartbeat, 0), ...mk(LOGO.church, 1)];
  const front = el('g', { class: 'fx-front' }, svg);
  const top = el('g', { class: 'top' }, svg);

  // SVG ids are document-global; prefix them so several stages can share a page.
  const prefix = `hb${++sceneCount}`;
  const scene = {
    uid: name => `${prefix}-${name}`,
    svg, W, H, aspect, theme, th, bg, defs, back, logo, mark, parts, word, letters, front, top,
    portrait: H > W,
    // Place a logo-space box so it is `size` px tall, centred on (cx, cy) in screen px.
    place(box = LOCKUP_BOX, { cx = W / 2, cy = H / 2, size } = {}) {
      const h = box[3] - box[1];
      const w = box[2] - box[0];
      const k = (size ?? H * 0.3) / h;
      const x = cx - (box[0] + w / 2) * k;
      const y = cy - (box[1] + h / 2) * k;
      set(logo, { transform: `translate(${x} ${y}) scale(${k})` });
      return { k, x, y };
    },
    // Lay out words as centred lines of SVG text in screen space.
    text(lines, { size = 64, weight = 700, cy = H / 2, lh = 1.12, fill = th.fg, tracking = -0.01, parent = top } = {}) {
      const words = [];
      const total = lines.length * size * lh;
      lines.forEach((line, li) => {
        const y = cy - total / 2 + size * lh * (li + 0.5) + size * 0.35;
        const tmp = line.map(wd => {
          const t = el('text', { 'font-family': 'Inter Tight', 'font-weight': weight, 'font-size': size, 'letter-spacing': `${tracking}em`, fill }, parent);
          t.textContent = wd;
          return t;
        });
        const space = size * 0.26;
        const widths = tmp.map(t => t.getComputedTextLength());
        const lw = widths.reduce((a, b) => a + b, 0) + space * (tmp.length - 1);
        let x = W / 2 - lw / 2;
        tmp.forEach((t, i) => {
          set(t, { x: 0, y: 0 });
          words.push({ t, x, y, w: widths[i], line: li, size });
          x += widths[i] + space;
        });
      });
      return words;
    },
  };
  return scene;
}

// Mark-only screen size that reads well on each aspect.
export const markSize = s => (s.portrait ? s.W * 0.42 : s.H * 0.38);
export const lockupSize = s => (s.portrait ? s.W * 0.3 : s.H * (s.aspect === '1x1' ? 0.24 : 0.26));
