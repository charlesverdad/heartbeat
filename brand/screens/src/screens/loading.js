// Loading screen: the mark in one of four motions (blink, hop, fill, bar) with a caption and dots that
// light in turn. A pure function of time — no countdown, no heartbeat pulsing.
(function () {
  const { G, mod, ep, ease, lerp } = HB;

  // The three mark letters, animated individually for blink / hop / fill.
  const PARTS = ['H', 'B', 'C'];

  const schema = [
    { key: 'style', type: 'seg', label: 'Style', options: [['blink', 'Blink'], ['hop', 'Hop'], ['fill', 'Fill'], ['bar', 'Bar']], default: 'blink', param: 'style' },
    { key: 'caption', type: 'text', label: 'Caption', default: 'Loading', param: 'caption' },
    { key: 'showCaption', type: 'check', label: 'Caption', text: 'Show caption', default: true, param: 'cap' },
  ];

  // ---------- DOM ----------
  const $ = id => document.getElementById(id);
  const logo = $('logo'), caption = $('caption'), capText = $('capText'), dots = $('dots');

  // Track elements, rebuilt when the style changes. The bar adds a track + segment under the lockup.
  // Fill stacks two copies of the mark: a faint outline that stays, and a solid fill that is clipped.
  let markEl = null, fillEl = null, trackEl = null, segEl = null, dotEls = [];

  function build(style, showCaption) {
    logo.innerHTML = '';
    logo.className = 'logo';
    fillEl = null;
    if (style === 'bar') {
      logo.classList.add('bar-wrap');
      const wrap = document.createElement('div');
      wrap.innerHTML = HB.lockupSVG();
      markEl = wrap.firstElementChild;
      logo.appendChild(markEl);
      trackEl = document.createElement('div'); trackEl.className = 'track';
      segEl = document.createElement('div'); segEl.className = 'seg';
      trackEl.appendChild(segEl);
      logo.appendChild(trackEl);
    } else if (style === 'fill') {
      // Outline copy (faint, stays throughout) under the solid fill copy (clipped by script).
      const outlineWrap = document.createElement('div');
      outlineWrap.innerHTML = HB.markSVG();
      markEl = outlineWrap.firstElementChild;
      markEl.classList.add('mark-only', 'mark-outline');
      const fillWrap = document.createElement('div');
      fillWrap.innerHTML = HB.markSVG();
      fillEl = fillWrap.firstElementChild;
      fillEl.classList.add('mark-only', 'mark-fill');
      fillEl.style.position = 'absolute';
      // Stack the fill exactly over the outline.
      logo.style.position = 'relative';
      logo.appendChild(markEl);
      logo.appendChild(fillEl);
      trackEl = segEl = null;
    } else {
      const wrap = document.createElement('div');
      wrap.innerHTML = HB.markSVG();
      markEl = wrap.firstElementChild;
      markEl.classList.add('mark-only');
      logo.style.position = '';
      logo.appendChild(markEl);
      trackEl = segEl = null;
    }
    // Per-letter transform origin (hop) lives on the inner paths via CSS .mark .H etc.
    caption.style.display = showCaption ? '' : 'none';
  }

  // ---------- draw ----------
  // Ported from the motion kit loaders (brand/logo-motion/src/anims-v3.js): load-blink, load-hop,
  // load-fill and load-bar, in seconds and logo units, so the motion matches the rendered videos.
  // Each letter's box in logo units, for hopping from its bottom centre.
  const BOX = { H: [0, 0, 49.83, 53.82], B: [51.87, 28.87, 93.43, 82.7], C: [14.56, 55.61, 49.94, 111.27] };
  // A Gaussian bump centred on each cycle (shifted by half a period so it never wraps mid-bump).
  const pulse = (t, P, w) => G(mod(t + P / 2, P) - P / 2, 0, w);

  function letters() {
    const m = markEl && markEl.querySelector('.mark');
    return m ? PARTS.map(k => [k, m.querySelector('.' + k)]).filter(([, el]) => el) : [];
  }

  function draw(t, SET) {
    if (!markEl) return;
    const els = letters();

    if (SET.style === 'blink') {
      // The letters light in turn, H to B to C.
      els.forEach(([, el], i) => el.setAttribute('opacity', 0.16 + 0.84 * pulse(t - 0.4 * i, 1.2, 0.24)));
    } else if (SET.style === 'hop') {
      // Each letter hops 20 logo units for the first 0.42 s of its 1.2 s cycle, stretching a little.
      els.forEach(([k, el], i) => {
        const ph = mod(t - 0.14 * i, 1.2);
        const h = ph < 0.42 ? Math.sin((Math.PI * ph) / 0.42) : 0;
        const [x0, , x1, y1] = BOX[k], cx = (x0 + x1) / 2;
        el.setAttribute('transform', `translate(0 ${-20 * h}) translate(${cx} ${y1}) scale(${1 - 0.04 * h} ${1 + 0.05 * h}) translate(${-cx} ${-y1})`);
      });
    } else if (SET.style === 'fill') {
      // The solid copy fills from the bottom up, holds, then drains out of the top.
      const tt = mod(t, 2.2);
      const top = 1 - ep(tt, 0.1, 1.1, ease.inOutCubic);
      const bottom = 1 - ep(tt, 1.45, 0.65, ease.inOutCubic);
      if (fillEl) fillEl.style.clipPath = bottom > top ? `inset(${(top * 100).toFixed(2)}% 0 ${((1 - bottom) * 100).toFixed(2)}% 0)` : 'inset(100% 0 0 0)';
    } else if (SET.style === 'bar' && segEl) {
      // A segment sweeps the track, easing in and out and stretching mid-way.
      const k = ease.inOutCubic(mod(t, 1.8) / 1.8);
      const len = 0.18 + 0.22 * Math.sin(Math.PI * k);
      segEl.style.width = `${len * 100}%`;
      segEl.style.left = `${lerp(-len, 1, k) * 100}%`;
    }

    // Dots after the caption light in turn.
    if (SET.showCaption) dotEls.forEach((d, i) => { d.style.opacity = 0.2 + 0.8 * pulse(t - 0.25 * i, 1.2, 0.22); });
  }

  // ---------- wiring ----------
  const panel = HB.panel({
    id: 'loading',
    title: 'Loading settings',
    schema,
    onChange(key, v) {
      if (key === 'style' || key === 'showCaption') build(v.style, v.showCaption);
      if (key === 'caption') capText.textContent = v.caption;
    },
  });

  capText.textContent = panel.values.caption;
  dotEls = [...dots.querySelectorAll('i')];
  build(panel.values.style, panel.values.showCaption);

  HB.loop(t => draw(t, panel.values));
})();
