const $ = s => document.querySelector(s);
const beacon = m => { try { fetch('/api/log', {method:'POST', body:String(m)}); } catch(e){} };
addEventListener('error', e => beacon('ERROR ' + e.message + ' @' + e.filename + ':' + e.lineno));
addEventListener('unhandledrejection', e => beacon('REJECT ' + e.reason));
const vid = $('#vid');
vid.src = '/video?s=' + Date.now();   // bypass any stale cache entry
vid.addEventListener('loadedmetadata', () => beacon(`video ready: ${vid.duration.toFixed(1)}s ${vid.videoWidth}x${vid.videoHeight}`));
vid.addEventListener('error', () => beacon('video error: code=' +
  (vid.error ? vid.error.code + ' ' + vid.error.message : '?') + ' src=' + vid.currentSrc));
vid.addEventListener('stalled', () => beacon('video stalled at ' + vid.currentTime));
let S = null, peaks = null, clips = [], sel = 0, edge = 'end', dirty = false;
let view = { c: 0, span: 24 };           // detail window: centre + seconds visible
let play = null;                          // active playback mode
let keptOnly = false;                     // when on, playback never leaves green
const keptBox = $('#keptonly');
try { keptOnly = localStorage.getItem('keptOnly') === '1'; } catch (e) {}
keptBox.checked = keptOnly;
keptBox.addEventListener('change', () => setKeptOnly(keptBox.checked));
function setKeptOnly(on) {
  keptOnly = on; keptBox.checked = on;
  try { localStorage.setItem('keptOnly', on ? '1' : '0'); } catch (e) {}
  invalidate();
}
function liveClips() {
  return clips.map((c, idx) => ({ ...c, idx })).filter(c => !c.deleted)
              .sort((a, b) => a.src_start - b.src_start);
}
// Where playback should be if only green may play: null = fine where it is,
// a clip = jump to its start, 'end' = nothing kept ahead.
function keptTarget(t) {
  const live = liveClips();
  if (live.some(c => c.src_start - 0.02 <= t && t < c.src_end)) return null;
  return live.find(c => c.src_start > t) || 'end';
}
const fmt = t => `${String(Math.floor(t/60)).padStart(2,'0')}:${(t%60).toFixed(1).padStart(4,'0')}`;
const clamp = (v,a,b) => Math.max(a, Math.min(b, v));

(async function init() {
  S = await (await fetch('/api/state')).json();
  peaks = new Uint8Array(await (await fetch('/peaks.u8')).arrayBuffer());
  clips = S.clips.map(c => ({ ...c, deleted: false }));
  $('#stats').textContent =
    `${clips.length} clips · source ${fmt(S.duration)} · keeping ${S.speaker} · from ${S.loaded_from}`;
  select(0);
  renderList();
  beacon(`booted: ${clips.length} clips, ${peaks.length} peak bins, ` +
         `${S.turns.length} turns, detail=${$('#detail').getBoundingClientRect().width|0}px`);
  requestAnimationFrame(tick);
  addEventListener('resize', invalidate);
  if (location.search.includes('selftest')) selftest();
})();

// Exercises the real handlers against the real DOM. Useful because synthetic
// input from outside the page does not always reach it.
function selftest() {
  const log = [], ok = (n, c) => log.push(`${c ? 'PASS' : 'FAIL'} ${n}`);
  try {
    const target = clips.findIndex(c => c.label === 'sermon');
    document.querySelector(`.clip[data-i="${target}"]`).click();
    ok('list click selects', sel === target);
    ok('header updates', $('#clipinfo').textContent.includes('#' + target));
    ok('transcript shown', $('#text').textContent.trim().length > 10);

    const before = cur().src_end;
    document.querySelector('[data-nudge="end,-0.5"]').click();
    ok('nudge end -0.5', Math.abs((before - 0.5) - cur().src_end) < 1e-6);
    document.querySelector('[data-nudge="end,0.5"]').click();
    ok('nudge restores', Math.abs(before - cur().src_end) < 1e-6);
    ok('save marked dirty', $('#save').classList.contains('dirty'));

    const s0 = cur().src_start;
    acts.snapstart();
    ok('snap start moves <=1.2s', Math.abs(cur().src_start - s0) <= 1.201);
    cur().src_start = s0;

    const n = clips.length;
    acts.del(); ok('drop marks deleted', cur().deleted === true);
    acts.del(); ok('restore clears it', cur().deleted === false);
    ok('clip count stable', clips.length === n);

    dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight' }));
    ok('ArrowRight advances', sel === target + 1);
    dispatchEvent(new KeyboardEvent('keydown', { key: ']' }));
    ok('] picks end edge', edge === 'end');

    const live = clips.filter(c => !c.deleted).length;
    ok('all clips live', live === clips.length);
    ok('waveform drawn', $('#detail').width > 0 && $('#over').width > 0);
    const lv = liveClips(), A = lv[5], B = lv[6];
    ok('kept-only: inside green stays put', keptTarget(A.src_start + 0.3) === null);
    const gapT = A.src_end + 0.01;
    const tg = keptTarget(gapT);
    ok('kept-only: after a clip jumps forward', tg === null || (tg !== 'end' && tg.src_start > gapT && tg.idx === B.idx));
    ok('kept-only: past the last clip ends', keptTarget(1e9) === 'end');
    setKeptOnly(true); ok('A toggles checkbox', keptBox.checked === true); setKeptOnly(false);
  } catch (e) { log.push('THREW ' + e + ' @' + (e.stack || '').split('\n')[1]); }
  beacon('SELFTEST ' + log.join(' | '));
}

/* ---------- selection ---------- */
function seek(t) {
  if (vid.readyState >= 1) { try { vid.currentTime = t; } catch (e) { beacon('seek: ' + e); } }
  else vid.src = '/video?s=' + Date.now();   // bypass any stale cache entry
vid.addEventListener('loadedmetadata', () => { vid.currentTime = t; }, { once: true });
}
function cur() { return clips[sel]; }
function select(i, doSeek = true) {
  sel = clamp(i, 0, clips.length - 1);
  const c = cur();
  view.c = (c.src_start + c.src_end) / 2;
  view.span = Math.max(12, (c.src_end - c.src_start) + 10);
  if (doSeek) { seek(c.src_start); play = null; }
  renderInfo(); renderText(); renderList(); invalidate();
  const el = document.querySelector(`.clip[data-i="${sel}"]`);
  if (el) el.scrollIntoView({ block: 'nearest' });
}

/* ---------- data helpers ---------- */
const overlaps = (a,b,c,d) => Math.min(b,d) - Math.max(a,c) > 0;
function othersIn(a, b) {
  return S.turns.filter(t => t.speaker !== S.speaker && overlaps(a,b,t.start,t.end));
}
function segsIn(a, b) {
  return S.segments.filter(s => overlaps(a,b,s.src_start,s.src_end));
}
function enFor(s) {
  const t = S.translations.find(t => overlaps(s.src_start,s.src_end,t.src_start,t.src_end));
  return t ? t.en : '';
}
// amplitude at time t, from the 10ms peak bins
function amp(t) {
  const i = Math.floor(t * 1000 / S.bin_ms);
  return (i >= 0 && i < peaks.length) ? peaks[i] : 0;
}
// walk outward for the quietest spot near t - what "snap to pause" uses
function findPause(t, dir, limit = 1.2) {
  let best = t, bestScore = Infinity;
  for (let d = 0; d <= limit; d += 0.02) {
    const p = t + dir * d;
    let win = 0;
    for (let k = -0.06; k <= 0.06; k += 0.02) win = Math.max(win, amp(p + k));
    const score = win + d * 12;          // prefer quiet, and prefer close
    if (score < bestScore) { bestScore = score; best = p; }
  }
  return +best.toFixed(3);
}

/* ---------- rendering ---------- */
function renderList() {
  $('#list').innerHTML = clips.map((c, i) => {
    const txt = segsIn(c.src_start, c.src_end).map(s => s.text).join(' ').slice(0, 60);
    return `<div class="clip${i===sel?' sel':''}${c.deleted?' deleted':''}" data-i="${i}">
      <span class="t">${String(i).padStart(3,'0')}  ${fmt(c.src_start)} · ${(c.src_end-c.src_start).toFixed(1)}s</span>
      <span class="tx">${txt || '<i>—</i>'}</span></div>`;
  }).join('');
}
function renderInfo() {
  const c = cur();
  $('#clipinfo').innerHTML =
    `<b>#${sel}</b> <span class="dim">${c.label}</span> &nbsp; ` +
    `${fmt(c.src_start)} → ${fmt(c.src_end)} &nbsp; <b>${(c.src_end-c.src_start).toFixed(2)}s</b>` +
    `&nbsp; <span class="dim">editing <b style="color:var(--me)">${edge}</b></span>`;
  const verbatim = new Set(S.sections.sections.filter(x => x.mode === 'all').map(x => x.label));
  const bad = verbatim.has(c.label) ? [] : othersIn(c.src_start, c.src_end);
  const tot = bad.reduce((n,t) => n + Math.min(c.src_end,t.end) - Math.max(c.src_start,t.start), 0);
  $('#warn').textContent = c.deleted ? 'dropped — will not be exported'
    : verbatim.has(c.label) ? `“${c.label}” — kept verbatim, English on purpose`
    : tot > 0.05 ? `⚠ ${tot.toFixed(2)}s of another speaker inside this clip` : '';
}
function renderText() {
  const c = cur();
  const a = Math.min(c.src_start, view.c - view.span/2), b = Math.max(c.src_end, view.c + view.span/2);
  $('#text').innerHTML = segsIn(a, b).map(s => {
    const inside = overlaps(c.src_start, c.src_end, s.src_start, s.src_end);
    return `<div class="row${inside?'':' out'}"><span class="t dim">${fmt(s.src_start)}</span>
      <span class="ko">${s.text}</span><br><span class="en">${enFor(s)}</span></div>`;
  }).join('') || '<span class="dim">no transcript here</span>';
}

// Resizing a canvas reallocates its backing store, so only do it when the
// size actually changed - not on every animation frame.
function setup(cv) {
  const r = cv.getBoundingClientRect(), dpr = devicePixelRatio || 1;
  const H = +cv.getAttribute('height'), w = Math.round(r.width * dpr), h = Math.round(H * dpr);
  if (cv.width !== w || cv.height !== h) { cv.width = w; cv.height = h; }
  const g = cv.getContext('2d'); g.setTransform(dpr,0,0,dpr,0,0);
  return [g, r.width, H];
}

function draw() {
  drawDetail(); drawOver();
}

function drawDetail() {
  const cv = $('#detail'); const [g, W, H] = setup(cv);
  const a = view.c - view.span/2, b = view.c + view.span/2;
  const X = t => (t - a) / (b - a) * W;
  g.clearRect(0,0,W,H);
  g.fillStyle = '#14161a'; g.fillRect(0,0,W,H);

  // ruler
  const step = view.span > 60 ? 10 : view.span > 24 ? 5 : view.span > 10 ? 2 : 1;
  g.font = '10px ui-monospace,monospace';
  for (let t = Math.ceil(a/step)*step; t < b; t += step) {
    g.strokeStyle = '#242832'; g.beginPath(); g.moveTo(X(t),18); g.lineTo(X(t),H); g.stroke();
    g.fillStyle = '#6c7484'; g.fillText(fmt(t), X(t)+3, 12);
  }

  // waveform
  const wy = 20, wh = 100;
  g.fillStyle = '#39414f';
  for (let x = 0; x < W; x++) {
    const t0 = a + (b-a)*x/W, t1 = a + (b-a)*(x+1)/W;
    let m = 0;
    for (let t = t0; t < t1; t += S.bin_ms/1000) m = Math.max(m, amp(t));
    const h = (m/255) * wh;
    g.fillRect(x, wy + wh/2 - h/2, 1, Math.max(1,h));
  }

  // kept clips
  const cy = 124, ch = 30;
  clips.forEach((c,i) => {
    if (c.src_end < a || c.src_start > b) return;
    const x0 = X(c.src_start), x1 = X(c.src_end);
    g.fillStyle = c.deleted ? '#5a606d55' : (i===sel ? '#3ddc8455' : '#3ddc8422');
    g.fillRect(x0, cy, x1-x0, ch);
    g.strokeStyle = c.deleted ? '#5a606d' : '#3ddc84';
    g.lineWidth = i===sel ? 2 : 1;
    g.strokeRect(x0, cy, x1-x0, ch);
    if (i === sel) {                                  // drag handles
      [['start',x0],['end',x1]].forEach(([e,x]) => {
        g.fillStyle = e===edge ? '#4c8dff' : '#3ddc84';
        g.fillRect(x-3, cy-5, 6, ch+10);
      });
    }
  });

  // speaker lanes
  const lane = (y, pred, col, label) => {
    g.fillStyle = '#6c7484'; g.font='9px ui-monospace,monospace'; g.fillText(label, 3, y+10);
    S.turns.filter(pred).forEach(t => {
      if (t.end < a || t.start > b) return;
      g.fillStyle = col; g.fillRect(X(t.start), y, Math.max(1, X(t.end)-X(t.start)), 12);
    });
  };
  lane(162, t => t.speaker === S.speaker, '#4c8dff', 'speaker');
  lane(178, t => t.speaker !== S.speaker, '#ff5c68', 'others');

  // transcript blocks
  g.font = '10px -apple-system,sans-serif';
  segsIn(a,b).forEach(s => {
    const x0 = X(s.src_start), w = Math.max(2, X(s.src_end)-x0);
    g.fillStyle = s.lang === 'ko' ? '#2a3446' : '#4a2630';
    g.fillRect(x0, 196, w, 16);
    g.save(); g.beginPath(); g.rect(x0,196,w,16); g.clip();
    g.fillStyle = '#aeb6c4'; g.fillText(s.text, x0+3, 208); g.restore();
  });

  // playhead
  const px = X(vid.currentTime);
  if (px >= 0 && px <= W) {
    g.strokeStyle = '#fff'; g.lineWidth = 1;
    g.beginPath(); g.moveTo(px,18); g.lineTo(px,H); g.stroke();
  }
}

function drawOver() {
  const cv = $('#over'); const [g, W, H] = setup(cv);
  const X = t => t / S.duration * W;
  g.clearRect(0,0,W,H); g.fillStyle = '#1c1f26'; g.fillRect(0,0,W,H);
  S.sections.sections.forEach(s => {
    g.fillStyle = '#232936'; g.fillRect(X(s.start), 0, X(s.end)-X(s.start), H);
  });
  clips.forEach((c,i) => {
    g.fillStyle = c.deleted ? '#5a606d' : (i===sel ? '#7bffc0' : '#3ddc84');
    g.fillRect(X(c.src_start), 12, Math.max(1, X(c.src_end)-X(c.src_start)), 26);
  });
  g.fillStyle = '#4c8dff33';
  g.fillRect(X(view.c - view.span/2), 0, Math.max(2, X(view.span)), H);
  g.strokeStyle = '#fff'; g.beginPath();
  g.moveTo(X(vid.currentTime),0); g.lineTo(X(vid.currentTime),H); g.stroke();
}

/* ---------- playback: preview the cut by seeking the source ---------- */
function playRange(t0, t1, then) {
  play = { end: t1, then };
  seek(t0); vid.play().catch(e => beacon('play: ' + e));
}
function playCutFrom(i) {
  const live = liveClips();
  const pos = live.findIndex(c => c.idx >= i);
  if (pos < 0) return;
  if (keptOnly) { play = null; select(live[pos].idx, false); seek(live[pos].src_start); vid.play().catch(()=>{}); return; }
  const step = k => {
    if (k >= live.length) { play = null; vid.pause(); return; }
    const c = live[k];
    select(c.idx, false);
    playRange(c.src_start, c.src_end, () => step(k+1));
  };
  step(pos);
}
let needsDraw = true, lastT = -1;
const invalidate = () => { needsDraw = true; };
function tick() {
  if (keptOnly && !vid.paused) {
    const tgt = keptTarget(vid.currentTime);
    if (tgt === 'end') { vid.pause(); play = null; }
    else if (tgt) { play = null; seek(tgt.src_start); if (sel !== tgt.idx) select(tgt.idx, false); }
    else {
      const here = liveClips().find(c => c.src_start - 0.02 <= vid.currentTime && vid.currentTime < c.src_end);
      if (here && sel !== here.idx) select(here.idx, false);   // list follows playback
    }
  }
  if (play && !vid.paused && vid.currentTime >= play.end) {
    const then = play.then; play = null;
    if (then) then(); else vid.pause();
  }
  // only repaint when the playhead moved or something changed
  if (needsDraw || vid.currentTime !== lastT) {
    lastT = vid.currentTime; needsDraw = false;
    draw();
  }
  requestAnimationFrame(tick);
}

/* ---------- edits ---------- */
function mark() {
  dirty = true; $('#save').classList.add('dirty'); $('#saved').textContent = 'unsaved changes';
}
function nudge(which, d) {
  const c = cur();
  if (which === 'start') c.src_start = +Math.min(c.src_end - 0.1, c.src_start + d).toFixed(3);
  else c.src_end = +Math.max(c.src_start + 0.1, c.src_end + d).toFixed(3);
  mark(); renderInfo(); renderText(); renderList(); invalidate();
}
const acts = {
  playclip() { const c = cur(); playRange(c.src_start, c.src_end); },
  audition() {
    const c = cur(), t = edge === 'start' ? c.src_start : c.src_end;
    playRange(Math.max(0, t - 2), t + 1.5);
  },
  playcut() { setKeptOnly(true); playCutFrom(sel); },
  snapstart() { cur().src_start = findPause(cur().src_start, -1); mark(); renderInfo(); invalidate(); },
  snapend()   { cur().src_end   = findPause(cur().src_end,   +1); mark(); renderInfo(); invalidate(); },
  del() { cur().deleted = !cur().deleted; mark(); renderList(); renderInfo(); invalidate(); },
  async revert() {
    if (!confirm('Discard all edits and go back to the cut the editor started from?')) return;
    clips = (await (await fetch('/api/baseline')).json()).map(c => ({ ...c, deleted: false }));
    sel = 0; mark(); renderList(); select(0);
    $('#saved').textContent = 'reverted to baseline — press Save to write it';
  },
  add() {
    const t = vid.currentTime;
    const c = { id: -1, label: cur().label, src_start: +(t-2).toFixed(3),
                src_end: +(t+2).toFixed(3), deleted: false };
    clips.push(c); clips.sort((a,b) => a.src_start - b.src_start);
    sel = clips.indexOf(c); mark(); renderList(); select(sel, false);
  },
};
document.addEventListener('click', e => {
  const b = e.target.closest('button'); if (!b) return;
  if (b.id === 'save') return save();
  if (b.dataset.act) return acts[b.dataset.act]();
  if (b.dataset.nudge) { const [w,d] = b.dataset.nudge.split(','); nudge(w, +d); }
});
$('#list').addEventListener('click', e => {
  const el = e.target.closest('.clip'); if (el) select(+el.dataset.i);
});

/* ---------- canvas interaction ---------- */
let drag = null;
$('#detail').addEventListener('mousedown', e => {
  const r = e.currentTarget.getBoundingClientRect();
  const a = view.c - view.span/2, b = view.c + view.span/2;
  const t = a + (e.clientX - r.left)/r.width * (b - a);
  const c = cur(), px = v => (v - a)/(b - a)*r.width, mx = e.clientX - r.left;
  if (Math.abs(px(c.src_start) - mx) < 7) { drag = 'start'; edge = 'start'; }
  else if (Math.abs(px(c.src_end) - mx) < 7) { drag = 'end'; edge = 'end'; }
  else { seek(t); play = null; }
  renderInfo();
});
addEventListener('mousemove', e => {
  if (!drag) return;
  const r = $('#detail').getBoundingClientRect();
  const a = view.c - view.span/2, b = view.c + view.span/2;
  const t = +(a + (e.clientX - r.left)/r.width * (b - a)).toFixed(3);
  const c = cur();
  if (drag === 'start') c.src_start = Math.min(t, c.src_end - 0.1);
  else c.src_end = Math.max(t, c.src_start + 0.1);
  mark(); renderInfo(); renderText(); invalidate();
});
addEventListener('mouseup', () => { if (drag) { drag = null; renderList(); } });
$('#detail').addEventListener('wheel', e => {
  e.preventDefault();
  if (e.shiftKey || Math.abs(e.deltaX) > Math.abs(e.deltaY)) {
    view.c += (e.deltaX || e.deltaY) * view.span / 800;
  } else {
    view.span = clamp(view.span * (e.deltaY > 0 ? 1.1 : 0.9), 2, 300);
  }
  renderText(); invalidate();
}, { passive: false });
$('#over').addEventListener('click', e => {
  const r = e.currentTarget.getBoundingClientRect();
  const t = (e.clientX - r.left)/r.width * S.duration;
  view.c = t; seek(t); play = null;
  const i = clips.findIndex(c => c.src_end >= t);
  if (i >= 0) sel = i;
  renderInfo(); renderText(); renderList(); invalidate();
});

/* ---------- keys ---------- */
addEventListener('keydown', e => {
  if (e.metaKey && e.key === 's') { e.preventDefault(); return save(); }
  if (e.metaKey || e.ctrlKey) return;
  const k = e.key;
  const big = e.shiftKey ? 0.5 : 0.1;
  if (k === 'ArrowRight') { e.preventDefault(); select(sel+1); }
  else if (k === 'ArrowLeft') { e.preventDefault(); select(sel-1); }
  else if (k === '[') { edge = 'start'; renderInfo(); }
  else if (k === ']') { edge = 'end'; renderInfo(); }
  else if (k.toLowerCase() === 'j') nudge(edge, -big);
  else if (k.toLowerCase() === 'l') nudge(edge, +big);
  else if (k === ' ') { e.preventDefault(); play = null; vid.paused ? vid.play() : vid.pause(); }
  else if (k === 'Enter') acts.playclip();
  else if (k.toLowerCase() === 'p') acts.audition();
  else if (k.toLowerCase() === 'c') acts.playcut();
  else if (k.toLowerCase() === 'a') setKeptOnly(!keptOnly);
  else if (k.toLowerCase() === 'd') acts.del();
});

/* ---------- save ---------- */
async function save() {
  const r = await (await fetch('/api/save', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ clips })
  })).json();
  dirty = false; $('#save').classList.remove('dirty');
  $('#saved').textContent = `saved ${r.clips} clips · ${fmt(r.duration)}`;
}
addEventListener('beforeunload', e => { if (dirty) e.preventDefault(); });
