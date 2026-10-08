// Schema-driven settings. A screen describes its options once; defaults, links, saving and the panel
// all come from that list. Pure apart from the localStorage helpers (always in try/catch).
//
//   { key, type: 'seg'|'check'|'number'|'time'|'text'|'lines', label, param, default,
//     options (seg), min/max/unit (number), text (check), when: values => bool, noSave }
(function () {
  const HB = (globalThis.HB = globalThis.HB || {});

  // Every screen gets a theme; it is added after the screen's own settings.
  const THEME = { key: 'theme', type: 'seg', label: 'Theme', options: [['dark', 'Dark'], ['light', 'Light']], default: 'dark', param: 'theme' };
  const withTheme = schema => (schema.some(s => s.key === 'theme') ? schema : [...schema, THEME]);

  const clone = v => (Array.isArray(v) ? v.map(clone) : v);
  const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
  const paramOf = s => s.param || s.key;

  const defaults = schema => Object.fromEntries(schema.map(s => [s.key, clone(s.default)]));

  // Turn one raw value (from a link or storage) into a valid value for the field, or undefined if unusable.
  function coerce(s, v) {
    if (v == null) return undefined;
    switch (s.type) {
      case 'seg': return s.options.some(o => o[0] === v) ? v : undefined;
      case 'check': return typeof v === 'boolean' ? v : v !== '0' && v !== 'false';
      case 'number': {
        const n = Number(v);
        if (v === '' || !Number.isFinite(n)) return undefined;
        const r = Math.round(n);
        return Math.min(s.max ?? Infinity, Math.max(s.min ?? -Infinity, r));
      }
      case 'time': return /^\d{1,2}:\d{2}$/.test(v) ? v : undefined;
      case 'text': return typeof v === 'string' ? v : undefined;
      case 'lines': return Array.isArray(v) && v.length ? v : undefined;
    }
  }

  // Lines in links: one `m=` param per item, its lines joined by |.
  const splitLines = v => v.split('|').map(l => l.trim()).filter(Boolean);

  // Read link params. Returns only the values the link sets. Screens may add their own rules
  // through `schema.legacy` (e.g. the countdown's "?at= implies until").
  function fromParams(schema, params, legacy) {
    const out = {};
    for (const s of withTheme(schema)) {
      const p = paramOf(s);
      let raw;
      if (s.type === 'lines') {
        const items = params.getAll(p).map(splitLines).filter(m => m.length);
        raw = items.length ? items : undefined;
      } else if (params.has(p)) raw = params.get(p);
      const v = coerce(s, raw);
      if (v !== undefined) out[s.key] = v;
    }
    return legacy ? legacy(out, params) : out;
  }

  // Write a link query from values: every value that differs from its default, plus any `always` keys.
  // `autostart` adds a bare ?autostart flag.
  function toParams(schema, values, { autostart = false, always = [] } = {}) {
    const p = new URLSearchParams();
    for (const s of withTheme(schema)) {
      const v = values[s.key];
      if (v === undefined || (same(v, s.default) && !always.includes(s.key))) continue;
      if (s.when && !s.when(values) && !always.includes(s.key)) continue;
      const name = paramOf(s);
      if (s.type === 'lines') v.forEach(m => p.append(name, m.join('|')));
      else if (s.type === 'check') p.set(name, v ? '1' : '0');
      else p.set(name, String(v));
    }
    let q = p.toString();
    if (autostart) q += (q ? '&' : '') + 'autostart';
    return q;
  }

  // ---- storage (per screen) ----
  const storeKey = id => `heartbeat-screens:${id}`;
  function load(id) {
    try { const v = JSON.parse(localStorage.getItem(storeKey(id))); return v && typeof v === 'object' ? v : {}; } catch { return {}; }
  }
  function save(id, values) {
    try { localStorage.setItem(storeKey(id), JSON.stringify(values)); } catch {}
  }
  // Drop values that equal their default or that must not be remembered, so a later change to a default still reaches users.
  function savable(schema, values, skip = []) {
    const out = {};
    for (const s of withTheme(schema)) {
      if (skip.includes(s.key) || same(values[s.key], s.default)) continue;
      out[s.key] = values[s.key];
    }
    return out;
  }
  // Merge order: defaults < saved < link. Saved values are validated the same way as link values.
  function resolve(schema, saved, linked) {
    const out = defaults(withTheme(schema));
    for (const s of withTheme(schema)) {
      const v = coerce(s, saved?.[s.key]);
      if (v !== undefined) out[s.key] = v;
    }
    return Object.assign(out, linked);
  }

  Object.assign(HB, { THEME, withTheme, defaults, coerce, fromParams, toParams, load, save, savable, resolve, splitLines });
})();
