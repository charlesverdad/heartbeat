// The "card" layout shared by Starting soon and Be right back: lockup above a heading that ends in three
// dots lighting in turn, with small lines under it. Needs core.js, logo.js, stage.js and card.css.
(function () {
  const HB = (globalThis.HB = globalThis.HB || {});
  const { G, mod } = HB;

  // Build the card inside `stage`. Returns { setHeading(text), addSub(el), fit(), frame(t) }.
  HB.card = function (stage) {
    const root = stage.appendChild(document.createElement('div'));
    root.className = 'card';
    root.innerHTML = `<div class="card-logo" role="img" aria-label="Heartbeat Church">${HB.lockupSVG()}</div><h1 class="card-h"></h1>`;
    const h = root.querySelector('h1');
    let dots = [];

    function setHeading(text) {
      h.textContent = '';
      const words = String(text).trim().split(/\s+/);
      const last = words.pop() || '';
      if (words.length) h.append(words.join(' ') + ' ');
      const tail = h.appendChild(document.createElement('span'));
      tail.className = 'tail';
      tail.append(last);
      const d = tail.appendChild(document.createElement('span'));
      d.className = 'dots';
      d.setAttribute('aria-hidden', 'true');
      dots = [0, 1, 2].map(() => d.appendChild(document.createElement('i')));
      fit();
    }

    // Shrink the heading until the whole group fits the screen (long custom headings).
    function fit() {
      h.style.fontSize = '';
      const H = stage.clientHeight, W = stage.clientWidth;
      if (!H) return;
      const base = parseFloat(getComputedStyle(h).fontSize);
      let size = base;
      const kids = [...root.children].filter(k => !k.hidden);
      const group = () => kids[kids.length - 1].getBoundingClientRect().bottom - kids[0].getBoundingClientRect().top;
      const over = () => group() > H * 0.86 || h.scrollWidth > W * 0.9 || h.getBoundingClientRect().height > H * 0.36;
      for (let i = 0; i < 24 && over() && size > 12; i++) { size *= 0.93; h.style.fontSize = `${size}px`; }
    }

    // Three dots lighting in turn: period 1.2 s, 0.25 s apart, a Gaussian bump from 0.2 to 1.
    function frame(t) {
      dots.forEach((d, i) => { d.style.opacity = 0.2 + 0.8 * G(mod(t - 0.25 * i + 0.6, 1.2) - 0.6, 0, 0.22); });
    }

    return { root, setHeading, fit, frame, addSub: el => root.appendChild(el) };
  };
})();
