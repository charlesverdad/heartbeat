// Helpers for laying out a screen on whatever size window or projector it lands on.
(function () {
  const HB = (globalThis.HB = globalThis.HB || {});

  // Shrink a block so every line fits maxW x maxH. `el` holds one or more <span> lines; the block's own
  // CSS font-size is the starting point, and we only ever scale down.
  function fitText(el, maxW, maxH, lineSel = 'span') {
    el.style.fontSize = '';
    const base = parseFloat(getComputedStyle(el).fontSize);
    let k = 1;
    el.querySelectorAll(lineSel).forEach(sp => { k = Math.min(k, maxW / Math.max(sp.scrollWidth, sp.offsetWidth)); });
    k = Math.min(k, maxH / el.offsetHeight);
    if (k < 1) el.style.fontSize = `${base * k * 0.98}px`;
  }

  // Call onResize({W, H, portrait}) now, on every size change, and once fonts are in (they change text widths).
  // Toggles .portrait on the stage when it is taller than wide.
  function watchStage(stage, onResize) {
    const run = () => {
      const W = stage.clientWidth, H = stage.clientHeight, portrait = H > W;
      stage.classList.toggle('portrait', portrait);
      onResize({ W, H, portrait });
    };
    new ResizeObserver(run).observe(stage);
    document.fonts?.ready.then(run);
    run();
    return run;
  }

  // requestAnimationFrame loop calling fn(timeSeconds) with seconds since the loop began.
  function loop(fn) {
    const t0 = performance.now();
    (function frame() { fn((performance.now() - t0) / 1000); requestAnimationFrame(frame); })();
  }

  Object.assign(HB, { fitText, watchStage, loop });
})();
