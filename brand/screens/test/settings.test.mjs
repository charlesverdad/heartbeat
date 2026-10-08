import test from 'node:test';
import assert from 'node:assert/strict';
await import('../src/shared/core.js');
await import('../src/shared/settings.js');
const HB = globalThis.HB;

const MSGS = [['A', 'B'], ['C']];
const schema = [
  ...[
    { key: 'kind', type: 'seg', label: 'Count', options: [['minutes', 'Timer'], ['until', 'Until']], default: 'minutes', param: 'kind' },
    { key: 'mins', type: 'number', label: 'Minutes', min: 1, max: 180, default: 5, param: 'min', when: v => v.kind === 'minutes' },
    { key: 'at', type: 'time', label: 'Start time', default: '11:00', param: 'at', when: v => v.kind === 'until' },
  ],
  { key: 'bar', type: 'seg', label: 'Bar', options: [['top', 'Top'], ['bottom', 'Bottom']], default: 'top', param: 'bar' },
  { key: 'big', type: 'check', label: 'Last 10 s', default: true, param: 'big' },
  { key: 'messages', type: 'lines', label: 'Messages', default: MSGS, param: 'm' },
];
const P = s => new URLSearchParams(s);

test('defaults include theme and clone list values', () => {
  const d = HB.defaults(HB.withTheme(schema));
  assert.equal(d.theme, 'dark');
  assert.equal(d.mins, 5);
  assert.deepEqual(d.messages, MSGS);
  d.messages[0].push('x');
  assert.deepEqual(schema[5].default, MSGS);
});

test('fromParams reads only what the link sets and validates', () => {
  assert.deepEqual(HB.fromParams(schema, P('')), {});
  assert.deepEqual(HB.fromParams(schema, P('bar=bottom&theme=light')), { bar: 'bottom', theme: 'light' });
  assert.deepEqual(HB.fromParams(schema, P('bar=sideways&min=abc')), {});
  assert.equal(HB.fromParams(schema, P('min=999')).mins, 180);
  assert.equal(HB.fromParams(schema, P('at=25')).at, undefined);
});

test('toParams/fromParams round trip', () => {
  const v = { ...HB.defaults(HB.withTheme(schema)), kind: 'until', at: '09:30', bar: 'bottom', big: false, theme: 'light', messages: [['One', 'Two'], ['Three']] };
  const q = HB.toParams(schema, v);
  assert.deepEqual(HB.fromParams(schema, P(q)), { kind: 'until', at: '09:30', bar: 'bottom', big: false, theme: 'light', messages: [['One', 'Two'], ['Three']] });
});

test('toParams omits defaults, adds always keys and autostart', () => {
  const v = HB.defaults(HB.withTheme(schema));
  assert.equal(HB.toParams(schema, v), '');
  assert.equal(HB.toParams(schema, v, { autostart: true }), 'autostart');
  assert.equal(HB.toParams(schema, v, { always: ['kind', 'mins'] }), 'kind=minutes&min=5');
  assert.equal(HB.toParams(schema, { ...v, big: false }), 'big=0');
});

test('merge order: defaults < saved < link', () => {
  const r = HB.resolve(HB.withTheme(schema), { mins: 10, bar: 'bottom', bogus: 1 }, { bar: 'top', theme: 'light' });
  assert.equal(r.mins, 10);
  assert.equal(r.bar, 'top');
  assert.equal(r.theme, 'light');
  assert.equal(r.bogus, undefined);
});

test('savable drops defaults and skipped keys', () => {
  const v = { ...HB.defaults(HB.withTheme(schema)), mins: 8, messages: [['Z']] };
  assert.deepEqual(HB.savable(schema, v, ['messages']), { mins: 8 });
});

// ---- countdown backward-compatible links ----
const legacy = (qs) => HB.fromParams(schema, P(qs), (out, params) => {
  if (params.get('at')) out.kind = 'until';
  else if (params.get('min')) out.kind = 'minutes';
  return out;
});

test('countdown links: ?min', () => {
  assert.deepEqual(legacy('min=10'), { mins: 10, kind: 'minutes' });
});
test('countdown links: ?at implies until', () => {
  assert.deepEqual(legacy('at=11:00'), { at: '11:00', kind: 'until' });
});
test('countdown links: ?big=0 and ?bar/theme', () => {
  assert.deepEqual(legacy('big=0&bar=bottom&theme=light'), { big: false, bar: 'bottom', theme: 'light' });
});
test('countdown links: repeated ?m with |', () => {
  assert.deepEqual(legacy('m=Hello%7CWorld&m=Second'), { messages: [['Hello', 'World'], ['Second']] });
});
test('countdown links: ?autostart is a flag, ignored by values', () => {
  assert.deepEqual(legacy('autostart'), {});
  assert.equal(HB.toParams(schema, HB.defaults(HB.withTheme(schema)), { autostart: true, always: ['theme'] }), 'theme=dark&autostart');
});
