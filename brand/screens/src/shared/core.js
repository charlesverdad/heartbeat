// Pure helpers shared by every screen: easing, timing maths and time formatting.
// A classic script (no import/export) so it can be inlined into a page and loaded by node tests.
(function () {
  const HB = (globalThis.HB = globalThis.HB || {});

  const clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v));
  const lerp = (a, b, k) => a + (b - a) * k;
  const mod = (a, n) => ((a % n) + n) % n;
  const ease = {
    outCubic: k => 1 - Math.pow(1 - k, 3),
    inCubic: k => k * k * k,
    inOutCubic: k => (k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2),
  };
  // Eased progress of t through [start, start + dur].
  const ep = (t, start, dur, fn = ease.outCubic) => fn(clamp((t - start) / dur));
  // Gaussian bump centred on c, width w (peaks at 1).
  const G = (x, c, w) => Math.exp(-Math.pow((x - c) / w, 2));

  // Where a COUNT-second countdown stands at t seconds: whole seconds left, and how far into this second.
  function tick(t, COUNT) {
    const R = COUNT - t;
    if (R <= 0) return { n: 0, phase: -R, done: true };
    const n = Math.ceil(R - 1e-6);
    return { n, phase: n - R, done: false };
  }

  // M:SS, or H:MM:SS when more than an hour is left.
  const pad = v => String(v).padStart(2, '0');
  const fmt = n => (n >= 3600
    ? `${Math.floor(n / 3600)}:${pad(Math.floor(n / 60) % 60)}:${pad(n % 60)}`
    : `${Math.floor(n / 60)}:${pad(n % 60)}`);

  // Seconds from nowMs until a time of day like "11:00". A time already gone today means tomorrow.
  // nowMs is injectable so tests don't depend on the clock.
  function secondsUntil(hhmm, nowMs = Date.now()) {
    const m = /^(\d{1,2}):(\d{2})/.exec(hhmm || '');
    if (!m) return null;
    const d = new Date(nowMs);
    d.setHours(+m[1], +m[2], 0, 0);
    if (d.getTime() <= nowMs) d.setDate(d.getDate() + 1);
    return (d.getTime() - nowMs) / 1000;
  }

  // "11:00" -> "11:00 AM" in the viewer's locale.
  function formatClockTime(hhmm) {
    const m = /^(\d{1,2}):(\d{2})/.exec(hhmm || '');
    if (!m) return '';
    const d = new Date(2000, 0, 1, +m[1], +m[2]);
    return d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
  }

  Object.assign(HB, { clamp, lerp, mod, ease, ep, G, tick, pad, fmt, secondsUntil, formatClockTime });
})();
