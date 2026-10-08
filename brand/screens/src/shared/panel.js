// The settings panel, built from a schema (see settings.js): Minimise / H / Esc, click anywhere to bring it
// back, full screen, wake lock, Copy link, toast and keyboard shortcuts.
//
//   const panel = HB.panel({
//     id: 'countdown',                 // storage key + page identity
//     title: 'Countdown settings',
//     schema: [...],                   // screen settings; Theme is added for you
//     legacy: (out, params) => out,    // optional: extra link-param rules
//     linkKeys: values => ['kind'],    // optional: keys always written to Copy link
//     skipSave: ['messages'],          // optional: never remembered in this browser
//     startable: true,                 // has a start action: shows "Start on open", honours ?autostart
//     actions: [{ id:'reset', label:'Reset', onclick }, { id:'go', label:'Start', primary:true, onclick }],
//     keys: { ' ': fn, r: fn },        // extra shortcuts by e.key.toLowerCase(); also listed by `keyHelp`
//     keyHelp: [['Space', 'start / pause'], ['R', 'reset']],
//     onChange(key, values) {},        // after any setting changes (not on first load)
//     enter() {},                      // Enter pressed in a number/time field
//     linesHelp: 'text under the editor', // optional
//   });
//   panel.values          current settings object (read-only; change with panel.set)
//   panel.set(key, value) change a setting and update UI, storage, theme
//   panel.setAction(id, { text, disabled })
//   panel.toast(msg, ms), panel.show(open), panel.keepAwake(), panel.demo, panel.autostart
//
// ?demo: no DOM, no storage, no keys: just values from the link.
(function () {
  const HB = (globalThis.HB = globalThis.HB || {});

  const h = (tag, attrs = {}, ...kids) => {
    const e = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) {
      if (v == null || v === false) continue;
      if (k === 'text') e.textContent = v;
      else if (k.startsWith('on')) e[k] = v;
      else e.setAttribute(k, v === true ? '' : v);
    }
    // Skip empty children so `cond && h(...)` can be passed straight in.
    kids.flat().forEach(c => { if (c != null && c !== false && c !== '') e.append(c); });
    return e;
  };
  const toText = list => list.map(m => m.join('\n')).join('\n\n');
  const fromText = txt => txt.split(/\n\s*\n/).map(b => b.split('\n').map(l => l.trim()).filter(Boolean)).filter(m => m.length);
  const MAC = /Mac|iPhone|iPad/.test(globalThis.navigator?.platform || globalThis.navigator?.userAgent || '');
  const FS_KEYS = MAC ? 'fn F (or ⌃⌘F)' : 'F11';

  function setLook(look) {
    document.body.dataset.look = look === 'light' ? 'light' : 'dark';
  }

  HB.panel = function (o) {
    const schema = HB.withTheme(o.schema);
    const q = new URLSearchParams(location.search);
    const demo = q.has('demo');
    const autostart = q.has('autostart') && !!o.startable && !demo;
    const linked = HB.fromParams(o.schema, q, o.legacy);
    const values = HB.resolve(schema, demo ? {} : HB.load(o.id), linked);
    // Link values for list fields are for this visit only; they are not remembered unless edited.
    const linkOnly = new Set(schema.filter(s => s.type === 'lines' && linked[s.key]).map(s => s.key));
    const api = { values, demo, autostart, schema };
    const ctl = {}; // per key: { show(values), set(value) } wired to the DOM

    setLook(values.theme);
    if (demo) {
      Object.assign(api, { set(k, v) { values[k] = v; if (k === 'theme') setLook(v); o.onChange?.(k, values); }, setAction() {}, toast() {}, show() {}, keepAwake() {} });
      return api;
    }

    // ---------- DOM ----------
    const remember = () => HB.save(o.id, HB.savable(schema, values, [...(o.skipSave || []), ...linkOnly]));

    const rowsEl = h('div', { class: 'rows' });
    let lastV = null;
    for (const s of schema) {
      const field = fieldFor(s);
      if (s.inline && lastV) { lastV.append(field.el); ctl[s.key] = field; continue; }
      const k = h('span', { class: 'k', text: s.label });
      const v = h('div', { class: 'v' }, field.el);
      rowsEl.append(k, v);
      field.row = [k, v];
      lastV = v;
      ctl[s.key] = field;
    }

    function fieldFor(s) {
      if (s.type === 'seg') {
        const btns = s.options.map(([val, text]) => h('button', { 'data-v': val, 'aria-pressed': 'false', text, onclick: () => api.set(s.key, val) }));
        return { el: h('div', { class: 'seg', role: 'group', 'aria-label': s.label }, btns), show: v => btns.forEach(b => b.setAttribute('aria-pressed', b.dataset.v === v)) };
      }
      if (s.type === 'check') {
        const inp = h('input', { type: 'checkbox', onchange: () => api.set(s.key, inp.checked) });
        return { el: h('label', { class: 'check' }, inp, ' ' + (s.text || s.label)), show: v => { inp.checked = v; } };
      }
      if (s.type === 'number' || s.type === 'time' || s.type === 'text') {
        const inp = h('input', { type: s.type === 'text' ? 'text' : s.type, 'aria-label': s.label, min: s.min, max: s.max, step: s.type === 'number' ? 1 : null,
          onkeydown: e => { if (e.key === 'Enter') o.enter?.(); },
          // Typing: accept valid values at once, but leave the text alone until the field is left (so "1" on the way to "10" survives).
          oninput: () => { const v = HB.coerce(s, inp.value); if (v !== undefined && v !== values[s.key]) api.set(s.key, v, inp); },
          onchange: () => { const v = HB.coerce(s, inp.value); if (v !== undefined) api.set(s.key, v); else inp.value = values[s.key]; } });
        const el = h('span', { class: 'field' }, inp, s.unit && h('span', { class: 'unit', text: s.unit }));
        return { el, show: (v, from) => { if (from !== inp) inp.value = v; } };
      }
      // lines: opens the editor below
      const btn = h('button', { 'aria-expanded': 'false', text: `Edit ${s.label.toLowerCase()}`, onclick: () => openEditor(s, !editorBox.hidden && editorFor === s ? false : true) });
      return { el: btn, show() {} };
    }

    // Lines editor and share box share one slot each.
    let editorFor = null;
    const area = h('textarea', { id: 'p-text', spellcheck: 'true' });
    const areaLabel = h('label', { for: 'p-text' });
    const editorBox = h('div', { class: 'editor', hidden: true }, areaLabel, area,
      h('p', { text: o.linesHelp || 'Leave a blank line between messages. Each line break inside a message is kept on wide screens; tall screens may wrap long lines.' }),
      h('div', { class: 'row-end' },
        h('button', { text: 'Use defaults', onclick: () => { area.value = toText(editorFor.default); } }),
        h('button', { class: 'primary', text: 'Save', onclick: () => {
          const list = fromText(area.value);
          linkOnly.delete(editorFor.key);
          api.set(editorFor.key, list.length ? list : HB.defaults([editorFor])[editorFor.key]);
          openEditor(null, false);
        } })));
    function openEditor(s, open) {
      editorBox.hidden = !open;
      document.querySelectorAll('.controls [aria-expanded]').forEach(b => { if (b !== shareBtn) b.setAttribute('aria-expanded', 'false'); });
      if (!open) { editorFor = null; return; }
      editorFor = s;
      shareBox.hidden = true; shareBtn.setAttribute('aria-expanded', 'false');
      areaLabel.textContent = s.label;
      area.value = toText(values[s.key]);
      ctl[s.key].el.setAttribute('aria-expanded', 'true');
      area.focus();
    }

    const linkInput = h('input', { id: 'p-link', readonly: true });
    const autoBox = h('input', { type: 'checkbox', checked: true, onchange: () => { linkInput.value = shareLink(); } });
    const copyBtn = h('button', { class: 'primary', text: 'Copy', onclick: () => {
      const link = linkInput.value = shareLink();
      const done = ok => { copyBtn.textContent = ok ? 'Copied' : 'Select and copy'; setTimeout(() => { copyBtn.textContent = 'Copy'; }, 1800); };
      try { navigator.clipboard.writeText(link).then(() => done(true), () => { linkInput.select(); done(false); }); }
      catch { linkInput.select(); done(false); }
    } });
    const shareBox = h('div', { class: 'editor', hidden: true },
      h('label', { for: 'p-link', text: 'Link with these settings' }), linkInput,
      h('p', { text: "Opening this link applies these settings. Bookmark it, or point ProPresenter's web view at it." }),
      h('div', { class: 'row-end' }, o.startable && h('label', { class: 'check' }, autoBox, ' Start on open'), copyBtn));
    function shareLink() {
      const always = o.linkKeys ? o.linkKeys(values) : [];
      const query = HB.toParams(o.schema, values, { autostart: !!o.startable && autoBox.checked, always: ['theme', ...always] });
      return location.href.split(/[?#]/)[0] + (query ? '?' + query : '');
    }
    const shareBtn = h('button', { 'aria-expanded': 'false', text: 'Copy link', onclick: () => {
      const open = shareBox.hidden;
      if (open) openEditor(null, false);
      shareBox.hidden = !open; shareBtn.setAttribute('aria-expanded', open);
      if (open) linkInput.value = shareLink();
    } });
    const fsBtn = h('button', { text: 'Full screen', onclick: toggleFullscreen });
    const actionEls = {};
    const pair = h('span', { class: 'pair' }, (o.actions || []).map(a => (actionEls[a.id] = h('button', { class: a.primary ? 'primary' : null, text: a.label, onclick: a.onclick }))));
    const keyList = [...(o.keyHelp || []), ['F', 'full screen'], ['H', 'hide / show settings']];
    const keysEl = h('div', { class: 'keys' }, keyList.flatMap(([k, t], i) => [i ? ' · ' : '', h('kbd', { text: k }), ' ' + t]));
    const hideBtn = h('button', { text: 'Minimise', title: 'Hide settings (H). Click anywhere to bring them back.', onclick: () => api.show(false) });
    const panelEl = h('div', { class: 'controls', role: 'dialog', 'aria-label': o.title },
      h('div', { class: 'head' }, h('strong', { text: o.title }), hideBtn),
      rowsEl, editorBox, shareBox,
      h('div', { class: 'foot' }, fsBtn, shareBtn, h('span', { class: 'grow' }), pair), keysEl);
    const toastEl = h('div', { class: 'toast', role: 'status', hidden: true });
    document.body.append(panelEl, toastEl);

    // ---------- settings ----------
    function sync(from) {
      for (const s of schema) {
        const c = ctl[s.key];
        c.show(values[s.key], from);
        const on = !s.when || s.when(values);
        if (c.row) c.row.forEach(e => { e.hidden = !on; }); else c.el.hidden = !on;
      }
    }
    api.set = function (key, value, from) {
      values[key] = value;
      if (key === 'theme') setLook(value);
      sync(from);
      remember();
      o.onChange?.(key, values);
    };
    api.setAction = (id, { text, disabled }) => {
      const b = actionEls[id];
      if (!b) return;
      if (text != null) b.textContent = text;
      if (disabled != null) b.disabled = disabled;
    };
    sync();

    // ---------- show / hide ----------
    const stage = o.stage || document.querySelector('.stage');
    api.show = function (open) {
      if (open === !panelEl.classList.contains('hide')) return;
      panelEl.classList.toggle('hide', !open);
      if (!open) {
        if (panelEl.contains(document.activeElement)) document.activeElement.blur();
        api.toast('Settings hidden. Click anywhere (or press H) to bring them back.', 2200);
      }
    };
    // A link that starts itself opens with the settings already minimised, ready for the screen.
    if (autostart) panelEl.classList.add('hide');
    // A click on the screen brings the settings back; a double-click is full screen, so wait to tell them apart.
    let clickTimer;
    stage.addEventListener('click', () => { clearTimeout(clickTimer); clickTimer = setTimeout(() => api.show(true), 260); });
    stage.addEventListener('dblclick', () => { clearTimeout(clickTimer); toggleFullscreen(); });
    // The cursor hides after a few still seconds while the settings are minimised.
    let cursorTimer;
    document.addEventListener('mousemove', () => {
      document.body.classList.remove('idle-ui');
      clearTimeout(cursorTimer);
      cursorTimer = setTimeout(() => { if (panelEl.classList.contains('hide')) document.body.classList.add('idle-ui'); }, 2500);
    }, { passive: true });

    // ---------- keyboard ----------
    document.addEventListener('keydown', e => {
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      if (e.target.tagName === 'TEXTAREA' || (e.target.tagName === 'INPUT' && e.key !== 'Escape')) return;
      const k = e.key.toLowerCase();
      const own = o.keys?.[k];
      if (own) { if (k === ' ') e.preventDefault(); own(e); }
      else if (k === 'f') toggleFullscreen();
      else if (k === 'l') api.set('theme', values.theme === 'light' ? 'dark' : 'light');
      else if (k === 'h') api.show(panelEl.classList.contains('hide'));
      else if (e.key === 'Escape') api.show(false);
    });

    // ---------- toast, full screen, wake lock ----------
    let toastTimer;
    api.toast = function (msg, ms = 6000) {
      toastEl.textContent = msg;
      toastEl.hidden = false;
      clearTimeout(toastTimer);
      toastTimer = setTimeout(() => { toastEl.hidden = true; }, ms);
    };
    // Full screen takes the whole display, hiding Chrome's tabs and toolbar. Browsers can refuse
    // (an embedding frame without permission, a window without focus); then say how to do it by hand.
    function toggleFullscreen() {
      const d = document;
      try {
        if (d.fullscreenElement || d.webkitFullscreenElement) { (d.exitFullscreen || d.webkitExitFullscreen).call(d); return; }
        const e = d.documentElement;
        const req = e.requestFullscreen || e.webkitRequestFullscreen;
        if (!req || d.fullscreenEnabled === false) return refused();
        req.call(e, { navigationUI: 'hide' })?.catch?.(refused);
      } catch { refused(); }
    }
    const refused = () => api.toast(`Chrome didn’t allow full screen here. Press ${FS_KEYS} to make the window full screen.`);
    document.addEventListener('fullscreenchange', () => { fsBtn.textContent = document.fullscreenElement ? 'Exit full screen' : 'Full screen'; });

    let wake = null, wanted = false;
    api.keepAwake = async function () {
      wanted = true;
      try { if ('wakeLock' in navigator && !wake) { wake = await navigator.wakeLock.request('screen'); wake.addEventListener('release', () => { wake = null; }); } } catch { wake = null; }
    };
    document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'visible' && wanted) api.keepAwake(); });

    return api;
  };
  HB.panelText = { toText, fromText };
})();
