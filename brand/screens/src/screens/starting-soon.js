// Starting soon: for the livestream before going live when there is no exact time.
(function () {
  const { ep, ease } = HB;
  const SLOT = 12; // seconds per message

  const schema = [
    { key: 'heading', type: 'text', label: 'Heading', unit: '', default: 'Starting soon', param: 'h' },
    { key: 'show', type: 'check', label: 'Start time', text: 'Show when we go live', default: false, param: 'show' },
    { key: 'at', type: 'time', label: 'We go live at', default: '11:00', param: 'at', inline: true, when: v => v.show },
    HB.THEME,
    { key: 'messages', type: 'lines', label: 'Messages', default: [['Living Out The Gospel', 'Together Wholeheartedly']], param: 'm' },
  ];

  const stage = document.getElementById('stage');
  const card = HB.card(stage);
  const msgs = document.createElement('div');
  msgs.className = 'card-sub card-msgs';
  const live = document.createElement('div');
  live.className = 'card-sub';
  card.addSub(msgs);
  card.addSub(live);

  let msgEls = [];
  function setMessages(list) {
    msgs.innerHTML = '';
    msgs.hidden = !list.length;
    msgEls = list.map(lines => {
      const d = msgs.appendChild(document.createElement('div'));
      lines.forEach(l => { d.appendChild(document.createElement('span')).textContent = l; });
      return d;
    });
  }
  function setLive(v) {
    live.hidden = !v.show;
    live.textContent = v.show ? `We go live at ${HB.formatClockTime(v.at)}` : '';
  }

  const panel = HB.panel({
    id: 'starting-soon',
    title: 'Starting soon settings',
    schema,
    linkKeys: v => (v.show ? ['show', 'at'] : []),
    skipSave: ['messages'],
    onChange(key, v) {
      if (key === 'heading') card.setHeading(v.heading || 'Starting soon');
      else if (key === 'messages') setMessages(v.messages);
      else setLive(v);
    },
  });

  const v0 = panel.values;
  if (panel.demo) v0.show = true;
  card.setHeading(v0.heading || 'Starting soon');
  setMessages(v0.messages);
  setLive(v0);
  HB.watchStage(stage, () => card.fit());

  // One message stays put; several take turns, each fading up and out.
  HB.loop(t => {
    card.frame(t);
    const n = msgEls.length, slot = Math.floor(t / SLOT);
    msgEls.forEach((m, i) => {
      if (n === 1) { m.style.opacity = 1; return; }
      const t0 = slot * SLOT, on = slot % n === i;
      const o = on ? ep(t, t0, 0.8) * (1 - ep(t, t0 + SLOT - 0.8, 0.8, ease.inCubic)) : 0;
      m.style.opacity = o;
      m.style.transform = `translateY(${(1 - o) * 0.6}em)`;
    });
  });
})();
