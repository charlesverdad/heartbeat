// Be right back: a break or technical hold, with an optional "Back in 1:59" clock.
(function () {
  const { clamp } = HB;
  const DEFAULT = 'We’ll be right back';

  const schema = [
    { key: 'heading', type: 'text', label: 'Heading', unit: '', default: DEFAULT, param: 'h' },
    { key: 'timer', type: 'check', label: 'Timer', text: 'Show a back-in clock', default: false, param: 'timer' },
    { key: 'mins', type: 'number', label: 'Minutes', min: 1, max: 180, unit: 'min', default: 2, param: 'min', inline: true, when: v => v.timer },
    HB.THEME,
  ];

  const stage = document.getElementById('stage');
  const card = HB.card(stage);
  const sub = document.createElement('div');
  sub.className = 'card-sub';
  sub.innerHTML = '<span id="lead">Back in </span><span id="clock" role="timer" style="display:inline-flex;font-variant-numeric:tabular-nums"></span>';
  card.addSub(sub);
  const lead = sub.querySelector('#lead'), clockEl = sub.querySelector('#clock');
  const setClock = HB.rollClock(clockEl);

  // At zero the clock gives way to words rather than 0:00.
  function show(f, on) {
    sub.hidden = !on;
    if (!on) return;
    const zero = !f.idle && f.n <= 0;
    lead.textContent = zero ? 'Back shortly' : 'Back in ';
    clockEl.hidden = zero;
    if (!zero) setClock(f.n, f.phase);
  }

  let panel;
  const timer = HB.createTimer({
    values: () => ({ kind: 'minutes', mins: panel.values.mins }),
    onChange: refreshButtons,
    keepAwake: () => panel.keepAwake(),
  });
  function refreshButtons() {
    const on = panel.values.timer;
    panel.setAction('go', { ...timer.button(), disabled: !on });
    panel.setAction('reset', { text: 'Reset', disabled: !on });
  }
  const step = d => { if (timer.mode === 'idle' && panel.values.timer) panel.set('mins', clamp(panel.values.mins + d, 1, 180)); };

  panel = HB.panel({
    id: 'be-right-back',
    title: 'Be right back settings',
    schema,
    linkKeys: v => (v.timer ? ['timer', 'mins'] : []),
    startable: true,
    actions: [
      { id: 'reset', label: 'Reset', onclick: () => timer.reset() },
      { id: 'go', label: 'Start', primary: true, onclick: () => timer.start() },
    ],
    keyHelp: [['Space', 'start / pause'], ['R', 'reset']],
    keys: { ' ': () => panel.values.timer && timer.start(), r: () => timer.reset(), arrowup: () => step(1), arrowdown: () => step(-1) },
    enter: () => panel.values.timer && timer.start(),
    onChange(key, v) {
      if (key === 'heading') card.setHeading(v.heading || DEFAULT);
      else if (key === 'mins') timer.refresh();
      else if (key === 'timer') { timer.reset(); refreshButtons(); }
    },
  });

  if (panel.demo) panel.values.timer = true;
  card.setHeading(panel.values.heading || DEFAULT);
  HB.watchStage(stage, () => card.fit());
  timer.reset();
  if (panel.autostart && panel.values.timer) timer.start();

  if (panel.demo) {
    // Homepage preview: a two-minute clock running, looping after a moment of "Back shortly".
    const COUNT = 120, LOOP = 126, SKIP = Number(new URLSearchParams(location.search).get('t')) || 0;
    HB.loop(s => {
      card.frame(s);
      const t = (s + SKIP) % LOOP;
      show({ idle: false, ...HB.tick(t, COUNT) }, true);
    });
  } else {
    HB.loop(s => { card.frame(s); show(timer.frame(), panel.values.timer); });
  }
})();
