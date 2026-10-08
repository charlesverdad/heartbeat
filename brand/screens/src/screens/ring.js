// Ring countdown: the mark inside a thin ring that drains clockwise over the whole count, with the
// time underneath. At zero the ring refills, mark and ring glide to the centre and grow, the ring
// ripples out once and goes, leaving the mark. No beats: everything here is calm.
(function () {
  const { clamp, lerp, ease, ep } = HB;
  const NS = 'http://www.w3.org/2000/svg';
  const [, , MARK_W, MARK_H] = HB.LOGO.markBox;

  const schema = [
    ...HB.timerSchema,
    HB.THEME,
    { key: 'label', type: 'text', label: 'Label', default: 'Service begins in', param: 'label' },
  ];

  // ---------- DOM ----------
  const $ = id => document.getElementById(id);
  const stage = $('stage'), art = $('art'), label = $('label'), under = $('under');
  const setClock = HB.rollClock($('clock'));
  const svgEl = (name, attrs, parent) => {
    const e = document.createElementNS(NS, name);
    for (const k in attrs) e.setAttribute(k, attrs[k]);
    return parent.appendChild(e);
  };
  // Everything the ring is made of sits in one group so it can move and scale as a unit.
  const mark = svgEl('g', { fill: 'currentColor' }, art);
  mark.innerHTML = HB.LOGO.mark;
  const ring = svgEl('g', { fill: 'none', stroke: 'currentColor' }, art);
  const track = svgEl('circle', { cx: 0, cy: 0, 'stroke-opacity': 0.16 }, ring);
  const arc = svgEl('circle', { cx: 0, cy: 0, transform: 'rotate(-90)' }, ring);
  const ripple = svgEl('circle', { cx: 0, cy: 0, opacity: 0 }, ring);
  const dot = svgEl('circle', { fill: 'currentColor', stroke: 'none' }, ring);

  // ---------- geometry (stage px), measured on resize ----------
  let g = null;
  function measure({ W, H, portrait }) {
    const r = Math.min(H * 0.22, W * 0.3);
    const sw = r * 0.035, C = 2 * Math.PI * r;
    const ls = portrait ? W * 0.035 : H * 0.026;
    g = {
      W, H, r, sw, C, cy: H * 0.42,
      m0: r * 0.95,                                 // mark height inside the ring
      m1: portrait ? W * 0.42 : H * 0.38,           // mark height once landed
    };
    art.setAttribute('viewBox', `0 0 ${W} ${H}`);
    stage.style.setProperty('--ring-r', `${r}px`);
    stage.style.setProperty('--ring-cy', `${g.cy}px`);
    stage.style.setProperty('--ls', `${ls}px`);
    stage.style.setProperty('--cs', `${portrait ? W * 0.14 : H * 0.1}px`);
    [track, arc, ripple].forEach(c => { c.setAttribute('r', r); c.setAttribute('stroke-width', sw); });
    arc.setAttribute('stroke-dasharray', C);
  }

  // Draw the screen for t seconds into a COUNT-second countdown.
  function render(f) {
    const { t, COUNT, n, phase, done, idle } = f;
    setClock(n, phase);
    const { W, r, sw, C } = g;
    // Label and clock fade as zero arrives.
    const out = idle ? 0 : ep(t, COUNT, 0.5, ease.inCubic);
    under.style.opacity = 1 - out;

    // The ring drains with the time left; after zero it refills fast.
    const fill = idle ? 1 : done ? ep(t, COUNT + 0.15, 0.8) : clamp((COUNT - t) / COUNT);
    // Mark and ring travel to the centre together, growing as they go.
    const km = idle ? 0 : ep(t, COUNT + 0.3, 1.1, ease.inOutCubic);
    const size = lerp(g.m0, g.m1, km);
    const cy = lerp(g.cy, g.H / 2, km);
    const k = size / g.m0;
    const ms = size / MARK_H;
    mark.setAttribute('transform', `translate(${W / 2 - (MARK_W * ms) / 2} ${cy - size / 2}) scale(${ms})`);
    ring.setAttribute('transform', `translate(${W / 2} ${cy}) scale(${k})`);

    // After landing the ring ripples out once and the track goes with it.
    const kr = idle ? 0 : ep(t, COUNT + 1.6, 1.3);
    const gone = idle ? 0 : clamp((t - COUNT - 1.6) / 0.25);
    arc.setAttribute('stroke-dashoffset', C * (1 - fill));
    arc.setAttribute('opacity', 1 - gone);
    track.setAttribute('stroke-opacity', 0.16 * (1 - gone));
    ripple.setAttribute('r', r * (1 + 0.42 * kr));
    ripple.setAttribute('opacity', kr > 0 ? 1 - kr : 0);
    // A small dot rides the head of the arc.
    const a = (-90 + 360 * fill) * (Math.PI / 180);
    dot.setAttribute('cx', r * Math.cos(a));
    dot.setAttribute('cy', r * Math.sin(a));
    dot.setAttribute('r', sw * 1.1);
    dot.setAttribute('opacity', done ? 1 - clamp((t - COUNT - 0.9) / 0.2) : 1);
  }

  // ---------- wiring ----------
  HB.countdownScreen({
    id: 'ring',
    title: 'Ring countdown settings',
    schema,
    onChange(key, v) { if (key === 'label') label.textContent = v.label; },
    ready(v) {
      label.textContent = v.label;
      HB.watchStage(stage, measure);
    },
    render: f => render(f),
  });
})();
